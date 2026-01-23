from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Job, JobPreference, Resume
from app.services.agent_service import JobMatchingAgent

router = APIRouter()


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


@router.get("", response_model=JobListResponse)
async def get_matched_jobs(
    skip: int = 0,
    limit: int = 10,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get matched job recommendations."""
    query = select(Job).where(Job.match_score >= min_score).order_by(
        Job.match_score.desc(),
        Job.searched_at.desc()
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Get total count
    count_query = select(Job).where(Job.match_score >= min_score)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # Get last search time
    last_job = await db.execute(
        select(Job).order_by(Job.searched_at.desc()).limit(1)
    )
    last = last_job.scalar_one_or_none()
    last_search = last.searched_at.isoformat() if last else None

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
async def get_job_detail(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific job's details."""
    result = await db.execute(select(Job).where(Job.id == job_id))
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


@router.post("/refresh")
async def refresh_jobs(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a job search."""
    # Check if resume exists
    resume_result = await db.execute(select(Resume).limit(1))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=400, detail="Please upload a resume first")

    # Check if preferences exist
    pref_result = await db.execute(select(JobPreference).limit(1))
    preferences = pref_result.scalar_one_or_none()
    if not preferences:
        raise HTTPException(status_code=400, detail="Please set job preferences first")

    # Run job search in background
    background_tasks.add_task(run_job_search)

    return {"message": "Job search started", "status": "processing"}


async def run_job_search():
    """Background task to run the job matching agent."""
    try:
        agent = JobMatchingAgent()
        await agent.run()
    except Exception as e:
        print(f"Job search error: {e}")


@router.put("/{job_id}/apply")
async def mark_job_applied(job_id: str, db: AsyncSession = Depends(get_db)):
    """Mark a job as applied."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_applied = True
    job.applied_at = datetime.utcnow()
    await db.commit()

    return {"message": "Job marked as applied", "job_id": job_id}
