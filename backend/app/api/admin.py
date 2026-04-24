from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUserResponse
from app.api.deps import require_admin
from app.core.database import get_db
from app.core.enums import REVIEW_STATUSES, ReviewStatus, USER_ROLES, UserRole
from app.core.text import normalize_company
from app.models.models import InterviewExperience, User

router = APIRouter()


class AdminUserResponse(CurrentUserResponse):
    created_at: datetime | None
    last_login_at: datetime | None


class UpdateRoleRequest(BaseModel):
    role: str


class AdminInterviewExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    company_name_normalized: str
    role: str
    level: Optional[str]
    year: Optional[int]
    rounds: Optional[str]
    topics: list[str]
    summary: str
    source_url: Optional[str]
    source_site: Optional[str]
    review_status: str
    relevance_keywords: list[str]
    created_by_user_id: Optional[str]
    reviewed_by_user_id: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class InterviewExperienceUpsertRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    role: str = Field(min_length=2, max_length=200)
    level: Optional[str] = Field(default=None, max_length=100)
    year: Optional[int] = None
    rounds: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=20)
    source_url: Optional[str] = None
    source_site: Optional[str] = Field(default=None, max_length=120)
    review_status: str = Field(default=ReviewStatus.DRAFT)
    relevance_keywords: list[str] = Field(default_factory=list)


def _apply_experience_payload(
    experience: InterviewExperience,
    payload: InterviewExperienceUpsertRequest,
    admin: User,
) -> None:
    """Populate InterviewExperience columns from an upsert payload. Shared by create + update."""
    experience.company_name = payload.company_name.strip()
    experience.company_name_normalized = normalize_company(payload.company_name)
    experience.role = payload.role.strip()
    experience.level = payload.level.strip() if payload.level else None
    experience.year = payload.year
    experience.rounds = payload.rounds.strip() if payload.rounds else None
    experience.topics = [topic.strip() for topic in payload.topics if topic.strip()]
    experience.summary = payload.summary.strip()
    experience.source_url = payload.source_url
    experience.source_site = payload.source_site.strip() if payload.source_site else None
    experience.review_status = payload.review_status
    experience.relevance_keywords = [kw.strip() for kw in payload.relevance_keywords if kw.strip()]
    is_published = payload.review_status == ReviewStatus.PUBLISHED
    experience.reviewed_by_user_id = admin.id if is_published else None
    experience.reviewed_at = datetime.now(timezone.utc) if is_published else None


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [AdminUserResponse.model_validate(user) for user in result.scalars().all()]


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.role not in USER_ROLES:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == current_admin.id and payload.role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role.")

    user.role = payload.role
    await db.flush()
    return AdminUserResponse.model_validate(user)


@router.get("/interview-experiences", response_model=list[AdminInterviewExperienceResponse])
async def list_interview_experiences(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(InterviewExperience)
        .order_by(InterviewExperience.updated_at.desc(), InterviewExperience.created_at.desc())
    )
    return [
        AdminInterviewExperienceResponse.model_validate(experience)
        for experience in result.scalars().all()
    ]


@router.post(
    "/interview-experiences",
    response_model=AdminInterviewExperienceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interview_experience(
    payload: InterviewExperienceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.review_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="review_status must be 'draft' or 'published'.")

    experience = InterviewExperience(id=str(uuid4()), created_by_user_id=current_admin.id)
    _apply_experience_payload(experience, payload, current_admin)
    db.add(experience)
    await db.flush()
    return AdminInterviewExperienceResponse.model_validate(experience)


@router.patch("/interview-experiences/{experience_id}", response_model=AdminInterviewExperienceResponse)
async def update_interview_experience(
    experience_id: str,
    payload: InterviewExperienceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.review_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="review_status must be 'draft' or 'published'.")

    result = await db.execute(select(InterviewExperience).where(InterviewExperience.id == experience_id))
    experience = result.scalar_one_or_none()
    if not experience:
        raise HTTPException(status_code=404, detail="Interview experience not found.")

    _apply_experience_payload(experience, payload, current_admin)
    await db.flush()
    return AdminInterviewExperienceResponse.model_validate(experience)


@router.delete("/interview-experiences/{experience_id}")
async def delete_interview_experience(
    experience_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(InterviewExperience).where(InterviewExperience.id == experience_id))
    experience = result.scalar_one_or_none()
    if not experience:
        raise HTTPException(status_code=404, detail="Interview experience not found.")

    await db.delete(experience)
    await db.flush()
    return {"message": "Interview experience deleted."}
