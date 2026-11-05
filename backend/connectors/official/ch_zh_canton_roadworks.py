"""Kanton Zürich, works on cantonal roads (Baustellen Kantonsstrassen), Switzerland (5 November 2026).

    GET https://maps.zh.ch/wfs/TbaBaustellenZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature
        &typeNames=ms:baustellen-detailansicht&outputFormat=geojson&srsName=EPSG:4326

The Canton of Zürich's civil engineering office (Tiefbauamt) publishes the
works on the cantonal roads it maintains, current and coming, as a WFS layer
served as GeoJSON in WGS 84 (catalogue: opendata.swiss, "WFS Baustellen
Kantonsstrassen", organisation geoinformation-kanton-zuerich). Each feature is
the works area drawn as a polygon, with the road number (`strassenbez`) and
the kilometre stretch on it (`kmvon`, `kmbis`, the canton's road stationing,
as text), the street (`strassenname`), the commune (`gemeindename`) and any
other communes touched (`weiteregemeinden`), the works (`beschreibung`), how
traffic is led past them (`verkehrsfuehrung`), the status (`status_baustelle`:
"aktiv (Bauzeit)", "zukünftig (Bauzeit in Zukunft)"), the first and last day
(`datum_baubeginn`, `datum_bauende`) and when the entry was last changed
(`lmutdat`). Fetched without a key on 5 November 2026: 55 works (numberMatched
55), all polygons, 52 under way and 3 to come, none ended. The GeoJSON is
written longitude first (Zürich lies at about 8.5° E, 47.4° N).

The features carry no id. A works site is where it is on a cantonal road, so
REI's record id is the road number with its kilometre stretch, as the source
states them (unique among the 55); a changed period, text or drawing of the
same stretch is a revision of the same record.

`datum_baubeginn` and `datum_bauende` are dates: 23 of the 55 starts are
written at midnight, the rest with a clock time that matches the end's to
within seconds (2026-04-20T08:26:18 and 2028-05-31T08:26:30), the moment the
dates were entered, not working hours; four ends read 01:00. Each is therefore
read as the day it names: the period runs from the start of the first day to
the end of the last, Zürich time. Every record is road works (ROAD_WORKS); the
traffic arrangements are kept in the source's words, not read as a closure.

Personal data: each works names a contact person and a telephone number
(`ansprechperson`, `telefonnummer`); both are dropped before anything is
stored, evidence included. `link1` is sometimes the works' page on www.zh.ch
(1 of 55), which is then the record's address, and sometimes a video (3).

Licence: opendata.swiss terms "Freie Nutzung" (terms_open, as the catalogue
entry states): "Sie dürfen diesen Datensatz für kommerzielle Zwecke nutzen.
Eine Quellenangabe wird empfohlen" (https://opendata.swiss/de/terms-of-use,
read by the researcher on 5 November 2026). Credit is recommended and given.
"""

import json
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
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, local_time, whole_days
from .feed_text import sentences

SOURCE_ID = "ch-zh-canton-roadworks"
ENDPOINT = "https://maps.zh.ch/wfs/TbaBaustellenZHWFS"
LAYER = "ms:baustellen-detailansicht"
PARAMS = {
    "Service": "WFS",
    "Version": "2.0.0",
    "Request": "GetFeature",
    "typeNames": LAYER,
    "outputFormat": "geojson",
    "srsName": "EPSG:4326",
}
SOURCE_URL = "https://opendata.swiss/de/dataset/wfs-baustellen-kantonsstrassen"
ATTRIBUTION = "Kanton Zürich, Tiefbauamt: Baustellen Kantonsstrassen (opendata.swiss)"
ZURICH = ZoneInfo("Europe/Zurich")
# A named contact person and a telephone number: personal data, not kept.
PERSONAL_FIELDS = frozenset({"ansprechperson", "telefonnummer"})
# When the entry was last touched: not content.
BOOKKEEPING = frozenset({"lmutdat"})


def zh_canton_roadworks_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("switzerland")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Kanton Zürich works on cantonal roads",
        organization="Kanton Zürich, Baudirektion, Tiefbauamt",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Zürich",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 2.0.0 GetFeature (GeoJSON, EPSG:4326), layer baustellen-detailansicht; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="ch_zh_canton_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled every six hours (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "opendata.swiss Freie Nutzung (terms_open): commercial use permitted, credit recommended "
            "(https://opendata.swiss/de/terms-of-use)"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works area as received, less its contact person and telephone number.",
        notes=(
            "Works on the cantonal roads of the Canton of Zürich, current and coming, each a polygon "
            "with a first and a last day. Fetched without a key on 5 November 2026: 55 works, 52 under "
            "way and 3 to come. Record ids are the stated road number and kilometre stretch."
        ),
    )


def record_id(properties: dict[str, Any], geometry: dict[str, Any]) -> str:
    """The road and its kilometre stretch as stated; without them, a fingerprint of what is stated."""
    road, start_km, end_km = (clean(properties.get(key)) for key in ("strassenbez", "kmvon", "kmbis"))
    if road and (start_km or end_km):
        return f"road:{road}:km:{start_km}-{end_km}"
    stated = [
        clean(properties.get("strassenname")),
        clean(properties.get("gemeindename")),
        clean(properties.get("datum_baubeginn"))[:10],
        geometry,
    ]
    return f"works:{sha256_hex(json.dumps(stated, sort_keys=True, ensure_ascii=False))[:20]}"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if geometry.get("type") not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point"):
        return None
    street = clean(properties.get("strassenname"))
    commune = clean(properties.get("gemeindename"))
    road = clean(properties.get("strassenbez"))
    start_km, end_km = clean(properties.get("kmvon")), clean(properties.get("kmbis"))
    first, last = clean(properties.get("datum_baubeginn")), clean(properties.get("datum_bauende"))
    start, end = whole_days(local_day(first, ZURICH), local_day(last, ZURICH), ZURICH)
    status = clean(properties.get("status_baustelle"))
    traffic = clean(properties.get("verkehrsfuehrung"))
    others = clean(properties.get("weiteregemeinden"))
    place = ", ".join(part for part in (street, commune) if part)
    page = clean(properties.get("link1"))
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        status=status or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="location", geometry=geometry)] if place else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first[:10]} – {last[:10]}" if first or last else None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=record_id(properties, geometry),
        # The works' own page on zh.ch when the canton links one (a video link is not one).
        url=page if page.startswith("https://www.zh.ch/") else SOURCE_URL,
        title=f"Road works: {street or 'cantonal road'} ({commune or 'Kanton Zürich'})",
        summary=sentences(
            clean(properties.get("beschreibung")),
            f"Verkehrsführung: {traffic}" if traffic else "",
            # The road number (strassenbez) and stationing as stated, without a name for the road class.
            f"Strasse {road}, km {start_km} – {end_km}" if road else "",
            f"Weitere Gemeinden: {others}" if others else "",
        ),
        categories=[part for part in ("Baustelle Kantonsstrasse", status) if part],
        item=_without_personal_data(feature),
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=local_time(properties.get("lmutdat"), ZURICH, ("%Y-%m-%dT%H:%M:%S",)),
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


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    matched = body.get("numberMatched", body.get("totalFeatures"))
    if isinstance(matched, int) and matched > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} works, more than it returned")
    works = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        # Zürich lies at about 8.5° E, 47.4° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
        works.append(_without_personal_data(feature))
    return works


class ZhCantonRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The works' content: a new last-changed time alone is not a revision."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in BOOKKEEPING
        }
        return content_key({**item, "properties": properties}, frozenset())
