"""Kanton Schwyz, works on its roads lasting more than five days (Baustellen), Switzerland (5 November 2026).

    GET https://map.geo.sz.ch/mapserv_proxy?ogcserver=source%20for%20image%2Fpng&SERVICE=WFS
        &VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:ch.sz.a083a.baustellen.erweitert
        &SRSNAME=urn:ogc:def:crs:EPSG::2056

The Canton of Schwyz's civil engineering office (Tiefbauamt) records the works
on its roads that last more than five days ("Baustellen, welche mehr als 5
Tage dauern, werden erfasst"; catalogue: opendata.swiss, dataset "Baustellen",
organisation Amt für Geoinformation Kanton Schwyz, publisher SZ Tiefbauamt,
updated irregularly). The canton's map server gives them as a WFS 2.0 layer in
GML 3.2 only (no GeoJSON). Each feature is a line along the road on the Swiss
grid LV95 (EPSG:2056), with where (`lokalname`, mostly the road number and the
stretch: "2 / Lauerzerstrasse / Zingel in Seewen SZ"), the works
(`beschreibung`), the first and last day (`baubeginn`, `bauende`, written
2026-08-31), how traffic is hindered (`behinderungsbemerkung`, led by the
canton's level "gering", "mittel" or "stark") and sometimes a link to a plan
(`link`). Fetched without a key on 5 November 2026: 27 lines (numberMatched
27), all with both days; 26 in force and 1 ended on 31 October but still
listed; none to come.

The features carry no id (the server warns "No featureid defined"), and one
works site can be drawn as several lines: the station area of Brunnen
("Bahnhofareal - ÖV - Drehscheibe") is three lines stating the same place,
works, hindrance and days, the Churerstrasse bus lane two. Lines that state
exactly the same are one works site and one record (a MultiLineString); a line
that states anything differently is its own record (a fourth Brunnen line
spelt "Drescheibe", a third Churerstrasse line rated "mittel" rather than
"gering"). On 5 November 2026 the 27 lines are 24 works sites (23 in force, 1
ended). A record's id is made from what the source states and does not
renumber: its place, its first day and its lines on the grid as received. A
changed end or text is a revision of the same record; a redrawn line is a new
one.

Positions are converted from LV95 to WGS 84 longitude and latitude with
swisstopo's approximate formulas (connectors/official/lv95.py). On 5 November
2026 they agreed within 0.7 m with the server's own WGS 84 output (the same
request with SRSNAME urn:ogc:def:crs:EPSG::4326, written latitude first). The
grid values are read rather than the server's degrees so that the ids rest on
the canton's stored values; a position off the Swiss grid, or a layer answered
in another reference system, fails the run (no position is guessed). A feature
with no line is not read.

Days are whole days, Zürich time (Schwyz keeps the same zone): from the start
of the first to the end of the last. Every site is road works (ROAD_WORKS): the
layer holds works on roads only, and none is left out. The hindrance is kept in
the source's words, with its level as the severity; it is not read as a
closure.

Personal data: each line names the site manager and the canton's contact, with
telephone numbers (`kontaktbauleitung`, `kontakttba`); both are dropped before
anything is stored, evidence included.

Licence: opendata.swiss terms "Freie Nutzung. Quellenangabe ist Pflicht"
(terms_by, as the catalogue entry states on both distributions): "Sie dürfen
diesen Datensatz für kommerzielle Zwecke nutzen. Eine Quellenangabe ist Pflicht
(Autor, Titel und Link zum Datensatz)" (https://opendata.swiss/de/terms-of-use,
read 5 November 2026). The credit names the author, the title and the link.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
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

from . import lv95
from .common import fetch_text
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, whole_days
from .feed_text import sentences

SOURCE_ID = "ch-sz-canton-roadworks"
ENDPOINT = "https://map.geo.sz.ch/mapserv_proxy"
LAYER = "ms:ch.sz.a083a.baustellen.erweitert"
LV95 = "urn:ogc:def:crs:EPSG::2056"
PARAMS = {
    "ogcserver": "source for image/png",
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "TYPENAMES": LAYER,
    "SRSNAME": LV95,
}
SOURCE_URL = "https://opendata.swiss/de/dataset/baustellen"
ATTRIBUTION = f"Kanton Schwyz, Tiefbauamt: Baustellen (opendata.swiss, {SOURCE_URL})"
ZURICH = ZoneInfo("Europe/Zurich")
WFS = "{http://www.opengis.net/wfs/2.0}"
GML = "{http://www.opengis.net/gml/3.2}"
MS = "{http://mapserver.gis.umn.edu/mapserver}"
# What a works site states: lines that state all of it alike are one site.
STATED_FIELDS = ("lokalname", "baubeginn", "bauende", "beschreibung", "behinderungsbemerkung", "link")
# The site manager and the canton's contact, with telephone numbers: personal data, not kept.
PERSONAL_FIELDS = frozenset({"kontaktbauleitung", "kontakttba"})
# The canton's level of hindrance, leading the hindrance text ("mittel: Einspurig, …").
LEVEL = re.compile(r"(gering|mittel|stark)\s*:", re.IGNORECASE)
LINE_SHAPES = frozenset({"LineString", "MultiCurve", "MultiLineString"})


def sz_canton_roadworks_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("switzerland")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Kanton Schwyz works on cantonal roads (over five days)",
        organization="Kanton Schwyz, Tiefbauamt (published by the Amt für Geoinformation)",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Schwyz",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method=(
            "WFS 2.0.0 GetFeature (GML 3.2, LV95 EPSG:2056), layer ch.sz.a083a.baustellen.erweitert; "
            "no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="ch_sz_canton_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; updated irregularly; polled every six hours (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "opendata.swiss Freie Nutzung. Quellenangabe ist Pflicht (terms_by): commercial use "
            "permitted, credit required (https://opendata.swiss/de/terms-of-use)"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention=(
            "Each works site's stated fields and its lines on the LV95 grid as received, less the "
            "site manager's and the canton's contacts."
        ),
        notes=(
            "Works lasting more than five days on the roads of the Canton of Schwyz, each a line "
            "with a first and a last day. Fetched without a key on 5 November 2026: 27 lines, 24 "
            "works sites (lines stating the same are one site), 23 in force and 1 ended but still "
            "listed. Positions converted from LV95 with swisstopo's approximate formulas."
        ),
    )


# --- reading the layer -----------------------------------------------------------------


def _name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _lines(shape: ET.Element) -> list[list[list[float]]] | None:
    """A line shape's positions on the grid, [[E, N], …] per line; None when unreadable."""
    lines = []
    for pos_list in shape.iter(f"{GML}posList"):
        try:
            dimension = int(pos_list.get("srsDimension") or 2)
            values = [float(value) for value in (pos_list.text or "").split()]
        except ValueError:
            return None
        if dimension < 2 or len(values) < 2 * dimension or len(values) % dimension:
            return None
        lines.append([values[i : i + 2] for i in range(0, len(values), dimension)])
    return lines or None


def feature_item(feature: ET.Element) -> dict[str, Any] | None:
    """One feature as REI reads it: its stated fields (less personal data) and its lines; None without a line."""
    geom = feature.find(f"{MS}geom")
    shapes = list(geom) if geom is not None else []
    if len(shapes) != 1 or _name(shapes[0]) not in LINE_SHAPES:
        return None
    srs = shapes[0].get("srsName", "")
    if srs and not srs.endswith("2056"):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned positions in {srs}, not LV95 (EPSG:2056)")
    lines = _lines(shapes[0])
    if lines is None:
        return None
    properties = {
        _name(child): (child.text or "").strip()
        for child in feature
        if _name(child) not in ("boundedBy", "geom") and _name(child) not in PERSONAL_FIELDS
    }
    return {"properties": properties, "lines": lines}


def parse_feed(text: str) -> list[dict[str, Any]]:
    """The layer's features; an error when the answer is not the whole layer."""
    try:
        root = ET.fromstring(text.lstrip("﻿"))
    except ET.ParseError as error:
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) is not readable XML: {error}") from error
    if _name(root) == "ExceptionReport":
        message = " ".join(clean(e.text) for e in root.iter() if _name(e) == "ExceptionText")
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) answered with an exception: {message[:200]}")
    if root.tag != f"{WFS}FeatureCollection":
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a WFS feature collection")
    features = [member[0] for member in root.findall(f"{WFS}member") if len(member)]
    matched = root.get("numberMatched", "")
    if matched.isdigit() and int(matched) > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} works, more than it returned")
    layer = LAYER.split(":", 1)[1]
    return [item for feature in features if _name(feature) == layer and (item := feature_item(feature))]


def sites(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The features grouped into works sites: lines that state the same are one site."""
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    for feature in features:
        properties = feature["properties"]
        key = tuple(clean(properties.get(field)) for field in STATED_FIELDS)
        site = grouped.setdefault(key, {"properties": properties, "lines": []})
        site["lines"].extend(feature["lines"])
    for site in grouped.values():
        unique = {json.dumps(line): line for line in site["lines"]}
        site["lines"] = [unique[text] for text in sorted(unique)]
    return list(grouped.values())


# --- one works site ---------------------------------------------------------------------


def geometry(site: dict[str, Any]) -> dict[str, Any] | None:
    """The site's lines in longitude and latitude; None when any position is not on the grid."""
    lines = site.get("lines") or []
    if len(lines) == 1:
        return lv95.geometry("LineString", lines[0])
    return lv95.geometry("MultiLineString", lines) if lines else None


def site_id(site: dict[str, Any]) -> str:
    """Its place, first day and lines on the grid, as stated: none of them renumbers."""
    properties = site.get("properties") or {}
    stated = [clean(properties.get("lokalname")), clean(properties.get("baubeginn")), site.get("lines")]
    return f"site:{sha256_hex(json.dumps(stated, ensure_ascii=False))[:20]}"


def to_record(site: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works site as REI's record; None when its lines are not on the Swiss grid."""
    properties = site.get("properties")
    shape = geometry(site) if isinstance(properties, dict) else None
    if shape is None:
        return None
    place = clean(properties.get("lokalname"))
    first, last = clean(properties.get("baubeginn")), clean(properties.get("bauende"))
    start, end = whole_days(local_day(first, ZURICH), local_day(last, ZURICH), ZURICH)
    hindrance = html_to_text(properties.get("behinderungsbemerkung"))
    level = LEVEL.match(hindrance)
    severity = level.group(1).lower() if level else None
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        severity=severity,
        start=start,
        end=end,
        geometry=shape,
        locations=[SourceLocation(name=place, kind="street section", geometry=shape)] if place else [],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}" if first or last else None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=site_id(site),
        url=SOURCE_URL,
        title=f"Road works: {place} (Kanton Schwyz)" if place else "Road works (Kanton Schwyz)",
        summary=sentences(
            clean(properties.get("beschreibung")),
            f"Behinderung {hindrance}" if hindrance else "",
        ),
        categories=[part for part in ("Baustelle", severity) if part],
        item=site,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    found = sites(parse_feed(fetch_text(ENDPOINT, user_agent, client=client, params=PARAMS)))
    for site in found:
        if geometry(site) is None:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned a position off the Swiss LV95 grid")
    return found


class SzCantonRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)
