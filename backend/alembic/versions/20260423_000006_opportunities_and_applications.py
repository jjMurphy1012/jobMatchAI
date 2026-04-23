"""add opportunities, user_job_matches, and applications

Revision ID: 20260423_000006
Revises: 20260423_000005
Create Date: 2026-04-23 00:00:06
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260423_000006"
down_revision = "20260423_000005"
branch_labels = None
depends_on = None


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        foreign_key["name"] == constraint_name
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def _parse_legacy_source(linkedin_job_id: str | None, fallback_id: str) -> tuple[str, str]:
    if not linkedin_job_id:
        return "legacy", fallback_id
    if "-" in linkedin_job_id:
        source_type, source_job_id = linkedin_job_id.split("-", 1)
        return source_type or "legacy", source_job_id or fallback_id
    return "legacy", linkedin_job_id


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "opportunities" not in existing_tables:
        op.create_table(
            "opportunities",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("source_job_id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("company", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("salary", sa.String(), nullable=True),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_type", "source_job_id", name="uq_opportunities_source_job"),
        )

    if "user_job_matches" not in existing_tables:
        op.create_table(
            "user_job_matches",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("match_score", sa.Integer(), nullable=False),
            sa.Column("match_reason", sa.Text(), nullable=True),
            sa.Column("matched_skills", sa.Text(), nullable=True),
            sa.Column("missing_skills", sa.Text(), nullable=True),
            sa.Column("cover_letter", sa.Text(), nullable=True),
            sa.Column("last_scored_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_job_matches_user_opportunity"),
        )
        op.create_index("ix_user_job_matches_user_id", "user_job_matches", ["user_id"], unique=False)
        op.create_index("ix_user_job_matches_opportunity_id", "user_job_matches", ["opportunity_id"], unique=False)

    if "applications" not in existing_tables:
        op.create_table(
            "applications",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("user_job_match_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="saved"),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("status_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_job_match_id"], ["user_job_matches.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "opportunity_id", name="uq_applications_user_opportunity"),
            sa.UniqueConstraint("user_job_match_id", name="uq_applications_user_job_match"),
        )
        op.create_index("ix_applications_user_id", "applications", ["user_id"], unique=False)
        op.create_index("ix_applications_opportunity_id", "applications", ["opportunity_id"], unique=False)
        op.create_index("ix_applications_user_job_match_id", "applications", ["user_job_match_id"], unique=False)

    inspector = sa.inspect(bind)
    daily_task_columns = {column["name"] for column in inspector.get_columns("daily_tasks")}
    if "user_job_match_id" not in daily_task_columns:
        op.add_column("daily_tasks", sa.Column("user_job_match_id", sa.String(), nullable=True))
    if not _has_foreign_key(inspector, "daily_tasks", "fk_daily_tasks_user_job_match_id"):
        op.create_foreign_key(
            "fk_daily_tasks_user_job_match_id",
            "daily_tasks",
            "user_job_matches",
            ["user_job_match_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if not _has_index(inspector, "daily_tasks", "ix_daily_tasks_user_job_match_id"):
        op.create_index("ix_daily_tasks_user_job_match_id", "daily_tasks", ["user_job_match_id"], unique=False)
    op.alter_column("daily_tasks", "job_id", existing_type=sa.String(), nullable=True)

    metadata = sa.MetaData()
    jobs = sa.Table("jobs", metadata, autoload_with=bind)
    opportunities = sa.Table("opportunities", metadata, autoload_with=bind)
    user_job_matches = sa.Table("user_job_matches", metadata, autoload_with=bind)
    applications = sa.Table("applications", metadata, autoload_with=bind)
    daily_tasks = sa.Table("daily_tasks", metadata, autoload_with=bind)

    existing_opportunities = {
        (row.source_type, row.source_job_id): row.id
        for row in bind.execute(
            sa.select(
                opportunities.c.id,
                opportunities.c.source_type,
                opportunities.c.source_job_id,
            )
        ).fetchall()
    }
    existing_matches = {
        (row.user_id, row.opportunity_id): row.id
        for row in bind.execute(
            sa.select(
                user_job_matches.c.id,
                user_job_matches.c.user_id,
                user_job_matches.c.opportunity_id,
            )
        ).fetchall()
    }
    existing_applications = {
        row.user_job_match_id
        for row in bind.execute(sa.select(applications.c.user_job_match_id)).fetchall()
    }

    legacy_job_to_match: dict[str, str] = {}
    for row in bind.execute(sa.select(jobs)).mappings().all():
        if not row["user_id"]:
            continue

        source_type, source_job_id = _parse_legacy_source(row["linkedin_job_id"], row["id"])
        opportunity_key = (source_type, source_job_id)
        opportunity_id = existing_opportunities.get(opportunity_key)

        if not opportunity_id:
            opportunity_id = _generate_uuid()
            bind.execute(
                opportunities.insert().values(
                    id=opportunity_id,
                    source_type=source_type,
                    source_job_id=source_job_id,
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    salary=row["salary"],
                    url=row["url"],
                    description=row["description"],
                    is_open=True,
                    posted_at=row["searched_at"],
                    first_seen_at=row["searched_at"],
                    last_seen_at=row["searched_at"],
                    created_at=row["searched_at"],
                    updated_at=row["searched_at"],
                )
            )
            existing_opportunities[opportunity_key] = opportunity_id

        match_key = (row["user_id"], opportunity_id)
        match_id = existing_matches.get(match_key)
        if not match_id:
            match_id = _generate_uuid()
            bind.execute(
                user_job_matches.insert().values(
                    id=match_id,
                    user_id=row["user_id"],
                    opportunity_id=opportunity_id,
                    match_score=row["match_score"],
                    match_reason=row["match_reason"],
                    matched_skills=row["matched_skills"],
                    missing_skills=row["missing_skills"],
                    cover_letter=row["cover_letter"],
                    last_scored_at=row["searched_at"],
                    created_at=row["searched_at"],
                    updated_at=row["searched_at"],
                )
            )
            existing_matches[match_key] = match_id

        legacy_job_to_match[row["id"]] = match_id

        if row["is_applied"] and match_id not in existing_applications:
            bind.execute(
                applications.insert().values(
                    id=_generate_uuid(),
                    user_id=row["user_id"],
                    opportunity_id=opportunity_id,
                    user_job_match_id=match_id,
                    status="applied",
                    applied_at=row["applied_at"] or row["searched_at"],
                    created_at=row["applied_at"] or row["searched_at"],
                    updated_at=row["applied_at"] or row["searched_at"],
                    status_updated_at=row["applied_at"] or row["searched_at"],
                )
            )
            existing_applications.add(match_id)

    for row in bind.execute(
        sa.select(daily_tasks.c.id, daily_tasks.c.job_id, daily_tasks.c.user_job_match_id)
    ).fetchall():
        if row.user_job_match_id or not row.job_id:
            continue
        match_id = legacy_job_to_match.get(row.job_id)
        if match_id:
            bind.execute(
                daily_tasks.update()
                .where(daily_tasks.c.id == row.id)
                .values(user_job_match_id=match_id)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "daily_tasks", "ix_daily_tasks_user_job_match_id"):
        op.drop_index("ix_daily_tasks_user_job_match_id", table_name="daily_tasks")
    if _has_foreign_key(inspector, "daily_tasks", "fk_daily_tasks_user_job_match_id"):
        op.drop_constraint("fk_daily_tasks_user_job_match_id", "daily_tasks", type_="foreignkey")
    if "user_job_match_id" in {column["name"] for column in inspector.get_columns("daily_tasks")}:
        op.drop_column("daily_tasks", "user_job_match_id")

    inspector = sa.inspect(bind)
    if "applications" in inspector.get_table_names():
        if _has_index(inspector, "applications", "ix_applications_user_job_match_id"):
            op.drop_index("ix_applications_user_job_match_id", table_name="applications")
        if _has_index(inspector, "applications", "ix_applications_opportunity_id"):
            op.drop_index("ix_applications_opportunity_id", table_name="applications")
        if _has_index(inspector, "applications", "ix_applications_user_id"):
            op.drop_index("ix_applications_user_id", table_name="applications")
        op.drop_table("applications")

    inspector = sa.inspect(bind)
    if "user_job_matches" in inspector.get_table_names():
        if _has_index(inspector, "user_job_matches", "ix_user_job_matches_opportunity_id"):
            op.drop_index("ix_user_job_matches_opportunity_id", table_name="user_job_matches")
        if _has_index(inspector, "user_job_matches", "ix_user_job_matches_user_id"):
            op.drop_index("ix_user_job_matches_user_id", table_name="user_job_matches")
        op.drop_table("user_job_matches")

    inspector = sa.inspect(bind)
    if "opportunities" in inspector.get_table_names():
        op.drop_table("opportunities")
