from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


# JSONB on PostgreSQL (indexable, and readable by PostGIS functions); plain JSON elsewhere.
# none_as_null: a missing value is stored as SQL NULL, not as the JSON literal `null`
# (which PostGIS would be asked to parse as a geometry).
JsonType = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")


class UtcDateTime(TypeDecorator):
    """A timestamp that is always timezone-aware UTC in Python.

    SQLite has no timezone support and hands back naive values; this stores
    UTC and re-attaches the timezone on the way out, so both databases behave
    the same.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime given; timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
