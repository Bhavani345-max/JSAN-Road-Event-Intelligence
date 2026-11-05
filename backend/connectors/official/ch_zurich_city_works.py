"""Stadt Zürich, current civil-engineering projects on public ground, Switzerland (5 November 2026).

    GET https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Aktuelle_Tiefbauprojekte_im_oeffentlichen_Grund
        ?service=WFS&version=1.1.0&request=GetFeature&typename=aer_baustellen_a
        &outputFormat=GeoJSON&srsName=EPSG:4326

The City of Zürich's civil engineering office (Tiefbauamt) publishes its
current and coming larger works on public ground ("Aktuelle Tiefbauprojekte
im öffentlichen Grund"; catalogue: opendata.swiss, organisation stadt-zurich),
a WFS layer served as GeoJSON in WGS 84. Each feature is one project's works
area as a multipolygon, with the project number (`id_proj_taz_z`, also in the
project page address `www`) and the works number (`baunr`), the title
(`titel`, usually the street or place), the stretch (`baubereich`, "Gabler-
bis Brunaustrasse"), the description (`projektbeschrieb`), the city district
(`kreis`), the category (`kategorie`) and the first and last day (`baubeginn`,
`bauende`, written 2026-04-27). `stand` is the date of the daily snapshot
(20261104 on every record). Fetched without a key on 5 November 2026: 133
projects, all "Grössere Baustelle", all with both days; 123 under way, 10 to
come, none ended. The GeoJSON is written longitude first.

The layer lists every civil-engineering project on public ground, not only
works on roads: a playground, a swimming pool, a cemetery's drainage, a park,
a school's sports field and city-wide measuring points are in it too, and
every record carries the same search words ("Projekt Bauen Tiefbauamt
Strassenbau Baustelle"), so no field tells them apart. A project is kept as a
road event only when its title or its stretch names a street, lane, quay,
square, avenue, bridge, junction, pavement or stop (strasse, gasse, quai,
platz, allee, brücke, graben, weg, Haltestelle, Knoten, Kreuzung, Einmündung,
Trottoir), and its title names no facility off the road (a park, Freibad,
Friedhof, Gartenareal, Schulhaus, Schulsport, Kindergarten, Sportanlage,
Spielplatz, Planschbecken, Velostation). On 5 November 2026 that keeps 100 of
the 133 (95 under way, 5 to come). Among those left out are two whole-area
programmes that name no street, "Niederdorf und Oberdorf" (whose streets the
layer also lists one by one) and "Energieverbund Höngg" (Gesamtperimeter). Every kept
project is road works (ROAD_WORKS); the layer does not say whether traffic is
closed, and REI does not say so either.

Days are whole days, Zürich time: from the start of the first to the end of
the last.

Personal data: each project names its project leader with an e-mail address
and a telephone number (`projektleiter`, `projektleiter_email`, `tel`); all
three are dropped before anything is stored, evidence included. The feature
ids and `objectid` are the server's row numbers; REI's record id is the
project number.

Licence: opendata.swiss terms "Freie Nutzung" (terms_open, as the catalogue
entry states on every distribution): "Sie dürfen diesen Datensatz für
kommerzielle Zwecke nutzen. Eine Quellenangabe wird empfohlen"
(https://opendata.swiss/de/terms-of-use, read by the researcher on 5 November
2026). Credit is recommended and given.
"""

import re
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
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, whole_days
from .feed_text import sentences

SOURCE_ID = "ch-zurich-city-civil-works"
ENDPOINT = "https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Aktuelle_Tiefbauprojekte_im_oeffentlichen_Grund"
LAYER = "aer_baustellen_a"
PARAMS = {
    "service": "WFS",
    "version": "1.1.0",
    "request": "GetFeature",
    "typename": LAYER,
    "outputFormat": "GeoJSON",
    "srsName": "EPSG:4326",
}
SOURCE_URL = "https://opendata.swiss/de/dataset/aktuelle-tiefbauprojekte-im-offentlichen-grund"
ATTRIBUTION = "Stadt Zürich, Tiefbauamt: Aktuelle Tiefbauprojekte im öffentlichen Grund (opendata.swiss)"
ZURICH = ZoneInfo("Europe/Zurich")
# The project leader, with e-mail address and telephone number: personal data, not kept.
PERSONAL_FIELDS = frozenset({"projektleiter", "projektleiter_email", "tel"})
# The server's row number and the daily snapshot date: not content.
BOOKKEEPING = frozenset({"objectid", "stand"})
# Words with which a title or stretch names a road, a square, a bridge or a stop.
ROAD_WORDS = re.compile(
    r"strasse|gasse|quai|platz\b|allee|brücke|bruecke|graben\b|weg\b"
    r"|haltestelle|knoten|kreuzung|einmündung|trottoir",
    re.IGNORECASE,
)
# Words with which a title names a facility off the road.
OFF_ROAD_WORDS = re.compile(
    r"park\b|freibad|friedhof|gartenareal|schulhaus|schulsport|kindergarten|sportanlage"
    r"|spielplatz|planschbecken|velostation",
    re.IGNORECASE,
)


def zurich_city_works_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("switzerland")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Stadt Zürich civil-engineering works on public ground",
        organization="Stadt Zürich, Tiefbauamt",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Zürich (Stadt Zürich)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WFS 1.1.0 GetFeature (GeoJSON, EPSG:4326), layer aer_baustellen_a; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="de",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="ch_zurich_city_civil_works",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; a daily snapshot, polled every twelve hours (one request).",
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
        evidence_retention="Each project as received, less its project leader's name, e-mail and telephone.",
        notes=(
            "The City of Zürich's larger civil-engineering projects on public ground, current and coming, "
            "each a works area with a first and a last day. Fetched without a key on 5 November 2026: 133 "
            "projects; the 100 whose title or stretch names a road and whose title names no park, pool, "
            "cemetery, school or sports ground are kept."
        ),
    )


def on_a_road(title: str, stretch: str) -> bool:
    """A project on a road: its title or stretch names one, and its title names no off-road facility."""
    return bool(ROAD_WORDS.search(f"{title} {stretch}")) and not OFF_ROAD_WORDS.search(title)


def _number(value: Any) -> str:
    """5704.0 -> '5704'; text stays text; nothing -> ''."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return clean(value)


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One project as REI's record; None when it is not on a road or names no project number."""
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if geometry.get("type") not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point"):
        return None
    if clean(properties.get("publish_internet")) == "0":
        return None
    project, works_number = _number(properties.get("id_proj_taz_z")), _number(properties.get("baunr"))
    title = clean(properties.get("titel"))
    stretch = clean(properties.get("baubereich"))
    if not (project or works_number) or not on_a_road(title, stretch):
        return None
    first, last = clean(properties.get("baubeginn")), clean(properties.get("bauende"))
    start, end = whole_days(local_day(first, ZURICH), local_day(last, ZURICH), ZURICH)
    district = _number(properties.get("kreis"))
    category = clean(properties.get("kategorie"))
    place = ", ".join(part for part in (title, stretch) if part)
    page = clean(properties.get("www"))
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=category or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="location", geometry=geometry)] if place else [],
        affected_road=title if ROAD_WORDS.search(title) else None,
        attribution=ATTRIBUTION,
        stated_period=f"{first} – {last}" if first or last else None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"project:{project}" if project else f"works:{works_number}",
        url=page if page.startswith("https://") else SOURCE_URL,
        title=f"Road works: {title or stretch} (Zürich)",
        summary=sentences(
            clean(properties.get("projektbeschrieb")),
            f"Baubereich: {stretch}" if stretch else "",
            f"Kreis {district}" if district else "",
        ),
        categories=[part for part in (category,) if part],
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
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def fetch_projects(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) did not return a GeoJSON feature collection")
    matched = body.get("numberMatched", body.get("totalFeatures"))
    if isinstance(matched, int) and matched > len(features):
        raise ConnectorError(f"{ENDPOINT} ({LAYER}) lists {matched} projects, more than it returned")
    projects = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        # Zürich lies at about 8.5° E, 47.4° N: a first number above the second is a latitude.
        position = _first_position(feature.get("geometry"))
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{ENDPOINT} ({LAYER}) returned coordinates in latitude-longitude order")
        projects.append(_without_personal_data(feature))
    return projects


class ZurichCityWorksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_projects)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The project's content: a new snapshot date or row number alone is not a revision."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in BOOKKEEPING
        }
        return content_key({**item, "properties": properties}, frozenset({"id"}))
