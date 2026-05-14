"""add opportunity embeddings

Revision ID: 20260514_000011
Revises: 20260504_000010
Create Date: 2026-05-14 00:00:11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_000011"
down_revision = "20260504_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("opportunities")}
    if "embedding" not in columns:
        op.execute("ALTER TABLE opportunities ADD COLUMN embedding vector(1536)")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("opportunities")}
    if "embedding" in columns:
        op.drop_column("opportunities", "embedding")
