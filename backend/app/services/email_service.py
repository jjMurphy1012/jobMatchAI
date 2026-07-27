from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any, Optional, Protocol
import asyncio
import logging

import httpx

from app.core.config import settings
from app.core.enums import NotificationStatus

logger = logging.getLogger(__name__)

SEND_ENDPOINT = "/v3/mail/send"

# SendGrid answers 202 on accept. Anything else in these sets decides retry vs give up.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    text_body: str
    html_body: str
    categories: list[str] = field(default_factory=list)


@dataclass
class EmailDeliveryResult:
    status: str
    attempts: int = 0
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def sent(self) -> bool:
        return self.status == NotificationStatus.SENT


@dataclass
class DigestJob:
    """One row in a daily digest email."""
    title: str
    company: str
    match_score: int
    location: Optional[str] = None
    url: Optional[str] = None
    match_reason: Optional[str] = None


class AsyncHttpClient(Protocol):
    async def post(self, url: str, *, json: Any, headers: dict[str, str]) -> httpx.Response:
        ...


class SendGridEmailService:
    """Sends transactional email through the SendGrid v3 API.

    The official SDK is synchronous, so this talks to the REST endpoint with the
    httpx client the rest of the project already depends on.
    """

    def __init__(self, client_factory=None, sleep=asyncio.sleep):
        self._client_factory = client_factory or self._default_client_factory
        self._sleep = sleep

    def _default_client_factory(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=settings.SENDGRID_TIMEOUT_SECONDS)

    def unconfigured_reason(self) -> Optional[str]:
        """Returns why sending is disabled, or None when the service can send."""
        if not settings.EMAIL_NOTIFICATIONS_ENABLED:
            return "EMAIL_NOTIFICATIONS_ENABLED is false"
        if not settings.SENDGRID_API_KEY:
            return "SENDGRID_API_KEY is not set"
        if not settings.SENDGRID_FROM_EMAIL:
            return "SENDGRID_FROM_EMAIL is not set"
        return None

    def _build_payload(self, message: EmailMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "personalizations": [{"to": [{"email": message.to_email}]}],
            "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDGRID_FROM_NAME},
            "subject": message.subject,
            "content": [
                # SendGrid requires text/plain before text/html.
                {"type": "text/plain", "value": message.text_body},
                {"type": "text/html", "value": message.html_body},
            ],
        }
        if message.categories:
            payload["categories"] = message.categories
        if settings.SENDGRID_SANDBOX_MODE:
            payload["mail_settings"] = {"sandbox_mode": {"enable": True}}
        return payload

    def _retry_delay(self, attempt: int, response: Optional[httpx.Response]) -> float:
        if response is not None:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
        return settings.EMAIL_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))

    async def send(self, message: EmailMessage) -> EmailDeliveryResult:
        reason = self.unconfigured_reason()
        if reason:
            logger.info("Skipping email to %s: %s", message.to_email, reason)
            return EmailDeliveryResult(status=NotificationStatus.SKIPPED, error_message=reason)

        payload = self._build_payload(message)
        headers = {
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{settings.SENDGRID_API_BASE_URL.rstrip('/')}{SEND_ENDPOINT}"
        max_attempts = max(1, settings.EMAIL_MAX_ATTEMPTS)
        last_error = "Email was never attempted"

        async with self._client_factory() as client:
            for attempt in range(1, max_attempts + 1):
                response = None
                try:
                    response = await client.post(url, json=payload, headers=headers)
                except httpx.HTTPError as exc:
                    last_error = f"Transport error: {exc}"
                else:
                    if response.status_code in (200, 202):
                        return EmailDeliveryResult(
                            status=NotificationStatus.SENT,
                            attempts=attempt,
                            provider_message_id=response.headers.get("x-message-id"),
                        )

                    last_error = f"SendGrid responded {response.status_code}: {_response_detail(response)}"

                    # 4xx other than 429 means the request itself is wrong (bad key,
                    # unverified sender, malformed recipient) — retrying only burns quota.
                    if response.status_code not in RETRYABLE_STATUS_CODES:
                        logger.error("SendGrid rejected the message: %s", last_error)
                        return EmailDeliveryResult(
                            status=NotificationStatus.FAILED,
                            attempts=attempt,
                            error_message=last_error,
                        )

                logger.warning("SendGrid attempt %s/%s failed: %s", attempt, max_attempts, last_error)
                if attempt == max_attempts:
                    break
                await self._sleep(self._retry_delay(attempt, response))

        return EmailDeliveryResult(
            status=NotificationStatus.FAILED,
            attempts=max_attempts,
            error_message=last_error,
        )


def _response_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]

    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors:
        messages = [str(error.get("message", "")) for error in errors if isinstance(error, dict)]
        joined = "; ".join(message for message in messages if message)
        if joined:
            return joined[:300]
    return str(body)[:300]


def render_daily_digest(
    jobs: list[DigestJob],
    *,
    to_email: str,
    recipient_name: Optional[str] = None,
    app_url: Optional[str] = None,
) -> EmailMessage:
    """Build the daily match digest. All job-supplied text is escaped before
    being interpolated into HTML — job descriptions come from external boards."""
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    subject = f"{len(jobs)} new job match{'es' if len(jobs) != 1 else ''} for you"
    dashboard_url = app_url or settings.FRONTEND_URL

    text_lines = [greeting, "", "Your latest matches:", ""]
    for index, job in enumerate(jobs, start=1):
        location = f" · {job.location}" if job.location else ""
        text_lines.append(f"{index}. {job.title} — {job.company}{location} ({job.match_score}%)")
        if job.match_reason:
            text_lines.append(f"   {job.match_reason}")
        if job.url:
            text_lines.append(f"   {job.url}")
        text_lines.append("")
    text_lines.append(f"Open the dashboard: {dashboard_url}")

    rows = []
    for job in jobs:
        title = escape(job.title or "")
        title_html = f'<a href="{escape(job.url, quote=True)}">{title}</a>' if job.url else title
        meta = escape(job.company or "")
        if job.location:
            meta = f"{meta} &middot; {escape(job.location)}"
        reason = f"<p>{escape(job.match_reason)}</p>" if job.match_reason else ""
        rows.append(
            "<li>"
            f"<strong>{title_html}</strong> &mdash; {job.match_score}%"
            f"<br><span>{meta}</span>{reason}"
            "</li>"
        )

    html_body = (
        "<html><body>"
        f"<p>{escape(greeting)}</p>"
        "<p>Your latest matches:</p>"
        f"<ol>{''.join(rows)}</ol>"
        f'<p><a href="{escape(dashboard_url, quote=True)}">Open the dashboard</a></p>'
        "</body></html>"
    )

    return EmailMessage(
        to_email=to_email,
        subject=subject,
        text_body="\n".join(text_lines),
        html_body=html_body,
        categories=["jobmatchai", "daily_digest"],
    )


def render_test_email(recipient: str) -> EmailMessage:
    return EmailMessage(
        to_email=recipient,
        subject="JobMatchAI test email",
        text_body=(
            "This is a test email from JobMatchAI.\n"
            "If you received it, SendGrid delivery is configured correctly."
        ),
        html_body=(
            "<html><body><p>This is a test email from JobMatchAI.</p>"
            "<p>If you received it, SendGrid delivery is configured correctly.</p>"
            "</body></html>"
        ),
        categories=["jobmatchai", "test"],
    )


email_service = SendGridEmailService()
