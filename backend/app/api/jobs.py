import asyncio
from datetime import datetime, timezone
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.enums import APPLIED_STATUSES, ApplicationStatus
from app.models.models import Application, JobPreference, Resume, User, UserJobMatch
from app.services.agent_service import JobMatchingAgent

router = APIRouter()
logger = logging.getLogger(__name__)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
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

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    last_search: Optional[str]


class JobRefreshResponse(BaseModel):
    message: str
    status: str
    jobs_found: int = 0
    final_threshold: Optional[int] = None


def _build_job_response(user_match: UserJobMatch) -> JobResponse:
    opportunity = user_match.opportunity
    application = user_match.application
    searched_at = user_match.last_scored_at or user_match.created_at

    return JobResponse(
        id=user_match.id,
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

    return _build_job_response(user_match)


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
    )


async def run_job_search(user_id: str):
    """Run the job matching agent and return its result."""
    try:
        agent = JobMatchingAgent(user_id=user_id)
        return await agent.run()
    except Exception as e:
        logger.exception("Job search error for user %s", user_id)
        return {"success": False, "error": str(e)}


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
