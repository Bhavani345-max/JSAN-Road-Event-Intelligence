"""Basque Country traffic incidences (Open Data Euskadi), Spain (decision 0034).

    GET https://api.euskadi.eus/traffic/v1.0/incidences/byDate/<yyyy>/<mm>/<dd>?_page=<n>

The Basque Government's traffic API gathers the incidences of several Basque
road administrations, each marked by its `sourceId`. `byDate` lists a day's
incidences, 20 a page with `totalPages` stated. Each gives its id (unique
only within its `sourceId`: id 1683 was both a Bilbao and a Donostia record
on 21 October 2026), type (`incidenceType`), cause, a name or description
(`incidenceName`, with HTML character references), road and kilometre points,
direction, province and town, level (`incidenceLevel`), a WGS 84 point
(`latitude`, `longitude`, as text), a start (`startDate`) and, for most
city-council records, an end (`endDate`). Times are Madrid local time
written without an offset, with or without seconds.

Fetched without a key on 21 October 2026 (today's list, 11 pages): 203
incidences, 202 distinct. The region-wide road incidences (sourceId 1:
works, breakdowns, accidents across the three provinces, with road and
kilometre point) were all started that day and state no end; the records of
sourceId 5, 6 and 7 (all in Bilbao, Vitoria-Gasteiz and Donostia
respectively: street works and occupations) include ones started weeks
before, each with an end. Bilbao's and Donostia's records write every start
and end at 00:00; they are read as written, so a work whose stated end is
today at 00:00 has ended for REI.

A run reads today's list (today in Madrid). An incidence dropping out of it
does not say it ended (the region-wide list holds only the day's starts), so
no `observed_ids` is reported, and nothing is counted missing.

The type comes from `incidenceType`, whatever its spelling or case: Obra,
Obras and Mantenimiento are road works, Accidente an accident, Seguridad
vial (breakdowns, spills, landslips), Meteorológica and Vialidad invernal
road hazards. Retención (queues) describes the traffic, not a road event, and
is not taken (as for Hamburg), nor is a closure to pedestrians only ("CORTE
DE TRAFICO PEATONAL", as Tokushima's pavement restrictions). Any other type
(Otros, OTRO, EVEN, none) keeps its words with no type.

Licence: Creative Commons Reconocimiento 4.0 (CC BY 4.0) per Open Data
Euskadi's legal page, which also asks that the information not be altered,
its source be cited and the date of its last update be mentioned
(docs/data-sources/spain-connectors-2026-10-21.md).
"""

import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
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
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from .common import content_key, fetch_json, select_for_run
from .feature_feed import clean, item_record, local_time

SOURCE_ID = "euskadi-traffic-incidences"
ENDPOINT = "https://api.euskadi.eus/traffic/v1.0/incidences/byDate/{year:04d}/{month:02d}/{day:02d}"
SOURCE_URL = "https://opendata.euskadi.eus/api-traffic/?api=traffic"
ATTRIBUTION_TEMPLATE = (
    "Source: Gobierno Vasco / Eusko Jaurlaritza, Open Data Euskadi traffic API (CC BY 4.0). "
    "Data as listed on {date}."
)
ATTRIBUTION = (
    "Gobierno Vasco / Eusko Jaurlaritza, Open Data Euskadi (CC BY 4.0); "
    "cite the source and the date of the last update"
)
MADRID = ZoneInfo("Europe/Madrid")
TIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M")
# 203 incidences on 21 October 2026 were 11 pages; more than this is not one day's list.
MAX_PAGES = 40
# incidenceType, case-folded: the REI type and an English label.
TYPES = {
    "obra": (EventType.ROAD_WORKS.value, "Road works"),
    "obras": (EventType.ROAD_WORKS.value, "Road works"),
    "mantenimiento": (EventType.ROAD_WORKS.value, "Maintenance works"),
    "accidente": (EventType.ACCIDENT.value, "Accident"),
    "seguridad vial": (EventType.ROAD_HAZARD.value, "Road safety"),
    "meteorológica": (EventType.ROAD_HAZARD.value, "Weather"),
    "vialidad invernal": (EventType.ROAD_HAZARD.value, "Winter road conditions"),
}
# Traffic-flow messages: they describe the traffic, not an event on the road.
NOT_TAKEN_TYPES = frozenset({"retención", "retenciones"})
# A closure to pedestrians only is not road traffic.
NOT_TAKEN_NAMES = frozenset({"corte de trafico peatonal", "corte de tráfico peatonal"})
# Donostia's name for a record without one; its cause then describes it.
UNTITLED = frozenset({"sin título", "sin titulo"})


def euskadi_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("spain")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Basque Country traffic incidences (Open Data Euskadi)",
        organization="Gobierno Vasco / Eusko Jaurlaritza (Basque Government)",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Basque Country (Euskadi)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint="https://api.euskadi.eus/traffic/v1.0/incidences/byDate/{yyyy}/{mm}/{dd}",
        access_method="Open Data Euskadi traffic REST API (JSON), today's incidences, 20 a page; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="es",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.ACCIDENT.value,
            EventType.ROAD_HAZARD.value,
        ),
        parser_type="euskadi_traffic_incidences",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; about 10 page requests per hourly poll.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (Creative Commons Reconocimiento 4.0, Open Data Euskadi legal page)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each incidence as received.",
        notes=(
            "Incidences on Basque roads and streets, each a point with a start. The region-wide "
            "road incidences (sourceId 1) state no end; the Bilbao, Vitoria-Gasteiz and "
            "Donostia records state one. Fetched without a key on 21 October "
            "2026: 203 incidences for the day (11 pages). The legal page asks that the data not "
            "be altered, the source be cited and its last update date be mentioned."
        ),
    )


def _text(value: Any) -> str:
    """Text with its HTML character references read ("V&#205;A" -> "VÍA")."""
    return clean(html.unescape(clean(value)))


def _number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except ValueError:
        return None


def _shorten(text: str, limit: int = 110) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    incidence, administration = clean(item.get("incidenceId")), clean(item.get("sourceId"))
    kind = _text(item.get("incidenceType"))
    name = _text(item.get("incidenceName"))
    if name.casefold() in UNTITLED:
        name = ""
    latitude, longitude = _number(item.get("latitude")), _number(item.get("longitude"))
    if not incidence or kind.casefold() in NOT_TAKEN_TYPES or name.casefold() in NOT_TAKEN_NAMES:
        return None
    if latitude is None or longitude is None or (latitude == 0 and longitude == 0):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    geometry = {"type": "Point", "coordinates": [longitude, latitude]}
    event_type, label = TYPES.get(kind.casefold(), (None, kind.capitalize() if kind else "Incidence"))
    cause = _text(item.get("cause"))
    # sourceId 1 and Bilbao repeat the type as the cause ("Obras" / "Obras");
    # Donostia writes a description there.
    own_cause = cause if cause.casefold() != kind.casefold() else ""
    road = clean(item.get("road"))
    town, province = _text(item.get("cityTown")), _text(item.get("province"))
    direction = _text(item.get("direction"))
    area = f"{town} ({province})" if town and province else town or province
    if road:
        # Kilometre points only with a road: without one they are 0.0 or not kilometres.
        start_km, end_km = clean(item.get("pkStart")), clean(item.get("pkEnd"))
        if start_km and end_km and start_km != end_km:
            subject = f"{road} km {start_km}–{end_km}"
        else:
            subject = f"{road} km {start_km or end_km}" if (start_km or end_km) else road
    else:
        subject = _shorten(name or own_cause)
    reason = f" ({own_cause})" if road and own_cause else ""
    place = ", ".join(part for part in (subject, area) if part) or "Basque Country"
    start_words, end_words = clean(item.get("startDate")), clean(item.get("endDate"))
    level = _text(item.get("incidenceLevel"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (kind, own_cause) if part) or None,
        severity=level or None,
        start=local_time(start_words, MADRID, TIME_FORMATS),
        end=local_time(end_words, MADRID, TIME_FORMATS),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind="incidence point",
                geometry=geometry,
                direction=direction or None,
            )
        ],
        affected_road=road or None,
        attribution=ATTRIBUTION_TEMPLATE.format(date=retrieved_at.date().isoformat()),
        stated_period=(
            f"startDate {start_words}"
            + (f" – endDate {end_words}" if end_words else " (no end stated)")
            + " (Madrid time)"
        ),
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"{administration or '0'}-{incidence}",
        url=SOURCE_URL,
        title=f"{label}{reason}: {place}",
        summary=". ".join(
            part
            for part in (
                f"{kind}: {own_cause}" if kind and own_cause else kind or cause,
                name,
                f"Direction / at: {direction}" if direction else "",
                f"Level: {level}" if level else "",
                ", ".join(part for part in (area, _text(item.get("autonomousRegion"))) if part),
            )
            if part
        )
        or None,
        categories=[part for part in (kind, cause) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_day(user_agent: str, day, *, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Every incidence listed for `day`, page by page."""
    url = ENDPOINT.format(year=day.year, month=day.month, day=day.day)
    items: list[dict[str, Any]] = []
    page, pages = 1, 1
    while page <= pages:
        body = fetch_json(url, user_agent, client=client, params={"_page": str(page)})
        batch = body.get("incidences") if isinstance(body, dict) else None
        if not isinstance(batch, list):
            raise ConnectorError(f"{url} did not return a list of incidences")
        items.extend(item for item in batch if isinstance(item, dict))
        stated = body.get("totalPages")
        pages = stated if isinstance(stated, int) and stated > 0 else page
        if pages > MAX_PAGES:
            raise ConnectorError(f"{url} lists {pages} pages, more than {MAX_PAGES}")
        if not batch:
            break
        page += 1
    return items


class EuskadiTrafficIncidencesConnector:
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
        # Dropping out of the day's list does not say an incidence ended (the
        # region-wide list holds only the day's starts): no `observed_ids` is
        # reported, and nothing is counted missing.

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("item", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        items = fetch_day(self._user_agent, now.astimezone(MADRID).date(), client=self._client)
        records: dict[str, RawSourceRecord] = {}
        for item in items:
            record = to_record(item, now)
            # An incidence listed twice (a page boundary moving during the run) is one.
            if record is not None:
                records.setdefault(record.external_id, record)
        return select_for_run(
            list(records.values()),
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
