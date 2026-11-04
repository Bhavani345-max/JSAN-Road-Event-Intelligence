"""Trafikverket road traffic situations, Sweden (4 November 2026, decision 0053).

    POST https://api.trafikinfo.trafikverket.se/v2/data.json
        <REQUEST><LOGIN authenticationkey="…" />
          <QUERY objecttype="Situation" namespace="Road.TrafficInfo" schemaversion="1.6">
            <FILTER><NE name="Deviation.Suspended" value="true" /></FILTER> …

Trafikverket (the Swedish Transport Administration) publishes the road traffic
situations of Sweden: works, lane closures, closed roads, diversions, speed and
weight limits, obstructions, accidents and events, on state roads and on the
streets of the municipalities that report to it (Göteborgs Stad, Stockholms
Stad, Uppsala kommun …, named in each part's `Creator`). A situation is one
event on the road; its parts (`Deviation`) are the measures it brings, each
with a start, an end ("ValidUntilFurtherNotice": none), a WGS 84 line or point,
a location description, a Swedish message and Trafikverket's own DATEX II terms
for what it is (`MessageTypeValue`: MaintenanceWorks,
RoadOrCarriagewayOrLaneManagement …; `MessageCodeValue`: roadworks,
laneClosures, roadClosed …). On 4 November 2026: 3,462 situations, every part
with a start and all but the ferry notices with a geometry.

REI keeps one record per situation, read by the same rules as the DATEX II
feeds of the Netherlands, Luxembourg and Norway (connectors/official/
datex3_nl_lu.py), from Trafikverket's own DATEX II terms: no mapping of REI's
is put between them. The Swedish words (message type and code, message, location,
severity, restriction, limit) are kept as written; titles are English labels of
the DATEX II terms with the source's location description. A situation made only
of ferry notices (TransitInformation) is not a road event.

Suspended parts: 2,070 of the 3,462 situations (60 %) had every part marked
`Suspended`, mostly long works periods with nothing happening on the road now
(DATEX II's validity status "suspended": currently inactive). REI shows what is
in force or upcoming, so the query asks for situations with a part that is not
suspended, and suspended parts are left out (KEEP_SUSPENDED). A situation the
source switches on again is in the next poll; one switched off is absent from it.
This also cuts each download from 13 MB to under 5 MB.

Access needs Trafikverket's free API key (TRAFIKVERKET_API_KEY), given after
registration at https://data.trafikverket.se/get-started; without it the source
is listed as needing access and never fetched. The key is sent in the request
body and never written to a log or an error message. Licence: CC0 1.0
(the API page's licence link: https://creativecommons.org/publicdomain/zero/1.0/).
Lines naming a contact (phone, e-mail, "kontakt", "telefon") are removed before
anything is kept (none on 4 November 2026).
"""

import re
import time as clock_time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
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
    SourceType,
    TermsStatus,
)

from . import datex3_nl_lu as datex
from .common import select_for_run
from .feature_feed import FeatureFeedConnector, clean

SOURCE_ID = "se-trafikverket-situations"
ENDPOINT = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SOURCE_URL = "https://www.trafikverket.se/e-tjanster/trafikverkets-oppna-api-for-trafikinformation/"
SCHEMA_VERSION = "1.6"
LICENCE = "CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/), as Trafikverket's API page states"
ATTRIBUTION = "Trafikverket (Swedish Transport Administration), road traffic information, CC0"
STOCKHOLM = ZoneInfo("Europe/Stockholm")
# Leave out parts the source marks suspended (inactive now); see the module notes.
KEEP_SUSPENDED = False
# A ferry service notice: not an event on the road.
NOT_ROAD_EVENTS = frozenset({"TransitInformation"})
EVENTS = (
    EventType.PLANNED_ROAD_CLOSURE.value,
    EventType.EMERGENCY_ROAD_CLOSURE.value,
    EventType.LANE_RESTRICTION.value,
    EventType.ROAD_WORKS.value,
    EventType.TRAFFIC_DIVERSION.value,
    EventType.ACCIDENT.value,
    EventType.ROAD_HAZARD.value,
    EventType.SPECIAL_EVENT.value,
)
# The SWEREF 99 TM copies of each shape are not read (REI does not project) and not fetched.
_EXCLUDED = (
    "Deviation.Geometry.SWEREF99TM",
    "Deviation.Geometry.Point.SWEREF99TM",
    "Deviation.Geometry.Line.SWEREF99TM",
)
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
RETRY_DELAY_SECONDS = 5.0

# Swedish contact details: an e-mail address, a phone number (+46 or a leading 0,
# then seven to nine digits with spaces or dashes), or a word naming a contact.
_PHONE_SE = re.compile(r"(?<![\w+])(?:\+46[\s-]?|0)\d{1,3}(?:[\s-]?\d){5,8}(?![\d:])")
_CONTACT_WORDS_SE = re.compile(r"(?i)\b(tel\.|telefon\w*|e-?post\w*|kontaktperson\w*|mobil(?:nr|nummer)\w*)")
_SPEED = re.compile(r"(?i)^hastighet:\s*(\d{2,3})\s*km/h$")
_WKT = re.compile(r"(?i)^\s*(POINT|LINESTRING|MULTILINESTRING)\s*\((.*)\)\s*$", re.S)


def trafikverket_source(*, scheduled: bool, connected: bool = True) -> SourceDefinition:
    country = get_city("sweden")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Trafikverket road traffic situations, Sweden",
        organization="Trafikverket (Swedish Transport Administration)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="National",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method=(
            "POST of an XML query (object type Situation, namespace Road.TrafficInfo, schema 1.6) "
            "with an authentication key; JSON answer, WGS 84"
        ),
        integration_status=IntegrationStatus.CONNECTED if connected else IntegrationStatus.REQUIRES_ACCESS,
        active=scheduled and connected,
        polling_frequency_minutes=30,
        language="sv",
        events_supported=EVENTS,
        parser_type="trafikverket_situation",
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        rate_limit=(
            "None published; Trafikverket contacts users whose traffic exceeds its documented limits. "
            "Polled every 30 minutes (one request, under 5 MB)."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=LICENCE,
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=True,
        evidence_retention=(
            "Each situation's parts as the fields they state (Trafikverket's DATEX II type and code, the "
            "Swedish message type, code and message, times, severity, road, location description, "
            "restriction, limit, creator, WGS 84 line or point); lines naming a contact person, phone "
            "number or e-mail address are removed. Suspended parts are not fetched."
        ),
        notes=(
            "Sweden's road traffic situations from Trafikverket's open API: works, lane closures, closed "
            "roads, diversions, limits, obstructions, accidents and events, on state roads and the streets "
            "of reporting municipalities (Gothenburg, Stockholm, Uppsala …). Fetched with the key on "
            "4 November 2026: 3,462 situations, 1,391 with a part not suspended (kept). One record per "
            "situation; ferry notices left out. Needs TRAFIKVERKET_API_KEY (free registration)."
            if connected
            else "Needs TRAFIKVERKET_API_KEY (free registration at https://data.trafikverket.se/get-started); "
            "without it the source is not fetched."
        ),
    )


def query_body(api_key: str) -> bytes:
    """The request: every situation with a part that is not suspended, without SWEREF 99 TM copies."""
    key = api_key.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    excluded = "".join(f"<EXCLUDE>{name}</EXCLUDE>" for name in _EXCLUDED)
    wanted = "" if KEEP_SUSPENDED else '<FILTER><NE name="Deviation.Suspended" value="true" /></FILTER>'
    return (
        f'<REQUEST><LOGIN authenticationkey="{key}" />'
        f'<QUERY objecttype="Situation" namespace="Road.TrafficInfo" schemaversion="{SCHEMA_VERSION}">'
        f"{wanted}{excluded}</QUERY></REQUEST>"
    ).encode("utf-8")


def _post(api_key: str, user_agent: str, client: httpx.Client | None) -> httpx.Response:
    """POST once, and once more after a dropped connection, a timeout or a 5xx."""
    options = {
        "content": query_body(api_key),
        "headers": {"User-Agent": user_agent, "Content-Type": "application/xml", "Accept": "application/json"},
        "timeout": 90,
    }
    for attempt in (1, 2):
        try:
            response = (client or httpx).post(ENDPOINT, **options)
        except httpx.TransportError as error:
            if attempt == 2:
                raise ConnectorError(f"Could not fetch {ENDPOINT}: {type(error).__name__}") from None
        else:
            if response.status_code < 500 or attempt == 2:
                return response
        clock_time.sleep(RETRY_DELAY_SECONDS)
    raise AssertionError("unreachable")


def _error_message(response: httpx.Response) -> str:
    try:
        result = response.json()["RESPONSE"]["RESULT"][0]["ERROR"]
        return clean(result.get("MESSAGE"))[:200]
    except (ValueError, KeyError, IndexError, TypeError):
        return ""


def fetch_payload(api_key: str, user_agent: str, *, client: httpx.Client | None = None) -> list[dict]:
    """Trafikverket's situations, as it gives them."""
    response = _post(api_key, user_agent, client)
    if response.status_code in (401, 403):
        raise ConnectorError(
            f"{ENDPOINT} refused the key (HTTP {response.status_code}): {_error_message(response) or 'not authorised'}"
        )
    if response.status_code == 429:
        raise ConnectorError(f"{ENDPOINT} refused the request (HTTP 429): rate limited; retried at the next run")
    if response.status_code != 200:
        raise ConnectorError(f"{ENDPOINT} answered HTTP {response.status_code}: {_error_message(response)}")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ConnectorError(f"{ENDPOINT} answered with more than {MAX_RESPONSE_BYTES} bytes")
    try:
        result = response.json()["RESPONSE"]["RESULT"][0]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise ConnectorError(f"{ENDPOINT} did not return Trafikverket's RESPONSE/RESULT") from error
    if "ERROR" in result:
        raise ConnectorError(f"{ENDPOINT} answered with an error: {_error_message(response)}")
    situations = result.get("Situation", [])
    if not isinstance(situations, list):
        raise ConnectorError(f"{ENDPOINT} did not return a list of situations")
    return [situation for situation in situations if isinstance(situation, dict)]


def without_contact_details(text: str | None) -> str | None:
    """The text with each line naming a contact replaced by a marker; None for nothing."""
    if not text:
        return None
    lines = []
    for line in str(text).splitlines():
        if datex._EMAIL.search(line) or _PHONE_SE.search(line) or _CONTACT_WORDS_SE.search(line):
            if not lines or lines[-1] != datex.REMOVED:
                lines.append(datex.REMOVED)
        else:
            lines.append(line.rstrip())
    return "\n".join(lines).strip() or None


def _number(value: str) -> str:
    return repr(float(value))


def _shape(geometry: Any) -> dict[str, Any]:
    """A part's WGS 84 shape in the form the DATEX II reader takes: lines as
    longitude-latitude position lists (CRS84), a point as 'latitude longitude'."""
    if not isinstance(geometry, dict):
        return {}
    line = (geometry.get("Line") or {}).get("WGS84") if isinstance(geometry.get("Line"), dict) else None
    point = (geometry.get("Point") or {}).get("WGS84") if isinstance(geometry.get("Point"), dict) else None
    shape: dict[str, Any] = {}
    try:
        if line and (match := _WKT.match(line)):
            kind, body = match.group(1).upper(), match.group(2)
            parts = re.findall(r"\(([^()]*)\)", body) if kind == "MULTILINESTRING" else [body]
            lines = []
            for part in parts:
                positions = [position.split() for position in part.split(",") if position.strip()]
                if len(positions) >= 2 and all(len(position) >= 2 for position in positions):
                    lines.append(
                        {
                            "srs": "CRS84",
                            "posList": " ".join(f"{_number(p[0])} {_number(p[1])}" for p in positions),
                        }
                    )
            if lines:
                shape["lines"] = lines
        point = point or geometry.get("WGS84")
        if point and (match := _WKT.match(point)) and match.group(1).upper() == "POINT":
            longitude, latitude = match.group(2).split()[:2]
            shape["points"] = [f"{_number(latitude)} {_number(longitude)}"]
    except (TypeError, ValueError, IndexError):
        return {}
    return shape


def _schedule(value: Any) -> tuple[list[str], list[str]]:
    """The periods the part states ("start/end") and its daily hours ("19:00-06:00")."""
    periods, hours = [], []
    for entry in value if isinstance(value, list) else []:
        if not isinstance(entry, dict):
            continue
        start, end = clean(entry.get("StartOfPeriod")), clean(entry.get("EndOfPeriod"))
        if start and end:
            periods.append(f"{start}/{end}")
        for daily in entry.get("RecurringTimePeriodOfDay") or []:
            if isinstance(daily, dict) and daily.get("Start") and daily.get("End"):
                hours.append(f"{clean(daily['Start'])}-{clean(daily['End'])}")
    return periods, hours


def deviation_item(deviation: dict[str, Any]) -> dict[str, Any]:
    """One part of a situation as the fields it states (REI's evidence of it)."""
    limit = clean(deviation.get("TemporaryLimit"))
    speed = _SPEED.match(limit) if limit else None
    location = clean(deviation.get("LocationDescriptor"))
    road_number = clean(deviation.get("RoadNumber"))
    road_name = clean(deviation.get("RoadName"))
    periods, hours = _schedule(deviation.get("Schedule"))
    comments = [
        [None, text]
        for value in (deviation.get("Header"), deviation.get("Message"))
        if (text := without_contact_details(clean(value) or None))
    ]
    severity = clean(deviation.get("SeverityText"))
    item: dict[str, Any] = {
        "id": clean(deviation.get("Id")) or None,
        # Trafikverket's own DATEX II terms for what the part is.
        "type": clean(deviation.get("MessageTypeValue")) or None,
        "detail": clean(deviation.get("MessageCodeValue")) or None,
        # The same in Trafikverket's Swedish words.
        "message_type": clean(deviation.get("MessageType")) or None,
        "message_code": clean(deviation.get("MessageCode")) or None,
        # "Objektet är orsaken till situationen": the part that is the cause.
        "main": deviation.get("ManagedCause") is True,
        "start": clean(deviation.get("StartTime")) or None,
        "end": None if deviation.get("ValidUntilFurtherNotice") else clean(deviation.get("EndTime")) or None,
        "until_further_notice": deviation.get("ValidUntilFurtherNotice") is True,
        "created": clean(deviation.get("CreationTime")) or None,
        "severity": severity or None,
        "severity_code": deviation.get("SeverityCode"),
        "source": clean(deviation.get("Creator")) or None,
        "road_number": road_number or None,
        "road_name": road_name or None,
        # Where the source says the part is: its location description names the road and places.
        "roads": [location or road_name or road_number] if location or road_name or road_number else [],
        "direction": clean(deviation.get("AffectedDirection")) or None,
        "restriction": clean(deviation.get("TrafficRestrictionType")) or None,
        "lanes_affected": str(deviation["NumberOfLanesRestricted"])
        if deviation.get("NumberOfLanesRestricted") is not None
        else None,
        "limit": limit or None,
        "speed_limit": speed.group(1) if speed else None,
        "periods": periods,
        "daily_hours": hours,
        "county": deviation.get("CountyNo"),
        "web_link": clean(deviation.get("WebLink")) or None,
        "comments": comments,
        **_shape(deviation.get("Geometry")),
    }
    return {key: value for key, value in item.items() if value not in (None, "", [], {}, False)}


def _squeezed(text: str) -> str:
    """For comparing road names: 'E 45' and 'E45' are one road."""
    return re.sub(r"\s+", "", text).casefold()


def situation_items(situations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each situation with the parts REI keeps, in the order the feed gives them."""
    items = []
    for situation in situations:
        situation_id = clean(situation.get("Id"))
        if not situation_id or situation.get("Deleted") is True:
            continue
        deviations = [
            deviation
            for deviation in situation.get("Deviation") or []
            if isinstance(deviation, dict) and (KEEP_SUSPENDED or deviation.get("Suspended") is not True)
        ]
        records = []
        for deviation in deviations:
            record = deviation_item(deviation)
            if record not in records:
                records.append(record)
        if not records:
            continue
        # A part naming only the road ("Väg 879") another part's location description
        # already holds ("Väg 879 från Salungen till Flytjärn …") adds nothing to where.
        places = [_squeezed(record["roads"][0]) for record in records if record.get("roads")]
        for record in records:
            road = _squeezed((record.get("roads") or [""])[0])
            if road and any(road != place and road in place for place in places):
                del record["roads"]
        main = next((record for record in records if record.get("main")), records[0])
        # The parts of a situation often repeat its line or point: each shape is kept
        # once, on the part that is the cause or else the first part that gives it.
        seen: list[Any] = [main[key] for key in ("lines", "points") if key in main]
        for record in records:
            if record is main:
                continue
            for key in ("lines", "points"):
                if key in record:
                    if record[key] in seen:
                        del record[key]
                    else:
                        seen.append(record[key])
        worst = max(records, key=lambda record: record.get("severity_code") or 0)
        items.append(
            {
                "id": situation_id,
                "severity": worst.get("severity"),
                # Bookkeeping: when the source last changed the situation (not content).
                "version_time": clean(situation.get("ModifiedTime") or situation.get("VersionTime")) or None,
                "records": records,
            }
        )
    return [{key: value for key, value in item.items() if value not in (None, "", [], {})} for item in items]


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One situation as REI's record; None when it is only ferry notices."""
    records = item.get("records", [])
    if not records or all(record.get("type") in NOT_ROAD_EVENTS for record in records):
        return None
    return datex.situation_record(
        item,
        source_id=SOURCE_ID,
        url=SOURCE_URL,
        attribution=ATTRIBUTION,
        default_authority="Trafikverket",
        zone=STOCKHOLM,
        retrieved_at=retrieved_at,
    )


class TrafikverketSituationsConnector(FeatureFeedConnector):
    to_record = staticmethod(to_record)
    revision_key = staticmethod(datex.revision_key)

    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        api_key: str,
        max_records: int | None = None,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        super().__init__(source, user_agent, max_records=max_records, client=client, clock=clock)
        self._api_key = api_key

    def fetch(self) -> list[RawSourceRecord]:
        """As FeatureFeedConnector.fetch, with the key."""
        now = self._clock()
        items = situation_items(fetch_payload(self._api_key, self._user_agent, client=self._client))
        records = [record for item in items if (record := to_record(item, now)) is not None]
        self.observed_ids = {record.external_id for record in records}
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )

