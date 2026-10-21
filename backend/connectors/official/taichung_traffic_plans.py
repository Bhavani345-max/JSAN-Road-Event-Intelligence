"""Taichung traffic maintenance plans (臺中市交通維持計畫資料集), Taiwan (21 October 2026).

    GET https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download
        ?rid=c3bf6ac0-3e2a-4fc1-9bc1-dbf4ef43c30e

Taichung City's Transportation Bureau (臺中市政府交通局) publishes the
approved traffic maintenance plans of works and activities that affect road
traffic, refreshed daily (catalogue: https://data.gov.tw/dataset/84900).
Each JSON row gives the plan (`Id`), its kind as a code (`Type`: 1, 2, 3, 4,
6; the codes' meanings are not published), its name (`Name`, empty for
kind 4), the place (`Address`), who carries it out (`Company`), the start and
end dates (`StartDate`, `EndDate`, ISO dates), the working hours as whole
hours (`StartTime`, `EndTime`: 9 and 16, 0 and 24) and the site as WGS 84
points in text (`LatLng`, "{lat:24.1559431,lng:120.7096224}", one or more).
Fetched without a key on 21 October 2026: 1,137 rows of 550 plans; 825 rows
with at least one point.

A plan worked on several days is listed once a day: rows of one plan at one
site, with the same hours, on following days are read as one period (the
first day's start to the last day's end), as the feed itself writes a plan
of several days in one row. The times are the source's: the start hour on
the first day and the end hour on the last, Taipei time (24 is the end of the
day). One point is the site; several are the line the plan's map draws in
the order listed, closed into an area when the last point is the first.
A row without a point is not taken (REI keeps only located events). The
kind codes are not explained by the source, so no event type is given; the
plan's own words are kept.

Personal data: the contact person (`Contact`) and phone (`Telephone`) are
dropped before anything is stored, and `Company` is kept only when it names
an organisation (an individual applicant's name is dropped).

Licence: Open Government Data License, version 1.0 (connectors/official/
taiwan_open_data.py; docs/data-sources/taiwan-connectors-2026-10-21.md).
"""

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.source_models import (
    IntegrationStatus,
    RawSourceRecord,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
)

from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, whole_days
from .taiwan_open_data import COMMON_TERMS, TAIPEI_TIME, at_hour, attribution, organisation, without

SOURCE_ID = "taichung-traffic-maintenance-plans"
ENDPOINT = "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download"
PARAMS = {"rid": "c3bf6ac0-3e2a-4fc1-9bc1-dbf4ef43c30e"}
SOURCE_URL = "https://data.gov.tw/dataset/84900"
PROVIDER = "臺中市政府交通局"
ATTRIBUTION = attribution(PROVIDER, "臺中市交通維持計畫資料集")
PERSONAL_FIELDS = frozenset({"Contact", "Telephone"})
# The fields that make one site of a plan: rows that share them are one site's days.
SITE_FIELDS = ("Id", "Type", "Name", "Address", "LatLng", "StartTime", "EndTime")
_POINT = re.compile(r"\{\s*lat\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*lng\s*:\s*(-?\d+(?:\.\d+)?)\s*\}")


def taichung_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("taichung")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Taichung traffic maintenance plans (臺中市交通維持計畫資料集)",
        organization=f"Taichung City Government, Transportation Bureau ({PROVIDER})",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        country=city.country,
        region="Taichung City",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=f"{ENDPOINT}?rid={PARAMS['rid']}",
        access_method="JSON file (WGS 84 points in text), refreshed daily; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        events_supported=(),
        parser_type="taichung_traffic_plans",
        rate_limit="None published; polled four times a day (one 0.5 MB file).",
        attribution=ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each plan's rows as received, without the contact person, the phone number or an "
            "individual applicant's name."
        ),
        notes=(
            "Approved traffic maintenance plans of works and activities affecting Taichung's "
            "roads, with their dates, hours and points. Fetched without a key on 21 October 2026: "
            "1,137 rows of 550 plans, 825 rows with a point. The kind codes (Type) are not "
            "explained by the source, so no event type is given."
        ),
        **COMMON_TERMS,
    )


def points(value: Any) -> list[list[float]]:
    """The [longitude, latitude] points of a LatLng text, in the order written."""
    found = []
    for lat, lng in _POINT.findall(str(value or "")):
        position = [float(lng), float(lat)]
        if not found or found[-1] != position:  # a point written twice in a row is one point
            found.append(position)
    return found


def shape(value: Any) -> dict | None:
    """The site: a point, the line through several, or the area they close."""
    found = points(value)
    if not found:
        return None
    if len(found) == 1:
        return {"type": "Point", "coordinates": found[0]}
    if len(found) >= 4 and found[0] == found[-1]:
        return {"type": "Polygon", "coordinates": [found]}
    return {"type": "LineString", "coordinates": found}


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(clean(value)[:10])
    except ValueError:
        return None


def _hour(value: Any) -> int | None:
    text = clean(value)
    return int(text) if text.isdigit() and 0 <= int(text) <= 24 else None


def stored_row(row: dict[str, Any]) -> dict[str, Any]:
    """The row as REI keeps it: no contact person or phone, no individual's name."""
    kept = without(row, PERSONAL_FIELDS)
    if "Company" in kept and organisation(kept["Company"]) is None:
        kept.pop("Company")
    return kept


def _site_key(row: dict[str, Any]) -> str:
    return hashlib.sha1(
        json.dumps([clean(row.get(field)) for field in SITE_FIELDS], ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:8]


def group_plans(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One item per period of one site: its rows, on following or overlapping days.

    Rows without a point or without readable dates are left out; rows that
    are exact copies of one another count once.
    """
    sites: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for row in rows:
        if not clean(row.get("Id")) or shape(row.get("LatLng")) is None:
            continue
        if _day(row.get("StartDate")) is None or _day(row.get("EndDate")) is None:
            continue
        copy = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if copy in seen:
            continue
        seen.add(copy)
        sites.setdefault(_site_key(row), []).append(row)
    items = []
    for key, site_rows in sites.items():
        site_rows.sort(key=lambda row: (_day(row["StartDate"]), _day(row["EndDate"])))
        run: list[dict[str, Any]] = []
        run_end: date | None = None
        for row in site_rows:
            first, last = _day(row["StartDate"]), _day(row["EndDate"])
            if run and run_end is not None and first <= run_end + timedelta(days=1):
                run.append(row)
                run_end = max(run_end, last)
                continue
            if run:
                items.append(_plan(key, run, run_end))
            run, run_end = [row], last
        if run:
            items.append(_plan(key, run, run_end))
    return items


def _plan(site: str, rows: list[dict[str, Any]], last: date) -> dict[str, Any]:
    return {
        "plan": f"{clean(rows[0]['Id'])}:{site}:{last.isoformat()}",
        "rows": [stored_row(row) for row in rows],
    }


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    rows = item.get("rows")
    plan = clean(item.get("plan"))
    if not plan or not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    geometry = shape(row.get("LatLng"))
    first = min(filter(None, (_day(r.get("StartDate")) for r in rows)), default=None)
    last = max(filter(None, (_day(r.get("EndDate")) for r in rows)), default=None)
    if geometry is None or first is None or last is None:
        return None
    start_hour, end_hour = _hour(row.get("StartTime")), _hour(row.get("EndTime"))
    if start_hour is not None and end_hour is not None and start_hour < end_hour:
        start, end = at_hour(first, start_hour), at_hour(last, end_hour)
    else:  # no usable hours: the stated days, whole
        start, end = whole_days(first, last, TAIPEI_TIME)
    name, address, kind = clean(row.get("Name")), clean(row.get("Address")), clean(row.get("Type"))
    company = clean(row.get("Company"))  # kept only when an organisation's (stored_row)
    hours = f"{clean(row.get('StartTime'))}時至{clean(row.get('EndTime'))}時" if clean(row.get("StartTime")) else ""
    days = "、".join(
        clean(r.get("StartDate")) if clean(r.get("StartDate")) == clean(r.get("EndDate"))
        else f"{clean(r.get('StartDate'))} – {clean(r.get('EndDate'))}"
        for r in rows
    )  # fmt: skip
    structured = SourceEvent(
        event_type=None,
        category=" / ".join(part for part in ("交通維持計畫", f"工程種類 {kind}" if kind else "") if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=address or name or "臺中市", kind="site", geometry=geometry)],
        affected_road=address or None,
        attribution=ATTRIBUTION,
        stated_period=" ".join(part for part in (f"施工日期：{days}", f"施工時段：{hours}" if hours else "") if part),
        covers_city=True,
    )
    summary = "。".join(
        part
        for part in (
            name,
            f"地點：{address}" if address else "",
            f"執行單位：{company}" if company else "",
            f"工程種類（代碼）：{kind}" if kind else "",
            f"施工時段：{hours}" if hours else "",
        )
        if part
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=plan,
        url=SOURCE_URL,
        title=f"Traffic maintenance plan: {name or address or '臺中市'}"
        + (f", {address}" if name and address else "")
        + " (Taichung)",
        summary=summary,
        categories=[part for part in ("交通維持計畫", f"Type {kind}" if kind else "") if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_plans(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=PARAMS)
    if not isinstance(body, list):
        raise ConnectorError(f"{ENDPOINT} did not return a list of plans")
    return group_plans([row for row in body if isinstance(row, dict)])


class TaichungTrafficPlansConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_plans)
    to_record = staticmethod(to_record)
