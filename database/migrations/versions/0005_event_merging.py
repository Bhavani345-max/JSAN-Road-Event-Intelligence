"""Cross-source event merging.

- `events.merged_into`: an event merged into another (its canonical event)
  keeps its row, its evidence and its history; this column links it to the
  canonical event, which lists it as a contribution.
- `event_merge_candidates`: pairs of events that may be the same real-world
  event, with why, what conflicts, and the review decision.

Nothing is deleted or rewritten: merging only links.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

Timestamp = sa.DateTime(timezone=True)
Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("events", sa.Column("merged_into", sa.String(40)))
    op.create_index("ix_events_merged_into", "events", ["merged_into"])
    op.create_table(
        "event_merge_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_a", sa.String(40), sa.ForeignKey("events.event_id"), nullable=False),
        sa.Column("event_b", sa.String(40), sa.ForeignKey("events.event_id"), nullable=False),
        # SAME (clearly the same event) or POSSIBLE (needs review).
        sa.Column("classification", sa.String(16), nullable=False),
        sa.Column("reasons", Json, nullable=False),
        sa.Column("conflicts", Json, nullable=False),
        # PENDING, AUTO_MERGED, CONFIRMED, REJECTED or SUPERSEDED.
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.Column("decided_at", Timestamp),
        sa.Column("decided_by", sa.String(120)),
        sa.Column("decision_reason", sa.Text()),
        sa.UniqueConstraint("event_a", "event_b", name="uq_event_merge_candidates_pair"),
    )
    op.create_index("ix_event_merge_candidates_status", "event_merge_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_event_merge_candidates_status", table_name="event_merge_candidates")
    op.drop_table("event_merge_candidates")
    op.drop_index("ix_events_merged_into", table_name="events")
    op.execute("ALTER TABLE events DROP COLUMN merged_into")
