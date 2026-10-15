"""Roads ACT planned road closures (decision 0029).

    GET https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/Road_Closures_public_view_HISTORICAL/FeatureServer/0/query

The ACT Government's Temporary Traffic Management plans: each planned road
closure in Canberra at a point, with the project, the roads closed, the
reason and the start and end, and Roads ACT's approval. This is the "JSON
Feed" of the ACT dataset "Temporary Traffic Management (TTM) - Planned Road
Closures (Live Stream)" (https://www.data.act.gov.au/d/gcdw-wgd8). On 15
October 2026: 140 plans (112 in force, 28 planned), all approved; keyless.
Only plans Roads ACT has approved are read.

Times are milliseconds since 1970, UTC.

CC BY-SA 4.0: commercial use is allowed, adapted data must be shared under
the same licence. Connected for testing; whether REI can meet the share-alike
condition when it publishes is the user's decision (decision 0029).
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

SOURCE_ID = "roads-act-planned-closures"
LAYER = (
    "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/"
    "Road_Closures_public_view_HISTORICAL/FeatureServer/0"
)
SOURCE_URL = "https://www.data.act.gov.au/d/gcdw-wgd8"
ATTRIBUTION = "Transport Canberra and City Services - Roads ACT. Licensed under CC BY-SA 4.0."
TYPE_LABELS = {
    "buildingConstruction": "Building construction",
    "roadWorks": "Road works",
    "lightRail": "Light rail works",
    "specialEvent": "Special event",
    "utilities": "Utility works",
    "telecommunications": "Telecommunications works",
    "other": "Other",
}


def roads_act_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("australia")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Roads ACT planned road closures",
        organization="ACT Government, Transport Canberra and City Services (Roads ACT)",
        authority_type="TERRITORY_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region="Australian Capital Territory",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service (the dataset's JSON feed), GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="roads_act_ttm_planned_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution-ShareAlike 4.0 (share-alike: adapted data under the same licence)",
        attribution=ATTRIBUTION,
        # Commercial use is allowed only with share-alike; whether REI can meet it is not decided.
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each plan as the service returns it and the structured event derived from it.",
        notes=(
            "Roads ACT's approved Temporary Traffic Management plans, each at a point. Fetched "
            "without a key on 15 October 2026: 140 plans (112 in force, 28 planned), all approved. "
            "CC BY-SA 4.0: connected for testing; the share-alike condition is the user's decision "
            "before publishing."
        ),
    )


def approved(properties: dict[str, Any]) -> bool:
    return clean(properties.get("roadsDelegateClosure")).lower() == "yes"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or not approved(properties):
        return None
    external_id = clean(properties.get("globalid"))
    if not external_id:
        return None
    kind = clean(properties.get("type"))
    label = TYPE_LABELS.get(kind, kind)
    roads = clean(properties.get("roadsClosed"))
    suburb = clean(properties.get("suburb1")).title()
    if suburb.lower() == "other":
        suburb = ""
    project = clean(properties.get("projectTitle"))
    if kind == "specialEvent":
        event_type = EventType.SPECIAL_EVENT.value
    elif kind == "roadWorks":
        event_type = EventType.ROAD_WORKS.value
    else:
        # Every plan in this list closes the roads it names.
        event_type = EventType.PLANNED_ROAD_CLOSURE.value
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in ("Planned road closure", label) if part),
        status="approved",
        start=epoch_ms(properties.get("startTimeClosure")),
        end=epoch_ms(properties.get("endTimeClosure")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (roads, suburb) if part)[:300],
                kind="roads closed",
                geometry=geometry,
                closure="closed",
            )
        ]
        if roads
        else [],
        affected_road=roads[:200] or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    summary = ". ".join(
        part
        for part in (
            roads,
            clean(properties.get("reasonRoadClosure")),
            clean(properties.get("describeActivity")),
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{project or label}: {suburb} (ACT)" if suburb else f"{project or label} (ACT)",
        summary=summary,
        categories=["planned road closure", label.lower()],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("roadsApprovalTimestamp")),
    )


def fetch_plans(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    return fetch_arcgis_features(LAYER, user_agent, order_by="objectid", client=client)


class RoadsActPlannedClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_plans)
    to_record = staticmethod(to_record)
