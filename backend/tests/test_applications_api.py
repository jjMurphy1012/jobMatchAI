from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import applications as applications_api
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.enums import ApplicationChannel, ApplicationStatus
from app.models.models import Application, User
from app.services.application_service import DuplicateApplicationError, MatchNotFoundError


class FakeSession:
    def __init__(self):
        self.deleted = []

    async def flush(self):
        return None

    async def delete(self, obj):
        self.deleted.append(obj)


def build_application(**overrides) -> Application:
    defaults = {
        "id": "app-1",
        "user_id": "user-1",
        "company_name": "Acme",
        "job_title": "Backend Engineer",
        "location": "Boston, MA",
        "job_url": "https://boards.test/acme/1",
        "job_type": "full_time",
        "season": "2026",
        "channel": ApplicationChannel.ONLINE,
        "status": ApplicationStatus.APPLIED,
        "applied_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "notes": None,
        "opportunity_id": "opp-1",
        "user_job_match_id": "match-1",
        "status_updated_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "created_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return Application(**defaults)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(applications_api.router, prefix="/api/applications")
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: User(id="user-1", email="user@example.com")
    with TestClient(app) as test_client:
        test_client.session = session
        yield test_client


def test_list_returns_applications_with_stage_counts(client, monkeypatch):
    async def fake_list(*_args, **_kwargs):
        return [build_application()]

    async def fake_counts(*_args, **_kwargs):
        return {ApplicationStatus.APPLIED: 31, ApplicationStatus.REJECTED: 5}

    monkeypatch.setattr(applications_api.application_service, "list_for_user", fake_list)
    monkeypatch.setattr(applications_api.application_service, "count_by_status", fake_counts)

    response = client.get("/api/applications")

    assert response.status_code == 200
    body = response.json()
    assert body["applications"][0]["company_name"] == "Acme"
    assert body["status_counts"] == {"applied": 31, "rejected": 5}
    assert body["total"] == 36


def test_list_rejects_an_unknown_stage_filter(client):
    response = client.get("/api/applications", params={"status": "ghosted"})

    assert response.status_code == 400
    assert "status must be one of" in response.json()["detail"]


def test_create_manual_application(client, monkeypatch):
    captured = {}

    async def fake_create(_db, user_id, payload):
        captured["user_id"] = user_id
        captured["payload"] = payload
        return build_application(
            company_name=payload.company_name,
            opportunity_id=None,
            user_job_match_id=None,
        )

    monkeypatch.setattr(applications_api.application_service, "create", fake_create)

    response = client.post(
        "/api/applications",
        json={
            "company_name": "Stripe",
            "job_title": "Backend Engineer",
            "channel": "referral",
        },
    )

    assert response.status_code == 201
    assert response.json()["company_name"] == "Stripe"
    assert captured["user_id"] == "user-1"
    assert captured["payload"].channel == "referral"


def test_create_from_match_passes_the_match_id(client, monkeypatch):
    captured = {}

    async def fake_create(_db, _user_id, payload):
        captured["match_id"] = payload.user_job_match_id
        return build_application()

    monkeypatch.setattr(applications_api.application_service, "create", fake_create)

    response = client.post("/api/applications", json={"user_job_match_id": "match-1"})

    assert response.status_code == 201
    assert captured["match_id"] == "match-1"


def test_create_rejects_an_unknown_channel(client):
    response = client.post(
        "/api/applications",
        json={"company_name": "Stripe", "job_title": "Engineer", "channel": "carrier-pigeon"},
    )

    assert response.status_code == 400


def test_create_reports_a_duplicate_with_the_existing_id(client, monkeypatch):
    async def fake_create(*_args, **_kwargs):
        raise DuplicateApplicationError("app-existing")

    monkeypatch.setattr(applications_api.application_service, "create", fake_create)

    response = client.post("/api/applications", json={"user_job_match_id": "match-1"})

    assert response.status_code == 409
    # The UI uses this id to jump to the record the user already has.
    assert response.json()["detail"]["application_id"] == "app-existing"


def test_create_from_a_foreign_match_is_not_found(client, monkeypatch):
    async def fake_create(*_args, **_kwargs):
        raise MatchNotFoundError()

    monkeypatch.setattr(applications_api.application_service, "create", fake_create)

    response = client.post("/api/applications", json={"user_job_match_id": "match-x"})

    assert response.status_code == 404


def test_update_changes_the_stage(client, monkeypatch):
    application = build_application()
    captured = {}

    async def fake_get_owned(*_args, **_kwargs):
        return application

    async def fake_update(_db, target, changes):
        captured["changes"] = changes
        target.status = changes["status"]
        return target

    monkeypatch.setattr(applications_api.application_service, "get_owned", fake_get_owned)
    monkeypatch.setattr(applications_api.application_service, "update", fake_update)

    response = client.patch("/api/applications/app-1", json={"status": "interviewing"})

    assert response.status_code == 200
    assert response.json()["status"] == "interviewing"
    # Only the submitted field travels, so untouched columns are never overwritten.
    assert captured["changes"] == {"status": "interviewing"}


def test_update_rejects_blanking_the_company(client, monkeypatch):
    async def fake_get_owned(*_args, **_kwargs):
        return build_application()

    monkeypatch.setattr(applications_api.application_service, "get_owned", fake_get_owned)

    response = client.patch("/api/applications/app-1", json={"company_name": "   "})

    assert response.status_code == 400


def test_update_of_another_users_record_is_not_found(client, monkeypatch):
    async def fake_get_owned(*_args, **_kwargs):
        return None

    monkeypatch.setattr(applications_api.application_service, "get_owned", fake_get_owned)

    response = client.patch("/api/applications/app-someone-else", json={"status": "offer"})

    # 404, not 403: the response must not confirm the record exists.
    assert response.status_code == 404


def test_delete_removes_the_record(client, monkeypatch):
    application = build_application()

    async def fake_get_owned(*_args, **_kwargs):
        return application

    monkeypatch.setattr(applications_api.application_service, "get_owned", fake_get_owned)

    response = client.delete("/api/applications/app-1")

    assert response.status_code == 204
    assert client.session.deleted == [application]


def test_delete_of_another_users_record_is_not_found(client, monkeypatch):
    async def fake_get_owned(*_args, **_kwargs):
        return None

    monkeypatch.setattr(applications_api.application_service, "get_owned", fake_get_owned)

    response = client.delete("/api/applications/app-someone-else")

    assert response.status_code == 404
