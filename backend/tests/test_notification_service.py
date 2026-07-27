from collections import deque
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.enums import NotificationKind, NotificationStatus
from app.models.models import JobPreference, NotificationLog, Opportunity, User, UserJobMatch
from app.services.email_service import EmailDeliveryResult
from app.services.notification_service import NotificationService


class FakeResult:
    """Mimics the subset of the SQLAlchemy Result API the service uses."""

    def __init__(self, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, *results, entities=None, commit_error=None):
        self.results = deque(results)
        self.entities = entities or {}
        self.commit_error = commit_error
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return False

    async def get(self, _model, primary_key):
        return self.entities.get(primary_key)

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, _statement):
        if not self.results:
            raise AssertionError("No fake result queued for execute()")
        return self.results.popleft()

    async def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeSessionFactory:
    """Hands out one prepared session per `async with` block, in order."""

    def __init__(self, *sessions):
        self.sessions = deque(sessions)
        self.used = []

    def __call__(self):
        session = self.sessions.popleft() if self.sessions else FakeSession()
        self.used.append(session)
        return session


class FakeSender:
    def __init__(self, result: EmailDeliveryResult):
        self.result = result
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return self.result


def build_user(email: str = "user@example.com") -> User:
    return User(id="user-1", email=email, name="Jiajun")


def build_preference(**overrides) -> JobPreference:
    defaults = {
        "id": "pref-1",
        "user_id": "user-1",
        "reminder_enabled": True,
        "reminder_email": None,
    }
    defaults.update(overrides)
    return JobPreference(**defaults)


def build_match_row(score: int = 88):
    match = UserJobMatch(
        id="match-1",
        user_id="user-1",
        opportunity_id="opp-1",
        match_score=score,
        match_reason="Strong Python overlap",
        last_scored_at=datetime.now(timezone.utc),
    )
    opportunity = Opportunity(
        id="opp-1",
        source_type="greenhouse",
        source_job_id="acme:1",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        url="https://boards.test/acme/1",
    )
    return match, opportunity


def read_session(preference, *, already_sent=None, rows=None, user=None):
    """Session for the read pass: preference lookup, idempotency probe, digest jobs."""
    results = [FakeResult(scalar=preference)]
    if preference is not None and preference.reminder_enabled:
        results.append(FakeResult(scalar=already_sent))
        if already_sent is None:
            results.append(FakeResult(rows=rows or []))
    return FakeSession(*results, entities={"user-1": user or build_user()})


@pytest.mark.asyncio
async def test_daily_digest_sends_and_records_delivery():
    sender = FakeSender(
        EmailDeliveryResult(
            status=NotificationStatus.SENT,
            attempts=1,
            provider_message_id="msg-1",
        )
    )
    write = FakeSession()
    factory = FakeSessionFactory(
        read_session(build_preference(), rows=[build_match_row()]),
        write,
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest(
        "user-1",
        for_date=date(2026, 7, 27),
    )

    assert isinstance(log, NotificationLog)
    assert log.status == NotificationStatus.SENT
    assert log.recipient == "user@example.com"
    assert log.kind == NotificationKind.DAILY_DIGEST
    assert log.provider_message_id == "msg-1"
    assert log.match_count == 1
    assert log.sent_for_date == date(2026, 7, 27)
    assert write.commits == 1

    assert sender.messages[0].to_email == "user@example.com"
    assert "Backend Engineer" in sender.messages[0].text_body


@pytest.mark.asyncio
async def test_send_happens_after_the_read_session_is_closed():
    """A slow provider must not pin a pooled connection."""
    closed_before_send = {}

    class TrackingSession(FakeSession):
        exited = False

        async def __aexit__(self, *exc_info):
            self.exited = True
            return await super().__aexit__(*exc_info)

    read = read_session(build_preference(), rows=[build_match_row()])
    tracked = TrackingSession(*read.results, entities=read.entities)

    class TrackingSender(FakeSender):
        async def send(self, message):
            closed_before_send["read_exited"] = tracked.exited
            return await super().send(message)

    read = tracked
    sender = TrackingSender(EmailDeliveryResult(status=NotificationStatus.SENT, attempts=1))
    factory = FakeSessionFactory(read, FakeSession())

    await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert closed_before_send["read_exited"] is True


@pytest.mark.asyncio
async def test_daily_digest_prefers_reminder_email_over_account_email():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT, attempts=1))
    factory = FakeSessionFactory(
        read_session(build_preference(reminder_email="alt@example.com"), rows=[build_match_row()]),
        FakeSession(),
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log.recipient == "alt@example.com"


@pytest.mark.asyncio
async def test_daily_digest_skipped_when_reminders_disabled():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT))
    factory = FakeSessionFactory(read_session(build_preference(reminder_enabled=False)))

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log is None
    assert sender.messages == []


@pytest.mark.asyncio
async def test_daily_digest_skipped_when_already_sent_today():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT))
    factory = FakeSessionFactory(
        read_session(build_preference(), already_sent="existing-log-id"),
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log is None
    assert sender.messages == []


@pytest.mark.asyncio
async def test_daily_digest_skipped_when_no_matches():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT))
    factory = FakeSessionFactory(read_session(build_preference(), rows=[]))

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log is None
    assert sender.messages == []


@pytest.mark.asyncio
async def test_daily_digest_skipped_when_user_has_no_address():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT))
    factory = FakeSessionFactory(
        read_session(build_preference(), user=build_user(email=""), rows=[build_match_row()]),
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log is None
    assert sender.messages == []


@pytest.mark.asyncio
async def test_failed_delivery_is_logged_without_claiming_the_daily_slot():
    sender = FakeSender(
        EmailDeliveryResult(
            status=NotificationStatus.FAILED,
            attempts=3,
            error_message="SendGrid responded 500",
        )
    )
    factory = FakeSessionFactory(
        read_session(build_preference(), rows=[build_match_row()]),
        FakeSession(),
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest(
        "user-1",
        for_date=date(2026, 7, 27),
    )

    assert log.status == NotificationStatus.FAILED
    assert log.attempts == 3
    assert log.error_message == "SendGrid responded 500"
    # sent_for_date stays NULL so the partial unique index does not block a retry.
    assert log.sent_for_date is None


@pytest.mark.asyncio
async def test_concurrent_duplicate_send_is_absorbed_by_the_unique_index():
    sender = FakeSender(EmailDeliveryResult(status=NotificationStatus.SENT, attempts=1))
    write = FakeSession(commit_error=IntegrityError("insert", {}, Exception("duplicate key")))
    factory = FakeSessionFactory(
        read_session(build_preference(), rows=[build_match_row()]),
        write,
    )

    log = await NotificationService(sender=sender, session_factory=factory).send_daily_digest("user-1")

    assert log is None
    assert write.rollbacks == 1


@pytest.mark.asyncio
async def test_test_email_is_logged_without_a_daily_slot():
    sender = FakeSender(
        EmailDeliveryResult(status=NotificationStatus.SENT, attempts=1, provider_message_id="msg-t")
    )
    factory = FakeSessionFactory(FakeSession())

    log = await NotificationService(sender=sender, session_factory=factory).send_test_email(
        "user-1",
        "admin@example.com",
    )

    assert log.kind == NotificationKind.TEST
    assert log.recipient == "admin@example.com"
    assert log.sent_for_date is None
    assert log.match_count == 0
