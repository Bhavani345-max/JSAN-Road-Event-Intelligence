"""Main Roads Western Australia: roadworks and events from WebEOC (decision 0029).

    GET https://services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services/WebEoc_Roadworks/FeatureServer/2/query
    GET https://services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services/WebEoc_Events/FeatureServer/0/query

The layers behind Main Roads' Travel Map, "updated every 5 min from WebEOC":
roadworks on the State road network and events (races, concerts) affecting
it, each at a point. On 15 October 2026: 248 roadworks (172 in force, 76
planned) and 18 events, keyless. The incident layer states no start or end,
so it is not read: without both, an event is not shown (15 October 2026).

Times are written dd/mm/yyyy HH:MM:SS in Western Australian time (UTC+8).

Creative Commons Attribution (catalogue: CC BY 4.0),
https://catalogue.data.wa.gov.au/dataset/mrwa-webeoc-roadworks.
"""

import re
from datetime import datetime
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

from .feature_feed import FeatureFeedConnector, clean, fetch_arcgis_features, item_record, local_time

SOURCE_ID = "main-roads-wa-webeoc"
SERVICES = "https://services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services"
LAYERS = {
    "roadworks": f"{SERVICES}/WebEoc_Roadworks/FeatureServer/2",
    "event": f"{SERVICES}/WebEoc_Events/FeatureServer/0",
}
SOURCE_URL = "https://catalogue.data.wa.gov.au/dataset/mrwa-webeoc-roadworks"
ATTRIBUTION = (
    "Source: Main Roads Western Australia (WebEOC). The Commissioner of Main Roads is the "
    "creator and owner of the data, accessed under a Creative Commons Attribution licence."
)
PERTH = ZoneInfo("Australia/Perth")
TIME_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


def main_roads_wa_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("australia")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Main Roads WA roadworks and events",
        organization="Main Roads Western Australia",
        authority_type="STATE_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region="Western Australia",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=LAYERS["roadworks"],
        access_method="ArcGIS feature services (WebEOC roadworks and events), GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.SPORTING_EVENT.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="main_roads_wa_webeoc",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0 (WA data catalogue; ArcGIS item licence text)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each WebEOC feature as the service returns it and the structured event.",
        notes=(
            "Roadworks and events on WA's State roads, each at a point, updated every 5 minutes. "
            "Fetched without a key on 15 October 2026: 248 roadworks (172 in force, 76 planned) "
            "and 18 events. Incidents state no times and are not read. Times are WA time."
        ),
    )


def _roadworks_type(text: str) -> str:
    text = text.lower()
    if re.search(r"\blanes?\b", text):
        return EventType.LANE_RESTRICTION.value
    if re.search(r"\b(closure|closed)\b", text):
        return EventType.PLANNED_ROAD_CLOSURE.value
    return EventType.ROAD_WORKS.value


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    layer = item.get("layer")
    feature = item.get("feature")
    properties = feature.get("properties") if isinstance(feature, dict) else None
    geometry = feature.get("geometry") if isinstance(feature, dict) else None
    if layer not in LAYERS or not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    record_id = clean(properties.get("Id"))
    if not record_id:
        return None
    road = clean(properties.get("LocalRoadName")) or clean(properties.get("LocalRoadN")) or clean(
        properties.get("Road")
    )
    place = ", ".join(part for part in (clean(properties.get("Suburb")), clean(properties.get("Region"))) if part)
    impact = clean(properties.get("TrafficImp"))
    if layer == "roadworks":
        description = clean(properties.get("Descriptio"))
        work = clean(properties.get("WorkType"))
        event_type = _roadworks_type(f"{impact} {description}")
        start = local_time(properties.get("DateStarte"), PERTH, TIME_FORMATS)
        end = local_time(properties.get("EstimatedC"), PERTH, TIME_FORMATS)
        title = description.split(" - ")[0] if description else f"{work}: {road}"
        category = " / ".join(part for part in ("Roadworks", work) if part)
        summary = ". ".join(part for part in (description, impact) if part)
    else:
        name = clean(properties.get("EventName"))
        kind = clean(properties.get("EventType"))
        event_type = (
            EventType.SPORTING_EVENT.value if "sport" in kind.lower() else EventType.SPECIAL_EVENT.value
        )
        start = local_time(properties.get("DateTimeSt"), PERTH, TIME_FORMATS)
        end = local_time(properties.get("DateTimeEn"), PERTH, TIME_FORMATS)
        title = f"{name}: {road}" if name and road else name or road
        category = " / ".join(part for part in ("Event", kind) if part)
        summary = ". ".join(part for part in (clean(properties.get("EventDescr")), impact) if part)
    structured = SourceEvent(
        event_type=event_type,
        category=category,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (road, place) if part), kind="road", geometry=geometry,
                closure=impact or None,
            )
        ]
        if road
        else [],
        affected_road=road or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"{layer}:{record_id}",
        url=clean(properties.get("SeeMoreUrl")) or SOURCE_URL,
        title=f"{title} (WA)",
        summary=summary,
        categories=[part.lower() for part in category.split(" / ")],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_webeoc(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    return [
        {"layer": layer, "feature": feature}
        for layer, url in LAYERS.items()
        for feature in fetch_arcgis_features(url, user_agent, order_by="FID", client=client)
    ]


class MainRoadsWaConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_webeoc)
    to_record = staticmethod(to_record)
