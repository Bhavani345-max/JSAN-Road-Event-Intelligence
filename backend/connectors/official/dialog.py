"""DiaLog: France's national database of traffic orders (arrêtés de circulation).

    GET https://dialog.beta.gouv.fr/api/regulations/json
        ?status=current|upcoming&category=temporaryRegulation&pageSize=100&page=N

Run by the Ministry of Transport (DGITM). Councils and departments publish
their temporary traffic orders in it: closures, diversions, speed limits,
parking bans, with the streets or road sections they apply to and their
geometry. On 14 October 2026: 482 current and 284 upcoming temporary orders
from about 50 authorities, keyless.

An order that only bans parking says nothing about traffic and is not read
as a road event. Permanent orders are not read.

DiaLog's own caveat: "Les restrictions diffusées par DiaLog n'ont pas de
valeur juridique. Seul l'arrêté fait foi." (only the signed order is legally
binding; it is linked when the authority attached it). Licence: Licence
Ouverte / Etalab 2.0 ("Sauf mention contraire, tous les contenus de ce site
sont sous licence etalab-2.0", https://dialog.beta.gouv.fr/mentions-legales).
robots.txt disallows only /regulations, not /api/.
"""

import json
from datetime import datetime
from typing import Any

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

SOURCE_ID = "france-dialog-traffic-orders"
ENDPOINT = "https://dialog.beta.gouv.fr/api/regulations/json"
SOURCE_URL = "https://dialog.beta.gouv.fr/"
ATTRIBUTION = "Source: DiaLog (Ministère chargé des Transports, DGITM), Licence Ouverte 2.0."
PAGE_SIZE = 100
# Stops a run that keeps finding pages (DiaLog listed 5 and 3 on 14 October 2026).
MAX_PAGES = 50

# What a measure does to traffic, in REI's terms. A parking ban is not here:
# an order with nothing else is not a road event.
_MEASURES = {
    "noEntry": "road closed",
    "alternateRoad": "diversion",
    "speedLimitation": "speed limit",
    "noOvertaking": "no overtaking",
}


def dialog_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("france")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="DiaLog traffic orders (France)",
        organization="Ministère chargé des Transports (DGITM), DiaLog",
        authority_type="NATIONAL_TRANSPORT_MINISTRY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="DiaLog public JSON API; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="fr",
        events_supported=tuple(
            event_type.value
            for event_type in (
                EventType.PLANNED_ROAD_CLOSURE,
                EventType.EMERGENCY_ROAD_CLOSURE,
                EventType.TRAFFIC_DIVERSION,
                EventType.ROAD_WORKS,
                EventType.SPECIAL_EVENT,
                EventType.ROAD_HAZARD,
            )
        ),
        parser_type="dialog_regulations_json",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Licence Ouverte / Etalab 2.0 (https://dialog.beta.gouv.fr/mentions-legales)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_segments=True,
        real_time=False,
        evidence_retention=(
            "Each traffic order as the API returns it and the structured event derived from it."
        ),
        notes=(
            "Temporary traffic orders that councils and departments publish in DiaLog. Fetched "
            "without a key on 14 October 2026: 482 current and 284 upcoming. Orders that only "
            "ban parking are not road events. DiaLog states that only the signed order is "
            "legally binding."
        ),
    )


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _geometry(value: Any) -> dict[str, Any] | None:
    """A location's geometry in a shape REI stores, built only from the source's coordinates.

    DiaLog sends GeoJSON as text, sometimes a GeometryCollection or a
    MultiPoint, which REI does not store: their lines become one
    MultiLineString, or else their first point is kept.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    if kind in ("Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"):
        return value
    if kind == "MultiPoint" and value.get("coordinates"):
        return {"type": "Point", "coordinates": value["coordinates"][0]}
    if kind == "GeometryCollection":
        parts = [_geometry(part) for part in value.get("geometries") or []]
        lines = _lines(part for part in parts if part)
        if lines:
            return {"type": "MultiLineString", "coordinates": lines}
        points = [part for part in parts if part and part["type"] == "Point"]
        return points[0] if points else None
    return None


def _lines(geometries) -> list:
    lines = []
    for geometry in geometries:
        if geometry["type"] == "LineString":
            lines.append(geometry["coordinates"])
        elif geometry["type"] == "MultiLineString":
            lines.extend(geometry["coordinates"])
    return lines


def _place(location: dict[str, Any]) -> tuple[str, str | None]:
    """(what the order names, the road) for one location."""
    street = location.get("namedStreet") or {}
    road = location.get("numberedRoad") or {}
    if street.get("roadName"):
        name = _clean(street["roadName"])
        start = _clean(street.get("fromHouseNumber") or street.get("fromRoadName"))
        end = _clean(street.get("toHouseNumber") or street.get("toRoadName"))
        if start or end:
            name += f", from {start or 'its start'} to {end or 'its end'}"
        town = _clean(street.get("cityLabel"))
        return (f"{name}, {town}" if town else name), _clean(street["roadName"])
    if road.get("roadNumber"):
        number = _clean(road["roadNumber"])
        name = number
        if road.get("fromPointNumber") or road.get("toPointNumber"):
            name += (
                f", from PR {_clean(road.get('fromPointNumber'))}+{road.get('fromAbscissa') or 0}"
                f" to PR {_clean(road.get('toPointNumber'))}+{road.get('toAbscissa') or 0}"
            )
        administrator = _clean(road.get("administrator"))
        return (f"{name} ({administrator})" if administrator else name), number
    for key in ("zone", "rawGeoJSON", "storageArea"):
        label = _clean((location.get(key) or {}).get("label"))
        if label:
            return label, None
    return "", None


def _event_type(subject: str, measures: set[str]) -> str | None:
    if "noEntry" in measures:
        if subject == "incident":
            return EventType.EMERGENCY_ROAD_CLOSURE.value
        return EventType.PLANNED_ROAD_CLOSURE.value
    if "alternateRoad" in measures:
        return EventType.TRAFFIC_DIVERSION.value
    if subject == "roadMaintenance":
        return EventType.ROAD_WORKS.value
    if subject == "event":
        return EventType.SPECIAL_EVENT.value
    if subject == "incident":
        return EventType.ROAD_HAZARD.value
    return None


def to_record(regulation: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    external_id = _clean(regulation.get("uuid"))
    measures = [m for m in regulation.get("measures") or [] if isinstance(m, dict)]
    kinds = {_clean(m.get("type")) for m in measures}
    traffic = [m for m in measures if _clean(m.get("type")) in _MEASURES]
    if not external_id or not traffic:
        return None

    locations: list[SourceLocation] = []
    shapes: list[dict[str, Any]] = []
    roads: list[str] = []
    for measure in traffic:
        what = _MEASURES[_clean(measure.get("type"))]
        for location in measure.get("locations") or []:
            if not isinstance(location, dict):
                continue
            name, road = _place(location)
            geometry = _geometry(location.get("geometry"))
            if geometry:
                shapes.append(geometry)
            if road and road not in roads:
                roads.append(road)
            uuid = _clean(location.get("uuid"))
            locations.append(
                SourceLocation(
                    name=name or what,
                    kind="road section",
                    geometry=geometry,
                    closure=what,
                    reference=f"DiaLog location {uuid}" if uuid else None,
                )
            )
    lines = _lines(shapes)
    if lines:
        geometry = {"type": "MultiLineString", "coordinates": lines}
    else:
        geometry = next((shape for shape in shapes if shape["type"] == "Point"), None) or (
            shapes[0] if shapes else None
        )

    subject = _clean(regulation.get("subject"))
    authority = _clean((regulation.get("organization") or {}).get("name"))
    order = _clean(regulation.get("title")) or "Arrêté temporaire"
    effects = sorted({_MEASURES[kind] for kind in kinds if kind in _MEASURES})
    structured = SourceEvent(
        event_type=_event_type(subject, kinds),
        category=" / ".join(part for part in (subject, ", ".join(effects)) if part),
        start=_time(regulation.get("startDate")),
        end=_time(regulation.get("endDate")),
        geometry=geometry,
        locations=locations,
        affected_road=roads[0] if roads else None,
        attribution=ATTRIBUTION,
    )
    places = "; ".join(dict.fromkeys(location.name for location in locations if location.name))
    effect = ", ".join(effects).capitalize()
    identifier = _clean(regulation.get("identifier"))
    order_by = ""
    if authority:
        order_by = f"Order by {authority}" + (f" ({identifier})" if identifier else "")
    what = f"{effect}: {places}" if places else effect
    summary = ". ".join(part for part in (what, order_by) if part)
    categories = [part for part in ("traffic order", subject, *effects) if part]
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=_clean(regulation.get("documentUrl")) or SOURCE_URL,
        title=f"{order} ({authority})" if authority else order,
        summary=summary or None,
        content_text=None,
        categories=categories,
        published_at=None,
        retrieved_at=retrieved_at,
        raw={
            "regulation": regulation,
            "summary_html": summary,
            "categories": categories,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=content_key(regulation, frozenset()),
        structured=structured,
    )


class DialogTrafficOrdersConnector:
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
        # The query asks only for current and upcoming orders, so an order
        # dropping out of it usually means it ended: no `observed_ids` is
        # reported, and nothing is counted missing.

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("regulation", {}), frozenset())

    def _regulations(self, status: str) -> list[dict[str, Any]]:
        regulations: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            body = fetch_json(
                ENDPOINT,
                self._user_agent,
                client=self._client,
                params={
                    "status": status,
                    "category": "temporaryRegulation",
                    "pageSize": str(PAGE_SIZE),
                    "page": str(page),
                },
            )
            items = body.get("regulations") if isinstance(body, dict) else None
            if not isinstance(items, list):
                raise ConnectorError(f"{ENDPOINT} did not return a list of regulations")
            regulations.extend(item for item in items if isinstance(item, dict))
            last = (body.get("metadata") or {}).get("lastPage")
            if not items or not isinstance(last, int) or page >= last:
                break
        return regulations

    def fetch(self) -> list[RawSourceRecord]:
        retrieved_at = self._clock()
        seen: set[str] = set()
        records: list[RawSourceRecord] = []
        for status in ("current", "upcoming"):
            for regulation in self._regulations(status):
                record = to_record(regulation, retrieved_at)
                if record and record.external_id not in seen:
                    seen.add(record.external_id)
                    records.append(record)
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
