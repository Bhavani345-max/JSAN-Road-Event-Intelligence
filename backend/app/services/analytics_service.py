"""Event analytics for the console's Analytics page (decision 0051). Read only.

One pass over the light columns of the events the filters select (never an
event's full record or its article), counted with the same rules as the
console's coverage counts (`_tally_names`, decision 0034), so the two never
disagree. Nothing is written.

Definitions (also returned with every answer, so the page shows them):

- Events: stored events not merged into another (a merged report is part of
  the event it was merged into; its count is given separately).
- Status groups, mutually exclusive, adding up to Events:
  awaiting review (DISCOVERED, EXTRACTED, GEO_RESOLVED, VALIDATION_REQUIRED,
  QC_PENDING); validated (APPROVED, SCHEDULED, ACTIVE, MONITORING, EXTENDED,
  MODIFIED, REOPENED: given only by a reviewer); closed (EXPIRED, CANCELLED,
  SUPERSEDED); rejected (REJECTED).
- Subsets, overlapping the groups:
  published: validated events the operations map shows now (located, a stated
  start, not over: decision 0038);
  in the review queue: events awaiting review that the review queue lists now
  (located and not known to be over: decision 0038);
  GIS pending: events whose location is not confirmed: not located, located
  only approximately (a named place's position), or a road-network match
  awaiting a reviewer.
- Detected over time: by the day REI stored the event, in the answer's time
  zone; the date range selects on the same days.
"""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Event, Source, SourceArtifact
from app.repositories.events import _light_columns, _tally_names
from packages.cities import default_city
from packages.common.time import ensure_utc, utc_now
from services.lifecycle.current import CLOSED_STATUSES, OPERATIONAL_STATUSES, REVIEW_STATUSES

UNCLASSIFIED = "UNCLASSIFIED"
GROUPS = ("awaiting_review", "validated", "closed", "rejected")
GROUP_STATUSES = {
    "awaiting_review": sorted(status.value for status in REVIEW_STATUSES),
    "validated": sorted(status.value for status in OPERATIONAL_STATUSES),
    "closed": sorted(s.value for s in CLOSED_STATUSES if s.value != "REJECTED"),
    "rejected": ["REJECTED"],
}
# `_tally_names` keys, by status group.
_TALLY_GROUP = {"pending_review": "awaiting_review", "validated": "validated", "closed": "closed", "rejected": "rejected"}
# Location statuses that are not a confirmed position of the event.
GIS_PENDING_STATUSES = frozenset({"NOT_LOCATED", "APPROXIMATE", "GIS_PENDING"})
# More days than this are not drawn day by day.
MAX_DAYS = 731

DEFINITIONS = {
    "total": "Stored events, not counting reports merged into another event (each is part of that event).",
    "awaiting_review": "Detected and not yet decided by a reviewer: " + ", ".join(GROUP_STATUSES["awaiting_review"]) + ".",
    "validated": "Confirmed by a reviewer as a road event: " + ", ".join(GROUP_STATUSES["validated"]) + ".",
    "closed": "Over or replaced: " + ", ".join(GROUP_STATUSES["closed"]) + ".",
    "rejected": "Rejected: not a road event, or not one REI keeps.",
    "published": (
        "Of the validated events, those the operations map shows now: located, with a stated "
        "start, and not over. A subset of Validated."
    ),
    "in_review_queue": (
        "Of the events awaiting review, those the review queue lists now: located and not known "
        "to be over. A subset of Awaiting review."
    ),
    "gis_pending": (
        "Events whose location is not confirmed: not located, located only approximately at a "
        "named place, or matched to the road network and awaiting a reviewer. Overlaps every group."
    ),
    "detected_over_time": "Events by the day REI stored them, in the time zone shown; the date range uses the same days.",
}


def location_status(located: bool, location_class: str | None, gis_applied: bool | None, gis_review: str | None) -> str:
    """The console's location status (features/events/model.ts locationStatusOf)."""
    if not located:
        return "NOT_LOCATED"
    if gis_applied and gis_review == "PENDING":
        return "GIS_PENDING"
    if location_class == "UNRESOLVED":
        return "NOT_LOCATED"
    return location_class or "UNSPECIFIED"


def day_bounds(start: date | None, end: date | None, zone: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """The UTC instants a range of whole days in `zone` covers: [start 00:00, the day after end 00:00)."""
    since = datetime.combine(start, time.min, zone).astimezone(timezone.utc) if start else None
    until = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(timezone.utc) if end else None
    return since, until


def event_analytics(
    session: Session,
    *,
    cities: list[str] | None,
    start: date | None,
    end: date | None,
    zone: ZoneInfo,
    event_types: list[str],
    status_groups: list[str],
    source_ids: list[str],
    now: datetime | None = None,
) -> dict:
    now = ensure_utc(now) if now else utc_now()
    query = (
        select(
            *_light_columns(),
            Event.source_id,
            Event.city,
            Event.merged_into,
            Event.created_at,
            Event.detection["location_class"].as_string().label("location_class"),
            Event.detection["gis"]["applied"].as_boolean().label("gis_applied"),
            Event.detection["gis"]["review_status"].as_string().label("gis_review"),
        )
        .outerjoin(Event.artifact)
    )
    if cities is not None:
        condition = Event.city.in_(cities)
        if default_city().name in cities:
            condition = or_(condition, Event.city.is_(None))
        query = query.where(condition)
    since, until = day_bounds(start, end, zone)
    if since is not None:
        query = query.where(Event.created_at >= since)
    if until is not None:
        query = query.where(Event.created_at < until)
    if event_types:
        typed = [t for t in event_types if t != UNCLASSIFIED]
        condition = Event.event_type.in_(typed)
        if UNCLASSIFIED in event_types:
            condition = or_(condition, Event.event_type.is_(None))
        query = query.where(condition)
    if status_groups:
        query = query.where(Event.status.in_([s for g in status_groups for s in GROUP_STATUSES[g]]))
    if source_ids:
        query = query.where(Event.source_id.in_(source_ids))

    totals = Counter({name: 0 for name in (*GROUPS, "total", "published", "in_review_queue", "gis_pending", "merged")})
    by_city: Counter = Counter()
    by_category: Counter = Counter()
    by_status: Counter = Counter()
    by_location: Counter = Counter()
    by_day: Counter = Counter()
    city_groups: dict[str, Counter] = {}
    source_groups: dict[str, Counter] = {}
    recent_since = now - timedelta(days=7)
    legacy_city = default_city().name
    for row in session.execute(query):
        names = _tally_names(row, now, recent_since)
        if "merged" in names:
            totals["merged"] += 1
            continue
        group = next(_TALLY_GROUP[name] for name in names if name in _TALLY_GROUP)
        city = row.city or legacy_city
        totals["total"] += 1
        totals[group] += 1
        if "on_map_operations" in names:
            totals["published"] += 1
        if "listed_review" in names:
            totals["in_review_queue"] += 1
        status = location_status(bool(row.located), row.location_class, row.gis_applied, row.gis_review)
        if status in GIS_PENDING_STATUSES:
            totals["gis_pending"] += 1
        by_city[city] += 1
        by_category[row.event_type or UNCLASSIFIED] += 1
        by_status[row.status] += 1
        by_location[status] += 1
        by_day[ensure_utc(row.created_at).astimezone(zone).date()] += 1
        city_groups.setdefault(city, Counter())[group] += 1
        source_groups.setdefault(row.source_id, Counter())[group] += 1

    names = dict(session.execute(select(Source.source_id, Source.source_name)).all())
    return {
        "generated_at": now,
        "time_zone": zone.key,
        "definitions": DEFINITIONS,
        "totals": dict(totals),
        "by_city": _ranked(by_city),
        "by_category": _ranked(by_category),
        "by_status": _ranked(by_status),
        "by_location": _ranked(by_location),
        "by_day": _days(by_day, start, end),
        "validation_by_city": [
            {"key": city, **{g: counts[g] for g in GROUPS}}
            for city, counts in sorted(city_groups.items(), key=lambda item: -sum(item[1].values()))
        ],
        "by_source": [
            {
                "source_id": source_id,
                "source_name": names.get(source_id, source_id),
                "total": sum(counts.values()),
                **{g: counts[g] for g in GROUPS},
            }
            for source_id, counts in sorted(source_groups.items(), key=lambda item: -sum(item[1].values()))
        ],
    }


def _ranked(counts: Counter) -> list[dict]:
    return [{"key": key, "count": count} for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))]


def _days(counts: Counter, start: date | None, end: date | None) -> list[dict]:
    """Every day from the range's (or the data's) first to last, days without events as 0."""
    if not counts and not (start and end):
        return []
    first = start or min(counts)
    last = end or max(counts)
    if counts:
        first, last = min(first, min(counts)), max(last, max(counts))
    if (last - first).days >= MAX_DAYS:
        first = last - timedelta(days=MAX_DAYS - 1)
    return [
        {"date": (first + timedelta(days=offset)).isoformat(), "count": counts.get(first + timedelta(days=offset), 0)}
        for offset in range((last - first).days + 1)
    ]
