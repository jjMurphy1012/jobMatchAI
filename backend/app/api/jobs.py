from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Job, JobPreference, Resume, User
from app.services.agent_service import JobMatchingAgent

router = APIRouter()
logger = logging.getLogger(__name__)


class JobResponse(BaseModel):
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

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    last_search: Optional[str]


class JobRefreshResponse(BaseModel):
    message: str
    status: str
    jobs_found: int = 0
    final_threshold: Optional[int] = None


@router.get("", response_model=JobListResponse)
async def get_matched_jobs(
    skip: int = 0,
    limit: int = 10,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get matched job recommendations."""
    filters = (Job.user_id == current_user.id, Job.match_score >= min_score)

    list_query = (
        select(Job)
        .where(*filters)
        .order_by(Job.match_score.desc(), Job.searched_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_query = select(func.count()).select_from(Job).where(*filters)
    last_query = (
        select(Job.searched_at)
        .where(Job.user_id == current_user.id)
        .order_by(Job.searched_at.desc())
        .limit(1)
    )

    list_result = await db.execute(list_query)
    count_result = await db.execute(count_query)
    last_result = await db.execute(last_query)

    jobs = list_result.scalars().all()
    total = count_result.scalar_one()
    last_search_dt = last_result.scalar_one_or_none()
    last_search = last_search_dt.isoformat() if last_search_dt else None

    return JobListResponse(
        jobs=[
            JobResponse(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                salary=job.salary,
                url=job.url,
                match_score=job.match_score,
                match_reason=job.match_reason,
                matched_skills=job.matched_skills,
                missing_skills=job.missing_skills,
                cover_letter=job.cover_letter,
                is_applied=job.is_applied,
                searched_at=job.searched_at.isoformat()
            )
            for job in jobs
        ],
        total=total,
        last_search=last_search
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific job's details."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary,
        url=job.url,
        match_score=job.match_score,
        match_reason=job.match_reason,
        matched_skills=job.matched_skills,
        missing_skills=job.missing_skills,
        cover_letter=job.cover_letter,
        is_applied=job.is_applied,
        searched_at=job.searched_at.isoformat()
    )


@router.post("/refresh", response_model=JobRefreshResponse)
async def refresh_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a job search synchronously for the current user."""
    # Check if resume exists
    resume_result = await db.execute(select(Resume).where(Resume.user_id == current_user.id).limit(1))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=400, detail="Please upload a resume first")

    # Check if preferences exist
    pref_result = await db.execute(select(JobPreference).where(JobPreference.user_id == current_user.id).limit(1))
    preferences = pref_result.scalar_one_or_none()
    if not preferences:
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
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_applied = True
    job.applied_at = datetime.utcnow()
    await db.commit()

    return {"message": "Job marked as applied", "job_id": job_id}
