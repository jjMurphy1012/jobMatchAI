from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import CurrentUserResponse
from app.api.deps import require_admin
from app.core.database import get_db
from app.core.enums import REVIEW_STATUSES, SOURCE_TYPES, SourceType, ReviewStatus, USER_ROLES, UserRole
from app.core.text import normalize_company
from app.models.models import CompanySource, InterviewExperience, SourceSyncRun, User
from app.services.source_sync_service import CompanySourceSyncService

router = APIRouter()
source_sync_service = CompanySourceSyncService()


class AdminUserResponse(CurrentUserResponse):
    created_at: datetime | None
    last_login_at: datetime | None


class UpdateRoleRequest(BaseModel):
    role: str


class CompanySourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str
    company_name: str
    board_token: str
    is_active: bool
    last_synced_at: Optional[datetime]
    created_by_user_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CompanySourceUpsertRequest(BaseModel):
    source_type: str = Field(default=SourceType.GREENHOUSE)
    company_name: str = Field(min_length=2, max_length=200)
    board_token: str = Field(min_length=2, max_length=200)
    is_active: bool = True


class SourceSyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_source_id: str
    source_type: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    fetched_count: int
    upserted_count: int
    closed_count: int
    error_message: Optional[str]
    company_name: Optional[str] = None
    board_token: Optional[str] = None


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


def _validate_source_type(source_type: str) -> str:
    normalized = source_type.strip().lower()
    if normalized not in SOURCE_TYPES:
        raise HTTPException(status_code=400, detail="source_type must be 'greenhouse'.")
    return normalized


def _apply_source_payload(
    source: CompanySource,
    payload: CompanySourceUpsertRequest,
    source_type: str,
) -> None:
    source.source_type = source_type
    source.company_name = payload.company_name.strip()
    source.board_token = payload.board_token.strip()
    source.is_active = payload.is_active


async def _ensure_source_unique(
    db: AsyncSession,
    source_type: str,
    board_token: str,
    current_id: str | None = None,
) -> None:
    result = await db.execute(
        select(CompanySource).where(
            CompanySource.source_type == source_type,
            CompanySource.board_token == board_token,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.id != current_id:
        raise HTTPException(status_code=400, detail="This company source already exists.")


def _build_sync_run_response(run: SourceSyncRun, source: CompanySource | None = None) -> SourceSyncRunResponse:
    response = SourceSyncRunResponse.model_validate(run)
    source_obj = source or run.company_source
    if source_obj is not None:
        response.company_name = source_obj.company_name
        response.board_token = source_obj.board_token
    return response


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


@router.get("/company-sources", response_model=list[CompanySourceResponse])
async def list_company_sources(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(CompanySource).order_by(CompanySource.is_active.desc(), CompanySource.company_name.asc())
    )
    return [CompanySourceResponse.model_validate(source) for source in result.scalars().all()]


@router.post(
    "/company-sources",
    response_model=CompanySourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_source(
    payload: CompanySourceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    source_type = _validate_source_type(payload.source_type)
    board_token = payload.board_token.strip()
    await _ensure_source_unique(db, source_type, board_token)

    source = CompanySource(id=str(uuid4()), created_by_user_id=current_admin.id)
    _apply_source_payload(source, payload, source_type)
    db.add(source)
    await db.flush()
    return CompanySourceResponse.model_validate(source)


@router.patch("/company-sources/{source_id}", response_model=CompanySourceResponse)
async def update_company_source(
    source_id: str,
    payload: CompanySourceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(CompanySource).where(CompanySource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Company source not found.")

    source_type = _validate_source_type(payload.source_type)
    board_token = payload.board_token.strip()
    await _ensure_source_unique(db, source_type, board_token, current_id=source.id)
    _apply_source_payload(source, payload, source_type)
    await db.flush()
    return CompanySourceResponse.model_validate(source)


@router.patch(
    "/company-sources/{source_id}/deactivate",
    response_model=CompanySourceResponse,
)
async def deactivate_company_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(CompanySource).where(CompanySource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Company source not found.")

    source.is_active = False
    await db.flush()
    return CompanySourceResponse.model_validate(source)


@router.post("/company-sources/{source_id}/sync", response_model=SourceSyncRunResponse)
async def sync_company_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(CompanySource).where(CompanySource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Company source not found.")

    run = await source_sync_service.sync_company_source(db, source)
    return _build_sync_run_response(run, source)


@router.get("/source-sync-runs", response_model=list[SourceSyncRunResponse])
async def list_source_sync_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    capped_limit = min(max(limit, 1), 100)
    result = await db.execute(
        select(SourceSyncRun)
        .options(selectinload(SourceSyncRun.company_source))
        .order_by(SourceSyncRun.started_at.desc())
        .limit(capped_limit)
    )
    return [_build_sync_run_response(run) for run in result.scalars().all()]


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
