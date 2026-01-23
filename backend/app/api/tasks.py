from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import pytz

from app.core.database import get_db
from app.core.config import settings
from app.models.models import DailyTask, Job

router = APIRouter()

eastern = pytz.timezone(settings.TIMEZONE)


class TaskJobInfo(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str]
    url: Optional[str]
    match_score: int

    class Config:
        from_attributes = True


class DailyTaskResponse(BaseModel):
    id: str
    job: TaskJobInfo
    is_completed: bool
    completed_at: Optional[str]
    task_order: int

    class Config:
        from_attributes = True


class DailyTasksListResponse(BaseModel):
    tasks: List[DailyTaskResponse]
    total: int
    completed: int
    date: str
    all_completed: bool


class TaskStatsResponse(BaseModel):
    today_total: int
    today_completed: int
    today_remaining: int
    completion_rate: float
    all_completed: bool
    streak_days: int  # Consecutive days with all tasks completed


@router.get("", response_model=DailyTasksListResponse)
async def get_daily_tasks(db: AsyncSession = Depends(get_db)):
    """Get today's daily tasks."""
    today = datetime.now(eastern).date()

    # Get today's tasks with job info
    query = (
        select(DailyTask)
        .join(Job)
        .where(func.date(DailyTask.date) == today)
        .order_by(DailyTask.task_order)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    # Build response
    task_responses = []
    completed_count = 0

    for task in tasks:
        if task.is_completed:
            completed_count += 1

        task_responses.append(DailyTaskResponse(
            id=task.id,
            job=TaskJobInfo(
                id=task.job.id,
                title=task.job.title,
                company=task.job.company,
                location=task.job.location,
                url=task.job.url,
                match_score=task.job.match_score
            ),
            is_completed=task.is_completed,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            task_order=task.task_order
        ))

    total = len(task_responses)
    all_done = completed_count == total and total > 0

    return DailyTasksListResponse(
        tasks=task_responses,
        total=total,
        completed=completed_count,
        date=today.isoformat(),
        all_completed=all_done
    )


@router.put("/{task_id}/complete")
async def complete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Mark a daily task as completed."""
    result = await db.execute(select(DailyTask).where(DailyTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_completed = True
    task.completed_at = datetime.now(eastern)

    # Also mark the job as applied
    task.job.is_applied = True
    task.job.applied_at = datetime.now(eastern)

    await db.commit()

    # Check if all tasks are completed
    today = datetime.now(eastern).date()
    all_tasks = await db.execute(
        select(DailyTask).where(func.date(DailyTask.date) == today)
    )
    tasks = all_tasks.scalars().all()
    all_completed = all(t.is_completed for t in tasks)

    return {
        "message": "Task completed!",
        "task_id": task_id,
        "all_completed": all_completed,
        "celebration_message": "🎉 今日任务已完成！Great job!" if all_completed else None
    }


@router.put("/{task_id}/uncomplete")
async def uncomplete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Unmark a daily task as completed."""
    result = await db.execute(select(DailyTask).where(DailyTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_completed = False
    task.completed_at = None
    task.job.is_applied = False
    task.job.applied_at = None

    await db.commit()

    return {"message": "Task marked as incomplete", "task_id": task_id}


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(db: AsyncSession = Depends(get_db)):
    """Get task completion statistics."""
    today = datetime.now(eastern).date()

    # Today's stats
    today_query = select(DailyTask).where(func.date(DailyTask.date) == today)
    today_result = await db.execute(today_query)
    today_tasks = today_result.scalars().all()

    total = len(today_tasks)
    completed = sum(1 for t in today_tasks if t.is_completed)
    rate = (completed / total * 100) if total > 0 else 0
    all_done = completed == total and total > 0

    # Calculate streak (simplified - just check if today is done)
    streak = 1 if all_done else 0

    return TaskStatsResponse(
        today_total=total,
        today_completed=completed,
        today_remaining=total - completed,
        completion_rate=round(rate, 1),
        all_completed=all_done,
        streak_days=streak
    )
