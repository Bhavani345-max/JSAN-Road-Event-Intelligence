"""Sources checked on 6 November 2026, NOT connected.

1. US WZDx feeds (decision 0060), below first.
2. A second search of the countries with no or few events (Poland, Latvia, Brazil,
   Ireland, Malaysia, South Africa): the notable finds, at the end. Full record:
   docs/data-sources/zero-event-countries-recheck-2026-11-06.md. None is connectable
   without permission; nothing else found was worth recording on its own.

US WZDx feeds (decision 0060).

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
    # --- Second search of the zero-event countries, 6 November 2026 -------------------
    _feed(
        source_id="pl-bialystok-road-disruptions", source_name="Białystok road disruptions (Utrudnienia drogowe)",
        organization="Urząd Miejski w Białymstoku", authority_type="MUNICIPAL_ROAD_AUTHORITY",
        country="PL", region="Podlaskie (Białystok)", city="poland", language="pl",
        source_url="https://www.arcgis.com/home/item.html?id=ef4d165fde7f497b97d469a74bafafa1",
        endpoint="https://services6.arcgis.com/jN5LJsqeW33UjdlH/arcgis/rest/services/Utrudnienia_drogowe/FeatureServer/0",
        access_method="ArcGIS feature service (lines); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        provides_segments=True,
        notes=(
            "On 6 November 2026: 13 closure and disruption lines, 10 in force, each with a start and an "
            "end (dates only) and the street; edited that day; it backs the city's public map. No licence "
            "on the layer, its web map, the city's ArcGIS organisation or dane.gov.pl. Ask Urząd Miejski "
            "w Białymstoku for an open licence (CC BY 4.0). Not connected."
        ),
    ),
    _feed(
        source_id="ie-galway-county-severe-weather-closures",
        source_name="Galway County Council severe-weather road closures",
        organization="Galway County Council", authority_type="MUNICIPAL_ROAD_AUTHORITY",
        country="IE", region="Galway (county)", city="ireland",
        source_url="https://opendata-galwaycoco.hub.arcgis.com/",
        endpoint="https://services1.arcgis.com/mJI7JYqAOKXPG7Hh/arcgis/rest/services/Severe_Weather_Road_Closures_View_Only/FeatureServer/0",
        access_method="ArcGIS feature service (lines); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        provides_segments=True,
        notes=(
            "On 6 November 2026: 3 road lines from the storm of 24 October 2026, all reopened; a logged "
            "date and a status but no start or end; staff user names in Creator/Editor (to be dropped). "
            "Its licence field holds a disclaimer and '(c) Galway County Council'; the council's open-data "
            "hub publishes its other 77 datasets under CC BY 4.0, not this one. Ask the council to add it "
            "there. Not connected."
        ),
    ),
    _feed(
        source_id="ie-kilkenny-road-notices", source_name="Kilkenny County Council road notices",
        organization="Kilkenny County Council", authority_type="MUNICIPAL_ROAD_AUTHORITY",
        country="IE", region="Kilkenny (county)", city="ireland",
        source_url="https://www.kilkennycoco.ie/eng/your_council/reuse_of_information/",
        endpoint="https://www.kilkennycoco.ie/eng/rss_roads_notices/",
        access_method="Web page (an HTML list, no feed despite the path)",
        integration_status=S.NOT_USABLE,
        provides_geometry=False,
        notes=(
            "On 6 November 2026: 14 items, about 4 of them closures, mixed with planning lists and filming "
            "notices; dates written without a year, no coordinates. The council's re-use page allows PSI "
            "re-use of downloads but reserves the rights to text and maps. Not connected."
        ),
    ),
    _feed(
        source_id="lv-riga-amd-street-repairs", source_name="Riga street surface repairs (ĀMD ielu seguma remontdarbi)",
        organization="Rīgas valstspilsētas pašvaldība, Ārtelpas un mobilitātes departaments",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        country="LV", region="Rīga", city="latvia", language="lv",
        source_url="https://data.gov.lv/dati/lv/dataset/amd-ielu-seguma-remontdarbi",
        endpoint="https://data.gov.lv/dati/lv/dataset/amd-ielu-seguma-remontdarbi",
        access_method="File on data.gov.lv (CKAN); no key",
        integration_status=S.NOT_USABLE,
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (data.gov.lv license_id CC-BY-4.0)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_segments=True,
        notes=(
            "File dated 15 October 2026, read 6 November 2026: 70 asphalt and 334 gravel street lines; "
            "notes say 31 done, 4 ongoing, 35 planned in 2026, but no record has a start or an end, so REI "
            "would show none. Not connected."
        ),
    ),
    _feed(
        source_id="br-artesp-programacao-de-obras",
        source_name="ARTESP works programme on São Paulo's concession highways (Programação de Obras)",
        organization="ARTESP (Agência de Transporte do Estado de São Paulo)", authority_type="STATE_ROAD_AUTHORITY",
        country="BR", region="São Paulo (state)", city="brazil", language="pt",
        source_url="https://dadosabertos.artesp.sp.gov.br/dataset/programacao-de-obras",
        endpoint="https://dadosabertos.artesp.sp.gov.br/dataset/programacao-de-obras",
        access_method="Files on ARTESP's open-data portal (CKAN); no key; robots.txt Crawl-Delay 10",
        integration_status=S.DISCOVERED,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Atribuição (dataset page)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        notes=(
            "On 4 and 6 November 2026 the dataset held only two 2026 circulars, XLSX templates, JSON "
            "schemas and example GeoJSON (road, km range, data_inicial/data_final, EPSG:4674): no works "
            "programme yet. Connectable once real files appear. Not connected."
        ),
    ),
    _feed(
        source_id="br-mt-sinfra-road-works", source_name="Mato Grosso SINFRA road works (Obras Viárias)",
        organization="SINFRA Mato Grosso (layer on a personal ArcGIS account)", authority_type="STATE_ROAD_AUTHORITY",
        country="BR", region="Mato Grosso", city="brazil", language="pt",
        source_url="https://services8.arcgis.com/WzZQ8WIosCQHAmSB/arcgis/rest/services",
        endpoint="https://services8.arcgis.com/WzZQ8WIosCQHAmSB/arcgis/rest/services/Obras_Vi%C3%A1rias_SINFRA/FeatureServer/0",
        access_method="ArcGIS feature service (lines); no key",
        integration_status=S.NOT_USABLE,
        provides_segments=True,
        notes=(
            "On 6 November 2026: 830 works lines (157 in progress, 24 to start), but the dates are contract "
            "dates, not traffic dates; a March 2026 snapshot on a personal account; no licence; inspectors "
            "named; outside REI's Brazilian cities. Not connected."
        ),
    ),
)
