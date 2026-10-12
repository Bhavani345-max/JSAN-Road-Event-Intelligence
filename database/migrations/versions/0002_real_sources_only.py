"""Real source data only; richer source registry.

- Removes the hand-made DEMO events, their source and the `is_demo` flag: every
  event must now come from a connected source and its stored evidence.
- Extends `sources` so the registry can describe each source (owner, tier,
  endpoint, access method, integration status, …), including sources that
  have been researched but are not connected.

Columns are renamed and dropped with plain ALTER TABLE statements, which both
PostgreSQL and SQLite (3.35+) support, so no table has to be rebuilt.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _new_source_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("organization", sa.String(200)),
        sa.Column("endpoint", sa.Text()),
        sa.Column("access_method", sa.Text()),
        # Rows that already exist are the feeds REI was already reading.
        sa.Column(
            "integration_status", sa.String(32), nullable=False, server_default="CONNECTED"
        ),
        sa.Column("language", sa.String(16)),
        sa.Column("events_supported", Json, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("parser_type", sa.String(32)),
        sa.Column("terms_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evidence_retention", sa.Text()),
        sa.Column("notes", sa.Text()),
    )


def upgrade() -> None:
    # Demo data goes first, while the flag that identifies it still exists.
    op.execute(
        "DELETE FROM event_versions WHERE event_id IN "
        "(SELECT event_id FROM events WHERE is_demo)"
    )
    op.execute("DELETE FROM events WHERE is_demo")
    op.execute("DELETE FROM sources WHERE source_id = 'rei-demo'")
    op.execute("ALTER TABLE events DROP COLUMN is_demo")

    op.execute("ALTER TABLE sources RENAME COLUMN tier TO source_tier")
    for column in _new_source_columns():
        op.add_column("sources", column)
    op.create_index("ix_sources_integration_status", "sources", ["integration_status"])


def downgrade() -> None:
    op.drop_index("ix_sources_integration_status", table_name="sources")
    for column in reversed(_new_source_columns()):
        op.execute(f"ALTER TABLE sources DROP COLUMN {column.name}")
    op.execute("ALTER TABLE sources RENAME COLUMN source_tier TO tier")

    # The demo events themselves are not restored.
    op.add_column(
        "events", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false())
    )
