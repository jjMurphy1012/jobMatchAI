"""remove legacy jobs and preference shadow columns

Revision ID: 20260504_000010
Revises: 20260428_000009
Create Date: 2026-05-04 00:00:10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260504_000010"
down_revision = "20260428_000009"
branch_labels = None
depends_on = None


JOB_PREFERENCE_LEGACY_COLUMNS = [
    "keywords",
    "location",
    "is_intern",
    "need_sponsor",
    "experience_level",
    "job_description",
    "remote_preference",
    "excluded_companies",
    "industries",
    "salary_min",
    "salary_max",
    "salary_currency",
]


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _has_table(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _drop_foreign_keys_for_columns(inspector: sa.Inspector, table_name: str, column_names: set[str]) -> None:
    if not _has_table(inspector, table_name):
        return
    for foreign_key in inspector.get_foreign_keys(table_name):
        if set(foreign_key.get("constrained_columns") or []) == column_names:
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "job_id" in _columns(inspector, "daily_tasks"):
        _drop_foreign_keys_for_columns(inspector, "daily_tasks", {"job_id"})
        op.drop_column("daily_tasks", "job_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "jobs"):
        op.drop_table("jobs")

    inspector = sa.inspect(bind)
    existing_preference_columns = _columns(inspector, "job_preferences")
    for column_name in JOB_PREFERENCE_LEGACY_COLUMNS:
        if column_name in existing_preference_columns:
            op.drop_column("job_preferences", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_preference_columns = _columns(inspector, "job_preferences")
    if "keywords" not in existing_preference_columns:
        op.add_column(
            "job_preferences",
            sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        )
    for column_name, column_type in [
        ("location", sa.String()),
        ("is_intern", sa.Boolean()),
        ("need_sponsor", sa.Boolean()),
        ("experience_level", sa.String()),
        ("job_description", sa.Text()),
        ("remote_preference", sa.String()),
        ("excluded_companies", sa.JSON()),
        ("industries", sa.JSON()),
        ("salary_min", sa.Integer()),
        ("salary_max", sa.Integer()),
        ("salary_currency", sa.String()),
    ]:
        if column_name not in existing_preference_columns:
            op.add_column("job_preferences", sa.Column(column_name, column_type, nullable=True))

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
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
            sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("linkedin_job_id", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "linkedin_job_id", name="uq_jobs_user_linkedin_job_id"),
        )
        op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)

    inspector = sa.inspect(bind)
    if "job_id" not in _columns(inspector, "daily_tasks"):
        op.add_column("daily_tasks", sa.Column("job_id", sa.String(), nullable=True))
        op.create_foreign_key(
            "fk_daily_tasks_job_id_jobs",
            "daily_tasks",
            "jobs",
            ["job_id"],
            ["id"],
            ondelete="CASCADE",
        )
