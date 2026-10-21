"""Spain's national road incidents: DGT DATEX II 3.7 (decision 0034).

    GET https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml

The Dirección General de Tráfico (DGT) publishes, every minute, the incidents
in force on Spain's roads outside the Basque Country and Catalonia: works,
closures, lane restrictions, stuck vehicles, objects on the road, accidents,
rockfalls, flooding. It is DATEX II 3.7 in DGT's own profile ("DGT (Spain)
Profile RTTI SituationPublication 3.7_1.0"; namespaces `http://levelC/...`,
not datex2.eu), one situation holding one or more records. Every record
states its start (`overallStartTime`, with its UTC offset) and its position
in WGS 84: a point (`PointLocation`), or the from and to points of a road
section (`SingleRoadLinearLocation`; no line is drawn between them, so none
is drawn here). Most records also state an end. Fetched without a key on
21 October 2026: 835 situations, 1,404 records, 996 with an end.

The event is put at the record's point, or at the `from` point of its
section (where the section starts); both points of a section are kept as its
locations, with the road, kilometre point, municipality and province the
source gives for each. Nothing is drawn between them.

The type comes from the record and its cause, in DATEX's own codes:
a road, carriageway or intermittent closure is a planned road closure when
caused by road maintenance and an emergency closure otherwise; lane closures,
alternating one-way traffic, narrow lanes, lane changes and the like are
lane restrictions; otherwise flooding is flooding, an accident an accident,
roadworks road works, and stuck vehicles, objects or spillages on the road,
rockfalls, damaged surfaces and poor conditions road hazards. AbnormalTraffic
records describe the traffic (slow traffic), not a road event, and are not
taken (as for Hamburg). Anything else keeps its codes with no type.

The Canary Islands (an hour behind the mainland) are outside the "spain"
entry's area: their records are stored as evidence, but no event is made.
The console shows an entry's events in one time zone (Europe/Madrid here;
`source_time_zones` is per source, and this source covers both zones).

Licence: "Creative Commons Attribution" (cc-by, no version stated), as the
NAP's dataset and resource pages state (read 21 October 2026); credit the
Dirección General de Tráfico. The NAP gives DGT's legal notice as the
condition for use (docs/data-sources/spain-connectors-2026-10-21.md).
"""

import re
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
)

from .common import fetch_text, select_for_run

SOURCE_ID = "dgt-spain-incidents"  # the id it was catalogued under (connectors/discovered.py until 21 Oct 2026)
ENDPOINT = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml"
SOURCE_URL = "https://nap.dgt.es/en/dataset/incidencias-dgt-datex2-v3-7"
ATTRIBUTION_TEMPLATE = (
    "Source: Dirección General de Tráfico (DGT), National Access Point (nap.dgt.es). "
    "Retrieved {date}. Creative Commons Attribution."
)
ATTRIBUTION = (
    "Dirección General de Tráfico (DGT), via the National Access Point nap.dgt.es "
    "(Creative Commons Attribution)"
)
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

# roadOrCarriagewayOrLaneManagementType codes.
CLOSURES = frozenset({"roadClosed", "carriagewayClosures", "intermittentShortTermClosures"})
LANES = frozenset(
    {
        "laneClosures",
        "singleAlternateLineTraffic",
        "narrowLanes",
        "newRoadworksLayout",
        "useOfSpecifiedLanesOrCarriagewaysAllowed",
        "doNotUseSpecifiedLanesOrCarriageways",
        "lanesDeviated",
        "contraflow",
    }
)
# Record kinds and causes that state a hazard on the road.
HAZARD_KINDS = frozenset(
    {
        "GeneralObstruction",
        "VehicleObstruction",
        "AnimalPresenceObstruction",
        "EnvironmentalObstruction",
        "InfrastructureDamageObstruction",
        "NonWeatherRelatedRoadConditions",
        "PoorEnvironmentConditions",
        "WeatherRelatedRoadConditions",
        "GeneralInstructionOrMessageToRoadUsers",
    }
)
HAZARD_CAUSES = frozenset(
    {
        "vehicleObstruction",
        "obstruction",
        "environmentalObstruction",
        "infrastructureDamageObstruction",
        "poorEnvironment",
        "animalPresence",
    }
)
# Traffic-flow records: they describe the traffic, not an event on the road.
NOT_TAKEN = frozenset({"AbnormalTraffic"})
COMPASS = {
    "northBound": EventDirection.NORTHBOUND.value,
    "southBound": EventDirection.SOUTHBOUND.value,
    "eastBound": EventDirection.EASTBOUND.value,
    "westBound": EventDirection.WESTBOUND.value,
}
# Sub-type codes a record may carry, read for its words.
SUBTYPE_FIELDS = (
    "roadOrCarriagewayOrLaneManagementType",
    "obstructionType",
    "vehicleObstructionType",
    "poorEnvironmentType",
    "nonWeatherRelatedRoadConditionType",
    "speedManagementType",
    "generalInstructionToRoadUsersType",
    "genericSituationRecordName",
)


def dgt_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("spain")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="DGT road incidents, Spain (DATEX II 3.7)",
        organization="Dirección General de Tráfico (DGT), Ministerio del Interior",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Spain except the Basque Country and Catalonia",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Public DATEX II 3.7 XML snapshot from the National Access Point; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="es",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.ACCIDENT.value,
            EventType.FLOODING.value,
            EventType.ROAD_HAZARD.value,
        ),
        parser_type="spain_dgt_datex_ii_37",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="robots.txt asks a 10-second crawl delay; one 5-7 MB snapshot per poll, hourly.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "Creative Commons Attribution (cc-by; no version stated), per the NAP dataset and "
            "resource pages"
        ),
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each DATEX II situation record as XML plus the derived structured event.",
        notes=(
            "Incidents in force on Spain's roads outside the Basque Country and Catalonia, each a "
            "WGS 84 point or the from/to points of a section, with a start (and an end on most). "
            "Fetched without a key on 21 October 2026: 835 situations, 1,404 records, 996 with an "
            "end. The NAP's 'condition for use' is DGT's website legal notice, which reserves "
            "unauthorised commercial use of the portal's works 'unless stated otherwise'; the "
            "dataset itself is labelled Creative Commons Attribution. Canary Islands records fall "
            "outside the 'spain' entry's area and make no event."
        ),
    )


# --- reading the XML ------------------------------------------------------------------


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next((child for child in element if _local(child) == name), None)


def _path(element: ET.Element | None, *names: str) -> ET.Element | None:
    for name in names:
        element = _child(element, name)
    return element


def _text(element: ET.Element | None) -> str:
    return " ".join((element.text or "").split()) if element is not None else ""


def _xsi_type(element: ET.Element | None) -> str:
    return (element.attrib.get(XSI_TYPE, "") if element is not None else "").rsplit(":", 1)[-1]


def _datetime(value: str) -> datetime | None:
    """A DATEX time, which states its offset ("2026-10-21T07:00:00.000+02:00")."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None
    return moment if moment is not None and moment.tzinfo is not None else None


def _words(code: str) -> str:
    """A DATEX code in words: "singleAlternateLineTraffic" -> "single alternate line traffic"."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", code).lower().strip()


def _point(point: ET.Element | None) -> dict[str, Any] | None:
    """A TPEG point: its WGS 84 position and the place DGT gives for it."""
    coordinates = _child(point, "pointCoordinates")
    try:
        latitude = float(_text(_child(coordinates, "latitude")))
        longitude = float(_text(_child(coordinates, "longitude")))
    except ValueError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    place = _path(point, "_tpegNonJunctionPointExtension", "extendedTpegNonJunctionPoint")
    found = {
        name: _text(_child(place, name))
        for name in ("kilometerPoint", "municipality", "province", "autonomousCommunity")
    }
    return {"geometry": {"type": "Point", "coordinates": [longitude, latitude]}, **found}


def _location(record: ET.Element) -> dict[str, Any]:
    """What the record's location reference states: road, points, directions."""
    reference = _child(record, "locationReference")
    road = _path(reference, "supplementaryPositionalDescription", "roadInformation")
    found: dict[str, Any] = {
        "kind": _xsi_type(reference),
        "road": _text(_child(road, "roadName")),
        "destination": _text(_child(road, "roadDestination")),
        "points": [],
    }
    linear = _child(reference, "tpegLinearLocation")
    simple = _child(reference, "tpegPointLocation")
    if linear is not None:
        found["direction"] = _text(_child(linear, "tpegDirection"))
        found["road_direction"] = _text(
            _path(linear, "_tpegLinearLocationExtension", "extendedTpegLinearLocation", "tpegDirectionRoad")
        )
        # `from` first: the section starts there.
        for role in ("from", "to"):
            point = _point(_child(linear, role))
            if point:
                found["points"].append({"role": role, **point})
    elif simple is not None:
        found["direction"] = _text(_child(simple, "tpegDirection"))
        found["road_direction"] = _text(
            _path(simple, "_tpegSimplePointExtension", "extendedTpegSimplePoint", "tpegDirectionRoad")
        )
        point = _point(_child(simple, "point"))
        if point:
            found["points"].append({"role": "point", **point})
    return found


def _cause(record: ET.Element) -> tuple[str, str]:
    """The cause code and its detailed code ("roadMaintenance", "roadworks")."""
    cause = _child(record, "cause")
    detail = _child(cause, "detailedCauseType")
    detailed = next((_text(child) for child in detail if _text(child)), "") if detail is not None else ""
    return _text(_child(cause, "causeType")), detailed


def event_type(kind: str, management: str, cause: str, detail: str) -> str | None:
    """The REI type a record's DATEX codes state (see the module notes)."""
    if kind == "RoadOrCarriagewayOrLaneManagement" and management in CLOSURES:
        if cause == "roadMaintenance":
            return EventType.PLANNED_ROAD_CLOSURE.value
        return EventType.EMERGENCY_ROAD_CLOSURE.value
    if kind == "RoadOrCarriagewayOrLaneManagement" and management in LANES:
        return EventType.LANE_RESTRICTION.value
    if detail == "flooding":
        return EventType.FLOODING.value
    if cause == "accident" or kind == "Accident":
        return EventType.ACCIDENT.value
    if cause == "roadMaintenance" or kind in {"MaintenanceWorks", "ConstructionWorks"}:
        return EventType.ROAD_WORKS.value
    if cause in HAZARD_CAUSES or kind in HAZARD_KINDS:
        return EventType.ROAD_HAZARD.value
    return None


def _direction(location: dict[str, Any]) -> str | None:
    """An EventDirection only when the source states one for the whole record."""
    if location.get("road_direction") == "both":
        return EventDirection.BOTH_DIRECTIONS.value
    return COMPASS.get(location.get("direction") or "")


def _town(point: dict[str, Any]) -> str:
    """"Ontígola (Toledo)": the municipality and province DGT gives for a point."""
    town, province = point.get("municipality") or "", point.get("province") or ""
    if town and province and town != province:
        return f"{town} ({province})"
    return town or province


def _place_name(road: str, point: dict[str, Any]) -> str:
    """"N-400 km 37.1, Ontígola (Toledo)", from what DGT gives for the point."""
    km = f"km {point['kilometerPoint']}" if point.get("kilometerPoint") else ""
    name = " ".join(part for part in (road, km) if part)
    return ", ".join(part for part in (name, _town(point)) if part) or "Spain"


def _label(kind: str, management: str, detail: str, subtypes: list[str], name: str) -> str:
    """What the record is, in its own codes: the most specific one that is not "other"
    (its own sub-type, then its cause, then the generic record name, then its kind)."""
    for code in (management, *subtypes, detail, name, kind):
        if code and code != "other":
            return _words(code).capitalize()
    return "Road event"


def to_record(
    situation: ET.Element, record: ET.Element, retrieved_at: datetime
) -> RawSourceRecord | None:
    record_id = record.attrib.get("id")
    situation_id = situation.attrib.get("id") or "situation"
    kind = _xsi_type(record)
    if not record_id or kind in NOT_TAKEN:
        return None
    location = _location(record)
    if not location["points"]:
        return None  # nothing located: this feed always gives a point (21 October 2026)
    # The record's own codes (a cause may repeat one: SpeedManagement caused by
    # "roadOrCarriagewayOrLaneManagement / other").
    management = _text(_child(record, "roadOrCarriagewayOrLaneManagementType"))
    cause, detail = _cause(record)
    subtypes = [code for name in SUBTYPE_FIELDS if (code := _text(_child(record, name)))]
    generic_name = _text(_child(record, "genericSituationRecordName"))
    speed_limit = _text(_child(record, "temporarySpeedLimit"))
    kind_of_event = event_type(kind, management, cause, detail)
    validity = _path(record, "validity", "validityTimeSpecification")
    start = _datetime(_text(_child(validity, "overallStartTime")))
    end = _datetime(_text(_child(validity, "overallEndTime")))
    status = _text(_path(record, "validity", "validityStatus"))
    severity = _text(_child(record, "severity")) or _text(_child(situation, "overallSeverity"))
    road = location["road"]
    first = location["points"][0]
    geometry = first["geometry"]
    compass_words = location.get("direction") or ""
    direction_words = "; ".join(
        part
        for part in (
            _words(compass_words) if compass_words != "unknown" else "",
            f"road direction {location['road_direction']}" if location.get("road_direction") else "",
        )
        if part
    )
    locations = [
        SourceLocation(
            name=f"{'From' if point['role'] == 'from' else 'To' if point['role'] == 'to' else 'At'}: "
            f"{_place_name(road, point)}",
            kind={"from": "section start", "to": "section end"}.get(point["role"], "point"),
            geometry=point["geometry"],
            direction=direction_words or None,
            closure=management or None,
            reference=point.get("autonomousCommunity") or None,
        )
        for point in location["points"]
    ]
    label = _label(
        kind,
        management,
        detail,
        [code for code in subtypes if code not in (management, generic_name)],
        generic_name,
    )
    # The cause's detail, when it adds to the label ("Lane closures (roadworks)").
    reason = _words(detail) if detail not in ("", "other") and _words(detail).capitalize() != label else ""
    points = location["points"]
    if len(points) == 2 and points[0].get("kilometerPoint") and points[1].get("kilometerPoint"):
        place = ", ".join(
            part
            for part in (
                f"{road} km {points[0]['kilometerPoint']}–{points[1]['kilometerPoint']}".strip(),
                _town(points[0]),
            )
            if part
        )
    else:
        place = _place_name(road, first)
    title = f"{label}{f' ({reason})' if reason else ''}: {place}"
    summary = ". ".join(
        part
        for part in (
            title,
            f"Towards {location['destination']}" if location.get("destination") else "",
            f"Direction: {direction_words}" if direction_words else "",
            f"Cause: {' / '.join(_words(code) for code in (cause, detail) if code)}" if cause else "",
            # Verbatim: some values (1.0, 2.0) cannot be km/h, so no unit is added.
            f"Temporary speed limit stated: {speed_limit}" if speed_limit else "",
            points[0].get("autonomousCommunity") or "",
        )
        if part
    )
    record_xml = ET.tostring(record, encoding="unicode")
    structured = SourceEvent(
        event_type=kind_of_event,
        category=" / ".join(part for part in (kind, management, cause, detail) if part),
        severity=severity or None,
        status=status or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=locations,
        affected_road=road or None,
        direction=_direction(location),
        attribution=ATTRIBUTION_TEMPLATE.format(date=retrieved_at.date().isoformat()),
        covers_city=True,
    )
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=f"{situation_id}:{record_id}",
        url=SOURCE_URL,
        title=title,
        summary=summary,
        content_text=summary,
        categories=[part for part in (kind, management, cause, detail) if part],
        published_at=_datetime(_text(_child(record, "situationRecordVersionTime"))),
        retrieved_at=retrieved_at,
        raw={
            "situation_id": situation_id,
            "record_id": record_id,
            "version": record.attrib.get("version"),
            "xml": record_xml,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=sha256_hex(record_xml),
        structured=structured,
    )


def read_situations(body: str, retrieved_at: datetime) -> tuple[list[RawSourceRecord], set[str]]:
    """Every taken record of the snapshot's real situations, and their ids."""
    try:
        root = ET.fromstring(body.lstrip("﻿"))
    except ET.ParseError as error:
        raise ConnectorError(f"{ENDPOINT} did not return valid DATEX II XML: {error}") from error
    if _local(root) != "payload":
        raise ConnectorError(f"{ENDPOINT} did not return a DATEX II payload (root {_local(root)!r})")
    records: list[RawSourceRecord] = []
    for situation in root.iter():
        if _local(situation) != "situation":
            continue
        status = _text(_path(situation, "headerInformation", "informationStatus")) or "real"
        if status.lower() != "real":
            continue  # test or exercise messages
        for source_record in situation:
            if _local(source_record) != "situationRecord":
                continue
            record = to_record(situation, source_record, retrieved_at)
            if record is not None:
                records.append(record)
    return records, {record.external_id for record in records}


class SpainDgtIncidentsConnector:
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
        retrieved_at = self._clock()
        records, observed = read_situations(body, retrieved_at)
        # The snapshot lists every incident DGT holds in force.
        self.observed_ids = observed
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.published_at or record.retrieved_at,
            limit=self.max_records,
        )
