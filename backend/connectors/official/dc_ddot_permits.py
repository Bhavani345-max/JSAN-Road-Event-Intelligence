"""District of Columbia DDOT construction permits, last 30 days (5 November 2026).

    GET https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/12/query
        ?where=STATUS = 'Issued' AND EXPIRATIONDATE >= DATE '<yesterday>'&outSR=4326&f=geojson

The District Department of Transportation's public space construction permits
("Construction Permit - Last 30 Days"; ArcGIS item fc7a616c7b8c4b2994759d61f5a826b7,
"Construction Permits in the Last 30 Days", owner DCGISopendata), one point
each at the permit's address, geocoded by DC GIS to the Master Address
Repository (native EPSG:26985; asked for in WGS 84). On 5 November 2026 the
layer held 2,998 permits and applications in every status (Issued 1,460,
Approved (Pending Payment) 808, Assigned 417, Revise and Resubmit 184,
Cancel/Withdrawn 68, Resubmitted 49, Denied 5, Pending Assignment 4, Not Paid 2,
Suspended 1). Only an issued permit allows work, so REI asks for the Issued
ones not yet expired: 1,460, keyless, in two pages (the layer states a
maxRecordCount of 2,000 but answers 1,000 a page and marks the first page
`exceededTransferLimit`; `fetch_arcgis_features` follows it).

Fields read: `PERMITNUMBER` (the id, "PA489229", a revision "PA497977-R1"),
`STATUS`, `WLFULLADDRESS` (an address, "4847 SEDGWICK STREET NW", or a block,
"1600 - 1699 BLOCK OF U STREET NW"), `EFFECTIVEDATE` and `EXPIRATIONDATE`
(days, served as milliseconds at the New York midnight; the layer's
dateFieldsTimeReference is America/New_York), so a permit runs from the start
of its first day to the end of its last, Washington time; `ISSUEDATE` (the
moment of issue); and the six work flags, "T" or "F": `ISEXCAVATION`,
`ISPAVING`, `ISFIXTURE`, `ISLANDSCAPING`, `ISPROJECTIONS`, `ISPSRENTAL`.

A permit that excavates or paves is road works (ROAD_WORKS): 1,340 of the 1,460
(excavation 1,230, paving 120; 1,109 in effect, 231 starting later, 218 of them
within 30 days and one on 1 January 2028, beyond REI's run window). Most are
utility excavation (DC Water's lead service replacement, Pepco conduit). The
layer does not say whether a dig is in the carriageway, the sidewalk or an
alley, nor whether traffic is closed, and REI does not say so either. The 120
others are left out: they dig and pave nothing (fixtures such as fences and
bike racks, landscaping, projections, a public-space rental, or no work flag
at all: 67, mostly overhead cable work on poles). The item's description warns
that an address the geocoder could not match "will contain 0,0 for X,Y
coordinates"; such a permit is unlocated and left out (none on 5 November).

Personal data: the permittee, owner, contractor and applicant company
(`PERMITTEENAME`, `OWNERNAME`, `CONTRACTORNAME`, `APPLICANTCOMPANYNAME`; an
owner can be a homeowner) and the account fields `CREATOR`/`EDITOR` are
dropped. `WORKDETAIL` is free text that routinely signs off with the utility
staff behind the application: 41 of the 1,460 had an e-mail address or a phone
number, and others name people with neither ("Designer Name: ...", "per site
discussions with UFD (a name)"), which no pattern removes reliably. It is not
kept, in the evidence or the summary; the work is described by the permit's
own work flags. `OBJECTID` (also the feature id) is a row number of the
automated reload (around 436.7 million on 5 November) and `GLOBALID` the
server's row id beside it: neither is content, neither is kept, so a reload
is no revision (the permit number is the id).

Licence: "This work is licensed under a Creative Commons Attribution 4.0
International License" (the licenseInfo of ArcGIS item
fc7a616c7b8c4b2994759d61f5a826b7, read 5 November 2026).
"""

from datetime import datetime, timedelta
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
    epoch_ms,
    fetch_arcgis_features,
    item_record,
    local_day,
    whole_days,
)
from .feed_text import sentences

SOURCE_ID = "dc-ddot-construction-permits"
LAYER = "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/12"
SOURCE_URL = "https://www.arcgis.com/home/item.html?id=fc7a616c7b8c4b2994759d61f5a826b7"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Source: District Department of Transportation (DDOT), Construction Permits in the Last 30 Days "
    "(DC GIS Open Data). CC BY 4.0."
)
WASHINGTON = ZoneInfo("America/New_York")
# The permittee, owner, contractor and applicant can be people; the account fields name staff.
PERSONAL = frozenset(
    {"PERMITTEENAME", "OWNERNAME", "CONTRACTORNAME", "APPLICANTCOMPANYNAME", "CREATOR", "EDITOR"}
)
# Free text naming staff with their e-mail addresses and phone numbers: not kept.
FREE_TEXT = frozenset({"WORKDETAIL"})
# The layer's row number and row id, renewed on reload: not content.
ROW_NUMBERS = frozenset({"OBJECTID", "GLOBALID"})
# The permit's work flags, in the layer's own words (field aliases "Is Excavation" ...).
WORKS = (
    ("ISEXCAVATION", "Excavation"),
    ("ISPAVING", "Paving"),
    ("ISFIXTURE", "Fixture"),
    ("ISLANDSCAPING", "Landscaping"),
    ("ISPROJECTIONS", "Projections"),
    ("ISPSRENTAL", "PS Rental"),
)
# The works that dig or pave a street.
ROAD_WORKS = frozenset({"Excavation", "Paving"})


def dc_ddot_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("united-states")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="District of Columbia DDOT construction permits (last 30 days)",
        organization="District of Columbia, District Department of Transportation (DDOT)",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="District of Columbia (Washington)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method=(
            "ArcGIS feature service (DC GIS), GeoJSON in WGS 84, Issued permits not yet expired, "
            "1,000 a page; no key"
        ),
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="en",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="dc_ddot_construction_permits",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; two requests a run (1,000 permits a page).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=f"Creative Commons Attribution 4.0 International ({LICENCE_URL}), the ArcGIS item's licence",
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each permit as the service returns it, less the permittee, owner, contractor and applicant "
            "company, the account fields, the free-text work detail and the row ids, and the "
            "structured event."
        ),
        notes=(
            "DDOT's public space construction permits, one point each at the permit's address. "
            "Fetched without a key on 5 November 2026: 1,460 Issued permits not yet expired; the "
            "1,340 that excavate or pave are kept (1,109 in effect, 231 starting later). Days are "
            "Washington days. The work detail is not kept: it names staff with e-mails and phones."
        ),
    )


def _works(properties: dict[str, Any]) -> list[str]:
    return [name for field, name in WORKS if clean(properties.get(field)).upper() == "T"]


def _located(geometry: Any, properties: dict[str, Any]) -> bool:
    """A point the geocoder placed: not missing, not at the 0,0 of an unmatched address."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return False
    position = geometry.get("coordinates")
    if not isinstance(position, list) or len(position) < 2:
        return False
    if not all(isinstance(value, (int, float)) for value in position[:2]):
        return False
    # The state-plane X,Y of an unmatched address is 0,0; its WGS 84 point is then not 0,0.
    unmatched = properties.get("XCOORD") == 0 and properties.get("YCOORD") == 0
    return not unmatched and position[:2] != [0, 0]


def _kept(feature: dict[str, Any]) -> dict[str, Any]:
    """The feature as REI keeps it: no people, no free text, no row ids."""
    properties = feature.get("properties") or {}
    left_out = PERSONAL | FREE_TEXT | ROW_NUMBERS
    return {
        "type": feature.get("type"),
        "geometry": feature.get("geometry"),
        "properties": {key: value for key, value in properties.items() if key not in left_out},
    }


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One permit as REI's record; None when it is not issued, digs and paves nothing, or is unlocated."""
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not _located(geometry, properties):
        return None
    permit = clean(properties.get("PERMITNUMBER"))
    status = clean(properties.get("STATUS"))
    works = _works(properties)
    if not permit or status.upper() != "ISSUED" or not ROAD_WORKS & set(works):
        return None
    address = clean(properties.get("WLFULLADDRESS"))
    start, end = whole_days(
        local_day(properties.get("EFFECTIVEDATE"), WASHINGTON),
        local_day(properties.get("EXPIRATIONDATE"), WASHINGTON),
        WASHINGTON,
    )
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        category=" / ".join(("Construction permit", *works)),
        status=status,
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
        title=f"Road works: {address or 'construction permit ' + permit} (Washington, DC)",
        summary=sentences(
            f"DDOT public space construction permit {permit}, {status.lower()}",
            f"Permitted work: {', '.join(name.lower() for name in works)}",
        ),
        categories=["construction permit", *(name.lower() for name in works)],
        item=_kept(feature),
        structured=structured,
        retrieved_at=retrieved_at,
        published_at=epoch_ms(properties.get("ISSUEDATE")),
    )


def where_clause(now: datetime | None = None) -> str:
    """Issued permits expiring yesterday (Washington) or later: a day's permit ends at that day's end."""
    today = (now or datetime.now(WASHINGTON)).astimezone(WASHINGTON).date()
    return f"STATUS = 'Issued' AND EXPIRATIONDATE >= DATE '{(today - timedelta(days=1)).isoformat()}'"


def fetch_permits(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    return fetch_arcgis_features(LAYER, user_agent, where=where_clause(now), client=client)


class DcDdotConstructionPermitsConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_permits)
    to_record = staticmethod(to_record)
