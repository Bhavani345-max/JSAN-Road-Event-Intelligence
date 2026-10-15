"""City of Gold Coast temporary road closures (decision 0029).

    GET https://services.arcgis.com/3vStCH7NDoBOZ5zn/arcgis/rest/services/Temporary_Road_Closure/FeatureServer/0/query

The City's permits for temporary road closures, each road segment with its
own line, the street, the suburb, the extent of the closure and its dates.
On 15 October 2026: 1,275 segments, 1,207 not yet ended, keyless. Closures of
only a footpath or a parking lane (579) close no traffic lane and are left
out.

Dates are days (stored as the local midnight, Queensland time UTC+10); the
daily hours are free text. A permit can list several segments: each is its
own closure at its own place. In some rows the street and the permit number
are swapped; they are put back.

Creative Commons Attribution 3.0 Unported (the service's item information).
"""

import re
from datetime import datetime, timedelta
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

from .feature_feed import (
    FeatureFeedConnector,
    clean,
    fetch_arcgis_features,
    item_record,
    local_day,
    whole_days,
)

SOURCE_ID = "gold-coast-temporary-road-closures"
LAYER = "https://services.arcgis.com/3vStCH7NDoBOZ5zn/arcgis/rest/services/Temporary_Road_Closure/FeatureServer/0"
SOURCE_URL = (
    "https://services.arcgis.com/3vStCH7NDoBOZ5zn/arcgis/rest/services/Temporary_Road_Closure/FeatureServer"
)
ATTRIBUTION = "Source: City of Gold Coast, temporary road closures. Licensed under CC BY 3.0."
BRISBANE = ZoneInfo("Australia/Brisbane")
NOT_TRAFFIC = {"FOOTPATH", "PARKING LANE"}
PERMIT = re.compile(r"^TRC", re.IGNORECASE)
EXTENT_LABELS = {
    "FULL CLOSURE": "Road closed",
    "PART CLOSURE": "Part closure",
    "HOLD AND RELEASE": "Hold and release",
    "MULTIPLE LONG TERM IMPACTS": "Long-term works",
}


def gold_coast_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("australia")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Gold Coast temporary road closures",
        organization="City of Gold Coast",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Queensland",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service, GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="gold_coast_temp_road_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 3.0 Unported",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each closure segment as the service returns it and the structured event.",
        notes=(
            "The City's temporary road closure permits, one line per road segment. Fetched "
            "without a key on 15 October 2026: 1,275 segments, 1,207 not yet ended; footpath and "
            "parking-lane closures are left out. Dates are whole days in Queensland time."
        ),
    )


def _event_type(extent: str, category: str) -> str:
    if category in ("SPECIAL EVENT", "FILMING"):
        return EventType.SPECIAL_EVENT.value
    if extent == "FULL CLOSURE":
        return EventType.PLANNED_ROAD_CLOSURE.value
    if extent in ("PART CLOSURE", "HOLD AND RELEASE"):
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("GlobalID"))
    extent = clean(properties.get("CLOSURE_EXTENT")).upper()
    if not external_id or extent in NOT_TRAFFIC:
        return None
    street, permit = clean(properties.get("STREET")), clean(properties.get("TRC_ID"))
    if PERMIT.match(street) and not PERMIT.match(permit):
        street, permit = permit, street
    suburb = clean(properties.get("SUBURB"))
    # Names come in capitals: written as names.
    street, suburb = (name.title() if name.isupper() else name for name in (street, suburb))
    category = clean(properties.get("CLOSURE_CATEGORY")).upper()
    start, end = whole_days(
        local_day(properties.get("START_DATE"), BRISBANE),
        local_day(properties.get("FINISH_DATE"), BRISBANE),
        BRISBANE,
    )
    label = EXTENT_LABELS.get(extent, extent.capitalize() or "Closure")
    place = ", ".join(part for part in (street, suburb) if part)
    hours = clean(properties.get("OPERATION_TIMES"))
    structured = SourceEvent(
        event_type=_event_type(extent, category),
        category=" / ".join(part for part in (category.capitalize(), label) if part),
        status="active" if clean(properties.get("ACTIVE_CLOSURE")).lower() == "yes" else None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="road segment", geometry=geometry, closure=label)]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    summary = ". ".join(
        part
        for part in (
            f"{label} ({category.capitalize()})" if category else label,
            f"Hours: {hours}" if hours else "",
            clean(properties.get("COMMENTS")),
            f"Permit {permit}" if permit else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {place} (Gold Coast)",
        summary=summary,
        categories=[part.lower() for part in (category, label) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # Finishing today or later: a day's closure ends at that day's end.
    since = ((now or datetime.now(BRISBANE)) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    return fetch_arcgis_features(
        LAYER,
        user_agent,
        where=f"FINISH_DATE IS NULL OR FINISH_DATE >= TIMESTAMP '{since}'",
        client=client,
    )


class GoldCoastTemporaryClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
