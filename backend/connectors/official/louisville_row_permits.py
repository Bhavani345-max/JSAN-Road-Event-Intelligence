"""Louisville Metro (Kentucky) right-of-way construction permits (5 November 2026).

    GET https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/
        Louisville_KY_ROW_Construction_Permits_new/FeatureServer/0/query?where=1=1&outSR=4326&f=geojson

Louisville Metro Public Works and Assets' "Approved and currently issued
right-of-way construction permits. Limited to projects that will affect
roadway traffic" (ArcGIS item c3d7b38b0ed54ea7b68b89361adc49eb, "Louisville
Metro KY - ROW Construction Permits", owner LouisvilleMetro, tagged "Updated
Weekly"). The permits come from Accela; the points "are added and removed
based upon the time window expressed on the permit and do not reflect the
actual condition of work on the ground" (the item's description). One point
per permit at the nearest street address. Fetched without a key on 5 November
2026: 281 permits in one page; 250 in effect, 3 starting later, 28 ended (an
ended permit is dropped by the run window).

Fields read: `PERMIT_NO` (the id, "PW-REP-26-03232"), `WORK_TYPE` (the
general type, comma-separated: "Excavation ,Lane Closure", "Road Closure",
"Lane Closure ,Utility Cut" ...), `STREET_ADDRESS` ("nearest street address to
the location of work"), `CITY` (Louisville or a city within the Metro:
Shively, Lyndon ...), `FROM_DATE`/`TO_DATE` (days, served as milliseconds at
the Louisville midnight, so a permit runs from the start of its first day to
the end of its last, Louisville time). Every permit affects roadway traffic,
by the layer's own description: a permit naming a road closure is a planned
road closure (26), one naming a lane closure a lane restriction (252), the
rest road works (3: an excavation or a utility cut only).

Personal data: `APPLICANT_NAME` is the "name of the person or organization
that applied for the permit": dropped. `WORK_DESCRIPTION` is the applicant's
free text, which in 277 of the 281 permits names the applicant's contact
persons (project engineers, managers, inspectors) with their phone numbers
and e-mail addresses, sometimes with neither: not kept, in the evidence or the
summary. `ObjectId` (also the feature id, 1 to 281) is a row number of the
weekly reload, not content, and is not kept.

Licence: "Louisville Metro's open datasets are published with the Open Data
Commons Public Domain Dedication and License (PDDL)" (Louisville Metro Open
Data Platform Terms of Use,
https://louisville-metro-opendata-lojic.hub.arcgis.com/pages/terms-of-use-and-license,
the item's licence link; read 5 November 2026 from the page's Hub item
d71a5507a1d04a679c7c49861d52a9eb). The terms add: "Application developers and
any other third-party entities must explicitly identify the source, version,
and modifications made to a dataset, should they publicly re-publish it
elsewhere or incorporate the dataset into an application"; REI's attribution
names all three.
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
    fetch_arcgis_features,
    item_record,
    local_day,
    whole_days,
)
from .feed_text import sentences

SOURCE_ID = "louisville-row-construction-permits"
SOURCE_URL = (
    "https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/"
    "Louisville_KY_ROW_Construction_Permits_new/FeatureServer"
)
LAYER = f"{SOURCE_URL}/0"
ITEM_URL = "https://www.arcgis.com/home/item.html?id=c3d7b38b0ed54ea7b68b89361adc49eb"
TERMS_URL = "https://louisville-metro-opendata-lojic.hub.arcgis.com/pages/terms-of-use-and-license"
# The terms ask for the source, the version and the modifications to be named.
ATTRIBUTION = (
    "Source: Louisville Metro Government, Public Works and Assets, Louisville Metro KY - ROW Construction "
    "Permits (Louisville Metro Open Data, ArcGIS item c3d7b38b0ed54ea7b68b89361adc49eb), Open Data Commons "
    "PDDL. Version: the layer as served at each record's retrieval time. Modified by REI: applicant names, "
    "work descriptions and row numbers removed; dates read as whole Louisville days."
)
LOUISVILLE = ZoneInfo("America/Kentucky/Louisville")
# "Name of the person or organization that applied for the permit."
PERSONAL = frozenset({"APPLICANT_NAME"})
# Free text naming the applicant's contact persons with phones and e-mails: not kept.
FREE_TEXT = frozenset({"WORK_DESCRIPTION"})
# The layer's row number, renumbered on reload: not content.
ROW_NUMBERS = frozenset({"ObjectId", "OBJECTID"})
ROAD_CLOSURE = "ROAD CLOSURE"
LANE_CLOSURE = "LANE CLOSURE"


def louisville_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-states")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Louisville Metro right-of-way construction permits (traffic-affecting)",
        organization="Louisville/Jefferson County Metro Government, Public Works and Assets",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Kentucky (Louisville Metro)",
        city=country.id,
        source_url=ITEM_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service (ArcGIS Online), GeoJSON in WGS 84; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="louisville_row_permits",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; one request a run.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Open Data Commons Public Domain Dedication and License (PDDL), Louisville Metro Open Data terms ({TERMS_URL})",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each permit as the service returns it, less the applicant's name, the free-text work "
            "description and the row number, and the structured event."
        ),
        notes=(
            "Louisville Metro's approved right-of-way construction permits that affect roadway traffic, "
            "one point each at the nearest street address; updated weekly. Fetched without a key on 5 "
            "November 2026: 281 permits, 250 in effect, 3 starting later, 28 ended. The terms ask an "
            "application to identify the source, version and modifications: the attribution does."
        ),
    )


def work_types(properties: dict[str, Any]) -> list[str]:
    """'Excavation ,Lane Closure' as ['Excavation', 'Lane Closure']."""
    return [part for part in (clean(text) for text in clean(properties.get("WORK_TYPE")).split(",")) if part]


def _event_type(kinds: list[str]) -> str:
    upper = {kind.upper() for kind in kinds}
    if ROAD_CLOSURE in upper:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if LANE_CLOSURE in upper:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _closure(kinds: list[str]) -> str | None:
    """The closure the permit names, in its own words."""
    for wanted in (ROAD_CLOSURE, LANE_CLOSURE):
        found = next((kind for kind in kinds if kind.upper() == wanted), None)
        if found:
            return found
    return None


def _located(geometry: Any) -> bool:
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return False
    position = geometry.get("coordinates")
    return (
        isinstance(position, list)
        and len(position) >= 2
        and all(isinstance(value, (int, float)) for value in position[:2])
        and position[:2] != [0, 0]
    )


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """The feature as REI keeps it: no applicant, no free text, no row number."""
    properties = feature.get("properties") or {}
    left_out = PERSONAL | FREE_TEXT | ROW_NUMBERS
    return {
        "type": feature.get("type"),
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in left_out},
    }


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One permit as REI's record; None without an id or a point."""
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not _located(geometry):
        return None
    permit = clean(properties.get("PERMIT_NO"))
    if not permit:
        return None
    kinds = work_types(properties)
    event_type = _event_type(kinds)
    closure = _closure(kinds)
    address = clean(properties.get("STREET_ADDRESS"))
    city = clean(properties.get("CITY"))
    place = ", ".join(part for part in (address, city) if part)
    start, end = whole_days(
        local_day(properties.get("FROM_DATE"), LOUISVILLE),
        local_day(properties.get("TO_DATE"), LOUISVILLE),
        LOUISVILLE,
    )
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(("Right-of-way construction permit", *kinds)),
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=place, kind="address", geometry=geometry, closure=closure)]
        if place
        else [],
        affected_road=address or None,
        attribution=ATTRIBUTION,
        covers_city=True,
    )
    label = {
        EventType.PLANNED_ROAD_CLOSURE.value: "Road closure",
        EventType.LANE_RESTRICTION.value: "Lane closure",
    }.get(event_type, "Road works")
    return item_record(
        source_id=SOURCE_ID,
        external_id=permit,
        url=ITEM_URL,
        title=f"{label}: {address or 'permit ' + permit} ({city or 'LOUISVILLE'}, KY)",
        summary=sentences(
            f"Louisville Metro right-of-way construction permit {permit}",
            f"Work type: {', '.join(kinds)}" if kinds else "",
        ),
        categories=["right-of-way construction permit", *(kind.lower() for kind in kinds)],
        item=_kept(feature),
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    # The layer holds the approved and current permits only (a few hundred); the
    # run window drops those that have ended.
    return fetch_arcgis_features(LAYER, user_agent, order_by="ObjectId", client=client)


class LouisvilleRowConstructionPermitsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
