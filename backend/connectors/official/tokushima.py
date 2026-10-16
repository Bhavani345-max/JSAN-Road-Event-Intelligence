"""Tokushima Prefecture road restrictions, Japan (decision 0034).

    GET https://bousai.pref.tokushima.lg.jp/00000_00000_00000.xml   the restrictions
    GET https://bousai.pref.tokushima.lg.jp/Symbol_08.xml           their points

Tokushima Prefecture's disaster-information portal publishes the current
restrictions on national and prefectural roads in the prefecture, refreshed
every 10 minutes. Each restriction (`trd`) states its road (`rkn` class,
`rn` name), the section it covers (`ssn` → `sfn`), what is restricted
(`rcc` code and `rc` words), why (`rr`), its start and end (`lsd`, `led`,
Japan Standard Time), exceptions (`ed`, e.g. "except Saturdays and
Sundays"), its direction (`rd`) and the office responsible (`ofn`). The
second file gives each restriction's point (WGS 84 "lon,lat"), its `Id`
carrying the restriction number in characters 2–11. Fetched without a key
on 16 October 2026: 234 restrictions, all with a start, an end and a point.

What is restricted decides the type, from the source's own words:
全面通行止 (full closure), 時間通行止 (closed at set times) and 車両通行止
(closed to vehicles) are planned road closures; 片側交互通行 (alternating
one-way traffic), 車線規制 (lane restriction) and 片側通行制限 are lane
restrictions; height and weight limits and その他 (other) keep their words
with no type; 歩道通行制限 (a pavement restriction) is not road traffic and
is not taken.

Licence: CC BY, as the Tokushima open-data portal marks both files; the
portal asks for the credit "出典：徳島県オープンデータポータルサイト
（https://opendata.pref.tokushima.lg.jp/dataset/414.html）"
(docs/data-sources/asia-mea-official-road-sources-2026-10-16.md).
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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

from .common import fetch_text
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time

SOURCE_ID = "tokushima-road-restrictions"
RESTRICTIONS_URL = "https://bousai.pref.tokushima.lg.jp/00000_00000_00000.xml"
POINTS_URL = "https://bousai.pref.tokushima.lg.jp/Symbol_08.xml"
SOURCE_URL = "https://opendata.pref.tokushima.lg.jp/dataset/414.html"
ATTRIBUTION = "出典：徳島県オープンデータポータルサイト（https://opendata.pref.tokushima.lg.jp/dataset/414.html）"
JST = ZoneInfo("Asia/Tokyo")

# What is restricted, in the source's words: the type and an English label.
CLOSURES = {
    "全面通行止": "Road closed",
    "時間通行止": "Road closed at set times",
    "車両通行止": "Closed to vehicles",
}
LANES = {
    "片側交互通行": "Alternating one-way traffic",
    "車線規制": "Lane restriction",
    "片側通行制限": "One side restricted",
}
# Not road traffic: a pavement (pedestrian) restriction.
NOT_TAKEN = frozenset({"歩道通行制限"})
ROAD_CLASS = {"国道": "National Route", "県道": "Prefectural Road"}
DIRECTION = {"上り": "inbound", "下り": "outbound", "上下": "both directions"}
# Only "both directions" is a compass statement (EventDirection); inbound/outbound stay words.
COMPASS = {"上下": "BOTH_DIRECTIONS"}


def tokushima_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("japan")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Tokushima Prefecture road restrictions",
        organization="Tokushima Prefecture",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Tokushima",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=RESTRICTIONS_URL,
        access_method="Two XML files (restrictions and their points), refreshed every 10 minutes; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="ja",
        events_supported=(EventType.PLANNED_ROAD_CLOSURE.value, EventType.LANE_RESTRICTION.value),
        parser_type="tokushima_road_restrictions",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY (Tokushima open-data portal)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each restriction as received, with its point.",
        notes=(
            "Current restrictions on national and prefectural roads in Tokushima Prefecture. "
            "Fetched without a key on 16 October 2026: 234 restrictions, each with a start, an end "
            "and a point."
        ),
    )


def _road(item: dict[str, Any]) -> str | None:
    kind, name = clean(item.get("rkn")), clean(item.get("rn"))
    if not name:
        return None
    return f"{ROAD_CLASS.get(kind, kind)} {name.removesuffix('号')}".strip()


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    rid = clean(item.get("rid"))
    restriction = clean(item.get("rc"))
    point = item.get("point")
    if not rid or restriction in NOT_TAKEN or not isinstance(point, list):
        return None
    geometry = {"type": "Point", "coordinates": point}
    if restriction in CLOSURES:
        event_type, label = EventType.PLANNED_ROAD_CLOSURE.value, CLOSURES[restriction]
    elif restriction in LANES:
        event_type, label = EventType.LANE_RESTRICTION.value, LANES[restriction]
    else:
        event_type, label = None, "Road restriction"
    road = _road(item)
    start_place, end_place = clean(item.get("ssn")), clean(item.get("sfn"))
    section = start_place if start_place == end_place or not end_place else f"{start_place} – {end_place}"
    direction = DIRECTION.get(clean(item.get("rd"))) or None
    compass = COMPASS.get(clean(item.get("rd")))
    reason, remarks, exceptions = clean(item.get("rr")), clean(item.get("rpr")), clean(item.get("ed"))
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (restriction, reason) if part),
        start=local_time(item.get("lsd"), JST, ("%Y/%m/%d %H:%M",)),
        end=local_time(item.get("led"), JST, ("%Y/%m/%d %H:%M",)),
        geometry=geometry,
        locations=[
            SourceLocation(
                name=" ".join(part for part in (section or road or "Tokushima", f"({direction})" if direction else "") if part),
                kind="section",
                geometry=geometry,
                closure=restriction or None,
            )
        ],
        affected_road=road,
        direction=compass,
        attribution=ATTRIBUTION,
        stated_period=" ".join(part for part in (clean(item.get("lsd")), "–", clean(item.get("led")), exceptions) if part),
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=rid,
        url=SOURCE_URL,
        title=f"{label}: {road or 'road'}, {section} (Tokushima)",
        summary=". ".join(part for part in (restriction, reason, remarks, f"Office: {clean(item.get('ofn'))}" if clean(item.get("ofn")) else "") if part),
        categories=[part for part in (restriction, reason) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def _points(body: str) -> dict[str, list[float]]:
    """Restriction number → [lon, lat], from the points file."""
    points: dict[str, list[float]] = {}
    for reg in ET.fromstring(body).iter("Reg"):
        identifier, position = clean(reg.findtext("Id")), clean(reg.findtext("Pt"))
        try:
            rid = str(int(identifier[1:11]))
            lon, lat = (float(value) for value in position.split(","))
        except ValueError:
            continue
        points.setdefault(rid, [lon, lat])
    return points


def fetch_restrictions(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """Each restriction as a flat dict of its fields, with its road and its point."""
    try:
        restrictions = ET.fromstring(fetch_text(RESTRICTIONS_URL, user_agent, client=client))
        points = _points(fetch_text(POINTS_URL, user_agent, client=client))
    except ET.ParseError as error:
        raise ConnectorError(f"Tokushima restrictions: not readable XML ({error})") from error
    items = []
    for road in restrictions.iter("ridt"):
        road_fields = {name: clean(road.findtext(name)) for name in ("rkn", "rn", "rnm")}
        for trd in road.iter("trd"):
            item = {**road_fields, **{child.tag: clean(child.text) for child in trd}}
            item["point"] = points.get(str(int(item["rid"]))) if item.get("rid", "").isdigit() else None
            items.append(item)
    return items


class TokushimaRoadRestrictionsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_restrictions)
    to_record = staticmethod(to_record)
