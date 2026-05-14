from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, List, Optional
from sqlalchemy import select, func, tuple_
from datetime import datetime, timezone
import asyncio
import json
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.models import Resume, JobPreference, Opportunity, UserJobMatch, DailyTask
from app.services.linkedin_service import LinkedInService
from app.services.preference_extractor import PreferenceStructuredFields
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def _parse_posted_at(value):
    """Best-effort parse for external provider timestamps."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (TypeError, ValueError, OSError):
            return None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        for candidate in (normalized, normalized.replace(" ", "T", 1)):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
    return None


def _build_preference_context(pref: JobPreference) -> dict:
    fields = PreferenceStructuredFields.model_validate(pref.effective_fields or {})
    profile_text = pref.raw_text or ""
    return {
        "keywords": ", ".join(fields.keywords),
        "location": fields.locations[0] if fields.locations else None,
        "locations": fields.locations,
        "is_intern": fields.is_intern,
        "need_sponsor": fields.need_sponsor,
        "job_description": profile_text,
        "profile_text": profile_text,
        "remote_preference": fields.remote_preference,
        "excluded_companies": fields.excluded_companies,
    }


def _extract_json_payload(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    object_start = content.find("{")
    array_start = content.find("[")

    if object_start != -1 and (array_start == -1 or object_start < array_start):
        object_end = content.rfind("}") + 1
        if object_end > object_start:
            return json.loads(content[object_start:object_end])

    array_end = content.rfind("]") + 1
    if array_start != -1 and array_end > array_start:
        return json.loads(content[array_start:array_end])

    if object_start != -1:
        object_end = content.rfind("}") + 1
        return json.loads(content[object_start:object_end])

    raise json.JSONDecodeError("No JSON payload found", content, 0)


def _normalize_score_item(item: dict) -> dict:
    return {
        "score": int(item.get("score", 0) or 0),
        "reason": item.get("reason", "") or "",
        "matched_skills": item.get("matched_skills", []) or [],
        "missing_skills": item.get("missing_skills", []) or [],
    }


class AgentState(TypedDict):
    """State for the job matching agent."""
    resume_text: str
    resume_embedding: Optional[List[float]]
    preferences: dict
    raw_jobs: List[dict]
    scored_jobs: List[dict]
    matched_jobs: List[dict]
    threshold: int
    candidate_stats: dict
    error: Optional[str]


class JobMatchingAgent:
    """LangGraph agent for job matching workflow."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.3
        )
        self.linkedin_service = LinkedInService()
        self.rag_service = RAGService()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("fetch_context", self._fetch_context)
        workflow.add_node("search_jobs", self._search_jobs)
        workflow.add_node("analyze_matches", self._analyze_matches)
        workflow.add_node("filter_and_adjust", self._filter_and_adjust)
        workflow.add_node("save_results", self._save_results)

        # Define edges
        workflow.set_entry_point("fetch_context")
        workflow.add_edge("fetch_context", "search_jobs")
        workflow.add_edge("search_jobs", "analyze_matches")
        workflow.add_edge("analyze_matches", "filter_and_adjust")

        # Conditional edge: check if we have enough matches
        workflow.add_conditional_edges(
            "filter_and_adjust",
            self._should_continue,
            {
                "save": "save_results",
                "retry": "filter_and_adjust",
                "end": END
            }
        )

        workflow.add_edge("save_results", END)

        return workflow.compile()

    async def _fetch_context(self, state: AgentState) -> AgentState:
        """Fetch resume and preferences from database."""
        async with async_session_maker() as db:
            # Get resume
            resume_result = await db.execute(
                select(Resume)
                .where(Resume.user_id == self.user_id)
                .order_by(Resume.uploaded_at.desc())
                .limit(1)
            )
            resume = resume_result.scalar_one_or_none()

            # Get preferences
            pref_result = await db.execute(
                select(JobPreference)
                .where(JobPreference.user_id == self.user_id)
                .order_by(JobPreference.created_at.desc())
                .limit(1)
            )
            pref = pref_result.scalar_one_or_none()

            if not resume or not pref:
                return {**state, "error": "Missing resume or preferences"}

            return {
                **state,
                "resume_text": resume.content or "",
                "resume_embedding": resume.embedding,
                "preferences": _build_preference_context(pref),
                "threshold": settings.MATCH_THRESHOLD
            }

    async def _search_jobs(self, state: AgentState) -> AgentState:
        """Load open synced opportunities, with legacy public API fallback."""
        if state.get("error"):
            return state

        prefs = state["preferences"]
        logger.info(
            "Loading synced opportunities with keywords=%s, location=%s, is_intern=%s",
            prefs["keywords"],
            prefs.get("location"),
            prefs.get("is_intern"),
        )

        jobs, candidate_stats = await self._load_synced_opportunities(
            prefs,
            state.get("resume_embedding"),
            limit=max(settings.TARGET_JOBS * 3, 20),
        )
        if jobs:
            logger.info("Loaded %s synced opportunities for scoring", len(jobs))
            return {**state, "raw_jobs": jobs, "candidate_stats": candidate_stats}

        logger.info("No synced opportunities available; falling back to legacy public job APIs")
        legacy_jobs = await self.linkedin_service.search_jobs(
            keywords=prefs["keywords"],
            location=prefs.get("location"),
            limit=20,
            is_intern=prefs.get("is_intern", False)
        )

        logger.info("Legacy public APIs returned %s jobs", len(legacy_jobs))
        return {
            **state,
            "raw_jobs": legacy_jobs,
            "candidate_stats": {
                "source": "legacy",
                "open_opportunities": candidate_stats.get("open_opportunities", 0),
                "after_hard_filters": 0,
                "after_structured_prefilter": 0,
                "scored_candidates": len(legacy_jobs),
                "candidate_limit": 20,
                "used_fallback": True,
            },
        }

    async def _load_synced_opportunities(
        self,
        prefs: dict,
        query_embedding: list[float] | None,
        limit: int,
    ) -> tuple[list[dict], dict]:
        query_vector = list(query_embedding) if query_embedding is not None else None
        async with async_session_maker() as db:
            result = await db.execute(
                select(Opportunity)
                .where(Opportunity.is_open.is_(True))
                .order_by(Opportunity.last_seen_at.desc(), Opportunity.updated_at.desc())
                .limit(200)
            )
            recent_opportunities = result.scalars().all()

            vector_distances: dict[str, float] = {}
            vector_opportunities: list[Opportunity] = []
            if query_vector is not None:
                distance = Opportunity.embedding.cosine_distance(query_vector).label("vector_distance")
                vector_result = await db.execute(
                    select(Opportunity, distance)
                    .where(
                        Opportunity.is_open.is_(True),
                        Opportunity.embedding.is_not(None),
                    )
                    .order_by(distance, Opportunity.last_seen_at.desc(), Opportunity.updated_at.desc())
                    .limit(max(limit * 4, 80))
                )
                for opportunity, vector_distance in vector_result.all():
                    vector_opportunities.append(opportunity)
                    if vector_distance is not None:
                        vector_distances[opportunity.id] = float(vector_distance)

        opportunities_by_id = {opportunity.id: opportunity for opportunity in vector_opportunities}
        for opportunity in recent_opportunities:
            opportunities_by_id.setdefault(opportunity.id, opportunity)
        opportunities = list(opportunities_by_id.values())

        stats = {
            "source": "synced_opportunities",
            "open_opportunities": len(opportunities),
            "vector_candidates": len(vector_opportunities),
            "after_hard_filters": 0,
            "after_structured_prefilter": 0,
            "scored_candidates": 0,
            "candidate_limit": limit,
            "used_fallback": False,
        }
        excluded = {company.strip().lower() for company in prefs.get("excluded_companies", []) if company.strip()}
        keywords = [keyword.strip().lower() for keyword in prefs.get("keywords", "").split(",") if keyword.strip()]
        locations = [location.strip().lower() for location in prefs.get("locations", []) if location.strip()]
        remote_preference = prefs.get("remote_preference")
        is_intern = prefs.get("is_intern", False)

        ranked: list[tuple[int, Opportunity]] = []
        for opportunity in opportunities:
            company_lower = (opportunity.company or "").lower()
            if company_lower in excluded or any(excluded_company in company_lower for excluded_company in excluded):
                continue

            title_lower = (opportunity.title or "").lower()
            description_lower = (opportunity.description or "").lower()
            location_lower = (opportunity.location or "").lower()
            searchable_text = f"{title_lower} {description_lower}"

            if is_intern and "intern" not in title_lower and "internship" not in title_lower:
                continue

            rank = 0
            if keywords and any(keyword in searchable_text for keyword in keywords):
                rank += 3
            if locations and any(location in location_lower for location in locations):
                rank += 2
            if remote_preference == "remote" and "remote" in location_lower:
                rank += 1
            if opportunity.id in vector_distances:
                similarity = max(0.0, 1.0 - vector_distances[opportunity.id])
                rank += 2 + min(5, int(similarity * 5))
            if opportunity.source_type == "greenhouse":
                rank += 1

            ranked.append((rank, opportunity))

        stats["after_hard_filters"] = len(ranked)
        if keywords and ranked and max(rank for rank, _ in ranked) > 0:
            ranked = [item for item in ranked if item[0] > 0]
        stats["after_structured_prefilter"] = len(ranked)

        def sort_timestamp(opportunity: Opportunity) -> float:
            value = opportunity.last_seen_at or opportunity.updated_at or opportunity.created_at
            return value.timestamp() if value else 0.0

        ranked.sort(key=lambda item: (item[0], sort_timestamp(item[1])), reverse=True)
        selected = ranked[:limit]
        stats["scored_candidates"] = len(selected)

        return [
            {
                "source_type": opportunity.source_type,
                "source_job_id": opportunity.source_job_id,
                "title": opportunity.title,
                "company": opportunity.company,
                "location": opportunity.location,
                "salary": opportunity.salary,
                "url": opportunity.url,
                "description": opportunity.description,
                "posted_at": opportunity.posted_at,
                "raw_payload": opportunity.raw_payload,
            }
            for _, opportunity in selected
        ], stats

    async def _analyze_matches(self, state: AgentState) -> AgentState:
        """Analyze job-resume match scores using LLM."""
        raw_jobs = state.get("raw_jobs", [])
        logger.info(f"Analyzing {len(raw_jobs)} jobs for match scores...")

        if state.get("error") or not raw_jobs:
            logger.warning("No jobs to analyze or error occurred")
            return {**state, "scored_jobs": []}

        resume = state["resume_text"]
        profile_text = state.get("preferences", {}).get("profile_text", "")
        rerank_limit = max(settings.TARGET_JOBS, settings.MATCH_LLM_RERANK_LIMIT)
        batch_size = max(1, settings.MATCH_LLM_BATCH_SIZE)
        candidate_jobs = raw_jobs[:rerank_limit]
        batches = [
            candidate_jobs[index:index + batch_size]
            for index in range(0, len(candidate_jobs), batch_size)
        ]

        results_by_batch = await asyncio.gather(
            *(self._score_job_batch(resume, profile_text, batch) for batch in batches),
            return_exceptions=True,
        )

        scored_jobs = []
        for batch, batch_result in zip(batches, results_by_batch):
            if isinstance(batch_result, Exception):
                logger.error("Error scoring job batch: %s", batch_result)
                fallback_results = await asyncio.gather(
                    *(self._score_job(resume, profile_text, job) for job in batch),
                    return_exceptions=True,
                )
                batch_scores = []
                for job, fallback_score in zip(batch, fallback_results):
                    if isinstance(fallback_score, Exception):
                        logger.error("Error scoring job %s: %s", job.get("title"), fallback_score)
                        continue
                    batch_scores.append((job, fallback_score))
            else:
                batch_scores = list(zip(batch, batch_result))

            for job, score_data in batch_scores:
                if isinstance(score_data, Exception):
                    logger.error("Error scoring job %s: %s", job.get("title"), score_data)
                    continue
                scored_jobs.append({
                    **job,
                    "match_score": score_data.get("score", 0),
                    "match_reason": score_data.get("reason", ""),
                    "matched_skills": json.dumps(score_data.get("matched_skills", [])),
                    "missing_skills": json.dumps(score_data.get("missing_skills", [])),
                })

        candidate_stats = {
            **state.get("candidate_stats", {}),
            "llm_rerank_limit": rerank_limit,
            "llm_scored_candidates": len(candidate_jobs),
            "llm_batch_size": batch_size,
            "llm_batches": len(batches),
        }
        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return {**state, "scored_jobs": scored_jobs, "candidate_stats": candidate_stats}

    async def _score_job_batch(self, resume: str, profile_text: str, jobs: list[dict]) -> list[dict]:
        """Score a batch of candidate jobs against the resume."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a career advisor ranking job-resume fit. Be objective and precise."),
            ("human", """
Analyze the match between this resume and each job posting.

RESUME:
{resume}

JOB SEARCH PROFILE:
{profile_text}

JOBS JSON:
{jobs_json}

Return a JSON array. Each item must include:
- index: original job index from JOBS JSON
- score: 0-100 match score
- reason: 1-2 sentence explanation
- matched_skills: list of matching skills
- missing_skills: list of required but missing skills

JSON array only, no markdown:
""")
        ])

        jobs_for_prompt = [
            {
                "index": index,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "description": (job.get("description") or "")[:1200],
            }
            for index, job in enumerate(jobs)
        ]
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "resume": resume[:3000],
            "profile_text": profile_text[:1500],
            "jobs_json": json.dumps(jobs_for_prompt),
        })

        parsed = _extract_json_payload(response.content)
        if isinstance(parsed, dict):
            parsed = parsed.get("results") or parsed.get("jobs") or []
        if not isinstance(parsed, list):
            raise ValueError("Batch scorer returned non-list JSON")

        score_by_index = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if isinstance(index, int) and 0 <= index < len(jobs):
                score_by_index[index] = _normalize_score_item(item)

        return [
            score_by_index.get(
                index,
                {"score": 0, "reason": "Unable to analyze", "matched_skills": [], "missing_skills": []},
            )
            for index in range(len(jobs))
        ]

    async def _score_job(self, resume: str, profile_text: str, job: dict) -> dict:
        """Score a single job against the resume."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a career advisor analyzing job-resume fit. Be objective and precise."),
            ("human", """
Analyze the match between this resume and job posting.

RESUME:
{resume}

JOB SEARCH PROFILE:
{profile_text}

JOB:
Title: {title}
Company: {company}
Description: {description}

Return a JSON object with:
- score: 0-100 match score
- reason: 2-3 sentence explanation
- matched_skills: list of matching skills
- missing_skills: list of required but missing skills

JSON only, no markdown:
""")
        ])

        chain = prompt | self.llm

        response = await chain.ainvoke({
            "resume": resume[:3000],  # Limit for token efficiency
            "profile_text": profile_text[:1500],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": job.get("description", "")[:2000]
        })

        # Parse JSON response
        try:
            return _normalize_score_item(_extract_json_payload(response.content))
        except (json.JSONDecodeError, ValueError):
            return {"score": 50, "reason": "Unable to analyze", "matched_skills": [], "missing_skills": []}

    async def _filter_and_adjust(self, state: AgentState) -> AgentState:
        """Filter jobs by threshold, adjust threshold if needed for next iteration."""
        threshold = state["threshold"]
        scored_jobs = state.get("scored_jobs", [])

        # Filter jobs by current threshold
        matched = [j for j in scored_jobs if j["match_score"] >= threshold]
        logger.info(f"Filtering: threshold={threshold}, scored={len(scored_jobs)}, matched={len(matched)}")

        # Determine next threshold (for potential retry)
        next_threshold = threshold
        if len(matched) < settings.TARGET_JOBS and threshold > settings.MIN_THRESHOLD:
            next_threshold = threshold - settings.THRESHOLD_STEP
            logger.info(f"Lowering threshold: {threshold} -> {next_threshold}")

        return {
            **state,
            "matched_jobs": matched,
            "threshold": next_threshold  # Update threshold for next iteration
        }

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue, retry with lower threshold, or end."""
        matched = state.get("matched_jobs", [])
        threshold = state["threshold"]
        scored_jobs = state.get("scored_jobs", [])

        # If we have enough matches, save them without pre-generating cover letters.
        if len(matched) >= settings.TARGET_JOBS:
            return "save"

        # If no scored jobs at all, just proceed with what we have
        if not scored_jobs:
            return "save"

        # Check if we can still lower threshold (threshold was already lowered in filter_and_adjust)
        # If threshold hasn't changed from MIN, we've hit the bottom
        if threshold <= settings.MIN_THRESHOLD:
            return "save"

        # Otherwise retry with the new (already lowered) threshold
        return "retry"

    async def generate_cover_letter_for_job(self, resume: str, user_match: UserJobMatch) -> str:
        """Generate a cover letter for a persisted match."""
        opportunity = user_match.opportunity
        return await self._generate_cover_letter(
            resume,
            {
                "title": opportunity.title,
                "company": opportunity.company,
                "match_reason": user_match.match_reason or "",
            },
        )

    async def _generate_cover_letter(self, resume: str, job: dict) -> str:
        """Generate a cover letter for a job."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional career advisor writing compelling cover letters."),
            ("human", """
Write a concise cover letter (250 words max) for this job application.

RESUME HIGHLIGHTS:
{resume}

JOB:
Title: {title}
Company: {company}
Why I'm a good fit: {reason}

Write a professional, enthusiastic cover letter. Be specific about skills and experience.
Do not include placeholders like [Your Name] - write it ready to use.
""")
        ])

        chain = prompt | self.llm

        response = await chain.ainvoke({
            "resume": resume[:2000],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "reason": job.get("match_reason", "")
        })

        return response.content

    async def _save_results(self, state: AgentState) -> AgentState:
        """Save matched jobs to database and create daily tasks."""
        matched = state.get("matched_jobs", [])
        now = datetime.now(timezone.utc)
        today = now.date()
        current_match_ids: set[str] = set()

        async with async_session_maker() as db:
            prepared_jobs = []
            for i, job_data in enumerate(matched):
                source_type = job_data.get("source_type") or "legacy"
                source_job_id = str(
                    job_data.get("source_job_id")
                    or job_data.get("linkedin_job_id")
                    or job_data.get("url")
                    or f"generated-{i}"
                )
                prepared_jobs.append((i, job_data, source_type, source_job_id))

            source_keys = [(source_type, source_job_id) for _, _, source_type, source_job_id in prepared_jobs]
            existing_opportunities: dict[tuple[str, str], Opportunity] = {}
            if source_keys:
                opportunity_result = await db.execute(
                    select(Opportunity).where(
                        tuple_(Opportunity.source_type, Opportunity.source_job_id).in_(source_keys)
                    )
                )
                existing_opportunities = {
                    (opportunity.source_type, opportunity.source_job_id): opportunity
                    for opportunity in opportunity_result.scalars().all()
                }

            opportunity_rows: list[tuple[int, dict, Opportunity]] = []
            for i, job_data, source_type, source_job_id in prepared_jobs:
                opportunity = existing_opportunities.get((source_type, source_job_id))
                if opportunity is None:
                    opportunity = Opportunity(
                        source_type=source_type,
                        source_job_id=source_job_id,
                        title=job_data["title"],
                        company=job_data["company"],
                        location=job_data.get("location"),
                        salary=job_data.get("salary"),
                        url=job_data.get("url"),
                        description=job_data.get("description"),
                        raw_payload=job_data.get("raw_payload"),
                        posted_at=_parse_posted_at(job_data.get("posted_at")),
                        is_open=True,
                    )
                    db.add(opportunity)
                else:
                    opportunity.title = job_data["title"]
                    opportunity.company = job_data["company"]
                    opportunity.location = job_data.get("location")
                    opportunity.salary = job_data.get("salary")
                    opportunity.url = job_data.get("url")
                    opportunity.description = job_data.get("description")
                    opportunity.raw_payload = job_data.get("raw_payload")
                    opportunity.posted_at = _parse_posted_at(job_data.get("posted_at")) or opportunity.posted_at
                    opportunity.is_open = True
                    opportunity.last_seen_at = now
                opportunity_rows.append((i, job_data, opportunity))

            if opportunity_rows:
                await db.flush()

            opportunity_ids = [opportunity.id for _, _, opportunity in opportunity_rows]
            existing_matches: dict[str, UserJobMatch] = {}
            if opportunity_ids:
                match_result = await db.execute(
                    select(UserJobMatch).where(
                        UserJobMatch.user_id == self.user_id,
                        UserJobMatch.opportunity_id.in_(opportunity_ids),
                    )
                )
                existing_matches = {
                    user_match.opportunity_id: user_match
                    for user_match in match_result.scalars().all()
                }

            match_rows: list[tuple[int, UserJobMatch]] = []
            for i, job_data, opportunity in opportunity_rows:
                user_match = existing_matches.get(opportunity.id)
                if user_match is None:
                    user_match = UserJobMatch(
                        user_id=self.user_id,
                        opportunity_id=opportunity.id,
                        match_score=job_data["match_score"],
                        match_reason=job_data.get("match_reason"),
                        matched_skills=job_data.get("matched_skills"),
                        missing_skills=job_data.get("missing_skills"),
                        cover_letter=job_data.get("cover_letter"),
                    )
                    db.add(user_match)
                else:
                    user_match.match_score = job_data["match_score"]
                    user_match.match_reason = job_data.get("match_reason")
                    user_match.matched_skills = job_data.get("matched_skills")
                    user_match.missing_skills = job_data.get("missing_skills")
                    if "cover_letter" in job_data:
                        user_match.cover_letter = job_data.get("cover_letter")
                    user_match.last_scored_at = now
                match_rows.append((i, user_match))

            if match_rows:
                await db.flush()

            match_ids = [user_match.id for _, user_match in match_rows]
            existing_tasks: dict[str, DailyTask] = {}
            if match_ids:
                task_result = await db.execute(
                    select(DailyTask).where(
                        DailyTask.user_job_match_id.in_(match_ids),
                        func.date(DailyTask.date) == today,
                    )
                )
                existing_tasks = {
                    task.user_job_match_id: task
                    for task in task_result.scalars().all()
                    if task.user_job_match_id
                }

            for i, user_match in match_rows:
                current_match_ids.add(user_match.id)
                existing_task = existing_tasks.get(user_match.id)

                if existing_task is None:
                    task = DailyTask(
                        user_job_match_id=user_match.id,
                        task_order=i,
                    )
                    db.add(task)
                else:
                    existing_task.task_order = i

            if current_match_ids:
                stale_tasks_result = await db.execute(
                    select(DailyTask)
                    .join(DailyTask.user_job_match)
                    .where(
                        UserJobMatch.user_id == self.user_id,
                        func.date(DailyTask.date) == today,
                    )
                )
                for task in stale_tasks_result.scalars().all():
                    if task.user_job_match_id not in current_match_ids and not task.is_completed:
                        await db.delete(task)

            await db.commit()

        return state

    async def run(self) -> dict:
        """Execute the job matching workflow."""
        workflow = self._create_workflow()

        initial_state: AgentState = {
            "resume_text": "",
            "preferences": {},
            "raw_jobs": [],
            "scored_jobs": [],
            "matched_jobs": [],
            "threshold": settings.MATCH_THRESHOLD,
            "resume_embedding": None,
            "candidate_stats": {},
            "error": None
        }

        # Configure with higher recursion limit for adaptive threshold iterations
        config = {"recursion_limit": 50}

        try:
            logger.info("Starting job matching workflow...")
            final_state = await workflow.ainvoke(initial_state, config=config)
            matched_jobs = final_state.get("matched_jobs", [])
            source_counts: dict[str, int] = {}
            for job in matched_jobs:
                source_type = job.get("source_type") or "unknown"
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            return {
                "success": True,
                "jobs_found": len(matched_jobs),
                "final_threshold": final_state.get("threshold"),
                "used_synced_opportunities": bool(source_counts.get("greenhouse")),
                "source_counts": source_counts,
                "candidate_stats": final_state.get("candidate_stats", {}),
            }
        except Exception as e:
            logger.error(f"Agent workflow error: {e}")
            return {"success": False, "error": str(e)}
