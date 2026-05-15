import asyncio
from datetime import datetime, timezone
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.enums import APPLIED_STATUSES, ApplicationStatus, ReviewStatus
from app.core.text import normalize_company
from app.models.models import Application, InterviewExperience, JobPreference, Opportunity, Resume, User, UserJobMatch
from app.services.agent_service import JobMatchingAgent

router = APIRouter()
logger = logging.getLogger(__name__)


class RelatedInterviewExperienceResponse(BaseModel):
    id: str
    company_name: str
    role: str
    level: Optional[str]
    year: Optional[int]
    topics: list[str]
    summary: str
    source_url: Optional[str]
    source_site: Optional[str]
    relevance_score: int


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: Optional[str] = None
    source_job_id: Optional[str] = None
    title: str
    company: str
    location: Optional[str]
    salary: Optional[str]
    url: Optional[str]
    match_score: int
    match_reason: Optional[str]
    matched_skills: Optional[str]
    missing_skills: Optional[str]
    cover_letter: Optional[str]
    is_applied: bool
    searched_at: str
    application_status: Optional[str] = None
    related_interviews: list[RelatedInterviewExperienceResponse] = Field(default_factory=list)

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    last_search: Optional[str]


class JobRefreshResponse(BaseModel):
    message: str
    status: str
    jobs_found: int = 0
    final_threshold: Optional[int] = None
    used_synced_opportunities: bool = False
    source_counts: dict[str, int] = Field(default_factory=dict)
    candidate_stats: dict[str, int | str | bool] = Field(default_factory=dict)


class CoverLetterResponse(BaseModel):
    job_id: str
    cover_letter: str


def _tokenize_text(*parts: object) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        if isinstance(part, list):
            for item in part:
                tokens.update(_tokenize_text(item))
            continue
        if not part:
            continue
        for raw in str(part).replace("/", " ").replace(",", " ").replace("-", " ").split():
            token = raw.strip().lower()
            if len(token) >= 2:
                tokens.add(token)
    return tokens


def _build_related_interview_response(
    experience: InterviewExperience,
    relevance_score: int,
) -> RelatedInterviewExperienceResponse:
    return RelatedInterviewExperienceResponse(
        id=experience.id,
        company_name=experience.company_name,
        role=experience.role,
        level=experience.level,
        year=experience.year,
        topics=list(experience.topics or []),
        summary=experience.summary,
        source_url=experience.source_url,
        source_site=experience.source_site,
        relevance_score=relevance_score,
    )


def _sort_timestamp(value: datetime | None) -> float:
    return value.timestamp() if value else 0.0


async def _load_related_interviews(
    db: AsyncSession,
    opportunity: Opportunity,
    limit: int = 3,
) -> list[RelatedInterviewExperienceResponse]:
    result = await db.execute(
        select(InterviewExperience)
        .where(InterviewExperience.review_status == ReviewStatus.PUBLISHED)
        .order_by(InterviewExperience.updated_at.desc(), InterviewExperience.created_at.desc())
        .limit(100)
    )
    experiences = result.scalars().all()
    company_normalized = normalize_company(opportunity.company)
    title_tokens = _tokenize_text(opportunity.title)

    ranked: list[tuple[int, InterviewExperience]] = []
    for experience in experiences:
        company_match = experience.company_name_normalized == company_normalized
        role_overlap = len(title_tokens & _tokenize_text(experience.role, experience.relevance_keywords or []))
        if not company_match and role_overlap == 0:
            continue
        score = (100 if company_match else 0) + role_overlap * 10
        ranked.append((score, experience))

    ranked.sort(
        key=lambda item: (
            item[0],
            _sort_timestamp(item[1].updated_at or item[1].created_at),
        ),
        reverse=True,
    )
    return [
        _build_related_interview_response(experience, score)
        for score, experience in ranked[:limit]
    ]


def _build_job_response(
    user_match: UserJobMatch,
    related_interviews: Optional[list[RelatedInterviewExperienceResponse]] = None,
) -> JobResponse:
    opportunity = user_match.opportunity
    application = user_match.application
    searched_at = user_match.last_scored_at or user_match.created_at

    return JobResponse(
        id=user_match.id,
        source_type=opportunity.source_type,
        source_job_id=opportunity.source_job_id,
        title=opportunity.title,
        company=opportunity.company,
        location=opportunity.location,
        salary=opportunity.salary,
        url=opportunity.url,
        match_score=user_match.match_score,
        match_reason=user_match.match_reason,
        matched_skills=user_match.matched_skills,
        missing_skills=user_match.missing_skills,
        cover_letter=user_match.cover_letter,
        is_applied=bool(application and application.status in APPLIED_STATUSES),
        searched_at=searched_at.isoformat() if searched_at else "",
        application_status=application.status if application else None,
        related_interviews=related_interviews or [],
    )


@router.get("", response_model=JobListResponse)
async def get_matched_jobs(
    skip: int = 0,
    limit: int = 10,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get matched job recommendations."""
    filters = (UserJobMatch.user_id == current_user.id, UserJobMatch.match_score >= min_score)

    list_query = (
        select(UserJobMatch)
        .options(
            selectinload(UserJobMatch.opportunity),
            selectinload(UserJobMatch.application),
        )
        .where(*filters)
        .order_by(UserJobMatch.match_score.desc(), UserJobMatch.last_scored_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_query = select(func.count()).select_from(UserJobMatch).where(*filters)
    last_query = (
        select(UserJobMatch.last_scored_at)
        .where(UserJobMatch.user_id == current_user.id)
        .order_by(UserJobMatch.last_scored_at.desc())
        .limit(1)
    )

    list_result, count_result, last_result = await asyncio.gather(
        db.execute(list_query),
        db.execute(count_query),
        db.execute(last_query),
    )

    jobs = list_result.scalars().all()
    total = count_result.scalar_one()
    last_search_dt = last_result.scalar_one_or_none()
    last_search = last_search_dt.isoformat() if last_search_dt else None

    return JobListResponse(
        jobs=[_build_job_response(job) for job in jobs],
        total=total,
        last_search=last_search,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific job's details."""
    result = await db.execute(
        select(UserJobMatch)
        .options(
            selectinload(UserJobMatch.opportunity),
            selectinload(UserJobMatch.application),
        )
        .where(UserJobMatch.id == job_id, UserJobMatch.user_id == current_user.id)
    )
    user_match = result.scalar_one_or_none()

    if not user_match:
        raise HTTPException(status_code=404, detail="Job not found")

    related_interviews = await _load_related_interviews(db, user_match.opportunity)
    return _build_job_response(user_match, related_interviews=related_interviews)


@router.post("/refresh", response_model=JobRefreshResponse)
async def refresh_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a job search synchronously for the current user."""
    resume_res, pref_res = await asyncio.gather(
        db.execute(select(Resume.id).where(Resume.user_id == current_user.id).limit(1)),
        db.execute(select(JobPreference.id).where(JobPreference.user_id == current_user.id).limit(1)),
    )
    if resume_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Please upload a resume first")
    if pref_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Please set job preferences first")

    result = await run_job_search(current_user.id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Job search failed"))

    return JobRefreshResponse(
        message=f"Job search completed with {result.get('jobs_found', 0)} matched jobs.",
        status="completed",
        jobs_found=result.get("jobs_found", 0),
        final_threshold=result.get("final_threshold"),
        used_synced_opportunities=result.get("used_synced_opportunities", False),
        source_counts=result.get("source_counts", {}),
        candidate_stats=result.get("candidate_stats", {}),
    )


async def run_job_search(user_id: str):
    """Run the job matching agent and return its result."""
    try:
        agent = JobMatchingAgent(user_id=user_id)
        return await agent.run()
    except Exception as e:
        logger.exception("Job search error for user %s", user_id)
        return {"success": False, "error": str(e)}


@router.post("/{job_id}/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and persist a cover letter for a matched job on demand."""
    match_result = await db.execute(
        select(UserJobMatch)
        .options(selectinload(UserJobMatch.opportunity))
        .where(UserJobMatch.id == job_id, UserJobMatch.user_id == current_user.id)
    )
    user_match = match_result.scalar_one_or_none()
    if not user_match:
        raise HTTPException(status_code=404, detail="Job not found")

    if user_match.cover_letter:
        return CoverLetterResponse(job_id=user_match.id, cover_letter=user_match.cover_letter)

    resume_result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .limit(1)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=400, detail="Please upload a resume first")

    agent = JobMatchingAgent(user_id=current_user.id)
    cover_letter = await agent.generate_cover_letter_for_job(resume.content or "", user_match)
    user_match.cover_letter = cover_letter
    await db.commit()

    return CoverLetterResponse(job_id=user_match.id, cover_letter=cover_letter)


@router.put("/{job_id}/apply")
async def mark_job_applied(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a job as applied."""
    result = await db.execute(
        select(UserJobMatch)
        .options(
            selectinload(UserJobMatch.opportunity),
            selectinload(UserJobMatch.application),
        )
        .where(UserJobMatch.id == job_id, UserJobMatch.user_id == current_user.id)
    )
    user_match = result.scalar_one_or_none()

    if not user_match:
        raise HTTPException(status_code=404, detail="Job not found")

    now = datetime.now(timezone.utc)
    if user_match.application is None:
        db.add(
            Application(
                user_id=current_user.id,
                opportunity_id=user_match.opportunity_id,
                user_job_match_id=user_match.id,
                status=ApplicationStatus.APPLIED,
                applied_at=now,
                status_updated_at=now,
            )
        )
    else:
        user_match.application.status = ApplicationStatus.APPLIED
        user_match.application.applied_at = now
        user_match.application.status_updated_at = now

    await db.commit()

    return {"message": "Job marked as applied", "job_id": job_id}
