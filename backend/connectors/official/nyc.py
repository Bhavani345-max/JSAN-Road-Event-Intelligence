"""New York City street closures published by NYC DOT on NYC Open Data.

The GeoJSON dataset is public and keyless. It covers full street closures for
construction, with a road-segment geometry and work start/end dates.

It lists a block's closure once per permit purpose ("place crane or shovel on
street", "occupancy of roadway as stipulated" ...), each row with its own id:
on 14 October 2026, 3,568 rows described 2,277 closures. Every row is kept as
evidence; rows of one closure are merged into one event (see
`same_closure_key` and app/services/merge_service.py).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.common.time import ensure_utc, utc_now
from packages.event_schema import EventType, ReiEvent
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

from .common import content_key, fetch_json, select_for_run

SOURCE_ID = "nyc-street-closures"
ENDPOINT = "https://data.cityofnewyork.us/resource/i6b5-j7bu.geojson"
ATTRIBUTION = (
    "Source: NYC Department of Transportation, Street Closures due to Construction "
    "Activities by Block (NYC Open Data dataset i6b5-j7bu)."
)
PAGE_SIZE = 5_000
NYC_TIME_ZONE = ZoneInfo("America/New_York")


def nyc_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("new-york")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="NYC DOT street closures for construction",
        organization="New York City Department of Transportation",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://data.cityofnewyork.us/d/i6b5-j7bu",
        endpoint=ENDPOINT,
        access_method="NYC Open Data Socrata GeoJSON API; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=1440,
        language="en",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value,),
        parser_type="nyc_dot_street_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="No numeric limit published; one GeoJSON request per 5,000 records.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="NYC Open Data public dataset; NYC Open Data Terms of Use",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention="Each GeoJSON feature and the structured event derived from it.",
        notes=(
            "Public NYC DOT data for full street closures caused by construction. The "
            "dataset was fetched without a key on 13 October 2026. NYC Open Data's FAQ "
            "states that open data has no use restrictions; polling is daily when enabled."
        ),
    )


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    # NYC publishes local permit times without an offset.
    return parsed.replace(tzinfo=NYC_TIME_ZONE) if parsed.tzinfo is None else parsed


def same_closure_key(event: ReiEvent) -> str | None:
    """What the dataset's rows for one closure share: the block's segment and the work period.

    Rows with the same street segment and the same work start and end are one
    closure of that block, whatever their permit purpose or the cross streets
    they name. None when an event states no segment or no full period.
    """
    if event.start_time is None or event.end_time is None or event.detection is None:
        return None
    locations = event.detection.affected_locations
    segments = sorted({location.reference for location in locations if location.reference})
    if not segments:
        return None
    start, end = (
        ensure_utc(time).strftime("%Y-%m-%d %H:%M") for time in (event.start_time, event.end_time)
    )
    return f"{'; '.join(segments)}, work period {start} to {end} UTC"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = _clean(properties.get("uniqueid"))
    if not external_id:
        return None

    road = _clean(properties.get("onstreetname"))
    from_street = _clean(properties.get("fromstreetname"))
    to_street = _clean(properties.get("tostreetname"))
    location = road or "Street closure"
    if from_street or to_street:
        location += f" between {from_street or 'the previous intersection'} and {to_street or 'the next intersection'}"
    purpose = _clean(properties.get("purpose")) or None
    work_type = _clean(properties.get("type")) or None
    structured = SourceEvent(
        event_type=EventType.PLANNED_ROAD_CLOSURE.value,
        category=" / ".join(part for part in ("Construction street closure", work_type) if part),
        start=_time(properties.get("work_start_date")),
        end=_time(properties.get("work_end_date")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=location,
                kind="road segment",
                geometry=geometry,
                reference=(f"NYC DOT segment {properties.get('segmentid')}" if properties.get("segmentid") else None),
            )
        ],
        affected_road=road or None,
        attribution=ATTRIBUTION,
    )
    raw = {"feature": feature, "source_event": structured.model_dump(mode="json")}
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url="https://data.cityofnewyork.us/d/i6b5-j7bu",
        title=f"Planned road closure: {location}",
        summary=purpose,
        content_text=None,
        categories=["construction", "street closure"],
        published_at=None,
        retrieved_at=retrieved_at,
        raw=raw,
        content_hash=content_key(feature, frozenset()),
        structured=structured,
    )


class NycStreetClosuresConnector:
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
        return content_key(raw.get("feature", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        features: list[dict[str, Any]] = []
        offset = 0
        while True:
            body = fetch_json(
                ENDPOINT,
                self._user_agent,
                client=self._client,
                params={"$limit": str(PAGE_SIZE), "$offset": str(offset)},
            )
            page = body.get("features") if isinstance(body, dict) else None
            if not isinstance(page, list):
                raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature list")
            features.extend(item for item in page if isinstance(item, dict))
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        retrieved_at = self._clock()
        records = [record for item in features if (record := to_record(item, retrieved_at))]
        # The feed is a full snapshot; keep all observed IDs even when the
        # time window or short-block rule keeps a record out of this run.
        self.observed_ids = {record.external_id for record in records}
        records = [record for record in records if too_short_road_block(record.structured) is None]
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
