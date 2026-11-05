"""South Tyrol traffic reports (Verkehrsmeldezentrale / Centro viabilità), Italy (5 November 2026).

    GET https://geoservices2.civis.bz.it/geoserver/pczs-Traffic/ows?service=WFS&version=2.0.0
        &request=GetFeature&typeNames=pczs-Traffic:TrafficReport-RoadWorksAndLocks
        &outputFormat=application/json&srsName=EPSG:4326
    and the same with typeNames=pczs-Traffic:TrafficReport-CurrentSituation

The Autonomous Province of Bolzano's Civil Protection Agency (Agenzia per la
Protezione civile / Agentur für Bevölkerungsschutz) publishes the traffic
centre's reports as WFS layers: road works and closures (RoadWorksAndLocks,
"Baustellen und Sperren von Straßen - Cantieri e chiusure stradali") and the
current situation (CurrentSituation, "Verkehrsbehinderungen - Impedimenti al
traffico"). Each feature is one report, a WGS 84 point, in Italian and German:
the message number (`MESSAGE_ID`), the road or place (`MESSAGE_HEADER_I`/`_D`),
the report (`MSG_LOCATION_I`/`_D`, with the stretch, the daily hours and the
detour in words), the road number (`STREETNUMBER`: SS12, LS/SP185 …), the zone
(`ZONE_I`/`_D`), the kind (`TIPO_SUBCODE`: BAUSTELLE works, SPERRE closure,
VERANSTALTUNG event, STAU queue, ÖFFENTLICHE VERKEHRSMITTEL public transport,
VORSICHT caution) and the first and last day (`BEGIN_DATE`, `END_DATE`, written
"2026-10-20Z"; an end may be missing). Fetched without a key on 5 November
2026: 111 and 28 reports. The GeoJSON is written longitude first (Bolzano at
11.35, 46.50), although it names urn:ogc:def:crs:EPSG::4326; a feed in
latitude-longitude order is refused.

The two layers are one source. `MESSAGE_ID` is the message number followed by
the layer's two-digit `TYPE_ID` (3155812 in RoadWorksAndLocks, TYPE_ID 12, is
message 31558, also listed in CurrentSituation as 3155801, TYPE_ID 1): 22 of
the 28 current reports are such copies, identical in every field, and a
message is one record (its RoadWorksAndLocks copy is kept). 117 messages on
5 November 2026.

Works (BAUSTELLE) are road works (ROAD_WORKS), closures (SPERRE) planned road
closures (PLANNED_ROAD_CLOSURE), events (VERANSTALTUNG) special events
(SPECIAL_EVENT). Left out, as not road events: queues (STAU: the traffic's
state at the moment, written without an end, here lorries queuing on the A22
because of works), public transport notices (a funicular out of service) and
cautions (VORSICHT: a railway line interrupted), and any other kind; 4 of the
117 on 5 November 2026, so 113 kept (97 in force, 16 starting later; 3 state
no end). A period stated in days runs from the start of the first day to the
end of the last, Italian time; the daily hours stay in the report's words. The
report's own row id (`ID`), the feature id and the server's date (`CURRENT_DATE`,
changed every day) are not content and are not kept.

Licence: CC0 1.0 Universal (public domain dedication), as the dati.gov.it entry
"Cantieri stradali/chiusure" (0fd3f0bc-1137-4ec1-8f81-dabfc8e1657a, holder
Agenzia per la Protezione civile, Provincia autonoma di Bolzano) states for the
service's resources (read 5 November 2026); no credit is required. The entry
lists the RoadWorksAndLocks layer; CurrentSituation is served by the same
Civil Protection service and was approved with it on 5 November 2026.
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
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, whole_days

SOURCE_ID = "it-south-tyrol-traffic-reports"
ENDPOINT = "https://geoservices2.civis.bz.it/geoserver/pczs-Traffic/ows"
WORKS_LAYER = "pczs-Traffic:TrafficReport-RoadWorksAndLocks"
CURRENT_LAYER = "pczs-Traffic:TrafficReport-CurrentSituation"
# The works layer first: a message in both layers keeps its works copy.
LAYERS = (WORKS_LAYER, CURRENT_LAYER)
SOURCE_URL = "https://www.dati.gov.it/view-dataset/dataset?id=0fd3f0bc-1137-4ec1-8f81-dabfc8e1657a"
ATTRIBUTION = "Provincia autonoma di Bolzano – Agenzia per la Protezione civile, Centro viabilità (CC0 1.0)"
ROME = ZoneInfo("Europe/Rome")
# The report's row id and the server's date: not content.
BOOKKEEPING_FIELDS = frozenset({"ID", "CURRENT_DATE"})
KINDS = {
    "BAUSTELLE": (EventType.ROAD_WORKS.value, "Road works"),
    "SPERRE": (EventType.PLANNED_ROAD_CLOSURE.value, "Road closure"),
    "VERANSTALTUNG": (EventType.SPECIAL_EVENT.value, "Event"),
}


def params_for(layer: str) -> dict[str, str]:
    return {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }


def south_tyrol_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("italy")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="South Tyrol traffic reports (Centro viabilità / Verkehrsmeldezentrale)",
        organization="Provincia autonoma di Bolzano – Agenzia per la Protezione civile",
        authority_type="TRAFFIC_MANAGEMENT_CENTRE",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Trentino-Alto Adige/Südtirol (Provincia autonoma di Bolzano)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 2.0.0 GetFeature (GeoJSON, EPSG:4326), two layers; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="it",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="south_tyrol_traffic_reports",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no robots.txt; polled hourly (two requests, about 170 kB).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/), as the dati.gov.it entry states",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each report as received, less its row id and the server's date.",
        notes=(
            "The South Tyrol traffic centre's works, closures and events, one point each, in Italian and "
            "German. Fetched without a key on 5 November 2026: 111 + 28 reports, 117 messages (22 are in "
            "both layers); queues, public transport and caution notices left out; 113 kept (97 in force, "
            "16 starting later; 3 with no end)."
        ),
    )


def message_number(properties: dict[str, Any]) -> str:
    """The message's number: MESSAGE_ID without the layer's TYPE_ID at its end."""
    message, layer_type = properties.get("MESSAGE_ID"), properties.get("TYPE_ID")
    if isinstance(message, int) and isinstance(layer_type, int) and 0 <= layer_type < 100 and message % 100 == layer_type:
        return str(message // 100)
    return clean(message)


def stored_report(feature: dict[str, Any], layer: str) -> dict[str, Any]:
    """A report as REI keeps it: its layer, geometry and fields, less the row id and the date."""
    properties = feature.get("properties") or {}
    return {
        "layer": layer,
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in BOOKKEEPING_FIELDS},
    }


def to_record(report: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One message as REI's record; None when it is not a road event or has no point."""
    properties = report.get("properties")
    geometry = report.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    number = message_number(properties)
    kind = clean(properties.get("TIPO_SUBCODE")).upper()
    if not number or kind not in KINDS:
        return None
    event_type, label = KINDS[kind]
    header_it, header_de = clean(properties.get("MESSAGE_HEADER_I")), clean(properties.get("MESSAGE_HEADER_D"))
    text_it, text_de = clean(properties.get("MSG_LOCATION_I")), clean(properties.get("MSG_LOCATION_D"))
    road = clean(properties.get("STREETNUMBER"))
    zone = clean(properties.get("ZONE_I"))
    first, last = clean(properties.get("BEGIN_DATE")), clean(properties.get("END_DATE"))
    start, end = whole_days(local_day(first, ROME), local_day(last, ROME), ROME)
    place = " ".join(part for part in (road, header_it) if part)
    # The kind in the source's German words, then its map label in Italian: "Baustelle / Cantiere".
    kind_words = (clean(properties.get("SUBCODE_D")) or kind.title(), clean(properties.get("MAP_SUBT_I")))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in kind_words if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="location",
                geometry=geometry,
                closure="closed" if kind == "SPERRE" else None,
                reference=f"message {number}",
            )
        ]
        if place
        else [],
        affected_road=" ".join(part for part in (road, header_it) if part) or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first[:10] or '?'} – {last[:10] or 'no end stated'}",
        covers_city=True,
    )
    summary = " / ".join(part for part in (text_it, text_de) if part)
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"message:{number}",
        url=SOURCE_URL,
        title=f"{label}: {header_it or header_de or road or 'Alto Adige'}"
        + (f" ({road})" if road and header_it else "")
        + (f", {zone}" if zone else "")
        + " (South Tyrol)",
        summary=summary or None,
        categories=[part for part in (kind.lower(), clean(properties.get("TIPO_CODE")).lower()) if part],
        item=report,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def fetch_reports(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """The reports of both layers, one per message (a message's works copy first)."""
    reports: dict[str, dict[str, Any]] = {}
    for layer in LAYERS:
        body = fetch_json(ENDPOINT, user_agent, client=client, params=params_for(layer))
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{ENDPOINT} ({layer}) did not return a GeoJSON feature collection")
        matched = body.get("numberMatched", body.get("totalFeatures"))
        if isinstance(matched, int) and matched > len(features):
            raise ConnectorError(f"{ENDPOINT} ({layer}) lists {matched} reports, more than it returned")
        for feature in features:
            if not isinstance(feature, dict):
                continue
            # South Tyrol lies at about 11.4° E, 46.6° N: a first number above the second is a latitude.
            position = _first_position(feature.get("geometry"))
            if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
                raise ConnectorError(f"{ENDPOINT} ({layer}) returned coordinates in latitude-longitude order")
            number = message_number(feature.get("properties") or {})
            if number:
                reports.setdefault(number, stored_report(feature, layer))
    return list(reports.values())


class SouthTyrolTrafficReportsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_reports)
    to_record = staticmethod(to_record)
