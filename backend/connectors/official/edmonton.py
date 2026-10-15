"""City of Edmonton traffic disruptions (decision 0029).

    GET https://data.edmonton.ca/resource/k4tx-5k8p.json
        ?$limit=5000&$where=status in('Current','Revised','Emergency') AND ...

The City lists its construction, special-event and incident disruptions with
the street, the cross streets, the impact and the dates, each row at a point.
A disruption between two cross streets is listed twice, at the from point and
at the to point, with the same id and text: those rows are one disruption
here, at its from point, with the to point kept as a second location. On 15
October 2026: 1,197 disruptions in 1,788 rows, 134 not yet ended; keyless.

Dates have no time (Edmonton local days); hours, when given, are in the text.
The status alone is not reliable (some "Current" disruptions have ended), so
the finish date is checked too.

Open Government Licence – City of Edmonton.
"""

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

from .feature_feed import (
    FeatureFeedConnector,
    clean,
    fetch_socrata_rows,
    item_record,
    local_day,
    whole_days,
)

SOURCE_ID = "edmonton-traffic-disruptions"
ENDPOINT = "https://data.edmonton.ca/resource/k4tx-5k8p.json"
SOURCE_URL = "https://data.edmonton.ca/d/k4tx-5k8p"
ATTRIBUTION = "Contains information licensed under the Open Government Licence – City of Edmonton."
EDMONTON = ZoneInfo("America/Edmonton")
OPEN_STATUSES = ("Current", "Revised", "Emergency")


def edmonton_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Edmonton traffic disruptions",
        organization="City of Edmonton",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Alberta",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Socrata SODA JSON (dataset k4tx-5k8p); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.EMERGENCY_ROAD_CLOSURE.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="edmonton_traffic_disruptions",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Open Government Licence – City of Edmonton",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each disruption's rows as the dataset returns them and the structured event.",
        notes=(
            "The City's traffic disruptions with a point at each end. Fetched without a key on "
            "15 October 2026: 1,197 disruptions in 1,788 rows, 134 not yet ended. A "
            "disruption's two rows are one event. Dates are Edmonton local days."
        ),
    )


def _event_type(row: dict[str, Any]) -> str:
    activity = clean(row.get("activity_type")).lower()
    impact = clean(row.get("impact")).lower()
    if activity == "special event":
        return EventType.SPECIAL_EVENT.value
    if "closure" in impact:
        return (
            EventType.EMERGENCY_ROAD_CLOSURE.value
            if activity == "traffic incident"
            else EventType.PLANNED_ROAD_CLOSURE.value
        )
    if activity == "traffic incident":
        return EventType.ACCIDENT.value
    return EventType.ROAD_WORKS.value


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    rows = [row for row in item.get("rows") or [] if isinstance(row, dict)]
    located = [row for row in rows if isinstance(row.get("point"), dict)]
    external_id = clean(item.get("disruption_id"))
    if not external_id or not located:
        return None
    row = located[0]
    street, start_at, end_at = (
        clean(row.get("on_street")), clean(row.get("from_street")), clean(row.get("to_street"))
    )  # fmt: skip
    stretch = " ".join(
        part
        for part in (street, f"from {start_at}" if start_at else "", f"to {end_at}" if end_at else "")
        if part
    )
    start, end = whole_days(
        local_day(row.get("start_date"), EDMONTON), local_day(row.get("finish_date"), EDMONTON), EDMONTON
    )
    impact = clean(row.get("impact"))
    structured = SourceEvent(
        event_type=_event_type(row),
        category=" / ".join(part for part in (clean(row.get("activity_type")), impact) if part),
        status=clean(row.get("status")) or None,
        start=start,
        end=end,
        geometry=row["point"],
        locations=[
            SourceLocation(
                name=f"{street} at {cross}" if street and cross else street or cross,
                kind=kind,
                geometry=point_row["point"],
                closure=impact or None,
            )
            for point_row, kind, cross in zip(
                located, ("from point", "to point"), (start_at, end_at)
            )
        ],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    summary = ". ".join(
        part for part in (clean(row.get("details")), clean(row.get("description")).capitalize()) if part
    )
    categories = [part.lower() for part in (clean(row.get("activity_type")), impact) if part]
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{impact or 'Disruption'}: {stretch} (Edmonton)",
        summary=summary,
        categories=categories,
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_disruptions(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """The open disruptions, each with its rows (one, or two: from and to)."""
    today = (now or datetime.now(EDMONTON)).astimezone(EDMONTON).date().isoformat()
    statuses = ",".join(f"'{status}'" for status in OPEN_STATUSES)
    rows = fetch_socrata_rows(
        ENDPOINT,
        user_agent,
        client=client,
        where=f"status in({statuses}) AND (finish_date IS NULL OR finish_date >= '{today}')",
    )
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(clean(row.get("disruption_id")), []).append(row)
    return [{"disruption_id": key, "rows": group} for key, group in grouped.items() if key]


class EdmontonTrafficDisruptionsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_disruptions)
    to_record = staticmethod(to_record)
