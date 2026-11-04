"""Copenhagen excavation permits (gravetilladelser), Denmark (4 November 2026).

    GET https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature
        &typeName=k101:gravetilladelser_aktiv_aabne&outputFormat=json&SRSNAME=EPSG:4326

The City of Copenhagen (Københavns Kommune) publishes the excavation permits
it has granted on public roads and private shared roads that are active or
coming ("Oversigt over gravetilladelser givet på offentlige veje eller private
fællesveje i Københavns Kommune"; catalogue: opendata.dk, city-of-copenhagen/
gravetilladelser), a WFS layer served as GeoJSON in WGS 84. Each feature is one
shape of a permit: its case number (`sagsnr`), where (`lokation`, a street and
house numbers), the first and last day (`projekt_start`, `projekt_slut`,
written '29-06-26'), the daily working hours (`tidspunkt_fra`, `tidspunkt_til`),
what is laid or mended (`kategori`: Fibernet, EL, Fjernvarme, Asfaltarbejder …)
and which surfaces are dug (`gravetype`: Kørebane, Cykelsti, Fortov, P-Areal,
Grønt areal, "Tættere end 4 m på træer"). Fetched without a key on 4 November
2026: 2,994 shapes of 1,597 permits (lines, polygons and points), every one with
both days; none had ended.

A permit is one event, so REI keeps one record per permit: its works area as
drawn (the polygons; else the lines; else the point), the period from the start
of the first day to the end of the last, Copenhagen time (the daily hours are
kept in the stated period, not read as the period). Every permit is road works
(ROAD_WORKS); a permit does not say whether traffic is closed, and REI does not
say so either. Only permits that dig the carriageway (Kørebane) or a cycle path
(Cykelsti) are road events; a permit for the pavement, parking spaces or green
areas only is not kept (642 of the 1,597 dug a carriageway or a cycle path).

Personal data: the developer (`bygherre`) and the contractor (`entreprenoer`)
are sometimes private persons (a named homeowner, a one-man firm "v/" its
owner), so both are dropped before anything is stored, evidence included. The
feature ids and `ogc_fid` are the server's row numbers, not content.

Licence: CC BY 4.0, as Københavns Kommune's Open Data DK catalogue entry for the
dataset states (license_id CC-BY-4.0, https://creativecommons.org/licenses/by/
4.0/); the rendered dataset page shows no licence text, and the city's general
terms page was not found (docs/data-sources/nordics-sources-2026-11-04.md).
"""

import json
from collections import defaultdict
from datetime import date, datetime
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
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days

SOURCE_ID = "copenhagen-excavation-permits"
ENDPOINT = "https://wfs-kbhkort.kk.dk/k101/ows"
LAYER = "k101:gravetilladelser_aktiv_aabne"
PARAMS = {
    "service": "WFS",
    "version": "1.0.0",
    "request": "GetFeature",
    "typeName": LAYER,
    "outputFormat": "json",
    "SRSNAME": "EPSG:4326",
}
SOURCE_URL = "https://www.opendata.dk/city-of-copenhagen/gravetilladelser"
ATTRIBUTION = "Københavns Kommune, Gravetilladelser (Open Data DK), CC BY 4.0"
COPENHAGEN = ZoneInfo("Europe/Copenhagen")
# The developer and the contractor may be private persons: not kept.
PERSONAL_FIELDS = frozenset({"bygherre", "entreprenoer"})
# The server's row numbers: not content.
ROW_NUMBERS = frozenset({"ogc_fid"})
# Dug surfaces that road users travel on.
ROAD_SURFACES = frozenset({"Kørebane", "Cykelsti"})


def copenhagen_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("copenhagen")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Copenhagen excavation permits (gravetilladelser)",
        organization="Københavns Kommune",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Hovedstaden",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.0.0 GetFeature (GeoJSON, EPSG:4326), layer gravetilladelser_aktiv_aabne; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="da",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="copenhagen_excavation",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no robots.txt; polled every three hours (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), as the Open Data DK catalogue entry states",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention="Each permit's shapes as received, less the developer and the contractor.",
        notes=(
            "Excavation permits granted on Copenhagen's public and private shared roads, active or "
            "coming, each with a first and a last day. Fetched without a key on 4 November 2026: 2,994 "
            "shapes of 1,597 permits; the 642 that dig a carriageway or a cycle path are kept, one "
            "record per permit."
        ),
    )


def _day(value: Any) -> date | None:
    """'29-06-26': day, month, two-digit year."""
    try:
        return datetime.strptime(clean(value), "%d-%m-%y").date()
    except ValueError:
        return None


def _surfaces(properties: dict[str, Any]) -> list[str]:
    return [part for part in (clean(text) for text in clean(properties.get("gravetype")).split(",")) if part]


def _geometry(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The permit's works area: its polygons, else its lines, else its first point."""
    shapes = [feature.get("geometry") for feature in features if isinstance(feature.get("geometry"), dict)]
    polygons = [s["coordinates"] for s in shapes if s.get("type") == "Polygon"]
    polygons += [part for s in shapes if s.get("type") == "MultiPolygon" for part in s["coordinates"]]
    if polygons:
        return {"type": "Polygon", "coordinates": polygons[0]} if len(polygons) == 1 else {"type": "MultiPolygon", "coordinates": polygons}
    lines = [s["coordinates"] for s in shapes if s.get("type") == "LineString"]
    lines += [part for s in shapes if s.get("type") == "MultiLineString" for part in s["coordinates"]]
    if lines:
        return {"type": "LineString", "coordinates": lines[0]} if len(lines) == 1 else {"type": "MultiLineString", "coordinates": lines}
    points = [s for s in shapes if s.get("type") == "Point"]
    return points[0] if points else None


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One permit as REI's record; None when it digs no carriageway or cycle path."""
    features = item.get("features") or []
    if not features or not item.get("sagsnr"):
        return None
    properties = features[0].get("properties") or {}
    surfaces = list(dict.fromkeys(part for feature in features for part in _surfaces(feature.get("properties") or {})))
    if not ROAD_SURFACES & set(surfaces):
        return None
    geometry = _geometry(features)
    if geometry is None:
        return None
    place = clean(properties.get("lokation"))
    works = clean(properties.get("kategori"))
    first, last = clean(properties.get("projekt_start")), clean(properties.get("projekt_slut"))
    hours_from, hours_to = clean(properties.get("tidspunkt_fra")), clean(properties.get("tidspunkt_til"))
    start, end = whole_days(_day(first), _day(last), COPENHAGEN)
    hours = f", tidspunkt {hours_from}–{hours_to}" if hours_from or hours_to else ""
    dug = ", ".join(surfaces)
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in (works, dug) if part) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street section" if geometry["type"] in ("LineString", "MultiLineString") else "location",
                geometry=geometry,
            )
        ]
        if place
        else [],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}{hours}" if first or last else None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"permit:{item['sagsnr']}",
        url=SOURCE_URL,
        title=f"Road works: {place or 'Copenhagen'} (Copenhagen)",
        summary=". ".join(
            part
            for part in (
                f"Gravetilladelse {item['sagsnr']}",
                works,
                f"Gravetype: {dug}" if dug else "",
                f"Tidspunkt {hours_from}–{hours_to}" if hours_from or hours_to else "",
            )
            if part
        ),
        categories=[part for part in (works, *surfaces) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """A shape as REI keeps it: geometry and properties, less personal data and row numbers."""
    properties = feature.get("properties") or {}
    return {
        "geometry": feature.get("geometry"),
        "properties": {
            key: value for key, value in properties.items() if key not in PERSONAL_FIELDS | ROW_NUMBERS
        },
    }


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def permits(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The shapes grouped by permit, each permit's shapes in a fixed order."""
    by_permit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        number = clean((feature.get("properties") or {}).get("sagsnr"))
        if number:
            by_permit[number].append(_kept(feature))
    return [
        {
            "sagsnr": number,
            "features": sorted(shapes, key=lambda shape: json.dumps(shape, sort_keys=True, ensure_ascii=False)),
        }
        for number, shapes in by_permit.items()
    ]


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    matched = body.get("numberMatched", body.get("totalFeatures"))
    if isinstance(matched, int) and matched > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} shapes, more than it returned")
    features = [feature for feature in features if isinstance(feature, dict)]
    for feature in features:
        # Copenhagen lies at about 12.6° E, 55.7° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
    return permits(features)


class CopenhagenExcavationPermitsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
