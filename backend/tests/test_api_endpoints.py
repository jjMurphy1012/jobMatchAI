from collections import deque

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.api import jobs as jobs_api
from app.api import preferences as preferences_api
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import JobPreference, Resume, User
from app.services.preference_extractor import (
    PreferenceAnalysisResult,
    PreferenceFieldOverrides,
    PreferenceStructuredFields,
)


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakePreferenceSession:
    def __init__(self) -> None:
        self.preference: JobPreference | None = None

    def add(self, preference: JobPreference) -> None:
        if not preference.id:
            preference.id = "pref-1"
        self.preference = preference

    async def commit(self) -> None:
        return None

    async def refresh(self, _obj) -> None:
        return None


class FakeJobsRefreshSession:
    def __init__(self, *results) -> None:
        self.results = deque(results)

    async def execute(self, _statement):
        return ScalarResult(self.results.popleft() if self.results else None)


def build_app(*routers) -> FastAPI:
    app = FastAPI()
    for prefix, router in routers:
        app.include_router(router, prefix=prefix)
    return app


@pytest.fixture(autouse=True)
def reset_auth_rate_limiter():
    auth_api.auth_rate_limiter.reset()
    yield
    auth_api.auth_rate_limiter.reset()


def test_google_login_sets_state_cookie_and_redirects(monkeypatch):
    app = build_app(("/api/auth", auth_api.router))

    async def override_db():
        yield None

    app.dependency_overrides[get_db] = override_db

    monkeypatch.setattr(
        auth_api.auth_service,
        "build_google_login_url",
        lambda state: f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
    )

    client = TestClient(app)
    response = client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?state=")
    assert response.cookies.get(settings.OAUTH_STATE_COOKIE_NAME)


def test_google_callback_is_rate_limited(monkeypatch):
    app = build_app(("/api/auth", auth_api.router))

    async def override_db():
        yield None

    app.dependency_overrides[get_db] = override_db

    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)

    client = TestClient(app)
    client.cookies.set(settings.OAUTH_STATE_COOKIE_NAME, "stored-state")
    for _ in range(2):
        response = client.get(
            "/api/auth/google/callback?code=fake-code&state=returned-state",
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}

    limited = client.get(
        "/api/auth/google/callback?code=fake-code&state=returned-state",
        follow_redirects=False,
    )

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Too many authentication attempts. Please try again later."


def test_preferences_round_trip_with_overrides(monkeypatch):
    session = FakePreferenceSession()
    user = User(id="user-1", email="user@example.com", role="user", is_disabled=False)
    app = build_app(("/api/preferences", preferences_api.router))

    async def override_db():
        yield session

    async def override_user():
        return user

    async def fake_get_current_preference(_db, _user_id):
        return session.preference

    async def fake_analyze(raw_text, overrides=None):
        extracted = PreferenceStructuredFields(
            keywords=["Backend"],
            locations=["New York, NY"],
            need_sponsor=True,
            remote_preference="hybrid",
        )
        effective = preferences_api.extractor_service.merge_fields(extracted, overrides)
        return PreferenceAnalysisResult(
            extracted_fields=extracted,
            effective_fields=effective,
            used_fallback=True,
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(preferences_api, "get_current_preference", fake_get_current_preference)
    monkeypatch.setattr(preferences_api.extractor_service, "analyze", fake_analyze)

    client = TestClient(app)

    create_response = client.post(
        "/api/preferences",
        json={
            "raw_text": "Looking for backend roles in New York with sponsorship.",
            "reminder_enabled": True,
            "reminder_email": "user@example.com",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["raw_text"].startswith("Looking for backend roles")
    assert created["extracted_fields"]["keywords"] == ["Backend"]
    assert created["effective_fields"]["need_sponsor"] is True

    patch_response = client.patch(
        "/api/preferences/fields",
        json={
            "override_fields": {
                "keywords": ["Backend", "Go"],
                "locations": ["Remote"],
            }
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["extracted_fields"]["keywords"] == ["Backend"]
    assert patched["override_fields"]["keywords"] == ["Backend", "Go"]
    assert patched["effective_fields"]["keywords"] == ["Backend", "Go"]
    assert patched["effective_fields"]["locations"] == ["Remote"]

    get_response = client.get("/api/preferences")
    assert get_response.status_code == 200
    current = get_response.json()
    assert current["effective_fields"]["keywords"] == ["Backend", "Go"]
    assert current["reminder_email"] == "user@example.com"


def test_jobs_refresh_runs_synchronously(monkeypatch):
    session = FakeJobsRefreshSession(
        Resume(user_id="user-1", file_name="resume.pdf"),
        JobPreference(user_id="user-1", keywords="Backend"),
    )
    user = User(id="user-1", email="user@example.com", role="user", is_disabled=False)
    app = build_app(("/api/jobs", jobs_api.router))

    async def override_db():
        yield session

    async def override_user():
        return user

    async def fake_run_job_search(user_id: str):
        assert user_id == "user-1"
        return {"success": True, "jobs_found": 4, "final_threshold": 65}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(jobs_api, "run_job_search", fake_run_job_search)

    client = TestClient(app)
    response = client.post("/api/jobs/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Job search completed with 4 matched jobs.",
        "status": "completed",
        "jobs_found": 4,
        "final_threshold": 65,
    }
