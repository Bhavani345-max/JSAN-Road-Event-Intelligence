"""Vienna roadworks affecting traffic, Austria (21 October 2026).

    GET https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0
        &typeName=ogdwien:BAUSTELLENLINOGD&srsName=EPSG:4326&outputFormat=json
    and the same with typeName=ogdwien:BAUSTELLENPKTOGD

The City of Vienna's current and coming traffic-affecting works and closures
on the main road network, in two layers (WFS, GeoJSON): street sections as WGS
84 lines (`BAUSTELLENLINOGD`) and single sites as points (`BAUSTELLENPKTOGD`).
Each states its district, where it is (`BEZEICHNUNG`), the kind of works
(`BEHINDERUNGSART`: Straßenbau, Rohrlegung, Gleisbau …), the press text with
the lane closures and detours, the applicant, and a first and a last day
(`OBJEKT_BEGINN`, `OBJEKT_ENDE`, written '2026-10-15Z'). Fetched without a
key on 21 October 2026: 53 lines and 22 points, all with both days. The GeoJSON
is written longitude first, although it names urn:ogc:def:crs:EPSG::4326.

A period stated in days runs from the start of the first day to the end of
the last, Vienna time. Works are road works; any other kind keeps its words
with no type.

The feature ids (and OBJECTID) are renumbered each time the layers are
reloaded: every one of the 75 changed between 16 and 21 October 2026. A
record's id is therefore made from what the source states and does not
renumber: its layer, district, place, kind of works, first day and geometry.
A changed end or press text is a revision of the same record; a redrawn
geometry is a new one.

Each record names a contact person and telephone number
(`ANSPRECHPERSON`, `ANSPRECHPERSON_TEL`); both are not kept.

Licence: CC BY 4.0, credit "Datenquelle: Stadt Wien – data.wien.gv.at"
(Stadt Wien's OGD terms; the data.gv.at entries of both layers name CC BY 4.0
on every distribution) (docs/data-sources/belgium-germany-austria-connectors-2026-10-21.md).
"""

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
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

from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, whole_days

SOURCE_ID = "vienna-roadworks"
ENDPOINT = "https://data.wien.gv.at/daten/geo"
LINES, POINTS = "BAUSTELLENLINOGD", "BAUSTELLENPKTOGD"
# The data.gv.at catalogue entry of each layer: where a record is described.
DATASETS = {
    LINES: "https://www.data.gv.at/katalog/datasets/3df7a50f-108d-40bc-a041-e3092fc50a81",
    POINTS: "https://www.data.gv.at/katalog/datasets/88e7ff53-257d-4299-99b5-c659b87b5116",
}
SOURCE_URL = DATASETS[LINES]
ATTRIBUTION = "Datenquelle: Stadt Wien – data.wien.gv.at (CC BY 4.0)"
VIENNA = ZoneInfo("Europe/Vienna")
# A named contact person and telephone number: personal data, not kept.
PERSONAL_FIELDS = frozenset({"ANSPRECHPERSON", "ANSPRECHPERSON_TEL"})
# Renumbered at each reload: not content.
RENUMBERED_FIELDS = frozenset({"OBJECTID"})
WORKS = re.compile(r"bau|arbeiten|rohrlegung", re.IGNORECASE)


def params_for(layer: str) -> dict[str, str]:
    return {
        "service": "WFS",
        "request": "GetFeature",
        "version": "1.1.0",
        "typeName": f"ogdwien:{layer}",
        "srsName": "EPSG:4326",
        "outputFormat": "json",
    }


def vienna_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("vienna")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Vienna roadworks affecting traffic",
        organization="Stadt Wien",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Wien",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.1.0 GetFeature (GeoJSON, EPSG:4326), two layers; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="vienna_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled every three hours (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/deed.de)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention="Each works record as received, less its contact person and telephone number.",
        notes=(
            "Vienna's traffic-affecting works and closures on the main road network: street sections "
            "(lines) and sites (points), each with a first and a last day. Fetched without a key on "
            "21 October 2026: 53 lines, 22 points. The source renumbers its ids at each reload; REI's "
            "record ids are made from the stated layer, place, works, first day and geometry."
        ),
    )


def record_id(layer: str, properties: dict[str, Any], geometry: dict[str, Any]) -> str:
    """An id from what the record states and the source does not renumber."""
    stated = [
        layer,
        clean(properties.get("BEZIRK")),
        clean(properties.get("BEZEICHNUNG")),
        clean(properties.get("BEHINDERUNGSART")),
        clean(properties.get("OBJEKT_BEGINN")),
        geometry,
    ]
    return f"{layer}:{sha256_hex(json.dumps(stated, sort_keys=True, ensure_ascii=False))[:20]}"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    layer = clean(feature.get("id")).split(".")[0]
    if layer not in DATASETS or geometry.get("type") not in ("LineString", "MultiLineString", "Point"):
        return None
    place = clean(properties.get("BEZEICHNUNG"))
    works = clean(properties.get("BEHINDERUNGSART"))
    district = clean(properties.get("BEZIRK"))
    first, last = clean(properties.get("OBJEKT_BEGINN")), clean(properties.get("OBJEKT_ENDE"))
    start, end = whole_days(local_day(first, VIENNA), local_day(last, VIENNA), VIENNA)
    is_works = bool(WORKS.search(works))
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value if is_works else None,
        category=" / ".join(part for part in (works, clean(properties.get("GISCODE_TXT"))) if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street section" if layer == LINES else "location",
                geometry=geometry,
            )
        ]
        if place
        else [],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first[:10]} – {last[:10]}" if first or last else None,
        covers_city=True,
    )
    where = f"Vienna, district {district}" if district else "Vienna"
    return item_record(
        source_id=SOURCE_ID,
        external_id=record_id(layer, properties, geometry),
        url=DATASETS[layer],
        title=f"{'Road works' if is_works else works or 'Works'}: {place or 'Vienna'} ({where})",
        summary=". ".join(
            part.rstrip(".")
            for part in (works, clean(properties.get("PRESSETEXT")), clean(properties.get("ANTRAGSTELLER")))
            if part
        )
        or None,
        categories=[part for part in (works, "street section" if layer == LINES else "site") if part],
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
    position = (geometry or {}).get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    works: list[dict] = []
    for layer in (LINES, POINTS):
        body = fetch_json(ENDPOINT, user_agent, client=client, params=params_for(layer))
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{ENDPOINT} ({layer}) did not return a GeoJSON feature collection")
        matched = body.get("numberMatched", body.get("totalFeatures"))
        if isinstance(matched, int) and matched > len(features):
            raise ConnectorError(f"{ENDPOINT} ({layer}) lists {matched} records, more than it returned")
        for feature in features:
            if not isinstance(feature, dict):
                continue
            # Vienna lies at about 16.4° E, 48.2° N: a first number above the second is a latitude.
            position = _first_position(feature.get("geometry"))
            if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
                raise ConnectorError(f"{ENDPOINT} ({layer}) returned coordinates in latitude-longitude order")
            works.append(_without_personal_data(feature))
    return works


class ViennaRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The record's content: ids the source renumbers at each reload are not content."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in RENUMBERED_FIELDS
        }
        return content_key({**item, "properties": properties}, frozenset({"id"}))
