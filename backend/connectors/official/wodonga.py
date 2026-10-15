"""City of Wodonga roadworks with their closures and disruptions (decision 0029).

    GET https://services-ap1.arcgis.com/w6r4LlwgJu8O0neQ/arcgis/rest/services/Traffic_management_plan_5_view/FeatureServer/{0,2,3,4}/query

The Council's traffic management plans: "Only roadworks consented by council
are included." Each works record (layer 0, the impact area as a polygon)
has its road closures (3), disruptions (2) and detours (4) as lines, linked
by `parentglobalid`. One works record is one event here, at its impact area,
with its closures and disruptions as its locations; a detour is where
traffic is sent, so its street is named but its line is not drawn as the
event. On 15 October 2026: 16 works (12 in force, 4 planned), keyless.

Times are milliseconds since 1970, UTC.

CC BY 4.0 (the service's ArcGIS item; access information "Wodonga council").
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

SOURCE_ID = "wodonga-roadworks"
SERVICE = (
    "https://services-ap1.arcgis.com/w6r4LlwgJu8O0neQ/arcgis/rest/services/"
    "Traffic_management_plan_5_view/FeatureServer"
)
LAYERS = {"works": 0, "disruption": 2, "closure": 3, "detour": 4}
SOURCE_URL = "https://www.arcgis.com/home/item.html?id=166e7348dc5248a98ba8bd5123503457"
ATTRIBUTION = "Source: Wodonga Council, traffic management plans. Licensed under CC BY 4.0."
# Each layer's field prefix.
PREFIX = {"disruption": "DR", "closure": "CL", "detour": "DT"}


def wodonga_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("australia")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Wodonga roadworks",
        organization="Wodonga Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Victoria",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=SERVICE,
        access_method="ArcGIS feature service (works, closures, disruptions, detours), GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="wodonga_traffic_management_plans",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works record with its linked closures, disruptions and detours.",
        notes=(
            "Council-consented roadworks in Wodonga, each with its impact area and the lines of its "
            "closures, disruptions and detours. Fetched without a key on 15 October 2026: 16 works "
            "(12 in force, 4 planned)."
        ),
    )


def _event_type(children: list[dict[str, Any]]) -> str:
    impacts = [
        clean(child["properties"].get(f"{PREFIX[child['layer']]}_lane_impact")).lower()
        for child in children
        if child["layer"] in ("closure", "disruption")
    ]
    if any("road closed" in impact or impact == "closed" for impact in impacts):
        return EventType.PLANNED_ROAD_CLOSURE.value
    if impacts:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _child_location(child: dict[str, Any]) -> SourceLocation | None:
    prefix = PREFIX[child["layer"]]
    properties = child["properties"]
    street = clean(properties.get(f"{prefix}_street")).title()
    if not street:
        return None
    impact = clean(properties.get(f"{prefix}_lane_impact"))
    return SourceLocation(
        name=street,
        kind=child["layer"],
        # Where traffic is sent is not where the road is affected.
        geometry=None if child["layer"] == "detour" else child.get("geometry"),
        closure=impact or clean(properties.get(f"{prefix}_description")) or None,
    )


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    works = item.get("works")
    properties = works.get("properties") if isinstance(works, dict) else None
    geometry = works.get("geometry") if isinstance(works, dict) else None
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("globalid"))
    if not external_id:
        return None
    children = [child for child in item.get("children") or [] if isinstance(child.get("properties"), dict)]
    location = clean(properties.get("RW_location"))
    description = clean(properties.get("RW_description"))
    impact = clean(properties.get("RW_traffic_impact")).replace("_", " ")
    event_type = _event_type(children)
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in ("Roadworks", impact) if part),
        start=epoch_ms(properties.get("RW_start")),
        end=epoch_ms(properties.get("RW_end")),
        geometry=geometry,
        locations=[
            SourceLocation(name=location, kind="impact area", geometry=geometry, closure=impact or None),
            *[place for child in children if (place := _child_location(child))],
        ]
        if location
        else [place for child in children if (place := _child_location(child))],
        affected_road=location.split(",")[0] or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    label = {
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
        EventType.LANE_RESTRICTION.value: "Lane restriction",
    }.get(event_type, "Roadworks")
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {location.split(',')[0] or 'Wodonga'} (Wodonga)",
        summary=". ".join(part for part in (description, impact) if part),
        categories=["roadworks", *(child["layer"] for child in children)],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """Each works record with the closures, disruptions and detours linked to it."""
    layers = {
        name: fetch_arcgis_features(f"{SERVICE}/{number}", user_agent, order_by="objectid", client=client)
        for name, number in LAYERS.items()
    }
    children: dict[str, list[dict]] = {}
    for name in ("closure", "disruption", "detour"):
        for feature in layers[name]:
            parent = clean((feature.get("properties") or {}).get("parentglobalid"))
            if parent:
                children.setdefault(parent, []).append(
                    {"layer": name, "properties": feature.get("properties"), "geometry": feature.get("geometry")}
                )
    return [
        {"works": works, "children": children.get(clean((works.get("properties") or {}).get("globalid")), [])}
        for works in layers["works"]
    ]


class WodongaRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)
