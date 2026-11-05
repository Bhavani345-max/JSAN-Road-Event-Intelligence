"""Region of Waterloo road closures, current and future (5 November 2026).

    GET https://utility.arcgis.com/usrsvcs/servers/fe45821bc236443d84b5fc3698f583bf/
        rest/services/OpenData/OpenData/MapServer/24/query   ("Road Closures - Current")
    GET https://utility.arcgis.com/usrsvcs/servers/737980ba63a34f9ca0cb8e1b5cea6c6d/
        rest/services/OpenData/OpenData/MapServer/25/query   ("Road Closures - Future")

The Region's closures on Regional roads in its seven municipalities
(Kitchener, Cambridge, Waterloo, Woolwich, Wilmot, Wellesley, North
Dumfries), published as two layers of one source: the closures in place
(`CLOSURE_SCHEDULED` "Existing") and those to come ("Future"). Each has its
line, the street and the stretch (`STREET_NAME`, `STREET_FROM`, `STREET_TO`;
a number in brackets after a name, "Frederick St(6)", is the Region's and is
kept in the evidence only), the municipality, a status ("Closed", "Partially
Closed", "Lane Reduced", "No Closure"), the reason, details, a detour, the
body doing the work (`ORGANIZATION`: the Region, a township, a city, MTO)
and the period. On 5 November 2026: 88 closures (62 current, 26 upcoming,
none ended; one states no end), keyless; 11 state "No Closure" ("No lane
closures; work occurring off road") and are left out, as are sidewalk and
trail closures (as for Kitchener): 77 kept.

`DATE_FROM`/`DATE_TO` are milliseconds since 1970 (UTC) with their times.
`CONTACT` names staff with e-mail addresses and telephone numbers; the
licence does not cover personal information, so it is not kept.

Overlap with the City feeds REI connects (`kitchener-traffic-closures`,
`cambridge-on-road-closures`): a Region closure in Kitchener or Cambridge is
left out when that City's feed, as REI reads it now, lists the same closure:
the same street between the same two streets (either order; names compared
without the Region's bracketed numbers, case or punctuation) and, where
both state a whole period, periods that meet. Each run reads both City
layers for this (two more requests); if either cannot be read the run fails
rather than risk storing a closure twice. On 5 November 2026 none of the 22
Kitchener and 23 Cambridge Region closures was in a City feed: Cambridge's
layer is "traffic closures on City Owned Roads" (its item points to the
Region for Regional roads), and all 34 of Kitchener's closures were the
City's own (`ORGANIZATION` "Kitchener"). So 0 were left out that day.

Region of Waterloo Open Data Licence v.2.0
(https://www.regionofwaterloo.ca/en/regional-government/open-data.aspx#Open-Data-Licence,
read 5 November 2026): "Use the Information commercially"; no credit
required; the credit the licence asks for when one is given is used below.
"""

import re
from datetime import datetime
from typing import Any

import httpx

from packages.cities import get_city
from packages.common.time import utc_now
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

from . import cambridge_on, kitchener
from .feature_feed import FeatureFeedConnector, clean, epoch_ms, fetch_arcgis_features, item_record
from .feed_text import sentences, stretch

SOURCE_ID = "ca-waterloo-region-road-closures"
CURRENT_LAYER = (
    "https://utility.arcgis.com/usrsvcs/servers/fe45821bc236443d84b5fc3698f583bf/"
    "rest/services/OpenData/OpenData/MapServer/24"
)
FUTURE_LAYER = (
    "https://utility.arcgis.com/usrsvcs/servers/737980ba63a34f9ca0cb8e1b5cea6c6d/"
    "rest/services/OpenData/OpenData/MapServer/25"
)
SOURCE_URL = "https://www.arcgis.com/home/item.html?id=fe45821bc236443d84b5fc3698f583bf"
LICENCE_URL = (
    "https://www.regionofwaterloo.ca/en/regional-government/open-data.aspx#Open-Data-Licence"
)
# The licence's own words for a credit, which it does not require.
ATTRIBUTION = (
    "Contains information provided by the Regional Municipality of Waterloo under licence."
)
# Columns not kept as evidence: staff names, e-mail addresses and telephone numbers.
PERSONAL = frozenset({"CONTACT"})
NOT_ROADS = {"SIDEWALK", "TRAIL"}
NO_CLOSURE = "NO CLOSURE"
CLOSED = {"CLOSED", "LOCAL ACCESS ONLY", "NO THROUGH TRAFFIC"}
PARTLY = {"PARTIALLY CLOSED", "LANE REDUCED"}
# The City feeds REI connects, by the municipality the Region names.
CITY_FEEDS = {
    "KITCHENER": (kitchener.LAYER, kitchener.to_record),
    "CAMBRIDGE": (cambridge_on.LAYER, cambridge_on.to_record),
}
_REGION_NUMBER = re.compile(r"\s*\(\d+\)")


def waterloo_region_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Region of Waterloo road closures (current and future)",
        organization="Regional Municipality of Waterloo, Transportation Services",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Ontario (Region of Waterloo)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=CURRENT_LAYER,
        access_method=(
            "Two ArcGIS map service layers (current 24, future 25), GeoJSON; no key; the Kitchener "
            "and Cambridge closure layers are read to leave out what they already list"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="waterloo_region_road_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly (four requests: two Region, two City layers).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Region of Waterloo Open Data Licence v.2.0 ({LICENCE_URL})",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each closure as the service returns it, less its contact column, and the structured "
            "event."
        ),
        notes=(
            "The Region's closures on Regional roads, current and future, one line each. Fetched "
            "without a key on 5 November 2026: 88 closures (62 current, 26 upcoming); the 11 with "
            "No Closure are left out, 77 kept. Closures the Kitchener or Cambridge feed already "
            "lists are left out (none that day). Times are UTC milliseconds."
        ),
    )


# --- the same closure in a City feed ------------------------------------------------------


def street_key(name: Any) -> str:
    """A street name as compared across feeds: no bracketed number, case or punctuation."""
    text = _REGION_NUMBER.sub("", clean(name)).upper()
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", text).split())


def closure_key(street: Any, start_at: Any, end_at: Any) -> tuple[str, frozenset[str]] | None:
    """The street and the two streets it runs between, in either order."""
    name = street_key(street)
    if not name:
        return None
    return name, frozenset(part for part in (street_key(start_at), street_key(end_at)) if part)


def _meet(first: tuple, second: tuple) -> bool:
    """Whether two periods (start, end) meet; True when either is not stated in full."""
    (a_start, a_end), (b_start, b_end) = first, second
    if None in (a_start, a_end, b_start, b_end):
        return True
    return a_start <= b_end and b_start <= a_end


def _key_of(feature: dict[str, Any]) -> tuple[str, frozenset[str]] | None:
    properties = feature.get("properties") or {}
    return closure_key(
        properties.get("STREET_NAME"), properties.get("STREET_FROM"), properties.get("STREET_TO")
    )


def city_closures(user_agent: str, *, client: httpx.Client | None = None, now: datetime) -> dict:
    """{municipality: [(key, (start, end))]}: the closures each City feed lists now,
    as REI's connector for it reads them (what it leaves out or has ended is not counted)."""
    listed: dict[str, list] = {}
    for municipality, (layer, read) in CITY_FEEDS.items():
        entries = []
        for feature in fetch_arcgis_features(layer, user_agent, client=client):
            record = read(feature, now)
            if record is None:
                continue
            start, end = record.structured.start, record.structured.end
            if (key := _key_of(feature)) is not None and (end is None or end >= now):
                entries.append((key, (start, end)))
        listed[municipality] = entries
    return listed


def carried_by_city(feature: dict[str, Any], listed: dict) -> bool:
    """Whether the City feed of the closure's municipality already lists the same closure."""
    properties = feature.get("properties") or {}
    municipality = clean(properties.get("MUNICIPALITY")).upper()
    key = _key_of(feature)
    if key is None or municipality not in listed:
        return False
    period = (epoch_ms(properties.get("DATE_FROM")), epoch_ms(properties.get("DATE_TO")))
    return any(
        key == city_key and _meet(period, city_period)
        for city_key, city_period in listed[municipality]
    )


# --- one closure ------------------------------------------------------------------------


def _event_type(status: str, reason: str, emergency: bool) -> str:
    if reason == "SPECIAL EVENT":
        return EventType.SPECIAL_EVENT.value
    if status in CLOSED:
        if emergency:
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if status in PARTLY:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _plain(name: Any) -> str:
    return _REGION_NUMBER.sub("", clean(name))


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("CLOSURE_ID"))
    status = clean(properties.get("STATUS"))
    kind = clean(properties.get("CLOSURE_TYPE"))
    if not external_id or kind.upper() in NOT_ROADS or status.upper() == NO_CLOSURE:
        return None
    street = _plain(properties.get("STREET_NAME"))
    start_at, end_at = _plain(properties.get("STREET_FROM")), _plain(properties.get("STREET_TO"))
    place = stretch(street, start_at, end_at)
    reason = clean(properties.get("REASON"))
    emergency_reason = clean(properties.get("EMERGENCY_REASON"))
    schedule = clean(properties.get("CLOSURE_SCHEDULED"))
    municipality = clean(properties.get("MUNICIPALITY"))
    event_type = _event_type(
        status.upper(), reason.upper(), reason.upper() == "EMERGENCY" or bool(emergency_reason)
    )
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (kind, reason, status) if part),
        status=" / ".join(part for part in (status, schedule) if part) or None,
        start=epoch_ms(properties.get("DATE_FROM")),
        end=epoch_ms(properties.get("DATE_TO")),
        geometry=geometry,
        locations=[
            SourceLocation(name=place, kind="street", geometry=geometry, closure=status or None)
        ]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        reported_ended=schedule.upper() == "COMPLETED",
        covers_city=True,
    )
    detour = clean(properties.get("DETOUR"))
    described = clean(properties.get("Description"))
    organisation = clean(properties.get("ORGANIZATION"))
    summary = sentences(
        clean(properties.get("DETAILS")),
        f"Detour: {detour}" if detour else "",
        f"Reason: {reason}" if reason else "",
        f"Emergency: {emergency_reason}" if emergency_reason else "",
        f"Location: {described}" if described and described != place else "",
        f"Work by: {organisation}" if organisation else "",
    )
    where = ", ".join(part for part in (municipality, "Region of Waterloo") if part)
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        # Without a status, the layer's own name for what it lists.
        title=f"{status or 'Road closure'}: {place or 'Regional road'} ({where})",
        summary=summary,
        categories=[part.lower() for part in (reason, status) if part],
        item={**feature, "properties": {k: v for k, v in properties.items() if k not in PERSONAL}},
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("Edit_Date")),
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    now = now or utc_now()
    # Both layers hold a few dozen closures each; a closure keeps its id when it moves
    # from the future layer to the current one, so it is taken once.
    seen: set[str] = set()
    region = []
    for layer in (CURRENT_LAYER, FUTURE_LAYER):
        for feature in fetch_arcgis_features(layer, user_agent, client=client):
            closure = clean((feature.get("properties") or {}).get("CLOSURE_ID"))
            if closure and closure in seen:
                continue
            seen.add(closure)
            region.append(feature)
    listed = city_closures(user_agent, client=client, now=now)
    return [feature for feature in region if not carried_by_city(feature, listed)]


class WaterlooRegionRoadClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
