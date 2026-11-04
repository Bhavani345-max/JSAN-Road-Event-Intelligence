"""Statens vegvesen road traffic situations, Norway (4 November 2026).

    GET https://ogckart-sn1.atlas.vegvesen.no/datex_3_1/ows?service=WFS&version=1.0.0
        &request=GetFeature&typeName=datex_3_1:SituationSimple_v2&outputFormat=application/json

The Norwegian Public Roads Administration (Statens vegvesen, NPRA) publishes
the road traffic messages of its traffic centres (roadworks, closures, lane
measures, diversions, accidents, obstructions, winter closures, ferry notices)
as DATEX II 3.1 situations. Its DATEX server needs an account, but the same
publication is also served openly as a WFS by a GeoServer: "NPRA publishes
Datex II WFS/WMS pull services that are open available. We do encourage the
consumer to identify themselves by sending an email to datex@vegvesen.no"
(README of git.vegvesen.no/projects/DATEX2/repos/datex2-spesifications,
3.1/wfs-wms). The simplified layer `SituationSimple_v2` gives one GeoJSON
feature per situation record: the situation (`SITUATION_ID`), the record
(`RECORD_ID`, `IS_MAIN_RECORD`), its DATEX II type and detail
(`SITUATION_TYPE`: MaintenanceWorks, RoadOrCarriagewayOrLaneManagement, …;
`SECONDARY_TYPES`: roadworks, roadClosed, laneClosures, …), a start and an end
with their offsets, the severity, the road number, a location description and
a description in Norwegian, and a WGS 84 line or point. Fetched without a key on
4 November 2026: 2,394 records of 1,075 situations, every one with a geometry
and a start; 4 records (2 situations, strong-wind closures) without an end.

One situation is one event on the road, so REI keeps one record per situation,
read by the same rules as the DATEX II feeds of the Netherlands and Luxembourg
(connectors/official/datex3_nl_lu.py: the type of the record that says most
about the road, the period from the earliest start to the latest end, the
lines the records draw). The records of a situation share one geometry and one
period. A situation made only of ferry notices (`TransitInformation`: a ferry
cancelled or delayed) is not a road event and is not kept.

What the source says is kept in its words: the Norwegian description (its
parts, which the source separates with "|") and the location description,
which names the road and the places ("Fv. 44 Vodla i Stavanger, Rogaland - …").
Statens vegvesen's conditions for DATEX information say "Norske meldinger skal
ikke oversettes til andre språk" (Norwegian messages are not to be translated):
REI's English titles are made from the DATEX II codes only, and the Norwegian
text is never translated. Lines naming a contact person, a phone number or an
e-mail address are removed before anything is kept (none on 4 November 2026).
The feed's internal ids (`ID`, `PUB_ID`) and fetch-time flag (`ACTIVE`) are
not content and are not kept.

Licence: Norwegian Licence for Open Government Data (NLOD) 2.0, which lets the
licensee "use the information for any purpose and in all contexts"
(https://data.norge.no/nlod/en/2.0, §2), as Statens vegvesen states for its
DATEX information ("Informasjon i DATEX-format fra Statens vegvesen er gjort
tilgjengelig under Norsk lisens for offentlige data") and on the dataset
(dataut.vegvesen.no/en/dataset/trafikkmeldinger). Credit Statens vegvesen
(its condition 4; NLOD §5) (docs/data-sources/nordics-sources-2026-11-04.md).
"""

import re
from collections import defaultdict
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
    SourceType,
    TermsStatus,
)

from . import datex3_nl_lu as datex
from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean

SOURCE_ID = "norway-vegvesen-datex-situations"
ENDPOINT = "https://ogckart-sn1.atlas.vegvesen.no/datex_3_1/ows"
LAYER = "datex_3_1:SituationSimple_v2"
PARAMS = {
    "service": "WFS",
    "version": "1.0.0",
    "request": "GetFeature",
    "typeName": LAYER,
    "outputFormat": "application/json",
}
SOURCE_URL = "https://dataut.vegvesen.no/en/dataset/trafikkmeldinger"
LICENCE = (
    "Norwegian Licence for Open Government Data (NLOD) 2.0 (https://data.norge.no/nlod/en/2.0), "
    "with Statens vegvesen's DATEX conditions: credit Statens vegvesen; do not translate Norwegian messages"
)
ATTRIBUTION = (
    "Contains data under the Norwegian licence for Open Government data (NLOD) distributed by Statens vegvesen"
)
OSLO = ZoneInfo("Europe/Oslo")
# A ferry cancelled, delayed or with less room: not an event on the road.
NOT_ROAD_EVENTS = frozenset({"TransitInformation"})
EVENTS = (
    EventType.PLANNED_ROAD_CLOSURE.value,
    EventType.EMERGENCY_ROAD_CLOSURE.value,
    EventType.LANE_RESTRICTION.value,
    EventType.ROAD_WORKS.value,
    EventType.TRAFFIC_DIVERSION.value,
    EventType.ACCIDENT.value,
    EventType.ROAD_HAZARD.value,
    EventType.SPECIAL_EVENT.value,
)

# Norwegian contact details: an e-mail address, a phone number (eight digits in
# pairs or as 3-2-3, with or without +47; spaces only: dots are dates, hyphens
# hours, "kl. 1010-1210"), or a word naming a contact. A line holding any of
# them is removed.
_PHONE_NO = re.compile(r"(?<![\w+])(?:\+47\s?)?(?:\d{2}(?:\s?\d{2}){3}|\d{3}\s\d{2}\s\d{3})(?![\d.\-])")
_CONTACT_WORDS_NO = re.compile(r"(?i)\b(tlf\.?|telefon\w*|e-?post\w*|kontaktperson\w*|mobilnr\w*|mobilnummer\w*)")


def vegvesen_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("norway")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Statens vegvesen road traffic situations (DATEX II), Norway",
        organization="Statens vegvesen (Norwegian Public Roads Administration)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="National",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.0.0 GetFeature, layer SituationSimple_v2 (DATEX II 3.1 as GeoJSON, WGS 84); open, no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="no",
        events_supported=EVENTS,
        parser_type="norway_vegvesen_datex",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "None published; Statens vegvesen asks consumers to identify themselves at datex@vegvesen.no; "
            "polled every 30 minutes (one request)."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=LICENCE,
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=True,
        evidence_retention=(
            "Each situation's records as the fields they state (types, times, severity, road number, "
            "location description, Norwegian description in its parts, line or point), without the feed's "
            "internal ids and fetch-time flag; lines naming a contact person, phone number or e-mail "
            "address are removed."
        ),
        notes=(
            "The road traffic messages of Statens vegvesen's traffic centres (works, closures, lane "
            "measures, diversions, accidents, obstructions) on Norway's roads, current and planned. "
            "Fetched without a key on 4 November 2026: 2,394 records of 1,075 situations, all with a "
            "line or point and a start, 2 situations without an end. One record per situation; ferry "
            "notices are left out. Norwegian texts are kept as written and never translated "
            "(Statens vegvesen's DATEX condition 2)."
        ),
    )


def without_contact_details(text: str | None) -> str | None:
    """The text with each line naming a contact replaced by a marker; None for nothing.

    Norwegian forms only: the Dutch phone pattern of the DATEX II reader takes a
    Norwegian date and hour ("05.11.2026 08:00") for a number.
    """
    if not text:
        return None
    lines = []
    for line in text.splitlines():
        if datex._EMAIL.search(line) or _PHONE_NO.search(line) or _CONTACT_WORDS_NO.search(line):
            if not lines or lines[-1] != datex.REMOVED:
                lines.append(datex.REMOVED)
        else:
            lines.append(line)
    return "\n".join(lines).strip() or None


def _stated_time(value: Any) -> str | None:
    """A time as written, without the zone name some versions append ('…+01:00[GMT+01:00]')."""
    text = clean(value)
    return re.sub(r"\[[^\]]*\]$", "", text) or None


def _number(value: Any) -> str:
    return repr(float(value))


def _shape(geometry: Any) -> dict[str, Any]:
    """The feature's geometry in the form the DATEX II reader takes: GeoJSON lines
    as longitude-latitude position lists (CRS84), a point as 'latitude longitude'."""
    if not isinstance(geometry, dict):
        return {}
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    try:
        if kind == "Point":
            longitude, latitude = coordinates[:2]
            return {"points": [f"{_number(latitude)} {_number(longitude)}"]}
        lines = [coordinates] if kind == "LineString" else coordinates if kind == "MultiLineString" else []
        return {
            "lines": [
                {"srs": "CRS84", "posList": " ".join(f"{_number(p[0])} {_number(p[1])}" for p in line)}
                for line in lines
                if isinstance(line, list) and len(line) >= 2
            ]
        }
    except (TypeError, ValueError, IndexError):
        return {}


def record_item(feature: dict[str, Any]) -> dict[str, Any]:
    """One situation record as the fields it states (REI's evidence of it)."""
    properties = feature.get("properties") or {}
    kind = clean(properties.get("SITUATION_TYPE"))
    secondary = clean(properties.get("SECONDARY_TYPES"))
    management = clean(properties.get("ROAD_OR_CARRIAGEWAY_OR_LANE_MANAGEMENT_TYPE"))
    vehicles = clean(properties.get("VEHICLE_USAGE"))
    location = clean(properties.get("LOCATION_DESCRIPTION"))
    road_number = clean(properties.get("ROAD_NUMBER"))
    parts = [part for part in str(properties.get("DESCRIPTION") or "").split("|") if part.strip()]
    lanes = properties.get("IMPACT_NUMBER_OF_LANES")
    item: dict[str, Any] = {
        "id": clean(properties.get("RECORD_ID")) or None,
        "type": kind or None,
        "detail": management or secondary or None,
        "details": {
            key: value
            for key, value in (("secondaryTypes", secondary), ("vehicleUsage", vehicles))
            if value and value != (management or secondary)
        }
        or None,
        "main": properties.get("IS_MAIN_RECORD") in (1, "1", True),
        "start": _stated_time(properties.get("START_TIME")),
        "end": _stated_time(properties.get("END_TIME")),
        "created": _stated_time(properties.get("CREATION_DATE")),
        "updated": _stated_time(properties.get("LAST_UPDATE_TIME")),
        "probability": clean(properties.get("PROBABILITY")) or None,
        "severity": clean(properties.get("SEVERITY")) or None,
        "road_number": road_number or None,
        # Where the source says the record is: its location description names the road.
        "roads": [location or road_number] if location or road_number else [],
        "lanes_affected": str(lanes) if lanes is not None else None,
        # [comment type, text]: the description's parts, in Norwegian, as written.
        "comments": [[None, text] for part in parts if (text := without_contact_details(part.strip()))],
        **_shape(feature.get("geometry")),
    }
    return {key: value for key, value in item.items() if value not in (None, "", [], {}, False)}


def situation_items(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The features grouped into their situations, in the order the feed gives them."""
    by_situation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        situation_id = clean((feature.get("properties") or {}).get("SITUATION_ID"))
        if situation_id:
            by_situation[situation_id].append(feature)
    items = []
    for situation_id, members in by_situation.items():
        records = [record_item(feature) for feature in members]
        # The same record is sometimes served twice (two feature rows): kept once.
        unique: list[dict[str, Any]] = []
        for record in records:
            if record not in unique:
                unique.append(record)
        main = next((record for record in unique if record.get("main")), unique[0])
        # The records of a situation repeat its line or point: each shape is kept once,
        # on the main record (works, an obstruction, an accident …) or else the first
        # record that gives it.
        seen: list[Any] = [main[key] for key in ("lines", "points") if key in main]
        for record in unique:
            if record is main:
                continue
            for key in ("lines", "points"):
                if key in record:
                    if record[key] in seen:
                        del record[key]
                    else:
                        seen.append(record[key])
        items.append(
            {
                "id": situation_id,
                "severity": main.get("severity"),
                # Bookkeeping: when the source last touched the situation (not content).
                "version_time": max((record.get("updated") or "" for record in unique), default="") or None,
                "records": [{k: v for k, v in record.items() if k != "updated"} for record in unique],
            }
        )
    return [{key: value for key, value in item.items() if value not in (None, "", [], {})} for item in items]


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def fetch_situations(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    matched = body.get("numberMatched", body.get("totalFeatures"))
    if isinstance(matched, int) and matched > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} records, more than it returned")
    features = [feature for feature in features if isinstance(feature, dict)]
    for feature in features:
        # Norway lies at 4-32° E, 57-72° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
    return situation_items(features)


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One situation as REI's record; None when it is only ferry notices."""
    records = item.get("records", [])
    if not records or all(record.get("type") in NOT_ROAD_EVENTS for record in records):
        return None
    return datex.situation_record(
        item,
        source_id=SOURCE_ID,
        url=SOURCE_URL,
        attribution=ATTRIBUTION,
        default_authority="Statens vegvesen",
        zone=OSLO,
        retrieved_at=retrieved_at,
    )


class VegvesenSituationsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_situations)
    to_record = staticmethod(to_record)
    revision_key = staticmethod(datex.revision_key)
