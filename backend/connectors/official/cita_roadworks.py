"""CITA current and future works, Luxembourg: DATEX II 2.2 (5 November 2026).

    GET https://www.cita.lu/info_trafic/datex/chantierActuelDatex.xml   (current works)
    GET https://www.cita.lu/info_trafic/datex/chantierFuturDatex.xml    (future works)

The Administration des ponts et chaussées (PCH) publishes, through its
traffic centre CITA's website, the works programme on Luxembourg's national
road network (motorways, N roads and CR roads): "Les chantiers actuels sur le
réseau routier national" and "Les futurs chantiers" on data.public.lu, each a
DATEX II 2.2 `SituationPublication` (namespace http://datex2.eu/schema/2/2_0),
without a key. REI reads the two files as one source.

How the files are built (both read 5 November 2026): a `situation` is one
works site; its `situationRecord`s are the site's stages ("Titre:Nouvelle
étape", "Phase 2"). A stage's record id ("73515-105351", the situation's id and
the stage's) is repeated when the stage covers several road sections or
measures at once (works, temporary traffic lights, a speed limit): those
records share the stage's period and title. Every record gives
`overallStartTime` and `overallEndTime` with their offset (+01:00 / +02:00),
`trafficConstrictionType` in most (roadBlocked, lanesBlocked,
lanesPartiallyObstructed), and a `tpegLinearLocation` section: its `from` and
`to` points in WGS 84, each named by the section's road code as CITA writes
it ("CR129", "N10", "A6W-G", "B-G-N"). Comments carry the
stage's title ("Titre:…") and, in some, what road users find ("ROUTE BARREE",
"chaussée rétrécie, feux tricolores lumineux") or a diversion. The publisher
writes no accented letters ("Nouvelle tape", "chausse rtrcie"); the words are
kept as published, never respelled.

On 5 November 2026 (13:30 CET): current works 150 situations, 259 records,
233 stages (154 in force, 20 to come later that day or after, 59 ended);
future works 61 situations, 109 records, 85 stages, all to come. No stage was
in both files.

One record per stage, as REI keeps it:

- **id**: the stage's record id; **period**: its start and end, as published;
  the stage drops out of the run once ended (kept as observed);
- **position**: the `from` point (where the section starts) of the section
  of its leading measure (a closure, else lanes, works, other measures, a
  speed limit), as Spain's DGT DATEX II feed is read; every section's from and
  to points are kept as the event's locations with their road codes. Nothing
  is drawn between them: the file gives no line;
- **type**, from the record codes: a section with roadBlocked is a planned
  road closure (an emergency one when `urgentRoadworks` is true; none on 5
  November 2026); lanesBlocked or lanesPartiallyObstructed is a lane
  restriction; otherwise MaintenanceWorks or ConstructionWorks is road works;
  a stage made only of a speed limit (SpeedManagement) or of other network
  management keeps its words with no type, for the reviewer (as for the 3.6
  feed). Events on the road for a fair or a market ("Haupeschfest 2026",
  "marché mensuel") are in the programme as works stages closing a road: their
  closures are kept as closures;
- the title's place is the sections' road codes; the stage's own title is
  added when it is not the default "Nouvelle étape" ("Nouvelle tape" as
  written). Comments go in the summary, a line naming a contact (a phone
  number, an e-mail address) removed first (datex3_nl_lu.py's rule); none did
  on 5 November 2026.

Not road events: a situation not marked "real" (a test or an exercise) and a
stage without any readable position are not taken (none on 5 November 2026).

How this relates to REI's other CITA source, lu-cita-datex2-v36
(connectors/official/cita.py, DATEX II 3.6, `situationrecord36`): that feed
lists events on the motorways and expressways as CITA activates them (works
under way, obstructions, broken-down vehicles, tunnel faults), with a start and
no end; this source is the PCH works programme for every national road, with
stated starts and ends, ahead of time. They share no ids: on 5 November 2026
the 3.6 feed's 16 situations were numbered 222918 to 238387 (records
"238387-2"), the works files' 211 situations 34246 to 74032. Some works are
in both, as different situations: of the 3.6 feed's 12 works situations at
13:40 that day, five lay within 150 m of a works stage in force here (on the
A6 at Capellen, 3 m; the Esch-Centre exit, 126 m, its 3.6 comment naming the
same dates, 2 to 13 November; the A1, 41 m; the CR137 by the A1, 33 m; the A13,
103 m). Matching them is left to REI's merge stage, by place and time.

Licence: Creative Commons Zero (CC0), as data.public.lu states for both
datasets, "PCH : Les chantiers actuels" and "PCH : Les futurs chantiers"
(licence `cc-zero`, read 5 November 2026); no attribution is required.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.time import utc_now
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

from . import datex3_nl_lu as datex
from .common import select_for_run
from .feature_feed import clean, item_record

SOURCE_ID = "lu-cita-roadworks-datex2"
CURRENT_WORKS = "https://www.cita.lu/info_trafic/datex/chantierActuelDatex.xml"
FUTURE_WORKS = "https://www.cita.lu/info_trafic/datex/chantierFuturDatex.xml"
ENDPOINTS = (CURRENT_WORKS, FUTURE_WORKS)
SOURCE_URL = "https://data.public.lu/fr/datasets/pch-les-chantiers-actuels/"
LICENCE = "Creative Commons Zero (CC0) 1.0 (data.public.lu dataset licence)"
ATTRIBUTION = "Source: Administration des ponts et chaussées, CITA (Luxembourg), CC0."
LUXEMBOURG = ZoneInfo("Europe/Luxembourg")
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
TITLE_PREFIX = "Titre:"
# The stage title the publisher gives by default ("Nouvelle étape", written without its accent).
DEFAULT_TITLES = frozenset({"nouvelle tape", "nouvelle étape", "nouvelle etape"})

WORKS = frozenset({"MaintenanceWorks", "ConstructionWorks"})
# The detail field of each DATEX II 2.2 record type this feed uses.
DETAIL_FIELDS = (
    "roadMaintenanceType",
    "constructionWorkType",
    "generalNetworkManagementType",
    "roadOrCarriagewayOrLaneManagementType",
    "speedManagementType",
)
CONSTRICTION_LABELS = {
    "roadBlocked": "Road closed",
    "lanesBlocked": "Lanes closed",
    "lanesPartiallyObstructed": "Lanes partially obstructed",
}
LANE_CONSTRICTIONS = frozenset({"lanesBlocked", "lanesPartiallyObstructed"})
# Which part names the stage first: a closure, then lanes, works, other measures, a speed limit.
_CONSTRICTION_RANK = {"roadBlocked": 0, "lanesBlocked": 1, "lanesPartiallyObstructed": 2}


def cita_roadworks_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("luxembourg")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="CITA current and future road works, Luxembourg",
        organization="Administration des ponts et chaussées (CITA traffic control centre)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="National",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=CURRENT_WORKS,
        access_method=(
            "Two DATEX II 2.2 situation publications (XML), current and future works "
            "(chantierActuelDatex.xml, chantierFuturDatex.xml); no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fr",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
        ),
        parser_type="cita_datex22_works",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "None published; robots.txt allows all; data.public.lu lists the files as updated "
            "daily. Two requests a run (0.6 MB and 0.3 MB)."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=LICENCE,
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each works stage as the fields its records state (types, codes, times, comments, "
            "sections' from and to points and road codes)."
        ),
        notes=(
            "The PCH works programme on Luxembourg's national roads, current and future, one "
            "record per works stage with a stated start and end and WGS 84 section points. "
            "Fetched without a key on 5 November 2026: 211 situations, 368 records, 318 stages "
            "(154 in force, 105 to come, 59 ended). A different feed from lu-cita-datex2-v36 "
            "(no shared ids)."
        ),
    )


# --- reading a publication --------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None, path: str) -> str | None:
    if element is None:
        return None
    return clean(element.findtext(path)) or None


def _values(element: ET.Element | None) -> list[str]:
    """The texts of a DATEX II multilingual string (`values/value`), as written (lines kept)."""
    if element is None:
        return []
    return [text for node in element.iter() if _local(node.tag) == "value" and (text := (node.text or "").strip())]


def _comment(value: str) -> str | None:
    """A comment as kept: each line naming a contact removed, spaces tidied."""
    text = datex.without_contact_details(value)
    lines = [line for line in (clean(part) for part in (text or "").splitlines()) if line]
    return "\n".join(lines) or None


def _point(element: ET.Element | None) -> dict[str, Any] | None:
    """A TPEG point: its WGS 84 position and the names the source gives it."""
    if element is None:
        return None
    coordinates = element.find("{*}pointCoordinates")
    point = {
        "lat": _text(coordinates, "{*}latitude"),
        "lon": _text(coordinates, "{*}longitude"),
        "names": [clean(name) for name in _values(element.find("{*}name/{*}descriptor"))],
    }
    return {key: value for key, value in point.items() if value}


def _part(record: ET.Element) -> dict[str, Any]:
    """The fields one situation record states (one section or measure of a stage)."""
    spec = record.find("{*}validity/{*}validityTimeSpecification")
    impact = record.find("{*}impact")
    location = record.find("{*}groupOfLocations")
    linear = location.find("{*}tpegLinearLocation") if location is not None else None
    single = location.find("{*}tpegPointLocation") if location is not None else None
    part: dict[str, Any] = {
        "type": (record.get(XSI_TYPE) or "").rsplit(":", 1)[-1],
        "detail": next((value for name in DETAIL_FIELDS if (value := _text(record, "{*}" + name))), None),
        "constriction": _text(impact, "{*}trafficConstrictionType"),
        "operational_lanes": _text(impact, "{*}numberOfOperationalLanes"),
        "original_lanes": _text(impact, "{*}originalNumberOfLanes"),
        "speed_limit": _text(record, "{*}temporarySpeedLimit"),
        "compliance": _text(record, "{*}complianceOption"),
        "urgent": _text(record, "{*}urgentRoadworks"),
        "probability": _text(record, "{*}probabilityOfOccurrence"),
        "start": _text(spec, "{*}overallStartTime"),
        "end": _text(spec, "{*}overallEndTime"),
        "periods": [
            f"{_text(period, '{*}startOfPeriod') or ''}/{_text(period, '{*}endOfPeriod') or ''}"
            for period in (spec.findall("{*}validPeriod") if spec is not None else [])
        ],
        "location_type": (location.get(XSI_TYPE) or "").rsplit(":", 1)[-1] if location is not None else None,
        "direction": _text(linear if linear is not None else single, "{*}tpegDirection"),
        "from": _point(linear.find("{*}from")) if linear is not None else None,
        "to": _point(linear.find("{*}to")) if linear is not None else None,
        "point": _point(single.find("{*}point")) if single is not None else None,
        "comments": [
            text
            for comment in record.findall("{*}generalPublicComment")
            for value in _values(comment.find("{*}comment"))
            if (text := _comment(value))
        ],
    }
    return {key: value for key, value in part.items() if value not in (None, "", [], {})}


def _unique(values: Iterable[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _first_in_time(values: Iterable[str | None], *, latest: bool = False) -> str | None:
    """The earliest (or latest) of some date-times, as written; their offsets may differ."""
    timed = [(moment, value) for value in values if value and (moment := _time(value)) is not None]
    if not timed:
        return None
    return (max if latest else min)(timed, key=lambda pair: pair[0])[1]


def stage_items(situation: ET.Element) -> list[dict[str, Any]]:
    """The situation's stages: its records grouped by record id, in the order listed."""
    situation_id = situation.get("id")
    grouped: dict[str, list[ET.Element]] = {}
    for record in situation.findall("{*}situationRecord"):
        if record.get("id"):
            grouped.setdefault(record.get("id"), []).append(record)
    items = []
    for stage_id, records in grouped.items():
        parts = [_part(record) for record in records]
        comments = _unique(text for part in parts for text in part.pop("comments", []))
        titles = [text[len(TITLE_PREFIX) :].strip() for text in comments if text.startswith(TITLE_PREFIX)]
        item = {
            "situation": situation_id,
            "id": stage_id,
            "title": titles[0] if titles else None,
            "comments": [text for text in comments if not text.startswith(TITLE_PREFIX)],
            "parts": parts,
            "created": _first_in_time(_text(record, "{*}situationRecordCreationTime") for record in records),
            # Bookkeeping: when the source last touched the stage (not content; see datex.revision_key).
            "version_time": _first_in_time(
                (_text(record, "{*}situationRecordVersionTime") for record in records), latest=True
            ),
            "record_versions": {
                "situation": situation.get("version"),
                "records": [record.get("version") for record in records],
            },
        }
        items.append({key: value for key, value in item.items() if value not in (None, "", [], {})})
    return items


def read_works(body: bytes, url: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """The stages of one publication's real situations, and counts of what was read."""
    counts = {"situations": 0, "records": 0, "not_real": 0}
    items: list[dict[str, Any]] = []
    for situation in datex.iter_situations(body, url):
        counts["situations"] += 1
        counts["records"] += len(situation.findall("{*}situationRecord"))
        if (_text(situation, "{*}headerInformation/{*}informationStatus") or "real").lower() != "real":
            counts["not_real"] += 1
            continue
        items.extend(stage_items(situation))
    if counts["situations"] and not items and counts["not_real"] < counts["situations"]:
        raise ConnectorError(f"{url} lists situations but no stage could be read")
    return items, counts


# --- the record REI keeps ---------------------------------------------------------------


def _time(value: str | None) -> datetime | None:
    """A DATEX II date-time; one written without an offset is read in Luxembourg time."""
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=LUXEMBOURG)


def _position(point: dict[str, Any] | None) -> list[float] | None:
    try:
        latitude, longitude = float(point["lat"]), float(point["lon"])  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude, longitude) == (0, 0):
        return None
    return [longitude, latitude]


def _words(camel: str | None) -> str:
    """A DATEX code in words: 'repairWork' -> 'repair work'."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", camel or "").lower().strip()


def part_label(part: dict[str, Any]) -> str:
    """What one section or measure is, in English labels of the source's codes
    ("Lanes partially obstructed (temporary traffic lights)", "Speed limit 70 km/h")."""
    constriction = part.get("constriction")
    kind, detail = part.get("type", ""), part.get("detail")
    if constriction in CONSTRICTION_LABELS:
        label = CONSTRICTION_LABELS[constriction]
        # A measure's own code adds to it; a works code ("roadworks") does not.
        return f"{label} ({_words(detail)})" if kind not in WORKS and detail and detail != "other" else label
    if kind in WORKS:
        words = _words(detail)
        return "Road works" if words in ("", "other", "roadworks", "maintenance work", "construction work") else f"Road works ({words})"
    if kind == "SpeedManagement":
        limit = part.get("speed_limit")
        return f"Speed limit {limit.removesuffix('.0')} km/h" if limit else "Speed restriction"
    return (_words(detail) or _words(kind) or "road event").capitalize()


def _rank(part: dict[str, Any]) -> int:
    if part.get("constriction") in _CONSTRICTION_RANK:
        return _CONSTRICTION_RANK[part["constriction"]]
    if part.get("type") in WORKS:
        return 3
    return 5 if part.get("type") == "SpeedManagement" else 4


def stage_type(parts: list[dict[str, Any]]) -> str | None:
    """The REI type a stage's codes state (see the module notes)."""
    constrictions = {part.get("constriction") for part in parts}
    if "roadBlocked" in constrictions:
        if any(part.get("urgent") == "true" for part in parts):
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if constrictions & LANE_CONSTRICTIONS:
        return EventType.LANE_RESTRICTION.value
    if any(part.get("type") in WORKS for part in parts):
        return EventType.ROAD_WORKS.value
    return None


def _stated_periods(parts: list[dict[str, Any]]) -> str | None:
    """The sub-periods the records state, when they differ from the stage's overall period."""
    periods = _unique(period for part in parts for period in part.get("periods", []))
    overall = _unique(f"{part.get('start') or ''}/{part.get('end') or ''}" for part in parts)
    if not periods or set(periods) <= set(overall):
        return None
    return "Periods stated: " + "; ".join(period.replace("/", " – ") for period in periods[:12])


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works stage as REI's record; None when it has no id or no position."""
    parts = item.get("parts") or []
    if not item.get("id") or not parts:
        return None
    # The leading measure first (a closure before lanes, works, a speed limit): the
    # event is put at its first section's start.
    ordered = sorted(parts, key=_rank)
    sections = [
        (part, role, point, position)
        for part in ordered
        for role in ("from", "to", "point")
        if (point := part.get(role)) and (position := _position(point))
    ]
    if not sections:
        return None
    geometry = {"type": "Point", "coordinates": sections[0][3]}
    roads = _unique(name for _, _, point, _ in sections for name in point.get("names", []))
    labels = _unique(part_label(part) for part in ordered)
    starts = [moment for part in parts if (moment := _time(part.get("start")))]
    ends = [_time(part.get("end")) for part in parts]
    start = min(starts) if starts else None
    end = max(ends) if ends and all(ends) else None  # type: ignore[type-var]
    stage_title = item.get("title")
    named = stage_title if stage_title and stage_title.lower() not in DEFAULT_TITLES else None
    where = " / ".join(roads[:3])
    title = f"{labels[0]} – {where}" if where else labels[0]
    title = f"{title}: {named} (CITA)" if named else f"{title} (CITA)"
    directions = {part.get("direction") for part in parts}
    locations = []
    seen: set[tuple[str, tuple[float, ...]]] = set()
    for part, role, point, position in sections:
        name = " / ".join(point.get("names", [])) or "Luxembourg"
        key = (f"{role}:{name}", tuple(position))
        if key in seen:
            continue
        seen.add(key)
        locations.append(
            SourceLocation(
                name=f"{'From' if role == 'from' else 'To' if role == 'to' else 'At'}: {name}",
                kind={"from": "section start", "to": "section end"}.get(role, "point"),
                geometry={"type": "Point", "coordinates": position},
                direction=_words(part.get("direction")) if part.get("direction") not in (None, "unknown") else None,
                closure=part.get("constriction"),
            )
        )
    categories = _unique(" / ".join(code for code in (part.get("type"), part.get("detail")) if code) for part in parts)
    categories += _unique(part.get("constriction") for part in parts)
    structured = SourceEvent(
        event_type=stage_type(parts),
        category="; ".join(categories) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=locations,
        affected_road="; ".join(roads) or None,
        direction=EventDirection.BOTH_DIRECTIONS.value if directions == {"bothWays"} else None,
        attribution=ATTRIBUTION,
        stated_period=_stated_periods(parts),
        # A national feed: every stage is Luxembourg's.
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=item["id"],
        url=SOURCE_URL,
        title=title,
        # The comments in the publisher's words, then what each section's codes say.
        summary="\n".join(_unique([*item.get("comments", []), *labels])) or None,
        categories=categories,
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(item.get("version_time")),
    )


# --- the connector ----------------------------------------------------------------------


def fetch_stages(user_agent: str, *, client: httpx.Client | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Every stage of both files (a stage listed in both is taken once, from the current works)."""
    stages: list[dict[str, Any]] = []
    counts = {"situations": 0, "records": 0, "not_real": 0, "stages": 0, "listed_twice": 0}
    taken: set[str] = set()
    for url in ENDPOINTS:
        items, read = read_works(datex.fetch_bytes(url, user_agent, client=client), url)
        for key, value in read.items():
            counts[key] += value
        for item in items:
            if item["id"] in taken:
                counts["listed_twice"] += 1
                continue
            taken.add(item["id"])
            stages.append(item)
    counts["stages"] = len(stages)
    return stages, counts


class CitaRoadworksConnector:
    """Luxembourg's works programme: one record per works stage of the two files."""

    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        max_records: int | None = None,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        self.source = source
        self._user_agent = user_agent
        self.max_records = max_records
        self._client = client
        self._clock = clock
        self.counts: dict[str, int] = {}

    revision_key = staticmethod(datex.revision_key)

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        stages, counts = fetch_stages(self._user_agent, client=self._client)
        records = [record for item in stages if (record := to_record(item, now)) is not None]
        # Both files list every stage of a works site, ended stages included.
        self.observed_ids = {record.external_id for record in records}
        self.counts = {**counts, "kept": len(records)}
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
