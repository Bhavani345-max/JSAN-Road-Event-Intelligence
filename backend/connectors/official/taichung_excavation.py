"""Taichung same-day road excavation information (當日道路挖掘資訊), Taiwan (5 November 2026).

    GET https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download
        ?rid=d5adb71a-00bb-4573-b67e-ffdccfc7cd27

Taichung City's Construction Bureau (臺中市政府建設局) publishes the road
excavation permits valid today, refreshed every ten minutes (catalogue:
https://data.gov.tw/dataset/105203). Each JSON row is one site of a permit:
the application and permit numbers (`申請書編號`, `許可證編號`), the approved
first and last day in the ROC calendar (`核准起日期`, `核准迄日期`, "1151105"),
the applicant (`申請單位`), the works name (`工程名稱`), the kind of case
(`案件類別`: 新增建築用戶申裝, 計劃性管線工程案件 …) and of pipeline
(`管線工程類別`: 自來水, 電力, 電信, 瓦斯 …), the district and place (`區域名稱`,
`地點`), whether works have started (`是否開工`: 是/否), the officer in charge
and their phone (`承辦人`, `承辦人電話`), the contractor and its phone
(`廠商名稱`, `廠商電話`), a WGS 84 point (`經度`, `緯度`) and the works area as
WKT (`施工範圍坐標`, POLYGON or MULTIPOLYGON, longitude first). Fetched without
a key on 5 November 2026: 1,350 rows of 854 permits (one row per site; a
permit has up to 16), every one valid today (no start after today, no end
before it); 105 rows of 71 permits marked started; 1,343 rows with a point and
an area, 7 with neither.

A permit is one event: REI keeps one record per application number, its works
area being the areas of all its sites (a MultiPolygon when there are several;
a site's point only when no site has an area). The approved period is stated
in days and is taken as whole days in Taipei time. Every permit is works under
the road (ROAD_WORKS); a permit does not say whether traffic is closed, and REI
does not say so either.

All valid permits are kept, started or not, as the New Taipei excavation
connector keeps every permit for its permitted period: the permit is what
allows digging on those days, and whether works have begun is the source's
own word on progress, kept as the record's status (已開工 / 尚未開工), not a
reason to drop it. A permit whose every site is stated to be on the pavement
(`地點` names 人行道 and none names a carriageway, 車道) digs no road and is
not kept (22 of the 854 on 5 November 2026), as for Copenhagen's permits; nor
is a permit without an area or a point (7). 825 permits kept, all in force
(70 started).

Personal data: the officer in charge, their phone and the contractor's phone
are dropped before anything is stored; `申請單位` and `廠商名稱` are kept only
when they name an organisation (two applicants and a contractor were people).
The works name of a utility customer's connection is the customer's order:
an order number and the customer's name ("賴琮盛 CTL251086", "8260397 郭銘峰
(115-1054)"), often a private person's, sometimes half-masked by the source
("王O揚", "吳*毅"). The rule: the works name is kept only for a public-works
case (計劃性管線工程案件, 計劃性道路工程案件, 非計劃性道路工程(含路修案件),
道路附屬設施…) or a case filed by a Taichung public body (申請單位 starting
臺中市/台中市), and never when it carries a sign of a person (a half-masked
name, 先生, 小姐, 女士, 負責人); otherwise it is replaced by "[masked]" before
anything is stored (625 of the 854 names on 5 November 2026; the 229 kept are
programme names such as "南屯區萬和路一段等汰換管線工程").

Licence: Open Government Data License, version 1.0 (connectors/official/
taiwan_open_data.py).
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import (
    IntegrationStatus,
    RawSourceRecord,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
)

from .barcelona import wkt_geometry
from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .taiwan_open_data import COMMON_TERMS, TAIPEI_TIME, attribution, organisation, roc_date, without

SOURCE_ID = "taichung-road-excavation-today"
ENDPOINT = "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download"
PARAMS = {"rid": "d5adb71a-00bb-4573-b67e-ffdccfc7cd27"}
SOURCE_URL = "https://data.gov.tw/dataset/105203"
PROVIDER = "臺中市政府建設局"
ATTRIBUTION = attribution(PROVIDER, "臺中市當日道路挖掘資訊")
# The officer in charge and the phone numbers: not kept.
PERSONAL_FIELDS = frozenset({"承辦人", "承辦人電話", "廠商電話"})
# The fields REI reads; a file without them is not this dataset.
REQUIRED_FIELDS = frozenset({"申請書編號", "核准起日期", "核准迄日期", "地點", "施工範圍坐標"})
# Cases that are public works programmes, whose works name names no customer.
PUBLIC_WORKS_CASES = frozenset(
    {
        "計劃性管線工程案件",
        "計劃性道路工程案件",
        "非計劃性道路工程(含路修案件)",
        "道路附屬設施(人行道、側溝、斜坡道及臨時抽排水施作包含新設及改建)",
    }
)
PUBLIC_BODY = ("臺中市", "台中市")
# A sign that a works name names a person: a name the source half-masks
# ("王O揚", "吳*毅", "鄭0雅"), a form of address, "the person responsible".
_PERSON = re.compile(r"[一-鿿][O○0*＊Ｏ〇][一-鿿]|先生|小姐|女士|負責人")
MASKED = "[masked]"
STARTED = {"是": "已開工", "否": "尚未開工"}


def taichung_excavation_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("taichung")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Taichung same-day road excavation information (當日道路挖掘資訊)",
        organization=f"Taichung City Government, Construction Bureau ({PROVIDER})",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        country=city.country,
        region="Taichung City",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=f"{ENDPOINT}?rid={PARAMS['rid']}",
        access_method="JSON file (WGS 84 points and WKT works areas), refreshed every 10 minutes; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="taichung_road_excavation",
        rate_limit="None published; polled hourly (one 1.2 MB file).",
        attribution=ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each permit's site rows as received, without the officer in charge, the phone numbers, "
            "a person named as applicant or contractor, or a works name that may name a customer."
        ),
        notes=(
            "Road excavation permits valid today in Taichung, one row per site with its works area. "
            "Fetched without a key on 5 November 2026: 1,350 rows of 854 permits (71 marked started); "
            "one record per permit; 22 permits only on the pavement and 7 without a location are "
            "left out (825 kept, 70 of them started)."
        ),
        **COMMON_TERMS,
    )


def keeps_works_name(row: dict[str, Any]) -> bool:
    """Whether the works name is a programme's (kept) or may be a customer's (masked)."""
    name = clean(row.get("工程名稱"))
    if not name or _PERSON.search(name):
        return False
    return clean(row.get("案件類別")) in PUBLIC_WORKS_CASES or clean(row.get("申請單位")).startswith(PUBLIC_BODY)


def stored_row(row: dict[str, Any]) -> dict[str, Any]:
    """A site row as REI keeps it: no officer, phones, individuals' names or customer's name."""
    kept = without(row, PERSONAL_FIELDS)
    for field in ("申請單位", "廠商名稱"):
        if field in kept and organisation(kept[field]) is None:
            kept.pop(field)
    if "工程名稱" in kept and not keeps_works_name(row):
        kept["工程名稱"] = MASKED
    return kept


def _point(row: dict[str, Any]) -> dict[str, Any] | None:
    try:
        longitude, latitude = float(clean(row.get("經度"))), float(clean(row.get("緯度")))
    except ValueError:
        return None
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return None
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _polygons(row: dict[str, Any]) -> list[list]:
    shape = wkt_geometry(row.get("施工範圍坐標"))
    if shape is None:
        return []
    if shape["type"] == "Polygon":
        return [shape["coordinates"]]
    if shape["type"] == "MultiPolygon":
        return list(shape["coordinates"])
    return []


def _area(polygons: list[list]) -> dict[str, Any] | None:
    if not polygons:
        return None
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def site_geometry(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The works area of these rows: their areas (each once), else the first point given."""
    polygons: list[list] = []
    for row in rows:
        for polygon in _polygons(row):
            if polygon not in polygons:
                polygons.append(polygon)
    if polygons:
        return _area(polygons)
    return next((point for row in rows if (point := _point(row)) is not None), None)


def pavement_only(rows: list[dict[str, Any]]) -> bool:
    """Every site is stated to be on the pavement (人行道) and none on a carriageway (車道)."""
    places = [clean(row.get("地點")) for row in rows]
    on_pavement = all("人行道" in place for place in places)
    return bool(places) and on_pavement and not any("車道" in place for place in places)


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One permit as REI's record; None without dates or a located site, or on the pavement only."""
    rows = item.get("rows")
    application = clean(item.get("application"))
    if not application or not isinstance(rows, list) or not rows:
        return None
    if pavement_only(rows):
        return None
    geometry = site_geometry(rows)
    first_text, last_text = clean(rows[0].get("核准起日期")), clean(rows[0].get("核准迄日期"))
    first, last = roc_date(first_text), roc_date(last_text)
    if geometry is None or first is None or last is None:
        return None
    start, end = whole_days(first, last, TAIPEI_TIME)
    row = rows[0]
    district = clean(row.get("區域名稱"))
    sites: dict[str, list[dict[str, Any]]] = {}
    for site in rows:
        sites.setdefault(clean(site.get("地點")), []).append(site)
    locations = [
        SourceLocation(name=f"{district}{place}", kind="excavation site", geometry=shape)
        for place, site_rows in sites.items()
        if place and (shape := site_geometry(site_rows)) is not None
    ]
    places = [place for place in sites if place]
    case, pipeline = clean(row.get("案件類別")), clean(row.get("管線工程類別"))
    works = clean(row.get("工程名稱"))
    works = "" if works == MASKED else works
    started = STARTED.get(clean(row.get("是否開工")))
    applicant, contractor = clean(row.get("申請單位")), clean(row.get("廠商名稱"))  # organisations only (stored_row)
    permit = clean(row.get("許可證編號"))
    where = f"{district}{places[0]}" if places else district or "臺中市"
    more = f" and {len(places) - 1} more sites" if len(places) > 1 else ""
    # The works name when kept, else the kind of case; then the kind of pipeline.
    what = " / ".join(part for part in (works or case, pipeline) if part) or "道路挖掘"
    # Up to three of the places, "等" (and others) for more.
    roads = "；".join(places[:3]) + ("等" if len(places) > 3 else "")
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in ("道路挖掘", case, pipeline) if part),
        status=started,
        start=start,
        end=end,
        geometry=geometry,
        locations=locations,
        affected_road=roads or None,
        attribution=ATTRIBUTION,
        stated_period=f"核准施工 {first_text} – {last_text}（民國紀年）",
        covers_city=True,
    )
    summary = "。".join(
        part
        for part in (
            works,
            f"案件類別：{case}" if case else "",
            f"管線工程類別：{pipeline}" if pipeline else "",
            f"申請單位：{applicant}" if applicant else "",
            f"施工廠商：{contractor}" if contractor else "",
            f"許可證編號：{permit}" if permit else "",
            f"是否開工：{clean(row.get('是否開工'))}" if clean(row.get("是否開工")) else "",
            f"施工地點：{'；'.join(places)}" if places else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=application,
        url=SOURCE_URL,
        title=f"Road excavation ({what}): {where}{more} (Taichung)",
        summary=summary,
        categories=[part for part in ("道路挖掘", case, pipeline) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def permits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The site rows grouped by application, stored without personal data, in a fixed order."""
    by_application: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        application = clean(row.get("申請書編號"))
        if application:
            by_application[application].append(stored_row(row))
    return [
        {
            "application": application,
            "rows": sorted(site_rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False)),
        }
        for application, site_rows in by_application.items()
    ]


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    if not isinstance(body, list):
        raise ConnectorError(f"{ENDPOINT} did not return a list of excavation sites")
    rows = [row for row in body if isinstance(row, dict)]
    if rows and not REQUIRED_FIELDS <= set(rows[0]):
        raise ConnectorError(f"{ENDPOINT} did not return the road excavation rows (fields: {sorted(rows[0])})")
    return permits(rows)


class TaichungRoadExcavationConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
