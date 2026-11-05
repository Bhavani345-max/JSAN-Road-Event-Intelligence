"""National Highways planned roadworks, England (5 November 2026).

    GET https://www.data.gov.uk/dataset/highways_agency_planned_roadworks
        -> the dataset page; its "Data links" table links one XML file per week
    GET https://s3.eu-west-2.amazonaws.com/webdata.nationalhighways.co.uk/ha-roadworks/nh_roadworks_YYYY_D_M.xml
        -> the newest file (day and month not zero-padded: nh_roadworks_2026_2_11.xml
           is the file of Monday 2 November 2026)

National Highways (the company that runs England's motorways and major A
roads) publishes "Planned road works on the National Highways road network"
on data.gov.uk: a new XML file each Monday, listing the works planned "up to
15 days in advance from the date of publication", which "could change right up
to point of go live" (the dataset's summary). Each `HE_PLANNED_WORKS` element
is one phase of one works: its event number (`NEW_EVENT_NUMBER`, e.g.
"00389408-001"), a start and an end (`SDATE`, `EDATE`, "24-JUL-2024 12:00"),
the expected delay (`EXPDEL`: "Slight (less than 10 mins)", "Moderate (10 - 30
mins)", "Severe (more than 30 mins)"), the description (the road, direction
and stretch on its first line, then what is done), the kind of works
(`CLOSURE_TYPE`: "Programmed Routine Works", "Area Schemes", "Major Schemes",
"Diversion/Alternate Route" ...), the roads (`ROAD_NUMBER`) and one centre
point on the British National Grid (`CENTRE_EASTING`, `CENTRE_NORTHING`,
EPSG:27700).

The newest file is found from the dataset page's links to National Highways'
own bucket, each dated by its words ("National Highways Road Network - 2
November 2026"), else by its name (an older file, nh_roadworks_2023_3_6.xml,
"6 March 2023", put the month first); when the page cannot be read or links no
file, the files of the last four Mondays are tried, newest first. data.gov.uk's robots.txt disallows only /v1; its CKAN API host
(ckan.publishing.service.gov.uk, robots.txt "Disallow: /") is never used. On
5 November 2026 the newest file was nh_roadworks_2026_2_11.xml (1.6 MB):
1,793 works phases, 533 in force at 12:00 UK time, 895 to come and 365 ended;
REI keeps 1,777 (527 in force, 887 to come, 363 ended: the run keeps the 1,414
in force or to come).

How REI reads one phase:

- **times**: `SDATE` and `EDATE` are UK local time (GMT in winter, BST in
  summer), written without an offset; works planned overnight start at 20:00
  and end at 06:00 in both seasons (5 November 2026 file), as local times do.
  They are read in Europe/London.
- **position**: the centre point, converted from the National Grid to WGS 84
  by connectors/official/osgb36.py (accurate to a few metres). A phase without
  a readable grid position is not kept (none on 5 November 2026). Only that
  point is drawn: the file gives no line.
- **type**, from the kind of works and the description's own words, read
  line by line: "Diversion/Alternate Route" is a diversion (a National
  Highways road used as the diversion route of someone else's closure); a
  line naming a carriageway, slip road, link road, roundabout or road closure
  ("carriageway closure", "Lane and slip road closure") is a planned road
  closure, or an emergency one when the kind of works starts "Emergency"
  (closure words after "no" or "off network" are not this road's); lane
  closures, narrow lanes, a contraflow, a hard shoulder closure, convoy
  working or temporary (2-way, multi-way) traffic signals are a lane
  restriction; a description stating only a diversion route ("Diversion Route
  only for off network road closure") is a diversion; anything else of a works
  kind ("... Works", "... Schemes", "... Renewals") is road works; the rest
  keeps no type, for the reviewer. The matched words stay in the category,
  beside the kind of works. On 5 November 2026: 960 lane restrictions, 689
  planned and 12 emergency road closures, 67 road works, 49 diversions.
- **not road events, not kept**: "Embargo" (a period when works are barred
  from a stretch, with possible delays from an event nearby), "Off Network"
  (works or an event off National Highways' roads, only signed from them) and
  "Abnormal Load Movements" (a load's journey along several motorways, put at
  one centre point): 15 of the 1,793 on 5 November 2026.
- an event number listed twice (one on 5 November 2026, the same phase with
  two publication dates) is kept once, as last published.

The file holds no contact or personal fields; descriptions name the body the
works are done for (a council, a utility, a developer), which is kept.

Licence: "UK Open Government Licence (OGL)", linked to the Open Government
Licence v3.0 (the dataset page's licence, read 5 November 2026); the licence's
own attribution statement is used.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from html import unescape
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

from . import osgb36
from .common import content_key, fetch_text, select_for_run
from .datex3_nl_lu import fetch_bytes
from .feature_feed import clean, item_record

SOURCE_ID = "gb-national-highways-roadworks"
DATASET_PAGE = "https://www.data.gov.uk/dataset/highways_agency_planned_roadworks"
FILE_BASE = "https://s3.eu-west-2.amazonaws.com/webdata.nationalhighways.co.uk/ha-roadworks/"
ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0 "
    "(National Highways, planned road works)."
)
LONDON = ZoneInfo("Europe/London")
# nh_roadworks_<year>_<day>_<month>.xml, on National Highways' own bucket only.
FILE_LINK = re.compile(r"^" + re.escape(FILE_BASE) + r"nh_roadworks_(\d{4})_(\d{1,2})_(\d{1,2})\.xml$")
_ANCHOR = re.compile(r"<a\s[^>]*?href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_WEEK_IN_WORDS = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    re.IGNORECASE,
)
# When the page cannot be read: the files of this many Mondays, newest first.
FALLBACK_MONDAYS = 4
_NAMESPACE = "{WebTeam}"
MONTHS = {name: number for number, name in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), start=1
)}  # fmt: skip
_STATED_TIME = re.compile(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+(\d{1,2}):(\d{2})$")

# Kinds of works that are not road events (see the module notes).
NOT_ROAD_EVENTS = frozenset({"Embargo", "Off Network", "Abnormal Load Movements"})
DIVERSION = "Diversion/Alternate Route"
_WORKS_KIND = re.compile(r"\b(works|schemes|renewals)\b", re.IGNORECASE)

# "carriageway closure", "Lane and slip road closure", "Carriageway, slip road and laneclosure".
_ROAD_PART = r"(?:carriageways?|(?:(?:entry|exit)\s+)?slips?(?:\s+roads?)?|link(?:\s+roads?)?|(?:full\s+)?road|roundabout|junction|motorway)"
_OTHER_PART = r"(?:lanes?(?:\s*\d)?|hard\s*-?\s*shoulders?|lay-?bys?)"
_PART = rf"(?:{_ROAD_PART}|{_OTHER_PART})"
_CLOSURE = re.compile(
    rf"(?<!partial\s)\b(?P<parts>{_PART}(?:\s*(?:,|\band\b|&)\s*{_PART})*)\s*(?:closures?|closed)\b",
    re.IGNORECASE,
)
_ROAD_PART_ONLY = re.compile(rf"^{_ROAD_PART}$", re.IGNORECASE)
_LIST_SEPARATOR = re.compile(r"\s*(?:,|\band\b|&)\s*", re.IGNORECASE)
_CLOSING_WORD = re.compile(r"\s*(?:closures?|closed)$", re.IGNORECASE)
_LANE_PART = re.compile(r"^(?:lanes?(?:\s*\d)?|hard\s*-?\s*shoulders?)$", re.IGNORECASE)
_LANE_MEASURES = re.compile(
    r"\bpartial\s+carriageway\s+closures?\b"
    r"|\blanes?\s+\d(?:\s*(?:,|and|&)\s*\d)*\s+(?:closures?|closed)\b"
    r"|\bnarrow(?:ed)?\s+lanes?\b"
    r"|\bcontra\s*-?\s*flow\b"
    r"|\blane\s+restrictions?\b"
    r"|\bsingle\s+lane\s+running\b"
    r"|\bconvoy\s+working\b"
    r"|\b(?:2|two|3|three|4|four|multi)\s*-?\s*way\s+(?:temporary\s+)?(?:traffic\s+)?(?:signals|lights)\b"
    r"|\b(?:temporary|portable)\s+(?:traffic\s+)?(?:signals|lights)\b"
    r"|\btraffic\s+(?:signals|lights)\b(?!\s+(?:renewal|maintenance|upgrade|replacement|installation|refurbishment))"
    r"|\bstop\s*/\s*go\b",
    re.IGNORECASE,
)
# Words just before a closure that make it not this road's: "no lane closure",
# "for off network road closure".
_NOT_THIS_ROAD = re.compile(r"\b(?:no|without|off[\s-]network)\s+$", re.IGNORECASE)
# A name just before a list whose first part is followed by a comma: that part ends
# the place's name ("to Eastern Roundabout, Lane closure", "to Clay Lane, Lane closure").
_NAME_BEFORE = re.compile(r"\b[A-Z][a-z]+\s+$")
# A diversion route the description states, without closing anything itself.
_DIVERSION_ROUTE = re.compile(r"\bdiversion(?:\s+route)?(?:\s+only)?\s+(?:for|due\s+to|on\s+behalf)\b", re.IGNORECASE)
BOTH_WAYS = re.compile(r"\bboth\s+directions\b|\bnorthbound\s+and\s+southbound\b|\beastbound\s+and\s+westbound\b", re.IGNORECASE)
_TITLE_PLACE_CHARS = 160


def national_highways_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-kingdom")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="National Highways planned roadworks (England)",
        organization="National Highways",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="England",
        city=country.id,
        source_url=DATASET_PAGE,
        endpoint=FILE_BASE,
        access_method=(
            "Weekly XML file (nh_roadworks_YYYY_D_M.xml) found from the data.gov.uk dataset page's "
            "links; British National Grid points; no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=24 * 60,
        language="en",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.TRAFFIC_DIVERSION.value,
        ),
        parser_type="national_highways_roadworks",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "None published; a new file each Monday, polled once a day (two requests: the dataset "
            "page and the newest file). data.gov.uk's robots.txt disallows only /v1; the CKAN API "
            "host is never used."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="UK Open Government Licence (OGL) v3.0, as the data.gov.uk dataset page states",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works phase's fields as published, its roads and its grid point.",
        notes=(
            "Planned works on England's motorways and major A roads, up to 15 days ahead, one "
            "British National Grid centre point each (converted to WGS 84, accurate to a few "
            "metres). Newest file on 5 November 2026: nh_roadworks_2026_2_11.xml, 1,793 phases "
            "(533 in force, 895 to come, 365 ended); embargoes, off-network notices and abnormal "
            "loads (15) are not road events and are not kept, and one event number listed twice is "
            "kept once: 1,777 kept (527 in force, 887 to come)."
        ),
    )


# --- reading the file -------------------------------------------------------------------


def stated_time(value: Any) -> datetime | None:
    """'24-JUL-2024 12:00', UK local time; None when it is not one."""
    match = _STATED_TIME.match(clean(value))
    if not match:
        return None
    day, month, year, hour, minute = match.groups()
    number = MONTHS.get(month.upper())
    if number is None:
        return None
    try:
        return datetime(int(year), number, int(day), int(hour), int(minute), tzinfo=LONDON)
    except ValueError:
        return None


def _local_time(value: Any) -> datetime | None:
    """PUBLISHED_DATE: '2024-07-24T11:00:45', UK local time."""
    try:
        moment = datetime.fromisoformat(clean(value))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=LONDON)


def _lines(description: str) -> list[str]:
    return [line for line in (clean(part) for part in description.splitlines()) if line]


def works_items(body: bytes, url: str) -> list[dict[str, Any]]:
    """Each works phase of a weekly file, as the fields it states."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise ConnectorError(f"{url} is not readable XML: {error}") from error
    if root.find(f"{_NAMESPACE}HE_PLANNED_ROADWORKS") is None:
        raise ConnectorError(f"{url} holds no HE_PLANNED_ROADWORKS list")
    items = []
    for works in root.iter(f"{_NAMESPACE}HE_PLANNED_WORKS"):
        centre = works.find(f".//{_NAMESPACE}EASTNORTH[@CENTRE_EASTING]")
        items.append(
            {
                **{key: value for key, value in works.attrib.items()},
                "ROADS": [
                    road
                    for element in works.iter(f"{_NAMESPACE}ROAD")
                    if (road := clean(element.get("ROAD_NUMBER")))
                ],
                "CENTRE_EASTING": centre.get("CENTRE_EASTING") if centre is not None else None,
                "CENTRE_NORTHING": centre.get("CENTRE_NORTHING") if centre is not None else None,
            }
        )
    return items


def once_each(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One item per event number: the one published last (the later in the file when equal)."""
    kept: dict[str, dict[str, Any]] = {}
    for item in items:
        number = clean(item.get("NEW_EVENT_NUMBER"))
        if not number:
            continue
        held = kept.get(number)
        if held is None or clean(item.get("PUBLISHED_DATE")) >= clean(held.get("PUBLISHED_DATE")):
            kept[number] = item
    return list(kept.values())


# --- what a phase is --------------------------------------------------------------------


def measures(description: str) -> tuple[list[str], list[str]]:
    """The closure words and the lane-restriction words the description states,
    read line by line (the first line names the place, the next ones the works)."""
    closures: list[str] = []
    lanes: list[str] = []
    for line in _lines(description):
        for match in _CLOSURE.finditer(line):
            before = line[max(0, match.start() - 16) : match.start()]
            if _NOT_THIS_ROAD.search(before):
                continue
            words = match.group(0)
            separator = _LIST_SEPARATOR.search(match.group("parts"))
            if separator and separator.group(0).strip() == "," and _NAME_BEFORE.search(before):
                # The first word ends a place's name, not a list of what is closed.
                words = words[separator.end() :]
            parts = _LIST_SEPARATOR.split(_CLOSING_WORD.sub("", words))
            if any(_ROAD_PART_ONLY.match(part.strip()) for part in parts):
                closures.append(clean(words))
            elif any(_LANE_PART.match(part.strip()) for part in parts):
                lanes.append(clean(words))
        for match in _LANE_MEASURES.finditer(line):
            if not _NOT_THIS_ROAD.search(line[max(0, match.start() - 16) : match.start()]):
                lanes.append(clean(match.group(0)))
    return _once(closures), _once(lanes)


def _once(words: list[str]) -> list[str]:
    """Each wording once, the first spelling kept ('road closure', 'Road closure')."""
    kept: dict[str, str] = {}
    for text in words:
        kept.setdefault(text.lower(), text)
    return list(kept.values())


def event_type(kind: str, closures: list[str], lanes: list[str], text: str = "") -> str | None:
    """The REI type of a phase, from its kind of works and the measures its description states."""
    if kind == DIVERSION:
        return EventType.TRAFFIC_DIVERSION.value
    if closures:
        if kind.lower().startswith("emergency"):
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if lanes:
        return EventType.LANE_RESTRICTION.value
    if _DIVERSION_ROUTE.search(text):
        # "Diversion Route only for off network road closure": the road carries a diversion.
        return EventType.TRAFFIC_DIVERSION.value
    if _WORKS_KIND.search(kind):
        return EventType.ROAD_WORKS.value
    return None


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works phase as REI's record; None when it is not a road event or has no position."""
    number = clean(item.get("NEW_EVENT_NUMBER"))
    kind = clean(item.get("CLOSURE_TYPE"))
    if not number or kind in NOT_ROAD_EVENTS:
        return None
    geometry = osgb36.point(item.get("CENTRE_EASTING"), item.get("CENTRE_NORTHING"))
    if geometry is None:
        return None
    description = str(item.get("DESCRIPTION") or "")
    lines = _lines(description)
    text = " ".join(lines)
    closures, lanes = measures(description)
    roads = list(dict.fromkeys(item.get("ROADS") or []))
    place = lines[0] if lines else ", ".join(roads) or "England"
    shown_place = place if len(place) <= _TITLE_PLACE_CHARS else place[: _TITLE_PLACE_CHARS - 1].rstrip() + "…"
    delay = clean(item.get("EXPDEL"))
    structured = SourceEvent(
        event_type=event_type(kind, closures, lanes, text),
        category=" / ".join(part for part in (kind, "; ".join(closures + lanes)) if part) or None,
        severity=delay or None,
        status=clean(item.get("STATUS")) or None,
        start=stated_time(item.get("SDATE")),
        end=stated_time(item.get("EDATE")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="works centre point",
                geometry=geometry,
                closure="; ".join(closures + lanes) or None,
                reference=", ".join(roads) or None,
            )
        ],
        affected_road="; ".join(roads) or None,
        direction=EventDirection.BOTH_DIRECTIONS.value if BOTH_WAYS.search(place) else None,
        attribution=ATTRIBUTION,
        # A national feed: every phase is England's.
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=number,
        url=DATASET_PAGE,
        title=f"{kind or 'Road works'}: {shown_place} (National Highways)",
        summary="\n".join([*lines, *([f"Expected delay: {delay}"] if delay else [])]) or None,
        categories=[part for part in (kind, *roads) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_local_time(item.get("PUBLISHED_DATE")),
    )


# --- finding and fetching the newest file -----------------------------------------------


def _week_of(href: str, text: str) -> date | None:
    """The week a link names: in its words ('... - 2 November 2026'), else in its file name (year, day, month)."""
    words = _WEEK_IN_WORDS.search(clean(unescape(re.sub(r"<[^>]+>", " ", text))))
    if words:
        try:
            return date(int(words.group(3)), MONTHS[words.group(2)[:3].upper()], int(words.group(1)))
        except ValueError:
            pass
    match = FILE_LINK.match(href)
    if match is None:
        return None
    year, day, month = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def newest_file(page: str) -> tuple[str, date]:
    """The address and week of the newest weekly file the dataset page links."""
    files = []
    for href, text in _ANCHOR.findall(page):
        address = unescape(href).strip()
        if FILE_LINK.match(address) and (week := _week_of(address, text)) is not None:
            files.append((week, address))
    if not files:
        raise ConnectorError(f"{DATASET_PAGE} links no National Highways roadworks file")
    week, address = max(files)
    return address, week


def file_for(week: date) -> str:
    """The address of a week's file: nh_roadworks_<year>_<day>_<month>.xml, not zero-padded."""
    return f"{FILE_BASE}nh_roadworks_{week.year}_{week.day}_{week.month}.xml"


def recent_mondays(today: date, count: int = FALLBACK_MONDAYS) -> list[date]:
    """The last `count` Mondays up to today, newest first."""
    latest = today - timedelta(days=today.weekday())
    return [latest - timedelta(weeks=weeks) for weeks in range(count)]


def fetch_newest(user_agent: str, *, client: httpx.Client | None = None, today: date) -> tuple[str, bytes]:
    """The address and bytes of the newest weekly file: from the dataset page's
    links, else the newest of the last few Mondays' files that answers."""
    try:
        address, _ = newest_file(fetch_text(DATASET_PAGE, user_agent, client=client))
    except ConnectorError as page_error:
        for week in recent_mondays(today):
            try:
                return file_for(week), fetch_bytes(file_for(week), user_agent, client=client)
            except ConnectorError:
                continue
        raise ConnectorError(
            f"No National Highways roadworks file found: {page_error}; and none of the last "
            f"{FALLBACK_MONDAYS} Mondays' files answered"
        ) from page_error
    return address, fetch_bytes(address, user_agent, client=client)


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now: datetime) -> tuple[str, list[dict[str, Any]]]:
    """The address of the newest weekly file and every works phase it lists."""
    address, body = fetch_newest(user_agent, client=client, today=now.astimezone(LONDON).date())
    return address, works_items(body, address)


class NationalHighwaysRoadworksConnector:
    """England's planned roadworks: one record per works phase of the newest weekly file."""

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

    @staticmethod
    def revision_key(raw: dict) -> str:
        # PUBLISHED_DATE changes when a phase is republished unchanged: not content.
        return content_key(raw.get("item", {}), frozenset({"PUBLISHED_DATE"}))

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        self.file_url, listed = fetch_works(self._user_agent, client=self._client, now=now)
        items = once_each(listed)
        records = [record for item in items if (record := to_record(item, now)) is not None]
        # The file lists every phase planned, in force or recently ended.
        self.observed_ids = {record.external_id for record in records}
        self.counts = {
            "listed": len(listed),
            "listed_twice": len(listed) - len(items),
            "not_road_events": sum(1 for item in items if clean(item.get("CLOSURE_TYPE")) in NOT_ROAD_EVENTS),
            "kept": len(records),
        }
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
