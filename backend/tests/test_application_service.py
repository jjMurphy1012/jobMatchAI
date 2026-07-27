from collections import deque
from datetime import date, datetime, timezone

import pytest

from app.core.enums import ApplicationChannel, ApplicationEventKind, ApplicationStatus
from app.models.models import Application, Opportunity, UserJobMatch
from app.services.application_service import (
    ApplicationError,
    ApplicationInput,
    ApplicationService,
    DuplicateApplicationError,
    MatchNotFoundError,
)


class FakeResult:
    def __init__(self, scalar=None):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class FakeSession:
    def __init__(self, *results):
        self.results = deque(results)
        self.added = []
        self.flushes = 0

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, _statement):
        if not self.results:
            raise AssertionError("No fake result queued for execute()")
        return self.results.popleft()

    async def flush(self):
        self.flushes += 1


def build_match(match_id: str = "match-1") -> UserJobMatch:
    match = UserJobMatch(
        id=match_id,
        user_id="user-1",
        opportunity_id="opp-1",
        match_score=88,
    )
    match.opportunity = Opportunity(
        id="opp-1",
        source_type="greenhouse",
        source_job_id="acme:1",
        title="Backend Engineer",
        company="Acme",
        location="Boston, MA",
        url="https://boards.test/acme/1",
    )
    return match


@pytest.mark.asyncio
async def test_manual_entry_snapshots_the_typed_details():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(
            company_name="  Stripe  ",
            job_title=" Backend Engineer ",
            location="Remote",
            channel=ApplicationChannel.REFERRAL,
            season="2026",
            notes="Referred by a friend",
        ),
    )

    assert application.company_name == "Stripe"
    assert application.job_title == "Backend Engineer"
    assert application.channel == ApplicationChannel.REFERRAL
    assert application.season == "2026"
    # No job in the system to point at, and that is a valid state.
    assert application.opportunity_id is None
    assert application.user_job_match_id is None
    # The submission is seeded as the first timeline entry.
    assert [event.kind for event in application.events] == [ApplicationEventKind.APPLIED]
    assert application.events[0].label == ApplicationChannel.REFERRAL


@pytest.mark.asyncio
async def test_creating_from_a_match_copies_the_job_details():
    match = build_match()
    session = FakeSession(FakeResult(scalar=match), FakeResult(scalar=None))

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(user_job_match_id="match-1"),
    )

    assert application.company_name == "Acme"
    assert application.job_title == "Backend Engineer"
    assert application.location == "Boston, MA"
    assert application.job_url == "https://boards.test/acme/1"
    assert application.opportunity_id == "opp-1"
    assert application.user_job_match_id == "match-1"
    assert application.status == ApplicationStatus.APPLIED
    assert application.applied_at is not None


@pytest.mark.asyncio
async def test_explicit_fields_win_over_the_matched_opportunity():
    match = build_match()
    session = FakeSession(FakeResult(scalar=match), FakeResult(scalar=None))

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(
            user_job_match_id="match-1",
            company_name="Acme Payments",
            location="New York, NY",
        ),
    )

    assert application.company_name == "Acme Payments"
    assert application.location == "New York, NY"
    # Untouched fields still come from the match.
    assert application.job_title == "Backend Engineer"


@pytest.mark.asyncio
async def test_snapshot_survives_a_deleted_opportunity():
    """The point of snapshotting: reading the record never goes back to the FK."""
    match = build_match()
    session = FakeSession(FakeResult(scalar=match), FakeResult(scalar=None))

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(user_job_match_id="match-1"),
    )
    # Simulate the nightly cleanup dropping the job rows.
    application.opportunity_id = None
    application.user_job_match_id = None

    assert application.company_name == "Acme"
    assert application.job_title == "Backend Engineer"


@pytest.mark.asyncio
async def test_match_belonging_to_another_user_is_not_found():
    session = FakeSession(FakeResult(scalar=None))

    with pytest.raises(MatchNotFoundError):
        await ApplicationService().create(
            session,
            "user-1",
            ApplicationInput(user_job_match_id="someone-elses-match"),
        )


@pytest.mark.asyncio
async def test_second_application_for_the_same_match_is_rejected():
    match = build_match()
    existing = Application(id="app-1", user_id="user-1", company_name="Acme", job_title="Backend Engineer")
    session = FakeSession(FakeResult(scalar=match), FakeResult(scalar=existing))

    with pytest.raises(DuplicateApplicationError) as exc_info:
        await ApplicationService().create(
            session,
            "user-1",
            ApplicationInput(user_job_match_id="match-1"),
        )

    assert exc_info.value.application_id == "app-1"


@pytest.mark.asyncio
async def test_manual_entry_requires_company_and_title():
    session = FakeSession()

    with pytest.raises(ApplicationError):
        await ApplicationService().create(session, "user-1", ApplicationInput(company_name="Stripe"))


@pytest.mark.asyncio
async def test_saved_status_does_not_stamp_an_applied_date():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(
            company_name="Stripe",
            job_title="Backend Engineer",
            status=ApplicationStatus.SAVED,
        ),
    )

    assert application.applied_at is None


@pytest.mark.asyncio
async def test_status_change_stamps_the_transition_time():
    session = FakeSession()
    application = Application(
        id="app-1",
        user_id="user-1",
        company_name="Acme",
        job_title="Backend Engineer",
        status=ApplicationStatus.APPLIED,
        status_updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        applied_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    updated = await ApplicationService().update(
        session,
        application,
        {"status": ApplicationStatus.INTERVIEWING},
    )

    assert updated.status == ApplicationStatus.INTERVIEWING
    assert updated.status_updated_at > datetime(2026, 1, 1, tzinfo=timezone.utc)
    # The original submission date is history and must not move.
    assert updated.applied_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_editing_notes_does_not_touch_the_status_timestamp():
    session = FakeSession()
    stamped = datetime(2026, 1, 1, tzinfo=timezone.utc)
    application = Application(
        id="app-1",
        user_id="user-1",
        company_name="Acme",
        job_title="Backend Engineer",
        status=ApplicationStatus.APPLIED,
        status_updated_at=stamped,
    )

    updated = await ApplicationService().update(session, application, {"notes": "Recruiter call booked"})

    assert updated.notes == "Recruiter call booked"
    assert updated.status_updated_at == stamped


@pytest.mark.asyncio
async def test_backfilling_a_stage_stamps_a_missing_applied_date():
    session = FakeSession()
    application = Application(
        id="app-1",
        user_id="user-1",
        company_name="Acme",
        job_title="Backend Engineer",
        status=ApplicationStatus.SAVED,
        applied_at=None,
    )

    updated = await ApplicationService().update(
        session,
        application,
        {"status": ApplicationStatus.ASSESSMENT},
    )

    assert updated.applied_at is not None


@pytest.mark.asyncio
async def test_saved_application_has_no_timeline_yet():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(
            company_name="Stripe",
            job_title="Backend Engineer",
            status=ApplicationStatus.SAVED,
        ),
    )

    assert application.events == []


@pytest.mark.asyncio
async def test_adding_a_stage_event_moves_the_application_to_that_stage():
    session = FakeSession()
    application = Application(
        id="app-1",
        user_id="user-1",
        company_name="Acme",
        job_title="Backend Engineer",
        status=ApplicationStatus.APPLIED,
    )

    updated = await ApplicationService().add_event(
        session,
        application,
        kind=ApplicationEventKind.ASSESSMENT,
        occurred_on=date(2026, 7, 23),
        label="Online Test",
    )

    assert updated.status == ApplicationStatus.ASSESSMENT
    assert updated.events[-1].occurred_on == date(2026, 7, 23)
    assert updated.events[-1].label == "Online Test"


@pytest.mark.asyncio
async def test_several_interview_rounds_are_kept_as_separate_events():
    session = FakeSession()
    application = Application(id="app-1", user_id="user-1", company_name="Acme", job_title="Engineer")
    service = ApplicationService()

    await service.add_event(
        session, application, kind=ApplicationEventKind.INTERVIEW,
        occurred_on=date(2026, 8, 1), label="Round 1",
    )
    await service.add_event(
        session, application, kind=ApplicationEventKind.INTERVIEW,
        occurred_on=date(2026, 8, 8), label="Round 2",
    )

    assert [event.label for event in application.events] == ["Round 1", "Round 2"]
    assert application.status == ApplicationStatus.INTERVIEWING


@pytest.mark.asyncio
async def test_deleting_an_event_reports_whether_it_existed():
    session = FakeSession()
    application = Application(id="app-1", user_id="user-1", company_name="Acme", job_title="Engineer")
    await ApplicationService().add_event(
        session, application, kind=ApplicationEventKind.INTERVIEW, occurred_on=date(2026, 8, 1),
    )
    application.events[0].id = "event-1"

    assert await ApplicationService().delete_event(session, application, "event-1") is True
    assert application.events == []
    assert await ApplicationService().delete_event(session, application, "event-1") is False


@pytest.mark.asyncio
async def test_region_is_inferred_from_the_location_when_not_given():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(company_name="Acme", job_title="Engineer", location="Boston, MA"),
    )

    assert application.region == "us"


@pytest.mark.asyncio
async def test_explicit_region_beats_the_guess():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(
            company_name="Acme", job_title="Engineer", location="Boston, MA", region="uk",
        ),
    )

    assert application.region == "uk"


@pytest.mark.asyncio
async def test_unrecognised_location_leaves_the_region_unset():
    session = FakeSession()

    application = await ApplicationService().create(
        session,
        "user-1",
        ApplicationInput(company_name="Acme", job_title="Engineer", location="Atlantis"),
    )

    assert application.region is None
