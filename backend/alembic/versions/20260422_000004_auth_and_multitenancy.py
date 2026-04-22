"""add auth tables and user ownership

Revision ID: 20260422_000004
Revises: 20260422_000003
Create Date: 2026-04-22 00:00:04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_000004"
down_revision = "20260422_000003"
branch_labels = None
depends_on = None


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_foreign_key(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        foreign_key["name"] == constraint_name
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("avatar_url", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=False, server_default="user"),
            sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )

    if "auth_accounts" not in existing_tables:
        op.create_table(
            "auth_accounts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("provider_sub", sa.String(), nullable=False),
            sa.Column("provider_email", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "provider_sub", name="uq_auth_accounts_provider_sub"),
        )
        op.create_index("ix_auth_accounts_user_id", "auth_accounts", ["user_id"], unique=False)

    if "user_sessions" not in existing_tables:
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("refresh_token_hash", sa.String(), nullable=False),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
        op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"], unique=True)

    inspector = sa.inspect(bind)
    resumes_columns = {column["name"] for column in inspector.get_columns("resumes")}
    preferences_columns = {column["name"] for column in inspector.get_columns("job_preferences")}
    jobs_columns = {column["name"] for column in inspector.get_columns("jobs")}

    if "user_id" not in resumes_columns:
        op.add_column("resumes", sa.Column("user_id", sa.String(), nullable=True))
    if not _has_foreign_key(inspector, "resumes", "fk_resumes_user_id_users"):
        op.create_foreign_key(
            "fk_resumes_user_id_users",
            "resumes",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if not _has_index(inspector, "resumes", "ix_resumes_user_id"):
        op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)

    if "user_id" not in preferences_columns:
        op.add_column("job_preferences", sa.Column("user_id", sa.String(), nullable=True))
    if not _has_foreign_key(inspector, "job_preferences", "fk_job_preferences_user_id_users"):
        op.create_foreign_key(
            "fk_job_preferences_user_id_users",
            "job_preferences",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if not _has_index(inspector, "job_preferences", "ix_job_preferences_user_id"):
        op.create_index("ix_job_preferences_user_id", "job_preferences", ["user_id"], unique=False)
    if not _has_unique_constraint(inspector, "job_preferences", "uq_job_preferences_user_id"):
        op.create_unique_constraint("uq_job_preferences_user_id", "job_preferences", ["user_id"])

    if "user_id" not in jobs_columns:
        op.add_column("jobs", sa.Column("user_id", sa.String(), nullable=True))
    if not _has_foreign_key(inspector, "jobs", "fk_jobs_user_id_users"):
        op.create_foreign_key(
            "fk_jobs_user_id_users",
            "jobs",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if not _has_index(inspector, "jobs", "ix_jobs_user_id"):
        op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)

    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints("jobs"):
        if constraint["name"] != "uq_jobs_user_linkedin_job_id" and constraint.get("column_names") == ["linkedin_job_id"]:
            op.drop_constraint(constraint["name"], "jobs", type_="unique")
    if not _has_unique_constraint(inspector, "jobs", "uq_jobs_user_linkedin_job_id"):
        op.create_unique_constraint("uq_jobs_user_linkedin_job_id", "jobs", ["user_id", "linkedin_job_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if _has_unique_constraint(inspector, "jobs", "uq_jobs_user_linkedin_job_id"):
        op.drop_constraint("uq_jobs_user_linkedin_job_id", "jobs", type_="unique")
    if _has_index(inspector, "jobs", "ix_jobs_user_id"):
        op.drop_index("ix_jobs_user_id", table_name="jobs")
    if _has_foreign_key(inspector, "jobs", "fk_jobs_user_id_users"):
        op.drop_constraint("fk_jobs_user_id_users", "jobs", type_="foreignkey")
    if "user_id" in {column["name"] for column in inspector.get_columns("jobs")}:
        op.drop_column("jobs", "user_id")
    if not _has_unique_constraint(inspector, "jobs", "jobs_linkedin_job_id_key"):
        op.create_unique_constraint("jobs_linkedin_job_id_key", "jobs", ["linkedin_job_id"])

    inspector = sa.inspect(op.get_bind())
    if _has_unique_constraint(inspector, "job_preferences", "uq_job_preferences_user_id"):
        op.drop_constraint("uq_job_preferences_user_id", "job_preferences", type_="unique")
    if _has_index(inspector, "job_preferences", "ix_job_preferences_user_id"):
        op.drop_index("ix_job_preferences_user_id", table_name="job_preferences")
    if _has_foreign_key(inspector, "job_preferences", "fk_job_preferences_user_id_users"):
        op.drop_constraint("fk_job_preferences_user_id_users", "job_preferences", type_="foreignkey")
    if "user_id" in {column["name"] for column in inspector.get_columns("job_preferences")}:
        op.drop_column("job_preferences", "user_id")

    inspector = sa.inspect(op.get_bind())
    if _has_index(inspector, "resumes", "ix_resumes_user_id"):
        op.drop_index("ix_resumes_user_id", table_name="resumes")
    if _has_foreign_key(inspector, "resumes", "fk_resumes_user_id_users"):
        op.drop_constraint("fk_resumes_user_id_users", "resumes", type_="foreignkey")
    if "user_id" in {column["name"] for column in inspector.get_columns("resumes")}:
        op.drop_column("resumes", "user_id")

    inspector = sa.inspect(op.get_bind())
    if "user_sessions" in inspector.get_table_names():
        op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
        op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
        op.drop_table("user_sessions")

    inspector = sa.inspect(op.get_bind())
    if "auth_accounts" in inspector.get_table_names():
        op.drop_index("ix_auth_accounts_user_id", table_name="auth_accounts")
        op.drop_table("auth_accounts")

    inspector = sa.inspect(op.get_bind())
    if "users" in inspector.get_table_names():
        op.drop_table("users")
