"""Transports Québec road works on the provincial network (6 November 2026, decision 0062).

    GET https://ws.mapserver.transports.gouv.qc.ca/swtq?service=wfs&version=2.0.0
        &request=getfeature&typename=ms:chantiers_mtmdet&srsname=EPSG:4326
        &outputformat=geojson

The Ministère des Transports et de la Mobilité durable du Québec's road works
("Travaux routiers", the works Québec 511 shows), one WFS layer served as GeoJSON
in WGS 84: one line per segment of a works site, with the segment's id
(`identifiant`), the site's id (`identifiantChantier`), the route or motorway
number (`routeAutoroute`, empty for some), how heavy the obstruction is
(`entraveType`: "Majeure (semaine)", "Mineure (semaine et fin de semaine)" …),
the start and end (`debut`, `fin`, "2025/05/05 05:00:00", local time without an
offset), the kind of works, the obstruction in the ministry's words (`entrave`:
"Fermeture de 1 voie sur 2", "Circulation en alternance", "Route fermée entre …",
"Aucune fermeture de voie" …), the place (`localisation`), the direction and a
description in French and in English. Fetched without a key on 6 November 2026
(15:10 UTC): 361 segments of 265 works sites, every one with a line, a start and
an end; 255 in force, 97 coming and 9 ended (the run window drops those).

Times are read in Eastern time (America/Toronto, Québec's zone). What a segment
does to traffic is the strongest effect `entrave` states for road traffic, at any
hour ("ROUTE FERMÉE, entre 7 h et 12 h" is a closure; the hours stay in the text),
leaving out sections headed "Au besoin" (only if needed) or for pedestrians and
cyclists. In this order:

- "Aucune fermeture" (no closure) is road works;
- a road, street, bridge, tunnel, ramp, access, exit or service road named
  "fermé(e)", its "fermeture" ("Fermeture de l'accès à la sortie 314"), or
  "fermeture complète", is a planned road closure;
- a lane ("voie"), alternating traffic ("alternance") or contraflow
  ("contresens") is a lane restriction;
- anything else (shoulders, height limits …) is road works.

A direction is a compass direction only when one is stated ("Nord", "Est" …);
two ("Ouest et est", "Sud et nord") are both directions; "Dans une direction à
la fois" is kept in words only.

No personal data. Licence: "Attribution (CC-BY 4.0)", the Données Québec record
"travaux-routiers" (read 6 November 2026), whose own GeoJSON link is the request
above. robots.txt of ws.mapserver.transports.gouv.qc.ca (read from REI's server
on 6 November 2026): "User-agent: * / Allow: /", disallowing only named AI
crawlers. One request a run.
"""

import re
import unicodedata
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
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time
from .feed_text import sentences

SOURCE_ID = "quebec-mtmd-road-works"
ENDPOINT = "https://ws.mapserver.transports.gouv.qc.ca/swtq"
LAYER = "ms:chantiers_mtmdet"
PARAMS = {
    "service": "wfs",
    "version": "2.0.0",
    "request": "getfeature",
    "typename": LAYER,
    "srsname": "EPSG:4326",
    "outputformat": "geojson",
}
SOURCE_URL = "https://www.donneesquebec.ca/recherche/dataset/travaux-routiers"
ATTRIBUTION = (
    "Ministère des Transports et de la Mobilité durable du Québec, Travaux routiers, "
    "Données Québec. Licence CC BY 4.0."
)
EASTERN = ZoneInfo("America/Toronto")
FORMATS = ("%Y/%m/%d %H:%M:%S",)
_ROADS = (
    r"(?:routes?|rues?|chemins?|ponts?|tunnels?|bretelles?|acces|sorties?|entrees?|autoroutes?"
    r"|boulevards?|rangs?|voies? de service)"
)
_CLOSED = re.compile(
    rf"\b{_ROADS}\b[^.;\n]{{0,30}}?\bfermee?s?\b"
    rf"|\bfermeture (?:complete |totale )?(?:de la |du |de l'|des |d'){_ROADS}\b"
    r"|\bfermeture complete\b"
)
# A heading ending in ":" opens a section; these sections do not say what the works do
# to road traffic: only if needed ("Au besoin"), or for people on foot or bicycles.
_SET_ASIDE = re.compile(r"\bau besoin\b|\bpietons?\b|\bcyclistes?\b")
_LANES = re.compile(r"\bvoies?\b|\balternance\b|\bcontresens\b")
_COMPASS = {"nord": "NORTHBOUND", "sud": "SOUTHBOUND", "est": "EASTBOUND", "ouest": "WESTBOUND"}


def quebec_mtmd_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Transports Québec road works (provincial network)",
        organization="Ministère des Transports et de la Mobilité durable du Québec",
        authority_type="PROVINCIAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=country.country,
        region="Québec (province)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS layer ms:chantiers_mtmdet as GeoJSON (WGS 84); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="quebec_mtmd_chantiers",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0), per Données Québec",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=False,
        evidence_retention="Each works segment as the layer gives it and the structured event.",
        notes=(
            "Road works on Québec's provincial roads and motorways, one line per segment, in French "
            "with an English description. Fetched without a key on 6 November 2026: 361 segments of "
            "265 works sites (255 in force, 97 coming, 9 ended), every one with a start and an end. "
            "Times are local Eastern time."
        ),
    )


def _fold(text: str) -> str:
    """Lower case without accents, so "Fermée" and "fermee" read the same."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _for_traffic(entrave: str) -> str:
    """`entrave` without its sections for "Au besoin" or for pedestrians and cyclists."""
    kept, skipping = [], False
    for line in _fold(entrave).splitlines():
        heading = line.strip().rstrip()
        if heading.endswith(":") or re.match(r"^(?:au besoin|pietons|cyclistes)\b.*:", heading):
            skipping = bool(_SET_ASIDE.search(heading.split(":")[0]))
            if skipping:
                continue
        elif skipping:
            continue
        kept.append(line)
    return "\n".join(kept)


def event_type(entrave: str) -> str:
    """The strongest effect on road traffic the text states, at any hour (see the module text)."""
    text = _for_traffic(entrave)
    if "aucune fermeture" in text:
        return EventType.ROAD_WORKS.value
    if _CLOSED.search(text):
        return EventType.PLANNED_ROAD_CLOSURE.value
    if _LANES.search(text):
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def compass(direction: str) -> str | None:
    words = [w for w in re.split(r"[\s,]+", _fold(direction)) if w in _COMPASS]
    if len(words) == 1:
        return _COMPASS[words[0]]
    if len(words) >= 2:
        return "BOTH_DIRECTIONS"
    return None


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or not geometry.get("coordinates"):
        return None
    external_id = clean(properties.get("identifiant"))
    if not external_id:
        return None
    # Its lines and section headings ("Piétons et cyclistes :") matter for the type,
    # so the type is read from the text as written; `clean` would join the lines.
    written = properties.get("entrave") if isinstance(properties.get("entrave"), str) else ""
    first_line = next((clean(line) for line in written.splitlines() if clean(line)), "")
    place = clean(properties.get("localisation"))
    road = clean(properties.get("routeAutoroute"))
    direction = clean(properties.get("direction"))
    works = clean(properties.get("identificationDesTravaux"))
    weight = clean(properties.get("entraveType"))
    first, last = clean(properties.get("debut")), clean(properties.get("fin"))
    kind = event_type(written)
    structured = SourceEvent(
        event_type=kind,
        category=" / ".join(part for part in (works, weight) if part) or None,
        start=local_time(first, EASTERN, FORMATS),
        end=local_time(last, EASTERN, FORMATS),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="chantier",
                geometry=geometry,
                closure=first_line or None,
            )
        ]
        if place
        else [],
        affected_road=road or None,
        direction=compass(direction),
        attribution=ATTRIBUTION,
        stated_period=" – ".join((first or "?", last or "?")) if first or last else None,
        covers_city=True,
    )
    label = {
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
        EventType.LANE_RESTRICTION.value: "Lane restriction",
    }.get(kind, "Road works")
    where = ", ".join(part for part in (place, f"road {road}" if road else "") if part) or "Québec"
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {where}{f' ({direction})' if direction else ''} (Québec)",
        summary=sentences(clean(properties.get("descriptionAnglais")), weight) or None,
        categories=[part.lower() for part in (works, weight) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    return [feature for feature in features if isinstance(feature, dict)]


class QuebecMtmdRoadWorksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)
