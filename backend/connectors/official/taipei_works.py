"""Taipei today's road works (臺北市今日施工資訊), Taiwan (21 October 2026).

    GET https://tpnco.blob.core.windows.net/blobfs/Todaywork.json

Taipei City's road-excavation management (臺北市政府工務局) publishes the
works reported on its roads today, refreshed every 10 minutes (catalogue:
https://data.gov.tw/dataset/145614). Each feature is one works site: its
point and its works area (`Positions`: a MultiPolygon for road maintenance,
a MultiLineString for excavation) on the TWD97 / TM2 grid (EPSG:3826), the
approval number (`Ac_no`) and sequence (`sno`), the kind of report
(`AppMode`), the district (`C_Name`) and address (`Addr`), the approved start
and end dates in the ROC calendar (`Cb_Da`, `Ce_Da`, "115/10/21"), the
working hours in words (`Co_Ti`), the purpose (`NPurp`), the works items
(`WItem`), whether traffic is affected (`IsBlock` 是/否) with the suggested
detour (`PlanB`), the applicant (`App_Name`) and contractor (`Tc_Na`).
Fetched without a key on 21 October 2026: 1,142 sites, every one with a
point, an area or line, and approved dates.

The approved period is stated in days, so it is taken as whole days in
Taipei time; the hours text is kept in the stated period, not read into a
time. The works area is converted from the grid to longitude and latitude
(connectors/official/twd97.py) and is the event's geometry; its point is the
site's location. Every report kind is works on or under the road
(ROAD_WORKS); its own words are kept. A site whose only works item is
pavement (sidewalk) maintenance, 人行道維護, and that the source says does
not affect traffic (IsBlock 否) is not road traffic and is not taken; nor
are the feed's own test entries (address "全市APP測試", city-wide app test).

Personal data: the site supervisor's and the contractor's site staff's names
(`Tc_Ma`, `Tc_Ma3`, masked by the source) and their mobile numbers (`Tc_Tl`,
`Tc_Tl3`) are dropped before anything is stored.

Licence: Open Government Data License, version 1.0 (connectors/official/
taiwan_open_data.py; docs/data-sources/taiwan-connectors-2026-10-21.md).
"""

from datetime import datetime
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.geo_models import Geometry
from packages.source_models import (
    IntegrationStatus,
    RawSourceRecord,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
)

from . import twd97
from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .taiwan_open_data import COMMON_TERMS, TAIPEI_TIME, attribution, roc_date, without

SOURCE_ID = "taipei-todaywork"
ENDPOINT = "https://tpnco.blob.core.windows.net/blobfs/Todaywork.json"
SOURCE_URL = "https://data.gov.tw/dataset/145614"
PROVIDER = "臺北市政府工務局"
ATTRIBUTION = attribution(PROVIDER, "臺北市今日施工資訊")
# The people in charge of a site and their mobile numbers.
PERSONAL_FIELDS = frozenset({"Tc_Ma", "Tc_Tl", "Tc_Ma3", "Tc_Tl3"})
# Report kinds (通報類別), as the catalogue lists them, with an English label.
REPORT_KINDS = {
    "0": ("施工通報", "Road works"),
    "3": ("銑鋪通報", "Resurfacing (milling and paving)"),
    "4": ("搶修通報", "Emergency repair works"),
    "5": ("道路維護通報", "Road maintenance"),
    "6": ("人手孔施工通報", "Manhole works"),
    "B": ("建案公設復舊", "Reinstatement after building works"),
}
SIDEWALK_ONLY = "人行道維護"
AFFECTS_TRAFFIC = "是"
# On 21 October 2026 the feed held 25 entries of approval 99015156 at this
# "address", drawn across Taiwan from Taipei to Taichung: tests, not works.
TEST_ADDRESS = "APP測試"
_GEOMETRY = TypeAdapter(Geometry)


def taipei_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("taipei")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Taipei today's road works (臺北市今日施工資訊)",
        organization=f"Taipei City Government, Public Works Department ({PROVIDER})",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        country=city.country,
        region="Taipei City",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="GeoJSON file (TWD97 / TM2 grid), refreshed every 10 minutes; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="taipei_todaywork",
        rate_limit="None published; polled hourly (one 2.7 MB file).",
        attribution=ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention=(
            "Each works site as received, without the site staff's names and mobile numbers."
        ),
        notes=(
            "Road works reported on Taipei's roads today, each with its point, its works area or "
            "line and its approved dates. Fetched without a key on 21 October 2026: 1,142 sites."
        ),
        **COMMON_TERMS,
    )


def _shape(properties: dict[str, Any]) -> dict | None:
    """The works area or line in longitude and latitude, if it is a valid shape."""
    shape = twd97.geometry(clean(properties.get("Positions_type")), properties.get("Positions"))
    if shape is None:
        return None
    try:
        _GEOMETRY.validate_python(shape)
    except ValidationError:
        return None
    return shape


def _not_road_traffic(properties: dict[str, Any]) -> bool:
    items = {part.strip() for part in clean(properties.get("WItem")).split(",") if part.strip()}
    return items == {SIDEWALK_ONLY} and clean(properties.get("IsBlock")) != AFFECTS_TRAFFIC


def _test_entry(properties: dict[str, Any]) -> bool:
    """The feed's own test entries: "全市APP測試" (city-wide app test) as the address."""
    return TEST_ADDRESS in clean(properties.get("Addr"))


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    approval, sequence = clean(properties.get("Ac_no")), clean(properties.get("sno"))
    point = twd97.point(*(geometry.get("coordinates") or [None, None])[:2])
    if not approval or not sequence or point is None or _not_road_traffic(properties) or _test_entry(properties):
        return None
    mode_words, label = REPORT_KINDS.get(clean(properties.get("AppMode")), ("", "Road works"))
    district, address = clean(properties.get("C_Name")), clean(properties.get("Addr"))
    place = f"臺北市{district}區 {address}".strip() if district else address or "臺北市"
    purpose, works, hours = clean(properties.get("NPurp")), clean(properties.get("WItem")), clean(properties.get("Co_Ti"))
    affects, detour = clean(properties.get("IsBlock")), clean(properties.get("PlanB"))
    closure = "影響通行" + (f"（{detour}）" if detour else "") if affects == AFFECTS_TRAFFIC else None
    first, last = clean(properties.get("Cb_Da")), clean(properties.get("Ce_Da"))
    start, end = whole_days(roc_date(first), roc_date(last), TAIPEI_TIME)
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in (mode_words, purpose) if part) or None,
        start=start,
        end=end,
        geometry=_shape(properties) or point,
        locations=[SourceLocation(name=place, kind="works site", geometry=point, closure=closure)],
        affected_road=address or None,
        attribution=ATTRIBUTION,
        stated_period=" ".join(
            part
            for part in (f"核准施工 {first} – {last}（民國紀年）" if first or last else "", f"施工時段：{hours}" if hours else "")
            if part
        )
        or None,
        covers_city=True,
    )
    summary = "。".join(
        part
        for part in (
            mode_words,
            f"挖掘目的：{purpose}" if purpose else "",
            f"施工工項：{works}" if works else "",
            f"施工時段：{hours}" if hours else "",
            f"是否影響通行：{affects}" if affects else "",
            f"替代方案：{detour}" if detour else "",
            f"申請單位：{clean(properties.get('App_Name'))}" if clean(properties.get("App_Name")) else "",
            f"施工廠商：{clean(properties.get('Tc_Na'))}" if clean(properties.get("Tc_Na")) else "",
            f"核備文號：{approval}",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=f"{approval}-{sequence}",
        url=SOURCE_URL,
        title=f"{label}: {address or place} ({district + '區, ' if district else ''}Taipei)",
        summary=summary,
        categories=[part for part in (mode_words, purpose) if part],
        item={**feature, "properties": without(properties, PERSONAL_FIELDS)},
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client)
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature collection")
    return [feature for feature in features if isinstance(feature, dict)]


class TaipeiTodayWorksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)
