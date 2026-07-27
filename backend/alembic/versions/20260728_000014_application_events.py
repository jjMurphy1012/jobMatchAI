"""add application stage events and region

Revision ID: 20260728_000014
Revises: 20260728_000013
Create Date: 2026-07-28 00:00:14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_000014"
down_revision = "20260728_000013"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "region" not in _column_names(inspector, "applications"):
        op.add_column("applications", sa.Column("region", sa.String(), nullable=True))

    if "application_events" not in inspector.get_table_names():
        op.create_table(
            "application_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "application_id",
                sa.String(),
                sa.ForeignKey("applications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("occurred_on", sa.Date(), nullable=False),
            sa.Column("label", sa.String(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_application_events_application_id", "application_events", ["application_id"])

    # Seed the timeline from what we already know: every application that has a
    # submission date gets its "applied" event, so the stage columns are not
    # blank for records created before this table existed.
    op.execute(
        """
        INSERT INTO application_events (id, application_id, kind, occurred_on, label)
        SELECT md5(random()::text || a.id), a.id, 'applied', a.applied_at::date, a.channel
        FROM applications AS a
        WHERE a.applied_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM application_events AS e
              WHERE e.application_id = a.id AND e.kind = 'applied'
          )
        """
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "application_events" in inspector.get_table_names():
        op.drop_index("ix_application_events_application_id", table_name="application_events")
        op.drop_table("application_events")

    if "region" in _column_names(inspector, "applications"):
        op.drop_column("applications", "region")
