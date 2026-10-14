"""Finland's public Digitraffic road-work and traffic-announcement feeds."""

import json
from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
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

from .common import select_for_run

SOURCE_ID = "finland-digitraffic-road-events"
BASE_URL = "https://tie.digitraffic.fi/api/traffic-message/v2"
SOURCE_URL = "https://www.digitraffic.fi/en/road-traffic/"
ATTRIBUTION = "Source: Fintraffic Digitraffic road traffic messages (CC BY 4.0)."
USER_HEADER = "JSAN-Road-Event-Intelligence/1.0"
FEEDS = (
    ("roadworks", "road works"),
    ("traffic-announcements", "traffic announcements"),
    ("exempted-transports", "exempted transports"),
)


def finland_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("finland")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Fintraffic Digitraffic national road events",
        organization="Fintraffic / Digitraffic",
        authority_type="NATIONAL_ROAD_TRAFFIC_MANAGEMENT",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country="FI",
        region="National",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=f"{BASE_URL}/{{roadworks,traffic-announcements,exempted-transports}}",
        access_method="Keyless GeoJSON-like Simple JSON API; Digitraffic-User identification header",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fi",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.ACCIDENT.value,
            EventType.TRAFFIC_DIVERSION.value,
        ),
        parser_type="fintraffic_simple_json",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="60 requests/minute per IP without an app header; payload is cached by the provider.",
        terms_reviewed=True,
        terms_status=TermsStatus.PERMITS_COMMERCIAL,
        licence="Creative Commons Attribution 4.0 International",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Original feature and source-provided event geometry, with attribution.",
        notes=(
            "National Finland feed for road works, traffic announcements and exceptional transports. "
            "Fetched live on 13 October 2026; provider lists CC BY 4.0 and recommends the "
            "Digitraffic-User header. Events retain Finnish text when no English text is published."
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
    return parsed


def _announcements(properties: dict[str, Any]) -> list[dict[str, Any]]:
    rows = properties.get("announcements")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _preferred_announcement(properties: dict[str, Any]) -> dict[str, Any]:
    rows = _announcements(properties)
    return next(
        (row for language in ("en", "fi", "sv") for row in rows if row.get("language") == language),
        rows[0] if rows else {},
    )


def _event_type(feed_kind: str, properties: dict[str, Any]) -> str | None:
    if feed_kind == "roadworks":
        return EventType.ROAD_WORKS.value
    announcement_type = _clean(properties.get("trafficAnnouncementType")).lower()
    if "accident" in announcement_type:
        return EventType.ACCIDENT.value
    if "arrangement" in announcement_type or "diversion" in announcement_type:
        return EventType.TRAFFIC_DIVERSION.value
    return None


def _period(announcement: dict[str, Any], properties: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    candidates = [announcement.get("timeAndDuration")]
    phases = properties.get("roadWorkPhases")
    if isinstance(phases, list):
        candidates.extend(phase for phase in phases if isinstance(phase, dict))
    starts = [_time(row.get("startTime")) for row in candidates if isinstance(row, dict)]
    ends = [_time(row.get("endTime")) for row in candidates if isinstance(row, dict)]
    starts = [value for value in starts if value is not None]
    ends = [value for value in ends if value is not None]
    return (min(starts) if starts else None, max(ends) if ends else None)


def to_record(
    feature: dict[str, Any], feed_kind: str, retrieved_at: datetime
) -> RawSourceRecord | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    situation_id = _clean(properties.get("situationId"))
    if not situation_id:
        return None

    announcement = _preferred_announcement(properties)
    title = _clean(announcement.get("title")) or _clean(properties.get("situationType")) or "Road event"
    location = announcement.get("location") if isinstance(announcement.get("location"), dict) else {}
    location_details = announcement.get("locationDetails") if isinstance(announcement.get("locationDetails"), dict) else {}
    road_location = location_details.get("roadAddressLocation") or {}
    primary = road_location.get("primaryPoint") if isinstance(road_location, dict) else {}
    primary = primary if isinstance(primary, dict) else {}
    road_address = primary.get("roadAddress") if isinstance(primary.get("roadAddress"), dict) else {}
    geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else None
    road = _clean(primary.get("roadName")) or _clean(road_address.get("roadName")) or None
    place_text = _clean(location.get("description"))
    summary = place_text or _clean(announcement.get("additionalInformation")) or None
    if road and road not in title:
        title = f"{title} — {road}"
    start, end = _period(announcement, properties)
    direction_text = _clean(road_location.get("direction")).lower() if isinstance(road_location, dict) else ""
    direction = EventDirection.BOTH_DIRECTIONS.value if direction_text == "both" else None
    category = " / ".join(
        value for value in (
            _clean(properties.get("situationType")),
            _clean(properties.get("trafficAnnouncementType")),
        ) if value
    ) or None
    structured = SourceEvent(
        event_type=_event_type(feed_kind, properties),
        category=category,
        status="ended" if _clean(properties.get("trafficAnnouncementType")).lower() == "ended" else None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place_text or road or title,
                kind="road segment" if geometry and "LineString" in geometry.get("type", "") else "road location",
                geometry=geometry,
                direction=direction_text or None,
                reference=f"Fintraffic situation {situation_id}",
            )
        ],
        affected_road=road,
        direction=direction,
        attribution=ATTRIBUTION,
        reported_ended=_clean(properties.get("trafficAnnouncementType")).lower() == "ended",
        covers_city=True,
    )
    raw = {
        "feed_kind": feed_kind,
        "feature": feature,
        "source_event": structured.model_dump(mode="json"),
    }
    external_id = f"{feed_kind}:{situation_id}"
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=title,
        summary=summary,
        content_text=None,
        categories=[_clean(properties.get("situationType")), _clean(properties.get("trafficAnnouncementType"))],
        published_at=_time(properties.get("versionTime")) or _time(properties.get("releaseTime")),
        retrieved_at=retrieved_at,
        raw=raw,
        content_hash=sha256_hex(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))),
        structured=structured,
    )


class FinlandDigitrafficConnector:
    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        self.source = source
        self._user_agent = user_agent
        self._client = client
        self._clock = clock

    @staticmethod
    def revision_key(raw: dict[str, Any]) -> str:
        feature = raw.get("feature", {})
        props = feature.get("properties", {}) if isinstance(feature, dict) else {}
        return sha256_hex(json.dumps(props, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    def fetch(self) -> list[RawSourceRecord]:
        retrieved_at = self._clock()
        records: list[RawSourceRecord] = []
        observed: set[str] = set()
        for feed_kind, _label in FEEDS:
            url = f"{BASE_URL}/{feed_kind}"
            try:
                response = (self._client or httpx).get(
                    url,
                    headers={
                        "User-Agent": self._user_agent,
                        "Digitraffic-User": USER_HEADER,
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                    },
                    timeout=45,
                    follow_redirects=True,
                )
                response.raise_for_status()
                body = response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise ConnectorError(f"Could not read Digitraffic {feed_kind}: {error}") from error
            features = body.get("features") if isinstance(body, dict) else None
            if not isinstance(features, list):
                raise ConnectorError(f"Digitraffic {feed_kind} did not return a feature list")
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                record = to_record(feature, feed_kind, retrieved_at)
                if record is None:
                    continue
                records.append(record)
                observed.add(record.external_id)

        self.observed_ids = observed
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.published_at or record.retrieved_at,
            limit=None,
        )
