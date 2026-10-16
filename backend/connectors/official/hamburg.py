"""Hamburg police traffic messages, Germany (decision 0034).

    GET https://api.hamburg.de/datasets/v1/verkehrsinformation/collections/hauptmeldungen_aktuell/items
        ?f=json&limit=10000

The Hamburg police's current traffic messages (OGC API Features, GeoJSON):
each a WGS 84 point with its DATEX II record type (`art`) and detail
(`art_detail`), a status word, the message in German, and a start and an end
in UTC written without a zone marker (the message text states local times
that match). Fetched without a key on 16 October 2026: 275 messages, 240
with an end.

The type comes from the DATEX II record: ConstructionWorks and
MaintenanceWorks are road works; RoadOrCarriagewayOrLaneManagement is a
planned road closure when its detail is roadClosed and a lane restriction
otherwise. Traffic-flow messages (AbnormalTraffic, Conditions,
GeneralInstructionOrMessageToRoadUsers) describe traffic, not a road event,
and are not taken.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0
(dl-de/by-2-0), credit "Freie und Hansestadt Hamburg, Polizei Hamburg"
(docs/data-sources/europe-official-road-sources-2026-10-16.md).
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

SOURCE_ID = "hamburg-police-traffic-messages"
ENDPOINT = "https://api.hamburg.de/datasets/v1/verkehrsinformation/collections/hauptmeldungen_aktuell/items"
PARAMS = {"f": "json", "limit": "10000"}
SOURCE_URL = "https://api.hamburg.de/datasets/v1/verkehrsinformation"
ATTRIBUTION = "Freie und Hansestadt Hamburg, Polizei Hamburg (Datenlizenz Deutschland – Namensnennung – Version 2.0)"
UTC = ZoneInfo("UTC")
WORKS = frozenset({"ConstructionWorks", "MaintenanceWorks"})
MANAGEMENT = "RoadOrCarriagewayOrLaneManagement"


def hamburg_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("hamburg")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Hamburg police traffic messages",
        organization="Polizei Hamburg",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Hamburg",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="OGC API Features (GeoJSON, WGS 84); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="de",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
        ),
        parser_type="hamburg_police_traffic",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each traffic message as received.",
        notes=(
            "The Hamburg police's current traffic messages: works, closures and lane restrictions, "
            "each a point. Fetched without a key on 16 October 2026: 275 messages, 240 with an end."
        ),
    )


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    kind, detail = clean(properties.get("art")), clean(properties.get("art_detail"))
    if kind in WORKS:
        event_type, label = EventType.ROAD_WORKS.value, "Road works"
    elif kind == MANAGEMENT and detail == "roadClosed":
        event_type, label = EventType.PLANNED_ROAD_CLOSURE.value, "Road closed"
    elif kind == MANAGEMENT:
        event_type, label = EventType.LANE_RESTRICTION.value, "Lane restriction"
    else:
        return None  # traffic flow or conditions, not a road event
    external_id = clean(properties.get("id") or feature.get("id"))
    if not external_id:
        return None
    lines = [clean(line) for line in str(properties.get("description") or "").splitlines() if clean(line)]
    place = lines[0].removeprefix("Hamburg, ") if lines else "Hamburg"
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (kind, detail, clean(properties.get("status"))) if part),
        start=local_time(properties.get("start"), UTC, ("%Y-%m-%d %H:%M:%S",)),
        end=local_time(properties.get("end"), UTC, ("%Y-%m-%d %H:%M:%S",)),
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="location", geometry=geometry, closure=detail or None)],
        affected_road=place.split(",")[0] or None,
        attribution=ATTRIBUTION,
        stated_period=" / ".join(lines[1:]) or None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {place} (Hamburg)",
        summary=" ".join(lines) or None,
        categories=[part for part in (kind, detail) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_messages(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    return [feature for feature in features if isinstance(feature, dict)]


class HamburgPoliceTrafficConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_messages)
    to_record = staticmethod(to_record)
