"""Mumbai Traffic Police notifications: an AUTHORITATIVE_OFFICIAL source for Mumbai.

    GET https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm

Verified on 7 and 8 October 2026 without a key: a static HTML table ("Public
Notice List") of the 50 newest notifications issued by the Mumbai Traffic
Police under section 115 of the Motor Vehicles Act, newest first. Each row
has the notice number ("Notification No 209/DCP/West/Traffic/Temp/2026"),
its date, its validity ("Till Next Order" on every row), a subject, a
one-line English summary and a link to the signed order as a PDF. The PDFs
are scanned Marathi images with no text layer: they are kept as the evidence
link, not read (no OCR is done; see docs/data-sources/mumbai-traffic-police-notifications.md).

The listing carries no coordinates. Roads, junctions and dates are read only
from the English summary's own words: road names as written, dates written
as day/month/year, a distance as stated ("100 meter"). The event is located
by a place the summary names, at that place's position on OpenStreetMap,
marked approximate; a notice naming no known place stays unlocated for a
reviewer. A notice that is only about parking (no parking, pay-and-park,
odd-even parking) states no change to the road network, so it is stored as
evidence but not taken as a road event.

Terms: no terms are published on this host (robots.txt 404). The departmental
website's policy says material "may be reproduced free of charge after taking
proper permission by sending a mail to us", with the source acknowledged.
Whether that applies to this listing is unresolved and is recorded as such.
"""

import re
from datetime import datetime
from typing import Any
from urllib.parse import quote, unquote, urljoin

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import start_of_day, utc_now
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
from services.extraction.road_mentions import find_road_mentions

from .common import fetch_text, select_for_run
from .stated_text import ascii_digits, distance_in_metres, parse_dmy, stated_dates, stated_distance

SOURCE_ID = "mumbai-traffic-police-notifications"
ENDPOINT = "https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm"
BASE_URL = "https://mtperp.mahatrafficechallan.gov.in/"
ATTRIBUTION = "Source: Mumbai Traffic Police notifications (Public Notice List, Brihanmumbai Police)."

_ROW = re.compile(r"<tr[^>]*class=\"data\"[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_HREF = re.compile(r"href=\"([^\"]*GetPublicNotice[^\"]*)\"", re.IGNORECASE)
_NOTICE_ID = re.compile(r"GetPublicNotice/(\d+)/")
_NUMBER = re.compile(r"No\.?\s*(\d+)", re.IGNORECASE)
_YEAR = re.compile(r"/(\d{4})\s*$")

# What the notice says it is, in the order a more specific word wins. Words
# that name a kind of event come before words that name a measure.
_EVENT_TYPE_WORDS: tuple[tuple[str, EventType], ...] = (
    (r"\bmarathon\b|\bhalf[- ]marathon\b|\brun\b", EventType.MARATHON),
    (r"\bprocession|\bvisarjan\b|\bimmersion\b|\brally\b|\bmorcha\b|\bjuloos\b", EventType.PUBLIC_PROCESSION),
    (r"\bv?vip\b|\bvvip\b|\bpresident\b|\bprime minister\b", EventType.VIP_MOVEMENT),
    (r"\bbridge\b|\brob\b|\bflyover\b|\bsubway\b|\bunderpass\b", EventType.BRIDGE_TUNNEL_RESTRICTION),
    (r"\bexcavation\b|\btrench\b|\brepair|\bwork\b|\bworks\b|\bconstruction\b|\bre-?surfacing\b", EventType.ROAD_WORKS),
    (r"\bdiversion|\bdivert|\balternat(?:e|ive) routes?\b|\bchanges? in (?:transportation|traffic) routes?\b", EventType.TRAFFIC_DIVERSION),
    (r"\bclosed\b|\bclosure\b|\bclose\b|\bshut\b", EventType.PLANNED_ROAD_CLOSURE),
    (r"\bno (?:right|left|u)[- ]turn\b|\bturn(?:ing)? (?:is )?(?:prohibited|banned|closed)\b", EventType.TURN_RESTRICTION),
    (r"\bone[- ]way\b|\bone way\b|\blane\b", EventType.LANE_RESTRICTION),
)  # fmt: skip
_EVENT_TYPES = [(re.compile(pattern, re.IGNORECASE), kind) for pattern, kind in _EVENT_TYPE_WORDS]

_ALTERNATE = re.compile(r"^alt[ea]r", re.IGNORECASE)
# The order's PDF file name, as the division saved it ("52. Dadar - angarki
# sankashti chaturthi notification", "Notification No 189, Ghatkopar Div 1").
# Half of them name the locality or division the order is for.
_FILE_NOISE = re.compile(
    r"^\d+\.\s*|\(\d+\)|\b(?:compressed|signed|copy|pdf)\b|[_\-]+|\s\d+$", re.IGNORECASE
)


def file_name_place(href: str | None) -> str | None:
    """The words of the order's file name, or None when it has none worth reading."""
    if not href:
        return None
    name = unquote(href.rsplit("/", 1)[-1])
    name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    # Strip the upload stamp: "202610050000_823622_<file name>".
    name = re.sub(r"^\d{12}_\d+_", "", name)
    name = " ".join(_FILE_NOISE.sub(" ", name).split())
    return name if re.search(r"[A-Za-z]{3}", name) else None
# A notice about where vehicles may stand, not about whether they may move.
_PARKING = re.compile(r"\bparking\b|\bpay\s*(?:and|&)\s*park\b|\bodd[- ]even\b", re.IGNORECASE)
# Words that say the road network itself is changed.
_ROAD_MEASURE = re.compile(
    r"\bclos|\bshut\b|\bdiver|\balternat|\broute|\bprohibit|\brestrict|\bbanned?\b|\bno entry\b"
    r"|\bone[- ]?way\b|\bbridge\b|\brob\b|\bflyover\b|\bheavy\b|\bprocession|\bmarathon\b|\brally\b"
    r"|\bv?vip\b|\bexcavation\b|\bwork|\bturn\b|\blane\b|\btraffic arrangement|\btraffic restriction",
    re.IGNORECASE,
)


def mumbai_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("mumbai")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Mumbai Traffic Police notifications",
        organization="Mumbai Traffic Police (Traffic Control Branch, Brihanmumbai Police)",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.HTML,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://trafficpolicemumbai.maharashtra.gov.in/en/",
        endpoint=ENDPOINT,
        access_method=(
            "Public web page (static HTML table of the 50 newest notifications, with the "
            "signed orders as scanned PDFs); no key, no login"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.TRAFFIC_DIVERSION.value,
            EventType.PUBLIC_PROCESSION.value,
            EventType.MARATHON.value,
            EventType.VIP_MOVEMENT.value,
            EventType.BRIDGE_TUNNEL_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.LANE_RESTRICTION.value,
            EventType.TURN_RESTRICTION.value,
        ),
        parser_type="mumbai_public_notice_list",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published (checked 7 October 2026). One request per run, every six hours.",
        terms_status=TermsStatus.REVIEW_REQUIRED,
        licence=(
            "No terms on the host. Departmental website policy: material may be reproduced "
            "free of charge after permission by mail, with the source acknowledged "
            "(trafficpolicemumbai.maharashtra.gov.in/en/website-policies/)"
        ),
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=False,
        provides_direction=False,
        real_time=False,
        evidence_retention=(
            "Each table row exactly as published (notice number, date, validity, subject, "
            "English summary, PDF link), with a SHA-256 hash. The PDF itself is linked, not stored."
        ),
        notes=(
            "Traffic notifications of the Mumbai Traffic Police, verified on 7 and 8 October "
            "2026 (50 newest of 1,605 since 2009; 207 issued in 2026 to 5 October). No "
            "coordinates: roads and dates are read from the English summary's own words and "
            "the event is placed at a named place, marked approximate. PDFs are scanned "
            "Marathi, not read. Parking-only notices are evidence, not events. "
            + ("Polled every six hours." if scheduled else "Test phase: run by hand, not on a schedule.")
        ),
    )


def _clean(value: Any) -> str:
    return " ".join(html_to_text(str(value or "")).split())


def event_type_for(text: str) -> EventType | None:
    """The kind of event the notice's own words state, or None when they do not say."""
    for pattern, kind in _EVENT_TYPES:
        if pattern.search(text):
            return kind
    return None


def is_parking_only(text: str) -> bool:
    """A notice about parking that states no change to the road network."""
    return bool(_PARKING.search(text)) and not _ROAD_MEASURE.search(text)


def _short_number(notice_number: str) -> str:
    number = _NUMBER.search(notice_number)
    year = _YEAR.search(notice_number)
    if number and year:
        return f"{number.group(1)}/{year.group(1)}"
    return notice_number


def parse_listing(page: str, retrieved_at: datetime) -> list[RawSourceRecord]:
    """Every notification row of the Public Notice List page, as a record."""
    rows = _ROW.findall(page)
    if not rows:
        raise ConnectorError(f"{ENDPOINT} did not contain the Public Notice List table")
    records = []
    for row in rows:
        cells = _CELL.findall(row)
        if len(cells) < 7:
            continue
        record = to_record(cells, retrieved_at)
        if record is not None:
            records.append(record)
    return records


def structured_for(
    subject: str, notice: str, valid_till: str, href: str | None
) -> SourceEvent | None:
    """What a row states about the road, from its own words; None for a parking-only notice."""
    notice = ascii_digits(notice)
    text = " . ".join(part for part in (subject, notice) if part)
    if is_parking_only(text):
        return None
    dates = stated_dates(notice, subject, zone=get_city("mumbai").tz)
    # "Alternate Route" is a measure, not a road; the listing spells it many ways.
    roads = [road for road in find_road_mentions(subject, notice) if not _ALTERNATE.match(road)]
    file_place = file_name_place(href)
    return SourceEvent(
        event_type=(kind.value if (kind := event_type_for(text)) else None),
        category=subject or None,
        status=valid_till or None,
        start=dates.start if dates else None,
        end=dates.end if dates else None,
        locations=[
            SourceLocation(name=road, kind="road", reference="named in the notification")
            for road in roads
        ]
        + (
            [
                SourceLocation(
                    name=file_place,
                    kind="file name",
                    reference="the file name of the order's PDF, as published",
                    fallback=True,
                )
            ]
            if file_place
            else []
        ),
        affected_road="; ".join(roads) or None,
        attribution=ATTRIBUTION,
        stated_period=dates.text if dates else None,
        stated_distance=(distance := stated_distance(notice, subject)),
        stated_distance_m=distance_in_metres(distance),
        covers_city=True,
    )


def rebuild_structured(raw: dict) -> SourceEvent | None:
    """The row's structured reading, redone from the row as stored.

    Reprocessing calls this so that stored notices are read with the current
    rules (a better reading of the file name, say), from the evidence itself.
    """
    row = raw.get("row") if isinstance(raw, dict) else None
    if not row:
        return None
    return structured_for(
        row.get("subject") or "", row.get("notice") or "", row.get("valid_till") or "", row.get("pdf_href")
    )


def to_record(cells: list[str], retrieved_at: datetime) -> RawSourceRecord | None:
    """One table row: Sr. No. | Notice Id | Date | Valid Till | Subject | Notice | Download."""
    notice_number = _clean(cells[1])
    issued = parse_dmy(_clean(cells[2]))
    valid_till = _clean(cells[3])
    subject = _clean(cells[4])
    notice = ascii_digits(_clean(cells[5]))
    href_match = _HREF.search(cells[6])
    href = href_match.group(1) if href_match else None
    if not notice_number and not href:
        return None
    id_match = _NOTICE_ID.search(href or "")
    external_id = id_match.group(1) if id_match else notice_number
    # The link exactly as published, byte for byte: the file names carry
    # spaces and characters that must be percent-encoded as they are.
    url = urljoin(BASE_URL, quote(href, safe="/")) if href else None
    published_at = start_of_day(issued, get_city("mumbai").tz) if issued else None

    title = subject or notice or "Traffic notification"
    if len(title) > 120:
        title = title[:117].rstrip() + "..."
    title = f"{title} (Notification {_short_number(notice_number)})" if notice_number else title
    summary = notice if notice and notice != subject else None
    text = " . ".join(part for part in (subject, notice) if part)

    structured = structured_for(subject, notice, valid_till, href)

    raw = {
        "row": {
            "notice_number": notice_number,
            "date": _clean(cells[2]),
            "valid_till": valid_till,
            "subject": subject,
            "notice": _clean(cells[5]),
            "pdf_href": href,
        },
        "summary_html": summary or "",
        "content_html": "",
        "categories": ["Mumbai Traffic Police notification"],
        "acquired_from": "Mumbai Traffic Police Public Notice List (HTML table)",
    }
    if structured is not None:
        raw["source_event"] = structured.model_dump(mode="json")
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=url,
        title=title,
        summary=summary,
        content_text=None,
        categories=["Mumbai Traffic Police notification"],
        published_at=published_at,
        retrieved_at=retrieved_at,
        raw=raw,
        content_hash=sha256_hex("\n".join([notice_number, _clean(cells[2]), subject, notice, href or ""])),
        structured=structured,
    )


class MumbaiTrafficPoliceConnector:
    """Reads the Public Notice List page. One request per run."""

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
        # The page lists the 50 newest notices, not the ones in force, so a
        # notice dropping off it says nothing about the order ending: no
        # `observed_ids` is reported, and nothing is ever counted missing.

    @staticmethod
    def rebuild_structured(raw: dict) -> SourceEvent | None:
        return rebuild_structured(raw)

    def fetch(self) -> list[RawSourceRecord]:
        page = fetch_text(ENDPOINT, self._user_agent, client=self._client)
        retrieved_at = self._clock()
        records = parse_listing(page, retrieved_at)
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start if record.structured else None,
            end=lambda record: record.structured.end if record.structured else None,
            # Newest notices first.
            order=lambda record: record.published_at or retrieved_at,
            limit=self.max_records,
        )
