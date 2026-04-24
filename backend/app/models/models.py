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
    content = Column(Text, nullable=True)
    embedding = Column(VECTOR_TYPE, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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

    resume = relationship("Resume", back_populates="chunks")


class JobPreference(Base):
    """User's job search preferences."""
    __tablename__ = "job_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_job_preferences_user_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Legacy structured fields — kept for backfill and agent_service reads.
    # New writers populate raw_text + effective_fields; a follow-up migration will drop these.
    keywords = Column(Text, nullable=False)  # Comma-separated
    location = Column(String, nullable=True)
    is_intern = Column(Boolean, default=False)
    need_sponsor = Column(Boolean, default=False)
    experience_level = Column(String, nullable=True)
    job_description = Column(Text, nullable=True)
    remote_preference = Column(String, nullable=True)

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

    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    match_score = Column(Integer, nullable=False)
    match_reason = Column(Text, nullable=True)
    matched_skills = Column(Text, nullable=True)  # JSON-encoded list[str]
    missing_skills = Column(Text, nullable=True)  # JSON-encoded list[str]

    cover_letter = Column(Text, nullable=True)

    is_applied = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    searched_at = Column(DateTime(timezone=True), server_default=func.now())
    linkedin_job_id = Column(String, nullable=True)

    user = relationship("User", back_populates="jobs")
    daily_task = relationship("DailyTask", back_populates="job", uselist=False)


class Opportunity(Base):
    """Global job opportunity shared across users."""
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("source_type", "source_job_id", name="uq_opportunities_source_job"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    source_type = Column(String, nullable=False)
    source_job_id = Column(String, nullable=False)

    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    raw_payload = Column(JSON, nullable=True)

    is_open = Column(Boolean, nullable=False, default=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_job_matches = relationship("UserJobMatch", back_populates="opportunity", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="opportunity", cascade="all, delete-orphan")


class UserJobMatch(Base):
    """User-specific evaluation of an opportunity."""
    __tablename__ = "user_job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_user_job_matches_user_opportunity"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)

    match_score = Column(Integer, nullable=False)
    match_reason = Column(Text, nullable=True)
    matched_skills = Column(Text, nullable=True)
    missing_skills = Column(Text, nullable=True)
    cover_letter = Column(Text, nullable=True)

    last_scored_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_job_matches")
    opportunity = relationship("Opportunity", back_populates="user_job_matches")
    daily_tasks = relationship("DailyTask", back_populates="user_job_match", cascade="all, delete-orphan")
    application = relationship("Application", back_populates="user_job_match", uselist=False, cascade="all, delete-orphan")


class Application(Base):
    """Persistent application lifecycle state for a user and opportunity."""
    __tablename__ = "applications"
    __table_args__ = (
        # user_job_match_id uniqueness implies (user_id, opportunity_id) uniqueness
        # via UserJobMatch.uq_user_job_matches_user_opportunity — no separate constraint needed.
        UniqueConstraint("user_job_match_id", name="uq_applications_user_job_match"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(String, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_job_match_id = Column(String, ForeignKey("user_job_matches.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String, nullable=False, default="saved")
    applied_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="applications")
    opportunity = relationship("Opportunity", back_populates="applications")
    user_job_match = relationship("UserJobMatch", back_populates="application")


class InterviewExperience(Base):
    """Curated interview experience content related to jobs and companies."""
    __tablename__ = "interview_experiences"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_name = Column(String, nullable=False)
    company_name_normalized = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    level = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    rounds = Column(Text, nullable=True)
    topics = Column(JSON, nullable=True)
    summary = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    source_site = Column(String, nullable=True)
    review_status = Column(String, nullable=False, default="draft")
    relevance_keywords = Column(JSON, nullable=True)
    created_by_user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_interview_experiences")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id], back_populates="reviewed_interview_experiences")


class DailyTask(Base):
    """Daily application tasks."""
    __tablename__ = "daily_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)
    user_job_match_id = Column(String, ForeignKey("user_job_matches.id", ondelete="CASCADE"), nullable=True, index=True)

    date = Column(DateTime(timezone=True), server_default=func.now())
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    task_order = Column(Integer, nullable=False, default=0)

    job = relationship("Job", back_populates="daily_task")
    user_job_match = relationship("UserJobMatch", back_populates="daily_tasks")


class User(Base):
    """Authenticated application user."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
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
    user_job_matches = relationship("UserJobMatch", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    created_interview_experiences = relationship(
        "InterviewExperience",
        foreign_keys="InterviewExperience.created_by_user_id",
        back_populates="created_by_user",
    )
    reviewed_interview_experiences = relationship(
        "InterviewExperience",
        foreign_keys="InterviewExperience.reviewed_by_user_id",
        back_populates="reviewed_by_user",
    )


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
