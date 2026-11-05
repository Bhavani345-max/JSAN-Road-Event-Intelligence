"""Tallinn street closures and works on city land (opinfo.tallinn.ee), Estonia (5 November 2026).

    GET https://opinfo.tallinn.ee/objektid/xml/183ac3aa   street closures
    GET https://opinfo.tallinn.ee/objektid/xml/f2325e11   works on city land

The Tallinn City Government (Tallinna Linnavalitsus) publishes, from its
opinfo.tallinn.ee information system, every temporary street closure
("Tänava ajutine sulgemine") and every permit for works on city land that is
in force or coming: excavations ("Kaevetöö", "Avariikaevetöö" for emergency
digs), road works, haulage and weight-limit permits and others. Each object
has its type (`too_liik`), the reason (`pohjus`, `pohjuse_selgitus`), a
description (`kirjeldus`), a start and an end (`algus`, `lopp`, Tallinn time,
'2026-11-05 08:00'), how the period runs (`perioodi_tyyp`: "pidev" for
continuous, "iga päev" every day, "tööpäeviti" on weekdays, with the hours in
`kellaajad`), its address, where on the street it happens (`toimumiskohad`:
carriageway "Sõidutee", pavements "Kõnnitee", green areas "Haljasala", each
with the total and the closed width, 'kogulaius 7 m, suletav laius 3 m') and
its shape (`ruumiobjekt_kml`: a point, a line or a polygon in WGS 84; the
`ruumiobjekt_geojson` beside it is in the Estonian grid, L-EST97, and is not
read). The closures list is also in the works list, so the two are read as
one, by object id. Fetched without a key on 5 November 2026: 209 closures
(179 in force, 30 coming) and 580 works objects, 610 objects in all.

Only what happens on the carriageway is a road event here, as for Copenhagen
(decision 0053):
- a closure is kept when its carriageway is closed, wholly (a road closure)
  or partly (a lane restriction), as its own widths state; a closure of the
  pavement or a square only, or one that closes 0 m of the carriageway, is not;
- an excavation is kept, as road works, when it digs the carriageway; one in
  the pavement or a green area only is not;
- road works ("Teetöö") give no place on the street and are not kept; nor are
  haulage, weight-limit and night-work permits, heating interruptions or
  street-lighting maintenance, which are not events on the road.
On 5 November 2026: 116 closures and 77 excavations kept.

Personal data: the applicant, the client, the contractor and the owner
(`taotleja`, `tellija`, `teostaja`, `valdaja`) can be private persons and are
dropped before anything is stored, evidence included; telephone numbers and
e-mail addresses written in the free text are removed from it.

Licence: CC BY 3.0, as the Estonian open data portal's entry for the dataset
states for both files ("license": "CC_BY_3.0"; publisher Tallinna Linnavalitsus;
andmed.eesti.ee/api/datasets/slug/tallinna-tanavate-sulgemised-ja-teemaa-alal-
toimuvate-toode-info-opinfo.tallinn.ee-infosusteemist, read 5 November 2026).
opinfo.tallinn.ee has no robots.txt (404).
"""

import re
import xml.etree.ElementTree as ET
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

from .common import fetch_text
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time

SOURCE_ID = "tallinn-street-closures-and-works"
CLOSURES_FEED = "https://opinfo.tallinn.ee/objektid/xml/183ac3aa"
WORKS_FEED = "https://opinfo.tallinn.ee/objektid/xml/f2325e11"
FEEDS = (CLOSURES_FEED, WORKS_FEED)
SOURCE_URL = (
    "https://andmed.eesti.ee/datasets/"
    "tallinna-tanavate-sulgemised-ja-teemaa-alal-toimuvate-toode-info-opinfo.tallinn.ee-infosusteemist"
)
ATTRIBUTION = "Tallinna Linnavalitsus, opinfo.tallinn.ee (Eesti avaandmete portaal), CC BY 3.0"
TALLINN = ZoneInfo("Europe/Tallinn")
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")

CLOSURE = "Tänava ajutine sulgemine"
EXCAVATION = "Kaevetöö"
EMERGENCY_EXCAVATION = "Avariikaevetöö"
KEPT_WORK = frozenset({CLOSURE, EXCAVATION, EMERGENCY_EXCAVATION})
# The carriageway, alone or with the pavement or a green area ("Sõidutee ja haljasala").
CARRIAGEWAY = "sõidutee"
# The applicant, client, contractor and owner may be private persons: not kept.
PERSONAL_FIELDS = frozenset({"taotleja", "tellija", "teostaja", "valdaja"})
FREE_TEXT = ("kirjeldus", "pohjuse_selgitus", "aadressi_tapsustus")

_WIDTHS = re.compile(r"kogulaius\s+([\d.,]+)\s*m,\s*suletav laius\s+([\d.,]+)\s*m", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Seven digits or more, single spaces allowed between them: '+372 5123 4567', '6404404'.
_PHONE = re.compile(r"(?<!\d)\+?\d(?:[  ]?\d){6,}(?!\d)")
_COORDINATES = re.compile(r"<coordinates>(.*?)</coordinates>", re.DOTALL)
_SHAPE = re.compile(r"<(Point|LineString|Polygon)\b")


def tallinn_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("tallinn")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Tallinn street closures and works (opinfo.tallinn.ee)",
        organization="Tallinna Linnavalitsus",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Harju maakond",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=CLOSURES_FEED,
        access_method=(
            "Two XML files (street closures 183ac3aa; works on city land f2325e11), "
            "shapes in WGS 84 (KML); no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=180,
        language="et",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="tallinn_opinfo",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no robots.txt; polled every three hours (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/), as the Estonian open data "
            "portal's entry for the dataset states for both files"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention=(
            "Each object as received, less the applicant, client, contractor and owner, and less "
            "telephone numbers and e-mail addresses in its text."
        ),
        notes=(
            "Temporary street closures and excavation permits in Tallinn, in force or coming, each "
            "with a start, an end and its shape. Fetched without a key on 5 November 2026: 209 closures "
            "and 580 works objects (610 objects); the 116 closures that close carriageway width and "
            "the 77 excavations in the carriageway are kept."
        ),
    )


# --- reading one object ------------------------------------------------------------


def _scrub(text: str) -> str:
    """Free text less telephone numbers and e-mail addresses."""
    return _PHONE.sub("[removed]", _EMAIL.sub("[removed]", text))


def _fields(element: ET.Element | None) -> dict[str, str]:
    return {child.tag: clean(child.text) for child in element} if element is not None else {}


def object_item(element: ET.Element) -> dict[str, Any]:
    """One <objekt> as REI keeps it: its values, less personal data."""
    item: dict[str, Any] = {
        child.tag: clean(child.text)
        for child in element
        if len(child) == 0 and child.tag not in PERSONAL_FIELDS
    }
    item["aadress"] = _fields(element.find("aadress"))
    item["toimumiskohad"] = [_fields(place) for place in element.findall("toimumiskohad/toimumiskoht")]
    item["kellaajad"] = [_fields(hours) for hours in element.findall("kellaajad/kellaaeg")]
    for key in FREE_TEXT:
        if item.get(key):
            item[key] = _scrub(item[key])
    return item


def _positions(text: str) -> list[list[float]]:
    positions = []
    for pair in text.split():
        longitude, latitude = pair.split(",")[:2]
        positions.append([float(longitude), float(latitude)])
    return positions


def geometry(item: dict[str, Any]) -> dict[str, Any] | None:
    """The object's shape from its KML: a point, a line or a polygon, in WGS 84."""
    kml = item.get("ruumiobjekt_kml") or ""
    shape = _SHAPE.match(kml)
    try:
        rings = [_positions(text) for text in _COORDINATES.findall(kml)]
    except ValueError:
        return None
    if not shape or not rings or not all(rings):
        return None
    kind = shape.group(1)
    if kind == "Point":
        return {"type": "Point", "coordinates": rings[0][0]}
    if kind == "LineString":
        return {"type": "LineString", "coordinates": rings[0]}
    return {"type": "Polygon", "coordinates": rings}


def _width(value: str) -> float:
    return float(value.replace(",", "."))


def _carriageway(item: dict[str, Any]) -> list[dict[str, str]]:
    return [place for place in item["toimumiskohad"] if CARRIAGEWAY in place.get("liik", "").lower()]


def closure_type(item: dict[str, Any]) -> str | None:
    """A closure's event type from its carriageway widths; None when it closes none of it."""
    closed = []
    for place in _carriageway(item):
        widths = _WIDTHS.search(place.get("ala", ""))
        if widths:
            total, shut = _width(widths.group(1)), _width(widths.group(2))
            if shut > 0:
                closed.append(shut >= total)
    if not closed:
        return None
    return EventType.PLANNED_ROAD_CLOSURE.value if any(closed) else EventType.LANE_RESTRICTION.value


def _stated_period(item: dict[str, Any]) -> str | None:
    first, last = item.get("algus", ""), item.get("lopp", "")
    if not first and not last:
        return None
    hours = ", ".join(
        f"{clean(h.get('algus'))}–{clean(h.get('lopp'))}" for h in item["kellaajad"] if h.get("algus") or h.get("lopp")
    )
    how = ": ".join(part for part in (item.get("perioodi_tyyp", ""), hours) if part)
    return f"{first} – {last}" + (f" ({how})" if how else "")


LABELS = {
    EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
    EventType.LANE_RESTRICTION.value: "Lane restriction",
}


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One object as REI's record; None when it is not an event on the carriageway."""
    work = item.get("too_liik", "")
    object_id = item.get("id", "")
    if work not in KEPT_WORK or not object_id:
        return None
    if work == CLOSURE:
        event_type = closure_type(item)
    else:
        event_type = EventType.ROAD_WORKS.value if _carriageway(item) else None
    shape = geometry(item)
    if event_type is None or shape is None:
        return None
    address = item["aadress"]
    place = address.get("tekst") or next(
        (p.get("street_name", "") for p in _carriageway(item) if p.get("street_name")), ""
    )
    road = address.get("ads_liikluspind") or address.get("ads_nimi") or ""
    widths = "; ".join(
        f"{p.get('liik', '')}: {p.get('ala', '')}".strip(": ") for p in _carriageway(item) if p.get("ala")
    )
    reasons = [part for part in (clean(text) for text in item.get("pohjus", "").split(",")) if part]
    label = LABELS.get(event_type) or ("Emergency excavation" if work == EMERGENCY_EXCAVATION else "Excavation")
    stated = _stated_period(item)
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (work, item.get("pohjus", "")) if part),
        start=local_time(item.get("algus"), TALLINN, TIME_FORMATS),
        end=local_time(item.get("lopp"), TALLINN, TIME_FORMATS),
        geometry=shape,
        locations=[
            SourceLocation(
                name=place,
                kind={"LineString": "street section", "Polygon": "works area"}.get(shape["type"], "location"),
                geometry=shape,
                closure=widths or None,
            )
        ]
        if place
        else [],
        affected_road=road or place or None,
        attribution=ATTRIBUTION,
        stated_period=stated,
        covers_city=True,
    )
    menetlus = item.get("menetlus_url", "")
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"objekt:{object_id}",
        url=menetlus if menetlus.startswith("https://opinfo.tallinn.ee/") else SOURCE_URL,
        title=f"{label}: {place or 'Tallinn'} (Tallinn)",
        summary=". ".join(
            part
            for part in (
                text.rstrip(". ")
                for text in (
                    work,
                    item.get("pohjus", ""),
                    item.get("pohjuse_selgitus", ""),
                    item.get("kirjeldus", ""),
                    widths,
                    "Olulise mõjuga" if item.get("olulise_mojuga") == "true" else "",
                )
            )
            if part
        ),
        categories=[work, *reasons],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=local_time(item.get("tekkimise_aeg"), TALLINN, TIME_FORMATS),
    )


# --- fetching ---------------------------------------------------------------------------


def parse_feed(text: str, url: str) -> list[dict[str, Any]]:
    """The objects of one file; an error when the file is not whole."""
    try:
        root = ET.fromstring(text.lstrip("﻿"))
    except ET.ParseError as error:
        raise ConnectorError(f"{url} is not readable XML: {error}") from error
    answer = root.find("vastus")
    if answer is None:
        raise ConnectorError(f"{url} has no answer (<vastus>)")
    pages = clean(answer.findtext("lehekylgi_kokku"))
    if pages not in ("", "0", "1"):
        raise ConnectorError(f"{url} lists {pages} pages; REI reads one")
    objects = answer.findall("objektid/objekt")
    count = clean(answer.findtext("kirjeid"))
    if count.isdigit() and int(count) != len(objects):
        raise ConnectorError(f"{url} says {count} objects but holds {len(objects)}")
    return [object_item(element) for element in objects]


def _first_position(shape: dict[str, Any]) -> list[float]:
    position = shape["coordinates"]
    while isinstance(position[0], list):
        position = position[0]
    return position


def fetch_objects(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """Both files' objects, each once (the closures are in both)."""
    by_id: dict[str, dict[str, Any]] = {}
    for url in FEEDS:
        for item in parse_feed(fetch_text(url, user_agent, client=client), url):
            if item.get("id"):
                by_id.setdefault(item["id"], item)
    for item in by_id.values():
        shape = geometry(item)
        # Tallinn lies at about 24.7° E, 59.4° N: a first number above the second is a latitude.
        if shape is not None and (position := _first_position(shape))[0] > position[1]:
            raise ConnectorError(f"{WORKS_FEED} returned coordinates in latitude-longitude order")
    return list(by_id.values())


class TallinnStreetClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_objects)
    to_record = staticmethod(to_record)
