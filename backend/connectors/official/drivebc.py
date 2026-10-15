"""DriveBC Open511: British Columbia's road events (decision 0029).

    GET https://api.open511.gov.bc.ca/events?format=json&status=ACTIVE&limit=500

The Province's Open511 API lists every active event on BC highways and
roads: construction, incidents and road conditions, each with a line or a
point, its roads (with direction and whether they are closed) and its
schedule. On 15 October 2026: 298 events (220 in force, 78 planned), keyless,
no robots.txt.

Schedule times carry no offset and are UTC: "From 7:30 AM to 5:30 PM PDT" is
written 14:30/00:30 (checked against the descriptions on 15 October 2026),
although the API names America/Vancouver as its zone. Rest-area and washroom
closures are listed as incidents; they close no road and are left out.

Open Government Licence – British Columbia (https://api.open511.gov.bc.ca/help).
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record

SOURCE_ID = "drivebc-events"
ENDPOINT = "https://api.open511.gov.bc.ca/events"
PARAMS = {"format": "json", "status": "ACTIVE", "limit": "500"}
SOURCE_URL = "https://api.open511.gov.bc.ca/help"
ATTRIBUTION = (
    "Contains information licensed under the Open Government Licence – British Columbia "
    "(DriveBC Open511)."
)
DIRECTIONS = {
    "BOTH": "BOTH_DIRECTIONS",
    "N": "NORTHBOUND",
    "S": "SOUTHBOUND",
    "E": "EASTBOUND",
    "W": "WESTBOUND",
}
# Closures of a facility beside the road, not of the road.
NOT_ROAD_EVENTS = ("rest area closed", "washrooms closed")


def drivebc_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="DriveBC road events (British Columbia)",
        organization="Province of British Columbia, Ministry of Transportation and Transit (DriveBC)",
        authority_type="PROVINCIAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="British Columbia",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Open511 JSON API; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.ROAD_WORKS.value,
            EventType.ROAD_HAZARD.value,
        ),
        parser_type="drivebc_open511",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; the API terms allow the Province to impose limits without notice.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – British Columbia",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each Open511 event as the API returns it and the structured event derived from it.",
        notes=(
            "DriveBC's events on BC highways and roads, each with a line or point. Fetched "
            "without a key on 15 October 2026: 298 active events (220 in force, 78 planned). "
            "Schedule times are UTC. Rest-area and washroom closures are left out."
        ),
    )


def _time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # The API writes UTC without an offset (see the module notes).
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _period(schedule: Any) -> tuple[datetime | None, datetime | None]:
    """The first interval's start to the last interval's end; an open end stays open."""
    intervals = schedule.get("intervals") if isinstance(schedule, dict) else None
    if not intervals:
        return None, None
    starts, ends = [], []
    for interval in intervals:
        start, _, end = str(interval).partition("/")
        starts.append(_time(start))
        ends.append(_time(end) if end else None)
    known_starts = [s for s in starts if s]
    start = min(known_starts) if known_starts else None
    end = None if any(e is None for e in ends) else max(ends)
    return start, end


def _event_type(event: dict[str, Any], closed: bool) -> str:
    kind = clean(event.get("event_type")).upper()
    if kind == "CONSTRUCTION":
        return EventType.PLANNED_ROAD_CLOSURE.value if closed else EventType.ROAD_WORKS.value
    if closed:
        return EventType.EMERGENCY_ROAD_CLOSURE.value
    if kind == "SPECIAL_EVENT":
        return EventType.SPECIAL_EVENT.value
    return EventType.ROAD_HAZARD.value


def to_record(event: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    external_id = clean(event.get("id"))
    geometry = event.get("geography")
    description = clean(event.get("description"))
    if not external_id or not isinstance(geometry, dict):
        return None
    if description.lower().startswith(NOT_ROAD_EVENTS):
        return None
    roads = [road for road in event.get("roads") or [] if isinstance(road, dict)]
    closed = any(clean(road.get("state")).upper() == "CLOSED" for road in roads)
    start, end = _period(event.get("schedule"))
    road_names = [clean(road.get("name")) for road in roads if clean(road.get("name"))]
    direction = next(
        (DIRECTIONS[d] for road in roads if (d := clean(road.get("direction")).upper()) in DIRECTIONS),
        None,
    )
    # The headline is only the type word; the description's first sentence names the place.
    headline = description.split(". ", 1)[0].rstrip(".") if description else clean(event.get("headline"))
    subtypes = [clean(s) for s in event.get("event_subtypes") or [] if clean(s)]
    structured = SourceEvent(
        event_type=_event_type(event, closed),
        category=" / ".join([clean(event.get("event_type"))] + subtypes),
        severity=clean(event.get("severity")) or None,
        status=clean(event.get("status")) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(
                    part for part in (clean(road.get("name")), clean(road.get("from"))) if part
                ) or headline,
                kind="road",
                direction=DIRECTIONS.get(clean(road.get("direction")).upper()),
                closure=clean(road.get("state")) or None,
            )
            for road in roads
        ],
        affected_road=road_names[0] if road_names else None,
        direction=direction,
        attribution=ATTRIBUTION,
        reported_ended=clean(event.get("status")).upper() == "ARCHIVED",
        covers_city=True,
    )
    categories = [part.lower() for part in [clean(event.get("event_type")), *subtypes] if part]
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=clean(event.get("url")) or SOURCE_URL,
        title=headline[:200],
        summary=description,
        categories=categories,
        item=event,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(clean(event.get("updated"))),
    )


def fetch_events(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    events = body.get("events") if isinstance(body, dict) else None
    if not isinstance(events, list):
        raise ConnectorError(f"{ENDPOINT} did not return an Open511 event list")
    if len(events) >= int(PARAMS["limit"]):
        raise ConnectorError(f"{ENDPOINT} returned {PARAMS['limit']} events or more; the list is cut")
    return [event for event in events if isinstance(event, dict)]


class DriveBcEventsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_events)
    to_record = staticmethod(to_record)

