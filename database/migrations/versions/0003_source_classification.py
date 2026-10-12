"""Source classification: what kind of body a source is, where it is about,
what it costs, what its terms say and what its records carry.

Adds columns to `sources` only. Every column has a default, so existing rows
(the Hyderabad feeds and the researched sources) stay valid; the registry
fills the new fields in on the next start-up.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _new_source_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("source_class", sa.String(32)),
        sa.Column("country", sa.String(2)),
        sa.Column("region", sa.String(120)),
        sa.Column("city", sa.String(64)),
        sa.Column("cost_category", sa.String(32)),
        sa.Column("rate_limit", sa.Text()),
        sa.Column("terms_status", sa.String(32), nullable=False, server_default="NOT_REVIEWED"),
        sa.Column("licence", sa.Text()),
        sa.Column("attribution", sa.Text()),
        sa.Column("commercial_use", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("provides_geometry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provides_segments", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provides_direction", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("real_time", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("discovery_only", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def upgrade() -> None:
    for column in _new_source_columns():
        op.add_column("sources", column)
    op.create_index("ix_sources_city", "sources", ["city"])


def downgrade() -> None:
    op.drop_index("ix_sources_city", table_name="sources")
    for column in reversed(_new_source_columns()):
        op.execute(f"ALTER TABLE sources DROP COLUMN {column.name}")
