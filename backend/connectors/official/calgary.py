"""City of Calgary construction detours and closures (decision 0029).

    GET https://data.calgary.ca/resource/w8zq-79bq.json?$limit=5000&$where=end_dt > '...'

The City's "scheduled road closures due to construction, planned maintenance
and utility work", updated twice a day (3 am and 3 pm), each at a point with
the location, what is closed and the start and end. On 15 October 2026: 235
records (177 in force, 50 planned, 8 ended), keyless.

The dataset has no type, status or id: the table is rebuilt at each refresh.
A row is known here by its location, description, period and point. The City
lists one closure in several rows (one per direction or lane, or the same
closure worded twice): rows at the same point over the same period are
one event (`same_place_and_period_key`, merge_service). Times are
local Calgary time without an offset.

Open Government Licence – City of Calgary.
"""

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.time import ensure_utc
from packages.event_schema import EventType, ReiEvent
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

from .feature_feed import FeatureFeedConnector, clean, fetch_socrata_rows, item_record, local_time

SOURCE_ID = "calgary-construction-detours"
ENDPOINT = "https://data.calgary.ca/resource/w8zq-79bq.json"
SOURCE_URL = "https://data.calgary.ca/d/w8zq-79bq"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – City of Calgary."
CALGARY = ZoneInfo("America/Edmonton")
TIME_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S")


def calgary_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Calgary construction detours and closures",
        organization="City of Calgary, Mobility",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Alberta",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Socrata SODA JSON (dataset w8zq-79bq); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="calgary_construction_detours",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – City of Calgary",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each record as the dataset returns it and the structured event derived from it.",
        notes=(
            "The City's scheduled closures for construction, maintenance and utility work, each "
            "at a point. Fetched without a key on 15 October 2026: 235 records (177 in force, "
            "50 planned). No id in the data: a record is known by location, start and point."
        ),
    )


def _text(value: Any) -> str:
    """The description, without the stray characters left where bullets were."""
    return clean(str(value or "").replace("�", " ").replace("¿", " "))


def _event_type(description: str) -> str:
    text = description.lower()
    if re.search(r"\b(road|street|avenue|ramp|bridge)\s+(closure|closed)\b|\bfull closure\b", text):
        return EventType.PLANNED_ROAD_CLOSURE.value
    if re.search(r"\blanes?\b", text):
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def record_key(row: dict[str, Any]) -> str:
    """A row's own key: what it says, where and when (the table has no id)."""
    point = row.get("point") if isinstance(row.get("point"), dict) else {}
    return sha256_hex(
        "|".join(
            [
                clean(row.get("construction_info")),
                _text(row.get("description")),
                clean(row.get("start_dt")),
                clean(row.get("end_dt")),
                str(point.get("coordinates")),
            ]
        )
    )[:24]


def same_place_and_period_key(event: ReiEvent, _external_id: str | None) -> str | None:
    """What the rows of one closure share: the point and the period.

    The City words one closure's location differently from row to row ("36
    Street between 32 and 26 Avenue NE", "36 ST NE at Sunridge Way") but
    places them at the same point.
    """
    if event.geometry is None or event.start_time is None or event.end_time is None:
        return None
    start, end = (
        ensure_utc(moment).strftime("%Y-%m-%d %H:%M") for moment in (event.start_time, event.end_time)
    )
    spot = json.dumps(event.geometry.model_dump(mode="json")["coordinates"])
    return f"{spot}, {start} to {end} UTC"


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    point = row.get("point")
    location = clean(row.get("construction_info"))
    if not isinstance(point, dict) or not location:
        return None
    description = _text(row.get("description"))
    structured = SourceEvent(
        event_type=_event_type(description),
        category="Construction detour",
        start=local_time(row.get("start_dt"), CALGARY, TIME_FORMATS),
        end=local_time(row.get("end_dt"), CALGARY, TIME_FORMATS),
        geometry=point,
        locations=[SourceLocation(name=location, kind="location", geometry=point, closure=description or None)],
        affected_road=location,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=record_key(row),
        url=SOURCE_URL,
        title=f"{description[:120] or 'Construction'}: {location} (Calgary)",
        summary=description,
        categories=["construction detour"],
        item={key: value for key, value in row.items() if not key.startswith(":@computed")},
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_detours(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    local_now = (now or datetime.now(CALGARY)).astimezone(CALGARY).strftime("%Y-%m-%dT%H:%M:%S")
    return fetch_socrata_rows(ENDPOINT, user_agent, client=client, where=f"end_dt > '{local_now}'")


class CalgaryConstructionDetoursConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_detours)
    to_record = staticmethod(to_record)
