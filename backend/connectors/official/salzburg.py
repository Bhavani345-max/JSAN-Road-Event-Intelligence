"""Stadt Salzburg roadworks, Austria (5 November 2026).

    GET https://data.stadt-salzburg.at/geodaten/wfs?service=WFS&version=1.1.0&request=GetFeature
        &srsName=EPSG:4326&outputFormat=application/json&typeName=ogdsbg:baustelle

The City of Salzburg's works sites, active and planned, one WFS layer served as
GeoJSON in WGS 84 (lines, a few points). Each states its works number
(`NUMMER`) and file number (`AKTENZAHL`), its status (`STATUS`: "Baustelle
aktiv", "Baustelle geplant"), what is dug or laid (`GRABUNGSART`: "01 - Strom",
"07 - Kanal" …), the measure (`MASSNAHME`), sometimes where (`LAGE`,
`BAUBEREICH`) and what it does to traffic in the city's words (`BEHINDERUNG`),
a comment (who carries it out, or "wurde bis aufweiteres zurückgestellt"), the
office in charge and, when stated, a first and a last day (`BEGINN`, `ENDE`,
written dd.mm.yyyy). Fetched without a key on 5 November 2026: 204 features of
203 works (one works is drawn as a line and a marker point); 90 active, 114
planned. Of the active, 80 state both days, 7 a first day only (6 of them from
2008) and 3 neither; 111 planned works state no day, 3 state both.

REI keeps one record per works number: its lines as drawn (several become one
multi-line), else its first point. Every record is road works; the city's
hindrance words are free text (11 works state any), kept as stated in the
summary and on the location, and REI does not read a closure out of them. A
period stated in days runs from the start of the first to the end of the last,
Salzburg time. A works that states no day keeps no time: REI never supplies
one (as for Kitchener's closures without a start or an end); such a record is
stored and shown as unconfirmed. On 5 November 2026 one planned works had
ended (4 September 2026) and is dropped by the run; 202 are kept (86 in force,
2 coming, 114 without a stated period). Many works name no street: their
title then says what is done, not where, and their place is their geometry.

The case officer and their telephone number (`SACHBEARBEITER`,
`SACHBEARBEITER_TELEFON`, empty on 5 November 2026) are not kept. The
feature ids repeat `ID`, which is not content.

Licence: CC BY 3.0 AT, credit "Datenquelle: Stadt Salzburg –
data.stadt-salzburg.at", as the service's own capabilities state
(AccessConstraints: "Datenquelle: Stadt Salzburg – data.stadt-salzburg.at;
Nutzungsbedingungen: CC BY 3.0 AT", read 5 November 2026; the data.gv.at entry
names the same licence, docs/data-sources/worldwide-sources-2026-11-05.md).
"""

import json
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
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from .common import content_key, fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .feed_text import sentences

SOURCE_ID = "at-salzburg-roadworks"
ENDPOINT = "https://data.stadt-salzburg.at/geodaten/wfs"
LAYER = "ogdsbg:baustelle"
PARAMS = {
    "service": "WFS",
    "version": "1.1.0",
    "request": "GetFeature",
    "srsName": "EPSG:4326",
    "outputFormat": "application/json",
    "typeName": LAYER,
}
SOURCE_URL = "https://data.stadt-salzburg.at"
ATTRIBUTION = "Datenquelle: Stadt Salzburg – data.stadt-salzburg.at (CC BY 3.0 AT)"
SALZBURG = ZoneInfo("Europe/Vienna")
# The case officer and their telephone number: personal data, not kept.
PERSONAL_FIELDS = frozenset({"SACHBEARBEITER", "SACHBEARBEITER_TELEFON"})
# The shape's own number (the feature id repeats it): not content.
SHAPE_IDS = frozenset({"ID"})


def salzburg_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("austria")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Stadt Salzburg roadworks",
        organization="Stadtgemeinde Salzburg",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Salzburg",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.1.0 GetFeature (GeoJSON, EPSG:4326), layer ogdsbg:baustelle; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="salzburg_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled every three hours (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 3.0 AT (https://creativecommons.org/licenses/by/3.0/at/deed.de)",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention="Each works' shapes as received, less the case officer and their telephone number.",
        notes=(
            "The City of Salzburg's active and planned works sites, mostly lines. Fetched without a key "
            "on 5 November 2026: 204 shapes of 203 works; 114 planned works state no day and are kept "
            "without times; one ended works is dropped."
        ),
    )


def _day(value: Any):
    """A day written dd.mm.yyyy ('08.12.2026')."""
    try:
        return datetime.strptime(clean(value), "%d.%m.%Y").date()
    except ValueError:
        return None


def _geometry(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The works as drawn: its lines, else its first point (a one-point MultiPoint is that point)."""
    shapes = [feature.get("geometry") for feature in features if isinstance(feature.get("geometry"), dict)]
    lines = [s["coordinates"] for s in shapes if s.get("type") == "LineString"]
    lines += [part for s in shapes if s.get("type") == "MultiLineString" for part in s["coordinates"]]
    if lines:
        if len(lines) == 1:
            return {"type": "LineString", "coordinates": lines[0]}
        return {"type": "MultiLineString", "coordinates": lines}
    points = [s["coordinates"] for s in shapes if s.get("type") == "Point"]
    points += [part for s in shapes if s.get("type") == "MultiPoint" for part in s["coordinates"]]
    return {"type": "Point", "coordinates": points[0]} if points else None


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works as REI's record."""
    features = item.get("features") or []
    number = clean(item.get("nummer"))
    if not features or not number:
        return None
    geometry = _geometry(features)
    if geometry is None:
        return None
    properties = features[0].get("properties") or {}
    place = clean(properties.get("LAGE")) or clean(properties.get("BAUBEREICH"))
    measure = clean(properties.get("MASSNAHME"))
    dug = clean(properties.get("GRABUNGSART"))
    status = clean(properties.get("STATUS"))
    hindrance = clean(properties.get("BEHINDERUNG"))
    first, last = clean(properties.get("BEGINN")), clean(properties.get("ENDE"))
    start, end = whole_days(_day(first), _day(last), SALZBURG)
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=dug or None,
        status=status or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street section" if geometry["type"] != "Point" else "location",
                geometry=geometry,
                closure=hindrance or None,
            )
        ]
        if place
        else [],
        affected_road=place or None,
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}" if first or last else None,
        covers_city=True,
    )
    file_number = clean(properties.get("AKTENZAHL"))
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"works:{number}",
        url=SOURCE_URL,
        title=f"Road works: {place or measure or dug or 'Salzburg'} (Salzburg)",
        summary=sentences(
            measure,
            f"Traffic: {hindrance}" if hindrance else "",
            clean(properties.get("BAUSTELLENEINRICHTUNG")),
            clean(properties.get("AKT_KOMMENTAR")),
            status,
            f"Aktenzahl {file_number}" if file_number else "",
        ),
        categories=[part for part in (dug, status) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """A shape as REI keeps it: geometry and properties, less the case officer."""
    properties = feature.get("properties") or {}
    return {
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in PERSONAL_FIELDS},
    }


def works(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The shapes grouped by works number, each works' shapes in a fixed order."""
    by_number: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        number = clean((feature.get("properties") or {}).get("NUMMER"))
        if number:
            by_number[number].append(_kept(feature))
    return [
        {
            "nummer": number,
            "features": sorted(shapes, key=lambda shape: json.dumps(shape, sort_keys=True, ensure_ascii=False)),
        }
        for number, shapes in by_number.items()
    ]


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
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} shapes, more than it returned")
    features = [feature for feature in features if isinstance(feature, dict)]
    for feature in features:
        # Salzburg lies at about 13° E, 47.8° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
    return works(features)


class SalzburgRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The works' content: the shapes' own numbers are not content."""
        item = raw.get("item", {})
        shapes = [
            {
                "geometry": shape.get("geometry"),
                "properties": {
                    key: value for key, value in (shape.get("properties") or {}).items() if key not in SHAPE_IDS
                },
            }
            for shape in item.get("features", [])
        ]
        return content_key({**item, "features": shapes}, frozenset())
