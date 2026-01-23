from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Resume(Base):
    """Resume model with vector embedding for RAG."""
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    content = Column(Text, nullable=True)  # Parsed text content
    embedding = Column(Vector(1536), nullable=True)  # OpenAI ada-002 dimension
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    chunks = relationship("ResumeChunk", back_populates="resume", cascade="all, delete-orphan")


class ResumeChunk(Base):
    """Individual chunks of resume for better RAG retrieval."""
    __tablename__ = "resume_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    resume = relationship("Resume", back_populates="chunks")


class JobPreference(Base):
    """User's job search preferences."""
    __tablename__ = "job_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Job criteria
    keywords = Column(Text, nullable=False)  # Comma-separated keywords
    location = Column(String, nullable=True)
    is_intern = Column(Boolean, default=False)
    need_sponsor = Column(Boolean, default=False)
    experience_level = Column(String, nullable=True)  # entry, mid, senior

    # Additional preferences
    job_description = Column(Text, nullable=True)  # User's target job description
    remote_preference = Column(String, nullable=True)  # remote, hybrid, onsite

    # Notification settings
    reminder_enabled = Column(Boolean, default=True)
    reminder_email = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    """Matched job positions."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)

    # Job info
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    url = Column(String, nullable=True)  # LinkedIn job URL
    description = Column(Text, nullable=True)

    # Match analysis
    match_score = Column(Integer, nullable=False)
    match_reason = Column(Text, nullable=True)
    matched_skills = Column(Text, nullable=True)  # JSON string
    missing_skills = Column(Text, nullable=True)  # JSON string

    # Generated content
    cover_letter = Column(Text, nullable=True)

    # Status
    is_applied = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    searched_at = Column(DateTime(timezone=True), server_default=func.now())
    linkedin_job_id = Column(String, nullable=True, unique=True)

    # Relationships
    daily_task = relationship("DailyTask", back_populates="job", uselist=False)


class DailyTask(Base):
    """Daily application tasks."""
    __tablename__ = "daily_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Task status
    date = Column(DateTime(timezone=True), server_default=func.now())
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Order in the daily list
    task_order = Column(Integer, nullable=False, default=0)

    # Relationships
    job = relationship("Job", back_populates="daily_task")
