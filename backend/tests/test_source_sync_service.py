from datetime import datetime, timezone
from collections import deque

import pytest

from app.core.enums import SourceSyncStatus, SourceType
from app.models.models import CompanySource, Opportunity, SourceSyncRun
from app.services.source_sync_service import CompanySourceSyncService


class FakeResult:
    def __init__(self, items=None):
        self.items = items or []

    def scalars(self):
        return self

    def all(self):
        return self.items


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


class FakeGreenhouseClient:
    async def fetch_jobs(self, board_token: str):
        assert board_token == "acme"
        return [
            {
                "id": 123,
                "title": "Backend Engineer",
                "location": {"name": "Remote"},
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                "content": "<p>Build Python services.</p>",
                "updated_at": "2026-04-27T12:00:00Z",
            }
        ]


@pytest.mark.asyncio
async def test_greenhouse_sync_upserts_jobs_and_closes_missing_opportunities():
    source = CompanySource(
        id="source-1",
        source_type=SourceType.GREENHOUSE,
        company_name="Acme",
        board_token="acme",
        is_active=True,
    )
    stale_opportunity = Opportunity(
        id="opp-old",
        company_source_id="source-1",
        source_type=SourceType.GREENHOUSE,
        source_job_id="acme:old",
        title="Old Role",
        company="Acme",
        is_open=True,
        last_seen_at=datetime.now(timezone.utc),
    )
    session = FakeSession(
        FakeResult(items=[]),
        FakeResult(items=[stale_opportunity]),
    )
    service = CompanySourceSyncService(greenhouse_client=FakeGreenhouseClient())

    run = await service.sync_company_source(session, source)

    assert isinstance(run, SourceSyncRun)
    assert run.status == SourceSyncStatus.SUCCESS
    assert run.fetched_count == 1
    assert run.upserted_count == 1
    assert run.closed_count == 1
    assert source.last_synced_at is not None
    assert stale_opportunity.is_open is False

    created_opportunity = next(item for item in session.added if isinstance(item, Opportunity))
    assert created_opportunity.source_job_id == "acme:123"
    assert created_opportunity.company == "Acme"
    assert created_opportunity.location == "Remote"
    assert created_opportunity.description == "Build Python services."
