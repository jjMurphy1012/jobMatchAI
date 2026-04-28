from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import logging
import re
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SourceSyncStatus, SourceType
from app.models.models import CompanySource, Opportunity, SourceSyncRun

logger = logging.getLogger(__name__)


class SourceSyncError(Exception):
    """Raised when an external job source cannot be synced."""


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    without_tags = re.sub(r"<[^>]+>", " ", unescape(value))
    return _collapse_whitespace(without_tags) or None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _location_name(job: dict[str, Any]) -> str | None:
    location = job.get("location")
    if isinstance(location, dict):
        name = location.get("name")
        if name:
            return str(name)
    if isinstance(location, str) and location.strip():
        return location.strip()

    offices = job.get("offices")
    if isinstance(offices, list):
        names = [
            str(office.get("name")).strip()
            for office in offices
            if isinstance(office, dict) and office.get("name")
        ]
        if names:
            return ", ".join(names[:3])
    return None


def _salary_text(job: dict[str, Any]) -> str | None:
    salary = job.get("salary")
    if isinstance(salary, str) and salary.strip():
        return salary.strip()

    ranges = job.get("pay_input_ranges")
    if not isinstance(ranges, list) or not ranges:
        return None

    first_range = next((item for item in ranges if isinstance(item, dict)), None)
    if not first_range:
        return None

    minimum = first_range.get("min_value") or first_range.get("min")
    maximum = first_range.get("max_value") or first_range.get("max")
    currency = first_range.get("currency_type") or first_range.get("currency")
    interval = first_range.get("pay_period") or first_range.get("interval")

    if minimum and maximum:
        amount = f"{minimum}-{maximum}"
    elif minimum:
        amount = f"{minimum}+"
    elif maximum:
        amount = f"up to {maximum}"
    else:
        return None

    suffix = " ".join(str(part) for part in (currency, interval) if part)
    return f"{amount} {suffix}".strip()


def normalize_greenhouse_job(job: dict[str, Any], source: CompanySource) -> dict[str, Any] | None:
    external_id = job.get("id") or job.get("internal_job_id") or job.get("absolute_url")
    if external_id is None:
        return None

    title = str(job.get("title") or "").strip()
    if not title:
        return None

    source_job_id = f"{source.board_token}:{external_id}"
    description = _strip_html(job.get("content"))

    return {
        "company_source_id": source.id,
        "source_type": SourceType.GREENHOUSE,
        "source_job_id": source_job_id,
        "title": title,
        "company": source.company_name,
        "location": _location_name(job),
        "salary": _salary_text(job),
        "url": job.get("absolute_url"),
        "description": description,
        "raw_payload": job,
        "posted_at": _parse_datetime(job.get("updated_at")),
    }


class GreenhouseJobBoardClient:
    """Client for Greenhouse Job Board API."""

    def __init__(self, base_url: str = "https://boards-api.greenhouse.io/v1/boards") -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch_jobs(self, board_token: str) -> list[dict[str, Any]]:
        token = board_token.strip()
        if not token:
            raise SourceSyncError("Greenhouse board_token is required.")

        url = f"{self.base_url}/{quote(token, safe='')}/jobs"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, params={"content": "true"})

        if response.status_code == 404:
            raise SourceSyncError(f"Greenhouse board '{token}' was not found.")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SourceSyncError(f"Greenhouse returned HTTP {response.status_code}.") from exc

        data = response.json()
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            raise SourceSyncError("Greenhouse response did not include a jobs list.")
        return [job for job in jobs if isinstance(job, dict)]


class CompanySourceSyncService:
    """Sync external company sources into the shared opportunities table."""

    def __init__(self, greenhouse_client: GreenhouseJobBoardClient | None = None) -> None:
        self.greenhouse_client = greenhouse_client or GreenhouseJobBoardClient()

    async def sync_company_source(self, db: AsyncSession, source: CompanySource) -> SourceSyncRun:
        run = SourceSyncRun(
            id=str(uuid4()),
            company_source_id=source.id,
            source_type=source.source_type,
            status=SourceSyncStatus.RUNNING,
            fetched_count=0,
            upserted_count=0,
            closed_count=0,
        )
        db.add(run)
        await db.flush()

        try:
            if source.source_type != SourceType.GREENHOUSE:
                raise SourceSyncError(f"Unsupported source_type '{source.source_type}'.")
            if not source.is_active:
                raise SourceSyncError("Company source is inactive.")

            raw_jobs = await self.greenhouse_client.fetch_jobs(source.board_token)
            normalized_jobs = [
                job
                for raw_job in raw_jobs
                if (job := normalize_greenhouse_job(raw_job, source)) is not None
            ]

            now = datetime.now(timezone.utc)
            source_job_ids = {job["source_job_id"] for job in normalized_jobs}
            existing_by_id: dict[str, Opportunity] = {}

            if source_job_ids:
                existing_result = await db.execute(
                    select(Opportunity).where(
                        Opportunity.source_type == source.source_type,
                        Opportunity.source_job_id.in_(source_job_ids),
                    )
                )
                existing_by_id = {
                    opportunity.source_job_id: opportunity
                    for opportunity in existing_result.scalars().all()
                }

            for job in normalized_jobs:
                opportunity = existing_by_id.get(job["source_job_id"])
                if opportunity is None:
                    db.add(Opportunity(**job, is_open=True, first_seen_at=now, last_seen_at=now))
                else:
                    opportunity.company_source_id = source.id
                    opportunity.title = job["title"]
                    opportunity.company = job["company"]
                    opportunity.location = job["location"]
                    opportunity.salary = job["salary"]
                    opportunity.url = job["url"]
                    opportunity.description = job["description"]
                    opportunity.raw_payload = job["raw_payload"]
                    opportunity.posted_at = job["posted_at"] or opportunity.posted_at
                    opportunity.is_open = True
                    opportunity.last_seen_at = now

            open_result = await db.execute(
                select(Opportunity).where(
                    Opportunity.company_source_id == source.id,
                    Opportunity.source_type == source.source_type,
                    Opportunity.is_open.is_(True),
                )
            )
            for opportunity in open_result.scalars().all():
                if opportunity.source_job_id not in source_job_ids:
                    opportunity.is_open = False
                    run.closed_count += 1

            source.last_synced_at = now
            run.status = SourceSyncStatus.SUCCESS
            run.fetched_count = len(raw_jobs)
            run.upserted_count = len(normalized_jobs)
            run.finished_at = now
        except Exception as exc:
            logger.exception("Company source sync failed for %s", source.id)
            run.status = SourceSyncStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)

        await db.flush()
        return run
