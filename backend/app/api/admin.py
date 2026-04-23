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
from app.models.models import InterviewExperience, User

router = APIRouter()


def _normalize_company(value: str) -> str:
    return " ".join(value.strip().lower().split())


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
    review_status: str = Field(default="draft")
    relevance_keywords: list[str] = Field(default_factory=list)


def _serialize_experience(experience: InterviewExperience) -> AdminInterviewExperienceResponse:
    return AdminInterviewExperienceResponse(
        id=experience.id,
        company_name=experience.company_name,
        company_name_normalized=experience.company_name_normalized,
        role=experience.role,
        level=experience.level,
        year=experience.year,
        rounds=experience.rounds,
        topics=list(experience.topics or []),
        summary=experience.summary,
        source_url=experience.source_url,
        source_site=experience.source_site,
        review_status=experience.review_status,
        relevance_keywords=list(experience.relevance_keywords or []),
        created_by_user_id=experience.created_by_user_id,
        reviewed_by_user_id=experience.reviewed_by_user_id,
        reviewed_at=experience.reviewed_at,
        created_at=experience.created_at,
        updated_at=experience.updated_at,
    )


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
    if payload.role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == current_admin.id and payload.role != "admin":
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
    return [_serialize_experience(experience) for experience in result.scalars().all()]


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
    if payload.review_status not in {"draft", "published"}:
        raise HTTPException(status_code=400, detail="review_status must be 'draft' or 'published'.")

    now = datetime.now(timezone.utc)
    experience = InterviewExperience(
        id=str(uuid4()),
        company_name=payload.company_name.strip(),
        company_name_normalized=_normalize_company(payload.company_name),
        role=payload.role.strip(),
        level=payload.level.strip() if payload.level else None,
        year=payload.year,
        rounds=payload.rounds.strip() if payload.rounds else None,
        topics=[topic.strip() for topic in payload.topics if topic.strip()],
        summary=payload.summary.strip(),
        source_url=payload.source_url,
        source_site=payload.source_site.strip() if payload.source_site else None,
        review_status=payload.review_status,
        relevance_keywords=[keyword.strip() for keyword in payload.relevance_keywords if keyword.strip()],
        created_by_user_id=current_admin.id,
        reviewed_by_user_id=current_admin.id if payload.review_status == "published" else None,
        reviewed_at=now if payload.review_status == "published" else None,
    )
    db.add(experience)
    await db.flush()
    return _serialize_experience(experience)


@router.patch("/interview-experiences/{experience_id}", response_model=AdminInterviewExperienceResponse)
async def update_interview_experience(
    experience_id: str,
    payload: InterviewExperienceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.review_status not in {"draft", "published"}:
        raise HTTPException(status_code=400, detail="review_status must be 'draft' or 'published'.")

    result = await db.execute(select(InterviewExperience).where(InterviewExperience.id == experience_id))
    experience = result.scalar_one_or_none()
    if not experience:
        raise HTTPException(status_code=404, detail="Interview experience not found.")

    experience.company_name = payload.company_name.strip()
    experience.company_name_normalized = _normalize_company(payload.company_name)
    experience.role = payload.role.strip()
    experience.level = payload.level.strip() if payload.level else None
    experience.year = payload.year
    experience.rounds = payload.rounds.strip() if payload.rounds else None
    experience.topics = [topic.strip() for topic in payload.topics if topic.strip()]
    experience.summary = payload.summary.strip()
    experience.source_url = payload.source_url
    experience.source_site = payload.source_site.strip() if payload.source_site else None
    experience.review_status = payload.review_status
    experience.relevance_keywords = [keyword.strip() for keyword in payload.relevance_keywords if keyword.strip()]
    experience.reviewed_by_user_id = current_admin.id if payload.review_status == "published" else None
    experience.reviewed_at = datetime.now(timezone.utc) if payload.review_status == "published" else None
    await db.flush()
    return _serialize_experience(experience)


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
