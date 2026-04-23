"""add interview experiences

Revision ID: 20260423_000007
Revises: 20260423_000006
Create Date: 2026-04-23 00:00:07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_000007"
down_revision = "20260423_000006"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "interview_experiences" not in existing_tables:
        op.create_table(
            "interview_experiences",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("company_name", sa.String(), nullable=False),
            sa.Column("company_name_normalized", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("level", sa.String(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("rounds", sa.Text(), nullable=True),
            sa.Column("topics", sa.JSON(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("source_url", sa.String(), nullable=True),
            sa.Column("source_site", sa.String(), nullable=True),
            sa.Column("review_status", sa.String(), nullable=False, server_default="draft"),
            sa.Column("relevance_keywords", sa.JSON(), nullable=True),
            sa.Column("created_by_user_id", sa.String(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.String(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "interview_experiences", "ix_interview_experiences_company_name_normalized"):
        op.create_index(
            "ix_interview_experiences_company_name_normalized",
            "interview_experiences",
            ["company_name_normalized"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "interview_experiences" in inspector.get_table_names():
        if _has_index(inspector, "interview_experiences", "ix_interview_experiences_company_name_normalized"):
            op.drop_index("ix_interview_experiences_company_name_normalized", table_name="interview_experiences")
        op.drop_table("interview_experiences")
