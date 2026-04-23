from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import InterviewExperience, JobPreference, User, UserJobMatch
from app.services.preference_extractor import PreferenceStructuredFields

router = APIRouter()


def _normalize_company(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _tokenize_text(*parts: object) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        if isinstance(part, list):
            for item in part:
                tokens.update(_tokenize_text(item))
            continue
        if not part:
            continue
        for raw in str(part).replace("/", " ").replace(",", " ").split():
            token = raw.strip().lower()
            if len(token) >= 2:
                tokens.add(token)
    return tokens


class InterviewExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    role: str
    level: Optional[str]
    year: Optional[int]
    rounds: Optional[str]
    topics: list[str]
    summary: str
    source_url: Optional[str]
    source_site: Optional[str]
    relevance_score: int
    matched_company: bool


@router.get("", response_model=list[InterviewExperienceResponse])
async def list_relevant_interview_experiences(
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List published interview experiences ranked by the user's current matches and profile."""
    pref_result = await db.execute(
        select(JobPreference)
        .where(JobPreference.user_id == current_user.id)
        .order_by(JobPreference.updated_at.desc().nullslast(), JobPreference.created_at.desc())
        .limit(1)
    )
    preference = pref_result.scalar_one_or_none()
    fields = PreferenceStructuredFields.model_validate((preference.effective_fields or {}) if preference else {})

    match_result = await db.execute(
        select(UserJobMatch)
        .options(selectinload(UserJobMatch.opportunity))
        .where(UserJobMatch.user_id == current_user.id)
        .order_by(UserJobMatch.match_score.desc(), UserJobMatch.last_scored_at.desc())
        .limit(20)
    )
    matches = match_result.scalars().all()
    preferred_companies = {
        _normalize_company(match.opportunity.company)
        for match in matches
        if match.opportunity and match.opportunity.company
    }

    keyword_tokens = _tokenize_text(fields.keywords, fields.industries, fields.locations)
    if preference and preference.raw_text:
        keyword_tokens.update(_tokenize_text(preference.raw_text))

    result = await db.execute(
        select(InterviewExperience)
        .where(InterviewExperience.review_status == "published")
        .order_by(InterviewExperience.updated_at.desc(), InterviewExperience.created_at.desc())
    )
    experiences = result.scalars().all()

    ranked: list[tuple[int, bool, InterviewExperience]] = []
    for experience in experiences:
        matched_company = experience.company_name_normalized in preferred_companies
        score = 100 if matched_company else 0
        experience_tokens = _tokenize_text(
            experience.company_name,
            experience.role,
            experience.level,
            experience.rounds,
            experience.summary,
            experience.topics or [],
            experience.relevance_keywords or [],
        )
        score += len(keyword_tokens & experience_tokens) * 5
        if experience.level and fields.experience_level and experience.level.lower() == fields.experience_level.lower():
            score += 10
        if score > 0 or not preferred_companies:
            ranked.append((score, matched_company, experience))

    ranked.sort(key=lambda item: (item[0], item[1], item[2].updated_at or item[2].created_at), reverse=True)

    return [
        InterviewExperienceResponse(
            id=experience.id,
            company_name=experience.company_name,
            role=experience.role,
            level=experience.level,
            year=experience.year,
            rounds=experience.rounds,
            topics=list(experience.topics or []),
            summary=experience.summary,
            source_url=experience.source_url,
            source_site=experience.source_site,
            relevance_score=score,
            matched_company=matched_company,
        )
        for score, matched_company, experience in ranked[:limit]
    ]
