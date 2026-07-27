"""add notification logs

Revision ID: 20260727_000012
Revises: 20260514_000011
Create Date: 2026-07-27 00:00:12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_000012"
down_revision = "20260514_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "notification_logs" in inspector.get_table_names():
        return

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="sendgrid"),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_for_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_logs_user_id", "notification_logs", ["user_id"])

    # Idempotency guarantee: at most one *successful* daily notification per user
    # per day. Failed rows are excluded so a failed send can still be retried.
    op.create_index(
        "uq_notification_logs_sent_per_day",
        "notification_logs",
        ["user_id", "kind", "sent_for_date"],
        unique=True,
        postgresql_where=sa.text("status = 'sent' AND sent_for_date IS NOT NULL"),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "notification_logs" not in inspector.get_table_names():
        return
    op.drop_table("notification_logs")
