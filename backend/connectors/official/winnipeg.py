"""City of Winnipeg lane closures (decision 0029).

    GET https://data.winnipeg.ca/resource/h367-iifg.json?$limit=5000&$where=...

Public Works lists every lane and street closure with its street, the
stretch, the direction, whether the street is fully closed and the dates,
each with its own lines. On 15 October 2026: 794 closures (593 in force, 108
planned, 93 ended), keyless.

Dates are Winnipeg local days with the hours as text ("09:00 AM"). An
indefinite closure carries the end date 2099-01-01, which the system demands
("End date is not applicable but is a requirement of the lane closure
system"): that is no stated end. Closures of only a sidewalk, a path, parking
or a loading zone close no traffic lane and are left out.

Open Government Licence – Winnipeg.
"""

import re
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import httpx

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

from .feature_feed import FeatureFeedConnector, clean, fetch_socrata_rows, item_record, local_day

SOURCE_ID = "winnipeg-lane-closures"
ENDPOINT = "https://data.winnipeg.ca/resource/h367-iifg.json"
SOURCE_URL = "https://data.winnipeg.ca/d/h367-iifg"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – Winnipeg."
WINNIPEG = ZoneInfo("America/Winnipeg")
# The system's stand-in for "no end".
NO_END_YEAR = 2099
# What a closure of traffic says; without it (and not a full closure) only a
# sidewalk, a path, parking or a loading zone is closed.
TRAFFIC_WORDS = re.compile(r"\b(lane|lanes|street|road|traffic|turn|turns|bridge|ramp|detour)\b")
DIRECTIONS = {
    "northbound": "NORTHBOUND",
    "southbound": "SOUTHBOUND",
    "eastbound": "EASTBOUND",
    "westbound": "WESTBOUND",
}


def winnipeg_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Winnipeg lane closures",
        organization="City of Winnipeg, Public Works",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Manitoba",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Socrata SODA JSON (dataset h367-iifg); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.TURN_RESTRICTION.value,
        ),
        parser_type="winnipeg_lane_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – Winnipeg",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=False,
        evidence_retention="Each closure as the dataset returns it and the structured event derived from it.",
        notes=(
            "Public Works' lane and street closures, each with its own lines. Fetched without a "
            "key on 15 October 2026: 794 closures (593 in force, 108 planned). Updated daily. "
            "The 2099 end date the system demands is read as no stated end."
        ),
    )


def _clock(value: Any) -> time | None:
    try:
        return datetime.strptime(clean(value).upper(), "%I:%M %p").time()
    except ValueError:
        return None


def _moment(day: date | None, clock: time | None, *, end: bool) -> datetime | None:
    if day is None:
        return None
    if clock is None:
        clock = time(23, 59, 59) if end else time.min
    return datetime.combine(day, clock, tzinfo=WINNIPEG)


def period(row: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    first = local_day(row.get("date_closed_from"), WINNIPEG)
    last = local_day(row.get("date_closed_to"), WINNIPEG)
    if last is not None and last.year >= NO_END_YEAR:
        last = None
    start = _moment(first, _clock(row.get("time_closed_from")), end=False)
    end = _moment(last, _clock(row.get("time_closed_to")), end=True)
    # "12:00 AM to 12:00 AM" on one day states the day, not an empty period.
    if start and end and end <= start:
        end = _moment(last, None, end=True)
    return start, end


def _direction(text: str) -> str | None:
    found = {value for word, value in DIRECTIONS.items() if word in text.lower()}
    if len(found) > 1:
        return "BOTH_DIRECTIONS"
    return found.pop() if found else None


def closes_traffic(row: dict[str, Any]) -> bool:
    if clean(row.get("complete_closure")).lower() == "yes":
        return True
    return bool(TRAFFIC_WORDS.search(clean(row.get("traffic_effect")).lower()))


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    external_id = clean(row.get("lane_closure_id"))
    geometry = row.get("geometry")
    if not external_id or not isinstance(geometry, dict) or not closes_traffic(row):
        return None
    street = clean(row.get("primary_street"))
    stretch = clean(row.get("boundaries")) or clean(row.get("cross_street"))
    effect = clean(row.get("traffic_effect"))
    full = clean(row.get("complete_closure")).lower() == "yes"
    if full:
        event_type = EventType.PLANNED_ROAD_CLOSURE.value
    elif re.search(r"\bturns?\b", effect.lower()):
        event_type = EventType.TURN_RESTRICTION.value
    else:
        event_type = EventType.LANE_RESTRICTION.value
    start, end = period(row)
    direction = _direction(clean(row.get("direction")))
    structured = SourceEvent(
        event_type=event_type,
        category="Complete closure" if full else "Lane closure",
        status=clean(row.get("status")) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (street, stretch) if part),
                kind="street",
                geometry=geometry,
                direction=direction,
                closure="complete closure" if full else "lane closure",
            )
        ]
        if street
        else [],
        affected_road=street or None,
        direction=direction,
        attribution=ATTRIBUTION,
        reported_ended=clean(row.get("status")).lower() == "expired",
        covers_city=True,
    )
    by = clean(row.get("organization"))
    summary = ". ".join(part for part in (effect, f"Works by: {by}" if by else "") if part)
    label = "Street closed" if full else "Lane closure"
    title = ": ".join(part for part in (label, ", ".join(p for p in (street, stretch) if p)) if part)
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{title} (Winnipeg)",
        summary=summary,
        categories=[structured.category.lower()],
        item={key: value for key, value in row.items() if key != "kml"},
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    today = (now or datetime.now(WINNIPEG)).astimezone(WINNIPEG).date().isoformat()
    return fetch_socrata_rows(
        ENDPOINT,
        user_agent,
        client=client,
        where=f"status != 'Expired' AND date_closed_to >= '{today}'",
    )


class WinnipegLaneClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
