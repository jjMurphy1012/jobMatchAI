from __future__ import annotations

from datetime import date, datetime
from typing import Optional
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.enums import (
    APPLICATION_CHANNELS,
    APPLICATION_EVENT_KINDS,
    APPLICATION_STATUSES,
    JOB_TYPES,
    REGIONS,
    ApplicationChannel,
    ApplicationEventKind,
    ApplicationStatus,
)
from app.models.models import Application, User
from app.services.application_service import (
    ApplicationError,
    ApplicationInput,
    DuplicateApplicationError,
    MatchNotFoundError,
    application_service,
)

router = APIRouter()


class ApplicationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    occurred_on: date
    label: Optional[str]
    note: Optional[str]


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    job_title: str
    location: Optional[str]
    job_url: Optional[str]
    job_type: Optional[str]
    season: Optional[str]
    region: Optional[str]
    channel: str
    status: str
    events: list[ApplicationEventResponse] = []
    applied_at: Optional[datetime]
    notes: Optional[str]
    opportunity_id: Optional[str]
    user_job_match_id: Optional[str]
    status_updated_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationResponse]
    status_counts: dict[str, int]
    total: int


class ApplicationFields(BaseModel):
    """Fields shared by create and update. Everything is optional here: create
    requires company/title only when no match supplies them, which the service
    decides."""

    company_name: Optional[str] = Field(default=None, max_length=200)
    job_title: Optional[str] = Field(default=None, max_length=300)
    location: Optional[str] = Field(default=None, max_length=200)
    job_url: Optional[str] = Field(default=None, max_length=1000)
    job_type: Optional[str] = None
    season: Optional[str] = Field(default=None, max_length=40)
    region: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    applied_at: Optional[datetime] = None
    notes: Optional[str] = None


class ApplicationCreateRequest(ApplicationFields):
    """Pass `user_job_match_id` to file a matched job (details are copied from
    it), or the fields directly for a manual entry."""

    user_job_match_id: Optional[str] = None
    channel: str = ApplicationChannel.ONLINE
    status: str = ApplicationStatus.APPLIED


class ApplicationUpdateRequest(ApplicationFields):
    pass


class ApplicationEventRequest(BaseModel):
    kind: str = ApplicationEventKind.ASSESSMENT
    occurred_on: date
    label: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = None


def _validate_choice(value: Optional[str], allowed: frozenset[str], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"{field} must be one of: {', '.join(sorted(allowed))}.",
        )


def _validate_payload(payload: ApplicationCreateRequest | ApplicationUpdateRequest) -> None:
    _validate_choice(payload.status, APPLICATION_STATUSES, "status")
    _validate_choice(payload.channel, APPLICATION_CHANNELS, "channel")
    _validate_choice(payload.job_type, JOB_TYPES, "job_type")
    _validate_choice(payload.region, REGIONS, "region")


def _validate_query_filters(status, job_type, channel, region) -> None:
    _validate_choice(status, APPLICATION_STATUSES, "status")
    _validate_choice(channel, APPLICATION_CHANNELS, "channel")
    _validate_choice(job_type, JOB_TYPES, "job_type")
    _validate_choice(region, REGIONS, "region")


async def _get_owned_or_404(db: AsyncSession, user_id: str, application_id: str) -> Application:
    application = await application_service.get_owned(db, user_id, application_id)
    if application is None:
        # 404 rather than 403 so the response cannot confirm the record exists.
        raise HTTPException(status_code=404, detail="Application not found.")
    return application


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    channel: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    search_field: str = Query(default="company", pattern="^(company|role)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_query_filters(status, job_type, channel, region)

    applications = await application_service.list_for_user(
        db,
        current_user.id,
        status=status,
        job_type=job_type,
        channel=channel,
        region=region,
        search=search,
        search_field=search_field,
        limit=limit,
        offset=offset,
    )
    status_counts = await application_service.count_by_status(
        db,
        current_user.id,
        job_type=job_type,
        channel=channel,
        region=region,
        search=search,
        search_field=search_field,
    )

    return ApplicationListResponse(
        applications=[ApplicationResponse.model_validate(item) for item in applications],
        status_counts=status_counts,
        total=sum(status_counts.values()),
    )


@router.get("/export")
async def export_applications(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    channel: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    search_field: str = Query(default="company", pattern="^(company|role)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """CSV of everything the current filters select, not just the visible page."""
    _validate_query_filters(status, job_type, channel, region)

    applications = await application_service.list_for_user(
        db,
        current_user.id,
        status=status,
        job_type=job_type,
        channel=channel,
        region=region,
        search=search,
        search_field=search_field,
        limit=1000,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Company", "Role", "Location", "Region", "Type", "Season", "Channel",
         "Stage", "Applied", "Assessment", "Interview", "Link", "Notes"]
    )
    for item in applications:
        latest = _latest_event_dates(item)
        writer.writerow([
            item.company_name,
            item.job_title,
            item.location or "",
            item.region or "",
            item.job_type or "",
            item.season or "",
            item.channel,
            item.status,
            latest.get(ApplicationEventKind.APPLIED, ""),
            latest.get(ApplicationEventKind.ASSESSMENT, ""),
            latest.get(ApplicationEventKind.INTERVIEW, ""),
            item.job_url or "",
            (item.notes or "").replace("\n", " "),
        ])

    buffer.seek(0)
    filename = f"applications-{datetime.now().date()}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _latest_event_dates(application: Application) -> dict[str, str]:
    latest: dict[str, str] = {}
    for event in application.events:
        current = latest.get(event.kind)
        stamp = event.occurred_on.isoformat()
        if current is None or stamp > current:
            latest[event.kind] = stamp
    return latest


@router.post("", response_model=ApplicationResponse, status_code=http_status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_payload(payload)

    try:
        application = await application_service.create(
            db,
            current_user.id,
            ApplicationInput(**payload.model_dump()),
        )
    except MatchNotFoundError:
        raise HTTPException(status_code=404, detail="Match not found.")
    except DuplicateApplicationError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This match is already in your applications.",
                "application_id": exc.application_id,
            },
        )
    except ApplicationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ApplicationResponse.model_validate(application)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    payload: ApplicationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_payload(payload)
    application = await _get_owned_or_404(db, current_user.id, application_id)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return ApplicationResponse.model_validate(application)

    try:
        updated = await application_service.update(db, application, changes)
    except ApplicationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ApplicationResponse.model_validate(updated)


@router.post("/{application_id}/events", response_model=ApplicationResponse)
async def add_application_event(
    application_id: str,
    payload: ApplicationEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_choice(payload.kind, APPLICATION_EVENT_KINDS, "kind")
    application = await _get_owned_or_404(db, current_user.id, application_id)

    updated = await application_service.add_event(
        db,
        application,
        kind=payload.kind,
        occurred_on=payload.occurred_on,
        label=payload.label,
        note=payload.note,
    )
    return ApplicationResponse.model_validate(updated)


@router.delete("/{application_id}/events/{event_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_application_event(
    application_id: str,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_owned_or_404(db, current_user.id, application_id)
    if not await application_service.delete_event(db, application, event_id):
        raise HTTPException(status_code=404, detail="Event not found.")


@router.delete("/{application_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_owned_or_404(db, current_user.id, application_id)
    await db.delete(application)
