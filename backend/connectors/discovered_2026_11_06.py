"""US WZDx feeds checked on 6 November 2026, NOT connected (decision 0060).

USDOT's WZDx feed registry (data.transportation.gov 69qe-yiui) listed 42 active
feeds that day: 15 REI already read, 13 need a key, and 14 needed no key and were
new to REI. Each of the 14 was fetched once (robots.txt read first) from this
machine and, where refused, once from REI's server on Railway. One is connected:
Washington State DOT, whose feed states CC0 1.0 (connectors/official/wzdx.py).
The other 13 are below, inactive and without a connector, each with the reason.
Endpoints are recorded without the access keys some registry URLs carry.
"""

from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    SourceClass,
    SourceDefinition,
    SourceType,
    TermsStatus,
)

from .official.wzdx import REGISTRY_URL

S = IntegrationStatus
WZDX = "WZDx GeoJSON feed listed in USDOT's WZDx feed registry; no key"
REFUSED = (
    "Refused on 6 November 2026: HTTP 403 from this machine and again from REI's server on "
    "Railway (an error page, not data), so automated access is not allowed. Not connected."
)


def _feed(**fields) -> SourceDefinition:
    return SourceDefinition(
        **{
            "source_tier": 1,
            "source_type": SourceType.API,
            "source_class": SourceClass.GOVERNMENT_OPEN_DATA,
            "authority_type": "STATE_ROAD_AUTHORITY",
            "country": "US",
            "city": "united-states",
            "language": "en",
            "source_url": REGISTRY_URL,
            "access_method": WZDX,
            "provides_geometry": True,
            **fields,
        }
    )


DISCOVERED_2026_11_06: tuple[SourceDefinition, ...] = (
    # --- Refused: HTTP 403 from both places --------------------------------------------
    _feed(
        source_id="us-ok-odot-wzdx", source_name="Oklahoma DOT work zones (WZDx)",
        organization="Oklahoma DOT", region="Oklahoma",
        endpoint="https://oktraffic.org/api/Geojsons/workzones",
        integration_status=S.BLOCKED,
        notes=f"{REFUSED} The registry's URL carries an access token (not kept here).",
    ),
    _feed(
        source_id="us-ut-udot-wzdx", source_name="Utah DOT work zones (WZDx)",
        organization="Utah DOT", region="Utah",
        endpoint="https://udottraffic.utah.gov/wzdx/udot/v40/data",
        integration_status=S.BLOCKED, notes=REFUSED,
    ),
    _feed(
        source_id="us-ia-iowadot-wzdx", source_name="Iowa DOT work zones (WZDx)",
        organization="Iowa DOT", region="Iowa",
        endpoint="https://iowa-atms.cloud-q-free.com/api/rest/dataprism/wzdx/wzdxfeed",
        integration_status=S.BLOCKED, notes=REFUSED,
    ),
    _feed(
        source_id="us-wi-wisdot-wzdx", source_name="Wisconsin DOT work zones (WZDx)",
        organization="Wisconsin DOT", region="Wisconsin",
        endpoint="https://511wi.gov/api/wzdx",
        integration_status=S.BLOCKED, notes=REFUSED,
    ),
    _feed(
        source_id="us-mo-modot-wzdx", source_name="Missouri DOT work zones (WZDx)",
        organization="Missouri DOT", region="Missouri",
        endpoint="https://traveler.modot.org/timconfig/feed/desktop/mo_wzdx.json",
        integration_status=S.BLOCKED,
        notes=(
            "On 6 November 2026: HTTP 403 from this machine; from REI's server on Railway the host "
            "name did not resolve. Not connected."
        ),
    ),
    # --- Not answering -------------------------------------------------------------------
    _feed(
        source_id="us-nm-nmdot-wzdx", source_name="New Mexico DOT work zones (WZDx)",
        organization="New Mexico DOT (feed published by Blyncsy)", region="New Mexico",
        endpoint="https://ai.blyncsy.io/wzdx/nmdot/feed",
        integration_status=S.BLOCKED,
        notes=(
            "On 6 November 2026: HTTP 503 'no healthy upstream' from this machine and from REI's "
            "server on Railway. Its sister feed for Hawaii, from the same publisher, has dates that "
            "are not the works' own (us-hi-hidot-wzdx); check the same before connecting. Not connected."
        ),
    ),
    # --- Fetched, but the dates are not the works' own -------------------------------------
    _feed(
        source_id="us-hi-hidot-wzdx", source_name="Hawaii DOT work zones (WZDx)",
        organization="Hawaii DOT (feed published by Blyncsy)", region="Hawaii",
        endpoint="https://ai.blyncsy.io/wzdx/hidot/feed",
        integration_status=S.NOT_USABLE,
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC0 1.0 Universal, stated in the feed's feed_info.license",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        notes=(
            "On 6 November 2026: 133 work zones with lines, but every one starts at the feed's update "
            "time (2026-11-04T21:02:41Z) and ends exactly 7 days later, none verified, impact "
            "'unknown', named only 'Dillingham Blvd Work Zone 1' and the like. The periods are not the "
            "works' own, and REI does not show invented times. Not connected."
        ),
    ),
    # --- Fetched, but no licence and no readable terms: permission to ask --------------------
    _feed(
        source_id="us-id-itd-wzdx", source_name="Idaho Transportation Department work zones (WZDx)",
        organization="Idaho Transportation Department (511 system run by Arcadis)", region="Idaho",
        endpoint="https://511.idaho.gov/api/wzdx",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        notes=(
            "On 6 November 2026: 723 work zones, all with lines and dates; robots.txt allows the feed. "
            "No licence in its feed_info, its developer page states no terms, and the 'User Terms and "
            "Conditions' page of 511.idaho.gov has no text. Terms silent: awaiting ITD's permission. "
            "Not connected."
        ),
    ),
    _feed(
        source_id="us-fl-fdot-wzdx", source_name="Florida DOT work zones (WZDx)",
        organization="Florida DOT (feed published by one.network)", region="Florida",
        endpoint="https://us-datacloud.one.network/fdot/feed.json",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        notes=(
            "On 6 November 2026: 106 MB in one response, 28,464 features (3,176 work zones, 25,288 "
            "detours), all with lines and dates. No licence in its feed_info (publisher one.network) "
            "and the terms page of fl511.com has no text. Terms silent: awaiting FDOT's permission; "
            "its size would also need a long polling interval. The registry's URL carries an app key "
            "(not kept here). Not connected."
        ),
    ),
    _feed(
        source_id="us-nec-wzdx", source_name="New Hampshire, Vermont and Maine work zones (WZDx)",
        organization="NHDOT, VTrans and MaineDOT (New England Compass)", region="New Hampshire, Vermont, Maine",
        endpoint="https://api.dx.ne-compass.com/wzdx-latest/",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        notes=(
            "On 6 November 2026: 198 work zones, all with lines and dates. No licence in its "
            "feed_info. Each state's 'Traveler Information Terms and Conditions of Use and Access and "
            "Development' (PDFs on newengland511.org/terms) covers the data feeds and expects users to "
            "'download, store, and use the data', but says nothing about commercial use or a licence. "
            "Terms silent: awaiting the states' permission. Not connected."
        ),
    ),
    # --- robots.txt forbids it ---------------------------------------------------------------
    _feed(
        source_id="us-ms-mdot-wzdx", source_name="Mississippi DOT work zones (WZDx)",
        organization="Mississippi DOT", region="Mississippi",
        endpoint="https://api.mdottraffic.com/prod/v3/data/wzdx",
        integration_status=S.BLOCKED,
        notes="robots.txt of api.mdottraffic.com is 'User-agent: * Disallow: /' (6 November 2026); not fetched.",
    ),
    # --- Not a road authority's feed ---------------------------------------------------------
    _feed(
        source_id="us-civiclink-crewcast-wzdx", source_name="CivicLink CrewCast work zones (WZDx)",
        organization="CivicLink", authority_type="COMMERCIAL", region="United States",
        source_class=SourceClass.COMMERCIAL, source_tier=None,
        endpoint="https://road-connect-community-bry7272.replit.app/api/wzdx/work-zones.geojson",
        integration_status=S.NOT_USABLE,
        notes=(
            "A community app on replit.app, not a road authority; its robots.txt is 'User-agent: * "
            "Disallow: /' (6 November 2026), so it was not fetched."
        ),
    ),
    _feed(
        source_id="us-purposebuilt-cwz", source_name="PurposeBuilt Systems Digital Traffic Control Diary (CWZ)",
        organization="PurposeBuilt Systems, LLC", authority_type="COMMERCIAL", region="United States",
        source_class=SourceClass.COMMERCIAL, source_tier=None,
        endpoint="https://feeds.purposebuilt.systems/cwz",
        access_method="CWZ 1.0 GeoJSON feed listed in USDOT's WZDx feed registry; no key",
        integration_status=S.NOT_USABLE,
        cost_category=CostCategory.FREE_PUBLIC,
        licence="CC0 1.0 Universal, stated in the feed's feed_info.license",
        notes=(
            "A company's traffic-control diary in the CWZ 1.0 format, not a road authority's feed: "
            "1 work zone on 6 November 2026 (I-80 E). Not connected."
        ),
    ),
)
