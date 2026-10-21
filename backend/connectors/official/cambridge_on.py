"""City of Cambridge (Ontario) road closures (21 October 2026).

    GET https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1/query

"Lines that represent traffic closures on City Owned Roads", refreshed every
3 hours (the "Road Closures" item of the City's open-data catalogue,
57f26d74f53f4078842c08833f20971a, which points to this layer). Each closure
has its street, the stretch, the reason, an impact level and `DETAILS` in
the form "<impact> - <lanes> - <direction>" ("High - All Lanes -
Both_Directions", "Low - Parking Lane - N/A"). On 21 October 2026: 145
closures, all current, keyless; 116 close only a parking lane, close no
traffic lane and are left out (as for the City of Gold Coast).

`DATE_FROM`/`DATE_TO` are milliseconds since 1970 (UTC) with their times.
`CONTACT` and `ORGANIZATION` name people and telephone numbers; the licence
does not cover personal information, so they are not kept.

Open Data Licence Version 2.0 – City of Cambridge
(https://maps.cambridge.ca/images/opendata/Open%20data%20licence.pdf, read 21 October 2026).
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
from .feed_text import sentences, stretch

SOURCE_ID = "cambridge-on-road-closures"
LAYER = "https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1"
SOURCE_URL = "https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer"
LICENCE_URL = "https://maps.cambridge.ca/images/opendata/Open%20data%20licence.pdf"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – City of Cambridge."
# Columns not kept as evidence: names and telephone numbers of people.
PERSONAL = frozenset({"CONTACT", "ORGANIZATION"})
NOT_TRAFFIC = {"PARKING LANE"}
FULL = {"ALL LANES", "ALL LANES AFFECTED"}
DIRECTIONS = {
    "BOTH_DIRECTIONS": "BOTH_DIRECTIONS",
    "NORTHBOUND": "NORTHBOUND",
    "SOUTHBOUND": "SOUTHBOUND",
    "EASTBOUND": "EASTBOUND",
    "WESTBOUND": "WESTBOUND",
}


def cambridge_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Cambridge (Ontario) road closures",
        organization="City of Cambridge (Ontario)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Ontario (Cambridge)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS map service layer, GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="cambridge_on_road_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Open Data Licence Version 2.0 – City of Cambridge ({LICENCE_URL})",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=False,
        evidence_retention=(
            "Each closure as the service returns it, less its contact and organisation columns, "
            "and the structured event."
        ),
        notes=(
            "The City's closures on City-owned roads, one line each, refreshed every 3 hours. "
            "Fetched without a key on 21 October 2026: 145 closures, of which 116 close only a "
            "parking lane and are left out. Times are UTC milliseconds."
        ),
    )


def details(properties: dict[str, Any]) -> tuple[str, str, str]:
    """The impact, the lanes and the direction `DETAILS` states ('' where it says N/A)."""
    parts = [part.strip() for part in clean(properties.get("DETAILS")).split(" - ")]
    parts += [""] * (3 - len(parts))
    impact, lanes, direction = (("" if part.upper() == "N/A" else part) for part in parts[:3])
    return impact, lanes, direction


def closes_traffic(properties: dict[str, Any]) -> bool:
    _, lanes, _ = details(properties)
    return lanes.upper() not in NOT_TRAFFIC


def _event_type(status: str, lanes: str) -> str:
    if status.startswith("FULL CLOSURE") or lanes.upper() in FULL:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if lanes:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("CLOSURE_ID"))
    if not external_id or not closes_traffic(properties):
        return None
    impact, lanes, stated_direction = details(properties)
    direction = DIRECTIONS.get(stated_direction.upper())
    street = clean(properties.get("STREET_NAME"))
    place = stretch(
        street, clean(properties.get("STREET_FROM")), clean(properties.get("STREET_TO"))
    )
    status = clean(properties.get("STATUS")).upper()
    event_type = _event_type(status, lanes)
    label = {
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
        EventType.LANE_RESTRICTION.value: "Lane closure",
    }.get(event_type, "Road works")
    reason = clean(properties.get("REASON"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (reason, impact, lanes) if part),
        severity=clean(properties.get("STATUS")) or None,
        start=epoch_ms(properties.get("DATE_FROM")),
        end=epoch_ms(properties.get("DATE_TO")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street",
                geometry=geometry,
                direction=stated_direction or None,
                closure=lanes or None,
            )
        ]
        if place
        else [],
        affected_road=street or None,
        direction=direction,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    reference = clean(properties.get("REFERENCE_INFO"))
    summary = sentences(
        reason,
        clean(properties.get("DETAILS")),
        f"Reference {reference}" if reference else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {place} (Cambridge, Ontario)",
        summary=summary,
        categories=[part.lower() for part in (reason, label) if part],
        item={**feature, "properties": {k: v for k, v in properties.items() if k not in PERSONAL}},
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("LAST_UPDATED")),
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The layer holds the current closures only ("Current Closures").
    return fetch_arcgis_features(LAYER, user_agent, client=client)


class CambridgeRoadClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
