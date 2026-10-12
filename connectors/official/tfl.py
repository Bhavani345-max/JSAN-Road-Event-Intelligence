"""Transport for London road disruptions: an AUTHORITATIVE_OFFICIAL source for London.

    GET https://api.tfl.gov.uk/Road/all/Disruption

Verified 6 October 2026 without a key: 115 disruptions, each with an id,
category and sub-category ("Works / Utility works", "Collisions / Vehicle
collision"), TfL's severity ("Minimal", "Serious"), status, start and end
times, a location ("[A13] NEWHAM WAY (E14 ,E16 ) (Newham)"), comments, and a
point. Some also carry a polygon or multipolygon of the affected area and a
list of streets, each with its direction ("Westbound", "Both directions"),
whether it is closed or open, and its segments as lines.

Terms: TfL's transport data service terms, the Open Government Licence v2.0
with TfL's amendments, which allow commercial and non-commercial use with the
attribution "Powered by TfL Open Data" and the Ordnance Survey notice. Limits:
50 requests a minute without a key; at most 500 a minute per feed with one.
A run makes one request. (https://tfl.gov.uk/corporate/terms-and-conditions/
transport-data-service, https://api-portal.tfl.gov.uk/products)

Everything below comes from TfL's own fields. TfL's geometry is kept as it
is; TfL's severity is kept in its words and not translated into REI's.
"""

from datetime import datetime
from typing import Any

import httpx

from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import ensure_utc, utc_now
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
    too_short_road_block,
)

from .common import content_key, fetch_json, parse_json_text, select_for_run

SOURCE_ID = "tfl-road-disruptions"
ENDPOINT = "https://api.tfl.gov.uk/Road/all/Disruption"
API_BASE = "https://api.tfl.gov.uk"
ATTRIBUTION = (
    "Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 "
    "and Geomni UK Map data © and database rights [2019]."
)

# Fields TfL updates without the disruption changing.
BOOKKEEPING_FIELDS = frozenset({"lastModifiedTime", "currentUpdateDateTime", "ordinal"})


def revision_key(raw: dict) -> str:
    """What must differ for a stored disruption to count as revised."""
    return content_key(raw.get("disruption"), BOOKKEEPING_FIELDS)


# TfL statuses that say the disruption is over (TfL's own words).
ENDED_STATUSES = frozenset({"recently cleared", "cleared", "cancelled", "removed"})

# TfL's categories and the REI event type each states. A category not listed
# (police activity, other incidents) gets no type: the reviewer decides.
EVENT_TYPE_BY_CATEGORY = {
    "works": EventType.ROAD_WORKS,
    "collisions": EventType.ACCIDENT,
    "asset issues": EventType.ROAD_HAZARD,
    "hazard(s)": EventType.ROAD_HAZARD,
    "hazards": EventType.ROAD_HAZARD,
    "special and planned events": EventType.SPECIAL_EVENT,
}
_DIRECTIONS = {
    "both directions": EventDirection.BOTH_DIRECTIONS,
    "northbound": EventDirection.NORTHBOUND,
    "southbound": EventDirection.SOUTHBOUND,
    "eastbound": EventDirection.EASTBOUND,
    "westbound": EventDirection.WESTBOUND,
}


def tfl_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("london")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Transport for London road disruptions",
        organization="Transport for London",
        authority_type="TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://tfl.gov.uk/traffic/status/",
        endpoint=ENDPOINT,
        access_method="TfL Unified API (REST, JSON); no key needed; an optional free app key raises the limit",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=15,
        language=city.language,
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.ACCIDENT.value,
            EventType.ROAD_HAZARD.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="tfl_road_disruption",
        cost_category=CostCategory.FREE_WITH_LIMITS,
        rate_limit=(
            "50 requests a minute without a key (api-portal.tfl.gov.uk/products); at most "
            "500 calls a minute per data feed under the terms. One request per run."
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "Open Government Licence v2.0 with TfL's amendments "
            "(tfl.gov.uk/corporate/terms-and-conditions/transport-data-service)"
        ),
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        provides_direction=True,
        real_time=True,
        evidence_retention=(
            "Each disruption exactly as TfL returned it, with a SHA-256 hash of its id, "
            "last-modified time, comments and current update."
        ),
        notes=(
            "Disruptions on the roads TfL manages, verified without a key on 6 October 2026 "
            "(115 records: works, collisions, asset faults). Every record has a start, an end "
            "and a point; some have an area polygon and street segments with direction. "
            + (
                "Polled every 15 minutes."
                if scheduled
                else "International test phase: run by hand, not on a schedule."
            )
        ),
    )


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def _clean(text: Any) -> str:
    return " ".join(html_to_text(str(text or "")).split())


def _geometry(disruption: dict) -> dict | None:
    """TfL's area if it gives one, otherwise its point. Its own shapes, unchanged."""
    shape = disruption.get("geometry")
    if isinstance(shape, dict) and shape.get("type") in ("Polygon", "MultiPolygon"):
        return {"type": shape["type"], "coordinates": shape.get("coordinates")}
    point = parse_json_text(disruption.get("point"))
    if isinstance(point, list) and len(point) == 2:
        return {"type": "Point", "coordinates": point}
    geography = disruption.get("geography")
    if isinstance(geography, dict) and geography.get("type") == "Point":
        return {"type": "Point", "coordinates": geography.get("coordinates")}
    return None


def _street(street: dict) -> SourceLocation:
    lines = []
    for segment in street.get("segments") or []:
        line = parse_json_text(segment.get("lineString"))
        if isinstance(line, list) and len(line) >= 2:
            lines.append(line)
    return SourceLocation(
        name=_clean(street.get("name")) or "Street",
        kind="street",
        geometry={"type": "MultiLineString", "coordinates": lines} if lines else None,
        direction=_clean(street.get("directions")) or None,
        closure=_clean(street.get("closure")) or None,
        reference="TfL street segments" if lines else None,
    )


def _direction(streets: list[SourceLocation]) -> str | None:
    """The event's direction when every street states the same one."""
    stated = {(street.direction or "").lower() for street in streets}
    if len(stated) == 1:
        direction = _DIRECTIONS.get(stated.pop())
        return direction.value if direction else None
    return None


def to_record(disruption: dict, retrieved_at: datetime) -> RawSourceRecord | None:
    disruption_id = str(disruption.get("id") or "").strip()
    if not disruption_id:
        return None
    category = _clean(disruption.get("category"))
    sub_category = _clean(disruption.get("subCategory"))
    location = _clean(disruption.get("location"))
    comments = _clean(disruption.get("comments"))
    update = _clean(disruption.get("currentUpdate"))
    streets = [_street(street) for street in disruption.get("streets") or []]
    structured = SourceEvent(
        event_type=(
            EVENT_TYPE_BY_CATEGORY[category.lower()].value
            if category.lower() in EVENT_TYPE_BY_CATEGORY
            else None
        ),
        category=" / ".join(part for part in (category, sub_category) if part) or None,
        severity=_clean(disruption.get("severity")) or None,
        status=_clean(disruption.get("status")) or None,
        start=_time(disruption.get("startDateTime")),
        end=_time(disruption.get("endDateTime")),
        geometry=_geometry(disruption),
        locations=streets,
        affected_road=location or None,
        direction=_direction(streets),
        attribution=ATTRIBUTION,
        reported_ended=_clean(disruption.get("status")).lower() in ENDED_STATUSES,
    )
    title = f"{sub_category or category or 'Disruption'}: {location or disruption_id}"
    summary = " ".join(part for part in (comments, update) if part) or None
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=disruption_id,
        url=f"{API_BASE}{disruption['url']}" if disruption.get("url") else f"{ENDPOINT}/{disruption_id}",
        title=title,
        summary=summary,
        content_text=None,
        categories=[part for part in (category, sub_category) if part],
        published_at=_time(disruption.get("lastModifiedTime")) or _time(disruption.get("startDateTime")),
        retrieved_at=retrieved_at,
        raw={
            "disruption": disruption,
            "summary_html": summary or "",
            "content_html": "",
            "categories": [part for part in (category, sub_category) if part],
            "acquired_from": "Transport for London Unified API, Road/all/Disruption",
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=sha256_hex(
            "\n".join([disruption_id, str(disruption.get("lastModifiedTime")), comments, update])
        ),
        structured=structured,
    )


class TflRoadDisruptionsConnector:
    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        app_key: str | None = None,
        max_records: int | None = None,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        self.source = source
        self._user_agent = user_agent
        self._app_key = app_key
        self.max_records = max_records
        self._client = client
        self._clock = clock

    @staticmethod
    def revision_key(raw: dict) -> str:
        return revision_key(raw)

    def fetch(self) -> list[RawSourceRecord]:
        params = {"app_key": self._app_key} if self._app_key else None
        body = fetch_json(ENDPOINT, self._user_agent, client=self._client, params=params)
        if not isinstance(body, list):
            from connectors.base import ConnectorError

            raise ConnectorError(f"{ENDPOINT} returned {type(body).__name__}, not a list")
        retrieved_at = self._clock()
        records = [record for item in body if (record := to_record(item, retrieved_at))]
        # Every record the feed listed, kept or not: what was observed this refresh.
        self.observed_ids = {record.external_id for record in records}
        # Road blocks under the minimum length are not events (road_block.py);
        # leaving them out first gives the run's places to the ones that are.
        records = [record for record in records if too_short_road_block(record.structured) is None]
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.published_at or retrieved_at,
            limit=self.max_records,
        )
