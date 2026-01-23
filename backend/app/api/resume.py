from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import os
import uuid

from app.core.database import get_db
from app.models.models import Resume
from app.services.rag_service import RAGService

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ResumeResponse(BaseModel):
    id: str
    file_name: str
    uploaded_at: str
    content_preview: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF resume."""
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Delete existing resume (single user mode)
    existing = await db.execute(select(Resume))
    for resume in existing.scalars().all():
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        await db.delete(resume)

    # Create resume record
    resume = Resume(
        id=file_id,
        file_path=file_path,
        file_name=file.filename
    )
    db.add(resume)
    await db.flush()

    # Process with RAG service
    rag_service = RAGService()
    try:
        result = await rag_service.process_resume(file_path, file_id, db)
        resume.content = result.get("content_preview", "")
    except Exception as e:
        # Log error but don't fail the upload
        print(f"RAG processing error: {e}")

    await db.commit()
    await db.refresh(resume)

    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        uploaded_at=resume.uploaded_at.isoformat(),
        content_preview=resume.content[:500] if resume.content else None
    )


@router.get("", response_model=Optional[ResumeResponse])
async def get_resume(db: AsyncSession = Depends(get_db)):
    """Get the current resume."""
    result = await db.execute(select(Resume).order_by(Resume.uploaded_at.desc()))
    resume = result.scalar_one_or_none()

    if not resume:
        return None

    return ResumeResponse(
        id=resume.id,
        file_name=resume.file_name,
        uploaded_at=resume.uploaded_at.isoformat(),
        content_preview=resume.content[:500] if resume.content else None
    )


@router.delete("")
async def delete_resume(db: AsyncSession = Depends(get_db)):
    """Delete the current resume."""
    result = await db.execute(select(Resume))
    resumes = result.scalars().all()

    if not resumes:
        raise HTTPException(status_code=404, detail="No resume found")

    for resume in resumes:
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        await db.delete(resume)

    await db.commit()
    return {"message": "Resume deleted successfully"}
