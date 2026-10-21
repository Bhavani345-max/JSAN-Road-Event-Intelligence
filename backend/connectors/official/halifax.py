"""Halifax Regional Municipality street closures (21 October 2026).

    GET https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/
        Street_Closures/FeatureServer/0/query

The Municipality's "graphical representation of planned street closures
approved by the Engineer in accordance with section 332 of the HRM charter"
(the layer's description), each with its own line, the street, the stretch
(from and to streets), the type and the dates. The layer keeps its history
back to 2019; only closures ending yesterday or later are asked for. On 21
October 2026: 37 such closures (Construction 13, Development 11, Utility 4,
Block Party 3, Special Event 3, Other 3), all "Approved", keyless.

Dates are days, stored as the local midnight (Atlantic time); the daily hours
are free text ("7:00AM" to "7:00PM", "N/A") and are kept as text, so a
closure runs from the start of its first day to the end of its last. Rain or
alternate dates (`ALT_START_DATE`, `ALT_END_DATE`) are named in the summary,
not taken as the period.

Open Government Licence – Halifax (https://data-hrm.hub.arcgis.com/pages/open-data-licence,
read 21 October 2026).
"""

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
    epoch_ms,
    fetch_arcgis_features,
    item_record,
    local_day,
    whole_days,
)
from .feed_text import sentences, stretch

SOURCE_ID = "halifax-street-closures"
SOURCE_URL = (
    "https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Street_Closures/FeatureServer"
)
LAYER = f"{SOURCE_URL}/0"
LICENCE_URL = "https://data-hrm.hub.arcgis.com/pages/open-data-licence"
ATTRIBUTION = "Contains information licenced under the Open Government Licence – Halifax."
HALIFAX = ZoneInfo("America/Halifax")
EVENTS = {"SPECIAL EVENT", "BLOCK PARTY"}
NOT_STATED = {"", "N/A", "NONE"}
# Text fields read as written, "N/A" read as not stated.
STATED_FIELDS = (
    "START_TIME", "END_TIME", "REOPEN_EVENINGS", "REOPEN_WEEKENDS", "DETOUR_URL", "PERMIT_NO",
)  # fmt: skip


def halifax_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Halifax street closures",
        organization="Halifax Regional Municipality, Transportation and Public Works",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Nova Scotia (Halifax)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service, GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value, EventType.SPECIAL_EVENT.value),
        parser_type="halifax_street_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Open Government Licence – Halifax ({LICENCE_URL})",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each closure as the service returns it and the structured event.",
        notes=(
            "The Municipality's approved street closures, one line each. Fetched without a key "
            "on 21 October 2026: 37 closures not yet ended. Dates are Atlantic-time days; the "
            "daily hours and any alternate dates are kept as text."
        ),
    )


def _stated(value: Any) -> str:
    text = clean(value)
    return "" if text.upper() in NOT_STATED else text


def _day(value: Any) -> str:
    moment = epoch_ms(value)
    return moment.astimezone(HALIFAX).date().isoformat() if moment else ""


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("GLOBALID"))
    if not external_id:
        return None
    street = _stated(properties.get("STREET_NAME"))
    place = stretch(street, _stated(properties.get("FROM_STR")), _stated(properties.get("TO_STR")))
    kind = clean(properties.get("CLOSURE_TYPE"))
    start, end = whole_days(
        local_day(properties.get("START_DATE"), HALIFAX),
        local_day(properties.get("END_DATE"), HALIFAX),
        HALIFAX,
    )
    structured = SourceEvent(
        event_type=(
            EventType.SPECIAL_EVENT.value
            if kind.upper() in EVENTS
            else EventType.PLANNED_ROAD_CLOSURE.value
        ),
        category=" / ".join(part for part in ("Street closure", kind) if part),
        status=clean(properties.get("CLOSURE_STAGE")) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(name=place, kind="street", geometry=geometry, closure="Street closure")
        ]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    stated = {key: _stated(properties.get(key)) for key in STATED_FIELDS}
    hours = " - ".join(part for part in (stated["START_TIME"], stated["END_TIME"]) if part)
    alternate = " to ".join(
        day
        for day in (_day(properties.get("ALT_START_DATE")), _day(properties.get("ALT_END_DATE")))
        if day
    )
    summary = sentences(
        clean(properties.get("COMMENTS")),
        f"Hours: {hours}" if hours else "",
        f"Re-opens evenings: {stated['REOPEN_EVENINGS']}" if stated["REOPEN_EVENINGS"] else "",
        f"Re-opens weekends: {stated['REOPEN_WEEKENDS']}" if stated["REOPEN_WEEKENDS"] else "",
        f"Alternate dates: {alternate}" if alternate else "",
        f"Detour: {stated['DETOUR_URL']}" if stated["DETOUR_URL"] else "",
        f"Permit {stated['PERMIT_NO']}" if stated["PERMIT_NO"] else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"Street closure{f' ({kind})' if kind else ''}: {place} (Halifax)",
        summary=summary,
        categories=[part.lower() for part in ("street closure", kind) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("MODDATE")),
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # Ending yesterday (local) or later: a day's closure ends at that day's end.
    today = (now or datetime.now(HALIFAX)).astimezone(HALIFAX).date()
    since = (today - timedelta(days=1)).isoformat()
    return fetch_arcgis_features(
        LAYER, user_agent, where=f"END_DATE >= DATE '{since}'", client=client
    )


class HalifaxStreetClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
