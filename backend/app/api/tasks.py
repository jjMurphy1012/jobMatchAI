import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.enums import ApplicationStatus
from app.models.models import Application, DailyTask, User, UserJobMatch

router = APIRouter()

eastern = pytz.timezone(settings.TIMEZONE)


class TaskJobInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    location: Optional[str]
    url: Optional[str]
    match_score: int

class DailyTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job: TaskJobInfo
    is_completed: bool
    completed_at: Optional[str]
    task_order: int

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
    streak_days: int


def _build_task_response(task: DailyTask) -> DailyTaskResponse:
    user_match = task.user_job_match
    opportunity = user_match.opportunity
    return DailyTaskResponse(
        id=task.id,
        job=TaskJobInfo(
            id=user_match.id,
            title=opportunity.title,
            company=opportunity.company,
            location=opportunity.location,
            url=opportunity.url,
            match_score=user_match.match_score,
        ),
        is_completed=task.is_completed,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        task_order=task.task_order,
    )


async def _load_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
) -> Optional[DailyTask]:
    result = await db.execute(
        select(DailyTask)
        .join(DailyTask.user_job_match)
        .options(
            selectinload(DailyTask.user_job_match).selectinload(UserJobMatch.opportunity),
            selectinload(DailyTask.user_job_match).selectinload(UserJobMatch.application),
        )
        .where(DailyTask.id == task_id, UserJobMatch.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _set_application_status(
    db: AsyncSession,
    task: DailyTask,
    user_id: str,
    status: str,
    applied_at: Optional[datetime],
) -> None:
    user_match = task.user_job_match
    application = user_match.application
    now = datetime.now(timezone.utc)

    if application is None:
        db.add(
            Application(
                user_id=user_id,
                opportunity_id=user_match.opportunity_id,
                user_job_match_id=user_match.id,
                status=status,
                applied_at=applied_at,
                status_updated_at=now,
            )
        )
        return

    application.status = status
    application.applied_at = applied_at
    application.status_updated_at = now


@router.get("", response_model=DailyTasksListResponse)
async def get_daily_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's daily tasks."""
    today = datetime.now(eastern).date()

    query = (
        select(DailyTask)
        .join(DailyTask.user_job_match)
        .options(
            selectinload(DailyTask.user_job_match).selectinload(UserJobMatch.opportunity),
            selectinload(DailyTask.user_job_match).selectinload(UserJobMatch.application),
        )
        .where(func.date(DailyTask.date) == today, UserJobMatch.user_id == current_user.id)
        .order_by(DailyTask.task_order)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    task_responses = [_build_task_response(task) for task in tasks]
    completed_count = sum(1 for task in tasks if task.is_completed)
    total = len(task_responses)
    all_done = completed_count == total and total > 0

    return DailyTasksListResponse(
        tasks=task_responses,
        total=total,
        completed=completed_count,
        date=today.isoformat(),
        all_completed=all_done,
    )


@router.put("/{task_id}/complete")
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a daily task as completed."""
    task = await _load_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.now(timezone.utc)
    task.is_completed = True
    task.completed_at = now
    await _set_application_status(db, task, current_user.id, ApplicationStatus.APPLIED, now)
    await db.commit()

    today = datetime.now(eastern).date()
    incomplete_result = await db.execute(
        select(func.count())
        .select_from(DailyTask)
        .join(DailyTask.user_job_match)
        .where(
            func.date(DailyTask.date) == today,
            UserJobMatch.user_id == current_user.id,
            DailyTask.is_completed.is_(False),
        )
    )
    all_completed = (incomplete_result.scalar_one() or 0) == 0

    return {
        "message": "Task completed!",
        "task_id": task_id,
        "all_completed": all_completed,
        "celebration_message": "🎉 今日任务已完成！Great job!" if all_completed else None,
    }


@router.put("/{task_id}/uncomplete")
async def uncomplete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unmark a daily task as completed."""
    task = await _load_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_completed = False
    task.completed_at = None
    await _set_application_status(db, task, current_user.id, ApplicationStatus.SAVED, None)
    await db.commit()

    return {"message": "Task marked as incomplete", "task_id": task_id}


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get task completion statistics."""
    today = datetime.now(eastern).date()
    today_filter = (func.date(DailyTask.date) == today, UserJobMatch.user_id == current_user.id)

    total_result, completed_result = await asyncio.gather(
        db.execute(
            select(func.count())
            .select_from(DailyTask)
            .join(DailyTask.user_job_match)
            .where(*today_filter)
        ),
        db.execute(
            select(func.count())
            .select_from(DailyTask)
            .join(DailyTask.user_job_match)
            .where(*today_filter, DailyTask.is_completed.is_(True))
        ),
    )
    total = total_result.scalar_one() or 0
    completed = completed_result.scalar_one() or 0
    rate = (completed / total * 100) if total > 0 else 0
    all_done = completed == total and total > 0
    streak = 1 if all_done else 0

    return TaskStatsResponse(
        today_total=total,
        today_completed=completed,
        today_remaining=total - completed,
        completion_rate=round(rate, 1),
        all_completed=all_done,
        streak_days=streak,
    )
