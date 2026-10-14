"""City of Toronto road restrictions: an AUTHORITATIVE_OFFICIAL source for Toronto.

    GET https://secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json

Verified 6 October 2026 without a key: {"Closure": [...]} with 2,047 records,
each with an id, the road and a description of the stretch ("Victoria St at
Shuter St to 45 m South of Shuter St"), coordinates and a polyline, the type
("ROAD_CLOSED", "CONSTRUCTION"), whether it is planned, the work type, the
directions affected ("BOTH_DIRECTIONS", "ONE_DIRECTION"), and start and end
times (milliseconds since 1970).

Terms: Open Government Licence – Toronto, which allows use "for any lawful
purpose", with the attribution "Contains information licensed under the Open
Government Licence – Toronto." (open.toronto.ca/open-data-licence). No rate
limit is published; a run makes one request.
"""

import re
from datetime import datetime, timezone
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
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
    too_short_road_block,
)

from .common import content_key, fetch_json, parse_json_text, select_for_run

SOURCE_ID = "toronto-road-restrictions"
ENDPOINT = "https://secure.toronto.ca/opendata/cart/road_restrictions/v3"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – Toronto."
_OPTION = re.compile(r'"Option"\s*:\s*"([^"]+)"')
# Fields the City updates without the restriction changing.
BOOKKEEPING_FIELDS = frozenset({"lastUpdated"})


def revision_key(raw: dict) -> str:
    """What must differ for a stored restriction to count as revised."""
    return content_key(raw.get("restriction"), BOOKKEEPING_FIELDS)


def toronto_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("toronto")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Toronto road restrictions",
        organization="City of Toronto, Transportation Services",
        authority_type="MUNICIPAL",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://open.toronto.ca/dataset/road-restrictions/",
        endpoint=ENDPOINT,
        access_method="City of Toronto open data feed (JSON); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language=city.language,
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="toronto_road_restrictions",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published (checked 6 October 2026). One request per run.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – Toronto (open.toronto.ca/open-data-licence)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each restriction exactly as the City returned it, with a SHA-256 hash.",
        notes=(
            "Road closures and construction restrictions on City of Toronto roads, verified "
            "without a key on 6 October 2026 (2,047 records, every one with coordinates, a "
            "polyline and start and end times). "
            + (
                "Polled every 30 minutes."
                if scheduled
                else "International test phase: run by hand, not on a schedule."
            )
        ),
    )


def _time(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(str(value)) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _clean(value: Any) -> str:
    text = " ".join(html_to_text(str(value or "")).split())
    return "" if text.lower() == "none" else text


def _work_type(value: Any) -> str:
    """The work type; some records send it as a fragment of a JSON table."""
    text = str(value or "")
    match = _OPTION.search(text)
    return match.group(1) if match else _clean(text)


def _geometry(record: dict) -> dict | None:
    """The City's polyline; its point when the polyline has a single position."""
    line = parse_json_text(f"[{record.get('geoPolyline')}]") if record.get("geoPolyline") else None
    if isinstance(line, list):
        positions = [p for p in line if isinstance(p, list) and len(p) == 2]
        distinct = [p for i, p in enumerate(positions) if i == 0 or p != positions[i - 1]]
        if len(distinct) >= 2:
            return {"type": "LineString", "coordinates": distinct}
        if distinct:
            return {"type": "Point", "coordinates": distinct[0]}
    try:
        return {
            "type": "Point",
            "coordinates": [float(record["longitude"]), float(record["latitude"])],
        }
    except (KeyError, TypeError, ValueError):
        return None


def _event_type(record: dict) -> str | None:
    if _clean(record.get("specialEvent")).lower() == "yes":
        return EventType.SPECIAL_EVENT.value
    kind = _clean(record.get("type")).upper()
    if kind == "ROAD_CLOSED":
        # Planned closures only; an unplanned one could be many things.
        return EventType.PLANNED_ROAD_CLOSURE.value if str(record.get("planned")) == "1" else None
    if kind == "CONSTRUCTION":
        return EventType.ROAD_WORKS.value
    return None


def to_record(item: dict, retrieved_at: datetime) -> RawSourceRecord | None:
    restriction_id = _clean(item.get("id"))
    if not restriction_id:
        return None
    kind = _clean(item.get("type"))
    name = _clean(item.get("name")) or _clean(item.get("road"))
    road = _clean(item.get("road")) or None
    directions = _clean(item.get("directionsAffected")) or None
    description = re.sub(r"^Toronto-TMC:\s*", "", _clean(item.get("description"))) or None
    geometry = _geometry(item)
    structured = SourceEvent(
        event_type=_event_type(item),
        category=" / ".join(part for part in (kind, _work_type(item.get("workEventType"))) if part)
        or None,
        severity=_clean(item.get("currImpact")) or _clean(item.get("maxImpact")) or None,
        status="expired" if str(item.get("expired")) == "1" else None,
        start=_time(item.get("startTime")),
        end=_time(item.get("endTime")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=name or restriction_id,
                kind="road segment",
                geometry=geometry,
                direction=directions,
                closure=kind or None,
                reference="City of Toronto polyline" if geometry else None,
            )
        ],
        affected_road=road,
        direction=(
            EventDirection.BOTH_DIRECTIONS.value if directions == "BOTH_DIRECTIONS" else None
        ),
        attribution=ATTRIBUTION,
        reported_ended=str(item.get("expired")) == "1",
    )
    label = kind.replace("_", " ").capitalize() if kind else "Restriction"
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=restriction_id,
        url=_clean(item.get("URL")) or None,
        title=f"{label}: {name}",
        summary=description,
        content_text=None,
        categories=[part for part in (kind, _work_type(item.get("workEventType"))) if part],
        published_at=_time(item.get("lastUpdated")) or _time(item.get("createdTime")),
        retrieved_at=retrieved_at,
        raw={
            "restriction": item,
            "summary_html": description or "",
            "content_html": "",
            "categories": [kind] if kind else [],
            "acquired_from": "City of Toronto open data, road_restrictions v3",
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=sha256_hex(
            "\n".join([restriction_id, str(item.get("lastUpdated")), description or ""])
        ),
        structured=structured,
    )


class TorontoRoadRestrictionsConnector:
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
        return revision_key(raw)

    def fetch(self) -> list[RawSourceRecord]:
        body = fetch_json(ENDPOINT, self._user_agent, client=self._client, params={"format": "json"})
        items = body.get("Closure") if isinstance(body, dict) else None
        if not isinstance(items, list):
            raise ConnectorError(f"{ENDPOINT} did not return a list of closures")
        retrieved_at = self._clock()
        records = [record for item in items if (record := to_record(item, retrieved_at))]
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
            # Full closures first, then the most recently updated.
            order=lambda record: (
                record.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value,
                record.published_at or retrieved_at,
            ),
            limit=self.max_records,
        )
