"""TechnologieRegion Karlsruhe roadworks, Germany (5 November 2026).

    GET https://mobil.trk.de/geoserver/TBA/ows?service=WFS&version=1.0.0&request=GetFeature
        &typeName=TBA:baustellen_aktuell&outputFormat=application/json&srsName=EPSG:4326
    and the same with typeName=TBA:baustellen_vorschau

The works of the cities of the TechnologieRegion Karlsruhe (Karlsruhe,
Bruchsal, Rheinstetten, Stutensee, Rastatt, Baden-Baden, Ettlingen) and of the
Collectivité européenne d'Alsace, in two WFS layers served as GeoJSON: the
works in force (`baustellen_aktuell`) and those starting from tomorrow
(`baustellen_vorschau`). Asked for EPSG:4326 (the layers are stored in
EPSG:25832), the server writes longitude first. Each works ("Vorgang") is one
or more features sharing its city (`datenquelle`) and works number
(`vorgangsnummer`): each area or line it occupies, and a marker point for
each. They all state where (`lage`), the kind of works (`art`: Gas bzw.
Wasserversorgung, Fernwärmeversorgung, Bauliche Sondernutzung …), what it
does to traffic (`sperrung`: "mit Vollsperrung", "mit Sperrung in eine
Fahrtrichtung", "mit Verkehrsbehinderung", "keine Verkehrsbehinderung"), who
causes it (`verursacher`: Stadtwerke Karlsruhe, Tiefbauamt, "Privat" …), a
note in HTML (`zusatzinfo`), a project number (`projektnummer`), the date of
the information (`stand`) and the period (`vorgangszeitraum_von`, `_bis`).
The period is two UTC instants, read as such: mostly the start and the end of
the local days the city states ("2026-11-04T23:00:00Z" to
"2026-11-06T22:59:59Z"), sometimes hours (Baden-Baden's night closure of the
Michaelstunnel from 22:00 to 04:00:59 local time); Rheinstetten, Ettlingen
and Stutensee write some ends a minute past midnight ("…T23:00:59Z"), kept as
written. Every shape of one works states the same words and period. Fetched
without a key on 5 November 2026 (12:33 UTC): 848 current and 472 coming
features, 1,246 of them in 502 works of the seven cities (318 current, 184
coming; no works in both layers) and 74 of Alsace.

REI keeps one record per works: its areas as drawn (the polygons; else the
lines; else the point; several become one multi-shape), with the period as
stated. A full closure and a closure in one direction are planned road
closures; a works "mit Verkehrsbehinderung" is road works. A works the city
states hinders no traffic ("keine Verkehrsbehinderung", 33 works) is not a
road event and is left out; 469 works are kept (220 closures, 249 road works:
288 in force, 180 coming, and one night closure that had ended that morning,
dropped by the run). The Alsace rows lie in France, are written in French,
carry no works number and no stated hindrance (27 of the 74 no end); they are
not Germany's and are left out (REI covers France through its own sources).
The feature ids and the per-shape `id` are the server's row numbers, not
content; a new `stand` alone is not a revision.

No field names a person: `verursacher` names a body or a kind of developer
("Privat" for a private one), and the notes of 5 November 2026 hold no names,
telephone numbers or e-mail addresses, so nothing is removed.

Licence: Creative Commons Namensnennung 4.0 International (CC BY 4.0), as the
dataset's MobiData BW page "Baustellen" states (mobidata-bw.de/dataset/
baustellen, organisation Stadt Karlsruhe, source mobil.trk.de, read 5 November
2026); mobil.trk.de has no robots.txt (docs/data-sources/
worldwide-sources-2026-11-05.md).
"""

import html
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
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

from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record
from .feed_text import sentences

SOURCE_ID = "de-trk-karlsruhe-roadworks"
ENDPOINT = "https://mobil.trk.de/geoserver/TBA/ows"
CURRENT, PREVIEW = "baustellen_aktuell", "baustellen_vorschau"
SOURCE_URL = "https://www.mobidata-bw.de/dataset/baustellen"
ATTRIBUTION = "Stadt Karlsruhe, Baustellen (mobil.trk.de, MobiData BW), CC BY 4.0"
BERLIN = ZoneInfo("Europe/Berlin")
# The Collectivité européenne d'Alsace: works in France (its name is written with ’).
FRANCE = "Collectivité européenne"
FULL_CLOSURE = "mit Vollsperrung"
ONE_WAY_CLOSURE = "mit Sperrung in eine Fahrtrichtung"
NO_HINDRANCE = "keine Verkehrsbehinderung"
LABELS = {FULL_CLOSURE: "Road closed", ONE_WAY_CLOSURE: "Road closed in one direction"}
# The server's row numbers: not content.
ROW_NUMBERS = frozenset({"id"})
# The date of the information: a new one alone is not a revision.
BOOKKEEPING = frozenset({"stand"})


def params_for(layer: str) -> dict[str, str]:
    return {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": f"TBA:{layer}",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }


def trk_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("germany")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="TechnologieRegion Karlsruhe roadworks",
        organization="Stadt Karlsruhe and the TechnologieRegion Karlsruhe cities (mobil.trk.de)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Baden-Württemberg (Karlsruhe region)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.0.0 GetFeature (GeoJSON, EPSG:4326), layers baustellen_aktuell and baustellen_vorschau; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="de",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value, EventType.ROAD_WORKS.value),
        parser_type="trk_karlsruhe_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no robots.txt; polled every three hours (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), as the MobiData BW dataset page states",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention="Each works' shapes as received, less the server's row numbers.",
        notes=(
            "Current and coming works of Karlsruhe, Bruchsal, Rheinstetten, Stutensee, Rastatt, "
            "Baden-Baden and Ettlingen, one record per works. Fetched without a key on 5 November 2026: "
            "502 works; 33 that hinder no traffic are left out, 469 kept (288 in force, 180 coming, "
            "1 ended). The Alsace rows (France) are left out."
        ),
    )


def _instant(value: Any) -> datetime | None:
    """'2026-11-04T23:00:00Z': an instant in UTC; one written without an offset is Karlsruhe time."""
    try:
        moment = datetime.fromisoformat(clean(value))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=BERLIN)


def _geometry(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The works area: its polygons, else its lines, else its first point."""
    shapes = [feature.get("geometry") for feature in features if isinstance(feature.get("geometry"), dict)]
    polygons = [s["coordinates"] for s in shapes if s.get("type") == "Polygon"]
    polygons += [part for s in shapes if s.get("type") == "MultiPolygon" for part in s["coordinates"]]
    if polygons:
        if len(polygons) == 1:
            return {"type": "Polygon", "coordinates": polygons[0]}
        return {"type": "MultiPolygon", "coordinates": polygons}
    lines = [s["coordinates"] for s in shapes if s.get("type") == "LineString"]
    lines += [part for s in shapes if s.get("type") == "MultiLineString" for part in s["coordinates"]]
    if lines:
        if len(lines) == 1:
            return {"type": "LineString", "coordinates": lines[0]}
        return {"type": "MultiLineString", "coordinates": lines}
    points = [s for s in shapes if s.get("type") == "Point"]
    return points[0] if points else None


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works as REI's record; None for Alsace and for works that hinder no traffic."""
    features = item.get("features") or []
    source, number = clean(item.get("datenquelle")), clean(item.get("vorgangsnummer"))
    if not features or not source or not number or source.startswith(FRANCE):
        return None
    properties = features[0].get("properties") or {}
    hindrance = clean(properties.get("sperrung"))
    if hindrance == NO_HINDRANCE:
        return None
    geometry = _geometry(features)
    if geometry is None:
        return None
    place = clean(html.unescape(clean(properties.get("lage"))))
    town = clean(properties.get("gemeinde")) or source.removeprefix("Stadt ")
    works = clean(properties.get("art"))
    site = clean(properties.get("tagesbaustelle"))
    closed = hindrance in (FULL_CLOSURE, ONE_WAY_CLOSURE)
    label = LABELS.get(hindrance, "Road works")
    structured = SourceEvent(
        event_type=EventType.PLANNED_ROAD_CLOSURE.value if closed else EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in (works, hindrance, site) if part) or None,
        start=_instant(properties.get("vorgangszeitraum_von")),
        end=_instant(properties.get("vorgangszeitraum_bis")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street section" if geometry["type"] in ("LineString", "MultiLineString") else "location",
                geometry=geometry,
                closure=hindrance or None,
            )
        ]
        if place
        else [],
        affected_road=place or None,
        attribution=f"{source}; {ATTRIBUTION}",
        covers_city=True,
    )
    causer = clean(properties.get("verursacher"))
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"{source}:{number}",
        url=SOURCE_URL,
        title=f"{label}: {place or town} ({town})",
        summary=sentences(
            works,
            hindrance,
            html_to_text(clean(properties.get("zusatzinfo"))),
            site,
            f"Works by: {causer}" if causer else "",
            f"Vorgang {number}, {source}",
        ),
        categories=[part for part in (works, hindrance, "coming" if PREVIEW in item.get("layers", ()) else "") if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_instant(properties.get("stand")),
    )


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """A shape as REI keeps it: geometry and properties, less the server's row numbers."""
    properties = feature.get("properties") or {}
    return {
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in ROW_NUMBERS},
    }


def works(features_by_layer: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The shapes grouped by works (city and works number), each works' shapes in a fixed order.

    A shape without a works number (the Alsace rows) belongs to no works and is not kept.
    """
    by_works: dict[tuple[str, str], dict[str, Any]] = {}
    for layer, features in features_by_layer.items():
        for feature in features:
            properties = feature.get("properties") or {}
            source, number = clean(properties.get("datenquelle")), clean(properties.get("vorgangsnummer"))
            if not source or not number:
                continue
            entry = by_works.setdefault(
                (source, number), {"datenquelle": source, "vorgangsnummer": number, "layers": [], "features": []}
            )
            if layer not in entry["layers"]:
                entry["layers"].append(layer)
            entry["features"].append(_kept(feature))
    for entry in by_works.values():
        entry["features"].sort(key=lambda shape: json.dumps(shape, sort_keys=True, ensure_ascii=False))
    return list(by_works.values())


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    layers: dict[str, list[dict[str, Any]]] = {}
    for layer in (CURRENT, PREVIEW):
        body = fetch_json(ENDPOINT, user_agent, client=client, params=params_for(layer))
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{ENDPOINT} ({layer}) did not return a GeoJSON feature collection")
        matched = body.get("numberMatched", body.get("totalFeatures"))
        if isinstance(matched, int) and matched > len(features):
            raise ConnectorError(f"{ENDPOINT} ({layer}) lists {matched} shapes, more than it returned")
        features = [feature for feature in features if isinstance(feature, dict)]
        for feature in features:
            # The region lies at about 7-9° E, 47-49.5° N: a first number above the second is a latitude.
            position = _first_position(feature.get("geometry"))
            if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
                raise ConnectorError(f"{ENDPOINT} ({layer}) returned coordinates in latitude-longitude order")
        layers[layer] = features
    return works(layers)


class TrkRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The works' content: the layer it is listed in and a new `stand` alone are not revisions."""
        item = raw.get("item", {})
        shapes = [
            {
                "geometry": shape.get("geometry"),
                "properties": {
                    key: value
                    for key, value in (shape.get("properties") or {}).items()
                    if key not in BOOKKEEPING | ROW_NUMBERS
                },
            }
            for shape in item.get("features", [])
        ]
        return content_key({**item, "features": shapes}, frozenset({"layers"}))
