from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import uuid

EMBEDDING_DIM = 1536
VECTOR_TYPE = Vector(EMBEDDING_DIM)


def generate_uuid():
    return str(uuid.uuid4())


class Resume(Base):
    """Resume model with vector embedding for RAG."""
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    file_path = Column(String, nullable=True)
    storage_provider = Column(String, nullable=True)
    storage_bucket = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    content = Column(Text, nullable=True)  # Parsed text content
    embedding = Column(VECTOR_TYPE, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="resumes")
    chunks = relationship("ResumeChunk", back_populates="resume", cascade="all, delete-orphan")


class ResumeChunk(Base):
    """Individual chunks of resume for better RAG retrieval."""
    __tablename__ = "resume_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VECTOR_TYPE, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    resume = relationship("Resume", back_populates="chunks")


class JobPreference(Base):
    """User's job search preferences."""
    __tablename__ = "job_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_job_preferences_user_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Job criteria
    keywords = Column(Text, nullable=False)  # Comma-separated keywords
    location = Column(String, nullable=True)
    is_intern = Column(Boolean, default=False)
    need_sponsor = Column(Boolean, default=False)
    experience_level = Column(String, nullable=True)  # entry, mid, senior

    # Additional preferences
    job_description = Column(Text, nullable=True)  # User's target job description
    remote_preference = Column(String, nullable=True)  # remote, hybrid, onsite

    # Free-form profile + extracted signals
    raw_text = Column(Text, nullable=True)
    extracted_fields = Column(JSON, nullable=True)
    override_fields = Column(JSON, nullable=True)
    effective_fields = Column(JSON, nullable=True)
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    extraction_version = Column(String, nullable=True)
    excluded_companies = Column(JSON, nullable=True)
    industries = Column(JSON, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String, nullable=True)

    # Notification settings
    reminder_enabled = Column(Boolean, default=True)
    reminder_email = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="job_preferences")


class Job(Base):
    """Matched job positions."""
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "linkedin_job_id", name="uq_jobs_user_linkedin_job_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

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
    linkedin_job_id = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
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


class User(Base):
    """Authenticated application user."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    is_disabled = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    auth_accounts = relationship("AuthAccount", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    job_preferences = relationship("JobPreference", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class AuthAccount(Base):
    """External identity linked to a user."""
    __tablename__ = "auth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_sub", name="uq_auth_accounts_provider_sub"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    provider_sub = Column(String, nullable=False)
    provider_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="auth_accounts")


class UserSession(Base):
    """Refresh-token backed session for cookie authentication."""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = Column(String, nullable=False, unique=True, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
