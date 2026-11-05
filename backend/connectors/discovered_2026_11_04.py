"""Sweden, Norway, Denmark, Estonia, Latvia, Poland, Ireland, Brazil and Malaysia:
researched on 4 November 2026, NOT connected.

Each is inactive and has no connector; listed so the coverage of the nine
countries is visible in one place, with what stops each (a key, a licence that
does not settle REI's use, a host that did not answer). The full records are in
docs/data-sources/{nordics,baltics-poland-ireland,brazil-malaysia}-sources-2026-11-04.md;
decision 0053. Connected that day: connectors/official/norway_vegvesen.py,
copenhagen_excavation.py and trafikverket.py (Sweden, with the user's key).
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


DISCOVERED_2026_11_04: tuple[SourceDefinition, ...] = (
    # --- Sweden: everything useful needs a free key ------------------------------------
    _researched(
        source_id="se-gothenburg-traffic-impact",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="SE", region="Västra Götaland", city="sweden",
        source_name="Göteborgs Stad traffic impact (TrafficInformation, Trafikpåverkan)",
        organization="Göteborgs Stad, Stadsmiljöförvaltningen",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://data.goteborg.se/PublicWebservices.aspx",
        access_method="Web service with an application key (APPID) from a free account on data.goteborg.se",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        licence="Göteborgs Stad: \"Göteborgs Stads öppna data är fritt att använda, utan avgifter eller licenser\" (goteborg.se/psidata)",
        commercial_use=CommercialUse.UNKNOWN,
        language="sv",
        notes=(
            "Listed on data.goteborg.se on 4 November 2026 as 'TrafficInformation' (Trafikpåverkan); "
            "the service's own description and licence field are shown only after signing in. A key "
            "is made under 'Mina applikationer' after registering. The city's statement reads as free "
            "use without a licence; confirm commercial use at registration. Not connected."
        ),
    ),
    _researched(
        source_id="se-gothenburg-start-permits",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="SE", region="Västra Götaland", city="sweden",
        source_name="Göteborgs Stad start permits for street works (StartPermissionService, Starttillstånd)",
        organization="Göteborgs Stad, Stadsmiljöförvaltningen",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://data.goteborg.se/PublicWebservices.aspx",
        access_method="Web service with an application key (APPID) from a free account on data.goteborg.se",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        licence="Göteborgs Stad: \"Göteborgs Stads öppna data är fritt att använda, utan avgifter eller licenser\" (goteborg.se/psidata)",
        commercial_use=CommercialUse.UNKNOWN,
        language="sv",
        notes=(
            "Permits to start works in Gothenburg's streets, listed on data.goteborg.se on 4 November "
            "2026; same key and terms as the city's traffic impact service. Whether it carries "
            "locations and periods is seen only with a key. Not connected."
        ),
    ),
    _researched(
        source_id="se-stockholm-street-works",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="SE", region="Stockholm", city="sweden",
        source_name="Stockholm Trafikkontoret street works (Schakt) and traffic management plans",
        organization="Stockholms stad, Trafikkontoret",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://openstreetgs.stockholm.se/Home/Data",
        access_method="Trafikkontoret's WMS/WFS and OGC API; the two layers are not published",
        integration_status=S.BLOCKED,
        language="sv",
        notes=(
            "On 4 November 2026 Trafikkontoret's open-data page lists 'Gatuarbete - Schakt' and "
            "'Gatuarbete - Trafikanordningsplan' as 'ej publicerad i avvaktan på ny leverantör' (not "
            "published, awaiting a new supplier). Check again later."
        ),
    ),
    # --- Norway: the DATEX server needs an account (the same data is open as a WFS) ----
    _researched(
        source_id="no-vegvesen-datex-server",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="NO", region="National", city="norway",
        source_name="Statens vegvesen DATEX II server (situations, full pull)",
        organization="Statens vegvesen (Norwegian Public Roads Administration)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://www.vegvesen.no/fag/teknologi/apne-data/et-utvalg-apne-data/hva-er-datex/bestille-tilgang-til-datex/",
        endpoint="https://datex-server-get-v3-1.atlas.vegvesen.no/datexapi/GetSituation/pullsnapshotdata",
        access_method="DATEX II 3.1 pull (SOAP/REST) with a username and password; HTTP 401 without",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        licence="NLOD (\"Informasjon i DATEX-format fra Statens vegvesen er gjort tilgjengelig under Norsk lisens for offentlige data\")",
        attribution="Statens vegvesen",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        language="no",
        notes=(
            "Not needed: the same situations are served openly as a WFS and are connected as "
            "norway-vegvesen-datex-situations. An account is asked for on vegvesen.no (organisation, "
            "organisation number, name, e-mail, purpose); its conditions: credit Statens vegvesen, "
            "do not translate Norwegian messages, keep the credentials confidential."
        ),
    ),
    # --- Denmark: the national access point needs an account and a token ---------------
    _researched(
        source_id="dk-vejdirektoratet-roadworks-planned-events",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="DK", region="National", city="denmark",
        source_name="Vejdirektoratet road works and planned events (DU-portal 1208 snapshot, 1209 changes)",
        organization="Vejdirektoratet (Danish Road Directorate)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://nap.vd.dk/",
        endpoint="https://distribution.dataudveksler.app.vd.dk/api/",
        access_method="DATEX II download with a bearer token from Vejdirektoratet's login (idp.vejdirektoratet.dk) and a subscription",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        licence="CC BY 4.0 (dataset 1208 listing, 16 October 2026; Open Data DK entry 'Dataudveksleren': CC-BY-4.0)",
        attribution="Vejdirektoratet",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        language="da",
        notes=(
            "Denmark's national road works and planned events, DATEX II, refreshed every 10 minutes "
            "(listing). The distribution service answered HTTP 401 'Bearer' without a token on "
            "4 November 2026. A profile is made on the DU-portal and the dataset subscribed to (a 2024 "
            "ITS Danmark slide, seen only in search results, says the login is MitID). Not connected."
        ),
    ),
    _researched(
        source_id="dk-vejdirektoratet-traffic-messages",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="DK", region="National", city="denmark",
        source_name="Vejdirektoratet traffic messages (DU-portal 222)",
        organization="Vejdirektoratet (Danish Road Directorate)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://nap.vd.dk/",
        endpoint="https://distribution.dataudveksler.app.vd.dk/api/",
        access_method="DATEX II download with a bearer token and a subscription",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        language="da",
        notes=(
            "Accidents, closures and other traffic messages on Danish state roads, in the same portal "
            "and behind the same token as dataset 1208. Its licence was not read without an account. "
            "Not connected."
        ),
    ),
    _researched(
        source_id="dk-copenhagen-roadworks-du",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="DK", region="Hovedstaden", city="copenhagen",
        source_name="Copenhagen roadworks in the Danish access point (DU-portal 1243)",
        organization="Københavns Kommune, via Vejdirektoratet's DU-portal",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://nap.vd.dk/",
        access_method="Download with a bearer token and a subscription",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        language="da",
        notes=(
            "Copenhagen's roadworks as published to the national access point; licence not read. The "
            "city's own excavation permits are connected without a key "
            "(copenhagen-excavation-permits). Not connected."
        ),
    ),
    # --- Denmark: open, but not built ---------------------------------------------------
    _researched(
        source_id="dk-copenhagen-road-use-permits",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="DK", region="Hovedstaden", city="copenhagen",
        source_name="Copenhagen use of road permits (råden over vej, with events)",
        organization="Københavns Kommune",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://www.opendata.dk/city-of-copenhagen/raden-over-vej-med-historik",
        endpoint="https://wfs-kbhkort.kk.dk/k101/ows",
        access_method="WFS GeoJSON, layer raaden_over_vej_events_anonym_aktuelt; no key",
        integration_status=S.VALIDATED,
        terms_status=TermsStatus.PERMITS_TESTING,
        cost_category=CostCategory.FREE_PUBLIC,
        licence="CC BY 4.0 (Open Data DK catalogue entry)",
        attribution="Københavns Kommune",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        language="da",
        notes=(
            "8,733 shapes on 4 November 2026: outdoor seating 2,818, temporary road use (scaffolding, "
            "containers, site huts) 2,859, excavation 2,390, street trading 355, events 146, filming 97. "
            "97 shapes are flagged closed to car traffic (veje_spaerret_for_biltrafik). Mostly not road "
            "events and its excavations repeat the connected permits; a follow-up could take its "
            "closures and events only. Not connected."
        ),
    ),
    _researched(
        source_id="dk-aarhus-excavation-permits",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="DK", region="Midtjylland", city="denmark",
        source_name="Aarhus excavation permits (gravetilladelser)",
        organization="Aarhus Kommune",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://www.opendata.dk/city-of-aarhus/gravetilladelser2",
        endpoint="https://mida.carto.com/api/v2/sql",
        access_method="CARTO SQL API (GeoJSON); no key",
        integration_status=S.NOT_USABLE,
        licence="CC BY 4.0 (Open Data DK catalogue entry)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        language="da",
        notes=(
            "The table behind the dataset stopped in 2018: on 4 November 2026 its newest start is "
            "29 July 2018 and its last update 1 May 2018 (881 excavation and 205 equipment permits). "
            "It also holds names and phone numbers of contact persons. Not usable."
        ),
    ),
    # --- Estonia ------------------------------------------------------------------------
    _researched(
        source_id="ee-tark-tee-datex2",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="EE", region="National", city="estonia",
        source_name="Tark Tee DATEX II gateway (traffic restrictions, SRTI)",
        organization="Transpordiamet (Estonian Transport Administration)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://www.tarktee.ee/en/datex",
        endpoint="https://www.tarktee.ee/api/v1/datex/",
        access_method="DATEX II 2.3 'restrictions' and 3.6 SRTI services; API key after staff review",
        integration_status=S.REQUIRES_ACCESS,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.UNKNOWN,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        language="et",
        notes=(
            "Registration form at tarktee.ee/en/datex-registration (establishment, optional registry "
            "code, name, e-mail, purpose); the key 'will only become valid once an employee of the "
            "Transport Administration has reviewed your registration'. Terms (tarktee.ee/en/terms) "
            "require a credit or link to the Service and the Administrator and say nothing on "
            "commercial use; the site calls the data 'for free use'. On 5 November 2026 the Estonian "
            "open data portal listed the dataset (liikluspiirangute-andmed) with licence CC BY. "
            "Not connected."
        ),
    ),
    _researched(
        source_id="tartu-traffic-restrictions",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="EE", region="Tartu", city="estonia",
        source_name="Tartu traffic restrictions and closures",
        organization="Tartu Linnavalitsus",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://liikluspiirangud.tartu.ee/",
        endpoint="https://gis.tartulv.ee/arcgis/rest/services/Sulgemised/PI_liikluspiirangud_avaandmed/FeatureServer",
        access_method="ArcGIS feature service (JSON; L-EST97, served as WGS 84 with outSR=4326); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.UNKNOWN,
        cost_category=CostCategory.FREE_PUBLIC,
        provides_geometry=True,
        provides_segments=True,
        language="et",
        notes=(
            "On 4 November 2026: 153 closed-road lines (layer 4) and 124 closure stages with start "
            "and end (table 7: 76 in force, 48 upcoming). The open-data hub lists the layer with "
            "licence 'none'; no terms found. Stages name a contractor's contact person, phone and "
            "e-mail (to be dropped). Ask gis@tartulv.ee for an open licence. Not connected."
        ),
    ),
    # --- Latvia -------------------------------------------------------------------------
    _researched(
        source_id="lv-nap-road-situations",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="LV", region="National", city="latvia",
        source_name="Latvian NAP road works, closures and incidents (DATEX II 3.4)",
        organization='VSIA "Latvijas Valsts ceļi" (National Access Point operator)',
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://transportdata.gov.lv/card/35fa5c41-90ce-4b74-a4a3-08216d470134",
        access_method="NAP REST API or MQTT after free registration; DATEX II 3.4 SituationPublication",
        integration_status=S.REQUIRES_ACCESS,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC0 1.0 (NAP Terms of Use, section 4, effective 6 January 2026)",
        attribution="Optional: 'Source: transportdata.gov.lv – National Access Point for Transport Sector Information'",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        language="lv",
        notes=(
            "Datasets 'Road works', 'Road closures', 'Lane closures', 'Short term road works', "
            "'Accidents and incidents' (LVC, state roads). Terms: 'API access require[s] user "
            "registration'; the road-works metadata says Private visibility, Push, georeferencing "
            "OpenLR (coordinate system WGS84): check after access whether points are given. The "
            "August 2024 sample files (read 5 November 2026) carry WGS84 points and point chains in "
            "their OpenLR fields (one sample with latitude and longitude swapped); an account needs "
            "only an e-mail (Cabinet Regulation No. 188, point 8). Not connected."
        ),
    ),
    # --- Poland -------------------------------------------------------------------------
    _researched(
        source_id="pl-gddkia-kpd-datex2",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="National", city="poland",
        source_name="GDDKiA National Access Point (KPD) DATEX II",
        organization="Generalna Dyrekcja Dróg Krajowych i Autostrad (GDDKiA)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://kpd.gddkia.gov.pl/",
        access_method="DATEX II 3.4 over the KPD API; registration, then test and production client certificates",
        integration_status=S.REQUIRES_ACCESS,
        terms_status=TermsStatus.NOT_REVIEWED,
        commercial_use=CommercialUse.UNKNOWN,
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        language="pl",
        notes=(
            "Registration form e-mailed to kpd@gddkia.gov.pl (or posted to GDDKiA, ul. Wronia 53, "
            "Warszawa): first the organisation as data recipient, then a user 'z dostępem do API', "
            "who receives a test certificate, passes a message-exchange test, then the production "
            "certificate. The regulamin (kpd.gov.pl/regulamin) did not resolve on 4 November 2026. "
            "Not connected."
        ),
    ),
    _researched(
        source_id="pl-gddkia-utrudnienia-xml",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="National", city="poland",
        source_name="GDDKiA road obstructions XML (utrdane.xml)",
        organization="Generalna Dyrekcja Dróg Krajowych i Autostrad (GDDKiA)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://dane.gov.pl/pl/dataset/2752,utrudnienia-na-drogach",
        endpoint="https://www.archiwum.gddkia.gov.pl/dane/zima_html/utrdane.xml",
        access_method="Public XML file; no key (host unreachable from REI's machine on 4 November 2026)",
        integration_status=S.DISCOVERED,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC0 1.0 (dane.gov.pl dataset 2752)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pl",
        notes=(
            "dane.gov.pl lists GDDKiA's current obstructions on national roads as this XML, CC0 1.0, "
            "resource dated 23 May 2022. Two connection timeouts on 4 November 2026 (and on "
            "www.gddkia.gov.pl): whether it is still current and located is unverified. Not connected."
        ),
    ),
    _researched(
        source_id="warsaw-traffic-disruptions",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="PL", region="Mazowieckie", city="poland",
        source_name="Warsaw traffic disruptions (Utrudnienia w ruchu drogowym)",
        organization="Urząd m.st. Warszawy",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://dane.um.warszawa.pl/pl/catalogue/f49d088a-00d3-4d5e-8aaf-1bc7092c706c",
        access_method="JSON file on Otwarte dane Warszawy (CKAN), daily; host unreachable on 4 November 2026",
        integration_status=S.DISCOVERED,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (dane.gov.pl dataset 39523, harvested from dane.um.warszawa.pl)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pl",
        notes=(
            "Listed on dane.gov.pl (CC BY 4.0, JSON, updated daily, last harvest 2 September 2026). "
            "dane.um.warszawa.pl timed out from REI's machine and refused a second network on "
            "4 November 2026, so its records (coordinates, times) were not seen. Not connected."
        ),
    ),
    # --- Ireland ------------------------------------------------------------------------
    _researched(
        source_id="ie-tii-traffic",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IE", region="National", city="ireland",
        source_name="TII Traffic (national roads events)",
        organization="Transport Infrastructure Ireland (TII)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://traffic.tii.ie/",
        access_method="Single-page map behind Google reCAPTCHA; no published API or feed",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.UNKNOWN,
        notes=(
            "Roadworks and incidents on national roads. No documented feed or reuse licence; the "
            "older NRA DATEX II service needed a username and password. data.tii.ie (CC BY 4.0) has "
            "no events. Ask opendata@tii.ie for DATEX II access and terms. Not connected."
        ),
    ),
    _researched(
        source_id="dublin-city-road-closures",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IE", region="Dublin", city="ireland",
        source_name="Dublin City Council current road closures",
        organization="Dublin City Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://www.dublincity.ie/travel-and-transport/read-latest-traffic-news/current-road-closures",
        access_method="HTML page with RDFa latitude/longitude and stated date-time ranges; no feed",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=True,
        notes=(
            "4 closures on 4 November 2026, each a point with start and end. Site terms: PSI posted "
            "on the site 'may be downloaded subject to' the PSI Licence (CC BY 4.0, Circular 12/2016), "
            "but 'All rights to design, text, graphics and other material on this website are the "
            "copyright of Dublin City Council'. Ask DCC to confirm reuse of this list. Not connected."
        ),
    ),
    # --- Brazil -------------------------------------------------------------------------
    SourceDefinition(
        source_id="rio-cor-ocorrencias",
        source_name="Rio de Janeiro COR occurrences (Comando system)",
        organization="Prefeitura do Rio de Janeiro: Centro de Operações Rio (COR), published by the Escritório de Dados",
        authority_type="TRAFFIC_MANAGEMENT_CENTRE",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country="BR", region="Rio de Janeiro", city="brazil",
        source_url="https://www.data.rio/documents/4b21231ce02243e99b5f080b8a0ff821",
        access_method=(
            "BigQuery table datario.adm_cor_comando.ocorrencias, read with a Google Cloud project "
            "(billing project id); the API at api.dados.rio/v1 reset the connection from REI's "
            "network on 4 November 2026; the CSV download page says the data is not available for download"
        ),
        integration_status=S.REQUIRES_ACCESS,
        language="pt",
        cost_category=CostCategory.REGISTRATION_REQUIRED,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        licence=(
            "CC BY-ND 3.0 Unported, as the catalogue item states "
            "(https://creativecommons.org/licenses/by-nd/3.0/deed.pt_BR): commercial use allowed, "
            "adapted material may not be distributed"
        ),
        attribution="COR (the item's credits)",
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=True,
        notes=(
            "Occurrences the COR opens and follows since 2015 (potholes, standing water, broken-down "
            "vehicles and the like), updated daily: WGS 84 latitude and longitude, data_inicio, "
            "data_fim (empty while open), status ABERTO/FECHADO, gravidade, prazo, tipo, bairro, "
            "descricao. Not fetched: BigQuery needs a Google Cloud project, the API host was "
            "unreachable from REI's network, and the licence forbids sharing adapted material, which "
            "REI's normalised events may be; ask the Escritório de Dados whether REI's use is "
            "allowed or whether the data can be offered under CC BY. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="cet-sp-interdicoes",
        source_name="CET São Paulo road closure notices",
        organization="Companhia de Engenharia de Tráfego (CET), Prefeitura de São Paulo",
        authority_type="MUNICIPAL_TRANSPORT_AUTHORITY",
        source_tier=1,
        source_type=SourceType.HTML,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country="BR", region="São Paulo", city="brazil",
        source_url="https://www.cetsp.com.br/",
        access_method="HTML news pages (/noticias/yyyy/mm/dd/<title>.aspx); no feed, no API, no coordinates",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        language="pt",
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=False,
        notes=(
            "CET announces each street, tunnel or lane closure (events, works, tree pruning, "
            "cleaning) as a news page; on 4 November 2026 the home page linked four closure notices "
            "dated 3 November. Text only, no coordinates; the site publishes privacy policies but no "
            "terms for reusing its content (robots.txt answers 404). Ask CET for permission and for "
            "a machine-readable list. Not connected."
        ),
    ),
    # --- Malaysia -----------------------------------------------------------------------
    SourceDefinition(
        source_id="llm-highway-incident-reports",
        source_name="LLM highway disaster and closure reports",
        organization="Lembaga Lebuhraya Malaysia (Malaysian Highway Authority)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL,
        country="MY", region="National", city="malaysia",
        source_url="https://gis02.llm.gov.my/geosmpt/apps/webappviewer/index.html?id=ca1c4ab5d0c34e36a1dd556d9aedccf6",
        endpoint="https://gis02.llm.gov.my/llmsmpt/rest/services/Hosted/survey123_6394fa57dfe34fc28d78d6db7bf41ad5/FeatureServer/0/query",
        access_method="ArcGIS feature service (WGS 84 points) of LLM's public highway map 'Peta Lebuh Raya Malaysia'; no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        language="ms",
        cost_category=CostCategory.FREE_PUBLIC,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        licence=(
            "None on the layer (licenseInfo empty). Not among the data sets LLM lists as open data "
            "under the Terms of Use Government Open Data 1.0; the site footer says "
            "'Hak Cipta Terpelihara © 2026 Lembaga Lebuhraya Malaysia'"
        ),
        commercial_use=CommercialUse.UNKNOWN,
        provides_geometry=True,
        evidence_retention="Each report as received, less the reporting officer and editor user names.",
        notes=(
            "Floods, slope failures, sinkholes and closures on the toll expressways, reported by LLM "
            "(Survey123 layer 'Bencana'): expressway code, direction, km from/to, type, report time, "
            "free-text status and Aktif/Tidak_Aktif. On 4 November 2026: 89 reports, 3 active "
            "(flash floods closing NKVE, GCE and the Shah Alam toll plaza that morning). Each names "
            "the reporting officer (pegawai_pelapor) and editors: personal data, not to be kept. The "
            "same map has the mandatory-exit diversions layer (PWS/ManExit, 61 lines, none active) "
            "and an events layer (10 events of 2018-2022 with applicants' names, e-mails and phones). "
            "Ask LLM (korporat@llm.gov.my) for permission to reuse the layers. Not connected."
        ),
    ),
    SourceDefinition(
        source_id="plus-highway-incidents",
        source_name="PLUS expressway incidents",
        organization="PLUS Malaysia Berhad",
        authority_type="TRANSPORT_OPERATOR",
        source_tier=2,
        source_type=SourceType.API,
        source_class=SourceClass.PARTNER,
        country="MY", region="National", city="malaysia",
        source_url="https://www.plus.com.my/?Itemid=239",
        endpoint="https://plusprodaio.azurewebsites.net/poi/incidents",
        access_method=(
            "The API behind the PLUS website's traffic page; HTTP 401 without credentials; "
            "no public developer programme found"
        ),
        integration_status=S.REQUIRES_ACCESS,
        language="en",
        cost_category=CostCategory.UNKNOWN,
        terms_status=TermsStatus.REVIEW_REQUIRED,
        licence="None published; the site footer says 'Copyright © 2024 PLUS Malaysia Berhad'",
        commercial_use=CommercialUse.UNKNOWN,
        notes=(
            "The concessionaire of the North-South Expressway and other toll roads. Its traffic page "
            "calls an incidents API that answered HTTP 401 on 4 November 2026; lane closures and "
            "diversions are otherwise published as PDF media statements and on X (@plustrafik). "
            "Access would need an agreement with PLUS. Not connected."
        ),
    ),
)
