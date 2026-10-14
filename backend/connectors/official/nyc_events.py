"""New York City permitted events that close a street, from NYC Open Data.

    GET https://data.cityofnewyork.us/resource/tvpp-9vvx.json

The City's Office of Citywide Event Coordination and Management publishes the
events approved for the next month (parades, street fairs, block parties,
races, Open Streets), permitted by the Street Activity Permit Office or the
NYPD. Only rows the dataset marks as a full street closure are read: on 14
October 2026, 179 rows of 129 events.

Each row is one day of one event at one place, so an event held on several
days is several rows; each stays its own event, as the source lists it. Times
carry no offset and are read as New York time, as for NYC DOT's closures. The
place is text only ("CENTRE STREET between DUANE STREET and PARK ROW"): no
geometry, so the event stays unlocated until a reviewer places it.

NYC Open Data FAQ (https://www.nyc.gov/opendata/get-started/FAQs, read 14
October 2026): "There are no restrictions on the use of Open Data."
"""

from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.time import utc_now
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

from .common import content_key, fetch_json, select_for_run
from .nyc import NYC_TIME_ZONE, _clean, _time

SOURCE_ID = "nyc-permitted-events"
ENDPOINT = "https://data.cityofnewyork.us/resource/tvpp-9vvx.json"
SOURCE_URL = "https://data.cityofnewyork.us/d/tvpp-9vvx"
ATTRIBUTION = (
    "Source: NYC Office of Citywide Event Coordination and Management, NYC Permitted "
    "Event Information (NYC Open Data dataset tvpp-9vvx)."
)
# The dataset's own words for a closure of the whole street.
FULL_CLOSURES = ("Full Street Closure", "Sidewalk and Street Closure")
PAGE_SIZE = 5_000

# The dataset's event types with a type of their own in REI; any other event
# that closes a street is a special event.
_EVENT_TYPES = {
    "Parade": EventType.PUBLIC_PROCESSION,
    "Athletic Race / Tour": EventType.MARATHON,
}


def nyc_events_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("new-york")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="NYC permitted events closing streets",
        organization="NYC Office of Citywide Event Coordination and Management",
        authority_type="MUNICIPAL_EVENT_PERMITTING_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="NYC Open Data Socrata JSON API; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.SPECIAL_EVENT.value,
            EventType.PUBLIC_PROCESSION.value,
            EventType.MARATHON.value,
        ),
        parser_type="nyc_permitted_events",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "No numeric limit published; requests without an app token share a pool by IP "
            "address and may be throttled (HTTP 429)."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="NYC Open Data: 'There are no restrictions on the use of Open Data.'",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=False,
        real_time=False,
        evidence_retention="Each dataset row and the structured event derived from it.",
        notes=(
            "Approved events for the next month that close a whole street (parades, street "
            "fairs, block parties, races, Open Streets). Fetched without a key on 14 October "
            "2026: 179 full-closure rows of 129 events. One row per day and place; places are "
            "street names only, so events are not located until a reviewer places them. "
            "Updated daily by the City."
        ),
    )


def _event_type(row: dict[str, Any]) -> str:
    return _EVENT_TYPES.get(_clean(row.get("event_type")), EventType.SPECIAL_EVENT).value


def _external_id(row: dict[str, Any]) -> str | None:
    """The event, the day and the place: a row's own identity (the dataset has no row id)."""
    event_id = _clean(row.get("event_id"))
    start = _clean(row.get("start_date_time"))
    if not event_id or not start:
        return None
    place = sha256_hex(_clean(row.get("event_location")))[:12]
    return f"{event_id}:{start}:{place}"


def _places(text: str) -> list[str]:
    """The places a row lists, in its order.

    Several are separated by commas ("ASTORIA PARK SOUTH between SHORE
    BOULEVARD and 14 STREET, SHORE BOULEVARD between ..."); a place is
    sometimes written twice around a colon ("Thomas Paine Park (Foley Square):
    Thomas Paine Park (Foley Square)"), and is then kept once.
    """
    places: list[str] = []
    for part in text.split(","):
        part = _clean(part)
        head, colon, tail = part.partition(": ")
        if colon and _clean(head) == _clean(tail):
            part = _clean(head)
        if part and part not in places:
            places.append(part)
    return places


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    if _clean(row.get("street_closure_type")) not in FULL_CLOSURES:
        return None
    external_id = _external_id(row)
    if external_id is None:
        return None

    name = _clean(row.get("event_name")) or "Permitted event"
    kind = _clean(row.get("event_type")) or None
    places = _places(row.get("event_location") or "")
    borough = _clean(row.get("event_borough"))
    location = "; ".join(places) + (f", {borough}" if borough and places else "")
    # "34 AVENUE between 93 STREET and 94 STREET": the street closed. Only
    # read when the first place is written that way.
    first = places[0] if places else ""
    road = None
    if " between " in first and ":" not in first:
        road = first.split(" between ")[0].strip()
    closure = _clean(row.get("street_closure_type"))
    agency = _clean(row.get("event_agency"))
    structured = SourceEvent(
        event_type=_event_type(row),
        category=" / ".join(part for part in (kind, closure) if part),
        start=_time(row.get("start_date_time")),
        end=_time(row.get("end_date_time")),
        locations=[
            SourceLocation(
                name=f"{place}, {borough}" if borough else place,
                kind="street stretch",
                closure=closure,
            )
            for place in places
        ],
        affected_road=road,
        attribution=ATTRIBUTION,
    )
    summary = ". ".join(
        part
        for part in (
            f"{closure}: {location}" if location else closure,
            f"{kind} permitted by the {agency}" if kind and agency else kind or agency,
        )
        if part
    )
    categories = [part for part in ("permitted event", kind) if part]
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{kind or 'Event'}: {name}",
        summary=summary or None,
        content_text=None,
        categories=categories,
        published_at=None,
        retrieved_at=retrieved_at,
        raw={
            "row": row,
            "summary_html": summary,
            "categories": categories,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=content_key(row, frozenset()),
        structured=structured,
    )


class NycPermittedEventsConnector:
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
        # The query asks only for events not yet ended, so a row dropping out
        # of it usually means its day is over: no `observed_ids` is reported,
        # and nothing is counted missing.

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("row", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        retrieved_at = self._clock()
        # The dataset's times are New York times without an offset.
        local_now = retrieved_at.astimezone(NYC_TIME_ZONE).strftime("%Y-%m-%dT%H:%M:%S")
        closures = ", ".join(f"'{value}'" for value in FULL_CLOSURES)
        where = f"end_date_time >= '{local_now}' AND street_closure_type in ({closures})"
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = fetch_json(
                ENDPOINT,
                self._user_agent,
                client=self._client,
                params={
                    "$where": where,
                    "$order": "start_date_time, event_id",
                    "$limit": str(PAGE_SIZE),
                    "$offset": str(offset),
                },
            )
            if not isinstance(page, list):
                raise ConnectorError(f"{ENDPOINT} did not return a list of rows")
            rows.extend(row for row in page if isinstance(row, dict))
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        records = [record for row in rows if (record := to_record(row, retrieved_at))]
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
