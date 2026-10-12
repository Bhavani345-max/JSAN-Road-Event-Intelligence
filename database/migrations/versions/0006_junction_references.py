"""Reviewer-confirmed junction references.

A small table of junction names the press uses that the road network does
not name itself ("IIIT Junction"). REI may propose one, from OSM evidence
such as the crossing of two named roads; it is used to resolve events only
once a reviewer has confirmed it. Nothing is confirmed by default.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

Timestamp = sa.DateTime(timezone=True)
Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "junction_references",
        sa.Column("junction_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column("aliases", Json, nullable=False),
        # A position only when it comes from a real feature (an OSM node) or a reviewer.
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("osm_node_id", sa.BigInteger()),
        sa.Column("related_roads", Json, nullable=False),
        # How the reference was proposed, e.g. "OSM: crossing of DLF road and Old Bombay Road".
        sa.Column("source", sa.Text(), nullable=False),
        # UNCONFIRMED, CONFIRMED or REJECTED.
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confirmation_method", sa.Text()),
        sa.Column("reviewer", sa.String(120)),
        sa.Column("confirmed_at", Timestamp),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("created_at", Timestamp, nullable=False),
        sa.Column("updated_at", Timestamp, nullable=False),
        sa.UniqueConstraint("city", "name_key", name="uq_junction_references_city_name"),
    )


def downgrade() -> None:
    op.drop_table("junction_references")
