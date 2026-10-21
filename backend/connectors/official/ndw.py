"""NDW (Nationaal Dataportaal Wegverkeer), the Netherlands: the current picture
and the planned roadworks and events (21 October 2026).

    GET https://opendata.ndw.nu/actueel_beeld.xml.gz
    GET https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz

NDW gathers the road events of every Dutch road authority (Rijkswaterstaat's
districts, the provinces, the municipalities) and publishes them as gzipped
DATEX II v3 situation publications, without a key. Times are UTC ("Z").

- The **current picture** (*actueel beeld*), rebuilt every minute: what is in
  force now. 21 October 2026, 13:00 CEST: 1,230 situations, 1,545 records.
  945 of the situations are the measures of planned works now in force: each
  record names, in `situationRecordCreationReference`, the planned-feed record
  it was made from (NDW03_…, RWS01_…). The planned-feed source lists the same
  works with their full planned period, so this source leaves them out by
  default (`include_planned_measures`): one road event is not two events. What
  remains is what was not planned: vehicle obstructions, accidents,
  obstructions, bridge openings, traffic-management measures.
- The **planned feed**: roadworks and events, current and up to years ahead.
  21 October 2026, 12:45 CEST: 14,684 situations, 62,898 records (16 MB packed,
  about 215 MB unpacked, read as a stream); 14,013 are current or start within
  REI's run window. Nearly all state a start and an end.

Licence: NDW's portal links its "Copyright & disclaimer" to
https://www.ndw.nu/copyright (read 21 October 2026): "Tenzij anders vermeld is
op de inhoud van deze website de Creative Commons Zero (CC0) verklaring van
toepassing. Dit houdt in dat hergebruik van de inhoud van deze site is
toegestaan …". Images are excluded, and a derived work must not suggest that
NDW endorses it. No attribution is required; "Bron: NDW" is given as a
courtesy (docs/data-sources/netherlands-luxembourg-connectors-2026-10-21.md).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

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

CURRENT_SOURCE_ID = "nl-ndw-actueel-beeld"
PLANNED_SOURCE_ID = "nl-ndw-planningsfeed-wegwerkzaamheden"
CURRENT_URL = "https://opendata.ndw.nu/actueel_beeld.xml.gz"
PLANNED_URL = "https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz"
SOURCE_URL = "https://opendata.ndw.nu/"
DOCS_URL = "https://docs.ndw.nu/"
LICENCE = "Creative Commons Zero (CC0) 1.0 (NDW copyright statement, https://www.ndw.nu/copyright)"
ATTRIBUTION = "Bron: NDW (Nationaal Dataportaal Wegverkeer), CC0. Not endorsed by NDW."
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
# The suppliers of the planned feed, by the prefix of their record ids (21 October
# 2026: every planned-feed situation id starts with one of these).
PLANNED_FEED_SUPPLIERS = ("NDW03_", "RWS01_", "AND01_")
EVENTS = (
    EventType.PLANNED_ROAD_CLOSURE.value,
    EventType.EMERGENCY_ROAD_CLOSURE.value,
    EventType.LANE_RESTRICTION.value,
    EventType.ROAD_WORKS.value,
    EventType.TRAFFIC_DIVERSION.value,
    EventType.ACCIDENT.value,
    EventType.ROAD_HAZARD.value,
    EventType.BRIDGE_TUNNEL_RESTRICTION.value,
)
PLANNED_EVENTS = (
    EventType.PLANNED_ROAD_CLOSURE.value,
    EventType.LANE_RESTRICTION.value,
    EventType.ROAD_WORKS.value,
    EventType.TRAFFIC_DIVERSION.value,
    EventType.SPECIAL_EVENT.value,
    EventType.MARATHON.value,
    EventType.SPORTING_EVENT.value,
    EventType.BRIDGE_TUNNEL_RESTRICTION.value,
)


def _definition(
    *,
    scheduled: bool,
    source_id: str,
    name: str,
    endpoint: str,
    access: str,
    minutes: int,
    events: tuple[str, ...],
    parser: str,
    real_time: bool,
    notes: str,
) -> SourceDefinition:
    country = get_city("netherlands")
    return SourceDefinition(
        source_id=source_id,
        source_name=name,
        organization="NDW (Nationaal Dataportaal Wegverkeer), for the Dutch road authorities",
        authority_type="NATIONAL_ROAD_TRAFFIC_DATA_PORTAL",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="National",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=endpoint,
        access_method=access,
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=minutes,
        language="nl",
        events_supported=events,
        parser_type=parser,
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; no availability guarantee.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=LICENCE,
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=real_time,
        evidence_retention=(
            "Each situation as the fields it states (types, times, periods, comments, roads, lines as "
            "published), with comment lines naming a contact person, phone number or e-mail address "
            "removed; ALERT-C location codes are not kept."
        ),
        notes=notes,
    )


def ndw_current_source(*, scheduled: bool) -> SourceDefinition:
    return _definition(
        scheduled=scheduled,
        source_id=CURRENT_SOURCE_ID,
        name="NDW current road situations (actueel beeld), Netherlands",
        endpoint=CURRENT_URL,
        access="Gzipped DATEX II v3 situation publication, rebuilt every minute; no key",
        minutes=30,
        events=EVENTS,
        parser="ndw_datex3_actueel_beeld",
        real_time=True,
        notes=(
            "What is in force now on Dutch roads, from every road authority. Fetched without a key on "
            "21 October 2026: 1,230 situations. The 945 that are planned works now in force (named by "
            "their planned-feed record) are left out: the planned-feed source lists them with their "
            "full period. Most of the rest (vehicle obstructions, accidents, bridge openings) state a "
            "start and no end."
        ),
    )


def ndw_planned_source(*, scheduled: bool) -> SourceDefinition:
    return _definition(
        scheduled=scheduled,
        source_id=PLANNED_SOURCE_ID,
        name="NDW planned roadworks and events (planningsfeed), Netherlands",
        endpoint=PLANNED_URL,
        access="Gzipped DATEX II v3 situation publication (16 MB packed, 215 MB unpacked); no key",
        minutes=180,
        events=PLANNED_EVENTS,
        parser="ndw_datex3_planningsfeed",
        real_time=False,
        notes=(
            "Planned roadworks and events of every Dutch road authority, current and ahead. Fetched "
            "without a key on 21 October 2026: 14,684 situations (62,898 records), 14,013 current or "
            "starting within a year; nearly all state a start and an end. Read as a stream."
        ),
    )


def is_planned_measure(item: dict[str, Any]) -> bool:
    """A current-picture situation whose every record was made from a planned-feed
    record (the source names it in `situationRecordCreationReference`)."""
    records = item.get("records", [])
    return bool(records) and all(
        str(record.get("created_from") or "").startswith(PLANNED_FEED_SUPPLIERS) for record in records
    )


def to_record(item: dict[str, Any], retrieved_at: datetime, *, source_id: str) -> RawSourceRecord | None:
    """One situation as REI's record. The planned feed lists planned works and
    events only, so its closures are planned closures."""
    return datex.situation_record(
        item,
        source_id=source_id,
        url=SOURCE_URL,
        attribution=ATTRIBUTION,
        default_authority="NDW",
        zone=AMSTERDAM,
        retrieved_at=retrieved_at,
        planned_feed=source_id == PLANNED_SOURCE_ID,
    )


class _NdwConnector:
    source_id: str
    endpoint: str

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

    revision_key = staticmethod(datex.revision_key)

    def _skip(self, item: dict[str, Any]) -> bool:
        return False

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        body = datex.fetch_bytes(self.endpoint, self._user_agent, client=self._client)
        records, observed, counts = datex.read_publication(
            body,
            self.endpoint,
            now=now,
            build=lambda item: to_record(item, now, source_id=self.source.source_id),
            skip=self._skip,
        )
        # The feed lists every situation it has in force or planned; ended ones
        # drop out of it (or out of the run window above).
        self.observed_ids = observed
        self.counts = counts
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.published_at or record.retrieved_at,
            limit=self.max_records,
        )


class NdwCurrentSituationsConnector(_NdwConnector):
    """The current picture, without the planned works now in force (unless asked)."""

    endpoint = CURRENT_URL

    def __init__(self, source: SourceDefinition, user_agent: str, *, include_planned_measures: bool = False, **options) -> None:
        super().__init__(source, user_agent, **options)
        self.include_planned_measures = include_planned_measures

    def _skip(self, item: dict[str, Any]) -> bool:
        return not self.include_planned_measures and is_planned_measure(item)


class NdwPlannedWorksConnector(_NdwConnector):
    """Planned roadworks and events."""

    endpoint = PLANNED_URL
