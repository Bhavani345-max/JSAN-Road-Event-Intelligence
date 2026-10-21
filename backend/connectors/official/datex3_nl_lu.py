"""Reading DATEX II version 3 situation publications: the Netherlands' NDW
feeds and Luxembourg's CITA feed (21 October 2026).

Both publish a `SituationPublication` (namespaces http://datex2.eu/schema/3/...):
situations, each holding one or more situation records (works, the closures
and lane measures they need, a speed limit, a diversion, an accident). A
situation is one event on the road, so REI keeps one record per situation:

- its **type** is that of the record that says most about the road, in the
  order REI's merge stage uses (a closure before the works needing it, before
  a lane measure, an accident, a diversion or a hazard); each record's own
  DATEX II type and detail stay in the category words;
- its **geometry** is the lines the source draws for the situation's records
  (a diversion's route is left out unless the situation is only a diversion),
  else the point it gives; GML `posList` values are read in latitude-longitude
  order (WGS 84, as both feeds declare), never projected or moved;
- its **period** runs from the earliest start the records state to the latest
  end, and has no end when any record states none. The source's own sub-periods
  (`validPeriod`: the nights the works happen) are kept in its words;
- records that describe traffic flow (`AbnormalTraffic`: queues) or extra
  capacity (`hardShoulderRunningInOperation`: a rush-hour lane opened) are not
  road events; a situation made only of them is not taken.

The evidence kept for each situation is a compact copy of the fields it
states (types, times, periods, comments, roads, lines as published). NDW's
comments often carry the contact details of the works' staff (names, phone
numbers, e-mail addresses): a line holding any of them is removed before
anything is kept, in the evidence too. ALERT-C location-table codes and a
diversion's own route line are not kept; the event's coordinates are. (NDW's
planned feed holds 14,000 situations in a run; the evidence is kept small so
that a run fits in a few hundred megabytes.)
"""

import gzip
import io
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError, refusal_detail
from packages.event_schema import EventDirection, EventType
from packages.source_models import RawSourceRecord, SourceEvent

from .common import UPCOMING_WINDOW, content_key, get_with_retry
from .feature_feed import clean, item_record

XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
# A compressed download larger than this is not a road-event feed (NDW's
# planned feed was 17 MB on 21 October 2026); unpacked, 1.5 GB.
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_XML_BYTES = 1536 * 1024 * 1024
UTC = ZoneInfo("UTC")

# --- fetching -----------------------------------------------------------------------


def fetch_bytes(url: str, user_agent: str, *, client: httpx.Client | None = None) -> bytes:
    """GET a feed as bytes (gzip files stay packed). A refusal (429, 503), a timeout
    or a non-200 is a ConnectorError (a dropped connection, timeout or 500/502/504
    is tried once more first, as for every official feed)."""
    try:
        response = get_with_retry(
            url,
            client=client,
            headers={"User-Agent": user_agent, "Accept": "application/xml, application/gzip"},
            timeout=120,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not fetch {url}: {error}") from error
    if response.status_code in (429, 503):
        raise ConnectorError(
            f"{url} refused the request (HTTP {response.status_code}): rate limited; "
            "retried at the next run"
        )
    if response.status_code != 200:
        raise ConnectorError(f"Could not fetch {url}: HTTP {response.status_code}" + refusal_detail(response))
    if len(response.content) > MAX_DOWNLOAD_BYTES:
        raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
    return response.content


class _CappedReader:
    """A stream that refuses to give more than `limit` bytes (a guard against a
    file that unpacks to far more than any feed)."""

    def __init__(self, stream: Any, limit: int, url: str) -> None:
        self._stream, self._limit, self._url, self._read = stream, limit, url, 0

    def read(self, size: int = -1) -> bytes:
        data = self._stream.read(size if size and size > 0 else 1 << 16)
        self._read += len(data)
        if self._read > self._limit:
            raise ConnectorError(f"{self._url} unpacks to more than the allowed maximum")
        return data


def iter_situations(body: bytes, url: str) -> Iterator[ET.Element]:
    """Each `situation` element of a publication, read as a stream.

    A gzip file is unpacked as it is read; each situation is dropped once the
    caller has read it, so only one is held at a time (NDW's planned feed
    unpacks to over 200 MB).
    """
    raw = gzip.GzipFile(fileobj=io.BytesIO(body)) if body[:2] == b"\x1f\x8b" else io.BytesIO(body)
    stream = _CappedReader(raw, MAX_XML_BYTES, url)
    stack: list[ET.Element] = []
    try:
        for event, element in ET.iterparse(stream, events=("start", "end")):
            if event == "start":
                stack.append(element)
                continue
            stack.pop()
            if _local(element.tag) != "situation":
                continue
            yield element
            if stack:
                stack[-1].remove(element)
            else:
                element.clear()
    except (ET.ParseError, EOFError, OSError) as error:
        raise ConnectorError(f"{url} did not return readable DATEX II XML: {error}") from error


# --- reading a situation ----------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None, path: str) -> str | None:
    if element is None:
        return None
    value = element.findtext(path)
    return clean(value) or None


def _values(element: ET.Element | None) -> list[str]:
    """The texts of a multilingual value list (`com:values/com:value`), kept as written."""
    if element is None:
        return []
    return [text for value in element.iter() if _local(value.tag) == "value" and (text := (value.text or "").strip())]


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Dutch and international phone numbers: 0 and nine digits, or +NN and eight to ten,
# with spaces, dashes, dots or slashes between. Not inside a project code (PR0212600…).
_PHONE = re.compile(
    r"(?<![\w+])\+\d{2}(?:[\s\-./]?\(0\))?(?:[\s\-./]?\d){8,10}(?!\d)"
    r"|(?<![\w+])0(?:[\s\-./]?\d){9}(?!\d)"
)
_CONTACT_WORDS = re.compile(
    r"(?i)\b(contact\w*|projectleider|telefoon\w*|tel\.|e-?mail|bij calamiteiten)"
)
REMOVED = "[contact details removed by REI]"


def without_contact_details(text: str | None) -> str | None:
    """The text with every line naming a contact (a person, a phone number, an
    e-mail address) replaced by a marker; None for nothing."""
    if not text:
        return None
    lines = []
    for line in text.splitlines():
        if _EMAIL.search(line) or _PHONE.search(line) or _CONTACT_WORDS.search(line):
            if not lines or lines[-1] != REMOVED:
                lines.append(REMOVED)
        else:
            lines.append(line.rstrip())
    result = "\n".join(lines).strip()
    return result or None


# The detail field of each DATEX II record type that names what it is.
PRIMARY_DETAIL = {
    "RoadOrCarriagewayOrLaneManagement": "roadOrCarriagewayOrLaneManagementType",
    "MaintenanceWorks": "roadMaintenanceType",
    "ConstructionWorks": "constructionWorkType",
    "SpeedManagement": "speedManagementType",
    "ReroutingManagement": "reroutingManagementType",
    "PublicEvent": "publicEventType",
    "VehicleObstruction": "vehicleObstructionType",
    "GeneralObstruction": "obstructionType",
    "AnimalPresenceObstruction": "animalPresenceType",
    "EnvironmentalObstruction": "environmentalObstructionType",
    "InfrastructureDamageObstruction": "infrastructureDamageType",
    "Accident": "accidentType",
    "AbnormalTraffic": "abnormalTrafficType",
    "GeneralNetworkManagement": "generalNetworkManagementType",
    "EquipmentOrSystemFault": "equipmentOrSystemFaultType",
}


class Shared(dict):
    """One copy of each repeated text (a type, a status, a time) while a
    publication is read: NDW's planned feed repeats them tens of thousands of times."""

    def __call__(self, text: str | None) -> str | None:
        return None if text is None else self.setdefault(text, text)


def _under(location: ET.Element | None, name: str) -> list[ET.Element]:
    return [node for node in location.iter() if _local(node.tag) == name] if location is not None else []


def _record_item(record: ET.Element, shared: Shared, local: Shared) -> dict[str, Any]:
    """The fields one situation record states, compactly (only those it gives).

    `shared` keeps one copy of repeated words across the publication, `local`
    of the lines and points the situation's records repeat.
    """
    kind = shared((record.get(XSI_TYPE) or "").rsplit(":", 1)[-1])
    details = {
        _local(child.tag): shared(clean(child.text))
        for child in record
        if _local(child.tag).endswith("Type") and _local(child.tag) != "causeType" and clean(child.text)
    }
    validity = record.find("{*}validity")
    spec = validity.find("{*}validityTimeSpecification") if validity is not None else None
    location = record.find("{*}locationReference")

    def periods(name: str) -> list[str]:
        return [
            shared(f"{_text(period, '{*}startOfPeriod') or ''}/{_text(period, '{*}endOfPeriod') or ''}")
            for period in (spec.findall("{*}" + name) if spec is not None else [])
        ]

    def texts(nodes: list[ET.Element]) -> list[str]:
        return [shared(clean(node.text)) for node in nodes if clean(node.text)]

    item: dict[str, Any] = {
        "id": record.get("id"),
        "type": kind,
        "detail": details.get(PRIMARY_DETAIL.get(kind, "")) or next(iter(details.values()), None),
        # Every detail, when the record gives more than one (a vehicle, a constriction).
        "details": details if len(details) > 1 else None,
        "source": shared(next(iter(_values(record.find("{*}source/{*}sourceName"))), None)),
        "start": shared(_text(spec, "{*}overallStartTime")),
        "end": shared(_text(spec, "{*}overallEndTime")),
        "periods": periods("validPeriod"),
        "exception_periods": periods("exceptionPeriod"),
        "status": shared(_text(record, "{*}operatorActionStatus")),
        "probability": shared(_text(record, "{*}probabilityOfOccurrence")),
        "compliance": shared(_text(record, "{*}complianceOption")),
        "created_from": _text(record, "{*}situationRecordCreationReference"),
        "cause": shared(_text(record, "{*}cause/{*}causeType")),
        "cause_text": shared(without_contact_details(" ".join(_values(record.find("{*}cause/{*}causeDescription"))))),
        # [comment type, text], with lines naming a contact removed.
        "comments": [
            [shared(_text(comment, "{*}commentType")), shared(text)]
            for comment in record.findall("{*}generalPublicComment")
            for value in _values(comment.find("{*}comment"))
            if (text := without_contact_details(value))
        ],
        "roads": [
            shared(road)
            for road in [_text(record, "{*}roadOrJunctionNumber"), *texts(_under(location, "roadName"))]
            if road
        ],
        "destinations": texts(_under(location, "roadDestination")),
        "location_descriptions": [
            shared(text) for node in _under(location, "locationDescription") for text in _values(node)
        ],
        "length_affected": texts(_under(location, "lengthAffected")),
        "carriageways": sorted({text for node in _under(location, "carriageway") if len(node) == 0 for text in texts([node])}),
        "lines": [
            {
                key: value
                for key, value in (
                    ("srs", shared(line.get("srsName"))),
                    ("dimension", shared(line.get("srsDimension"))),
                    ("posList", local(clean(line.findtext("{*}posList")))),
                )
                if value
            }
            for line in _under(location, "gmlLineString")
            if clean(line.findtext("{*}posList"))
        ],
        "points": [
            local(f"{clean(point.findtext('{*}latitude'))} {clean(point.findtext('{*}longitude'))}")
            for point in _under(location, "pointCoordinates")
        ],
        # A diversion's own route is not kept (REI does not draw it), only how many lines it has.
        "alternative_route_lines": sum(len(_under(route, "posList")) for route in record.findall("{*}alternativeRoute")) or None,
        "rerouting": [
            shared(text)
            for value in _values(record.find("{*}reroutingItineraryDescription"))
            if (text := without_contact_details(value))
        ],
        "speed_limit": shared(_text(record, "{*}temporarySpeedLimit")),
        "lanes_restricted": shared(_text(record, "{*}impact/{*}numberOfLanesRestricted")),
        "operational_lanes": shared(_text(record, "{*}impact/{*}numberOfOperationalLanes")),
        "delay": shared(_text(record, "{*}impact/{*}delays/{*}delayBand")),
        "roadwork_status": next(iter(texts(_under(record, "roadworkStatus"))), None),
        "hindrance_class": next(iter(texts(_under(record, "roadworkHindranceClass"))), None),
        "subjects": texts(_under(record, "subjectTypeOfWorks")),
        "links": [clean(node.text) for node in _under(record, "urlLinkAddress") if clean(node.text)],
    }
    return {key: value for key, value in item.items() if value not in (None, "", [], {})}


def situation_item(situation: ET.Element, shared: Shared | None = None) -> dict[str, Any]:
    """The fields a situation and its records state (the evidence REI keeps)."""
    shared = Shared() if shared is None else shared
    local = Shared()
    records = situation.findall("{*}situationRecord")
    item: dict[str, Any] = {
        "id": situation.get("id"),
        "severity": shared(_text(situation, "{*}overallSeverity")),
        "information_status": shared(_text(situation, "{*}headerInformation/{*}informationStatus")),
        # Bookkeeping: when the source last touched the situation (not content).
        "version_time": _text(situation, "{*}situationVersionTime")
        or max((value for r in records if (value := _text(r, "{*}situationRecordVersionTime"))), default=None),
        "record_versions": {r.get("id"): shared(r.get("version")) for r in records if r.get("id")},
        "records": [_record_item(record, shared, local) for record in records],
    }
    return {key: value for key, value in item.items() if value not in (None, "", [], {})}


# Fields of the evidence that are bookkeeping, not content (see `revision_key`).
BOOKKEEPING = frozenset({"version_time", "record_versions"})


def revision_key(raw: dict) -> str:
    return content_key(raw.get("item", {}), BOOKKEEPING)


# --- what a record is -------------------------------------------------------------------

CLOSURES = {
    "roadClosed": "Road closed",
    "carriagewayClosures": "Carriageway closed",
    "overnightClosures": "Closed overnight",
    "intermittentShortTermClosures": "Intermittent short closures",
}
LANES = {
    "laneClosures": "Lane closures",
    "narrowLanes": "Narrow lanes",
    "lanesDeviated": "Lanes deviated",
    "singleAlternateLineTraffic": "Alternating one-way traffic",
    "contraflow": "Contraflow",
    "useOfSpecifiedLanesOrCarriagewaysAllowed": "Specified lanes or carriageways in use",
    "useSpecifiedLanesOrCarriageways": "Use specified lanes or carriageways",
    "doNotUseSpecifiedLanesOrCarriageways": "Specified lanes or carriageways not to be used",
    "keepToTheLeft": "Keep to the left",
    "keepToTheRight": "Keep to the right",
    "newRoadworksLayout": "New roadworks layout",
    "clearALane": "Clear a lane",
    "clearASpecificLane": "Clear a specific lane",
}
# Extra capacity or a road reopened, not a restriction: not a road event.
NOT_RESTRICTIONS = frozenset({"hardShoulderRunningInOperation", "tidalFlowLaneInOperation", "roadCleared"})
# Traffic flow (queues, slow traffic), not a road event (as for Hamburg's feed).
TRAFFIC_FLOW = frozenset({"AbnormalTraffic"})
WORKS = frozenset({"MaintenanceWorks", "ConstructionWorks", "Roadworks"})
INCIDENTS = frozenset(
    {
        "Accident", "VehicleObstruction", "GeneralObstruction", "AnimalPresenceObstruction",
        "EnvironmentalObstruction", "InfrastructureDamageObstruction", "EquipmentOrSystemFault",
    }
)  # fmt: skip
HAZARDS = INCIDENTS - {"Accident"} | {
    "PoorEnvironmentConditions", "WeatherRelatedRoadConditions", "NonWeatherRelatedRoadConditions",
}  # fmt: skip
PLANNED_CAUSES = frozenset({"roadMaintenance", "constructionWork", "publicEvent"})
SPORTS = frozenset(
    {
        "sportsMeeting", "footballMatch", "bicycleRace", "cyclingRace", "athleticsMeeting", "ballGame",
        "boxingTournament", "cricketMatch", "golfTournament", "horseRacingMeeting", "iceHockeyGame",
        "motorSportRaceMeeting", "rugbyMatch", "skiJumpingEvent", "skiRace", "tennisTournament",
        "waterSportsMeeting", "winterSportsMeeting", "sportsEvent",
    }
)  # fmt: skip
PROCESSIONS = frozenset({"procession", "parade"})
BRIDGES = frozenset({"bridgeSwingInOperation", "bridgeLiftingInOperation", "bridgeClosed"})
# Which record leads a situation: as REI's merge stage ranks one event's rows.
RANK = {
    EventType.PLANNED_ROAD_CLOSURE.value: 0, EventType.EMERGENCY_ROAD_CLOSURE.value: 0,
    EventType.BRIDGE_TUNNEL_RESTRICTION.value: 1, EventType.ROAD_WORKS.value: 2,
    EventType.SPECIAL_EVENT.value: 2, EventType.MARATHON.value: 2, EventType.SPORTING_EVENT.value: 2,
    EventType.PUBLIC_PROCESSION.value: 2, EventType.LANE_RESTRICTION.value: 3,
    EventType.ACCIDENT.value: 4, EventType.TRAFFIC_DIVERSION.value: 5, EventType.ROAD_HAZARD.value: 6,
}  # fmt: skip


def _words(camel: str | None) -> str:
    """camelCase source words as plain words: 'bridgeSwingInOperation' -> 'bridge swing in operation'."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", camel or "").lower().strip()


def _role(record: dict[str, Any], *, planned: bool, incident: bool) -> tuple[str | None, str] | None:
    """The REI type and an English label of one record, in the source's terms;
    None when the record is not a road event.

    A closure is planned when the source says why and it is works or an event
    (its cause, the situation's works or event records, or a feed of planned
    works and events: `planned`); it is an emergency closure when the
    situation reports an accident, an obstruction or a fault; otherwise the
    source does not say, and the closure keeps its words with no type.
    """
    kind, detail = record.get("type", ""), record.get("detail")
    if kind in TRAFFIC_FLOW:
        return None
    if kind == "RoadOrCarriagewayOrLaneManagement":
        if detail in NOT_RESTRICTIONS:
            return None
        if detail in CLOSURES:
            if planned or record.get("cause") in PLANNED_CAUSES:
                return EventType.PLANNED_ROAD_CLOSURE.value, CLOSURES[detail]
            if incident:
                return EventType.EMERGENCY_ROAD_CLOSURE.value, CLOSURES[detail]
            return None, CLOSURES[detail]
        if detail in LANES:
            return EventType.LANE_RESTRICTION.value, LANES[detail]
        return None, (_words(detail) or "road or lane management").capitalize()
    if kind in WORKS:
        words = _words(detail)
        return EventType.ROAD_WORKS.value, "Road works" if words in ("", "other", "maintenance work", "construction work", "roadworks") else f"Road works ({words})"
    if kind == "PublicEvent":
        words = _words(detail)
        label = "Public event" if words in ("", "other") else f"Public event ({words})"
        if detail == "marathon":
            return EventType.MARATHON.value, label
        if detail in SPORTS:
            return EventType.SPORTING_EVENT.value, label
        if detail in PROCESSIONS:
            return EventType.PUBLIC_PROCESSION.value, label
        return EventType.SPECIAL_EVENT.value, label
    if kind == "Accident":
        return EventType.ACCIDENT.value, "Accident"
    if kind in HAZARDS:
        words = _words(detail)
        name = {"VehicleObstruction": "Vehicle obstruction", "EquipmentOrSystemFault": "Equipment or system fault"}.get(kind, "Obstruction")
        if kind == "VehicleObstruction" and detail == "brokenDownVehicle":
            return EventType.ROAD_HAZARD.value, "Broken-down vehicle"
        return EventType.ROAD_HAZARD.value, name if words in ("", "other") else f"{name} ({words})"
    if kind == "ReroutingManagement":
        return EventType.TRAFFIC_DIVERSION.value, "Diversion"
    if kind == "GeneralNetworkManagement" and detail in BRIDGES:
        return EventType.BRIDGE_TUNNEL_RESTRICTION.value, _words(detail).capitalize()
    if kind == "SpeedManagement":
        limit = record.get("speed_limit")
        return None, f"Speed limit {limit.removesuffix('.0')} km/h" if limit else "Speed restriction"
    return None, (_words(detail) or _words(kind) or "road event").capitalize()


# --- geometry ---------------------------------------------------------------------------

_LAT_LON = ("WGS84", "4326")


def _positions(text: str, srs: str | None, dimension: str | None) -> list[list[float]] | None:
    """A GML posList as [longitude, latitude] positions; None if it is not WGS 84 or not readable."""
    name = (srs or "WGS84").upper().replace(" ", "")
    if "CRS84" in name:
        lon_first = True
    elif any(marker in name for marker in _LAT_LON):
        lon_first = False
    else:
        return None  # another reference system: REI does not project coordinates
    try:
        step = int(dimension or 2)
        values = [float(value) for value in text.split()]
    except ValueError:
        return None
    if step not in (2, 3) or not values or len(values) % step:
        return None
    positions = []
    for index in range(0, len(values), step):
        first, second = values[index], values[index + 1]
        lon, lat = (first, second) if lon_first else (second, first)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        positions.append([lon, lat])
    return positions


def _point(text: str) -> list[float] | None:
    try:
        lat, lon = (float(value) for value in text.split())
    except ValueError:
        return None
    return [lon, lat] if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def _geometry(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The lines the records draw, else the first point they give.

    A line drawn twice (by several records, or once per direction with the
    same positions in reverse order) is kept once.
    """
    lines: list[list[list[float]]] = []
    seen: set[str] = set()
    drawn: set[tuple[tuple[float, float], ...]] = set()
    for record in records:
        for line in record.get("lines", []):
            if line["posList"] in seen:
                continue
            seen.add(line["posList"])
            positions = _positions(line["posList"], line.get("srs"), line.get("dimension"))
            if not positions or len(positions) < 2:
                continue
            shape = tuple((lon, lat) for lon, lat in positions)
            if shape in drawn or shape[::-1] in drawn:
                continue
            drawn.add(shape)
            lines.append(positions)
    if len(lines) == 1:
        return {"type": "LineString", "coordinates": lines[0]}
    if lines:
        return {"type": "MultiLineString", "coordinates": lines}
    for record in records:
        for text in record.get("points", []):
            if (point := _point(text)) is not None:
                return {"type": "Point", "coordinates": point}
    return None


# --- times ------------------------------------------------------------------------------


def _time(value: str | None, zone: ZoneInfo) -> datetime | None:
    """A DATEX II date-time; one written without an offset is read in the source's zone."""
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=zone)


def _period_text(records: list[dict[str, Any]], zone: ZoneInfo) -> str | None:
    """The sub-periods the records state (e.g. the nights works happen), in UTC."""
    periods: set[tuple[datetime, datetime]] = set()
    for record in records:
        for period in record.get("periods", []):
            start, _, end = period.partition("/")
            first, last = _time(start, zone), _time(end, zone)
            if first and last:
                periods.add((first.astimezone(UTC), last.astimezone(UTC)))
    if len(periods) < 2:
        return None
    ordered = sorted(periods)

    def written(first: datetime, last: datetime) -> str:
        if first.date() == last.date():
            return f"{first:%Y-%m-%d %H:%M}–{last:%H:%M}"
        return f"{first:%Y-%m-%d %H:%M} – {last:%Y-%m-%d %H:%M}"

    shown = "; ".join(written(*period) for period in ordered[:12])
    more = f"; and {len(ordered) - 12} more" if len(ordered) > 12 else ""
    return f"{len(ordered)} periods stated (UTC): {shown}{more}"


def period_of(records: list[dict[str, Any]], zone: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """From the earliest stated start to the latest stated end; no end if any record states none."""
    starts = [moment for record in records if (moment := _time(record.get("start"), zone))]
    ends = [_time(record.get("end"), zone) for record in records]
    start = min(starts) if starts else None
    end = max(ends) if ends and all(ends) else None  # type: ignore[type-var]
    return start, end


def in_run_window(start: datetime | None, end: datetime | None, now: datetime) -> bool:
    """The run window of `select_for_run`: in effect now, or starting within UPCOMING_WINDOW."""
    return (end is None or end >= now) and (start is None or start <= now + UPCOMING_WINDOW)


# --- the record REI keeps ---------------------------------------------------------------

# Comments that only number a measure ("Beperking 1", "Omleiding A", "Fase 2").
_LABEL_ONLY = re.compile(r"(?i)^(beperking|omleiding|fietsomleiding|afsluiting|fase)\s*\w{0,3}$")
# The comment order of a summary: warnings to road users first.
_COMMENT_ORDER = {"warning": 0, "other": 1, None: 2, "roadworksName": 2, "internalNote": 3}
BOTH_WAYS = frozenset({"weg dicht in beide richtingen"})


def authority_name(source: str | None) -> str | None:
    """A source name as written, or the full name it gives in brackets
    ('MN-Z [RWS Midden-Nederland District Zuid]' -> 'RWS Midden-Nederland District Zuid')."""
    if not source:
        return None
    match = re.search(r"\[([^\]]+)\]", source)
    return clean(match.group(1)) if match else clean(source)


def _unique(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def situation_record(
    item: dict[str, Any],
    *,
    source_id: str,
    url: str,
    attribution: str,
    default_authority: str,
    zone: ZoneInfo,
    retrieved_at: datetime,
    planned_feed: bool = False,
) -> RawSourceRecord | None:
    """One situation as REI's record of it; None when none of its records is a road event.

    `planned_feed`: the publication lists planned works and events only (NDW's
    planned feed), so each of its closures is a planned one.
    """
    records = item.get("records", [])
    kinds = {record.get("type") for record in records}
    planned = planned_feed or bool(kinds & (WORKS | {"PublicEvent"}))
    incident = bool(kinds & INCIDENTS)
    roles = [
        (record, role)
        for record in records
        if (role := _role(record, planned=planned, incident=incident)) is not None
    ]
    if not roles or not item.get("id"):
        return None
    # A closure leads even when the source does not say why the road is closed.
    roles.sort(
        key=lambda pair: 0
        if pair[0].get("type") == "RoadOrCarriagewayOrLaneManagement" and pair[0].get("detail") in CLOSURES
        else RANK.get(pair[1][0] or "", 8)
    )
    lead, (event_type, label) = roles[0]
    counted = [record for record, _ in roles]
    # The diversion's route is where traffic is sent, not where the event is.
    on_the_road = [record for record in counted if record.get("type") != "ReroutingManagement"]
    geometry = _geometry(on_the_road) or _geometry(counted)
    start, end = period_of(counted, zone)

    roads = _unique(road for record in counted for road in record.get("roads", []))
    destinations = _unique(text for record in counted for text in record.get("destinations", []))
    # Each comment is [its type, its text].
    comments = sorted(
        (comment for record in counted for comment in record.get("comments", [])),
        key=lambda comment: _COMMENT_ORDER.get(comment[0], 2),
    )
    texts = _unique(
        line.strip()
        for _, text in comments
        for line in text.splitlines()
        if line.strip() and line.strip() != REMOVED and not _LABEL_ONLY.match(line.strip())
    )
    notes = [text for kind, text in comments if kind in ("internalNote", "roadworksName")]
    authority = authority_name(lead.get("source")) or default_authority
    if roads:
        where = " / ".join(roads[:3]) + (f" ({' / '.join(destinations[:3])})" if destinations else "")
    else:
        note = next((line.strip() for text in notes for line in text.splitlines() if line.strip() and line.strip() != REMOVED), "")
        where = note if len(note) <= 120 else note[:119].rstrip() + "…"
    title = f"{label} – {where} ({authority})" if where else f"{label} ({authority})"
    summary = "\n".join(
        _unique(
            [
                *texts,
                *(record.get("cause_text") for record in counted),
                *(text for record in counted for text in record.get("rerouting", [])),
            ]
        )[:20]
    ) or None
    categories = _unique(
        " / ".join(part for part in (record.get("type"), record.get("detail")) if part) for record in counted
    )
    lengths = _unique(value for record in counted for value in record.get("length_affected", []))
    both_ways = any(line.lower() in BOTH_WAYS for line in texts)
    # No separate affected locations: the situation's geometry is the event's own,
    # and a copy per location would double what a run of NDW's planned feed
    # (14,000 situations) holds in memory.
    structured = SourceEvent(
        event_type=event_type,
        category="; ".join(categories) or None,
        severity=item.get("severity"),
        status=" / ".join(part for part in (lead.get("status"), lead.get("roadwork_status")) if part) or None,
        start=start,
        end=end,
        geometry=geometry,
        affected_road="; ".join(roads) or None,
        direction=EventDirection.BOTH_DIRECTIONS.value if both_ways else None,
        attribution=attribution,
        stated_period=_period_text(counted, zone),
        stated_distance="; ".join(f"{value} m" for value in lengths) or None,
        stated_distance_m=float(lengths[0]) if len(lengths) == 1 and _is_number(lengths[0]) else None,
        # A national feed: a situation without coordinates is still the country's.
        covers_city=True,
    )
    return item_record(
        source_id=source_id,
        external_id=item["id"],
        url=url,
        title=title,
        summary=summary,
        categories=categories,
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(item.get("version_time"), zone),
    )


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def read_publication(
    body: bytes,
    url: str,
    *,
    now: datetime,
    build: Callable[[dict[str, Any]], RawSourceRecord | None],
    skip: Callable[[dict[str, Any]], bool] = lambda item: False,
) -> tuple[list[RawSourceRecord], set[str], dict[str, int]]:
    """The records of a publication in the run window, the ids of every situation
    taken, and counts of what was read.

    A situation that is not real (a test or an exercise), that `skip` leaves out,
    or that holds no road event is not taken; one taken but outside the run
    window (ended) is reported as observed and not built.
    """
    records: list[RawSourceRecord] = []
    observed: set[str] = set()
    counts = {"situations": 0, "not_real": 0, "skipped": 0, "not_road_events": 0, "outside_window": 0}
    shared = Shared()
    for situation in iter_situations(body, url):
        counts["situations"] += 1
        status = (_text(situation, "{*}headerInformation/{*}informationStatus") or "real").lower()
        if status != "real":
            counts["not_real"] += 1
            continue
        item = situation_item(situation, shared)
        if skip(item):
            counts["skipped"] += 1
            continue
        record = build(item)
        if record is None:
            counts["not_road_events"] += 1
            continue
        observed.add(record.external_id)
        if not in_run_window(record.structured.start, record.structured.end, now):
            counts["outside_window"] += 1
            continue
        records.append(record)
    return records, observed, counts


__all__ = [
    "BOOKKEEPING",
    "fetch_bytes",
    "iter_situations",
    "period_of",
    "read_publication",
    "revision_key",
    "situation_item",
    "situation_record",
    "without_contact_details",
]
