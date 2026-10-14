from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, JsonType, UtcDateTime


class JunctionReference(Base):
    """A junction name the resolver may use, once a reviewer has confirmed it."""

    __tablename__ = "junction_references"
    __table_args__ = (UniqueConstraint("city", "name_key", name="uq_junction_references_city_name"),)

    junction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(64))
    canonical_name: Mapped[str] = mapped_column(Text)
    name_key: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    osm_node_id: Mapped[int | None] = mapped_column(BigInteger)
    related_roads: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    source: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))
    confirmation_method: Mapped[str | None] = mapped_column(Text)
    reviewer: Mapped[str | None] = mapped_column(String(120))
    confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
