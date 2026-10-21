"""Barcelona works in public space ("obres"), Spain (decision 0034).

    GET https://opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search
        ?resource_id=4e6b3bfe-2f47-4d35-aa7d-3e4bcc930cea&limit=1000&offset=0&sort=_id&fields=...

Barcelona City Council's works in the city's public space ("Barcelona city's
road works in public space", source system GIAT), read from the open-data
portal's CKAN datastore in pages of 1,000 rows. Each work states its code
(`codi`), type (`tipusobra`), status (`estat`: En execució, Aturada,
Finalitzada), location words (`ubicacio`), district and neighbourhood, title
and description in Catalan, its first and last day (`data_inici`, `data_fi`:
dates without a time) and its site as a WGS 84 WKT polygon or multipolygon
(`geometria_wgs84`; an ETRS89 copy is not requested). A work spanning several
neighbourhoods is listed once per neighbourhood with the same code, site and
days: those rows are one work here. The datastore's own row number (`_id`)
changes when the table is reloaded (0 of 465 codes kept theirs between 16 and
21 October 2026), so the work's code is its identity. Fetched without a key
on 21 October 2026: 1,939 rows, 1,766 works, 235 not yet ended.

Days are whole days in Madrid time (the first day from 00:00, the last until
23:59:59). Status Finalitzada is the source reporting the work finished.

The type comes from `tipusobra`: urbanisation, utility services, sewers,
paving, mobility, street lighting and school-surroundings works are road
works; building works, green spaces, cranes, transport infrastructure (often
inside a metro station) and "Altres" keep their words with no type. A work
with no readable site is not taken (REI keeps located events only).

Licence: CC BY 4.0 (`license_id` CC-BY-4.0 on the dataset, read through the
portal's API on 21 October 2026), credit "Ajuntament de Barcelona"
(docs/data-sources/spain-connectors-2026-10-21.md).
"""

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from pydantic import TypeAdapter, ValidationError

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.geo_models import Geometry
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

SOURCE_ID = "barcelona-public-space-works"
RESOURCE_ID = "4e6b3bfe-2f47-4d35-aa7d-3e4bcc930cea"
ENDPOINT = "https://opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search"
SOURCE_URL = "https://opendata-ajuntament.barcelona.cat/data/en/dataset/obres"
ATTRIBUTION = "Ajuntament de Barcelona, Open Data BCN: Obres a l'espai públic (CC BY 4.0)"
MADRID = ZoneInfo("Europe/Madrid")
PAGE_SIZE = 1000
# The table held 1,939 rows on 21 October 2026; more than this is not a works list.
MAX_PAGES = 10
# Every column but the ETRS89 copy of the site.
FIELDS = (
    "_id,codi,ubicacio,codi_districte,nom_districte,codi_barri,nom_barri,tipusobra,"
    "pressupost_licitacio,pressupost_adjudicacio,data_inici,data_fi,promotor,constructor,"
    "estat,titol,descripcio,url_web_obres,geometria_wgs84"
)
ROAD_WORKS = frozenset(
    {
        "Urbanització",
        "Serveis",
        "Clavegueram",
        "Pavimentacions",
        "Mobilitat",
        "Enllumenat",
        "Entorns Escolars",
    }
)
FINISHED = "Finalitzada"
# Per-neighbourhood columns: the only ones that differ between a work's rows.
AREA_FIELDS = ("codi_districte", "nom_districte", "codi_barri", "nom_barri")
_GEOMETRY = TypeAdapter(Geometry)


def barcelona_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("barcelona")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Barcelona works in public space (obres)",
        organization="Ajuntament de Barcelona (Gerència de Mobilitat, Infraestructures i Serveis Urbans)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Catalonia",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Open Data BCN CKAN datastore_search (JSON, WKT in WGS 84), pages of 1,000; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="ca",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="barcelona_obres",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; updated daily, polled twice a day (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (dataset licence CC-BY-4.0, Open Data BCN)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each work's rows as received (one per neighbourhood).",
        notes=(
            "Works in Barcelona's public space, each with its site as a polygon and its first and "
            "last day. Fetched without a key on 21 October 2026: 1,939 rows (1,766 works), 235 "
            "works not yet ended. The portal's web pages answer HTTP 403 to REI's user agent; the "
            "documented API answers."
        ),
    )


# --- WKT ------------------------------------------------------------------------------

_TOKEN = re.compile(r"\(|\)|,|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_SHAPES = {
    "POINT": "Point",
    "LINESTRING": "LineString",
    "POLYGON": "Polygon",
    "MULTILINESTRING": "MultiLineString",
    "MULTIPOLYGON": "MultiPolygon",
}


def _nested(tokens: list[str], position: int) -> tuple[Any, int]:
    """One parenthesised WKT list from tokens[position]: a position, or a list of them."""
    if tokens[position] != "(":
        raise ValueError("expected '('")
    position += 1
    if tokens[position] == "(":
        parts = []
        while True:
            part, position = _nested(tokens, position)
            parts.append(part)
            if tokens[position] == ",":
                position += 1
                continue
            if tokens[position] == ")":
                return parts, position + 1
            raise ValueError("expected ',' or ')'")
    positions: list[list[float]] = []
    current: list[float] = []
    while tokens[position] != ")":
        if tokens[position] == ",":
            positions.append(current)
            current = []
        else:
            current.append(float(tokens[position]))
        position += 1
    positions.append(current)
    return positions, position + 1


def wkt_geometry(text: Any) -> dict[str, Any] | None:
    """A WKT shape as GeoJSON, exactly as written (x y = longitude latitude); None if
    it is empty, of another kind, or not a valid GeoJSON shape (an unclosed ring, say)."""
    value = clean(text)
    match = re.match(r"^([A-Za-z]+)\s*(?:Z|M|ZM)?\s*(\(.*\))$", value, re.DOTALL)
    if not match or match.group(1).upper() not in _SHAPES:
        return None
    kind = _SHAPES[match.group(1).upper()]
    try:
        tokens = _TOKEN.findall(match.group(2))
        coordinates, end = _nested(tokens, 0)
        if end != len(tokens):
            return None
        if kind == "Point":
            coordinates = coordinates[0]
        geometry = {"type": kind, "coordinates": _two_d(coordinates)}
        # The shape must be valid GeoJSON as written (nesting, closed rings, ranges).
        _GEOMETRY.validate_python(geometry)
    except (ValueError, IndexError, ValidationError):
        return None
    return geometry


def _two_d(value: Any) -> Any:
    """Positions as [longitude, latitude]; a third or fourth value (Z, M) is left out."""
    if value and all(isinstance(number, float) for number in value):
        return value[:2]
    return [_two_d(part) for part in value]


# --- the feed ---------------------------------------------------------------------------


def _names(rows: list[dict[str, Any]], field: str) -> list[str]:
    names: list[str] = []
    for row in rows:
        name = clean(row.get(field))
        if name and name not in names:
            names.append(name)
    return names


def to_record(work: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    rows = work.get("rows")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    row = rows[0]
    code = clean(work.get("codi") or row.get("codi"))
    geometry = wkt_geometry(row.get("geometria_wgs84"))
    if not code or geometry is None:
        return None
    kind = clean(row.get("tipusobra"))
    status = clean(row.get("estat"))
    start, end = whole_days(
        local_day(row.get("data_inici"), MADRID), local_day(row.get("data_fi"), MADRID), MADRID
    )
    districts = _names(rows, "nom_districte")
    neighbourhoods = _names(rows, "nom_barri")
    street = clean(row.get("ubicacio"))
    if street.upper() == "VARIS":  # "various": several sites
        street = ""
    title_words = clean(row.get("titol"))
    place = street or title_words or "several sites"
    area = ", ".join(districts[:2]) + (" and others" if len(districts) > 2 else "")
    label = "Road works" if kind in ROAD_WORKS else "Works in public space"
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value if kind in ROAD_WORKS else None,
        category=" / ".join(part for part in ("Obres a l'espai públic", kind) if part),
        status=status or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=", ".join(part for part in (place, area, "Barcelona") if part),
                kind="work site",
                geometry=geometry,
            )
        ],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        reported_ended=status == FINISHED,
        stated_period=(
            f"data_inici {clean(row.get('data_inici'))[:10]} – data_fi {clean(row.get('data_fi'))[:10]} "
            "(days, Barcelona time)"
        ),
        covers_city=True,
    )
    summary = ". ".join(
        part
        for part in (
            title_words if title_words != place else "",
            clean(row.get("descripcio")),
            f"Type: {kind}" if kind else "",
            f"Status: {status}" if status else "",
            f"Neighbourhoods: {', '.join(neighbourhoods)}" if neighbourhoods else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=code,
        url=clean(row.get("url_web_obres")) or SOURCE_URL,
        title=f"{label} ({kind or 'obres'}): {place}" + (f" ({area})" if area else ""),
        summary=summary or None,
        categories=[part for part in (kind, status) if part],
        item=work,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def group_works(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The rows of each work code together, in the order the codes first appear."""
    works: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        code = clean(row.get("codi"))
        if code:
            works.setdefault(code, []).append(row)
    def area(row: dict[str, Any]) -> list[str]:
        return [clean(row.get(field)) for field in AREA_FIELDS]

    return [{"codi": code, "rows": sorted(group, key=area)} for code, group in works.items()]


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    rows: list[dict[str, Any]] = []
    for page in range(MAX_PAGES):
        body = fetch_json(
            ENDPOINT,
            user_agent,
            client=client,
            params={
                "resource_id": RESOURCE_ID,
                "limit": str(PAGE_SIZE),
                "offset": str(page * PAGE_SIZE),
                "sort": "_id",
                "fields": FIELDS,
            },
        )
        result = body.get("result") if isinstance(body, dict) else None
        if not isinstance(body, dict) or body.get("success") is not True or not isinstance(result, dict):
            raise ConnectorError(f"{ENDPOINT} did not return a CKAN datastore result")
        batch = result.get("records")
        if not isinstance(batch, list):
            raise ConnectorError(f"{ENDPOINT} did not return a list of records")
        rows.extend(row for row in batch if isinstance(row, dict))
        total = result.get("total")
        if not batch or (isinstance(total, int) and len(rows) >= total) or len(batch) < PAGE_SIZE:
            return group_works(rows)
    raise ConnectorError(f"{ENDPOINT} lists more than {MAX_PAGES * PAGE_SIZE} works")


class BarcelonaWorksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        # The datastore renumbers its rows (`_id`) when the table is reloaded;
        # that is not a change of the work.
        item = raw.get("item", {})
        rows = [row for row in (item.get("rows", []) if isinstance(item, dict) else []) if isinstance(row, dict)]
        return content_key({"rows": [content_key(row, frozenset({"_id"})) for row in rows]}, frozenset())
