"""baseline schema

Revision ID: 20260422_000001
Revises:
Create Date: 2026-04-22 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "job_preferences" not in existing_tables:
        op.create_table(
            "job_preferences",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("keywords", sa.Text(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("is_intern", sa.Boolean(), nullable=True),
            sa.Column("need_sponsor", sa.Boolean(), nullable=True),
            sa.Column("experience_level", sa.String(), nullable=True),
            sa.Column("job_description", sa.Text(), nullable=True),
            sa.Column("remote_preference", sa.String(), nullable=True),
            sa.Column("reminder_enabled", sa.Boolean(), nullable=True),
            sa.Column("reminder_email", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "jobs" not in existing_tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("salary", sa.String(), nullable=True),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("match_score", sa.Integer(), nullable=False),
            sa.Column("match_reason", sa.Text(), nullable=True),
            sa.Column("matched_skills", sa.Text(), nullable=True),
            sa.Column("missing_skills", sa.Text(), nullable=True),
            sa.Column("cover_letter", sa.Text(), nullable=True),
            sa.Column("is_applied", sa.Boolean(), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("linkedin_job_id", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("linkedin_job_id"),
        )

    if "resumes" not in existing_tables:
        op.create_table(
            "resumes",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "daily_tasks" not in existing_tables:
        op.create_table(
            "daily_tasks",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("job_id", sa.String(), nullable=False),
            sa.Column("date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("is_completed", sa.Boolean(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("task_order", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "resume_chunks" not in existing_tables:
        op.create_table(
            "resume_chunks",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("resume_id", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("resume_chunks")
    op.drop_table("daily_tasks")
    op.drop_table("resumes")
    op.drop_table("jobs")
    op.drop_table("job_preferences")
