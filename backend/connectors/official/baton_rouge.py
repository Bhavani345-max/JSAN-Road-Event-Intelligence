"""City of Baton Rouge / Parish of East Baton Rouge road closures (21 October 2026).

    GET https://data.brla.gov/resource/ra2i-eye8.json?$limit=5000

The City-Parish Department of Transportation and Drainage (Traffic
Engineering) publishes its "active City-Parish road closures, road blocks,
and detours in East Baton Rouge Parish" with the street, the cross streets,
whether the closure is full or partial, the direction and the period, each
with its own lines (MultiLineString). On 21 October 2026: 30 closures
(CONSTRUCTION 27, BRIDGE 3; Full 14, Partial 13, Bridge 3), keyless.

Times are written with a "Z" (UTC) and read so. The rows carry no id (the
incident and permit columns are empty): a row is known by its street, cross
streets, period and line. The contact column is left out of the stored
evidence. The severity ("MAJOR") is the source's word, kept apart from REI's.

Public Domain (the dataset's licence on data.brla.gov, read 21 October 2026).
"""

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from packages.cities import get_city
from packages.common.hashing import sha256_hex
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

from .feature_feed import FeatureFeedConnector, clean, fetch_socrata_rows, item_record
from .feed_text import sentences, stretch

SOURCE_ID = "baton-rouge-road-closures"
ENDPOINT = "https://data.brla.gov/resource/ra2i-eye8.json"
SOURCE_URL = "https://data.brla.gov/d/ra2i-eye8"
ATTRIBUTION = (
    "Source: City of Baton Rouge / Parish of East Baton Rouge, Department of Transportation and "
    "Drainage, Traffic Engineering (data.brla.gov). Public domain."
)
# Columns not kept as evidence: a person or office to call.
PERSONAL = frozenset({"contact"})
LABELS = {"FULL": "Road closed", "PARTIAL": "Partial closure", "BRIDGE": "Bridge closure"}
# What a row is known by (the rows have no id), with its line.
KEY_FIELDS = ("street", "from_cross_street", "end_cross_street", "start_date", "end_date")


def baton_rouge_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-states")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Baton Rouge road closures (East Baton Rouge Parish)",
        organization=(
            "City of Baton Rouge / Parish of East Baton Rouge, Department of Transportation and "
            "Drainage, Traffic Engineering Division"
        ),
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Louisiana (Baton Rouge)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Socrata SODA JSON (dataset ra2i-eye8); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.BRIDGE_TUNNEL_RESTRICTION.value,
        ),
        parser_type="baton_rouge_road_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt asks for a crawl delay of 1 second.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Public Domain (dataset licence on data.brla.gov)",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each row as the dataset returns it (less its contact column) and the structured event."
        ),
        notes=(
            "The City-Parish's active road closures, each with its own lines. Fetched without a "
            "key on 21 October 2026: 30 closures (Full 14, Partial 13, Bridge 3). Times are UTC "
            "as written. No id in the data: a row is known by its street, period and line."
        ),
    )


def _time(value: Any) -> datetime | None:
    text = clean(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    # Only a time that states its zone ("Z") is taken.
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _event_type(closure: str, kind: str) -> str:
    if closure == "FULL":
        return EventType.PLANNED_ROAD_CLOSURE.value
    if closure == "PARTIAL":
        return EventType.LANE_RESTRICTION.value
    if closure == "BRIDGE" or kind == "BRIDGE":
        return EventType.BRIDGE_TUNNEL_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def record_key(row: dict[str, Any]) -> str:
    """A row's own key: what it closes, where and when (the rows have no id)."""
    return sha256_hex(
        "|".join(
            [clean(row.get(key)) for key in KEY_FIELDS]
            + [json.dumps(row.get("the_geom"), sort_keys=True)]
        )
    )[:24]


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    geometry = row.get("the_geom")
    street = clean(row.get("street"))
    if not isinstance(geometry, dict) or not street:
        return None
    place = stretch(street, clean(row.get("from_cross_street")), clean(row.get("end_cross_street")))
    closure, kind = clean(row.get("full_closure")).upper(), clean(row.get("type")).upper()
    label = LABELS.get(closure, closure.capitalize() or "Closure")
    direction = clean(row.get("direction"))
    structured = SourceEvent(
        event_type=_event_type(closure, kind),
        category=" / ".join(
            part
            for part in (clean(row.get(key)) for key in ("type", "subtype", "full_closure"))
            if part
        ),
        severity=clean(row.get("severity")) or None,
        start=_time(row.get("start_date")),
        end=_time(row.get("end_date")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street",
                geometry=geometry,
                direction=direction or None,
                closure=label,
            )
        ],
        affected_road=street,
        # Only "BOTH" names the directions; "ALL", "NORTH" and "EAST" are kept as written.
        direction="BOTH_DIRECTIONS" if direction.upper() == "BOTH" else None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    alternative = clean(row.get("alt_route"))
    summary = sentences(
        clean(row.get("description")),
        f"{label} ({clean(row.get('type')).capitalize()})" if kind else label,
        f"Direction: {direction}" if direction else "",
        f"Recurring: {clean(row.get('recurring'))}" if clean(row.get("recurring")) else "",
        f"Sidewalk: {clean(row.get('sidewalk'))}" if clean(row.get("sidewalk")) else "",
        f"Alternate route: {alternative}" if alternative and alternative.upper() != "N/A" else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=record_key(row),
        url=SOURCE_URL,
        title=f"{label}: {place} (Baton Rouge)",
        summary=summary,
        categories=[part.lower() for part in (clean(row.get("type")), label) if part],
        item={
            key: value
            for key, value in row.items()
            if key not in PERSONAL and not key.startswith(":@computed")
        },
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The dataset holds the active closures only (a few dozen); the run window drops ended ones.
    return fetch_socrata_rows(ENDPOINT, user_agent, client=client)


class BatonRougeRoadClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
