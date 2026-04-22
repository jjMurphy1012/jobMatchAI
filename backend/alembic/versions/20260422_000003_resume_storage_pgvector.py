"""add resume storage metadata and pgvector embeddings

Revision ID: 20260422_000003
Revises: 20260422_000002
Create Date: 2026-04-22 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_000003"
down_revision = "20260422_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    inspector = sa.inspect(op.get_bind())
    resume_columns = {
        column["name"]: column
        for column in inspector.get_columns("resumes")
    }
    chunk_columns = {
        column["name"]: column
        for column in inspector.get_columns("resume_chunks")
    }

    if "storage_provider" not in resume_columns:
        op.add_column("resumes", sa.Column("storage_provider", sa.String(), nullable=True))
    if "storage_bucket" not in resume_columns:
        op.add_column("resumes", sa.Column("storage_bucket", sa.String(), nullable=True))
    if "storage_path" not in resume_columns:
        op.add_column("resumes", sa.Column("storage_path", sa.String(), nullable=True))

    if "file_path" in resume_columns and not resume_columns["file_path"].get("nullable", True):
        op.alter_column("resumes", "file_path", existing_type=sa.String(), nullable=True)

    op.execute(
        """
        UPDATE resumes
        SET storage_provider = COALESCE(storage_provider, 'local'),
            storage_path = COALESCE(storage_path, file_path)
        WHERE file_path IS NOT NULL
        """
    )

    resume_embedding_type = str(resume_columns["embedding"]["type"]).lower()
    chunk_embedding_type = str(chunk_columns["embedding"]["type"]).lower()

    if "vector" not in resume_embedding_type or "vector" not in chunk_embedding_type:
        op.execute("DELETE FROM resume_chunks")
        op.execute("UPDATE resumes SET embedding = NULL")
        op.execute(
            "ALTER TABLE resumes ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)"
        )
        op.execute(
            "ALTER TABLE resume_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)"
        )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE resume_chunks ALTER COLUMN embedding TYPE json USING to_json(embedding)"
    )
    op.execute(
        "ALTER TABLE resumes ALTER COLUMN embedding TYPE json USING to_json(embedding)"
    )

    op.alter_column("resumes", "file_path", existing_type=sa.String(), nullable=False)
    op.drop_column("resumes", "storage_path")
    op.drop_column("resumes", "storage_bucket")
    op.drop_column("resumes", "storage_provider")
