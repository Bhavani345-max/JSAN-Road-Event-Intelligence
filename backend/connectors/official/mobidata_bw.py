"""MobiData BW roadworks, Baden-Württemberg, Germany (5 November 2026).

    GET https://api.mobidata-bw.de/datasets/traffic/roadworks/roadworks_geojson.json

"Baustelleninformationen Baden-Württemberg": the planned and current works on
the federal roads (Bundesstraßen) and the classified state and district roads
(Landes- und Kreisstraßen) of Baden-Württemberg, as shown in the VerkehrsInfo
BW, published by the Ministerium für Verkehr Baden-Württemberg on MobiData BW
(run by the NVBW) as one GeoJSON file in WGS 84. It is not the motorways'
list, although a few features lie on one (on 5 November 2026 an A98 tunnel
closure and an A5 section of the B 35 works; kept like any other).
Each feature is one closure or works phase with a stable `id`; its `type`
(CONSTRUCTION, or ROAD_CLOSED with the subtype ROAD_CLOSED_CONSTRUCTION); a
`description` ("Bauphase", "B294 Straßenausbau", "B29 Tunnelwartung"); the
road and its section (`street`: "B311 Krauchenwies-Mengen", or
"Gemeindestraße" for a municipal road); the `direction` affected
(BOTH_DIRECTIONS or ONE_DIRECTION); a start and an end with their offset
(`starttime`, `endtime`: "2027-03-01T00:00:00.000+01:00", read as written);
and `reference` ("MobiData BW" on every feature). Fetched without a key on
5 November 2026 (12:33 UTC): 909 features (905 lines, 4 points), every one
with a start and an end; 709 in force, 200 starting later, none ended.
Nothing in it names a person.

A works phase with its own id ("….001", "….002": the nights of a tunnel's
maintenance) is its own record. ROAD_CLOSED is a planned road closure;
CONSTRUCTION is road works, and as the source does not say whether it
restricts traffic, REI does not either. BOTH_DIRECTIONS is kept as the
event's direction; ONE_DIRECTION names no direction, so its words stay on the
location only. A municipal road's `street` is only its class,
"Gemeindestraße" (319 features on 5 November 2026): it names no road, so such
a record keeps no affected road and no named location (the title keeps the
words; the description often names the place); its place is its line.

The 4 points of 5 November 2026 (one B535 closure near Schwetzingen, two
places each listed under two ids) are written latitude first ([49.39, 8.57])
while every line is written longitude first. REI does not swap a source's
coordinates: a feature written latitude first is left out (4 on 5 November
2026, so 905 records: 705 in force, 200 coming; one of them starts on 1 April
2031, beyond REI's run window of a year, so a run keeps 904), and a response
written latitude first throughout is refused.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0, as the
dataset's MobiData BW page states (mobidata-bw.de/dataset/
baustelleninformationen-baden-wurttemberg, organisation Verkehrsministerium
Baden-Württemberg, read 5 November 2026); the API host's robots.txt allows
every path (docs/data-sources/worldwide-sources-2026-11-05.md). The licence
asks for the provider, the licence with its link, the dataset's address and a
note that the data were changed.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventDirection, EventType
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
from .feature_feed import FeatureFeedConnector, clean, item_record
from .feed_text import sentences

SOURCE_ID = "de-mobidata-bw-roadworks"
ENDPOINT = "https://api.mobidata-bw.de/datasets/traffic/roadworks/roadworks_geojson.json"
SOURCE_URL = "https://www.mobidata-bw.de/dataset/baustelleninformationen-baden-wurttemberg"
ATTRIBUTION = (
    "Ministerium für Verkehr Baden-Württemberg, Baustelleninformationen Baden-Württemberg (MobiData BW); "
    "Datenlizenz Deutschland – Namensnennung – Version 2.0 (www.govdata.de/dl-de/by-2-0); "
    f"{SOURCE_URL}; data changed (read into REI events)"
)
BERLIN = ZoneInfo("Europe/Berlin")
CLOSED, WORKS = "ROAD_CLOSED", "CONSTRUCTION"
EVENT_TYPES = {CLOSED: EventType.PLANNED_ROAD_CLOSURE.value, WORKS: EventType.ROAD_WORKS.value}
LABELS = {CLOSED: "Road closed", WORKS: "Road works"}
DIRECTION_WORDS = {"BOTH_DIRECTIONS": "both directions", "ONE_DIRECTION": "one direction"}
# What `street` says of a municipal road: its class, without a name.
UNNAMED_MUNICIPAL_ROAD = "Gemeindestraße"
SHAPES = ("LineString", "MultiLineString", "Point")


def mobidata_bw_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("germany")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="MobiData BW roadworks (Baden-Württemberg)",
        organization="Ministerium für Verkehr Baden-Württemberg (MobiData BW, NVBW)",
        authority_type="STATE_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Baden-Württemberg",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="GeoJSON file (WGS 84) on the MobiData BW API; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="de",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value, EventType.ROAD_WORKS.value),
        parser_type="mobidata_bw_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt allows all; polled hourly (one request, about 1 MB).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        provides_direction=True,
        real_time=False,
        evidence_retention="Each closure or works phase as received.",
        notes=(
            "Planned and current works and closures on Baden-Württemberg's federal, state and district "
            "roads (rarely a motorway), each a line with a start and an end. Fetched without a key on "
            "5 November 2026: 909 features; 4 points written latitude first are left out, 905 kept "
            "(705 in force, 200 coming)."
        ),
    )


def _first_position(geometry: Any) -> Any:
    position = geometry.get("coordinates") if isinstance(geometry, dict) else None
    while isinstance(position, list) and position and isinstance(position[0], list):
        position = position[0]
    return position


def latitude_first(geometry: Any) -> bool:
    """Baden-Württemberg lies at 7.5-10.5° E, 47.5-49.8° N: a first number above the second is a latitude."""
    position = _first_position(geometry)
    return (
        isinstance(position, list)
        and len(position) >= 2
        and all(isinstance(value, (int, float)) for value in position[:2])
        and position[0] > position[1]
    )


def _time(value: Any) -> datetime | None:
    """An ISO time with its offset; one written without an offset is Baden-Württemberg time."""
    try:
        moment = datetime.fromisoformat(clean(value))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=BERLIN)


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("id"))
    if not external_id or geometry.get("type") not in SHAPES or latitude_first(geometry):
        return None
    kind, subtype = clean(properties.get("type")), clean(properties.get("subtype"))
    street = clean(properties.get("street"))
    # "Gemeindestraße" is the class of a municipal road, not its name: no road is named.
    road = "" if street == UNNAMED_MUNICIPAL_ROAD else street
    description = clean(properties.get("description"))
    direction = clean(properties.get("direction"))
    direction_words = DIRECTION_WORDS.get(direction, direction.lower())
    # A type REI does not know keeps its own words and no event type.
    label = LABELS.get(kind) or kind.replace("_", " ").capitalize() or "Works"
    structured = SourceEvent(
        event_type=EVENT_TYPES.get(kind),
        category=" / ".join(part for part in (kind, subtype) if part) or None,
        start=_time(properties.get("starttime")),
        end=_time(properties.get("endtime")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=road,
                kind="road section" if geometry["type"] != "Point" else "location",
                geometry=geometry,
                direction=direction_words or None,
                closure=kind if kind == CLOSED else None,
            )
        ]
        if road
        else [],
        affected_road=road or None,
        direction=EventDirection.BOTH_DIRECTIONS.value if direction == "BOTH_DIRECTIONS" else None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    what = f" – {description}" if description and description != street else ""
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {street or 'Baden-Württemberg'}{what} (Baden-Württemberg)",
        summary=sentences(description, f"Direction: {direction_words}" if direction_words else ""),
        categories=[part for part in (label.lower(), direction_words, street if not road else "") if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_roadworks(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    features = [feature for feature in features if isinstance(feature, dict)]
    located = [feature for feature in features if isinstance(_first_position(feature.get("geometry")), list)]
    # A few points written latitude first are left out one by one (to_record);
    # a response written so throughout has been read the wrong way round.
    if located and all(latitude_first(feature.get("geometry")) for feature in located):
        raise ConnectorError(f"{ENDPOINT} returned coordinates in latitude-longitude order")
    return features


class MobiDataBwRoadworksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_roadworks)
    to_record = staticmethod(to_record)
