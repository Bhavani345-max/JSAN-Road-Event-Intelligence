from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JsonType, UtcDateTime
from .source import Source
from .source_artifact import SourceArtifact


class Event(Base):
    """A canonical REI event (see packages/event_schema)."""

    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), index=True)
    # The evidence this event was derived from. Unique: one event per artifact.
    source_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_artifacts.artifact_id"), unique=True
    )
    source_reference: Mapped[str | None] = mapped_column(Text)

    title: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    affected_road: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime | None] = mapped_column(UtcDateTime)
    end_time: Mapped[datetime | None] = mapped_column(UtcDateTime)
    status: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str | None] = mapped_column(String(16))
    direction: Mapped[str | None] = mapped_column(String(24))
    # GeoJSON geometry; NULL until the event has been located.
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    confidence: Mapped[float | None] = mapped_column(Float)
    detection: Mapped[dict[str, Any] | None] = mapped_column(JsonType)

    # Set when this event was merged into another (its canonical event). The
    # row, its evidence and its history stay; it is no longer listed by itself.
    merged_into: Mapped[str | None] = mapped_column(String(40), index=True)

    # Incremented on every change; each value has a row in event_versions.
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)

    source: Mapped[Source] = relationship(lazy="joined")
    artifact: Mapped[SourceArtifact | None] = relationship(lazy="joined")
    versions: Mapped[list["EventVersion"]] = relationship(
        order_by="EventVersion.version", cascade="all, delete-orphan"
    )


class EventMergeCandidate(Base):
    """Two events that may be the same real-world event, and the review decision."""

    __tablename__ = "event_merge_candidates"
    __table_args__ = (UniqueConstraint("event_a", "event_b", name="uq_event_merge_candidates_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The pair, in id order. The unique constraint indexes event_a first; event_b
    # has its own index (migration 0008): candidates are looked up by either event.
    event_a: Mapped[str] = mapped_column(ForeignKey("events.event_id"))
    event_b: Mapped[str] = mapped_column(ForeignKey("events.event_id"), index=True)
    # SAME (clearly the same event) or POSSIBLE (needs review).
    classification: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list[Any]] = mapped_column(JsonType)
    conflicts: Mapped[list[Any]] = mapped_column(JsonType)
    # PENDING, AUTO_MERGED, CONFIRMED, REJECTED or SUPERSEDED.
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    decided_by: Mapped[str | None] = mapped_column(String(120))
    decision_reason: Mapped[str | None] = mapped_column(Text)


class EventVersion(Base):
    """History of an event: a full snapshot for every version."""

    __tablename__ = "event_versions"
    __table_args__ = (UniqueConstraint("event_id", "version", name="uq_event_versions_event_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.event_id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType)
    change_reason: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
