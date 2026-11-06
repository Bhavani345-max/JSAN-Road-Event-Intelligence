"""Landeshauptstadt München roadworks, the next four weeks, Germany (5 November 2026).

    GET https://geoportal.muenchen.de/geoserver/mor_wfs/ows?service=WFS&version=1.1.0
        &request=GetFeature&typeName=mor_wfs:baustellen_opendata
        &outputFormat=application/json&srsName=EPSG:4326

The City of Munich's works and temporary no-parking zones in force or starting
within four weeks ("Baustellen – nächste 4 Wochen"), one WFS layer served as
GeoJSON in WGS 84: each a works area (a polygon) with the street and house
numbers (`strasse_hausnr`), the surfaces it occupies (`betroffene_bereiche`:
Fahrbahn, Gehweg, Radweg, Parkbucht …), a description, what it does to traffic
in the city's words (`beeintraechtigung`: "Fahrbahn eingeengt", "halbseitige
Straßensperrung", "Vollsperre" …), its kind (`art`), a link for more
information, a public contact and a first and a last day
(`beginn_datum_kombiniert`, written dd.mm.yyyy, or "Beginn vor mehr als einem
Jahr"; `ende_datum_kombiniert`, dd.mm.yyyy or "dd.mm.yyyy 23:59"). Fetched
without a key on 5 November 2026 (12:33 UTC): 5,963 features (5,065 polygons,
898 multi-polygons), 3,148 works ("Baumaßnahme") and 2,815 temporary
no-parking zones ("Vorübergehendes Haltverbot"). A request asking the server
to filter (CQL_FILTER) was answered 503 "Temporarily Not available" that day,
so REI asks for the whole layer and filters itself.

Only works on the carriageway are road events: a feature is kept when it is a
"Baumaßnahme" whose `betroffene_bereiche` include "Fahrbahn" (however the
list is written: "Gehweg,Fahrbahn", "Parkbucht;Fahrbahn", "GehwegFahrbahn").
On 5 November 2026 that was 1,130 features; 5 of them listed twice,
identical, are one record each, so 1,125 records: 970 begun, 131 coming and
24 whose start is not read (23 "Beginn vor mehr als einem Jahr", one of the
year 0226), every one with an end and none ended. No-parking zones (2 of them
on the carriageway), works naming no surface (558) and works on the pavement,
cycle path, pedestrian zone or parking bays only are left out. The city's
impairment words are free text (607 different phrasings among the kept
works), so every kept works is road works, its words kept as stated in the
summary and on its location; REI does not read a closure out of them (a
"Vollsperre" may close only the parking bays). A works naming no street (2
kept) keeps no place; its title says München.

A day runs from its start to its end, Munich time; "23:59" is read as written.
A start stated only as "Beginn vor mehr als einem Jahr" stays unstated. A
date before the year 2000 cannot be a day of works listed for the coming four
weeks (one record of 5 November 2026 begins "07.11.0226"): it is read as
unstated and never corrected.

The feature ids are a running number, and `fachliche_id` is empty but for 298
works (136 of those kept, each the Stadtwerke München's), so every record's
id is made the same way, from what it states: the street and house numbers,
the description, its kind, its first day and its area. A changed end,
impairment or surface is a revision of the same record; a redrawn area is a
new one. The public contact (`kontakt_oeffentlich`: an e-mail address and a
telephone number) is not kept.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0, as the city's
open-data portal states for the dataset (opendata.muenchen.de/dataset/
baustellen_4_weeks_opendata; the portal's robots.txt disallows /api/, which REI
never fetches; geoportal.muenchen.de has no robots.txt)
(docs/data-sources/worldwide-sources-2026-11-05.md).
"""

import json
import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
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

from . import common
from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time, whole_days
from .feed_text import sentences

SOURCE_ID = "de-muenchen-roadworks"
ENDPOINT = "https://geoportal.muenchen.de/geoserver/mor_wfs/ows"
LAYER = "mor_wfs:baustellen_opendata"
PARAMS = {
    "service": "WFS",
    "version": "1.1.0",
    "request": "GetFeature",
    "typeName": LAYER,
    "outputFormat": "application/json",
    "srsName": "EPSG:4326",
}
# The server republishes this layer every hour from 20 minutes past (UTC) and, for
# about three minutes, answers HTTP 404 or an empty 200 now and then (decision 0061:
# REI's 3-hourly poll drifted onto that minute on 6 November 2026 and failed at 08:20
# and 11:20 UTC; a probe every 15 s on 6 November saw 404s from 12:20:03 to 12:22:40
# and the layer before and after). Such an answer is asked again after each pause, in
# the same run, the last at least 3.5 minutes after the first; then the run fails as before.
REPUBLISH_PAUSES_SECONDS = (60.0, 150.0)
_REPUBLISH_ANSWER = re.compile(r"HTTP 404\b|did not return JSON")
SOURCE_URL = "https://opendata.muenchen.de/dataset/baustellen_4_weeks_opendata"
ATTRIBUTION = (
    "Landeshauptstadt München, Baustellen (nächste 4 Wochen); Datenlizenz Deutschland – Namensnennung – "
    f"Version 2.0 (www.govdata.de/dl-de/by-2-0); {SOURCE_URL}; data changed (read into REI events)"
)
BERLIN = ZoneInfo("Europe/Berlin")
WORKS = "Baumaßnahme"
CARRIAGEWAY = "Fahrbahn"
# Public contact e-mail addresses and telephone numbers: not kept.
PERSONAL_FIELDS = frozenset({"kontakt_oeffentlich"})
# A day before this year cannot be one of works listed for the coming four weeks.
EARLIEST_YEAR = 2000


def muenchen_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("germany")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="München roadworks (next 4 weeks)",
        organization="Landeshauptstadt München",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Bayern (München)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.1.0 GetFeature (GeoJSON, EPSG:4326), layer baustellen_opendata; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="muenchen_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled every three hours (one request, about 6 MB).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works area as received, less its public contact.",
        notes=(
            "Munich's works in force or starting within four weeks, each an area with a first and a last "
            "day. Fetched without a key on 5 November 2026: 5,963 features; the 1,130 works on the "
            "carriageway are kept (1,125 records: 994 in force, 131 coming), no-parking zones and "
            "works off the carriageway are not."
        ),
    )


def _day(value: Any) -> date | None:
    """A day written dd.mm.yyyy; None for words ('Beginn vor mehr als einem Jahr') or an impossible year."""
    try:
        day = datetime.strptime(clean(value)[:10], "%d.%m.%Y").date()
    except ValueError:
        return None
    return day if day.year >= EARLIEST_YEAR else None


def _end(value: Any) -> datetime | None:
    """'04.12.2026 23:59' as written, Munich time; '04.12.2026' to the end of that day."""
    moment = local_time(value, BERLIN, ("%d.%m.%Y %H:%M",))
    if moment is not None:
        return moment if moment.year >= EARLIEST_YEAR else None
    return whole_days(None, _day(value), BERLIN)[1]


def is_carriageway_works(properties: dict[str, Any]) -> bool:
    return clean(properties.get("art")) == WORKS and CARRIAGEWAY in clean(properties.get("betroffene_bereiche"))


def record_id(properties: dict[str, Any], geometry: dict[str, Any]) -> str:
    """An id from what the record states: the running feature number is not one."""
    stated = [
        clean(properties.get("strasse_hausnr")),
        clean(properties.get("beschreibung")),
        clean(properties.get("art")),
        clean(properties.get("beginn_datum_kombiniert")),
        geometry,
    ]
    return f"works:{sha256_hex(json.dumps(stated, sort_keys=True, ensure_ascii=False))[:20]}"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works on the carriageway as REI's record; None for anything else."""
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if geometry.get("type") not in ("Polygon", "MultiPolygon") or not is_carriageway_works(properties):
        return None
    place = clean(properties.get("strasse_hausnr"))
    areas = clean(properties.get("betroffene_bereiche"))
    impact = clean(properties.get("beeintraechtigung"))
    first, last = clean(properties.get("beginn_datum_kombiniert")), clean(properties.get("ende_datum_kombiniert"))
    start = whole_days(_day(first), None, BERLIN)[0]
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in (WORKS, areas) if part),
        start=start,
        end=_end(last),
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="works area", geometry=geometry, closure=impact or None)]
        if place
        else [],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}" if first or last else None,
        covers_city=True,
    )
    more = html_to_text(clean(properties.get("weitere_info")))
    return item_record(
        source_id=SOURCE_ID,
        external_id=record_id(properties, geometry),
        url=SOURCE_URL,
        title=f"Road works: {place} (München)" if place else "Road works (München)",
        summary=sentences(
            clean(properties.get("beschreibung")),
            f"Impact: {impact}" if impact else "",
            f"Areas affected: {areas}" if areas else "",
            f"More information: {more}" if more else "",
        ),
        categories=[part for part in (WORKS, *(clean(area) for area in areas.split(","))) if part],
        item=_without_personal_data(feature),
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _without_personal_data(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return feature
    return {**feature, "properties": {k: v for k, v in properties.items() if k not in PERSONAL_FIELDS}}


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def _mid_republish(error: ConnectorError) -> bool:
    """Whether the server answered as it does while the layer is being republished:
    HTTP 404, or a body that is not JSON (an empty 200)."""
    return bool(_REPUBLISH_ANSWER.search(str(error)))


def _fetch_layer(user_agent: str, client: httpx.Client | None) -> Any:
    """The layer, asked again after each pause in REPUBLISH_PAUSES_SECONDS while the
    server answers as it does mid-republish; any other failure fails at once."""
    for pause in (*REPUBLISH_PAUSES_SECONDS, None):
        try:
            return fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
        except ConnectorError as error:
            if pause is None or not _mid_republish(error):
                raise
        common._sleep(pause)
    raise AssertionError("unreachable")


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = _fetch_layer(user_agent, client)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    matched = body.get("numberMatched", body.get("totalFeatures"))
    if isinstance(matched, int) and matched > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} records, more than it returned")
    kept: list[dict] = []
    seen: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict):
            continue
        # Munich lies at about 11.6° E, 48.1° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
        feature = _without_personal_data(feature)
        # A works listed twice, identical but for its running number, is one record.
        same = json.dumps(
            [feature.get("geometry"), feature.get("properties")], sort_keys=True, ensure_ascii=False
        )
        if same in seen:
            continue
        seen.add(same)
        kept.append(feature)
    return kept


class MuenchenRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The record's content: the running feature number is not content."""
        return content_key(raw.get("item", {}), frozenset({"id"}))
