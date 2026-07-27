from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import SUBMITTED_STATUSES, ApplicationChannel, ApplicationStatus
from app.models.models import Application, Opportunity, UserJobMatch


class ApplicationError(Exception):
    """Base for application write failures the API turns into HTTP errors."""


class MatchNotFoundError(ApplicationError):
    pass


class DuplicateApplicationError(ApplicationError):
    """The user already tracks an application for this match."""

    def __init__(self, application_id: str):
        super().__init__("An application already exists for this match.")
        self.application_id = application_id


@dataclass
class ApplicationInput:
    """Everything a caller can set. Snapshot fields are optional only when a
    match supplies them."""
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    job_type: Optional[str] = None
    season: Optional[str] = None
    channel: str = ApplicationChannel.ONLINE
    status: str = ApplicationStatus.APPLIED
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    user_job_match_id: Optional[str] = None


class ApplicationService:
    """Single write path for tracked applications, whether they come from a
    match or are typed in by hand."""

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        payload: ApplicationInput,
    ) -> Application:
        if not payload.user_job_match_id:
            return await self._insert(db, user_id, payload, match=None)

        match = await self._load_match(db, user_id, payload.user_job_match_id)
        existing = await self._find_by_match(db, user_id, match.id)
        if existing is not None:
            raise DuplicateApplicationError(existing.id)
        return await self._insert(db, user_id, payload, match=match)

    async def create_for_match(
        self,
        db: AsyncSession,
        user_id: str,
        match: UserJobMatch,
        payload: ApplicationInput,
    ) -> Application:
        """For callers that already loaded and authorized the match."""
        return await self._insert(db, user_id, payload, match=match)

    async def _insert(
        self,
        db: AsyncSession,
        user_id: str,
        payload: ApplicationInput,
        *,
        match: Optional[UserJobMatch],
    ) -> Application:
        snapshot = self._build_snapshot(payload, match)
        now = datetime.now(timezone.utc)
        status = payload.status or ApplicationStatus.APPLIED

        application = Application(
            user_id=user_id,
            opportunity_id=match.opportunity_id if match else None,
            user_job_match_id=match.id if match else None,
            status=status,
            applied_at=payload.applied_at or (now if status in SUBMITTED_STATUSES else None),
            notes=payload.notes,
            status_updated_at=now,
            **snapshot,
        )
        db.add(application)
        await db.flush()
        return application

    async def update(
        self,
        db: AsyncSession,
        application: Application,
        changes: dict,
    ) -> Application:
        status_changed = "status" in changes and changes["status"] != application.status

        for field in ("company_name", "job_title"):
            if field in changes:
                cleaned = _first_text(changes[field])
                if cleaned is None:
                    raise ApplicationError(f"{field} cannot be empty.")
                changes[field] = cleaned

        for field, value in changes.items():
            setattr(application, field, value)

        if status_changed:
            application.status_updated_at = datetime.now(timezone.utc)
            # Reaching a submitted stage without a recorded date is almost always
            # an edit made after the fact; stamp it rather than leaving a hole.
            if application.status in SUBMITTED_STATUSES and application.applied_at is None:
                application.applied_at = datetime.now(timezone.utc)

        await db.flush()
        return application

    async def get_owned(self, db: AsyncSession, user_id: str, application_id: str) -> Optional[Application]:
        result = await db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Application]:
        query = select(Application).where(Application.user_id == user_id)
        query = self._apply_filters(query, status=status, job_type=job_type, channel=channel, search=search)

        result = await db.execute(
            query.order_by(
                Application.applied_at.desc().nullslast(),
                Application.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_status(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        job_type: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, int]:
        """Stage counts for the filter tabs. Deliberately ignores the status
        filter so the tabs keep showing every stage's total."""
        query = (
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        query = self._apply_filters(query, job_type=job_type, channel=channel, search=search)
        result = await db.execute(query)
        return {status: count for status, count in result.all()}

    def _apply_filters(
        self,
        query,
        *,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
    ):
        if status:
            query = query.where(Application.status == status)
        if job_type:
            query = query.where(Application.job_type == job_type)
        if channel:
            query = query.where(Application.channel == channel)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                func.lower(Application.company_name).like(pattern)
                | func.lower(Application.job_title).like(pattern)
            )
        return query

    async def _load_match(self, db: AsyncSession, user_id: str, match_id: str) -> UserJobMatch:
        result = await db.execute(
            select(UserJobMatch)
            .options(selectinload(UserJobMatch.opportunity))
            .where(UserJobMatch.id == match_id, UserJobMatch.user_id == user_id)
        )
        match = result.scalar_one_or_none()
        if match is None:
            raise MatchNotFoundError("Match not found.")
        return match

    async def _find_by_match(self, db: AsyncSession, user_id: str, match_id: str) -> Optional[Application]:
        result = await db.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.user_job_match_id == match_id,
            )
        )
        return result.scalar_one_or_none()

    def _build_snapshot(self, payload: ApplicationInput, match: Optional[UserJobMatch]) -> dict:
        """Freeze the job details onto the application. Explicit input wins, the
        matched opportunity fills the gaps, and nothing reads back through the
        foreign key afterwards."""
        opportunity: Optional[Opportunity] = match.opportunity if match else None

        company = _first_text(payload.company_name, opportunity.company if opportunity else None)
        title = _first_text(payload.job_title, opportunity.title if opportunity else None)
        if not company or not title:
            raise ApplicationError("company_name and job_title are required.")

        return {
            "company_name": company,
            "job_title": title,
            "location": _first_text(payload.location, opportunity.location if opportunity else None),
            "job_url": _first_text(payload.job_url, opportunity.url if opportunity else None),
            "job_type": _first_text(payload.job_type),
            "season": _first_text(payload.season),
            "channel": payload.channel or ApplicationChannel.ONLINE,
        }


def _first_text(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


application_service = ApplicationService()
