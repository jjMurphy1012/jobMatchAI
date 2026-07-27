"""snapshot job details on applications and allow manual entries

Revision ID: 20260728_000013
Revises: 20260727_000012
Create Date: 2026-07-28 00:00:13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_000013"
down_revision = "20260727_000012"
branch_labels = None
depends_on = None

SNAPSHOT_COLUMNS = {
    "company_name": sa.String(),
    "job_title": sa.String(),
    "location": sa.String(),
    "job_url": sa.String(),
    "job_type": sa.String(),
    "season": sa.String(),
    "channel": sa.String(),
}


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _fk_name(inspector: sa.Inspector, table: str, column: str) -> str | None:
    for fk in inspector.get_foreign_keys(table):
        if fk.get("constrained_columns") == [column]:
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = _column_names(inspector, "applications")

    # 1. Add every snapshot column as nullable so existing rows stay valid.
    for name, column_type in SNAPSHOT_COLUMNS.items():
        if name not in existing:
            op.add_column("applications", sa.Column(name, column_type, nullable=True))

    # 2. Backfill from the linked opportunity before anything becomes required.
    op.execute(
        """
        UPDATE applications AS a
        SET company_name = COALESCE(a.company_name, o.company),
            job_title = COALESCE(a.job_title, o.title),
            location = COALESCE(a.location, o.location),
            job_url = COALESCE(a.job_url, o.url)
        FROM opportunities AS o
        WHERE a.opportunity_id = o.id
        """
    )
    # Any row whose opportunity vanished still needs the NOT NULL columns filled.
    op.execute(
        """
        UPDATE applications
        SET company_name = COALESCE(company_name, 'Unknown company'),
            job_title = COALESCE(job_title, 'Unknown role'),
            channel = COALESCE(channel, 'online')
        """
    )

    # 3. Now the snapshot can carry the guarantees the app relies on.
    op.alter_column("applications", "company_name", nullable=False)
    op.alter_column("applications", "job_title", nullable=False)
    op.alter_column("applications", "channel", nullable=False, server_default="online")

    # 4. Manual entries have no opportunity or match; a deleted job must not take
    #    the application with it, so the foreign keys become SET NULL.
    op.alter_column("applications", "opportunity_id", existing_type=sa.String(), nullable=True)
    op.alter_column("applications", "user_job_match_id", existing_type=sa.String(), nullable=True)

    for column, target in (("opportunity_id", "opportunities"), ("user_job_match_id", "user_job_matches")):
        old_name = _fk_name(inspector, "applications", column)
        if old_name:
            op.drop_constraint(old_name, "applications", type_="foreignkey")
        op.create_foreign_key(
            f"fk_applications_{column}",
            "applications",
            target,
            [column],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Manual applications have no opportunity or match and cannot be represented
    # by the old schema. Refuse rather than silently deleting a user's history.
    orphan_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM applications "
            "WHERE opportunity_id IS NULL OR user_job_match_id IS NULL"
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            f"{orphan_count} application(s) are not linked to a job and would be lost. "
            "Export or delete them before downgrading."
        )

    for column, target in (("opportunity_id", "opportunities"), ("user_job_match_id", "user_job_matches")):
        old_name = _fk_name(inspector, "applications", column)
        if old_name:
            op.drop_constraint(old_name, "applications", type_="foreignkey")
        op.create_foreign_key(
            f"fk_applications_{column}",
            "applications",
            target,
            [column],
            ["id"],
            ondelete="CASCADE",
        )
        op.alter_column("applications", column, existing_type=sa.String(), nullable=False)

    existing = _column_names(inspector, "applications")
    for name in SNAPSHOT_COLUMNS:
        if name in existing:
            op.drop_column("applications", name)
