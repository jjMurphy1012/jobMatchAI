from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, List, Optional, Annotated
from operator import add
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


class AgentState(TypedDict):
    """State for the job matching agent."""
    resume_text: str
    preferences: dict
    raw_jobs: List[dict]
    scored_jobs: List[dict]
    matched_jobs: List[dict]
    threshold: int
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
        workflow.add_node("generate_content", self._generate_content)
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
                "generate": "generate_content",
                "retry": "filter_and_adjust",
                "end": END
            }
        )

        workflow.add_edge("generate_content", "save_results")
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

        jobs = await self._load_synced_opportunities(prefs, limit=max(settings.TARGET_JOBS * 3, 20))
        if jobs:
            logger.info("Loaded %s synced opportunities for scoring", len(jobs))
            return {**state, "raw_jobs": jobs}

        logger.info("No synced opportunities available; falling back to legacy public job APIs")
        legacy_jobs = await self.linkedin_service.search_jobs(
            keywords=prefs["keywords"],
            location=prefs.get("location"),
            limit=20,
            is_intern=prefs.get("is_intern", False)
        )

        logger.info("Legacy public APIs returned %s jobs", len(legacy_jobs))
        return {**state, "raw_jobs": legacy_jobs}

    async def _load_synced_opportunities(self, prefs: dict, limit: int) -> list[dict]:
        async with async_session_maker() as db:
            result = await db.execute(
                select(Opportunity)
                .where(Opportunity.is_open.is_(True))
                .order_by(Opportunity.last_seen_at.desc(), Opportunity.updated_at.desc())
                .limit(200)
            )
            opportunities = result.scalars().all()

        excluded = {company.strip().lower() for company in prefs.get("excluded_companies", []) if company.strip()}
        keywords = [keyword.strip().lower() for keyword in prefs.get("keywords", "").split(",") if keyword.strip()]
        locations = [location.strip().lower() for location in prefs.get("locations", []) if location.strip()]
        remote_preference = prefs.get("remote_preference")
        is_intern = prefs.get("is_intern", False)

        ranked: list[tuple[int, Opportunity]] = []
        for opportunity in opportunities:
            company_lower = (opportunity.company or "").lower()
            if company_lower in excluded:
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
            if opportunity.source_type == "greenhouse":
                rank += 1

            ranked.append((rank, opportunity))

        if keywords and ranked and max(rank for rank, _ in ranked) > 0:
            ranked = [item for item in ranked if item[0] > 0]

        def sort_timestamp(opportunity: Opportunity) -> float:
            value = opportunity.last_seen_at or opportunity.updated_at or opportunity.created_at
            return value.timestamp() if value else 0.0

        ranked.sort(key=lambda item: (item[0], sort_timestamp(item[1])), reverse=True)

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
            for _, opportunity in ranked[:limit]
        ]

    async def _analyze_matches(self, state: AgentState) -> AgentState:
        """Analyze job-resume match scores using LLM."""
        raw_jobs = state.get("raw_jobs", [])
        logger.info(f"Analyzing {len(raw_jobs)} jobs for match scores...")

        if state.get("error") or not raw_jobs:
            logger.warning("No jobs to analyze or error occurred")
            return {**state, "scored_jobs": []}

        resume = state["resume_text"]
        profile_text = state.get("preferences", {}).get("profile_text", "")

        results = await asyncio.gather(
            *(self._score_job(resume, profile_text, job) for job in raw_jobs),
            return_exceptions=True,
        )

        scored_jobs = []
        for job, score_data in zip(raw_jobs, results):
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

        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return {**state, "scored_jobs": scored_jobs}

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
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
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

        # If we have enough matches, generate content
        if len(matched) >= settings.TARGET_JOBS:
            return "generate"

        # If no scored jobs at all, just proceed with what we have
        if not scored_jobs:
            return "generate"

        # Check if we can still lower threshold (threshold was already lowered in filter_and_adjust)
        # If threshold hasn't changed from MIN, we've hit the bottom
        if threshold <= settings.MIN_THRESHOLD:
            return "generate"

        # Otherwise retry with the new (already lowered) threshold
        return "retry"

    async def _generate_content(self, state: AgentState) -> AgentState:
        """Generate cover letters for matched jobs."""
        matched = state.get("matched_jobs", [])[:settings.TARGET_JOBS]
        resume = state["resume_text"]

        results = await asyncio.gather(
            *(self._generate_cover_letter(resume, job) for job in matched),
            return_exceptions=True,
        )
        for job, result in zip(matched, results):
            if isinstance(result, Exception):
                logger.error("Error generating cover letter: %s", result)
                job["cover_letter"] = ""
            else:
                job["cover_letter"] = result

        return {**state, "matched_jobs": matched}

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
            }
        except Exception as e:
            logger.error(f"Agent workflow error: {e}")
            return {"success": False, "error": str(e)}
