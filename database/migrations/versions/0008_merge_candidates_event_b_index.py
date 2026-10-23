"""Index merge candidates by their second event.

Matching and the event lists now read only the candidates that concern the
events they handle, by either event. The pair's unique constraint already
indexes `event_a` first; this adds `event_b`, so neither lookup reads the
whole table (23 October 2026: production loaded every candidate each time).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_event_merge_candidates_event_b", "event_merge_candidates", ["event_b"])


def downgrade() -> None:
    op.drop_index("ix_event_merge_candidates_event_b", table_name="event_merge_candidates")
