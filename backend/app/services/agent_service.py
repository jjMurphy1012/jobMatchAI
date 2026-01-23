from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, List, Optional, Annotated
from operator import add
from sqlalchemy import select
from datetime import datetime
import json
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.models import Resume, JobPreference, Job, DailyTask
from app.services.linkedin_service import LinkedInService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


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

    def __init__(self):
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
                select(Resume).order_by(Resume.uploaded_at.desc()).limit(1)
            )
            resume = resume_result.scalar_one_or_none()

            # Get preferences
            pref_result = await db.execute(
                select(JobPreference).order_by(JobPreference.created_at.desc()).limit(1)
            )
            pref = pref_result.scalar_one_or_none()

            if not resume or not pref:
                return {**state, "error": "Missing resume or preferences"}

            return {
                **state,
                "resume_text": resume.content or "",
                "preferences": {
                    "keywords": pref.keywords,
                    "location": pref.location,
                    "is_intern": pref.is_intern,
                    "need_sponsor": pref.need_sponsor,
                    "job_description": pref.job_description
                },
                "threshold": settings.MATCH_THRESHOLD
            }

    async def _search_jobs(self, state: AgentState) -> AgentState:
        """Search for jobs using LinkedIn API."""
        if state.get("error"):
            return state

        prefs = state["preferences"]
        jobs = await self.linkedin_service.search_jobs(
            keywords=prefs["keywords"],
            location=prefs.get("location"),
            limit=20,
            is_intern=prefs.get("is_intern", False)
        )

        return {**state, "raw_jobs": jobs}

    async def _analyze_matches(self, state: AgentState) -> AgentState:
        """Analyze job-resume match scores using LLM."""
        if state.get("error") or not state.get("raw_jobs"):
            return {**state, "scored_jobs": []}

        resume = state["resume_text"]
        scored_jobs = []

        for job in state["raw_jobs"]:
            try:
                score_data = await self._score_job(resume, job)
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

    async def _score_job(self, resume: str, job: dict) -> dict:
        """Score a single job against the resume."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a career advisor analyzing job-resume fit. Be objective and precise."),
            ("human", """
Analyze the match between this resume and job posting.

RESUME:
{resume}

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
        """Filter jobs by threshold and adjust if needed."""
        threshold = state["threshold"]
        scored_jobs = state.get("scored_jobs", [])

        matched = [j for j in scored_jobs if j["match_score"] >= threshold]

        return {
            **state,
            "matched_jobs": matched,
            "threshold": threshold
        }

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue, retry with lower threshold, or end."""
        matched = state.get("matched_jobs", [])
        threshold = state["threshold"]

        if len(matched) >= settings.TARGET_JOBS:
            return "generate"
        elif threshold > settings.MIN_THRESHOLD:
            # Lower threshold and retry
            state["threshold"] = threshold - settings.THRESHOLD_STEP
            return "retry"
        else:
            # Can't lower threshold anymore, proceed with what we have
            return "generate"

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

        async with async_session_maker() as db:
            for i, job_data in enumerate(matched):
                # Check if job already exists
                existing = await db.execute(
                    select(Job).where(Job.linkedin_job_id == job_data.get("linkedin_job_id"))
                )
                if existing.scalar_one_or_none():
                    continue

                # Create job record
                job = Job(
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data.get("location"),
                    salary=job_data.get("salary"),
                    url=job_data.get("url"),
                    description=job_data.get("description"),
                    match_score=job_data["match_score"],
                    match_reason=job_data.get("match_reason"),
                    matched_skills=job_data.get("matched_skills"),
                    missing_skills=job_data.get("missing_skills"),
                    cover_letter=job_data.get("cover_letter"),
                    linkedin_job_id=job_data.get("linkedin_job_id")
                )
                db.add(job)
                await db.flush()

                # Create daily task
                task = DailyTask(
                    job_id=job.id,
                    task_order=i
                )
                db.add(task)

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

        try:
            final_state = await workflow.ainvoke(initial_state)
            return {
                "success": True,
                "jobs_found": len(final_state.get("matched_jobs", [])),
                "final_threshold": final_state.get("threshold")
            }
        except Exception as e:
            logger.error(f"Agent workflow error: {e}")
            return {"success": False, "error": str(e)}
