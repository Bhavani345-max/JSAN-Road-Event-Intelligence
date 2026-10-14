"""France's open, nationwide DATEX II road-event feed (non-concession roads)."""

import xml.etree.ElementTree as ET
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
    too_short_road_block,
)

from .common import select_for_run
from .common import fetch_text

SOURCE_ID = "france-bison-fute-road-events"
ENDPOINT = "https://transport.data.gouv.fr/resources/79174/download"
SOURCE_PAGE = "https://transport.data.gouv.fr/datasets/evenements-routiers-sur-le-reseau-routier-national-non-concede/"
NAMESPACE = "{http://datex2.eu/schema/2/2_0}"
ATTRIBUTION_TEMPLATE = (
    "Source: French Interdepartmental Road Directorates (DIR), via Bison Futé / "
    "transport.data.gouv.fr. Retrieved {date}. Licence Ouverte 2.0."
)


def bison_fute_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("france")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="French national road events (Bison Futé / DIR)",
        organization="French Ministry of Transport; Interdepartmental Road Directorates",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="France",
        city=country.id,
        source_url=SOURCE_PAGE,
        endpoint=ENDPOINT,
        access_method="Public nationwide DATEX II XML snapshot; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="fr",
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="bison_fute_datex_ii",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="No request limit published; one 4–5 MB aggregate download per poll.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Licence Ouverte / Open Licence version 2.0 (Etalab)",
        attribution="Name the producing authority, source, retrieval date and Licence Ouverte 2.0.",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each DATEX II situation record as XML plus the derived structured event.",
        notes=(
            "Covers current and forecast events on France's non-concession national road "
            "network: roadworks, closures, diversions, accidents and hazards. The aggregate "
            "XML endpoint was fetched successfully without credentials on 13 October 2026; "
            "the publisher updates the aggregate hourly. France's concessioned motorways "
            "are outside this feed."
        ),
    )


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _first_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child) == name and child.text and child.text.strip():
            return child.text.strip()
    return None


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _record_type(record: ET.Element) -> str:
    for key, value in record.attrib.items():
        if key.endswith("}type"):
            return value.rsplit(":", 1)[-1]
    return ""


def _description(record: ET.Element) -> str | None:
    descriptions: list[str] = []
    for comment in record.iter(NAMESPACE + "comment"):
        kind = _first_text(comment, "commentType")
        value = _first_text(comment, "value")
        if value and (kind or "").lower() == "description" and value not in descriptions:
            descriptions.append(value)
    return "\n".join(descriptions) or None


def _descriptors(record: ET.Element) -> tuple[list[str], list[str]]:
    towns: list[str] = []
    roads: list[str] = []
    for descriptor in record.iter():
        if _local_name(descriptor) != "tpegOtherPointDescriptor":
            continue
        kind = _first_text(descriptor, "tpegOtherPointDescriptorType")
        value = _first_text(descriptor, "value")
        if not value:
            continue
        target = towns if (kind or "").lower() == "townname" else roads
        if value not in target:
            target.append(value)
    road_number = _first_text(record, "roadNumber")
    if road_number and road_number not in roads:
        roads.insert(0, road_number)
    return towns, roads


def _geometry(record: ET.Element) -> dict[str, Any] | None:
    # The feed publishes a precise DATEX point for each record. Other location
    # references can be linear identifiers rather than GeoJSON linework.
    try:
        latitude = float(_first_text(record, "latitude") or "")
        longitude = float(_first_text(record, "longitude") or "")
    except ValueError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _event_type(record: ET.Element) -> str | None:
    record_type = _record_type(record)
    if record_type == "Accident":
        return EventType.ACCIDENT.value
    if record_type in {"MaintenanceWorks", "ConstructionWorks"}:
        return EventType.ROAD_WORKS.value
    if record_type == "ReroutingManagement":
        return EventType.TRAFFIC_DIVERSION.value
    if record_type == "RoadOrCarriagewayOrLaneManagement":
        subtype = (_first_text(record, "roadOrCarriagewayOrLaneManagementType") or "").lower()
        if "closure" in subtype or "closed" in subtype:
            return EventType.PLANNED_ROAD_CLOSURE.value
        if "lane" in subtype or "restriction" in subtype:
            return EventType.LANE_RESTRICTION.value
        return EventType.ROAD_HAZARD.value
    if record_type in {
        "AbnormalTraffic",
        "AnimalPresenceObstruction",
        "EnvironmentalObstruction",
        "GeneralObstruction",
        "InfrastructureDamageObstruction",
        "VehicleObstruction",
        "WeatherRelatedRoadConditions",
    }:
        return EventType.ROAD_HAZARD.value
    if record_type in {"SpeedManagement", "GeneralNetworkManagement", "GeneralInstructionOrMessageToRoadUsers"}:
        return EventType.ROAD_HAZARD.value
    return None


def _direction(record: ET.Element) -> str | None:
    value = (_first_text(record, "tpegDirection") or "").lower()
    if value in {"bothways", "bothdirections"}:
        return EventDirection.BOTH_DIRECTIONS.value
    return None


def to_record(
    situation: ET.Element,
    record: ET.Element,
    retrieved_at: datetime,
) -> RawSourceRecord | None:
    record_id = record.attrib.get("id") or situation.attrib.get("id")
    if not record_id:
        return None
    # Record IDs are usually globally unique; include the parent ID for feeds
    # that only guarantee uniqueness within a situation.
    external_id = f"{situation.attrib.get('id', 'situation')}:{record_id}"
    geometry = _geometry(record)
    towns, roads = _descriptors(record)
    road = roads[0] if roads else None
    town = towns[0] if towns else None
    label = {
        EventType.ACCIDENT.value: "Accident",
        EventType.ROAD_WORKS.value: "Roadworks",
        EventType.TRAFFIC_DIVERSION.value: "Traffic diversion",
        EventType.PLANNED_ROAD_CLOSURE.value: "Planned road closure",
        EventType.LANE_RESTRICTION.value: "Lane restriction",
        EventType.ROAD_HAZARD.value: "Road hazard",
    }.get(_event_type(record), "Road event")
    place = " near ".join(part for part in (road, town) if part)
    title = f"{label}: {place}" if place else f"{label} ({record_id})"
    description = _description(record)
    record_xml = ET.tostring(record, encoding="unicode")
    attribution = ATTRIBUTION_TEMPLATE.format(date=retrieved_at.date().isoformat())
    locations = [
        SourceLocation(name=name, kind="road or locality", geometry=geometry)
        for name in [*roads, *towns]
    ]
    if not locations and geometry:
        locations = [SourceLocation(name=title, kind="road event", geometry=geometry)]

    structured = SourceEvent(
        event_type=_event_type(record),
        category=" / ".join(part for part in (_record_type(record), _first_text(record, "roadOrCarriagewayOrLaneManagementType")) if part),
        severity=_first_text(situation, "overallSeverity"),
        start=_datetime(_first_text(record, "overallStartTime")),
        end=_datetime(_first_text(record, "overallEndTime")),
        geometry=geometry,
        locations=locations,
        affected_road=road,
        direction=_direction(record),
        attribution=attribution,
        # The feed is scoped to France; entries without a coordinate remain
        # visible as unresolved records instead of receiving guessed points.
        covers_city=True,
    )
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_PAGE,
        title=title,
        summary=description,
        content_text=description,
        categories=[_record_type(record)] if _record_type(record) else [],
        published_at=_datetime(_first_text(record, "situationRecordVersionTime")),
        retrieved_at=retrieved_at,
        raw={
            "situation_id": situation.attrib.get("id"),
            "record_id": record_id,
            "version": record.attrib.get("version"),
            "xml": record_xml,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=sha256_hex(record_xml),
        structured=structured,
    )


class BisonFuteRoadEventsConnector:
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
        return sha256_hex(str(raw.get("xml", "")))

    def fetch(self) -> list[RawSourceRecord]:
        body = fetch_text(ENDPOINT, self._user_agent, client=self._client)
        try:
            root = ET.fromstring(body)
        except ET.ParseError as error:
            raise ConnectorError(f"{ENDPOINT} did not return valid DATEX II XML: {error}") from error

        retrieved_at = self._clock()
        records: list[RawSourceRecord] = []
        observed: set[str] = set()
        for situation in root.iter(NAMESPACE + "situation"):
            if (_first_text(situation, "informationStatus") or "real").lower() != "real":
                continue
            for source_record in situation.findall(NAMESPACE + "situationRecord"):
                record = to_record(situation, source_record, retrieved_at)
                if record:
                    records.append(record)
                    observed.add(record.external_id)

        self.observed_ids = observed
        records = [record for record in records if too_short_road_block(record.structured) is None]
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.published_at or record.retrieved_at,
            limit=self.max_records,
        )
