"""Revisions of source records.

An official source revises its records: a new end time, a changed severity.
The first version of a record stays in `source_artifacts`, never modified; each
later version the source publishes is added to `source_artifact_revisions`,
also never modified. Evidence is append-only.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

Timestamp = sa.DateTime(timezone=True)
Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "source_artifact_revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "artifact_id",
            sa.String(36),
            sa.ForeignKey("source_artifacts.artifact_id"),
            nullable=False,
        ),
        # The original record is revision 1; the first revision stored here is 2.
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_at", Timestamp),
        sa.Column("retrieved_at", Timestamp, nullable=False),
        sa.Column("raw_content", Json, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.UniqueConstraint("artifact_id", "revision", name="uq_artifact_revisions_artifact_revision"),
    )
    op.create_index(
        "ix_source_artifact_revisions_artifact_id", "source_artifact_revisions", ["artifact_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_source_artifact_revisions_artifact_id", table_name="source_artifact_revisions")
    op.drop_table("source_artifact_revisions")
