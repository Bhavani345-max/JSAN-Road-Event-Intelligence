"""Département des Côtes d'Armor: works on departmental roads, traffic orders (5 November 2026).

    GET https://datarmor.cotesdarmor.fr/data-fair/api/v1/datasets/cd22arreteschantiers/lines
        ?size=1000&sort=-DATEFIN&format=geojson

The Département's "Travaux sur les routes départementales des Côtes d'Armor
(Arrêtés de circulation)": "Arrêtés de circulation générant une contrainte de
circulation pour l'usager avec nature du chantier, périodes d'exécution et
mesures d'exploitation associées" (the dataset's description; Data Fair
portal datarmor.cotesdarmor.fr, updated daily around 03:00 UTC). One line per
traffic order, each with its road section as a line in WGS 84 (`_geoshape`,
served as the feature's geometry; the native GEOMETRY is Lambert-93 and is not
asked for). On 5 November 2026 the dataset held 5,979 lines since February
2025 (5,555 dossiers), keyless.

Paging: Data Fair answers `size` lines a page and gives the next page only in
the `Link` header (rel="next"; the GeoJSON body has no `next`). Sorted by
`-DATEFIN`, the orders still running or to come are first: REI reads pages
until a page ends with an order that ended before today (Paris), and keeps
the lines not yet ended. On 5 November 2026 the first page held all of them:
168 orders, 115 in effect and 53 starting later, every one with its line (5
older orders on the page had none). A line without DATEFIN would sort last
and is read only if the pages before it are all still running.

Fields read: `NUMDOSSIER` (the order, "2026T3115"), `ROUTE` ("D52"), the
section's start and end as road reference points (`PRDEBUT`+`ABSCISSEDEBUT`
to `PRFIN`+`ABSCISSEFIN`, written "PR 14+2930"), `COMMUNE`, `TRAVAUX` (the
works, "Travaux sur le réseau d'électricité"), `CIRCULATION` (the traffic
measure), `JOURSETHORAIRES1`/`2` (days and hours, the order's own words, kept
as text) and `DATEDEBUT`/`DATEFIN` ("2026-11-03 00:00:00.0", local, no zone).
Every date on 5 November was a midnight: a day, so an order runs from the
start of its first day to the end of its last, Paris time; a value with
another time would be read as that local moment.

Event types, from `CIRCULATION`: "INTERDICTION" (26 of the 168) or
"Circulation interdite" (2) close the road (PLANNED_ROAD_CLOSURE); a
"Circulation alternée" (128, most with a speed limit) is a LANE_RESTRICTION;
a speed limit or a vehicle-category limit alone (12) is ROAD_WORKS. Every
order restricts traffic, by the dataset's description; none is left out.

A dossier may be listed more than once: 5,979 lines hold 5,555 dossiers, and
those looked at were the same line pushed again on a later day (identical but
for Data Fair's own line id and update time). One order is one event: REI
keeps the most recently updated line of each dossier. Data Fair's line id,
line number, random number and update time (`_id`, `_i`, `_rand`,
`_updatedAt`) are bookkeeping, not content, and are not kept as evidence, so
a line pushed again is no revision; the update time is the record's
publication time. A GeometryCollection (9 on the first page; a section and a
point beside it) is kept as its lines, or else its polygons, or else its
first point: REI stores no collections. No field names a person.

Licence: "Licence Ouverte / Open Licence"
(https://www.etalab.gouv.fr/licence-ouverte-open-licence; the dataset's
licence on datarmor.cotesdarmor.fr, read 5 November 2026); the Département's
data.gouv.fr record of the dataset states Licence Ouverte 2.0 (lov2). robots.txt
allows everything.
"""

from collections.abc import Iterable
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError, refusal_detail
from packages.cities import get_city
from packages.common.time import utc_now
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

from .common import MAX_RESPONSE_BYTES, get_with_retry
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .feed_text import sentences

SOURCE_ID = "fr-cotes-darmor-works-orders"
ENDPOINT = "https://datarmor.cotesdarmor.fr/data-fair/api/v1/datasets/cd22arreteschantiers/lines"
PARAMS = {"size": "1000", "sort": "-DATEFIN", "format": "geojson"}
SOURCE_URL = "https://datarmor.cotesdarmor.fr/datasets/cd22arreteschantiers"
LICENCE_URL = "https://www.etalab.gouv.fr/licence-ouverte-open-licence"
ATTRIBUTION = (
    "Source : Département des Côtes d'Armor, Travaux sur les routes départementales des Côtes d'Armor "
    "(Arrêtés de circulation), datarmor.cotesdarmor.fr. Licence Ouverte / Open Licence."
)
PARIS = ZoneInfo("Europe/Paris")
AREA = "Côtes-d'Armor"
# Data Fair's own line id, line number, random number and update time: not content.
BOOKKEEPING = frozenset({"_id", "_i", "_rand", "_updatedAt"})
# A dataset larger than this many pages of running orders is not what REI expects; stop.
MAX_PAGES = 10
STORED_SHAPES = ("Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon")


def cotes_darmor_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("france")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Côtes d'Armor works on departmental roads (traffic orders)",
        organization="Département des Côtes d'Armor",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Bretagne (Côtes-d'Armor)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method=(
            "Data Fair lines API (dataset cd22arreteschantiers), GeoJSON in WGS 84, latest end first, "
            "1,000 a page, next page from the Link header; no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="cotes_darmor_works_orders",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt allows everything; one request a run (1,000 orders a page).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            f"Licence Ouverte / Open Licence ({LICENCE_URL}), the dataset's licence on datarmor.cotesdarmor.fr; "
            "Licence Ouverte 2.0 on its data.gouv.fr record"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention=(
            "Each order's line as the API returns it, less Data Fair's line id, line number, random number "
            "and update time, and the structured event."
        ),
        notes=(
            "The Département's traffic orders for works on its roads, one road section each, updated daily. "
            "Fetched without a key on 5 November 2026: 5,979 orders listed since February 2025; the first "
            "page (latest end first) held the 168 not yet ended, 115 in effect and 53 starting later "
            "(28 road closures, 128 alternating traffic, 12 speed or vehicle limits). Days are Paris days; "
            "a dossier listed twice is kept once."
        ),
    )


# --- reading a line -------------------------------------------------------------------


def _moment(value: Any) -> tuple[date | None, datetime | None]:
    """'2026-11-03 00:00:00.0': (the day, None) at midnight; (None, the local moment) otherwise."""
    text = clean(value)
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            stated = datetime.strptime(text, pattern)
        except ValueError:
            continue
        if stated.time() == time.min:
            return stated.date(), None
        return None, stated.replace(tzinfo=PARIS)
    return None, None


def _period(properties: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    first, start_at = _moment(properties.get("DATEDEBUT"))
    last, end_at = _moment(properties.get("DATEFIN"))
    start, _ = whole_days(first, None, PARIS)
    _, end = whole_days(None, last, PARIS)
    return start or start_at, end or end_at


def last_day(properties: dict[str, Any]) -> date | None:
    """The order's last day (Paris), or None when DATEFIN is not stated."""
    last, end_at = _moment(properties.get("DATEFIN"))
    return last or (end_at.date() if end_at else None)


def _number(value: Any) -> str:
    """A stated number as text; 0 is a number ('PR 7+0'), None or blank is not stated."""
    if isinstance(value, bool) or value is None:
        return ""
    return str(value) if isinstance(value, int) else clean(value)


def _reference(point: Any, offset: Any) -> str:
    """'PR 14+2930': the reference point and the distance past it, as the order states them."""
    point, offset = _number(point), _number(offset)
    if not point:
        return ""
    return f"PR {point}+{offset}" if offset else f"PR {point}"


def section(properties: dict[str, Any]) -> str:
    """'D52, PR 14+2930 à PR 15+340': the road and its section, in the order's own references."""
    road = clean(properties.get("ROUTE"))
    start = _reference(properties.get("PRDEBUT"), properties.get("ABSCISSEDEBUT"))
    end = _reference(properties.get("PRFIN"), properties.get("ABSCISSEFIN"))
    stretch = " à ".join(part for part in (start, end) if part) if start != end else start
    return ", ".join(part for part in (road, stretch) if part)


def event_type(measure: str) -> str:
    """'INTERDICTION', 'Circulation interdite': closed; alternating traffic: restricted; else works."""
    words = measure.lower()
    if words.startswith("interdiction") or words.startswith("circulation interdite"):
        return EventType.PLANNED_ROAD_CLOSURE.value
    if "alternée" in words:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def stored_geometry(value: Any) -> dict[str, Any] | None:
    """The line as REI stores it: a collection becomes its lines, else its polygons, else its first point."""
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    if kind in STORED_SHAPES:
        return value if value.get("coordinates") else None
    if kind != "GeometryCollection":
        return None
    parts = [part for part in value.get("geometries") or [] if isinstance(part, dict) and part.get("coordinates")]
    lines = [p["coordinates"] for p in parts if p.get("type") == "LineString"]
    lines += [line for p in parts if p.get("type") == "MultiLineString" for line in p["coordinates"]]
    if lines:
        return {"type": "LineString", "coordinates": lines[0]} if len(lines) == 1 else {"type": "MultiLineString", "coordinates": lines}
    polygons = [p["coordinates"] for p in parts if p.get("type") == "Polygon"]
    polygons += [polygon for p in parts if p.get("type") == "MultiPolygon" for polygon in p["coordinates"]]
    if polygons:
        return {"type": "Polygon", "coordinates": polygons[0]} if len(polygons) == 1 else {"type": "MultiPolygon", "coordinates": polygons}
    points = [p for p in parts if p.get("type") == "Point"]
    return points[0] if points else None


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """The line as REI keeps it: its geometry and fields, less Data Fair's bookkeeping."""
    properties = feature.get("properties") or {}
    return {
        "type": feature.get("type"),
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in BOOKKEEPING},
    }


def _updated(properties: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromisoformat(clean(properties.get("_updatedAt")).replace("Z", "+00:00"))
    except ValueError:
        return None


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One traffic order as REI's record; None without a dossier number or a line."""
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    number = clean(properties.get("NUMDOSSIER"))
    geometry = stored_geometry(feature.get("geometry"))
    if not number or geometry is None:
        return None
    measure = clean(properties.get("CIRCULATION"))
    works = clean(properties.get("TRAVAUX"))
    commune = clean(properties.get("COMMUNE"))
    road = clean(properties.get("ROUTE"))
    place = section(properties)
    hours = list(dict.fromkeys(text for key in ("JOURSETHORAIRES1", "JOURSETHORAIRES2") if (text := clean(properties.get(key)))))
    start, end = _period(properties)
    first, last = clean(properties.get("DATEDEBUT"))[:10], clean(properties.get("DATEFIN"))[:10]
    stated = f"{first} – {last}" if first or last else ""
    structured = SourceEvent(
        event_type=event_type(measure),
        category=" / ".join(part for part in ("Arrêté de circulation", works, measure) if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (place, commune) if part),
                kind="road section",
                geometry=geometry,
                closure=measure or None,
            )
        ]
        if place or commune
        else [],
        affected_road=road or None,
        attribution=ATTRIBUTION,
        stated_period="; ".join(part for part in (stated, *hours) if part) or None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=number,
        url=SOURCE_URL,
        # Without a measure, the dataset's own word for what it lists.
        title=f"{measure or 'Travaux'}: {place or 'arrêté ' + number} ({commune or AREA})",
        summary=sentences(
            works,
            f"Circulation : {measure}" if measure else "",
            f"Jours et horaires : {' ; '.join(hours)}" if hours else "",
            f"Arrêté de circulation {number}",
        ),
        categories=[part.lower() for part in (works, measure) if part],
        item=_kept(feature),
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_updated(properties),
    )


# --- fetching -------------------------------------------------------------------------


def _page(
    url: str, user_agent: str, *, client: httpx.Client | None, params: dict[str, str] | None
) -> tuple[list[dict[str, Any]], str | None]:
    """One page of lines and the next page's address (the Link header), if any."""
    try:
        response = get_with_retry(
            url,
            client=client,
            params=params,
            headers={"User-Agent": user_agent, "Accept": "application/geo+json, application/json"},
            timeout=60,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not fetch {url}: {error}") from error
    if response.status_code in (429, 503):
        raise ConnectorError(
            f"{url} refused the request (HTTP {response.status_code}): rate limited; retried at the next run"
        )
    if response.status_code != 200:
        raise ConnectorError(f"Could not fetch {url}: HTTP {response.status_code}" + refusal_detail(response))
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
    try:
        body = response.json()
    except ValueError as error:
        raise ConnectorError(f"{url} did not return JSON: {error}") from error
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{url} did not return a GeoJSON feature collection")
    next_url = response.links.get("next", {}).get("url")
    return [feature for feature in features if isinstance(feature, dict)], next_url


def orders(lines: Iterable[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    """The lines not yet ended, one per dossier: the most recently updated line of each."""
    latest: dict[str, tuple[tuple[str, str], dict[str, Any]]] = {}
    for line in lines:
        properties = line.get("properties") or {}
        number = clean(properties.get("NUMDOSSIER"))
        ends = last_day(properties)
        if not number or (ends is not None and ends < today):
            continue
        key = (clean(properties.get("_updatedAt")), clean(properties.get("_id")))
        if number not in latest or key > latest[number][0]:
            latest[number] = (key, line)
    return [line for _, line in latest.values()]


def fetch_orders(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    today = (now or utc_now()).astimezone(PARIS).date()
    lines: list[dict[str, Any]] = []
    url, params = ENDPOINT, dict(PARAMS)
    for _ in range(MAX_PAGES):
        batch, next_url = _page(url, user_agent, client=client, params=params)
        lines.extend(batch)
        # Latest end first: once a page ends with an order already ended, so have all after it.
        ends = last_day(batch[-1].get("properties") or {}) if batch else None
        if not batch or not next_url or (ends is not None and ends < today):
            return orders(lines, today)
        url, params = next_url, None
    raise ConnectorError(f"{ENDPOINT} lists more than {MAX_PAGES} pages of orders not yet ended")


class CotesDarmorWorksOrdersConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_orders)
    to_record = staticmethod(to_record)
