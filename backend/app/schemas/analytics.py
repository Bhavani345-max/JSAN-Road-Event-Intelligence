from datetime import datetime

from pydantic import BaseModel


class CountOut(BaseModel):
    key: str
    count: int


class DayCountOut(BaseModel):
    # YYYY-MM-DD, in the answer's time zone.
    date: str
    count: int


class GroupCountsOut(BaseModel):
    """Events by mutually exclusive status group."""

    awaiting_review: int
    validated: int
    closed: int
    rejected: int


class CityGroupsOut(GroupCountsOut):
    key: str


class SourceGroupsOut(GroupCountsOut):
    source_id: str
    source_name: str
    total: int


class AnalyticsTotalsOut(GroupCountsOut):
    # total = awaiting_review + validated + closed + rejected.
    total: int
    # Subsets, overlapping the groups (see `definitions`).
    published: int
    in_review_queue: int
    gis_pending: int
    # Reports merged into another event: not in `total`.
    merged: int


class AnalyticsOut(BaseModel):
    """GET /api/events/analytics: counts for the Analytics page (decision 0051). Read only."""

    generated_at: datetime
    time_zone: str
    # What each number counts, in words (shown by the page).
    definitions: dict[str, str]
    totals: AnalyticsTotalsOut
    by_city: list[CountOut]
    by_category: list[CountOut]
    by_status: list[CountOut]
    by_location: list[CountOut]
    by_day: list[DayCountOut]
    validation_by_city: list[CityGroupsOut]
    by_source: list[SourceGroupsOut]
