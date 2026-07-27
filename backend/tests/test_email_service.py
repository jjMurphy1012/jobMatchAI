from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.core.enums import NotificationStatus
from app.services.email_service import (
    DigestJob,
    EmailMessage,
    SendGridEmailService,
    render_daily_digest,
)


class FakeResponse:
    def __init__(self, status_code: int, headers: dict | None = None, payload=None, text: str = ""):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON payload")
        return self._payload


class FakeClient:
    """Stands in for httpx.AsyncClient and records every request it receives."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return False

    async def post(self, url, *, json, headers):
        self.requests.append(SimpleNamespace(url=url, json=json, headers=headers))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def build_service(responses, sleeps=None):
    client = FakeClient(responses)

    async def fake_sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)

    service = SendGridEmailService(client_factory=lambda: client, sleep=fake_sleep)
    return service, client


def sample_message() -> EmailMessage:
    return EmailMessage(
        to_email="user@example.com",
        subject="Your matches",
        text_body="text",
        html_body="<p>html</p>",
        categories=["jobmatchai"],
    )


@pytest.fixture(autouse=True)
def enable_email(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True)
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "sg-test-key")
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "jobs@example.com")
    monkeypatch.setattr(settings, "SENDGRID_API_BASE_URL", "https://api.sendgrid.test")
    monkeypatch.setattr(settings, "EMAIL_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "EMAIL_RETRY_BACKOFF_SECONDS", 1.0)
    monkeypatch.setattr(settings, "SENDGRID_SANDBOX_MODE", False)


@pytest.mark.asyncio
async def test_send_returns_sent_with_provider_message_id():
    service, client = build_service([FakeResponse(202, {"x-message-id": "msg-123"})])

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.SENT
    assert result.attempts == 1
    assert result.provider_message_id == "msg-123"

    request = client.requests[0]
    assert request.url == "https://api.sendgrid.test/v3/mail/send"
    assert request.headers["Authorization"] == "Bearer sg-test-key"
    assert request.json["personalizations"] == [{"to": [{"email": "user@example.com"}]}]
    # SendGrid requires text/plain to come before text/html.
    assert [item["type"] for item in request.json["content"]] == ["text/plain", "text/html"]


@pytest.mark.asyncio
async def test_send_retries_server_errors_then_succeeds():
    sleeps = []
    service, client = build_service(
        [FakeResponse(503), FakeResponse(202, {"x-message-id": "msg-9"})],
        sleeps=sleeps,
    )

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.SENT
    assert result.attempts == 2
    assert len(client.requests) == 2
    assert sleeps == [1.0]


@pytest.mark.asyncio
async def test_send_honors_retry_after_header():
    sleeps = []
    service, _ = build_service(
        [FakeResponse(429, {"retry-after": "7"}), FakeResponse(202)],
        sleeps=sleeps,
    )

    result = await service.send(sample_message())

    assert result.sent
    assert sleeps == [7.0]


@pytest.mark.asyncio
async def test_send_does_not_retry_client_errors():
    service, client = build_service(
        [FakeResponse(401, payload={"errors": [{"message": "Bad API key"}]})]
    )

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.FAILED
    assert result.attempts == 1
    assert "Bad API key" in result.error_message
    # A wrong key never becomes right on retry — one call only.
    assert len(client.requests) == 1


@pytest.mark.asyncio
async def test_send_gives_up_after_max_attempts():
    sleeps = []
    service, client = build_service([FakeResponse(500)] * 3, sleeps=sleeps)

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.FAILED
    assert result.attempts == 3
    assert len(client.requests) == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.asyncio
async def test_send_retries_transport_errors():
    service, client = build_service(
        [httpx.ConnectError("connection reset"), FakeResponse(202)]
    )

    result = await service.send(sample_message())

    assert result.sent
    assert len(client.requests) == 2


@pytest.mark.asyncio
async def test_send_skips_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False)
    service, client = build_service([FakeResponse(202)])

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.SKIPPED
    assert client.requests == []


@pytest.mark.asyncio
async def test_send_skips_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", None)
    service, client = build_service([FakeResponse(202)])

    result = await service.send(sample_message())

    assert result.status == NotificationStatus.SKIPPED
    assert "SENDGRID_API_KEY" in result.error_message
    assert client.requests == []


@pytest.mark.asyncio
async def test_sandbox_mode_is_declared_in_payload(monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_SANDBOX_MODE", True)
    service, client = build_service([FakeResponse(202)])

    await service.send(sample_message())

    assert client.requests[0].json["mail_settings"] == {"sandbox_mode": {"enable": True}}


def test_render_daily_digest_escapes_job_text():
    jobs = [
        DigestJob(
            title="Engineer <script>alert(1)</script>",
            company="Acme & Co",
            match_score=91,
            location="Boston, MA",
            url="https://boards.test/jobs/1",
            match_reason="Python & FastAPI overlap",
        )
    ]

    message = render_daily_digest(jobs, to_email="user@example.com", recipient_name="Jiajun")

    assert message.to_email == "user@example.com"
    assert message.subject == "1 new job match for you"
    assert "<script>" not in message.html_body
    assert "&lt;script&gt;" in message.html_body
    assert "Acme &amp; Co" in message.html_body
    assert 'href="https://boards.test/jobs/1"' in message.html_body
    # Plain-text part stays human readable, not escaped.
    assert "Engineer <script>alert(1)</script>" in message.text_body
    assert "91%" in message.text_body


def test_render_daily_digest_pluralizes_subject():
    jobs = [
        DigestJob(title="A", company="X", match_score=80),
        DigestJob(title="B", company="Y", match_score=70),
    ]

    message = render_daily_digest(jobs, to_email="user@example.com")

    assert message.subject == "2 new job matches for you"
    assert message.categories == ["jobmatchai", "daily_digest"]
