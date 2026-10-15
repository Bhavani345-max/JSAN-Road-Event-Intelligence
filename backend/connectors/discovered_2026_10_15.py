"""Canada, Australia and South Africa: researched on 15 October 2026, NOT connected.

Each is inactive and has no connector; listed so the coverage of the three
countries is visible in one place, with what stops each. The full record is in
docs/data-sources/{canada,australia,south-africa}-source-research-2026-10-15.md.
The connected ones are in connectors/official/ (decision 0029).
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

S = IntegrationStatus


def _researched(**fields) -> SourceDefinition:
    return SourceDefinition(**{"source_tier": 1, "source_type": SourceType.API, "language": "en", **fields})


DISCOVERED_2026_10_15: tuple[SourceDefinition, ...] = (
    # --- South Africa: nothing passes every check -----------------------------------
    _researched(
        source_id="western-cape-road-closures",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="ZA", region="Western Cape", city="south-africa",
        source_name="Western Cape public road closures",
        organization="Western Cape Government, Department of Infrastructure",
        authority_type="PROVINCIAL_ROAD_AUTHORITY",
        source_url="https://gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer",
        access_method="ArcGIS feature service (lines); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.CONTRACT_REQUIRED,
        provides_geometry=True,
        notes=(
            "47 provincial road closures with lines on 15 October 2026, all marked Approved, all "
            "without an end date (so none would be shown). No licence on the layer; the "
            "provincial terms say commercial reuse 'may be granted subject to a written request' "
            "to service@westerncape.gov.za. Not connected."
        ),
    ),
    _researched(
        source_id="sanral-i-traffic",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="ZA", region="National", city="south-africa",
        source_name="SANRAL i-TRAFFIC",
        organization="South African National Roads Agency (SANRAL)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://www.i-traffic.co.za/",
        access_method="Developer API; without a key it answers HTTP 400 'Invalid Key'",
        integration_status=S.REQUIRES_ACCESS,
        terms_status=TermsStatus.RESTRICTED,
        commercial_use=CommercialUse.CONTRACT_REQUIRED,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        notes=(
            "National roads. Needs a developer key, and its terms forbid redistribution, "
            "commercial use and robots without SANRAL's written consent. Not connected."
        ),
    ),
    # --- Canada: passed, not connected --------------------------------------------------
    _researched(
        source_id="montreal-entraves-travaux",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="CA", region="Quebec", city="canada",
        source_name="Ville de Montréal works and obstructions",
        organization="Ville de Montréal",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://donnees.montreal.ca/",
        access_method="CSV download (points); no key",
        integration_status=S.VALIDATED,
        terms_status=TermsStatus.PERMITS_TESTING,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        language="fr",
        notes=(
            "2,209 permits with points on 15 October 2026, CC BY 4.0. Not connected: its times "
            "look like local day boundaries written with the UTC offset's sign reversed, which is "
            "undocumented; reading them would mean guessing the times. Ask the City first."
        ),
    ),
    _researched(
        source_id="quebec-mtmd-road-works",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="CA", region="Quebec", city="canada",
        source_name="Transports Québec road works and warnings",
        organization="Ministère des Transports et de la Mobilité durable du Québec",
        authority_type="PROVINCIAL_ROAD_AUTHORITY",
        source_url="https://ws.mapserver.transports.gouv.qc.ca/swtq",
        access_method="WFS (lines); no key",
        integration_status=S.BLOCKED,
        terms_status=TermsStatus.PERMITS_TESTING,
        provides_geometry=True,
        language="fr",
        notes=(
            "526 road works and 19 warnings with lines on 15 October 2026, CC BY 4.0. Its "
            "robots.txt sits behind a Cloudflare challenge and could not be read: whether to use "
            "it is the user's decision. Not connected."
        ),
    ),
    _researched(
        source_id="brampton-road-closures",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="CA", region="Ontario", city="canada",
        source_name="City of Brampton road closures",
        organization="City of Brampton",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/BramptonWorks_OpenData/FeatureServer/3",
        access_method="ArcGIS feature service (lines); no key",
        integration_status=S.VALIDATED,
        terms_status=TermsStatus.PERMITS_TESTING,
        provides_geometry=True,
        notes="6 long-running closures on 15 October 2026, 'CC BY' (no version). Too small to connect yet.",
    ),
    _researched(
        source_id="canada-provincial-511-apis",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="CA", region="Several provinces", city="canada",
        source_name="Ontario, Alberta, Manitoba, New Brunswick and Yukon 511 APIs",
        organization="Provincial transportation ministries",
        authority_type="PROVINCIAL_ROAD_AUTHORITY",
        source_url="https://511on.ca/developers",
        access_method="Developer key per province",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        notes="Need a developer key each (the user's decision). Not connected.",
    ),
    # --- Australia: passed, not connected -----------------------------------------------
    _researched(
        source_id="qldtraffic-events",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="Queensland", city="australia",
        source_name="QLDTraffic events",
        organization="Queensland Department of Transport and Main Roads",
        authority_type="STATE_ROAD_AUTHORITY",
        source_url="https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api",
        access_method="GeoJSON API with a key; the specification prints a shared public key",
        integration_status=S.REQUIRES_ACCESS,
        terms_status=TermsStatus.PERMITS_TESTING,
        cost_category=CostCategory.FREE_WITH_LIMITS,
        provides_geometry=True,
        notes=(
            "529 events on 15 October 2026 (459 in force), CC BY 4.0. The specification offers a "
            "public key 'for developers who do not wish to register' (100 requests a minute, shared). "
            "Using a key is the user's decision. Not connected."
        ),
    ),
    _researched(
        source_id="transport-nsw-live-traffic",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="New South Wales", city="australia",
        source_name="Transport for NSW Live Traffic hazards",
        organization="Transport for NSW",
        authority_type="STATE_ROAD_AUTHORITY",
        source_url="https://opendata.transport.nsw.gov.au/",
        access_method="API with a registered key (HTTP 401 without)",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        provides_geometry=True,
        notes="CC BY 4.0; needs a registered key (the user's decision). Not connected.",
    ),
    _researched(
        source_id="victoria-dtp-disruptions",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="Victoria", city="australia",
        source_name="Victoria Department of Transport and Planning disruptions",
        organization="Department of Transport and Planning, Victoria",
        authority_type="STATE_ROAD_AUTHORITY",
        source_url="https://opendata.transport.vic.gov.au/",
        access_method="API with a KeyID header (HTTP 401 without)",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        provides_geometry=True,
        notes="CC BY 4.0; needs a registered key (the user's decision). Not connected.",
    ),
    _researched(
        source_id="radar-national-roadworks",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="AU", region="National", city="australia",
        source_name="Harmonised National Roadworks and Road Closures (RADAR)",
        organization="Australian Government, Department of Infrastructure, Transport, Regional Development, Communications, Sport and the Arts",
        authority_type="NATIONAL_TRANSPORT_AUTHORITY",
        source_url="https://catalogue.data.infrastructure.gov.au/dataset/harmonised-national-roadworks-and-road-closures",
        access_method="ArcGIS feature service (points); no key; refreshed nightly",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        provides_geometry=True,
        notes=(
            "10,833 records from every state on 15 October 2026 (VIC 8,202). CC BY 4.0 on the "
            "Digital Atlas listing, 'Licence not specified' in the department's catalogue; includes "
            "other parties' material; nightly; overlaps the state feeds. Not connected."
        ),
    ),
    _researched(
        source_id="nt-road-report",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="Northern Territory", city="australia",
        source_name="NT Road Report",
        organization="Northern Territory Government",
        authority_type="TERRITORY_ROAD_AUTHORITY",
        source_url="https://roadreport.nt.gov.au/",
        access_method="JSON API; no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        provides_geometry=True,
        notes="82 obstructions on 15 October 2026. No licence stated; NT copyright reserves reuse. Not connected.",
    ),
    _researched(
        source_id="tasmania-state-growth-roadworks",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="Tasmania", city="australia",
        source_name="Tasmania State Growth roadworks",
        organization="Tasmanian Department of State Growth",
        authority_type="STATE_ROAD_AUTHORITY",
        source_url="https://data.stategrowth.tas.gov.au/",
        access_method="GeoServer WFS (lines); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        provides_geometry=True,
        notes=(
            "36 roadworks on 15 October 2026. No licence stated; the Tasmanian Government default "
            "is non-commercial. Not connected."
        ),
    ),
    _researched(
        source_id="traffic-sa-open-data",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="South Australia", city="australia",
        source_name="Traffic SA open data",
        organization="South Australia Department for Infrastructure and Transport",
        authority_type="STATE_ROAD_AUTHORITY",
        source_url="https://maps.sa.gov.au/",
        access_method="ArcGIS service; answered 'configured to block access from your country' (tested from India)",
        integration_status=S.BLOCKED,
        notes="Untested: blocked by country from the research machine; may answer from production. Not connected.",
    ),
)
