"""New Plymouth District Council corridor access requests (CARs), New Zealand (5 November 2026).

    GET https://services2.arcgis.com/JthOmqz8HxPqljUO/arcgis/rest/services/
        OpenData_Infrastructure_Transport/FeatureServer/{2,3,4}/query

New Plymouth District Council (NPDC) publishes the corridor access requests
for work and events in its road corridor (the council's open data service
"NPDC Open Data Service - Infrastructure Transport", ArcGIS item
c28e56105e184ccb86a47e598dd9328f, owner NPDC.GeoHUB, reloaded nightly), in
three layers: points (CARPoint, 2), lines (CARLine, 3) and areas (CARPolygon,
4). Each feature is one mapped part of a CAR (`CAR_ID`): the kind of request
(`CAR_Type`: Excavation, Non Excavation, Preliminary, Retrospective, Event),
the activity (`Activity`), the street and town (`StreetName`, `Township`),
which parts of the road it occupies (`LocationInRoad`: Carriageway, Footpath,
Berm, Nature Strip), its step and status (`CAR_Step`, `CAR_Status`), whether a
road closure is required (`RoadClosureRequired`), whether traffic is disrupted
(`TrafficDisruption`), the temporary traffic management level of the road
(`TTM_RoadLevel`), the organisations involved, and its dates: the estimated
start and completion (`EstimatedStartDate`, `EstimatedCompletionDate`) and the
work start and completion (`DateWorkStart`, `DateWorkComplete`, each with its
status: Actual, Proposed, Revised; a completion not yet known is null and
"Unknown"). Dates are milliseconds since 1970 at midnight UTC: dates only.
Fetched without a key on 5 November 2026: 3,669 features of 2,791 CARs (1,362
points, 1,276 lines, 1,031 areas), of which 2,322 are in their warranty
period (done) or closed; one CAR has up to 369 parts, 15 have parts in two
layers, and every CAR's parts state the same fields.

A CAR is one event: REI asks for the CARs not in their warranty period or
closed (962 features of 469 CARs on 5 November 2026) and keeps one record per
CAR, its geometry being its own parts: its areas (a MultiPolygon when there
are several), else its lines, else one of its points (REI has no multi-point
shape; the number of points is stated in the summary). The period runs from
the start of the work start day (else the estimated start) to the end of the
work completion day (else, while that is unknown, the estimated completion),
New Zealand time; the dates' statuses are kept in the stated period.

Left out, as not road events: CARs whose `LocationInRoad` is stated and does
not include the carriageway (berm, footpath or nature strip only: 54 of the
280 CARs in force or starting within a year on 5 November 2026), and CARs
declined or cancelled (3). 223 kept: 187 in force, 36 starting later (28
within 30 days); 14 require a road closure. A request for an event is an event (a parade: PUBLIC_
PROCESSION; a sport event or cycling: SPORTING_EVENT; else SPECIAL_EVENT; the
13 event CARs state no location in road); other requests are road works
(ROAD_WORKS), or a planned road closure (PLANNED_ROAD_CLOSURE) when they
require a road closure. A CAR whose work is completed (step Work Completion,
status Completion Notified) is marked ended by the source.

Personal data: `Creator` and `Editor` (accounts) are dropped, as are the layer
bookkeeping fields (`OBJECTID`, `CreationDate`, `EditDate`, `Shape__Length`,
`Shape__Area`), which change at each nightly reload. An organisation field is
kept only for the parts that name a registered company (Limited, Ltd,
Incorporated, Pty) or a public body (a council, the transport agency):
"private", "Sole Trader" or a trading name may be a person's. The free-text
fields (`WorkDescription`, `CauseOfDisruption`, empty on 5 November 2026) are
dropped when they hold an e-mail address or a phone number.

Licence: Creative Commons Attribution 4.0 International (the item's
licenseInfo, read 5 November 2026: "Licensed under Creative Commons
Attribution 4.0 International License", with NPDC's terms of use
https://geohub.npdc.govt.nz/pages/termsofuse); credit "New Plymouth District
Council (NPDC)" (the item's accessInformation).
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from packages.cities import get_city
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

from .feature_feed import FeatureFeedConnector, clean, fetch_arcgis_features, item_record, local_day, whole_days

SOURCE_ID = "nz-new-plymouth-corridor-access"
SOURCE_URL = (
    "https://services2.arcgis.com/JthOmqz8HxPqljUO/arcgis/rest/services/OpenData_Infrastructure_Transport/FeatureServer"
)
ITEM_URL = "https://www.arcgis.com/home/item.html?id=c28e56105e184ccb86a47e598dd9328f"
POINTS, LINES, AREAS = 2, 3, 4
LAYERS = (POINTS, LINES, AREAS)
# The CARs still to be done or under way: not those done (in warranty) or closed.
WHERE = "CAR_Step NOT IN ('Warranty Period', 'CAR Closed')"
ATTRIBUTION = "New Plymouth District Council (NPDC), CC BY 4.0"
NEW_ZEALAND = ZoneInfo("Pacific/Auckland")
# Accounts and layer bookkeeping: not kept.
DROPPED_FIELDS = frozenset({"Creator", "Editor", "OBJECTID", "CreationDate", "EditDate", "Shape__Length", "Shape__Area"})
ORGANISATION_FIELDS = (
    "ApplicantOrganisation",
    "UtilityOperatorOrganisation",
    "PrincipalOrganisation",
    "ContractorOrganisation",
)
FREE_TEXT_FIELDS = ("WorkDescription", "CauseOfDisruption")
_COMPANY_OR_PUBLIC_BODY = re.compile(
    r"\b(limited|ltd|incorporated|inc|pty|council|agency|nzta|waka kotahi|kiwirail)\b", re.IGNORECASE
)
_CONTACT = re.compile(r"@|\+?\d[\d\s\-()]{6,}\d")
NOT_GOING_AHEAD = frozenset({"Declined", "Cancelled"})
WORK_DONE_STEPS = frozenset({"Work Completion", "Warranty Period", "CAR Closed"})
WORK_DONE_STATUSES = frozenset({"Completion Notified", "Work Completion Notified"})


def new_plymouth_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("new-zealand")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="New Plymouth District Council corridor access requests",
        organization="New Plymouth District Council (NPDC)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Taranaki (New Plymouth District)",
        city=country.id,
        source_url=ITEM_URL,
        endpoint=SOURCE_URL,
        access_method="ArcGIS feature service (ArcGIS Online), GeoJSON, layers 2-4 (points, lines, areas); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.SPECIAL_EVENT.value,
            EventType.PUBLIC_PROCESSION.value,
            EventType.SPORTING_EVENT.value,
        ),
        parser_type="new_plymouth_corridor_access",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; reloaded nightly; polled every six hours (three requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), the item's licenseInfo",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention=(
            "Each CAR's fields once and its mapped parts, less the editing accounts, the layer "
            "bookkeeping and any organisation name that is not a company's or a public body's."
        ),
        notes=(
            "Corridor access requests for work and events in New Plymouth District's roads, one "
            "record per CAR with its own points, lines or areas. Fetched without a key on 5 November "
            "2026: 2,791 CARs; 280 in force or starting within a year; 54 off the carriageway and 3 "
            "declined left out; 223 kept (187 in force, 36 starting later); 14 require a road closure."
        ),
    )


def _organisations(value: Any) -> str | None:
    """The parts of an organisation field that name a company or a public body."""
    parts = [part for part in (clean(text) for text in clean(value).split(",")) if part]
    kept = [part for part in parts if _COMPANY_OR_PUBLIC_BODY.search(part)]
    return ", ".join(kept) or None


def stored_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """A CAR's fields as REI keeps them: no accounts, bookkeeping, or possible person's name."""
    kept = {key: value for key, value in properties.items() if key not in DROPPED_FIELDS}
    for field in ORGANISATION_FIELDS:
        if kept.get(field) is not None:
            kept[field] = _organisations(kept[field])
    for field in FREE_TEXT_FIELDS:
        if kept.get(field) is not None and _CONTACT.search(str(kept[field])):
            kept[field] = None
    return kept


def _joined(shapes: list[dict[str, Any]], single: str, multi: str) -> dict[str, Any] | None:
    """The parts of the shapes of one kind, each once, as one shape of that kind."""
    parts: list = []
    for shape in shapes:
        if shape.get("type") == single:
            found = [shape["coordinates"]]
        elif shape.get("type") == multi:
            found = list(shape["coordinates"])
        else:
            found = []
        parts.extend(part for part in found if part not in parts)
    if not parts:
        return None
    return {"type": single, "coordinates": parts[0]} if len(parts) == 1 else {"type": multi, "coordinates": parts}


def car_geometry(parts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The CAR's own shape: its areas, else its lines, else its first point (coordinate order)."""
    shapes = [part["geometry"] for part in parts if isinstance(part.get("geometry"), dict)]
    shape = _joined(shapes, "Polygon", "MultiPolygon") or _joined(shapes, "LineString", "MultiLineString")
    if shape is not None:
        return shape
    points = sorted({json.dumps(s["coordinates"]) for s in shapes if s.get("type") == "Point"})
    return {"type": "Point", "coordinates": json.loads(points[0])} if points else None


def _point_count(parts: list[dict[str, Any]]) -> int:
    return len({json.dumps(p["geometry"]["coordinates"]) for p in parts if (p.get("geometry") or {}).get("type") == "Point"})


def on_carriageway(properties: dict[str, Any]) -> bool:
    """False only when the CAR states where in the road it is and the carriageway is not among it."""
    where = clean(properties.get("LocationInRoad"))
    return not where or "carriageway" in where.lower()


def _event_type(properties: dict[str, Any]) -> str:
    activity = clean(properties.get("Activity")).lower()
    if clean(properties.get("CAR_Type")) == "Event":
        if "parade" in activity:
            return EventType.PUBLIC_PROCESSION.value
        if "sport" in activity or "cycling" in activity:
            return EventType.SPORTING_EVENT.value
        return EventType.SPECIAL_EVENT.value
    if clean(properties.get("RoadClosureRequired")).lower() == "yes":
        return EventType.PLANNED_ROAD_CLOSURE.value
    return EventType.ROAD_WORKS.value


_LABELS = {
    EventType.ROAD_WORKS.value: "Road works",
    EventType.PLANNED_ROAD_CLOSURE.value: "Road works with road closure",
    EventType.SPECIAL_EVENT.value: "Event",
    EventType.PUBLIC_PROCESSION.value: "Parade",
    EventType.SPORTING_EVENT.value: "Sport event",
}


def _day(properties: dict[str, Any], *fields: str):
    """The first of the fields that states a day (milliseconds at midnight UTC), read in NZ time."""
    return next((day for field in fields if (day := local_day(properties.get(field), NEW_ZEALAND))), None)


def _date_text(properties: dict[str, Any], field: str) -> str:
    day = _day(properties, field)
    return day.isoformat() if day else ""


def _stated_period(properties: dict[str, Any]) -> str:
    def stated(label: str, field: str, status_field: str) -> str:
        day, status = _date_text(properties, field), clean(properties.get(status_field))
        return f"{label} {day or 'not stated'}" + (f" ({status.lower()})" if status else "")

    estimated = " – ".join(
        (_date_text(properties, "EstimatedStartDate"), _date_text(properties, "EstimatedCompletionDate"))
    )
    return "; ".join(
        (
            stated("work start", "DateWorkStart", "DateWorkStartStatus"),
            stated("work completion", "DateWorkComplete", "DateWorkCompleteStatus"),
            f"estimated {estimated}",
        )
    )


def _stated(properties: dict[str, Any], label: str, field: str, ignore: tuple[str, ...] = ("",)) -> str:
    value = clean(properties.get(field))
    return f"{label}: {value}" if value not in ignore else ""


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One CAR as REI's record; None when it is not a road event or has no shape of its own."""
    properties = item.get("properties")
    parts = item.get("parts")
    car = clean(item.get("car"))
    if not car or not isinstance(properties, dict) or not isinstance(parts, list):
        return None
    if clean(properties.get("CAR_Status")) in NOT_GOING_AHEAD or not on_carriageway(properties):
        return None
    geometry = car_geometry(parts)
    if geometry is None:
        return None
    # The work dates; while the completion is unknown (null), the estimated completion.
    first = _day(properties, "DateWorkStart", "EstimatedStartDate")
    last = _day(properties, "DateWorkComplete", "EstimatedCompletionDate")
    start, end = whole_days(first, last, NEW_ZEALAND)
    event_type = _event_type(properties)
    street, town = clean(properties.get("StreetName")), clean(properties.get("Township"))
    place = ", ".join(part for part in (street, town) if part)
    kind, activity, work_type = (clean(properties.get(field)) for field in ("CAR_Type", "Activity", "WorkType"))
    step, status = clean(properties.get("CAR_Step")), clean(properties.get("CAR_Status"))
    closure = clean(properties.get("RoadClosureRequired")).lower() == "yes"
    points = _point_count(parts) if geometry["type"] == "Point" else 0
    kind_of_place = {"Point": "location", "LineString": "street section", "MultiLineString": "street sections"}.get(
        geometry["type"], "works area"
    )
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (kind, activity, work_type) if part and part != "Not Applicable") or None,
        status=" / ".join(part for part in (step, status) if part) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place,
                kind=kind_of_place,
                geometry=geometry,
                closure="Road closure required" if closure else None,
                reference=f"CAR {car}",
            )
        ]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        reported_ended=step in WORK_DONE_STEPS or status in WORK_DONE_STATUSES,
        stated_period=_stated_period(properties),
        covers_city=True,
    )
    organisations = [
        f"{label}: {properties[field]}"
        for label, field in (
            ("Principal", "PrincipalOrganisation"),
            ("Utility operator", "UtilityOperatorOrganisation"),
            ("Applicant", "ApplicantOrganisation"),
            ("Contractor", "ContractorOrganisation"),
        )
        if properties.get(field)
    ]
    summary = ". ".join(
        part
        for part in (
            f"Corridor access request {car} ({kind})" if kind else f"Corridor access request {car}",
            f"Activity: {activity}" if activity else "",
            clean(properties.get("WorkDescription")),
            _stated(properties, "Location in road", "LocationInRoad"),
            f"Status: {status} ({step})" if status else "",
            _stated(properties, "Road closure required", "RoadClosureRequired"),
            _stated(properties, "Traffic disruption", "TrafficDisruption"),
            _stated(properties, "Cause of disruption", "CauseOfDisruption"),
            _stated(properties, "Traffic management", "TTM_RoadLevel", ignore=("", "NA")),
            *organisations,
            f"Mapped at {points} points; shown at one of them" if points > 1 else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"CAR:{car}",
        url=ITEM_URL,
        title=f"{_LABELS[event_type]}: {place or 'New Plymouth District'} (New Plymouth District)",
        summary=summary,
        categories=[part for part in (kind, activity, "road closure" if closure else "") if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def cars(features_by_layer: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The features grouped by CAR across the layers: the CAR's fields once, its parts in a fixed order.

    Every part of a CAR states the same fields (5 November 2026); the first
    part's (points, then lines, then areas) are kept.
    """
    properties: dict[str, dict[str, Any]] = {}
    parts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for layer in LAYERS:
        for feature in features_by_layer.get(layer, []):
            fields = feature.get("properties") if isinstance(feature, dict) else None
            car = clean((fields or {}).get("CAR_ID"))
            if not car or not isinstance(feature.get("geometry"), dict):
                continue
            properties.setdefault(car, stored_properties(fields))
            part = {"layer": layer, "geometry": feature["geometry"]}
            if part not in parts[car]:
                parts[car].append(part)
    return [
        {
            "car": car,
            "properties": properties[car],
            "parts": sorted(parts[car], key=lambda part: json.dumps(part, sort_keys=True)),
        }
        for car in properties
    ]


def fetch_requests(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    return cars(
        {
            layer: fetch_arcgis_features(f"{SOURCE_URL}/{layer}", user_agent, where=WHERE, client=client)
            for layer in LAYERS
        }
    )


class NewPlymouthCorridorAccessConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_requests)
    to_record = staticmethod(to_record)
