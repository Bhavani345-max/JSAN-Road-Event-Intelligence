"""Bengaluru Traffic Police website: an AUTHORITATIVE_OFFICIAL source for Bengaluru.

    GET https://btp.karnataka.gov.in/en

Verified on 7 and 8 October 2026 without a key: the home page is static HTML
whose "UPCOMING EVENTS / PRESS NOTES" panel lists planned works and events,
each one line in a fixed form:

    Department Work : White Topping Work at New Diagonal Road, Jayanagar.
    near 7th Main Road, Byrasandra, ... | Start : 00:00 Hrs 07-10-2026 and End : 04-01-2027

The kinds seen are "Department Work", "Public Event" and "Private Event".
Items have no id, link, PDF or coordinates; most say "near None". The list
is the whole current list (40 items on 7 October), repeated in a scrolling
card and a "View All" dialog; the dialog is read.

What the line states is kept as it is: the kind as the source's category,
the start (date and time) and end (a date) as whole days in Bengaluru's time
zone, the "near" address as a named location. An item is located by a place
it names, at that place's position on OpenStreetMap, marked approximate;
one that names no known place stays unlocated for a reviewer. An item with
neither a description nor a place ("None near None") states nothing a
reviewer could check and is stored as evidence only.

The same page's "TRAFFIC ALERTS" panel (congestion points with coordinates,
breakdowns, "construction occurred at") is transient and is not read: whether
REI should carry such alerts is the user's decision (docs/cities/bengaluru-source-research.md).

Terms: the Centre for e-Governance copyright policy says information "can be
re-published in any media form free of any charge only with prior permission"
by email. That is recorded, not resolved.
"""

import re
from datetime import datetime, time
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import end_of_day, utc_now
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

from .common import fetch_text, select_for_run
from .stated_text import parse_dmy

SOURCE_ID = "bengaluru-traffic-police-website"
ENDPOINT = "https://btp.karnataka.gov.in/en"
ATTRIBUTION = "Source: Bengaluru Traffic Police (btp.karnataka.gov.in), Upcoming Events / Press Notes."

_MODAL = re.compile(
    r"id=\"UPCOMING_EVENTS\".*?<div class=\"modal-body[^\"]*\">(.*?)</div>", re.DOTALL
)
_CARD = re.compile(r"<div class=\"scroll-content2\">(.*?)</div>", re.DOTALL)
_ITEM = re.compile(
    r"^(?P<kind>[A-Za-z][A-Za-z ]{2,40}?)\s*:\s*(?P<body>.*?)\s*\|\s*Start\s*:\s*"
    r"(?P<start_time>\d{1,2}:\d{2})\s*Hrs\s*(?P<start_date>\d{2}-\d{2}-\d{4})\s*and\s*End\s*:\s*"
    r"(?P<end_date>\d{2}-\d{2}-\d{4})\s*$",
    re.DOTALL,
)

# The source's kinds and the REI event type each states.
EVENT_TYPE_BY_KIND = {
    "department work": EventType.ROAD_WORKS,
    "public event": EventType.SPECIAL_EVENT,
    "private event": EventType.SPECIAL_EVENT,
}


def bengaluru_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("bengaluru")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Bengaluru Traffic Police website: upcoming events and works",
        organization="Bengaluru Traffic Police, Karnataka State Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.HTML,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://btp.karnataka.gov.in/en",
        endpoint=ENDPOINT,
        access_method=(
            "Public web page: the home page's 'Upcoming Events / Press Notes' list, "
            "server-rendered HTML; no key, no login"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(EventType.ROAD_WORKS.value, EventType.SPECIAL_EVENT.value),
        parser_type="btp_upcoming_events",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published (checked 7 October 2026). One request per run, every six hours.",
        terms_status=TermsStatus.REVIEW_REQUIRED,
        licence=(
            "Centre for e-Governance copyright policy: re-publication free of charge only "
            "with prior permission by email (site footer policy)"
        ),
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=False,
        provides_direction=False,
        real_time=False,
        evidence_retention=(
            "Each list line exactly as published, with a SHA-256 hash; the line's own "
            "text is the item's identity (the source gives none)."
        ),
        notes=(
            "Planned works and events the Bengaluru Traffic Police list on their home page, "
            "verified 7 and 8 October 2026 (40 items: department works, public and private "
            "events, each with a start and end date; 34 of 40 name no place). No coordinates: "
            "an item is placed at a named place, marked approximate. The page's transient "
            "traffic alerts are not read. The force's actual advisories are published on X "
            "only, which REI does not read. "
            + ("Polled every six hours." if scheduled else "Test phase: run by hand, not on a schedule.")
        ),
    )


def _clean(value: Any) -> str:
    return " ".join(html_to_text(str(value or "")).split())


def _none(value: str) -> str | None:
    value = value.strip().strip(".").strip()
    return None if not value or value.lower() == "none" else value


# The administrative tail of a geocoded address ("Bengaluru South City
# Corporation, Bengaluru, Bengaluru Urban, Karnataka, 560011, India"), which
# names no place an event could be at.
_ADDRESS_TAIL = re.compile(
    r"city corporation|^none$|^bengaluru( urban)?$|^bangalore$|^karnataka$|^india$|^\d{6}$|^\s*$",
    re.IGNORECASE,
)


def place_part(address: str | None) -> str | None:
    """The address up to its administrative tail: "Kalidasa Road, Gandhinagar"."""
    if not address:
        return None
    kept = []
    for part in address.split(","):
        if _ADDRESS_TAIL.search(part.strip()):
            break
        kept.append(part.strip())
    return ", ".join(kept) or None


def parse_items(page: str) -> list[str]:
    """The event lines of the page, each as plain text, de-duplicated in order."""
    match = _MODAL.search(page) or _CARD.search(page)
    if not match:
        raise ConnectorError(f"{ENDPOINT} did not contain the Upcoming Events list")
    lines = []
    for part in re.split(r"<br\s*/?>\s*<br\s*/?>", match.group(1)):
        text = _clean(part)
        if text and text not in lines:
            lines.append(text)
    return lines


def to_record(line: str, retrieved_at: datetime) -> RawSourceRecord | None:
    """One list line, or None for one that is not in the known form or states nothing."""
    match = _ITEM.match(line)
    if not match:
        return None
    kind = " ".join(match.group("kind").split())
    body = match.group("body")
    # "<description> near <address>": the last " near " separates them.
    description, _, near = body.rpartition(" near ")
    if not _:
        description, near = body, ""
    description, near = _none(description), place_part(_none(near))
    if description is None and near is None:
        return None
    zone = get_city("bengaluru").tz
    start_date, end_date = parse_dmy(match.group("start_date")), parse_dmy(match.group("end_date"))
    hours, minutes = (int(part) for part in match.group("start_time").split(":"))
    start = (
        datetime.combine(start_date, time(hours % 24, minutes % 60), tzinfo=zone) if start_date else None
    )
    end = end_of_day(end_date, zone) if end_date else None

    locations = []
    if near:
        locations.append(SourceLocation(name=near, kind="address", reference="the item's 'near' address"))
    structured = SourceEvent(
        event_type=(kind_type.value if (kind_type := EVENT_TYPE_BY_KIND.get(kind.lower())) else None),
        category=kind,
        start=start,
        end=end,
        locations=locations,
        attribution=ATTRIBUTION,
        stated_period=f"Start : {match.group('start_time')} Hrs {match.group('start_date')} and End : {match.group('end_date')}",
        covers_city=True,
    )
    title = f"{kind}: {description or near}"
    if len(title) > 140:
        title = title[:137].rstrip() + "..."
    summary = " near ".join(part for part in (description, near) if part)
    return RawSourceRecord(
        source_id=SOURCE_ID,
        # The source gives no id: the line's own words are the item's identity.
        external_id=sha256_hex(line)[:24],
        url=ENDPOINT,
        title=title,
        summary=summary,
        content_text=None,
        categories=[kind],
        published_at=None,
        retrieved_at=retrieved_at,
        raw={
            "line": line,
            "kind": kind,
            "description": description,
            "near": near,
            "summary_html": summary,
            "content_html": "",
            "categories": [kind],
            "acquired_from": "Bengaluru Traffic Police home page, Upcoming Events / Press Notes (HTML)",
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=sha256_hex(line),
        structured=structured,
    )


def rebuild_structured(raw: dict) -> SourceEvent | None:
    """The line's structured reading, redone from the line as stored (for reprocessing)."""
    line = raw.get("line") if isinstance(raw, dict) else None
    if not line:
        return None
    record = to_record(line, utc_now())
    return record.structured if record else None


class BengaluruTrafficPoliceConnector:
    """Reads the home page's events list. One request per run."""

    @staticmethod
    def rebuild_structured(raw: dict) -> SourceEvent | None:
        return rebuild_structured(raw)

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

    def fetch(self) -> list[RawSourceRecord]:
        page = fetch_text(ENDPOINT, self._user_agent, client=self._client)
        retrieved_at = self._clock()
        records = [
            record for line in parse_items(page) if (record := to_record(line, retrieved_at))
        ]
        # The list is the whole current list: what was observed this refresh.
        self.observed_ids = {record.external_id for record in records}
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            # Soonest to start first.
            order=lambda record: -(record.structured.start or retrieved_at).timestamp(),
            limit=self.max_records,
        )
