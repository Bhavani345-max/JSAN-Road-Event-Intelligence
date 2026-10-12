"""Initial schema: sources, source_artifacts, events, event_versions.

Revision ID: 0001
Revises:
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

Timestamp = sa.DateTime(timezone=True)
Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("source_id", sa.String(64), primary_key=True),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("authority_type", sa.String(64)),
        sa.Column("tier", sa.Integer()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("polling_frequency_minutes", sa.Integer()),
        sa.Column("last_poll_at", Timestamp),
        sa.Column("last_success_at", Timestamp),
        sa.Column("last_failure_at", Timestamp),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.Column("updated_at", Timestamp, nullable=False),
    )

    op.create_table(
        "source_artifacts",
        sa.Column("artifact_id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id"), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_at", Timestamp),
        sa.Column("retrieved_at", Timestamp, nullable=False),
        sa.Column("raw_content", Json, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("classification_details", Json, nullable=False),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_source_artifacts_source_item"),
    )
    op.create_index("ix_source_artifacts_source_id", "source_artifacts", ["source_id"])
    op.create_index("ix_source_artifacts_classification", "source_artifacts", ["classification"])

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(40), primary_key=True),
        sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.source_id"), nullable=False),
        sa.Column(
            "source_artifact_id",
            sa.String(36),
            sa.ForeignKey("source_artifacts.artifact_id"),
            unique=True,
        ),
        sa.Column("source_reference", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(40)),
        sa.Column("description", sa.Text()),
        sa.Column("city", sa.String(120)),
        sa.Column("affected_road", sa.Text()),
        sa.Column("start_time", Timestamp),
        sa.Column("end_time", Timestamp),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16)),
        sa.Column("direction", sa.String(24)),
        sa.Column("geometry", Json),
        sa.Column("confidence", sa.Float()),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("detection", Json),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.Column("updated_at", Timestamp, nullable=False),
    )
    op.create_index("ix_events_source_id", "events", ["source_id"])
    op.create_index("ix_events_status", "events", ["status"])

    op.create_table(
        "event_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(40), sa.ForeignKey("events.event_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("snapshot", Json, nullable=False),
        sa.Column("change_reason", sa.Text()),
        sa.Column("changed_by", sa.String(120), nullable=False),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.UniqueConstraint("event_id", "version", name="uq_event_versions_event_version"),
    )
    op.create_index("ix_event_versions_event_id", "event_versions", ["event_id"])

    if op.get_bind().dialect.name == "postgresql":
        # PostGIS: a real geometry column, kept in step with the GeoJSON by the
        # database itself, ready for spatial queries by the GIS Resolution Engine.
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            """
            ALTER TABLE events ADD COLUMN geom geometry(Geometry, 4326)
            GENERATED ALWAYS AS (ST_SetSRID(ST_GeomFromGeoJSON(geometry), 4326)) STORED
            """
        )
        op.execute("CREATE INDEX ix_events_geom ON events USING GIST (geom)")


def downgrade() -> None:
    op.drop_table("event_versions")
    op.drop_table("events")
    op.drop_table("source_artifacts")
    op.drop_table("sources")
