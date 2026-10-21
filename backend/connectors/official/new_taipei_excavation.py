"""New Taipei road excavation permits (新北市政府道路挖掘資訊), Taiwan (21 October 2026).

    GET https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv/file

New Taipei City's Public Works Department (新北市政府工務局) publishes the
road excavation permits it has issued, refreshed daily (catalogue:
https://data.gov.tw/dataset/122989). Each CSV row is one permit (`caseid`):
its kind (`casetype`: 一般, 民生, 新建房屋, 緊急, 計畫), the works name
(`constname`), the site (`digsite`, with district and road), what is dug
(`digarea`), the permitted start and end dates in the ROC calendar
(`casestartdate_yyymmddroc`, `caseenddate_yyymmddroc`, "1151021"), the
working period in words (`workperiod`), the contractor (`constructionunit`),
the utility or owner it digs for (`supervise`), the unit that examined it
(`examunit`), the permit number (`licno`) and the site's point on the TWD97 /
TM2 grid (`twd97x`, `twd97y`). Fetched without a key on 21 October 2026:
2,149 permits, every one with a point and dates.

The permitted period is stated in days and is taken as whole days in Taipei
time. Only where the working period is one continuous stretch with stated
hours ("連續性施工，115年03月02日11時起115年03月06日23時止") on the same days
as the date fields are those hours used; otherwise the words are kept in the
stated period and no time is read. Every permit is works under the road
(ROAD_WORKS); a permit does not say whether traffic is closed, and REI does
not say so either.

Personal data: the contractor's and the supervisor's people in charge
(`construction_man`, `supervise_man`) and every phone field are dropped
before anything is stored; `supervise` and `constructionunit` are kept only
when they name an organisation (a private owner may be a person), and
`remark` only when it holds no phone number or contact person.

Licence: Open Government Data License, version 1.0 (connectors/official/
taiwan_open_data.py; docs/data-sources/taiwan-connectors-2026-10-21.md).
"""

import csv
import io
import re
from datetime import date, datetime
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

from . import twd97
from .common import fetch_text
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .taiwan_open_data import (
    COMMON_TERMS,
    ROC_YEAR_OFFSET,
    TAIPEI_TIME,
    at_hour,
    attribution,
    organisation,
    roc_date,
    without,
)

SOURCE_ID = "new-taipei-road-excavation"
ENDPOINT = "https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv/file"
SOURCE_URL = "https://data.gov.tw/dataset/122989"
PROVIDER = "新北市政府工務局"
ATTRIBUTION = attribution(PROVIDER, "新北市政府道路挖掘資訊")
PERSONAL_FIELDS = frozenset(
    {
        "construction_man",
        "construction_localcallservice",
        "construction_tel_ext",
        "construction_mobiletelephone",
        "supervise_man",
        "supervise_localcallservice",
        "supervise_tel_ext",
        "supervise_mobiletelephone",
    }
)
# The columns REI reads; a file without them is not this dataset.
REQUIRED_COLUMNS = frozenset({"caseid", "casestartdate_yyymmddroc", "caseenddate_yyymmddroc", "twd97x", "twd97y"})
# A phone number (seven digits or more, with or without dashes) or a contact
# person ("黃先生", "請洽") in a remark.
_CONTACT = re.compile(r"\d[\d\-\s#.]{6,}\d|先生|小姐|女士|請洽|聯絡|連絡|電話|手機")
_CONTINUOUS = re.compile(
    r"^連續性施工，(\d{2,3})年(\d{1,2})月(\d{1,2})日(\d{1,2})時起(\d{2,3})年(\d{1,2})月(\d{1,2})日(\d{1,2})時止，共\d+日。?$"
)


def new_taipei_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("new-taipei")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="New Taipei road excavation permits (新北市政府道路挖掘資訊)",
        organization=f"New Taipei City Government, Public Works Department ({PROVIDER})",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        country=city.country,
        region="New Taipei City",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="CSV file (points on the TWD97 / TM2 grid), refreshed daily; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="new_taipei_road_excavation",
        rate_limit="None published; polled four times a day (one 1.7 MB file).",
        attribution=ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each permit as received, without the people in charge, their phone numbers, "
            "a person named as owner, or a remark with contact details."
        ),
        notes=(
            "Road excavation permits issued by New Taipei City, each with a point and its "
            "permitted dates. Fetched without a key on 21 October 2026: 2,149 permits."
        ),
        **COMMON_TERMS,
    )


def _stated_hours(period: str, first: date | None, last: date | None) -> tuple[datetime, datetime] | None:
    """The start and end of one continuous stretch with stated hours, on the permit's own days."""
    match = _CONTINUOUS.match(period)
    if not match:
        return None
    y1, m1, d1, h1, y2, m2, d2, h2 = (int(part) for part in match.groups())
    try:
        start_day = date(y1 + ROC_YEAR_OFFSET, m1, d1)
        end_day = date(y2 + ROC_YEAR_OFFSET, m2, d2)
    except ValueError:
        return None
    if (start_day, end_day) != (first, last) or not (0 <= h1 <= 24 and 0 <= h2 <= 24):
        return None
    return at_hour(start_day, h1), at_hour(end_day, h2)


def stored_row(row: dict[str, Any]) -> dict[str, Any]:
    """The permit as REI keeps it: without the people in charge and their numbers."""
    kept = without(row, PERSONAL_FIELDS)
    for field in ("supervise", "constructionunit"):
        if field in kept and organisation(kept[field]) is None:
            kept.pop(field)
    if "remark" in kept and _CONTACT.search(clean(kept["remark"])):
        kept.pop("remark")
    return kept


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    case = clean(row.get("caseid"))
    point = twd97.point(row.get("twd97x"), row.get("twd97y"))
    if not case or point is None:
        return None
    first_text, last_text = clean(row.get("casestartdate_yyymmddroc")), clean(row.get("caseenddate_yyymmddroc"))
    first, last = roc_date(first_text), roc_date(last_text)
    period = clean(row.get("workperiod"))
    start, end = _stated_hours(period, first, last) or whole_days(first, last, TAIPEI_TIME)
    kind, works, site = clean(row.get("casetype")), clean(row.get("constname")), clean(row.get("digsite"))
    kept = stored_row(row)
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in ("道路挖掘", kind) if part),
        status=clean(row.get("statdesc")) or None,
        start=start,
        end=end,
        geometry=point,
        locations=[SourceLocation(name=site or "新北市", kind="excavation site", geometry=point)],
        affected_road=site or None,
        attribution=ATTRIBUTION,
        stated_period=" ".join(
            part
            for part in (
                f"許可施工 {first_text} – {last_text}（民國紀年）" if first_text or last_text else "",
                f"施工期間：{period}" if period else "",
            )
            if part
        )
        or None,
        covers_city=True,
    )
    summary = "。".join(
        part
        for part in (
            works,
            f"挖掘內容：{clean(row.get('digarea'))}" if clean(row.get("digarea")) else "",
            f"施工單位：{clean(kept['constructionunit'])}" if kept.get("constructionunit") else "",
            f"管線/申請單位：{clean(kept['supervise'])}" if kept.get("supervise") else "",
            f"審查單位：{clean(row.get('examunit'))}" if clean(row.get("examunit")) else "",
            f"許可證號：{clean(row.get('licno'))}" if clean(row.get("licno")) else "",
            f"備註：{clean(kept['remark'])}" if clean(kept.get("remark")) else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=case,
        url=SOURCE_URL,
        title=f"Road excavation ({kind or '道路挖掘'}): {site or works or '新北市'} (New Taipei)",
        summary=summary,
        categories=[part for part in ("道路挖掘", kind) if part],
        item=kept,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def read_rows(text: str) -> list[dict[str, str]]:
    """The permits of the CSV file (UTF-8, with or without a byte-order mark)."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames or not REQUIRED_COLUMNS <= set(reader.fieldnames):
        raise ConnectorError(f"{ENDPOINT} did not return the road excavation CSV (columns: {reader.fieldnames})")
    return [dict(row) for row in reader]


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    return read_rows(fetch_text(ENDPOINT, user_agent, client=client))


class NewTaipeiRoadExcavationConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
