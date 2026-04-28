"""add greenhouse company sources and sync logs

Revision ID: 20260428_000009
Revises: 20260424_000008
Create Date: 2026-04-28 00:00:09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_000009"
down_revision = "20260424_000008"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        foreign_key["name"] == constraint_name
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "company_sources"):
        op.create_table(
            "company_sources",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("company_name", sa.String(), nullable=False),
            sa.Column("board_token", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_user_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_type", "board_token", name="uq_company_sources_source_board"),
        )
        op.create_index("ix_company_sources_created_by_user_id", "company_sources", ["created_by_user_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "source_sync_runs"):
        op.create_table(
            "source_sync_runs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("company_source_id", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("upserted_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("closed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["company_source_id"], ["company_sources.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_source_sync_runs_company_source_id", "source_sync_runs", ["company_source_id"], unique=False)

    inspector = sa.inspect(bind)
    if _has_table(inspector, "opportunities") and not _has_column(inspector, "opportunities", "company_source_id"):
        op.add_column("opportunities", sa.Column("company_source_id", sa.String(), nullable=True))
        op.create_foreign_key(
            "fk_opportunities_company_source_id",
            "opportunities",
            "company_sources",
            ["company_source_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_opportunities_company_source_id", "opportunities", ["company_source_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "opportunities") and _has_column(inspector, "opportunities", "company_source_id"):
        if _has_foreign_key(inspector, "opportunities", "fk_opportunities_company_source_id"):
            op.drop_constraint("fk_opportunities_company_source_id", "opportunities", type_="foreignkey")
        if _has_index(inspector, "opportunities", "ix_opportunities_company_source_id"):
            op.drop_index("ix_opportunities_company_source_id", table_name="opportunities")
        op.drop_column("opportunities", "company_source_id")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "source_sync_runs"):
        op.drop_table("source_sync_runs")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "company_sources"):
        if _has_unique_constraint(inspector, "company_sources", "uq_company_sources_source_board"):
            op.drop_constraint("uq_company_sources_source_board", "company_sources", type_="unique")
        if _has_index(inspector, "company_sources", "ix_company_sources_created_by_user_id"):
            op.drop_index("ix_company_sources_created_by_user_id", table_name="company_sources")
        op.drop_table("company_sources")
