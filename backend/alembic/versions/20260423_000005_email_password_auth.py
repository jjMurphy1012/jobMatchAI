"""add email/password auth to users

Revision ID: 20260423_000005
Revises: 20260422_000004
Create Date: 2026-04-23 00:00:05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_000005"
down_revision = "20260422_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" not in columns:
        op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" in columns:
        op.drop_column("users", "password_hash")
