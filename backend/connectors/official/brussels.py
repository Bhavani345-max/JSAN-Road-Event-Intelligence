"""Brussels traffic events, Belgium (decision 0034).

    GET https://data-mobility.irisnet.be/datasets/v1/traffic/collections/traffic_events/items/
        ?limit=1000&crs=http://www.opengis.net/def/crs/EPSG/0/4326

Brussels Mobility's traffic events (OGC API Features, GeoJSON): roadworks,
closures and incidents on the region's roads, each a WGS 84 point with its
DATEX II code, its type and location in French and Dutch, the consequences,
and a start and an end in Brussels local time (written without an offset).
Fetched without a key on 16 October 2026: 233 events (230 works, 2 road
closures, 1 broken-down vehicle), all with a start and an end.

The type comes from the DATEX II code: RWK (works) is road works, RCA (road
closed) a planned road closure, BKD (broken-down vehicle) a road hazard; any
other code keeps its words with no type.

Licence: CC0 1.0 (docs/data-sources/europe-official-road-sources-2026-10-16.md).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time

SOURCE_ID = "brussels-traffic-events"
ENDPOINT = "https://data-mobility.irisnet.be/datasets/v1/traffic/collections/traffic_events/items/"
PARAMS = {"limit": "1000", "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
SOURCE_URL = "https://data-mobility.irisnet.be/datasets/v1/traffic/collections/traffic_events/"
ATTRIBUTION = "Traffic events: Brussels Mobility (CC0 1.0)."
BRUSSELS = ZoneInfo("Europe/Brussels")
TYPES = {
    "RWK": (EventType.ROAD_WORKS.value, "Road works"),
    "RCA": (EventType.PLANNED_ROAD_CLOSURE.value, "Road closed"),
    "BKD": (EventType.ROAD_HAZARD.value, "Broken-down vehicle"),
}
TIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")


def brussels_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("brussels")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Brussels Mobility traffic events",
        organization="Brussels Mobility (Brussels-Capital Region)",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Brussels-Capital Region",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="OGC API Features (GeoJSON, WGS 84); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fr",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.ROAD_HAZARD.value,
        ),
        parser_type="brussels_traffic_events",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC0 1.0",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each traffic event as received.",
        notes=(
            "Roadworks, closures and incidents on Brussels' roads, each a point with a start and an "
            "end. Fetched without a key on 16 October 2026: 233 events."
        ),
    )


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    external_id = clean(properties.get("fid") or feature.get("id"))
    if not external_id:
        return None
    code = clean(properties.get("datex_codes"))
    event_type, label = TYPES.get(code, (None, clean(properties.get("type_fr")) or "Traffic event"))
    place = clean(properties.get("location_fr")) or clean(properties.get("location_nl"))
    area = clean(properties.get("direction_fr"))
    consequences = clean(properties.get("consequences_fr"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (clean(properties.get("type_fr")), consequences) if part),
        start=local_time(properties.get("start_time"), BRUSSELS, TIME_FORMATS),
        end=local_time(properties.get("end_time"), BRUSSELS, TIME_FORMATS),
        geometry=geometry,
        locations=[SourceLocation(name=place or "Brussels", kind="location", geometry=geometry, closure=consequences or None)],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{clean(properties.get('start_time'))} – {clean(properties.get('end_time'))} (Brussels time)",
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=f"{ENDPOINT}{external_id}/",
        title=f"{label}: {place or 'Brussels'}{f' ({area})' if area else ''}",
        summary=". ".join(
            part
            for part in (clean(properties.get("type_fr")), consequences, clean(properties.get("consequences_nl")))
            if part
        )
        or None,
        categories=[part for part in (code, clean(properties.get("type_fr"))) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_events(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    if isinstance(body.get("numberMatched"), int) and body["numberMatched"] > len(features):
        raise ConnectorError(f"{ENDPOINT} lists {body['numberMatched']} events, more than one page")
    return [feature for feature in features if isinstance(feature, dict)]


class BrusselsTrafficEventsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_events)
    to_record = staticmethod(to_record)
