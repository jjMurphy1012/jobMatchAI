from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, List, Optional, Annotated
from operator import add
from sqlalchemy import select, func
from datetime import datetime, timezone
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

            effective_fields = PreferenceStructuredFields.model_validate(pref.effective_fields or {})
            keyword_text = ", ".join(effective_fields.keywords) or pref.keywords or ""
            location = effective_fields.locations[0] if effective_fields.locations else pref.location
            profile_text = pref.raw_text or pref.job_description or ""

            return {
                **state,
                "resume_text": resume.content or "",
                "preferences": {
                    "keywords": keyword_text,
                    "location": location,
                    "is_intern": effective_fields.is_intern if pref.effective_fields else pref.is_intern,
                    "need_sponsor": effective_fields.need_sponsor if pref.effective_fields else pref.need_sponsor,
                    "job_description": profile_text,
                    "profile_text": profile_text,
                    "remote_preference": effective_fields.remote_preference if pref.effective_fields else pref.remote_preference,
                },
                "threshold": settings.MATCH_THRESHOLD
            }

    async def _search_jobs(self, state: AgentState) -> AgentState:
        """Search for jobs using LinkedIn API."""
        if state.get("error"):
            return state

        prefs = state["preferences"]
        logger.info(f"Searching jobs with keywords: {prefs['keywords']}, location: {prefs.get('location')}, is_intern: {prefs.get('is_intern')}")

        jobs = await self.linkedin_service.search_jobs(
            keywords=prefs["keywords"],
            location=prefs.get("location"),
            limit=20,
            is_intern=prefs.get("is_intern", False)
        )

        logger.info(f"LinkedIn returned {len(jobs)} jobs")
        return {**state, "raw_jobs": jobs}

    async def _analyze_matches(self, state: AgentState) -> AgentState:
        """Analyze job-resume match scores using LLM."""
        raw_jobs = state.get("raw_jobs", [])
        logger.info(f"Analyzing {len(raw_jobs)} jobs for match scores...")

        if state.get("error") or not raw_jobs:
            logger.warning("No jobs to analyze or error occurred")
            return {**state, "scored_jobs": []}

        resume = state["resume_text"]
        profile_text = state.get("preferences", {}).get("profile_text", "")
        scored_jobs = []

        for job in state["raw_jobs"]:
            try:
                score_data = await self._score_job(resume, profile_text, job)
                scored_jobs.append({
                    **job,
                    "match_score": score_data.get("score", 0),
                    "match_reason": score_data.get("reason", ""),
                    "matched_skills": json.dumps(score_data.get("matched_skills", [])),
                    "missing_skills": json.dumps(score_data.get("missing_skills", []))
                })
            except Exception as e:
                logger.error(f"Error scoring job {job.get('title')}: {e}")
                continue

        # Sort by score
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

        for job in matched:
            try:
                cover_letter = await self._generate_cover_letter(resume, job)
                job["cover_letter"] = cover_letter
            except Exception as e:
                logger.error(f"Error generating cover letter: {e}")
                job["cover_letter"] = ""

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
            for i, job_data in enumerate(matched):
                source_type = job_data.get("source_type") or "legacy"
                source_job_id = str(
                    job_data.get("source_job_id")
                    or job_data.get("linkedin_job_id")
                    or job_data.get("url")
                    or f"generated-{i}"
                )

                opportunity_result = await db.execute(
                    select(Opportunity).where(
                        Opportunity.source_type == source_type,
                        Opportunity.source_job_id == source_job_id,
                    )
                )
                opportunity = opportunity_result.scalar_one_or_none()

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
                    await db.flush()
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

                match_result = await db.execute(
                    select(UserJobMatch).where(
                        UserJobMatch.user_id == self.user_id,
                        UserJobMatch.opportunity_id == opportunity.id,
                    )
                )
                user_match = match_result.scalar_one_or_none()

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
                    await db.flush()
                else:
                    user_match.match_score = job_data["match_score"]
                    user_match.match_reason = job_data.get("match_reason")
                    user_match.matched_skills = job_data.get("matched_skills")
                    user_match.missing_skills = job_data.get("missing_skills")
                    user_match.cover_letter = job_data.get("cover_letter")
                    user_match.last_scored_at = now

                current_match_ids.add(user_match.id)

                existing_task_result = await db.execute(
                    select(DailyTask).where(
                        DailyTask.user_job_match_id == user_match.id,
                        func.date(DailyTask.date) == today,
                    )
                )
                existing_task = existing_task_result.scalar_one_or_none()

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
                        DailyTask.user_job_match_id.is_not(None),
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
            return {
                "success": True,
                "jobs_found": len(final_state.get("matched_jobs", [])),
                "final_threshold": final_state.get("threshold")
            }
        except Exception as e:
            logger.error(f"Agent workflow error: {e}")
            return {"success": False, "error": str(e)}
