"""City of Burlington (Ontario) road closures (5 November 2026).

    GET https://services1.arcgis.com/xbWF6o8qyXoMFa8L/arcgis/rest/services/
        Road_Closures_Open_Date_View/FeatureServer/1/query

"Current and planned road closures for the City of Burlington" (ArcGIS item
9aaba30995b84dc1a336f54d2fe7ec24, owner GISCOB; the layer the City also
gives to Waze), one line each: the road (`blocknm`), a description
(`locdesc`), the reason (`blocktype`: Construction, Event, Incident,
Maintenance, Permit, Other), whether the road is fully closed (`fullclose`
Yes/No), the direction (`direction`: Both, East, North, South, West),
recurring or continuous (`blockoccur`) and the period. The layer keeps past
closures too: on 5 November 2026, 92 lines, of which 82 had ended, 6 were
current (lane restrictions on Waterdown, Snake, Blair and Landmark Roads)
and 4 were empty rows (no road, no dates, nothing stated) that are left out.
None was upcoming.

`startdate`/`enddate` are milliseconds since 1970 (UTC) with their times.
`active` (Yes/No) is kept in the evidence but not read: its meaning is not
stated, and on 5 November 2026 62 of the 82 ended lines said Yes and 5 of
the 6 current ones No. Only "Both" names the directions; "East", "North" ...
stay the City's word on the location (a side or a travel direction is not
said). `pocname` and `pocemail` name City staff with their e-mail addresses:
personal data, not kept.

Creative Commons Attribution 4.0 International (the item's licence, read 5
November 2026; credit: "City of Burlington").
"""

from datetime import datetime
from typing import Any

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

from .feature_feed import FeatureFeedConnector, clean, epoch_ms, fetch_arcgis_features, item_record
from .feed_text import sentences

SOURCE_ID = "ca-burlington-road-closures"
SOURCE_URL = (
    "https://services1.arcgis.com/xbWF6o8qyXoMFa8L/arcgis/rest/services/"
    "Road_Closures_Open_Date_View/FeatureServer"
)
LAYER = f"{SOURCE_URL}/1"
ITEM_URL = "https://www.arcgis.com/home/item.html?id=9aaba30995b84dc1a336f54d2fe7ec24"
ATTRIBUTION = "City of Burlington, Road Closures Open Data View. Licence CC BY 4.0."
# Columns not kept as evidence: staff names and e-mail addresses.
PERSONAL = frozenset({"pocname", "pocemail"})


def burlington_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Burlington road closures",
        organization="City of Burlington (Ontario)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Ontario (Burlington)",
        city=country.id,
        source_url=ITEM_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service (ArcGIS Online), GeoJSON; no key",
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
        parser_type="burlington_road_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "Creative Commons Attribution 4.0 International (CC BY 4.0), the ArcGIS item's licence "
            "(9aaba30995b84dc1a336f54d2fe7ec24)"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=False,
        evidence_retention=(
            "Each closure as the service returns it, less its staff name and e-mail columns, "
            "and the structured event."
        ),
        notes=(
            "The City's current, planned and past road closures, one line each. Fetched without a "
            "key on 5 November 2026: 92 lines; 82 ended, 4 empty rows left out, 6 current. Times "
            "are UTC milliseconds."
        ),
    )


def _event_type(reason: str, full: str) -> str:
    if reason == "EVENT":
        return EventType.SPECIAL_EVENT.value
    if full == "YES":
        if reason == "INCIDENT":
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if full == "NO":
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("GlobalID"))
    road = clean(properties.get("blocknm"))
    # A row that names no road states nothing to take.
    if not external_id or not road:
        return None
    reason = clean(properties.get("blocktype"))
    full = clean(properties.get("fullclose"))
    direction = clean(properties.get("direction"))
    occurrence = clean(properties.get("blockoccur"))
    event_type = _event_type(reason.upper(), full.upper())
    closure = {"YES": "Full closure", "NO": "Not a full closure"}.get(full.upper())
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (reason, closure, occurrence) if part) or None,
        start=epoch_ms(properties.get("startdate")),
        end=epoch_ms(properties.get("enddate")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=road,
                kind="street",
                geometry=geometry,
                direction=direction or None,
                closure=closure,
            )
        ],
        affected_road=road,
        direction="BOTH_DIRECTIONS" if direction.upper() == "BOTH" else None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    label = {
        EventType.SPECIAL_EVENT.value: "Event",
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
        EventType.EMERGENCY_ROAD_CLOSURE.value: "Road closed",
        EventType.LANE_RESTRICTION.value: "Lane restriction",
    }.get(event_type, "Road works")
    summary = sentences(
        clean(properties.get("locdesc")),
        clean(properties.get("comment")),
        f"Reason: {reason}" if reason else "",
        f"Full closure: {full}" if full else "",
        f"Direction: {direction}" if direction else "",
        f"Duration: {occurrence}" if occurrence else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=ITEM_URL,
        title=f"{label}: {road} (Burlington)",
        summary=summary,
        categories=[part.lower() for part in (reason, label) if part],
        item={**feature, "properties": {k: v for k, v in properties.items() if k not in PERSONAL}},
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The layer keeps past closures too (92 lines on 5 November 2026); the run window drops them.
    return fetch_arcgis_features(LAYER, user_agent, client=client)


class BurlingtonRoadClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
