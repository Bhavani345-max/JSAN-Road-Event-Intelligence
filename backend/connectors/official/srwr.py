"""Scottish Road Works Register (SRWR) disruptions export, Scotland (21 October 2026).

    GET https://downloads.srwr.scot/disruptions-export/api/v1/files/
        -> {"files": [{"name": "SRWRDisruptionsExport20261021.zip", ...}, ...]}  (the last 7 days)
    GET https://downloads.srwr.scot/disruptions-export/api/v1/file/<name>/
        -> {"url": "<a signed download link, valid about 10 minutes>"}
    GET <that link>
        -> a zip holding CurrentActivities.csv (about 25 MB), CompletedActivities.csv
           and PotentialBusConflicts.csv

The Office of the Scottish Road Works Commissioner publishes, once a day
(overnight), "a summary of the activities which could have a disruptive effect
on the road network" recorded on the SRWR by every Scottish road authority and
utility: road works, events and permissions. Each row of CurrentActivities.csv
is one phase of one activity, with its category ("Major", "Emergency",
"Event"), its traffic management ("Road Closure", "Lane Closure", "Portable
Traffic Lights (TTLS)"), its traffic impact ("Low" ... "Road Closure"), its
status ("Proposed", "In Progress"), a start and an end in UTC, the street and
town, a WGS 84 point (Latitude, Longitude) and its full shape in British
National Grid (EPSG:27700) as WKT. Fetched 21 October 2026: see
docs/data-sources/united-kingdom-connectors-2026-10-21.md.

The event's geometry is the export's own WGS 84 point. The British National
Grid shape is kept in the stored row, not converted: REI has no tested
OSGB36 transform. Rows whose traffic management says the carriageway is not
touched ("No Obstruction On C/W Or F/W", "Works Entirely On The Footway")
are not road events and are not taken. The type comes from the traffic
management (a closure or a lane restriction) and the category (works or an
event); an activity whose words state neither keeps no type, for the
reviewer. The export lists activities whose end has passed but that are not
yet closed; they are observed, not kept.

Licence: Open Government Licence v3.0 ("Open Data from the SRWR is available
under the Open Government Licence v3",
https://roadworks.scot/publications/scottish-road-works-register-open-data,
read 21 October 2026). No attribution wording is given, so the licence's own
default statement is used.
"""

import csv
import io
import re
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError, refusal_detail
from packages.cities import get_city
from packages.common.time import ensure_utc, utc_now
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

from . import common
from .common import content_key, fetch_json, select_for_run
from .feature_feed import clean, item_record

SOURCE_ID = "scotland-srwr-disruptions"
API_BASE = "https://downloads.srwr.scot/disruptions-export/api/v1"
ENDPOINT = f"{API_BASE}/files/"
FILE_ENDPOINT = f"{API_BASE}/file/"
SOURCE_URL = "https://roadworks.scot/publications/scottish-road-works-register-open-data"
ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0 "
    "(Scottish Road Works Register, Office of the Scottish Road Works Commissioner)."
)
MEMBER = "CurrentActivities.csv"
EXPORT_NAME = re.compile(r"^SRWRDisruptionsExport(\d{8})\.zip$")
# The zip was 6.9-7.0 MB and its CSV 25 MB from 15 to 21 October 2026.
MAX_ZIP_BYTES = common.MAX_RESPONSE_BYTES
MAX_CSV_BYTES = 200 * 1024 * 1024
# A row's British National Grid shape can be longer than the csv module's
# default 128 KB field limit (2 rows on 16 October 2026).
MAX_FIELD_CHARS = 16 * 1024 * 1024

# Traffic management that leaves the carriageway untouched: not a road event.
NOT_ON_THE_ROAD = frozenset({"No Obstruction On C/W Or F/W", "Works Entirely On The Footway"})
CLOSURES = frozenset({"Road Closure", "Slip Closure"})
LANE_RESTRICTIONS = frozenset(
    {"Lane Closure", "Hard Shoulder Closure", "Contraflow", "Road Narrowing (Two Way Working)"}
)
EMERGENCIES = frozenset({"Emergency", "Remedial Dangerous"})
# SRWR categories that are works on the road (the others are events,
# permissions, restrictions and requests).
WORKS = frozenset(
    {
        "Major",
        "Standard",
        "Minor With Excavation",
        "Minor Without Excavation",
        "Minor Mobile and Short Duration",
        "Emergency",
        "Urgent",
        "Remedial Other",
        "Remedial Dangerous",
        "Diversionary Works",
        "Works Licence",
    }
)


def srwr_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-kingdom")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Scottish Road Works Register disruptions",
        organization="Office of the Scottish Road Works Commissioner",
        authority_type="ROAD_WORKS_REGULATOR",
        source_tier=1,
        source_type=SourceType.CSV,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Scotland",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Daily zip of CSV files (SRWR disruptions export, WGS 84 points); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=24 * 60,
        language="en",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="srwr_disruptions_csv",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; the export is updated once a day overnight. Three requests a run.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence v3.0",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each current activity's row of the export as received.",
        notes=(
            "Road works, events and permissions on every Scottish road, from the register all road "
            "authorities and utilities must use; each a WGS 84 point with a start and an end. "
            "Fetched 21 October 2026. Rows that leave the carriageway untouched are not taken."
        ),
    )


def _time(value: Any) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _point(row: dict[str, Any]) -> dict[str, Any] | None:
    """The export's WGS 84 point, as GeoJSON."""
    try:
        latitude, longitude = float(row.get("Latitude") or ""), float(row.get("Longitude") or "")
    except ValueError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude, longitude) == (0, 0):
        return None
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _event_type(category: str, traffic_management: str) -> str | None:
    if category == "Event":
        return EventType.SPECIAL_EVENT.value
    if traffic_management in CLOSURES:
        if category in EMERGENCIES:
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if traffic_management in LANE_RESTRICTIONS:
        return EventType.LANE_RESTRICTION.value
    if category in WORKS:
        return EventType.ROAD_WORKS.value
    return None


def external_id_of(row: dict[str, Any]) -> str:
    """One phase of one activity: its reference and phase number."""
    reference, phase = clean(row.get("ActivityReference")), clean(row.get("PhaseNumber"))
    return f"{reference}#{phase}" if reference and phase else ""


def _text(value: Any) -> str:
    """A text field without the quotation marks some rows wrap it in."""
    return clean(value).strip('"').strip()


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    traffic_management = clean(row.get("TrafficManagement"))
    if traffic_management in NOT_ON_THE_ROAD:
        return None
    external_id = external_id_of(row)
    geometry = _point(row)
    if not external_id or geometry is None:
        return None
    category = clean(row.get("Category"))
    street, locality, town = (clean(row.get(key)) for key in ("Street", "Locality", "Town"))
    place = ", ".join(dict.fromkeys(part for part in (street, locality, town) if part)) or "Scotland"
    location, description = _text(row.get("Location")), _text(row.get("Description"))
    structured = SourceEvent(
        event_type=_event_type(category, traffic_management),
        category=" / ".join(
            part for part in (category, clean(row.get("LicenceType")), traffic_management) if part
        ),
        severity=clean(row.get("TrafficImpact")) or None,
        status=clean(row.get("ActivityStatus")) or None,
        start=_time(row.get("StartDateTimeUTC")),
        end=_time(row.get("EndDateTimeUTC")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="street",
                geometry=geometry,
                closure=traffic_management or None,
                reference=clean(row.get("UniqueStreetReferenceNumber")) or None,
            )
        ],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{traffic_management or category or 'Road works'}: {place}"[:300],
        summary=". ".join(part.rstrip(".") for part in (location, description) if part) or None,
        categories=[part for part in (category, traffic_management) if part],
        item=row,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(row.get("LastUpdatedDateTimeUTC")),
    )


# --- fetching -------------------------------------------------------------------------


def latest_export(listing: Any) -> str:
    """The newest daily zip the listing names."""
    files = listing.get("files") if isinstance(listing, dict) else None
    names = [
        name
        for item in files or []
        if isinstance(item, dict) and EXPORT_NAME.match(name := clean(item.get("name")))
    ]
    if not names:
        raise ConnectorError(f"{ENDPOINT} lists no disruptions export file")
    return max(names, key=lambda name: EXPORT_NAME.match(name).group(1))


def _download(url: str, user_agent: str, client: httpx.Client | None) -> bytes:
    """The zip behind the signed link (the link itself is never stored: it is a credential)."""
    try:
        response = common.get_with_retry(
            url,
            client=client,
            headers={"User-Agent": user_agent, "Accept": "application/zip"},
            timeout=120,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not download the SRWR export: {type(error).__name__}") from error
    if response.status_code in (429, 503):
        raise ConnectorError(
            f"The SRWR export download refused the request (HTTP {response.status_code}): "
            "rate limited; retried at the next run"
        )
    if response.status_code != 200:
        raise ConnectorError(
            f"Could not download the SRWR export: HTTP {response.status_code}" + refusal_detail(response)
        )
    if len(response.content) > MAX_ZIP_BYTES:
        raise ConnectorError("The SRWR export is larger than the allowed maximum")
    return response.content


def fetch_export(user_agent: str, *, client: httpx.Client | None = None) -> tuple[str, bytes]:
    """The name and bytes of the newest daily export."""
    name = latest_export(fetch_json(ENDPOINT, user_agent, client=client))
    link = fetch_json(f"{FILE_ENDPOINT}{name}/", user_agent, client=client)
    url = clean(link.get("url")) if isinstance(link, dict) else ""
    if not url.startswith("https://"):
        raise ConnectorError(f"{FILE_ENDPOINT}{name}/ gave no download link")
    return name, _download(url, user_agent, client)


@contextmanager
def _wide_csv_fields() -> Iterator[None]:
    previous = csv.field_size_limit(MAX_FIELD_CHARS)
    try:
        yield
    finally:
        csv.field_size_limit(previous)


def read_rows(archive: bytes) -> Iterator[dict[str, str]]:
    """CurrentActivities.csv's rows, read one at a time from the zip (never all in memory)."""
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as export:
            try:
                member = export.getinfo(MEMBER)
            except KeyError:
                raise ConnectorError(f"The SRWR export holds no {MEMBER}") from None
            if member.file_size > MAX_CSV_BYTES:
                raise ConnectorError(f"The SRWR export's {MEMBER} is larger than the allowed maximum")
            with export.open(member) as raw, _wide_csv_fields():
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                if not reader.fieldnames or "ActivityReference" not in reader.fieldnames:
                    raise ConnectorError(f"The SRWR export's {MEMBER} has no ActivityReference column")
                yield from reader
    except (zipfile.BadZipFile, csv.Error, UnicodeDecodeError) as error:
        raise ConnectorError(f"The SRWR export could not be read: {error}") from error


class SrwrDisruptionsConnector:
    """Scotland's daily disruptions export: one record per current activity phase."""

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

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("item", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        self.export_name, archive = fetch_export(self._user_agent, client=self._client)
        observed: set[str] = set()
        records: list[RawSourceRecord] = []
        for row in read_rows(archive):
            record = to_record(row, now)
            if record is None:
                continue
            # Listed by the source, kept or not.
            observed.add(record.external_id)
            if record.structured.end is not None and record.structured.end < now:
                continue  # ended but not yet closed on the register: not kept (and not held in memory)
            records.append(record)
        self.observed_ids = observed
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
