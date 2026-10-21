"""Sources that have been researched but are NOT connected.

None of these is ever fetched: each is inactive and has no connector. They are
kept in the registry so the state of REI's source coverage is visible in one
place. Findings are from checks made on 2 October 2026; the full record is in
docs/data-sources/hyderabad-source-research.md.

A field is left unset where it could not be established. Classification
fields (source_class, country, city, cost, terms) were added on 6 October 2026;
a cost category is given only where there is some machine access to price.
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

DISCOVERED_SOURCES: tuple[SourceDefinition, ...] = (
    # --- Police and traffic authorities ----------------------------------
    SourceDefinition(
        source_id="hyderabad-traffic-police",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad",
        source_name="Hyderabad Traffic Police",
        organization="Hyderabad City Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://www.htp.gov.in/",
        access_method="Advisories are posted on Facebook, X and a WhatsApp channel",
        integration_status=S.MANUAL_ONLY,
        language="en",
        notes=(
            "The website links 'Traffic Updates' to the Facebook page. No RSS feed, "
            "API or advisory listing was found on the site."
        ),
    ),
    SourceDefinition(
        source_id="hyderabad-city-police",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Hyderabad City Police press notes",
        organization="Hyderabad City Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.PDF,
        source_url="https://www.hyderabadpolice.gov.in/",
        access_method="Press notes published as PDF files linked from the home page",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "Press notes include traffic diversion notices, but the newest one listed "
            "on 2 October 2026 was dated December 2025, so the listing appears not to "
            "be kept current. No RSS feed or API."
        ),
    ),
    SourceDefinition(
        source_id="cyberabad-police",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad",
        source_name="Cyberabad Police",
        organization="Cyberabad Police Commissionerate",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://www.cyberabadpolice.gov.in/",
        access_method="Advisories are posted on X, Facebook and WhatsApp",
        integration_status=S.MANUAL_ONLY,
        language="en",
        notes="No traffic advisory listing, RSS feed or API was found on the website.",
    ),
    SourceDefinition(
        source_id="cyberabad-traffic-pulse",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.REGISTRATION_REQUIRED,
        source_name="Cyberabad Traffic Pulse",
        organization="Cyberabad Police Commissionerate",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://cyberabadtrafficpulse.telangana.gov.in/",
        access_method="Personal subscription: alerts are sent to a registered phone",
        integration_status=S.MANUAL_ONLY,
        language="en",
        notes=(
            "A sign-up service that messages traffic alerts for chosen routes to an "
            "individual's phone. Its only web endpoints are for registration and are "
            "protected against automation. It publishes no data feed."
        ),
    ),
    SourceDefinition(
        source_id="rachakonda-police",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad",
        source_name="Rachakonda Police",
        organization="Rachakonda Police Commissionerate",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://rachakondapolice.telangana.gov.in/",
        integration_status=S.NOT_USABLE,
        notes=(
            "The website did not respond when checked on 2 October 2026. On 6 October 2026 "
            "three addresses (rachakondapolice.gov.in, www.rachakondapolice.gov.in, "
            "rachakondapolice.telangana.gov.in) did not resolve at all. The commissionerate "
            "is reported to have been renamed Malkajgiri Police Commissionerate; no website "
            "or feed under that name was found. Advisories reach the public through news "
            "reports."
        ),
    ),
    SourceDefinition(
        source_id="telangana-state-police",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana",
        source_name="Telangana State Police",
        organization="Telangana State Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://www.tspolice.gov.in/",
        integration_status=S.MANUAL_ONLY,
        notes=(
            "Checked 6 October 2026: news headlines only; no traffic advisory section, RSS "
            "feed, API or open data."
        ),
    ),
    SourceDefinition(
        source_id="tgiccc",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana",
        city="hyderabad",
        source_name="Telangana Integrated Command and Control Centre (TGiCCC)",
        organization="Telangana Police",
        authority_type="TRAFFIC_MANAGEMENT_CENTRE",
        source_tier=1,
        source_type=SourceType.MANUAL,
        integration_status=S.NOT_USABLE,
        notes=(
            "Checked 6 October 2026: no public website, API, open data or dashboard was "
            "found. Published descriptions are of internal systems (traffic management, "
            "number-plate recognition, message signs). Not publicly available."
        ),
    ),
    SourceDefinition(
        source_id="telangana-gis",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="IN", region="Telangana",
        source_name="Telangana GIS (TRAC ArcGIS services)",
        organization="Telangana Remote Sensing Applications Centre",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://tgracgis.telangana.gov.in/arcgis/rest/services",
        endpoint="https://tgracgis.telangana.gov.in/arcgis/rest/services",
        access_method="ArcGIS REST services, as listed by a third party",
        integration_status=S.BLOCKED,
        notes=(
            "Checked 6 October 2026: the connection was refused, so no service, layer or "
            "terms could be seen. Whether it holds road or closure layers is not established."
        ),
    ),
    # --- Civic and disaster authorities ----------------------------------
    SourceDefinition(
        source_id="ghmc",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad",
        source_name="Greater Hyderabad Municipal Corporation",
        organization="Greater Hyderabad Municipal Corporation",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://www.ghmc.gov.in/",
        access_method="Website pages, tender notices, X and Facebook",
        integration_status=S.MANUAL_ONLY,
        notes=(
            "No road-works, closure or waterlogging notices, RSS feed, API or open "
            "data were found on the website. Its 'Traffic and Transportation' page is "
            "a departmental description."
        ),
    ),
    SourceDefinition(
        source_id="hydraa",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad",
        source_name="HYDRAA",
        organization="Hyderabad Disaster Response and Asset Protection Agency",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://hydraa.telangana.gov.in/",
        access_method="X, Facebook, WhatsApp channel; a news page on the website",
        integration_status=S.MANUAL_ONLY,
        notes=(
            "The news page showed no items without running its web application, and "
            "no RSS feed or API was found. Its rainfall links lead to TGDPS pages."
        ),
    ),
    SourceDefinition(
        source_id="tgdps-rainfall",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC, real_time=True,
        source_name="TGDPS live rainfall",
        organization="Telangana Development Planning Society",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.HTML,
        source_url="https://tgdps.telangana.gov.in/liveghmcrain.jsp",
        access_method="Public web pages with a table of rainfall per weather station",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "Rainfall in millimetres per automatic weather station for the Hyderabad "
            "area, updated through the day. It is an HTML table, not an API. Rainfall "
            "is context for possible waterlogging, not a road event, so it is not "
            "fed into event creation."
        ),
    ),
    SourceDefinition(
        source_id="open-data-telangana",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="IN", region="Telangana", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Open Data Telangana",
        organization="Government of Telangana",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.CSV,
        source_url="https://data.telangana.gov.in/",
        access_method="Dataset downloads from a web portal",
        integration_status=S.DISCOVERED,
        notes=(
            "Publishes historical datasets such as daily weather by mandal. No "
            "road-works or road-closure dataset was found, and no public API could "
            "be confirmed. Historical data is not a live road-event source."
        ),
    ),
    SourceDefinition(
        source_id="ndma-sachet-telangana",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", cost_category=CostCategory.FREE_PUBLIC, real_time=True,
        source_name="NDMA SACHET alerts (Telangana)",
        organization="National Disaster Management Authority",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.RSS,
        source_url="https://sachet.ndma.gov.in/",
        endpoint="https://sachet.ndma.gov.in/cap_public_website/rss/rss_telangana.xml",
        access_method="Public RSS feed of Common Alerting Protocol messages",
        integration_status=S.DISCOVERED,
        notes=(
            "A working official feed of weather and flood warnings issued by IMD "
            "Hyderabad and the Central Water Commission. Alerts are at district "
            "level and describe weather, not roads, so it is context only and is "
            "not connected to event creation."
        ),
    ),
    SourceDefinition(
        source_id="imd-hyderabad",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="IMD Meteorological Centre Hyderabad",
        organization="India Meteorological Department",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.PDF,
        source_url="https://mausam.imd.gov.in/hyderabad/",
        access_method="Forecast and rainfall bulletins published as PDF files",
        integration_status=S.DISCOVERED,
        notes=(
            "District-level forecasts and rainfall bulletins. Weather context only. "
            "Its warnings also reach the NDMA SACHET feed in machine-readable form."
        ),
    ),
    # --- Road authorities and transport operators ------------------------
    SourceDefinition(
        source_id="nhai",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN",
        source_name="National Highways Authority of India",
        organization="National Highways Authority of India",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.MANUAL,
        source_url="https://nhai.gov.in/",
        integration_status=S.MANUAL_ONLY,
        notes="No closure or diversion notices, feed or API were found on the website.",
    ),
    SourceDefinition(
        source_id="hmda",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Hyderabad Metropolitan Development Authority",
        organization="Hyderabad Metropolitan Development Authority",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.HTML,
        source_url="https://www.hmda.gov.in/notices/",
        access_method="Notices page on the website",
        integration_status=S.DISCOVERED,
        notes=(
            "The notices page is reachable, but whether it carries road closures "
            "(for example on the Outer Ring Road) was not established."
        ),
    ),
    SourceDefinition(
        source_id="tgsrtc",
        source_class=SourceClass.PARTNER, country="IN", region="Telangana",
        source_name="TGSRTC",
        organization="Telangana State Road Transport Corporation",
        authority_type="TRANSPORT_OPERATOR",
        source_tier=2,
        source_type=SourceType.MANUAL,
        source_url="https://www.tgsrtc.telangana.gov.in/",
        integration_status=S.MANUAL_ONLY,
        notes=(
            "No service-diversion notices, feed or API were found. Its 'Open Data' "
            "page describes IT initiatives rather than offering data."
        ),
    ),
    SourceDefinition(
        source_id="hyderabad-metro",
        source_class=SourceClass.PARTNER, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Hyderabad Metro Rail",
        organization="L&T Metro Rail (Hyderabad) Ltd.",
        authority_type="TRANSPORT_OPERATOR",
        source_tier=2,
        source_type=SourceType.RSS,
        source_url="https://ltmetro.com/",
        endpoint="https://ltmetro.com/feed/",
        access_method="Public RSS feed of company news",
        integration_status=S.NOT_USABLE,
        notes=(
            "The feed works but carries corporate news; its newest item was dated "
            "December 2025. It has no road-event content."
        ),
    ),
    SourceDefinition(
        source_id="rgia",
        source_class=SourceClass.PARTNER, country="IN", region="Telangana", city="hyderabad",
        source_name="Rajiv Gandhi International Airport",
        organization="GMR Hyderabad International Airport Ltd.",
        authority_type="TRANSPORT_OPERATOR",
        source_tier=2,
        source_type=SourceType.MANUAL,
        source_url="https://www.hyderabad.aero/",
        access_method="Website advisories, X, Facebook and a WhatsApp channel",
        integration_status=S.MANUAL_ONLY,
        notes="No airport-access or road advisories, feed or API were found on the website.",
    ),
    # --- Other news feeds --------------------------------------------------
    SourceDefinition(
        source_id="times-of-india-hyderabad",
        source_class=SourceClass.PUBLISHER, discovery_only=True, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="The Times of India (Hyderabad)",
        organization="The Times of India",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://timesofindia.indiatimes.com/city/hyderabad",
        endpoint="https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms",
        access_method="Public RSS feed",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "The feed works (20 items, under a day), but items carry no tags and no "
            "body and most have no summary, so with the current rules an article can "
            "only be placed in Hyderabad if its headline names the city. Reuse terms "
            "could not be confirmed."
        ),
    ),
    SourceDefinition(
        source_id="hyderabad-mail",
        source_class=SourceClass.PUBLISHER, discovery_only=True, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Hyderabad Mail",
        organization="Hyderabad Mail",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://hyderabadmail.com/",
        endpoint="https://hyderabadmail.com/feed/",
        access_method="Public RSS feed",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "The feed works (10 items, under a day) and the site has reported "
            "Hyderabad traffic advisories. Not connected: the reliability of the "
            "publication has not been assessed."
        ),
    ),
    SourceDefinition(
        source_id="telangana-tribune",
        source_class=SourceClass.PUBLISHER, discovery_only=True, country="IN", region="Telangana", city="hyderabad", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Telangana Tribune",
        organization="Telangana Tribune",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://www.telanganatribune.com/",
        endpoint="https://www.telanganatribune.com/feed/",
        access_method="Public RSS feed",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "The feed works (10 items, about two days). Not connected: the "
            "reliability of the publication has not been assessed."
        ),
    ),
    # --- Commercial traffic data providers ----------------------------------
    SourceDefinition(
        source_id="tomtom-traffic-incidents",
        source_class=SourceClass.COMMERCIAL, cost_category=CostCategory.FREE_WITH_LIMITS, rate_limit="2,500 requests a month on the free plan, as listed in the API documentation on 2 October 2026", provides_geometry=True, provides_direction=True, real_time=True, commercial_use=CommercialUse.CONTRACT_REQUIRED,
        source_name="TomTom Traffic Incidents API",
        organization="TomTom",
        authority_type="COMMERCIAL",
        source_type=SourceType.API,
        source_url="https://docs.tomtom.com/traffic-api/documentation/traffic-incidents/incident-details",
        access_method="REST API with an API key",
        integration_status=S.REQUIRES_ACCESS,
        notes=(
            "Incidents with geometry, category (road closed, road works, flooding, "
            "jam, accident, …), start and end times; planned incidents can be "
            "requested. India is listed in the coverage table; coverage and quality "
            "for Hyderabad have not been tested. The free allowance listed for this "
            "API is 2,500 requests a month. Storage and redistribution terms have "
            "not been reviewed. No tier assigned: it is not yet an approved source."
        ),
    ),
    SourceDefinition(
        source_id="here-traffic",
        source_class=SourceClass.COMMERCIAL, cost_category=CostCategory.UNKNOWN, provides_geometry=True, real_time=True, commercial_use=CommercialUse.CONTRACT_REQUIRED,
        source_name="HERE Traffic API",
        organization="HERE Technologies",
        authority_type="COMMERCIAL",
        source_type=SourceType.API,
        source_url="https://docs.here.com/traffic-api/docs",
        access_method="REST API with an API key",
        integration_status=S.REQUIRES_ACCESS,
        notes=(
            "HERE's documentation lists India among countries with real-time flow "
            "and incident coverage. Hyderabad coverage, plan limits and terms were "
            "not verified. No tier assigned: it is not yet an approved source."
        ),
    ),
    SourceDefinition(
        source_id="mappls",
        source_class=SourceClass.COMMERCIAL, cost_category=CostCategory.PAID, commercial_use=CommercialUse.CONTRACT_REQUIRED,
        source_name="Mappls (MapmyIndia)",
        organization="CE Info Systems Ltd.",
        authority_type="COMMERCIAL",
        source_type=SourceType.API,
        source_url="https://www.mappls.com/",
        access_method="Commercial APIs under contract",
        integration_status=S.REQUIRES_ACCESS,
        notes=(
            "Advertises real-time incident and road-closure data, including closures "
            "supplied by traffic police in some cities. No public documentation of "
            "an incidents API, and no evidence of Hyderabad coverage, was found. "
            "No tier assigned."
        ),
    ),
    SourceDefinition(
        source_id="waze-for-cities",
        source_class=SourceClass.COMMERCIAL, cost_category=CostCategory.PARTNER_ONLY, provides_geometry=True, real_time=True, commercial_use=CommercialUse.NOT_PERMITTED,
        source_name="Waze for Cities",
        organization="Google (Waze)",
        authority_type="COMMERCIAL",
        source_type=SourceType.PARTNER_FEED,
        source_url="https://www.waze.com/",
        access_method="Partner data exchange",
        integration_status=S.NOT_USABLE,
        notes=(
            "Membership is for government agencies and road operators that contribute "
            "their own traffic data. REI does not qualify, and no Hyderabad agency "
            "partnership was found."
        ),
    ),
    # --- International sources researched 6–13 October 2026 ---------------
    # NYC and France are now connected in connectors/official/; new regional
    # discoveries below remain inactive until access and terms are resolved.
    SourceDefinition(
        source_id="511ny",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="US", region="New York",
        source_name="511NY events API",
        organization="New York State Department of Transportation",
        authority_type="TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://511ny.org/developers",
        access_method="REST API with a developer key after an access request and agreement",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        rate_limit="10 calls every 60 seconds (511NY developer help, as quoted in search results)",
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        notes=(
            "Events on state-maintained roads with type, severity, direction, start and "
            "planned end, coordinates and an encoded polyline. The developer pages could "
            "not be read directly (they run only as a web application) and the Developers "
            "Access Agreement could not be retrieved; facts come from search results and a "
            "third-party mirror. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="511-sf-bay-wzdx",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="US", region="San Francisco Bay Area",
        source_name="511 SF Bay work-zone and closure feed (WZDx)",
        organization="Metropolitan Transportation Commission / 511 SF Bay",
        authority_type="REGIONAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://511.org/open-data/faqs",
        endpoint="https://api.511.org/traffic/wzdx",
        access_method="WZDx feed; requires a free 511 Open Data API key",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        rate_limit="No numeric limit established in the feed FAQ.",
        provides_geometry=True,
        provides_segments=True,
        real_time=True,
        notes=(
            "511 states its WZDx feed covers local streets, freeways and state highways "
            "in participating Bay Area jurisdictions. Individual feed terms and exact "
            "coverage should be confirmed after API-key registration."
        ),
    ),
    SourceDefinition(
        source_id="qld-traffic-geojson",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="Queensland",
        source_name="Queensland QLDTraffic GeoJSON feeds",
        organization="Queensland Department of Transport and Main Roads",
        authority_type="STATE_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api",
        endpoint="https://qldtraffic.qld.gov.au/",
        access_method="GeoJSON API; API access key described in the developer specification",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        licence="Creative Commons Attribution 4.0 (dataset listing)",
        attribution="State of Queensland (Department of Transport and Main Roads)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        notes=(
            "The Queensland Open Data listing documents GeoJSON feeds for hazards, crashes, "
            "congestion, flooding, roadworks and special events, and lists CC BY 4.0. The "
            "developer guide specifies API access keys; the public endpoint and its current "
            "key conditions need validation before integration."
        ),
    ),
    SourceDefinition(
        source_id="germany-autobahn-traffic",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="DE", region="Germany",
        source_name="Autobahn GmbH roadworks, warnings and closures API",
        organization="Die Autobahn GmbH des Bundes",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://www.autobahn.de/betrieb-verkehr/verkehrsmeldungen",
        endpoint="https://verkehr.autobahn.de/o/autobahn",
        access_method="Public REST API, organized by autobahn route",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.UNKNOWN,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        provides_geometry=True,
        real_time=True,
        notes=(
            "The public service exposes current roadworks, traffic warnings and closures "
            "by route. It requires route enumeration and several requests per route. The "
            "official re-use licence, rate limit and commercial terms were not established."
        ),
    ),
    SourceDefinition(
        source_id="tfnsw-live-traffic-hazards",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="AU", region="New South Wales",
        source_name="Transport for NSW Live Traffic hazards",
        organization="Transport for NSW",
        authority_type="TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://opendata.transport.nsw.gov.au/data/dataset/live-traffic-hazards",
        endpoint="https://api.transport.nsw.gov.au/v1/live/hazards/incident-open.json",
        access_method="GeoJSON files over HTTPS with an API key from the Open Data Hub",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        rate_limit="Default plan: 60,000 requests a day, 5 a second (opendata.transport.nsw.gov.au)",
        licence="Creative Commons Attribution 4.0 International",
        attribution="Transport for NSW is attributed as the source",
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        notes=(
            "Incidents, roadworks, floods, fires, major events and alpine conditions as "
            "GeoJSON, with planned start and end, lane-level direction and roads. Needs a "
            "registered account and key (HTTP 401 without one on 6 October 2026); no page "
            "states the key is free of charge. The guide warns that category values may "
            "change. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="lta-datamall-traffic-incidents",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="SG", region="Singapore",
        source_name="LTA DataMall traffic incidents and road works",
        organization="Land Transport Authority, Singapore",
        authority_type="TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html",
        endpoint="https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents",
        access_method="REST API with an AccountKey issued to registered subscribers",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        rate_limit="Up to 10 million calls a day; 500 records a call (API terms and user guide)",
        licence="Singapore Open Data Licence v1.0",
        provides_geometry=True,
        real_time=True,
        notes=(
            "Incidents (accidents, roadworks, breakdowns, diversions, …) every two minutes "
            "with a point and a text message, but no id, no start or end and direction "
            "only in the text. Approved road works have start and end dates but no "
            "coordinates. Needs a registered AccountKey. Not connected."
        ),
    ),
)


# --- Mumbai and Bengaluru (researched 7 October 2026) -----------------------
# Full record: docs/cities/mumbai-source-research.md and bengaluru-source-research.md.
# The two usable official listings are connected (connectors/official/); the
# rest are listed here so coverage is visible.
DISCOVERED_SOURCES += (
    SourceDefinition(
        source_id="mumbai-police-press-releases",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Maharashtra", city="mumbai", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Mumbai Police press releases",
        organization="Brihanmumbai Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.PDF,
        source_url="https://mumbaipolice.gov.in/PressRelease",
        access_method="Static HTML list of press notes, each a scanned Marathi PDF",
        integration_status=S.DISCOVERED,
        language="mr",
        notes=(
            "49 rows on 7 October 2026, mostly crime bulletins; a few traffic DCP press "
            "notes a month, one confirmed to repeat a Traffic Police notification. Scanned "
            "PDFs, no text layer. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="bmc-mcgm",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Maharashtra", city="mumbai",
        source_name="Brihanmumbai Municipal Corporation (BMC / MCGM) portal",
        organization="Brihanmumbai Municipal Corporation",
        authority_type="MUNICIPAL",
        source_tier=1,
        source_type=SourceType.HTML,
        source_url="https://portal.mcgm.gov.in/",
        access_method="SAP portal; answers a non-browser client with an error page",
        integration_status=S.BLOCKED,
        language="en",
        notes=(
            "On 7 October 2026 the portal returned 'iView is not compatible with your "
            "browser' to a plain HTTP client; no road-works or closure listing was found. "
            "The disaster-management site's data comes from a private API. Needs a browser check."
        ),
    ),
    SourceDefinition(
        source_id="mmrda-press-releases",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Maharashtra", city="mumbai", cost_category=CostCategory.FREE_PUBLIC,
        source_name="MMRDA news and announcements",
        organization="Mumbai Metropolitan Region Development Authority",
        authority_type="GOVERNMENT",
        source_tier=1,
        source_type=SourceType.PDF,
        source_url="https://mmrda.maharashtra.gov.in/en/other-services/news-and-announcements",
        access_method="Static listing of dated press releases (PDF); the server's TLS chain is incomplete",
        integration_status=S.DISCOVERED,
        language="en",
        notes=(
            "Project news (metro blocks, barricade removal, corridor lengths); no closure or "
            "diversion notice with roads and dates was found on 7 October 2026. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="msrdc",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Maharashtra", city="mumbai",
        source_name="Maharashtra State Road Development Corporation",
        organization="MSRDC",
        authority_type="ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.HTML,
        source_url="https://msrdc.in/",
        access_method="Unknown: the site reset every connection on 7 October 2026",
        integration_status=S.NOT_USABLE,
        language="en",
        notes="Could not be reached. msrdc.org is an unrelated real-estate blog and is excluded.",
    ),
    SourceDefinition(
        source_id="hindustan-times-mumbai",
        source_class=SourceClass.PUBLISHER, country="IN", region="Maharashtra", city="mumbai", cost_category=CostCategory.FREE_PUBLIC,
        source_name="Hindustan Times (Mumbai)",
        organization="HT Media",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://www.hindustantimes.com/cities/mumbai-news",
        endpoint="https://www.hindustantimes.com/feeds/rss/cities/mumbai-news/rssfeed.xml",
        access_method="Public RSS feed (one-line summaries)",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        language="en",
        discovery_only=True,
        notes=(
            "63 items over 34 hours on 7 October 2026, one-line summaries. RSS terms: "
            "solely for personal and non-commercial use; crawlers prohibited. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="indian-express-mumbai",
        source_class=SourceClass.PUBLISHER, country="IN", region="Maharashtra", city="mumbai", cost_category=CostCategory.FREE_PUBLIC,
        source_name="The Indian Express (Mumbai)",
        organization="Indian Express Group",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://indianexpress.com/section/cities/mumbai/",
        endpoint="https://indianexpress.com/section/cities/mumbai/feed/",
        access_method="Public RSS feed; titles only (descriptions and bodies empty)",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.RESTRICTED,
        language="en",
        discovery_only=True,
        notes=(
            "200 items over three weeks with empty bodies; the text needs the article page, "
            "and the terms prohibit automated tools and scrapers. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="btp-astram",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Karnataka", city="bengaluru",
        source_name="Bengaluru Traffic Police ASTraM",
        organization="Bengaluru Traffic Police",
        authority_type="POLICE",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://btp.karnataka.gov.in/209/astram/en",
        access_method="Described as an API for map service providers; no public endpoint or registration found",
        integration_status=S.REQUIRES_ACCESS,
        language="en",
        notes=(
            "The page describes congestion alerts every 15 minutes, incident reporting and an "
            "event calendar; nothing public was found on 7 October 2026. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="bbmp-gba",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IN", region="Karnataka", city="bengaluru",
        source_name="BBMP / Greater Bengaluru Authority",
        organization="Greater Bengaluru Authority (formerly BBMP)",
        authority_type="MUNICIPAL",
        source_tier=1,
        source_type=SourceType.API,
        source_url="https://gba.karnataka.gov.in/",
        access_method="React shell over api.bbmpgov.in and updates.bbmpgov.in, both unreachable",
        integration_status=S.BLOCKED,
        language="en",
        notes=(
            "bbmp.gov.in, updates.bbmpgov.in and api.bbmpgov.in refused or timed out from two "
            "networks on 7 October 2026. The GBA copyright policy permits reproduction with "
            "acknowledgement. Re-test another day."
        ),
    ),
    SourceDefinition(
        source_id="bmrcl-namma-metro",
        source_class=SourceClass.PARTNER, country="IN", region="Karnataka", city="bengaluru",
        source_name="BMRCL / Namma Metro news",
        organization="Bangalore Metro Rail Corporation",
        authority_type="TRANSPORT_OPERATOR",
        source_tier=2,
        source_type=SourceType.HTML,
        source_url="https://english.bmrc.co.in/news/",
        access_method="Client-rendered page over a raw-IP backend; No Data Found server-side",
        integration_status=S.NOT_USABLE,
        language="en",
        notes="Nothing readable without a browser on 7 October 2026. Not connected.",
    ),
    SourceDefinition(
        source_id="times-of-india-bengaluru",
        source_class=SourceClass.PUBLISHER, country="IN", region="Karnataka", city="bengaluru", cost_category=CostCategory.FREE_PUBLIC,
        source_name="The Times of India (Bengaluru)",
        organization="Times Internet",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://timesofindia.indiatimes.com/city/bangalore",
        endpoint="https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms",
        access_method="Public RSS feed (20-item rolling window, abstracts)",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        language="en",
        discovery_only=True,
        notes=(
            "20 items over 20 hours on 7 October 2026, 15 with abstracts. RSS terms require a "
            "link back and non-commercial use and forbid aggregation. Not connected, as for "
            "the Hyderabad feed."
        ),
    ),
    SourceDefinition(
        source_id="tv9-kannada-bengaluru",
        source_class=SourceClass.PUBLISHER, country="IN", region="Karnataka", city="bengaluru", cost_category=CostCategory.FREE_PUBLIC,
        source_name="TV9 Kannada (Bengaluru)",
        organization="TV9 Network",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://tv9kannada.com/karnataka/bengaluru",
        endpoint="https://tv9kannada.com/karnataka/bengaluru/feed",
        access_method="Public RSS feed, full text in Kannada",
        integration_status=S.VALIDATED,
        language="kn",
        discovery_only=True,
        notes=(
            "60 items over two days on 7 October 2026, full Kannada text, often quoting the "
            "traffic police's English posts. REI's detection rules are English; a Kannada "
            "term list would be needed first. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="deccan-herald-bengaluru",
        source_class=SourceClass.PUBLISHER, country="IN", region="Karnataka", city="bengaluru",
        source_name="Deccan Herald (Bengaluru)",
        organization="The Printers (Mysore)",
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_url="https://www.deccanherald.com/india/karnataka/bengaluru",
        access_method="No Bengaluru feed found; the site-wide feed held no Bengaluru items",
        integration_status=S.NOT_USABLE,
        terms_status=TermsStatus.RESTRICTED,
        language="en",
        discovery_only=True,
        notes="Terms: automated extraction, scraping and republication are not permitted. Not connected.",
    ),
)
