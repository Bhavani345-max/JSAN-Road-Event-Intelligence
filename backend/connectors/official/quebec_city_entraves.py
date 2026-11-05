"""Ville de Québec real-time traffic obstructions, WZDx 3.1 (5 November 2026).

    GET https://quebec.gewi.com/wzdx4waze/pull   GeoJSON FeatureCollection, WZDx v3.1; no key

The City's "Entraves à la circulation en temps réel de la Ville de Québec"
(Données Québec, update frequency "Temps réel"), in the US Work Zone Data
Exchange format version 3.1: a `road_event_feed_info` header and one feature
per road event, each with flat `properties` (WZDx 4.x, read by `wzdx.py`,
nests them under `core_details`). Each event states its type (`work-zone`
or `detour`), its status (`active`, `pending`, `planned`), its road names
and direction, what it does to traffic (`vehicle_impact`), its lanes, a
French description, and a start and an end in UTC ("2026-11-11T13:00:00Z",
both "estimated"). Works on both sides of a street are two features, one
per direction. On 5 November 2026: 355 features (266 current, 89 upcoming,
none ended): 259 work zones and 96 detours.

Taken, as in `wzdx.py`: a `work-zone` event is one record, its type from
`vehicle_impact` ("all-lanes-closed" a road closure; lanes closed,
alternating one-way traffic and the like a lane restriction). Left out:
detours, which describe the route traffic is sent along, not where the road
is affected (96, among them the 2 features without geometry); and work zones
whose `vehicle_impact` is "all-lanes-open", which close no lane (22 of 259:
private sites with containers or materials beside the road and the like),
as REI leaves out closures that state no effect on traffic. Kept: 237.

One feature id can name two work zones on two streets ("ACL-20261022-SPA-01"
on Rue Arago O and on Rue St-Germain, 5 November 2026): a record is known by
its id and its first road name.

The feed carries no personal data. Licence: "Licence Attribution (CC-BY 4.0)",
the Données Québec record of the dataset (entraves-a-la-circulation-en-temps-
reel-de-la-ville-de-quebec, read 5 November 2026), which recommends the
citation used as the attribution below.
"""

from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
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

from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record
from .feed_text import sentences
from .wzdx import CLOSED, COMPASS, RESTRICTED

SOURCE_ID = "ca-quebec-city-entraves-wzdx"
ENDPOINT = "https://quebec.gewi.com/wzdx4waze/pull"
SOURCE_URL = (
    "https://www.donneesquebec.ca/recherche/dataset/"
    "entraves-a-la-circulation-en-temps-reel-de-la-ville-de-quebec"
)
ATTRIBUTION = (
    "VILLE DE QUÉBEC. Entraves à la circulation en temps réel de la Ville de Québec, "
    "[Jeu de données], dans Données Québec. Licence CC BY 4.0."
)
# Work zones that state no effect on traffic.
NOT_TRAFFIC = frozenset({"all-lanes-open"})
# WZDx 3.1 statuses saying the event is over.
OVER = frozenset({"completed", "cancelled"})


def quebec_city_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Ville de Québec real-time traffic obstructions (WZDx 3.1)",
        organization="Ville de Québec, Service du transport et de la mobilité intelligente",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Québec (Ville de Québec)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="WZDx 3.1 GeoJSON feed listed on Données Québec; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=30,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="wzdx_v3",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; real-time dataset; polled every 30 minutes (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0), per Données Québec",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each work-zone feature as received.",
        notes=(
            "The City's obstructions in WZDx 3.1, one line per road event and direction, French "
            "descriptions. Fetched without a key on 5 November 2026: 355 features (266 current, "
            "89 upcoming): 259 work zones and 96 detours; detours and the 22 work zones with all "
            "lanes open are left out, 237 kept. Times are UTC."
        ),
    )


def _event_type(impact: str) -> str:
    if impact in CLOSED:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if impact in RESTRICTED:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _time(value: Any) -> datetime | None:
    """An ISO 8601 time with its zone ("2026-11-11T13:00:00Z"); None without a zone."""
    try:
        moment = datetime.fromisoformat(clean(value))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def _lanes(properties: dict[str, Any]) -> str:
    """'1 lane closed, 2 sidewalk open': each lane the feed lists, in its words."""
    lanes = [lane for lane in properties.get("lanes") or [] if isinstance(lane, dict)]
    lanes.sort(key=lambda lane: lane["order"] if isinstance(lane.get("order"), int) else 0)
    fields = ("order", "type", "status")
    words = (" ".join(filter(None, (clean(lane.get(name)) for name in fields))) for lane in lanes)
    return ", ".join(text for text in words if text)


def road_names(properties: dict[str, Any]) -> list[str]:
    return [name for name in (clean(road) for road in properties.get("road_names") or []) if name]


def record_key(feature: dict[str, Any]) -> str | None:
    """The feature's id and its first road name: one id can name two streets."""
    feature_id = clean(feature.get("id"))
    if not feature_id:
        return None
    roads = road_names(feature.get("properties") or {})
    return f"{feature_id}|{roads[0]}" if roads else feature_id


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if clean(properties.get("event_type")) != "work-zone":
        return None
    impact = clean(properties.get("vehicle_impact"))
    external_id = record_key(feature)
    if not external_id or impact in NOT_TRAFFIC:
        return None
    roads = road_names(properties)
    direction = clean(properties.get("direction"))
    if direction in ("unknown", "undefined"):
        direction = ""
    event_type = _event_type(impact)
    status = clean(properties.get("event_status"))
    impact_words = impact.replace("-", " ")
    works = ", ".join(
        clean(work.get("type_name")).replace("-", " ")
        for work in properties.get("types_of_work") or []
        if isinstance(work, dict) and clean(work.get("type_name"))
    )
    restrictions = ", ".join(
        clean(item).replace("-", " ")
        for item in properties.get("restrictions") or []
        if clean(item)
    )
    place = " / ".join(roads)
    stated = {
        name: f"{name} {clean(properties.get(f'{name}_date'))} "
        f"({clean(properties.get(f'{name}_date_accuracy')) or 'accuracy not stated'})"
        for name in ("start", "end")
    }
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in ("Work zone", impact_words, works) if part),
        status=status or None,
        start=_time(properties.get("start_date")),
        end=_time(properties.get("end_date")),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=" ".join(part for part in (place or "Work zone", direction) if part),
                kind="work zone",
                geometry=geometry,
                direction=direction or None,
                closure=impact_words or None,
            )
        ],
        affected_road=roads[0] if roads else None,
        direction=COMPASS.get(direction),
        attribution=ATTRIBUTION,
        reported_ended=status in OVER,
        stated_period=f"{stated['start']}, {stated['end']}",
        covers_city=True,
    )
    label = {
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
        EventType.LANE_RESTRICTION.value: "Lane restriction",
    }.get(event_type, "Road works")
    lanes = _lanes(properties)
    where = " ".join(part for part in (place or "work zone", direction) if part)
    summary = sentences(
        clean(properties.get("description")),
        f"Lanes: {lanes}" if lanes else "",
        f"Restrictions: {restrictions}" if restrictions else "",
        f"Types of work: {works}" if works else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label}: {where} (Québec)",
        summary=summary,
        categories=["work-zone", *([impact] if impact else []), *([status] if status else [])],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=_time(properties.get("update_date")),
    )


def fetch_features(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a WZDx feature collection")
    version = clean((body.get("road_event_feed_info") or {}).get("version"))
    # The 3.1 reader reads 3.x only; WZDx 4 moved the fields (see wzdx.py).
    if not version.startswith("3."):
        raise ConnectorError(
            f"{ENDPOINT} states WZDx version {version or '(none)'}; this reader reads WZDx 3.x"
        )
    return [feature for feature in features if isinstance(feature, dict)]


class QuebecCityEntravesConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_features)
    to_record = staticmethod(to_record)
