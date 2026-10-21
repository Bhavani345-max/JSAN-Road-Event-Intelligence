"""Seattle Department of Transportation street closures (21 October 2026).

    GET https://data.seattle.gov/resource/ium9-iqtc.json?$limit=5000&$where=end_date >= '...'

SDOT's short-term street closures from issued Street Use permits: "only the
closures permitted for non-construction activities, including Block Parties,
Play Streets, Farmers markets and Cafe Streets. This dataset does not include
closures for parades, festivals, or construction related activities" (the
dataset's description). Each row is one street segment (`segkey`) closed
over one period under one permit, with its own line. On 21 October 2026: 117
rows from 68 permits (Block Party 39, Farmers Market 29, Temporary
Activation 28, Play Street 21), keyless. Refreshed daily.

Dates are days (Seattle local, written without an offset); the hours are in
one column per weekday ("9:30AM-1:30PM", "All Day") and are kept as text: a
period here runs from the start of the first day to the end of the last.

Public Domain (the dataset's licence on data.seattle.gov, read 21 October
2026); attribution: Seattle Department of Transportation.
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
from .feed_text import sentences, stretch

SOURCE_ID = "seattle-sdot-street-closures"
ENDPOINT = "https://data.seattle.gov/resource/ium9-iqtc.json"
SOURCE_URL = "https://data.seattle.gov/d/ium9-iqtc"
ATTRIBUTION = (
    "Source: Seattle Department of Transportation, Street Closures (data.seattle.gov). "
    "Public domain."
)
SEATTLE = ZoneInfo("America/Los_Angeles")
WEEKDAYS = (
    ("sunday", "Sun"), ("monday", "Mon"), ("tuesday", "Tue"), ("wednesday", "Wed"),
    ("thursday", "Thu"), ("friday", "Fri"), ("saturday", "Sat"),
)  # fmt: skip


def seattle_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-states")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Seattle SDOT street closures (permitted events)",
        organization="City of Seattle, Seattle Department of Transportation (SDOT)",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Washington (Seattle)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Socrata SODA JSON (dataset ium9-iqtc); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(EventType.SPECIAL_EVENT.value,),
        parser_type="seattle_sdot_street_closures",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt asks for a crawl delay of 1 second.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Public Domain (dataset licence on data.seattle.gov)",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each row as the dataset returns it and the structured event.",
        notes=(
            "SDOT's street closures for permitted non-construction activities (block parties, "
            "play streets, farmers markets, temporary activations), one line per street segment "
            "and period. Fetched without a key on 21 October 2026: 117 rows from 68 permits. "
            "Dates are Seattle local days; the hours per weekday are kept as text."
        ),
    )


def _hours(row: dict[str, Any]) -> str:
    return "; ".join(
        f"{label} {hours}" for key, label in WEEKDAYS if (hours := clean(row.get(key)))
    )


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    permit = clean(row.get("permit_number"))
    geometry = row.get("line_string")
    if not permit or not isinstance(geometry, dict):
        return None
    street = clean(row.get("street_on"))
    place = stretch(street, clean(row.get("street_from")), clean(row.get("street_to")))
    kind = clean(row.get("permit_type"))
    start, end = whole_days(
        local_day(row.get("start_date"), SEATTLE), local_day(row.get("end_date"), SEATTLE), SEATTLE
    )
    structured = SourceEvent(
        event_type=EventType.SPECIAL_EVENT.value,
        category=" / ".join(part for part in ("Street closure", kind) if part),
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(
                name=place, kind="street segment", geometry=geometry, closure="Street closure"
            )
        ]
        if place
        else [],
        affected_road=street or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    hours = _hours(row)
    name = clean(row.get("project_name"))
    summary = sentences(
        f"{kind}: {name}" if kind and name and name.lower() != kind.lower() else kind or name,
        clean(row.get("project_description")),
        f"Hours: {hours}" if hours else "",
        f"Permit {permit}",
    )
    segment = clean(row.get("segkey"))
    return item_record(
        source_id=SOURCE_ID,
        # A permit closes several segments, some on several periods.
        external_id=":".join(
            (permit, segment, clean(row.get("start_date"))[:10], clean(row.get("end_date"))[:10])
        ),
        url=SOURCE_URL,
        title=f"{kind or 'Street closure'}: {place or name} (Seattle)",
        summary=summary,
        categories=[part.lower() for part in ("street closure", kind) if part],
        item=row,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_closures(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    today = (now or datetime.now(SEATTLE)).astimezone(SEATTLE).date().isoformat()
    return fetch_socrata_rows(ENDPOINT, user_agent, client=client, where=f"end_date >= '{today}'")


class SeattleStreetClosuresConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_closures)
    to_record = staticmethod(to_record)
