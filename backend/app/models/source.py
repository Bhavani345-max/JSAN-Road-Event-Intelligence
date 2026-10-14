from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JsonType, UtcDateTime


class Source(Base):
    """Source registry entry, plus the state of polling it.

    The descriptive columns mirror `SourceDefinition` and are overwritten from
    the code registry on every start; the polling columns belong to the database.
    """

    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(200))
    organization: Mapped[str | None] = mapped_column(String(200))
    authority_type: Mapped[str | None] = mapped_column(String(64))
    source_tier: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str | None] = mapped_column(Text)
    endpoint: Mapped[str | None] = mapped_column(Text)
    access_method: Mapped[str | None] = mapped_column(Text)
    integration_status: Mapped[str] = mapped_column(String(32), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    polling_frequency_minutes: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(16))
    events_supported: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    parser_type: Mapped[str | None] = mapped_column(String(32))
    terms_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_retention: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Classification (migration 0003): what kind of body the source is, where
    # it is about, what it costs, what its terms say, what its records carry.
    source_class: Mapped[str | None] = mapped_column(String(32))
    country: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(64), index=True)
    cost_category: Mapped[str | None] = mapped_column(String(32))
    rate_limit: Mapped[str | None] = mapped_column(Text)
    terms_status: Mapped[str] = mapped_column(String(32), default="NOT_REVIEWED")
    licence: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    commercial_use: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    provides_geometry: Mapped[bool] = mapped_column(Boolean, default=False)
    provides_segments: Mapped[bool] = mapped_column(Boolean, default=False)
    provides_direction: Mapped[bool] = mapped_column(Boolean, default=False)
    real_time: Mapped[bool] = mapped_column(Boolean, default=False)
    discovery_only: Mapped[bool] = mapped_column(Boolean, default=False)

    last_poll_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_failure_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
