"""City of Kitchener traffic closures (21 October 2026).

    GET https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/
        Traffic_Closures/FeatureServer/0/query

The City's "Current and Future Traffic Closures" (update frequency: hourly),
each with its own line, the street, the stretch, the status ("Closed",
"Local Access Only", "No Through Traffic", "Partially Closed", "Lane
Reduced", "Tentative"), the reason and the dates. On 21 October 2026: 44
road closures, keyless; 15 state no start and 21 no end (those periods stay
unstated). The City's own map server answers "Token Required"; this is the
City's ArcGIS Online copy (item c500d56ecbec41a6b96e3e264ce65d22, owner
KitchenerGIS).

`DATE_FROM`/`DATE_TO` are milliseconds since 1970 (UTC) with their times.
Sidewalk and trail closures and closures marked "Open" close no road and are
left out. `CONTACT` and `ALTERNATE_CONTACT` name staff with telephone
numbers and `CREATE_BY`/`UPDATE_BY` name staff accounts; the licence does
not cover personal information, so they are not kept.

Open Government Licence – The Corporation of the City of Kitchener v1.0 (the
item's licence, read 21 October 2026): commercial use permitted, no credit
required.
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

SOURCE_ID = "kitchener-traffic-closures"
SOURCE_URL = (
    "https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Closures/FeatureServer"
)
LAYER = f"{SOURCE_URL}/0"
# The licence's own words for a credit, which it does not require.
ATTRIBUTION = (
    "Contains information licensed under the Open Government Licence - The Corporation of the City "
    "of Kitchener."
)
# Columns not kept as evidence: staff names, accounts and telephone numbers.
PERSONAL = frozenset({"CONTACT", "ALTERNATE_CONTACT", "CREATE_BY", "UPDATE_BY"})
NOT_ROADS = {"SIDEWALK", "TRAIL"}
CLOSED = {"CLOSED", "LOCAL ACCESS ONLY", "NO THROUGH TRAFFIC"}
PARTLY = {"PARTIALLY CLOSED", "LANE REDUCED"}


def kitchener_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Kitchener traffic closures",
        organization="City of Kitchener, Infrastructure Services, Transportation Services",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Ontario (Kitchener)",
        city=country.id,
        source_url=SOURCE_URL,
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
        parser_type="kitchener_traffic_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – The Corporation of the City of Kitchener v1.0",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each closure as the service returns it, less its staff contact and account columns, "
            "and the structured event."
        ),
        notes=(
            "The City's current and future road closures, one line each, updated hourly. "
            "Fetched without a key on 21 October 2026: 44 road closures; 15 state no start and "
            "21 no end. Times are UTC milliseconds. Sidewalk and trail closures are left out."
        ),
    )


def _event_type(status: str, reason: str) -> str:
    if reason == "SPECIAL EVENT":
        return EventType.SPECIAL_EVENT.value
    if "EMERGENCY" in (status, reason):
        return EventType.EMERGENCY_ROAD_CLOSURE.value
    if status in CLOSED:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if status in PARTLY:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("TRAFFICCLOSURESID"))
    status = clean(properties.get("STATUS"))
    kind = clean(properties.get("CLOSURE_TYPE"))
    if not external_id or kind.upper() in NOT_ROADS or status.upper() == "OPEN":
        return None
    street = clean(properties.get("STREET_NAME"))
    place = stretch(
        street, clean(properties.get("STREET_FROM")), clean(properties.get("STREET_TO"))
    )
    reason = clean(properties.get("REASON"))
    schedule = clean(properties.get("CLOSURE_SCHEDULED"))
    structured = SourceEvent(
        event_type=_event_type(status.upper(), reason.upper()),
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
    summary = sentences(
        clean(properties.get("DETAILS")),
        clean(properties.get("UPDATES")),
        f"Hours: {clean(properties.get('TIME'))}" if clean(properties.get("TIME")) else "",
        f"Detour: {detour}" if detour else "",
        f"Reason: {reason}" if reason else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        # Without a status, the layer's own name for what it lists.
        title=f"{status or 'Traffic closure'}: {place} (Kitchener)",
        summary=summary,
        categories=[part.lower() for part in (reason, status) if part],
        item={**feature, "properties": {k: v for k, v in properties.items() if k not in PERSONAL}},
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("UPDATE_DATE")),
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The layer holds the current and future closures only (a few dozen).
    return fetch_arcgis_features(LAYER, user_agent, client=client)


class KitchenerTrafficClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
