"""drop redundant unique constraint on applications

Revision ID: 20260424_000008
Revises: 20260423_000007
Create Date: 2026-04-24 00:00:08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_000008"
down_revision = "20260423_000007"
branch_labels = None
depends_on = None


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_unique_constraint(inspector, "applications", "uq_applications_user_opportunity"):
        op.drop_constraint("uq_applications_user_opportunity", "applications", type_="unique")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_unique_constraint(inspector, "applications", "uq_applications_user_opportunity"):
        op.create_unique_constraint(
            "uq_applications_user_opportunity",
            "applications",
            ["user_id", "opportunity_id"],
        )
