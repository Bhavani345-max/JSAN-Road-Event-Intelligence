"""Registration, email verification, administrator approval, reset links.

Additive only (decision 0045). Every existing account becomes "active" through
the column default, keeps its role, password and sessions: nobody is downgraded
or signed out. Existing accounts have no proved email (email_verified_at NULL),
so reset links are not sent to them until they prove one; their recovery codes
and the administrator's reset keep working.

- users.status ("active", "pending_approval", "rejected", "suspended"),
  email_verified_at, registered_at, decided_at, decided_by.
- email_tokens: single-use, expiring links, stored as SHA-256 digests.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columns are added in place, never by rebuilding the table: on SQLite a rebuild
    # drops the old users table, and with foreign keys on that deletes every
    # session, recovery code and link of every account (caught by
    # tests/integration/test_migrations.py).
    op.add_column("users", sa.Column("status", sa.String(length=24), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("decided_by", sa.String(length=36), nullable=True))
    # SQLite cannot add a constraint without a rebuild; the code checks the same values there.
    if op.get_bind().dialect.name != "sqlite":
        op.create_check_constraint(
            "ck_users_status", "users", "status IN ('active', 'pending_approval', 'rejected', 'suspended')"
        )
    op.create_table(
        "email_tokens",
        sa.Column("token_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_email_tokens_token_hash"),
        sa.CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_email_tokens_purpose"),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
    op.drop_table("email_tokens")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("ck_users_status", "users", type_="check")
    for column in ("decided_by", "decided_at", "registered_at", "email_verified_at", "status"):
        op.drop_column("users", column)
