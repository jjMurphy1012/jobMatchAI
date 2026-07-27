from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional
import logging

import pytz
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.enums import NotificationKind, NotificationStatus
from app.models.models import JobPreference, NotificationLog, Opportunity, User, UserJobMatch
from app.services.email_service import (
    DigestJob,
    EmailMessage,
    SendGridEmailService,
    email_service,
    render_daily_digest,
    render_test_email,
)

logger = logging.getLogger(__name__)


def local_today() -> date:
    return datetime.now(pytz.timezone(settings.TIMEZONE)).date()


@dataclass
class _PendingEmail:
    """What a read pass decided to send, carried across the DB-free send step."""
    message: EmailMessage
    match_count: int


class NotificationService:
    """Decides who gets an email, keeps delivery idempotent, and records outcomes.

    Sessions are owned here and deliberately closed before the SendGrid call, so
    a slow provider never pins a pooled connection for the length of a retry
    sequence.
    """

    def __init__(self, sender: Optional[SendGridEmailService] = None, session_factory=None):
        self.sender = sender or email_service
        self._session_factory = session_factory or async_session_maker

    async def send_daily_digest(
        self,
        user_id: str,
        *,
        for_date: Optional[date] = None,
        scored_since: Optional[datetime] = None,
    ) -> Optional[NotificationLog]:
        """Email one user their latest matches. Returns None when nothing was sent."""
        target_date = for_date or local_today()

        async with self._session_factory() as db:
            pending = await self._prepare_digest(db, user_id, target_date, scored_since)
        if pending is None:
            return None

        result = await self.sender.send(pending.message)

        return await self._record(
            user_id=user_id,
            kind=NotificationKind.DAILY_DIGEST,
            message=pending.message,
            result=result,
            match_count=pending.match_count,
            # Only successful sends claim the daily slot; failures stay retryable.
            sent_for_date=target_date if result.sent else None,
        )

    async def send_test_email(self, user_id: str, recipient: str) -> Optional[NotificationLog]:
        message = render_test_email(recipient.strip())
        result = await self.sender.send(message)
        return await self._record(
            user_id=user_id,
            kind=NotificationKind.TEST,
            message=message,
            result=result,
            match_count=0,
            sent_for_date=None,
        )

    async def _prepare_digest(
        self,
        db: AsyncSession,
        user_id: str,
        target_date: date,
        scored_since: Optional[datetime],
    ) -> Optional[_PendingEmail]:
        user = await db.get(User, user_id)
        if user is None:
            return None

        preference = await self._get_preference(db, user_id)
        if preference is None or not preference.reminder_enabled:
            logger.debug("Digest skipped for user %s: reminders disabled", user_id)
            return None

        recipient = (preference.reminder_email or user.email or "").strip()
        if not recipient:
            logger.warning("Digest skipped for user %s: no recipient address", user_id)
            return None

        # Cheap index probe that avoids the API call in the common repeat case;
        # the partial unique index on notification_logs is the real guarantee.
        if await self._already_sent(db, user_id, NotificationKind.DAILY_DIGEST, target_date):
            logger.info("Digest already sent to user %s for %s", user_id, target_date)
            return None

        jobs = await self._load_digest_jobs(db, user_id, scored_since)
        if not jobs:
            logger.info("Digest skipped for user %s: no matches to report", user_id)
            return None

        message = render_daily_digest(jobs, to_email=recipient, recipient_name=user.name)
        return _PendingEmail(message=message, match_count=len(jobs))

    async def _record(
        self,
        *,
        user_id: str,
        kind: str,
        message: EmailMessage,
        result,
        match_count: int,
        sent_for_date: Optional[date],
    ) -> Optional[NotificationLog]:
        log = NotificationLog(
            user_id=user_id,
            kind=kind,
            recipient=message.to_email,
            subject=message.subject,
            status=result.status,
            attempts=result.attempts,
            provider_message_id=result.provider_message_id,
            error_message=result.error_message,
            match_count=match_count,
            sent_for_date=sent_for_date,
        )

        async with self._session_factory() as db:
            db.add(log)
            try:
                await db.commit()
            except IntegrityError:
                # Another worker delivered the same digest between the check and
                # this insert. The partial unique index is the real guarantee.
                await db.rollback()
                logger.info("Digest for user %s on %s was already recorded", user_id, sent_for_date)
                return None

        if result.status == NotificationStatus.FAILED:
            logger.error(
                "Email to %s failed after %s attempt(s): %s",
                message.to_email,
                result.attempts,
                result.error_message,
            )
        return log

    async def _get_preference(self, db: AsyncSession, user_id: str) -> Optional[JobPreference]:
        result = await db.execute(
            select(JobPreference)
            .where(JobPreference.user_id == user_id)
            .order_by(JobPreference.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _already_sent(self, db: AsyncSession, user_id: str, kind: str, target_date: date) -> bool:
        result = await db.execute(
            select(NotificationLog.id)
            .where(
                NotificationLog.user_id == user_id,
                NotificationLog.kind == kind,
                NotificationLog.sent_for_date == target_date,
                NotificationLog.status == NotificationStatus.SENT,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _load_digest_jobs(
        self,
        db: AsyncSession,
        user_id: str,
        scored_since: Optional[datetime],
    ) -> list[DigestJob]:
        query = (
            select(UserJobMatch, Opportunity)
            .join(Opportunity, Opportunity.id == UserJobMatch.opportunity_id)
            .where(UserJobMatch.user_id == user_id)
        )
        if scored_since is not None:
            query = query.where(UserJobMatch.last_scored_at >= scored_since)

        result = await db.execute(
            query.order_by(UserJobMatch.match_score.desc(), UserJobMatch.last_scored_at.desc())
            .limit(max(1, settings.EMAIL_DIGEST_MAX_MATCHES))
        )

        return [
            DigestJob(
                title=opportunity.title,
                company=opportunity.company,
                match_score=match.match_score,
                location=opportunity.location,
                url=opportunity.url,
                match_reason=match.match_reason,
            )
            for match, opportunity in result.all()
        ]


notification_service = NotificationService()
