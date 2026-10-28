"""Account recovery: temporary passwords, recovery codes and security events.

Adds to the users table only a column with a default (existing accounts keep
working unchanged), and two new tables (decision 0044):

- users.must_change_password: set when an administrator (or the server's
  emergency procedure) gives the account a temporary password.
- recovery_codes: single-use codes an administrator keeps for a forgotten
  password; only their SHA-256 digests are stored.
- security_events: who changed which account's credentials, and when; never a
  password or a code.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "recovery_codes",
        sa.Column("code_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code_hash", name="uq_recovery_codes_code_hash"),
    )
    op.create_index("ix_recovery_codes_user_id", "recovery_codes", ["user_id"])
    op.create_table(
        "security_events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=True),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("detail", sa.String(length=300), nullable=True),
    )
    op.create_index("ix_security_events_occurred_at", "security_events", ["occurred_at"])
    op.create_index("ix_security_events_account_id", "security_events", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_security_events_account_id", table_name="security_events")
    op.drop_index("ix_security_events_occurred_at", table_name="security_events")
    op.drop_table("security_events")
    op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes")
    op.drop_table("recovery_codes")
    # In place, not by rebuilding the table (see 0010).
    op.drop_column("users", "must_change_password")
