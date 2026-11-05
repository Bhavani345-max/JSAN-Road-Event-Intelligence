"""City of Cambridge (Massachusetts) street excavation permits (5 November 2026).

    GET https://data.cambridgema.gov/resource/nuxx-d95m.json?$select=<the columns below>
        &$where=status='Active' AND public_roadway=true AND end_date>='<today>'&$limit=5000

The City's "Excavation permits since April 2019" (Socrata dataset nuxx-d95m,
category Public Works, "Estimated Update Frequency: Weekly"), one row per
permit with its address and point. REI asks only for the Active permits that
work in the public roadway and have not ended: 91 on 5 November 2026, keyless
(cutting "Yes - Street & Sidewalk" 50, "Yes - Street" 40, "Yes - Sidewalk" 1),
all in effect (first days from 16 February 2024 to 3 November 2026), none
starting later. Active permits not ticked as working in the public roadway
(48 not ended on 5 November: 23 cutting nothing, 11 the sidewalk only, 14 a
street the permit does not mark as public roadway) and completed permits are
not asked for. Not to be confused with Cambridge, Ontario
(`cambridge-on-road-closures`).

Fields read: `id` (the permit), `full_address` ("112 Thorndike St, Cambridge, MA
02141"), `coordinates` (the dataset's own GeoJSON point; the same as the
`latitude`/`longitude` text, which is read only when the point is missing),
`status`, `start_date`/`end_date` (days, written '2026-07-24T00:00:00.000'),
so a permit runs from the start of its first day to the end of its last,
Cambridge time (America/New_York); `public_roadway`, `cutting_the_street_and_or`,
`number_of_street_cuts`, `utilities` (Eversource Gas 64, Other 11, Water
Service 5 ...), `other_utility` (what "Other" is, in the applicant's words),
`new_gas_main`. The dataset has no title: REI's title is the utility and the
address ("Excavation (Eversource Gas): 112 Thorndike St, Cambridge, MA 02141";
the permit type, then the utility unless it is "Other"). Every permit is
road works (ROAD_WORKS); a permit does not say whether traffic is closed, and
REI does not say so either.

Personal data: the `$select` names only the columns REI reads, so the
applicant's name (`applicant_name`), the company, contractor, subcontractor
and client names, the hoisting licence number and grade of the machine
operator and the parcel number are never fetched. The stored row holds the
selected columns only.

Licence: "Open Data Commons Public Domain Dedication and License" (the
dataset's licence, http://opendatacommons.org/licenses/pddl/1.0/, in
https://data.cambridgema.gov/api/views/nuxx-d95m.json, read 5 November 2026).
robots.txt asks for a crawl delay of 1 second; `/resource/` is not disallowed.
"""

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

from .common import fetch_json
from .feature_feed import FeatureFeedConnector, clean, item_record, local_day, whole_days
from .feed_text import sentences

SOURCE_ID = "us-cambridge-ma-street-excavations"
ENDPOINT = "https://data.cambridgema.gov/resource/nuxx-d95m.json"
SOURCE_URL = "https://data.cambridgema.gov/d/nuxx-d95m"
LICENCE_URL = "http://opendatacommons.org/licenses/pddl/1.0/"
ATTRIBUTION = (
    "Source: City of Cambridge, Massachusetts, Excavation Permits (Cambridge Open Data, dataset nuxx-d95m). "
    "Open Data Commons PDDL."
)
CAMBRIDGE = ZoneInfo("America/New_York")
# The columns REI asks for and keeps; nothing naming a person is among them.
COLUMNS = (
    "id",
    "full_address",
    "latitude",
    "longitude",
    "coordinates",
    "status",
    "permit_type",
    "issue_date",
    "start_date",
    "end_date",
    "public_roadway",
    "public_sidewalk",
    "cutting_the_street_and_or",
    "number_of_street_cuts",
    "number_of_sidewalk_cuts",
    "utilities",
    "other_utility",
    "performing_utility_work",
    "new_gas_main",
)
LIMIT = 5000


def cambridge_ma_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-states")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="City of Cambridge (Massachusetts) street excavation permits",
        organization="City of Cambridge, Massachusetts (Public Works)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Massachusetts (Cambridge)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method=(
            "Socrata SODA JSON (dataset nuxx-d95m), Active public-roadway permits not ended, "
            "named columns only; no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=1440,
        language="en",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="cambridge_ma_street_excavations",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; robots.txt asks for a crawl delay of 1 second; one request a run.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Open Data Commons Public Domain Dedication and License ({LICENCE_URL}), the dataset's licence",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each permit's selected columns as returned (no applicant, company, contractor or licence "
            "columns are asked for) and the structured event."
        ),
        notes=(
            "The City of Cambridge's Active excavation permits in the public roadway, one point each at "
            "the permit's address; updated weekly. Fetched without a key on 5 November 2026: 91 permits, "
            "all in effect. Days are Cambridge days. Not Cambridge, Ontario (cambridge-on-road-closures)."
        ),
    )


def _number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except ValueError:
        return None


def _point(row: dict[str, Any]) -> dict[str, Any] | None:
    """The dataset's own point; else the point its latitude and longitude state; None at 0,0."""
    stated = row.get("coordinates")
    if isinstance(stated, dict) and stated.get("type") == "Point":
        position = stated.get("coordinates")
        if (
            isinstance(position, list)
            and len(position) >= 2
            and all(isinstance(value, (int, float)) for value in position[:2])
            and position[:2] != [0, 0]
        ):
            return stated
        return None
    latitude, longitude = _number(row.get("latitude")), _number(row.get("longitude"))
    if latitude is None or longitude is None or (latitude, longitude) == (0, 0):
        return None
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _stated_true(value: Any) -> bool:
    return value is True or clean(value).lower() == "true"


def to_record(row: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One permit as REI's record; None when it is not Active in the public roadway or has no point."""
    permit = clean(row.get("id"))
    if not permit or clean(row.get("status")).upper() != "ACTIVE" or not _stated_true(row.get("public_roadway")):
        return None
    geometry = _point(row)
    if geometry is None:
        return None
    address = clean(row.get("full_address"))
    utility = clean(row.get("utilities"))
    other = clean(row.get("other_utility"))
    cutting = clean(row.get("cutting_the_street_and_or"))
    street_cuts = clean(row.get("number_of_street_cuts"))
    sidewalk_cuts = clean(row.get("number_of_sidewalk_cuts"))
    gas_main = clean(row.get("new_gas_main"))
    kind = clean(row.get("permit_type")) or "Excavation"
    # "Other" says only that the utility is not in the list; its words are in other_utility.
    named = utility if utility and utility.upper() != "OTHER" else ""
    start, end = whole_days(
        local_day(row.get("start_date"), CAMBRIDGE), local_day(row.get("end_date"), CAMBRIDGE), CAMBRIDGE
    )
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(part for part in ("Excavation permit", utility, cutting) if part),
        status=clean(row.get("status")) or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=address, kind="address", geometry=geometry)] if address else [],
        affected_road=address or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=permit,
        url=SOURCE_URL,
        # The permit's own type ("Excavation"): a cut may be in the street, the sidewalk or both.
        title=f"{kind}{f' ({named})' if named else ''}: {address or 'permit ' + permit}",
        summary=sentences(
            f"City of Cambridge excavation permit {permit}",
            f"Cutting the street and/or sidewalk: {cutting}" if cutting else "",
            f"Street cuts: {street_cuts}" if street_cuts else "",
            f"Sidewalk cuts: {sidewalk_cuts}" if sidewalk_cuts else "",
            f"Utility: {utility}" if utility else "",
            f"Other utility work: {other}" if other else "",
            f"New gas main: {gas_main}" if gas_main else "",
        ),
        categories=[part.lower() for part in ("excavation permit", utility) if part],
        item={column: row[column] for column in COLUMNS if column in row},
        structured=structured,
        retrieved_at=retrieved_at,
    )


def query(now: datetime | None = None) -> dict[str, str]:
    """The SODA parameters: the named columns of the Active public-roadway permits not ended."""
    today = (now or datetime.now(CAMBRIDGE)).astimezone(CAMBRIDGE).date().isoformat()
    return {
        "$select": ",".join(COLUMNS),
        "$where": f"status='Active' AND public_roadway=true AND end_date>='{today}'",
        "$limit": str(LIMIT),
    }


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    body = fetch_json(ENDPOINT, user_agent, client=client, params=query(now))
    if not isinstance(body, list):
        raise ConnectorError(f"{ENDPOINT} did not return a list of rows")
    if len(body) >= LIMIT:
        raise ConnectorError(f"{ENDPOINT} returned {LIMIT} rows or more; the list is cut")
    return [row for row in body if isinstance(row, dict)]


class CambridgeMaStreetExcavationsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
