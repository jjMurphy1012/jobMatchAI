"""add preference profile fields

Revision ID: 20260422_000002
Revises: 20260422_000001
Create Date: 2026-04-22 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_000002"
down_revision = "20260422_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("job_preferences")}

    additions = [
        ("raw_text", sa.Column("raw_text", sa.Text(), nullable=True)),
        ("extracted_fields", sa.Column("extracted_fields", sa.JSON(), nullable=True)),
        ("override_fields", sa.Column("override_fields", sa.JSON(), nullable=True)),
        ("effective_fields", sa.Column("effective_fields", sa.JSON(), nullable=True)),
        ("extracted_at", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True)),
        ("extraction_version", sa.Column("extraction_version", sa.String(), nullable=True)),
        ("excluded_companies", sa.Column("excluded_companies", sa.JSON(), nullable=True)),
        ("industries", sa.Column("industries", sa.JSON(), nullable=True)),
        ("salary_min", sa.Column("salary_min", sa.Integer(), nullable=True)),
        ("salary_max", sa.Column("salary_max", sa.Integer(), nullable=True)),
        ("salary_currency", sa.Column("salary_currency", sa.String(), nullable=True)),
    ]

    for column_name, column in additions:
        if column_name not in columns:
            op.add_column("job_preferences", column)


def downgrade() -> None:
    op.drop_column("job_preferences", "salary_currency")
    op.drop_column("job_preferences", "salary_max")
    op.drop_column("job_preferences", "salary_min")
    op.drop_column("job_preferences", "industries")
    op.drop_column("job_preferences", "excluded_companies")
    op.drop_column("job_preferences", "extraction_version")
    op.drop_column("job_preferences", "extracted_at")
    op.drop_column("job_preferences", "effective_fields")
    op.drop_column("job_preferences", "override_fields")
    op.drop_column("job_preferences", "extracted_fields")
    op.drop_column("job_preferences", "raw_text")
