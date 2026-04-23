from typing import Optional
import asyncio
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Resume, User
from app.services.rag_service import RAGService
from app.services.storage_service import StoredFile, get_storage_service

router = APIRouter()

storage_service = get_storage_service()
logger = logging.getLogger(__name__)


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    uploaded_at: str
    content_preview: Optional[str] = None
    storage_provider: Optional[str] = None
    download_url: Optional[str] = None


def _stored_file_from_resume(resume: Resume) -> Optional[StoredFile]:
    path = resume.storage_path or resume.file_path
    if not path:
        return None

    return StoredFile(
        provider=resume.storage_provider or "local",
        bucket=resume.storage_bucket,
        path=path,
    )


async def serialize_resume(resume: Resume) -> ResumeResponse:
    stored_file = _stored_file_from_resume(resume)
    download_url = None
    if stored_file:
        download_url = await storage_service.create_download_url(stored_file)

    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        uploaded_at=resume.uploaded_at.isoformat(),
        content_preview=resume.content[:500] if resume.content else None,
        storage_provider=resume.storage_provider,
        download_url=download_url,
    )


async def _delete_stored_files(stored_files: list[StoredFile]) -> None:
    if not stored_files:
        return

    results = await asyncio.gather(
        *(storage_service.delete_file(stored_file) for stored_file in stored_files),
        return_exceptions=True,
    )
    for stored_file, result in zip(stored_files, results):
        if isinstance(result, Exception):
            logger.warning("Failed to delete stored file %s from %s: %s", stored_file.path, stored_file.provider, result)


@router.post("", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF resume."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = str(uuid.uuid4())
    content = await file.read()
    stored_file = await storage_service.upload_resume(file_id, file.filename, content)

    existing = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    existing_resumes = existing.scalars().all()
    stale_files = [
        stored
        for stored in (_stored_file_from_resume(r) for r in existing_resumes)
        if stored
    ]
    for resume in existing_resumes:
        await db.delete(resume)

    resume = Resume(
        id=file_id,
        user_id=current_user.id,
        file_path=stored_file.path if stored_file.provider == "local" else None,
        storage_provider=stored_file.provider,
        storage_bucket=stored_file.bucket,
        storage_path=stored_file.path,
        file_name=file.filename,
    )
    db.add(resume)
    try:
        await db.flush()

        rag_service = RAGService()
        try:
            await rag_service.process_resume(content, file_id, db)
        except Exception as exc:
            logger.warning("RAG processing error for resume %s: %s", file_id, exc)

        await db.commit()
        await db.refresh(resume)
    except Exception:
        await storage_service.delete_file(stored_file)
        raise

    await _delete_stored_files(stale_files)

    return await serialize_resume(resume)


@router.get("", response_model=Optional[ResumeResponse])
async def get_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current resume."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
    )
    resume = result.scalar_one_or_none()

    if not resume:
        return None

    return await serialize_resume(resume)


@router.delete("")
async def delete_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the current resume."""
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resumes = result.scalars().all()

    if not resumes:
        raise HTTPException(status_code=404, detail="No resume found")

    stored_files = [
        stored
        for stored in (_stored_file_from_resume(r) for r in resumes)
        if stored
    ]
    for resume in resumes:
        await db.delete(resume)

    await db.commit()
    await _delete_stored_files(stored_files)
    return {"message": "Resume deleted successfully"}
