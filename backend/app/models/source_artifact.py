from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JsonType, UtcDateTime


class SourceArtifact(Base):
    """The original item acquired from a source, kept as evidence.

    Written before anything is derived from the item and never modified
    afterwards. One row per (source, item): this is also what prevents the same
    article from being ingested twice. Later versions a source publishes of
    the same item are added as `SourceArtifactRevision`s.
    """

    __tablename__ = "source_artifacts"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_artifacts_source_item"),
    )

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"), index=True)
    external_id: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    retrieved_at: Mapped[datetime] = mapped_column(UtcDateTime)
    # The item as the connector received it.
    raw_content: Mapped[dict[str, Any]] = mapped_column(JsonType)
    content_hash: Mapped[str] = mapped_column(String(64))
    # RELEVANT_TRAFFIC_ARTICLE or NOT_RELEVANT, and how that was decided.
    classification: Mapped[str] = mapped_column(String(40), index=True)
    classification_details: Mapped[dict[str, Any]] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)

    revisions: Mapped[list["SourceArtifactRevision"]] = relationship(
        order_by="SourceArtifactRevision.revision", lazy="selectin"
    )

    @property
    def latest(self) -> "SourceArtifact | SourceArtifactRevision":
        """The latest version of the item: the last revision, or the original."""
        return self.revisions[-1] if self.revisions else self

    @property
    def revision_count(self) -> int:
        """How many versions of the item are held, the original included."""
        return 1 + len(self.revisions)


class SourceArtifactRevision(Base):
    """A later version of a source item, as the source published it. Never modified."""

    __tablename__ = "source_artifact_revisions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "revision", name="uq_artifact_revisions_artifact_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.artifact_id"), index=True)
    # The original item is revision 1; the first revision stored here is 2.
    revision: Mapped[int] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    retrieved_at: Mapped[datetime] = mapped_column(UtcDateTime)
    raw_content: Mapped[dict[str, Any]] = mapped_column(JsonType)
    content_hash: Mapped[str] = mapped_column(String(64))
    classification: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
