"""Brest métropole: temporary traffic orders in force (5 November 2026).

    GET https://geo.brest-metropole.fr/arcgis/rest/services/public/GPB_DEP/MapServer/1718004/query
        ?where=1=1&outFields=*&outSR=4326&f=geojson

Brest métropole's "Arrêtés temporaires de circulation en cours" (data.gouv.fr
dataset 648095568d8509ead0ac4fe2; layer "ARRETES - Arrêtés Temporaires en cours
(Litteralis)"): the temporary traffic orders for works, each drawn as one or
more areas ("emprises") in WGS 84, polygons. An order (`ARRETESRCID`,
"26-AT-0036") has its works areas (`EMPR_TYPE` CIRCULATION or STATIONNEMENT)
and, when it closes a road, its detour (DEVIATION). Each area states where
(`LOCALISATIO`), the measures (`MESURES`, "BZH - Circulation alternée;BZH -
Interdiction de stationnement"), their detail (`PARAMMESUR`, "type
interdiction : interdiction totale"), the order's detail (`PARAMARR`: its
title, the works, the works period) and the order's first and last day
(`ARRETEDEB`, `ARRETEFIN`). Fetched without a key on 5 November 2026: 56 areas
of 45 orders, in one page (maxRecordCount 2,000); despite the layer's name, 43
orders had ended and 2 were in effect, none to come.

One order is one event, so REI keeps one record per order: the works areas
that state a traffic measure, together, as its geometry; the detour is named
in the summary, not drawn (it is where traffic is sent, not where the road is
closed). The event type is the measure's own detail: "type interdiction :
interdiction totale" closes the road (PLANNED_ROAD_CLOSURE); "voie réduite",
"sur une voie précise" or a "Circulation alternée" restrict it
(LANE_RESTRICTION); a traffic measure whose extent is not stated is road works
(ROAD_WORKS). The order's title ("Route barrée", "Alternat", "Chaussée
rétrécie") is kept as text and not read for the type: four orders titled
"Route barrée" state a reduced lane. Left out: an order whose works areas ban
only parking ("Interdiction de stationnement") or close only a footpath
("Cheminement piétonnier interdit"), which is no road event (4 of the 45, one
of the two in effect on 5 November); an area marked `INTERNET` "false", which
the publisher does not put on the web (2, both without a shape); an order with
no drawn works area.

The layer cuts `LOCALISATIO` and `MESURES` at 100 characters and `PARAMMESUR`
at 1,000; a cut measure name ("BZH - Circulat") is not read, the full names in
`PARAMMESUR` are. `ARRETEDEB`/`ARRETEFIN` are milliseconds at the UTC midnight
of the day `PARAMARR` states ("Date de début de l'arrêté : 26/10/2026"): days,
so an order runs from the start of its first day to the end of its last, Paris
time.

Personal data: `EMETTEUR` is the applicant, a company or a private person
(one of the 45 on 5 November was "M." and a name) and `EMETT_ID` its id: both
dropped. `PARAMMESUR` names the firm allowed to park in the works area
("entreprise autorisée : ..."): that part is dropped. `CREATED_USER` and
`LAST_EDITED_USER` are accounts; `OBJECTID`, `CREATED_DATE` and
`LAST_EDITED_DATE` are the layer's load (all 56 loaded at 21:14 UTC on 3
November): not kept, so a reload is no revision.

Licence: Licence Ouverte 2.0 ("lov2", Brest métropole's data.gouv.fr record of
the dataset, https://www.data.gouv.fr/datasets/arretes-temporaires-de-circulation-en-cours,
read 5 November 2026). The map server has no robots.txt.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timezone
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
from .feed_text import sentences

SOURCE_ID = "fr-brest-traffic-orders"
LAYER = "https://geo.brest-metropole.fr/arcgis/rest/services/public/GPB_DEP/MapServer/1718004"
PARAMS = {"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson"}
SOURCE_URL = "https://www.data.gouv.fr/datasets/arretes-temporaires-de-circulation-en-cours"
ATTRIBUTION = "Source : Brest métropole, Arrêtés temporaires de circulation en cours (data.gouv.fr). Licence Ouverte 2.0."
PARIS = ZoneInfo("Europe/Paris")
# The applicant (a company or a private person) and its id.
PERSONAL = frozenset({"EMETTEUR", "EMETT_ID"})
# Accounts and the layer's load: not content.
BOOKKEEPING = frozenset({"CREATED_USER", "LAST_EDITED_USER", "OBJECTID", "CREATED_DATE", "LAST_EDITED_DATE"})
# The firm allowed to park in the works area, inside PARAMMESUR.
COMPANY_KEY = "entreprise autorisée"
DETOUR = "DEVIATION"
# Measures that do not restrict traffic on the road.
NOT_TRAFFIC = ("Interdiction de stationnement", "Cheminement piétonnier interdit", "Déviation")
KNOWN = (*NOT_TRAFFIC, "Circulation interdite totale ou partielle", "Circulation alternée")
CLOSED = "interdiction totale"
NARROWED = ("voie réduite", "sur une voie précise")
ALTERNATING = "Circulation alternée"


def brest_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("france")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Brest métropole temporary traffic orders in force (arrêtés temporaires)",
        organization="Brest métropole",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Bretagne (Brest métropole)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS map service (GPB_DEP MapServer layer 1718004, Litteralis), GeoJSON in WGS 84; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="brest_traffic_orders",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no robots.txt; one request a run.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Licence Ouverte 2.0 (lov2), Brest métropole's data.gouv.fr record ({SOURCE_URL})",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each order's areas as the service returns them, less the applicant, the firm allowed to park, "
            "the accounts and the layer's load fields, and the structured event."
        ),
        notes=(
            "Brest métropole's temporary traffic orders for works, each with its works areas and detour as "
            "polygons. Fetched without a key on 5 November 2026: 56 areas of 45 orders; 2 in effect (one bans "
            "parking only and is left out), the rest ended. Days are Paris days; one record per order."
        ),
    )


# --- reading an order -----------------------------------------------------------------


def _day(value: Any) -> date | None:
    """Milliseconds at the UTC midnight of the stated day."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
    return None


def _measure_name(text: str) -> str:
    """'BZH - Circulation interdite totale ou partielle 3' as 'Circulation interdite totale ou partielle'."""
    name = re.sub(r"^BZH\s*-\s*", "", clean(text))
    return re.sub(r"\s+\d+$", "", name)


def _details(properties: dict[str, Any]) -> list[tuple[str, str, str]]:
    """PARAMMESUR as (measure, key, value): 'BZH - X | type interdiction : interdiction totale'."""
    found = []
    for part in str(properties.get("PARAMMESUR") or "").split(" ; "):
        measure, _, rest = part.partition(" | ")
        key, _, value = rest.partition(" : ")
        if clean(measure) and clean(key):
            found.append((_measure_name(measure), clean(key), clean(value)))
    return found


def measures(properties: dict[str, Any]) -> list[str]:
    """The area's measures by their full names; a name the layer cut short is not read."""
    names = [_measure_name(part) for part in str(properties.get("MESURES") or "").split(";")]
    names += [measure for measure, _, _ in _details(properties)]
    whole = [
        name
        for name in names
        if name and (name in KNOWN or not any(known.startswith(name) for known in KNOWN))
    ]
    return list(dict.fromkeys(whole))


def restricts_traffic(properties: dict[str, Any]) -> bool:
    return any(name not in NOT_TRAFFIC for name in measures(properties))


def _order_detail(properties: dict[str, Any], key: str) -> str:
    """One entry of PARAMARR: 'titre : Route barrée ; ...'."""
    for part in str(properties.get("PARAMARR") or "").split(" ; "):
        name, _, value = part.partition(" : ")
        if clean(name) == key:
            return clean(value)
    return ""


def _kind(areas: list[dict[str, Any]]) -> tuple[str, str]:
    """(REI's event type, the measure in the order's words) from the areas' measures."""
    names = [name for area in areas for name in measures(area)]
    types = [value for area in areas for _, key, value in _details(area) if key == "type interdiction"]
    if CLOSED in types:
        return EventType.PLANNED_ROAD_CLOSURE.value, f"Circulation interdite ({CLOSED})"
    narrowed = next((value for value in types if value in NARROWED), None)
    if narrowed:
        return EventType.LANE_RESTRICTION.value, f"Circulation interdite ({narrowed})"
    if ALTERNATING in names:
        return EventType.LANE_RESTRICTION.value, ALTERNATING
    stated = next((name for name in names if name not in NOT_TRAFFIC), "")
    return EventType.ROAD_WORKS.value, stated


def _combined(geometries: list[dict[str, Any]]) -> dict[str, Any] | None:
    polygons = [g["coordinates"] for g in geometries if g.get("type") == "Polygon"]
    polygons += [part for g in geometries if g.get("type") == "MultiPolygon" for part in g["coordinates"]]
    if not polygons:
        return None
    return {"type": "Polygon", "coordinates": polygons[0]} if len(polygons) == 1 else {"type": "MultiPolygon", "coordinates": polygons}


def _places(text: Any) -> list[str]:
    return [place for place in (clean(part) for part in str(text or "").split(";")) if place]


def to_record(order: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One traffic order as REI's record; None when it restricts no traffic or has no drawn works area."""
    number = clean(order.get("ARRETESRCID"))
    shapes = [shape for shape in order.get("features") or [] if isinstance(shape, dict)]
    public = [s for s in shapes if clean((s.get("properties") or {}).get("INTERNET")).lower() != "false"]
    works = [s for s in public if clean(s["properties"].get("EMPR_TYPE")).upper() != DETOUR]
    detours = [s for s in public if clean(s["properties"].get("EMPR_TYPE")).upper() == DETOUR]
    drawn = [s for s in works if restricts_traffic(s["properties"]) and isinstance(s.get("geometry"), dict)]
    geometry = _combined([s["geometry"] for s in drawn])
    if not number or geometry is None:
        return None
    areas = [s["properties"] for s in drawn]
    event_type, measure = _kind(areas)
    first = min((day for a in areas if (day := _day(a.get("ARRETEDEB")))), default=None)
    last = max((day for a in areas if (day := _day(a.get("ARRETEFIN")))), default=None)
    start, end = whole_days(first, last, PARIS)
    lead = areas[0]
    places = list(dict.fromkeys(place for a in areas for place in _places(a.get("LOCALISATIO"))))
    detour_places = list(dict.fromkeys(place for s in detours for place in _places(s["properties"].get("LOCALISATIO"))))
    title_words = _order_detail(lead, "titre")
    works_words = _order_detail(lead, "Description des travaux")
    period = _order_detail(lead, "Période des travaux")
    category = clean(lead.get("CATEGMODEL"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in ("Arrêté temporaire", category, measure) if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=" ; ".join(_places(area["properties"].get("LOCALISATIO"))),
                kind="work area",
                geometry=area["geometry"],
                closure=" ; ".join(measures(area["properties"])) or None,
            )
            for area in drawn
            if _places(area["properties"].get("LOCALISATIO"))
        ],
        affected_road=places[0] if places else None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=number,
        url=SOURCE_URL,
        title=f"{measure or 'Arrêté temporaire'}: {places[0] if places else 'arrêté ' + number} (Brest métropole)",
        summary=sentences(
            f"Arrêté temporaire {number}" + (f" ({title_words})" if title_words else ""),
            f"Travaux {works_words}" if works_words else "",
            f"Mesures : {' ; '.join(dict.fromkeys(n for a in areas for n in measures(a)))}",
            f"Localisation : {' ; '.join(places)}" if places else "",
            f"Déviation : {' ; '.join(detour_places)}" if detour_places else "",
            f"Période des travaux : {period}" if period else "",
        ),
        categories=[part.lower() for part in ("arrêté temporaire", category, measure) if part],
        item=order,
        structured=structured,
        retrieved_at=retrieved_at,
    )


# --- fetching -------------------------------------------------------------------------


def _without_company(text: Any) -> Any:
    """PARAMMESUR less the firm allowed to park ('... | entreprise autorisée : <name>')."""
    if not isinstance(text, str):
        return text
    parts = text.split(" ; ")
    return " ; ".join(part for part in parts if clean(part.partition(" | ")[2].partition(" : ")[0]) != COMPANY_KEY)


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """An area as REI keeps it: no applicant, no firm, no accounts or load fields."""
    properties = feature.get("properties") or {}
    kept = {key: value for key, value in properties.items() if key not in PERSONAL | BOOKKEEPING}
    if "PARAMMESUR" in kept:
        kept["PARAMMESUR"] = _without_company(kept["PARAMMESUR"])
    return {"type": feature.get("type"), "geometry": feature.get("geometry"), "properties": kept}


def orders(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The areas grouped by order, each order's areas in their own order (EMPRISENO)."""
    by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        number = clean((feature.get("properties") or {}).get("ARRETESRCID"))
        if number:
            by_order[number].append(_kept(feature))
    return [
        {
            "ARRETESRCID": number,
            "features": sorted(
                areas,
                key=lambda area: (
                    area["properties"].get("EMPRISENO") or 0,
                    area["properties"].get("IDEMPRISE") or 0,
                ),
            ),
        }
        for number, areas in by_order.items()
    ]


def fetch_orders(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(f"{LAYER}/query", user_agent, client=client, params=PARAMS)
    if not isinstance(body, dict) or "error" in body:
        detail = body.get("error") if isinstance(body, dict) else body
        raise ConnectorError(f"{LAYER} answered with an error: {str(detail)[:200]}")
    features = body.get("features")
    if not isinstance(features, list):
        raise ConnectorError(f"{LAYER} did not return a GeoJSON feature list")
    if body.get("exceededTransferLimit") or (body.get("properties") or {}).get("exceededTransferLimit"):
        raise ConnectorError(f"{LAYER} lists more areas than one page holds; the list is cut")
    # The layer lists the orders of the year, ended or not; the run window drops the ended.
    return orders([feature for feature in features if isinstance(feature, dict)])


class BrestTrafficOrdersConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_orders)
    to_record = staticmethod(to_record)
