"""CITA traffic events, Luxembourg (21 October 2026).

    GET https://cita.lu/info_trafic/datex/situationrecord36

The Administration des ponts et chaussées' motorway traffic control centre
(CITA, Contrôle et Information du Trafic sur les Autoroutes) publishes the
active and planned events on Luxembourg's motorways and expressways as a
DATEX II 3.6 situation publication, refreshed every minute, without a key:
roadworks, obstructions, broken-down vehicles, tunnel equipment faults. Each
record gives its road (`roadName`), the direction (`roadDestination`), the
length affected and a line and a point in WGS 84; one record per direction.
Times carry their offset (+01:00 / +02:00). Fetched 21 October 2026, 12:55
CEST: 15 situations, 20 records, each with a start and none with an end (the
publisher removes an event when it is over), so every event stays
unconfirmed under REI's display rules until the source states an end.

The type comes from the DATEX II record (shared rules in datex3_nl_lu.py):
MaintenanceWorks and ConstructionWorks are road works; obstructions, a
broken-down vehicle and an equipment fault (a tunnel's systems not working)
are road hazards.

Licence: Creative Commons Zero (CC0), as data.public.lu states for the
dataset "Cita : Événements trafic en Datex-II v3.6" (licence field `cc-zero`,
read 21 October 2026); no attribution is required
(docs/data-sources/netherlands-luxembourg-connectors-2026-10-21.md).
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

SOURCE_ID = "lu-cita-datex2-v36"
ENDPOINT = "https://cita.lu/info_trafic/datex/situationrecord36"
SOURCE_URL = "https://data.public.lu/fr/datasets/cita-evenements-trafic-en-datex-ii-v3-6/"
LICENCE = "Creative Commons Zero (CC0) 1.0 (data.public.lu dataset licence)"
ATTRIBUTION = "Source: Administration des ponts et chaussées, CITA (Luxembourg), CC0."
LUXEMBOURG = ZoneInfo("Europe/Luxembourg")


def cita_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("luxembourg")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="CITA motorway traffic events, Luxembourg",
        organization="Administration des ponts et chaussées (CITA traffic control centre)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="National",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="DATEX II 3.6 situation publication (XML), refreshed every minute; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="fr",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.ROAD_HAZARD.value,
            EventType.ACCIDENT.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
        ),
        parser_type="cita_datex3_situations",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; the file is refreshed every minute.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=LICENCE,
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each situation as the fields it states (types, times, roads, directions, lines as published).",
        notes=(
            "Active and planned events on Luxembourg's motorways and expressways. Fetched without a key "
            "on 21 October 2026: 15 situations, each with a line, a start and no end (the publisher "
            "removes an event when it is over)."
        ),
    )


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    return datex.situation_record(
        item,
        source_id=SOURCE_ID,
        url=SOURCE_URL,
        attribution=ATTRIBUTION,
        default_authority="CITA",
        zone=LUXEMBOURG,
        retrieved_at=retrieved_at,
    )


class CitaTrafficEventsConnector:
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

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        body = datex.fetch_bytes(ENDPOINT, self._user_agent, client=self._client)
        records, observed, counts = datex.read_publication(
            body, ENDPOINT, now=now, build=lambda item: to_record(item, now)
        )
        # The feed lists every event in force or planned; the publisher removes
        # an event once it is over.
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
