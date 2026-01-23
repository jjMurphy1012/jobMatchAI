from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import JobPreference

router = APIRouter()


class PreferenceCreate(BaseModel):
    keywords: str  # Comma-separated: "React, TypeScript, Frontend"
    location: Optional[str] = None
    is_intern: bool = False
    need_sponsor: bool = False
    experience_level: Optional[str] = None  # entry, mid, senior
    job_description: Optional[str] = None
    remote_preference: Optional[str] = None  # remote, hybrid, onsite
    reminder_enabled: bool = True
    reminder_email: Optional[str] = None


class PreferenceResponse(BaseModel):
    id: str
    keywords: str
    location: Optional[str]
    is_intern: bool
    need_sponsor: bool
    experience_level: Optional[str]
    job_description: Optional[str]
    remote_preference: Optional[str]
    reminder_enabled: bool
    reminder_email: Optional[str]

    class Config:
        from_attributes = True


@router.post("", response_model=PreferenceResponse)
async def create_or_update_preferences(
    data: PreferenceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create or update job preferences (single user mode - replaces existing)."""
    # Delete existing preferences
    result = await db.execute(select(JobPreference))
    for pref in result.scalars().all():
        await db.delete(pref)

    # Create new preferences
    preference = JobPreference(
        keywords=data.keywords,
        location=data.location,
        is_intern=data.is_intern,
        need_sponsor=data.need_sponsor,
        experience_level=data.experience_level,
        job_description=data.job_description,
        remote_preference=data.remote_preference,
        reminder_enabled=data.reminder_enabled,
        reminder_email=data.reminder_email
    )
    db.add(preference)
    await db.commit()
    await db.refresh(preference)

    return preference


@router.get("", response_model=Optional[PreferenceResponse])
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get current job preferences."""
    result = await db.execute(
        select(JobPreference).order_by(JobPreference.created_at.desc())
    )
    preference = result.scalar_one_or_none()
    return preference


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    data: PreferenceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update existing preferences."""
    result = await db.execute(select(JobPreference))
    preference = result.scalar_one_or_none()

    if not preference:
        raise HTTPException(status_code=404, detail="No preferences found. Create first.")

    # Update fields
    preference.keywords = data.keywords
    preference.location = data.location
    preference.is_intern = data.is_intern
    preference.need_sponsor = data.need_sponsor
    preference.experience_level = data.experience_level
    preference.job_description = data.job_description
    preference.remote_preference = data.remote_preference
    preference.reminder_enabled = data.reminder_enabled
    preference.reminder_email = data.reminder_email

    await db.commit()
    await db.refresh(preference)

    return preference
