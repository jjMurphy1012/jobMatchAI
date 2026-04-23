from collections import deque
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin as admin_api
from app.api import auth as auth_api
from app.api import jobs as jobs_api
from app.api import resume as resume_api
from app.api import tasks as tasks_api
from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Application, DailyTask, Opportunity, Resume, User, UserJobMatch
from app.services.storage_service import StoredFile


class FakeResult:
    def __init__(self, value=None, items=None):
        self.value = value
        self.items = items

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        if self.items is not None:
            return self.items
        if self.value is None:
            return []
        return [self.value]


class QueueSession:
    def __init__(self, *results):
        self.results = deque(results)
        self.added = []
        self.deleted = []
        self.committed = False
        self.flushed = False
        self.refreshed = []

    async def execute(self, _statement):
        if not self.results:
            raise AssertionError("No fake result queued for execute()")
        return self.results.popleft()

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed = True

    async def flush(self):
        self.flushed = True

    async def refresh(self, obj):
        if hasattr(obj, "uploaded_at") and getattr(obj, "uploaded_at", None) is None:
            obj.uploaded_at = datetime.now(timezone.utc)
        self.refreshed.append(obj)


class FakeStorageService:
    def __init__(self):
        self.uploaded = []
        self.deleted = []
        self.download_requests = []

    async def upload_resume(self, file_id: str, file_name: str, content: bytes) -> StoredFile:
        self.uploaded.append((file_id, file_name, content))
        return StoredFile(provider="supabase", bucket="resumes", path=f"resumes/{file_id}-{file_name}")

    async def create_download_url(self, stored_file: StoredFile) -> str:
        self.download_requests.append(stored_file)
        return f"https://download.test/{stored_file.path}"

    async def delete_file(self, stored_file: StoredFile) -> None:
        self.deleted.append(stored_file)


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


def test_google_callback_success_redirects_to_frontend_and_sets_cookies(monkeypatch):
    app = build_app(("/api/auth", auth_api.router))

    async def override_db():
        yield None

    app.dependency_overrides[get_db] = override_db

    bundle = SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
        user=User(id="user-1", email="user@example.com", role="user", is_disabled=False),
    )

    async def fake_exchange_code_for_tokens(code):
        return {"access_token": "google-token"}

    async def fake_fetch_google_profile(access_token):
        return SimpleNamespace(
            email="user@example.com",
            email_verified=True,
            sub="google-sub",
            name="Google User",
            picture=None,
        )

    async def fake_upsert_google_user(db, profile):
        return bundle.user

    async def fake_create_session(db, user, request):
        return bundle

    monkeypatch.setattr(auth_api.auth_service, "exchange_code_for_tokens", fake_exchange_code_for_tokens)
    monkeypatch.setattr(auth_api.auth_service, "fetch_google_profile", fake_fetch_google_profile)
    monkeypatch.setattr(auth_api.auth_service, "upsert_google_user", fake_upsert_google_user)
    monkeypatch.setattr(auth_api.auth_service, "create_session", fake_create_session)

    def fake_set_auth_cookies(response, bundle):
        response.set_cookie(settings.ACCESS_COOKIE_NAME, bundle.access_token)
        response.set_cookie(settings.REFRESH_COOKIE_NAME, bundle.refresh_token)

    monkeypatch.setattr(auth_api.auth_service, "set_auth_cookies", fake_set_auth_cookies)

    client = TestClient(app)
    client.cookies.set(settings.OAUTH_STATE_COOKIE_NAME, "expected-state")
    response = client.get(
        "/api/auth/google/callback?code=auth-code&state=expected-state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.FRONTEND_URL}/auth/callback"
    assert response.cookies.get(settings.ACCESS_COOKIE_NAME) == "access-token"
    assert response.cookies.get(settings.REFRESH_COOKIE_NAME) == "refresh-token"


def test_auth_me_refresh_and_logout(monkeypatch):
    user = User(id="user-1", email="user@example.com", name="Example User", role="admin", is_disabled=False)
    app = build_app(("/api/auth", auth_api.router))

    async def override_user():
        return user

    async def override_db():
        yield None

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    bundle = SimpleNamespace(access_token="new-access", refresh_token="new-refresh", user=user)
    async def fake_rotate_refresh_session(db, token, request):
        return bundle

    monkeypatch.setattr(auth_api.auth_service, "rotate_refresh_session", fake_rotate_refresh_session)

    revoked = {}

    async def fake_revoke(db, refresh_token):
        revoked["token"] = refresh_token

    monkeypatch.setattr(auth_api.auth_service, "revoke_refresh_session", fake_revoke)

    def fake_set_auth_cookies(response, auth_bundle):
        response.set_cookie(settings.ACCESS_COOKIE_NAME, auth_bundle.access_token)
        response.set_cookie(settings.REFRESH_COOKIE_NAME, auth_bundle.refresh_token)

    def fake_clear_auth_cookies(response):
        response.delete_cookie(settings.ACCESS_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME)

    monkeypatch.setattr(auth_api.auth_service, "set_auth_cookies", fake_set_auth_cookies)
    monkeypatch.setattr(auth_api.auth_service, "clear_auth_cookies", fake_clear_auth_cookies)

    client = TestClient(app)

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"

    client.cookies.set(settings.REFRESH_COOKIE_NAME, "existing-refresh")
    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.cookies.get(settings.ACCESS_COOKIE_NAME) == "new-access"
    assert refresh_response.cookies.get(settings.REFRESH_COOKIE_NAME) == "new-refresh"

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert revoked["token"] == "new-refresh"


def test_admin_list_users_and_update_roles():
    admin_user = User(id="admin-1", email="admin@example.com", role="admin", is_disabled=False)
    target_user = User(id="user-2", email="user@example.com", role="user", is_disabled=False)
    session = QueueSession(
        FakeResult(items=[target_user, admin_user]),
        FakeResult(value=target_user),
        FakeResult(value=admin_user),
    )
    app = build_app(("/api/admin", admin_api.router))

    async def override_db():
        yield session

    async def override_admin():
        return admin_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin] = override_admin

    client = TestClient(app)

    list_response = client.get("/api/admin/users")
    assert list_response.status_code == 200
    assert [user["email"] for user in list_response.json()] == ["user@example.com", "admin@example.com"]

    update_response = client.patch("/api/admin/users/user-2/role", json={"role": "admin"})
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "admin"
    assert target_user.role == "admin"
    assert session.flushed is True

    self_remove_response = client.patch("/api/admin/users/admin-1/role", json={"role": "user"})
    assert self_remove_response.status_code == 400
    assert self_remove_response.json()["detail"] == "You cannot remove your own admin role."


def test_resume_upload_get_and_delete(monkeypatch):
    user = User(id="user-1", email="user@example.com", role="user", is_disabled=False)
    existing_resume = Resume(
        id="resume-old",
        user_id="user-1",
        file_name="old.pdf",
        storage_provider="supabase",
        storage_bucket="resumes",
        storage_path="resumes/old.pdf",
        content="old resume content",
        uploaded_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    stored_resume = Resume(
        id="resume-new",
        user_id="user-1",
        file_name="resume.pdf",
        storage_provider="supabase",
        storage_bucket="resumes",
        storage_path="resumes/resume-new-resume.pdf",
        content="new resume content",
        uploaded_at=datetime.now(timezone.utc),
    )
    session = QueueSession(
        FakeResult(items=[existing_resume]),
        FakeResult(value=stored_resume),
        FakeResult(items=[stored_resume]),
    )
    storage = FakeStorageService()
    processed = {}

    class FakeRAGService:
        async def process_resume(self, content, file_id, db):
            processed["content"] = content
            processed["file_id"] = file_id

    app = build_app(("/api/resume", resume_api.router))

    async def override_db():
        yield session

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr(resume_api, "storage_service", storage)
    monkeypatch.setattr(resume_api, "RAGService", FakeRAGService)

    client = TestClient(app)
    upload_response = client.post(
        "/api/resume",
        files={"file": ("resume.pdf", b"%PDF fake", "application/pdf")},
    )

    assert upload_response.status_code == 200
    assert session.committed is True
    assert existing_resume in session.deleted
    assert processed["content"] == b"%PDF fake"
    assert storage.deleted[0].path == "resumes/old.pdf"

    get_response = client.get("/api/resume")
    assert get_response.status_code == 200
    assert get_response.json()["download_url"].startswith("https://download.test/")

    delete_response = client.delete("/api/resume")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Resume deleted successfully"
    assert storage.deleted[-1].path == "resumes/resume-new-resume.pdf"


def test_jobs_list_detail_and_apply():
    user = User(id="user-1", email="user@example.com", role="user", is_disabled=False)
    opportunity = Opportunity(
        id="opp-1",
        source_type="remotive",
        source_job_id="123",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        salary="$120k",
        url="https://example.com/job",
        description="Backend role",
    )
    application = Application(
        id="app-1",
        user_id="user-1",
        opportunity_id="opp-1",
        user_job_match_id="match-1",
        status="saved",
    )
    user_match = UserJobMatch(
        id="match-1",
        user_id="user-1",
        opportunity_id="opp-1",
        opportunity=opportunity,
        application=application,
        match_score=88,
        match_reason="Strong backend fit",
        matched_skills='["Python"]',
        missing_skills='["AWS"]',
        cover_letter="Dear hiring team",
        last_scored_at=datetime.now(timezone.utc),
    )
    session = QueueSession(
        FakeResult(items=[user_match]),
        FakeResult(value=1),
        FakeResult(value=user_match.last_scored_at),
        FakeResult(value=user_match),
        FakeResult(value=user_match),
    )
    app = build_app(("/api/jobs", jobs_api.router))

    async def override_db():
        yield session

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    client = TestClient(app)

    list_response = client.get("/api/jobs")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["jobs"][0]["title"] == "Backend Engineer"
    assert body["jobs"][0]["application_status"] == "saved"
    assert body["jobs"][0]["is_applied"] is False

    detail_response = client.get("/api/jobs/match-1")
    assert detail_response.status_code == 200
    assert detail_response.json()["company"] == "Acme"

    apply_response = client.put("/api/jobs/match-1/apply")
    assert apply_response.status_code == 200
    assert application.status == "applied"
    assert session.committed is True


def test_tasks_list_complete_uncomplete_and_stats():
    user = User(id="user-1", email="user@example.com", role="user", is_disabled=False)
    opportunity = Opportunity(
        id="opp-1",
        source_type="remotive",
        source_job_id="123",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        url="https://example.com/job",
        description="Backend role",
    )
    user_match = UserJobMatch(
        id="match-1",
        user_id="user-1",
        opportunity_id="opp-1",
        opportunity=opportunity,
        match_score=91,
        created_at=datetime.now(timezone.utc),
    )
    task = DailyTask(
        id="task-1",
        user_job_match_id="match-1",
        user_job_match=user_match,
        is_completed=False,
        task_order=0,
        date=datetime.now(timezone.utc),
    )
    session = QueueSession(
        FakeResult(items=[task]),
        FakeResult(value=task),
        FakeResult(items=[task]),
        FakeResult(value=task),
        FakeResult(items=[task]),
        FakeResult(items=[task]),
    )
    app = build_app(("/api/daily-tasks", tasks_api.router))

    async def override_db():
        yield session

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    client = TestClient(app)

    list_response = client.get("/api/daily-tasks")
    assert list_response.status_code == 200
    assert list_response.json()["tasks"][0]["job"]["title"] == "Backend Engineer"

    complete_response = client.put("/api/daily-tasks/task-1/complete")
    assert complete_response.status_code == 200
    assert task.is_completed is True
    created_application = session.added[0]
    assert isinstance(created_application, Application)
    assert created_application.status == "applied"

    existing_application = Application(
        id="app-1",
        user_id="user-1",
        opportunity_id="opp-1",
        user_job_match_id="match-1",
        status="applied",
    )
    user_match.application = existing_application
    uncomplete_response = client.put("/api/daily-tasks/task-1/uncomplete")
    assert uncomplete_response.status_code == 200
    assert task.is_completed is False
    assert existing_application.status == "saved"

    stats_response = client.get("/api/daily-tasks/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["today_total"] == 1
    assert stats_response.json()["today_remaining"] == 1
