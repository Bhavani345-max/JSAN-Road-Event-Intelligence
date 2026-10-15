"""City of Ottawa traffic events (decision 0029).

    GET https://traffic.ottawa.ca/map/service/events?accept-language=en&version=v2&format=geojson

The City's Traffic Services publish their construction, special-event and
incident closures as GeoJSON, each with its own line or point, the streets,
whether the road or lanes are closed and the schedule. On 15 October 2026:
129 events (122 in force, 2 planned, 5 without a schedule), keyless, no
robots.txt. Documented at https://traffic.ottawa.ca/en/opendata.

Times have no offset; the City's FAQ: "All time and time information is
presented in local Ottawa time (EST/EDT)".

Open Government Licence – City of Ottawa (Open Data Licence Version 2.0).
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

SOURCE_ID = "ottawa-traffic-events"
ENDPOINT = "https://traffic.ottawa.ca/map/service/events"
PARAMS = {"accept-language": "en", "version": "v2", "format": "geojson"}
SOURCE_URL = "https://traffic.ottawa.ca/en/opendata"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – City of Ottawa."
OTTAWA = ZoneInfo("America/Toronto")
DIRECTIONS = {"BOTH_DIRECTIONS": "BOTH_DIRECTIONS"}


def ottawa_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Ottawa traffic events",
        organization="City of Ottawa, Traffic Services",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Ontario",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="City of Ottawa traffic GeoJSON feed (version 2); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="ottawa_traffic_events_v2",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – City of Ottawa (Open Data Licence Version 2.0)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each GeoJSON feature and the structured event derived from it.",
        notes=(
            "The City's construction, special-event and incident closures, each with its own "
            "line or point. Fetched without a key on 15 October 2026: 129 events (122 in force, "
            "2 planned, 5 without a schedule). Times are local Ottawa time."
        ),
    )


def _time(value: Any) -> datetime | None:
    return local_time(value, OTTAWA, ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"))


def _event_type(properties: dict[str, Any]) -> str:
    kind = clean(properties.get("eventType")).upper()
    closure = clean(properties.get("closureType")).upper()
    if kind == "SPECIAL_EVENT":
        return EventType.SPECIAL_EVENT.value
    if closure == "ROAD_CLOSED":
        return (
            EventType.EMERGENCY_ROAD_CLOSURE.value
            if kind == "INCIDENT"
            else EventType.PLANNED_ROAD_CLOSURE.value
        )
    if closure in ("LANES_CLOSED", "BUS_LANE_CLOSED"):
        return EventType.LANE_RESTRICTION.value
    if kind == "INCIDENT":
        return EventType.ROAD_HAZARD.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("id"))
    if not external_id:
        return None
    schedule = [part for part in properties.get("schedule") or [] if isinstance(part, dict)]
    starts = [s for part in schedule if (s := _time(part.get("startDateTime")))]
    ends = [e for part in schedule if (e := _time(part.get("endDateTime")))]
    headline = clean(properties.get("headline"))
    message = clean(properties.get("message"))
    street = clean(properties.get("mainStreet"))
    crossing = " and ".join(
        part for part in (clean(properties.get("crossStreet1")), clean(properties.get("crossStreet2"))) if part
    )
    closure = clean(properties.get("closureType"))
    structured = SourceEvent(
        event_type=_event_type(properties),
        category=" / ".join(part for part in (clean(properties.get("eventType")), closure) if part),
        status=clean(properties.get("status")) or None,
        start=min(starts) if starts else None,
        # An open part of the schedule leaves the end unstated.
        end=max(ends) if ends and len(ends) == len(schedule) else None,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=headline or street,
                kind="street",
                geometry=geometry,
                direction=DIRECTIONS.get(clean(properties.get("closureFlow")).upper()),
                closure=closure or None,
            )
        ]
        if headline or street
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        reported_ended=clean(properties.get("status")).upper() == "ARCHIVED",
        covers_city=True,
    )
    categories = [part.lower() for part in (clean(properties.get("eventType")), closure) if part]
    title = headline or ", ".join(part for part in (street, crossing) if part)
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{title} (Ottawa)",
        summary=message,
        categories=categories,
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(properties.get("updated")),
    )


def fetch_features(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature list")
    return [feature for feature in features if isinstance(feature, dict)]


class OttawaTrafficEventsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_features)
    to_record = staticmethod(to_record)
