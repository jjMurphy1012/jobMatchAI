from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import JobPreference, User
from app.services.preference_extractor import (
    EXTRACTION_VERSION,
    PreferenceAnalysisResult,
    PreferenceExtractorService,
    PreferenceFieldOverrides,
    PreferenceStructuredFields,
)

router = APIRouter()

extractor_service = PreferenceExtractorService()


class PreferenceAnalyzeRequest(BaseModel):
    raw_text: str = Field(min_length=10)


class PreferenceAnalyzeResponse(BaseModel):
    raw_text: str
    extracted_fields: PreferenceStructuredFields
    effective_fields: PreferenceStructuredFields
    extraction_version: str
    extracted_at: str
    used_fallback: bool


class PreferenceUpsertRequest(BaseModel):
    raw_text: str = Field(min_length=10)
    extracted_fields: Optional[PreferenceStructuredFields] = None
    override_fields: PreferenceFieldOverrides = Field(default_factory=PreferenceFieldOverrides)
    reminder_enabled: bool = True
    reminder_email: Optional[str] = None


class PreferencePatchRequest(BaseModel):
    override_fields: PreferenceFieldOverrides = Field(default_factory=PreferenceFieldOverrides)
    reminder_enabled: Optional[bool] = None
    reminder_email: Optional[str] = None


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    raw_text: Optional[str]
    extracted_fields: PreferenceStructuredFields
    override_fields: dict[str, Any]
    effective_fields: PreferenceStructuredFields
    extracted_at: Optional[str]
    extraction_version: Optional[str]
    reminder_enabled: bool
    reminder_email: Optional[str]

async def get_current_preference(db: AsyncSession, user_id: str) -> Optional[JobPreference]:
    result = await db.execute(
        select(JobPreference)
        .where(JobPreference.user_id == user_id)
        .order_by(JobPreference.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def serialize_preference(preference: JobPreference) -> PreferenceResponse:
    extracted_fields = PreferenceStructuredFields.model_validate(preference.extracted_fields or {})
    effective_fields = PreferenceStructuredFields.model_validate(
        preference.effective_fields or preference.extracted_fields or {}
    )

    return PreferenceResponse(
        id=preference.id,
        raw_text=preference.raw_text,
        extracted_fields=extracted_fields,
        override_fields=preference.override_fields or {},
        effective_fields=effective_fields,
        extracted_at=preference.extracted_at.isoformat() if preference.extracted_at else None,
        extraction_version=preference.extraction_version,
        reminder_enabled=preference.reminder_enabled,
        reminder_email=preference.reminder_email,
    )


def apply_preference_payload(
    preference: JobPreference,
    raw_text: str,
    analysis: PreferenceAnalysisResult,
    overrides: PreferenceFieldOverrides,
    reminder_enabled: bool,
    reminder_email: Optional[str],
):
    override_payload = overrides.model_dump(exclude_unset=True)
    effective = analysis.effective_fields
    legacy = extractor_service.legacy_payload(effective, raw_text)

    preference.raw_text = raw_text
    preference.extracted_fields = analysis.extracted_fields.model_dump()
    preference.override_fields = override_payload
    preference.effective_fields = effective.model_dump()
    preference.extracted_at = analysis.extracted_at
    preference.extraction_version = analysis.extraction_version
    preference.reminder_enabled = reminder_enabled
    preference.reminder_email = reminder_email

    preference.keywords = legacy["keywords"]
    preference.location = legacy["location"]
    preference.is_intern = legacy["is_intern"]
    preference.need_sponsor = legacy["need_sponsor"]
    preference.experience_level = legacy["experience_level"]
    preference.job_description = legacy["job_description"]
    preference.remote_preference = legacy["remote_preference"]
    preference.excluded_companies = legacy["excluded_companies"]
    preference.industries = legacy["industries"]
    preference.salary_min = legacy["salary_min"]
    preference.salary_max = legacy["salary_max"]
    preference.salary_currency = legacy["salary_currency"]


@router.post("/analyze", response_model=PreferenceAnalyzeResponse)
async def analyze_preferences(
    data: PreferenceAnalyzeRequest,
    _: User = Depends(get_current_user),
):
    analysis = await extractor_service.analyze(data.raw_text)
    return PreferenceAnalyzeResponse(
        raw_text=data.raw_text,
        extracted_fields=analysis.extracted_fields,
        effective_fields=analysis.effective_fields,
        extraction_version=analysis.extraction_version,
        extracted_at=analysis.extracted_at.isoformat(),
        used_fallback=analysis.used_fallback,
    )


@router.post("", response_model=PreferenceResponse)
async def create_or_update_preferences(
    data: PreferenceUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = await get_current_preference(db, current_user.id)
    if not preference:
        preference = JobPreference(user_id=current_user.id)
        db.add(preference)

    if data.extracted_fields:
        extracted_fields = PreferenceStructuredFields.model_validate(data.extracted_fields)
        effective_fields = extractor_service.merge_fields(extracted_fields, data.override_fields)
        analysis = PreferenceAnalysisResult(
            extracted_fields=extracted_fields,
            effective_fields=effective_fields,
        )
    else:
        analysis = await extractor_service.analyze(data.raw_text, data.override_fields)

    apply_preference_payload(
        preference=preference,
        raw_text=data.raw_text,
        analysis=analysis,
        overrides=data.override_fields,
        reminder_enabled=data.reminder_enabled,
        reminder_email=data.reminder_email,
    )

    await db.commit()
    await db.refresh(preference)

    return serialize_preference(preference)


@router.patch("/fields", response_model=PreferenceResponse)
async def patch_preference_fields(
    data: PreferencePatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = await get_current_preference(db, current_user.id)
    if not preference:
        raise HTTPException(status_code=404, detail="No preferences found. Analyze and save first.")

    extracted_fields = PreferenceStructuredFields.model_validate(preference.extracted_fields or {})
    merged_overrides = {
        **(preference.override_fields or {}),
        **data.override_fields.model_dump(exclude_unset=True),
    }
    override_fields = PreferenceFieldOverrides.model_validate(merged_overrides)
    effective_fields = extractor_service.merge_fields(extracted_fields, override_fields)
    analysis = PreferenceAnalysisResult(
        extracted_fields=extracted_fields,
        effective_fields=effective_fields,
        extraction_version=preference.extraction_version or EXTRACTION_VERSION,
        extracted_at=preference.extracted_at or datetime.utcnow(),
    )

    apply_preference_payload(
        preference=preference,
        raw_text=preference.raw_text or "",
        analysis=analysis,
        overrides=override_fields,
        reminder_enabled=data.reminder_enabled if data.reminder_enabled is not None else preference.reminder_enabled,
        reminder_email=data.reminder_email if data.reminder_email is not None else preference.reminder_email,
    )

    await db.commit()
    await db.refresh(preference)

    return serialize_preference(preference)


@router.get("", response_model=Optional[PreferenceResponse])
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preference = await get_current_preference(db, current_user.id)
    if not preference:
        return None

    return serialize_preference(preference)
