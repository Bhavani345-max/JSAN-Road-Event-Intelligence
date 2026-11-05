"""Poland, Ireland, Brazil and Malaysia: sources found on 5 November 2026, NOT connected.

The second search for the six countries with no event (Brazil, Estonia, Ireland,
Latvia, Malaysia, Poland) looked only where the 4 November search had not
(discovered_2026_11_04.py). Each source below is inactive and has no connector:
its data is good but its terms do not yet let REI reuse it (permission to ask),
it needs a key, or it is too thin to connect. Connected that day: Tallinn
(connectors/official/tallinn_opinfo.py). The full record, with the requests
made, is docs/data-sources/zero-event-countries-sources-2026-11-05.md; decision 0058.
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
    return SourceDefinition(
        **{
            "source_tier": 1,
            "source_type": SourceType.API,
            "language": "en",
            "terms_status": TermsStatus.REVIEW_REQUIRED,
            "commercial_use": CommercialUse.UNKNOWN,
            **fields,
        }
    )


DISCOVERED_2026_11_05: tuple[SourceDefinition, ...] = (
    # --- Ireland ------------------------------------------------------------------------
    _researched(
        source_id="ie-meath-road-notices",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="IE", region="Meath", city="ireland",
        source_name="Meath County Council road notices",
        organization="Meath County Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://www.arcgis.com/home/item.html?id=fd13914e2a1343f784d925f35229e56c",
        endpoint="https://services-eu1.arcgis.com/33tCl0taHHdVAN9O/arcgis/rest/services/Road_Notices_County_View/FeatureServer",
        access_method="ArcGIS feature service (layer 7 notices as points, layer 8 closure and diversion lines); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        provides_geometry=True,
        provides_segments=True,
        licence=(
            "None on the service. meath.ie allows reuse 'subject to the latest Public Sector "
            "Information licence' but also says 'Reproduction … is prohibited save with the prior "
            "written authorisation'"
        ),
        notes=(
            "On 5 November 2026: 721 road notices, 6 in force and 7 upcoming, with points, start and "
            "end dates and 28 closure and diversion lines; most closures appear twice (proposal and "
            "order). Ask gisoff@meathcoco.ie (copy customerservice@meathcoco.ie) for written permission "
            "or a CC BY 4.0 statement on the service. Not connected."
        ),
    ),
    _researched(
        source_id="ie-cork-city-road-closure-alerts",
        source_class=SourceClass.GOVERNMENT_OPEN_DATA, country="IE", region="Cork", city="ireland",
        source_name="Cork City Council road closure alerts",
        organization="Cork City Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://www.arcgis.com/home/item.html?id=9e031281759a4252890dae12ebd87990",
        endpoint="https://services-eu1.arcgis.com/f0ZQOHXBIeLonX0V/arcgis/rest/services/RoadClosureAlerts/FeatureServer/0",
        access_method="ArcGIS feature service (points; end date as text YYYYMMDD); no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        provides_geometry=True,
        licence=(
            "None on the service. corkcity.ie forbids reproduction 'save with the prior written "
            "authorisation'; its reuse policy excludes 'Other maps of any kind'"
        ),
        notes=(
            "On 5 November 2026: 59 closure points, 32 in force and 1 upcoming, updated daily. Ask "
            "foi@corkcity.ie, for the re-use of public sector information, for permission or for the "
            "layer on data.corkcity.ie under CC BY 4.0. Not connected."
        ),
    ),
    _researched(
        source_id="ie-limerick-road-notices",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IE", region="Limerick", city="ireland",
        source_name="Limerick City and County Council road notices map",
        organization="Limerick City and County Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://www.limerick.ie/council/newsroom/road-notices/map",
        access_method="Web map page with markers; dates only in the text; no feed",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        licence="None stated beyond '© 2026 Limerick City and County Council'",
        notes=(
            "On 5 November 2026: 40 markers with coordinates; periods are written in each notice's "
            "text. Ask web.content@limerick.ie whether the map may be reused and whether a feed "
            "exists. Not connected."
        ),
    ),
    _researched(
        source_id="ie-dlr-traffic-news",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="IE", region="Dún Laoghaire-Rathdown", city="ireland",
        source_name="Dún Laoghaire-Rathdown traffic news (road closures)",
        organization="Dún Laoghaire-Rathdown County Council",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://www.dlrcoco.ie/traffic-management/traffic-news",
        access_method="Web page and a weekly PDF; text only, no coordinates; no feed",
        integration_status=S.DISCOVERED,
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Creative Commons Attribution (its Smart Dublin dataset entry, which points at this page)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        cost_category=CostCategory.FREE_PUBLIC,
        notes=(
            "The one Irish source of 5 November 2026 whose licence already permits reuse, but thin: "
            "3 closures in force and 2 proposed, written as text with road names and no coordinates "
            "(locating them needs an Irish place list). The weekly PDF was not read. Not connected."
        ),
    ),
    # --- Poland -------------------------------------------------------------------------
    _researched(
        source_id="pl-szczecin-zditm-driver-notices",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="Zachodniopomorskie", city="poland",
        source_name="ZDiTM Szczecin notices for drivers (Atom)",
        organization="Zarząd Dróg i Transportu Miejskiego w Szczecinie",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.RSS,
        source_url="https://www.zditm.szczecin.pl/pl/atom/informacje/kierowca",
        access_method="Atom feed; streets and dates in the text, no coordinates; no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pl",
        licence=(
            "The developer page states 'Dane udostępniane są bezpłatnie na licencji CC0 1.0, do "
            "wykorzystania w dowolnym celu' for the data it lists; this feed is listed separately"
        ),
        notes=(
            "On 5 November 2026: 30 entries (9 September to 4 November), about 5 to 8 in force or "
            "coming. Some entries name private persons (to be dropped). Ask zditm@zditm.szczecin.pl "
            "whether the CC0 licence covers this feed. Not connected."
        ),
    ),
    _researched(
        source_id="pl-gdynia-zdiz-road-messages",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="Pomorskie", city="poland",
        source_name="ZDiZ Gdynia current road messages",
        organization="Zarząd Dróg i Zieleni w Gdyni",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_url="https://dane.gov.pl/pl/dataset/41278",
        endpoint="https://api.zdiz.gdynia.pl/ri/rest/messages",
        access_method="REST API; answered HTTP 401 Unauthorized, even for robots.txt",
        integration_status=S.REQUIRES_ACCESS,
        cost_category=CostCategory.UNKNOWN,
        language="pl",
        licence="CC BY 4.0 (dane.gov.pl catalogue entry 41278)",
        notes=(
            "'Aktualne komunikaty drogowe'. The data host refused REI on 5 November 2026 (HTTP 401), "
            "so its records, fields and coordinates are unknown. Ask otwartedane@gdynia.pl whether it "
            "is open or needs a key. Not connected."
        ),
    ),
    _researched(
        source_id="pl-lodz-road-works",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="Łódzkie", city="poland",
        source_name="Łódź road works and closures (lodz.pl/remonty)",
        organization="Urząd Miasta Łodzi",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://lodz.pl/remonty/",
        access_method="Web page; one item per street section; no feed",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pl",
        licence="None stated",
        notes=(
            "On 5 November 2026: 57 items, 22 with exact dates; some out of date. Ask "
            "redakcja_portal@biblioteka.lodz.pl (the publisher) for permission. Not connected."
        ),
    ),
    _researched(
        source_id="pl-krakow-zdmk-works",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="PL", region="Małopolskie", city="poland",
        source_name="Kraków road authority (ZDMK) works list",
        organization="Zarząd Dróg Miasta Krakowa",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://zdmk.krakow.pl/zestawienie-prac-w-miescie/",
        access_method="Web page; dated items in prose by district; no feed",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pl",
        licence="None stated",
        notes=(
            "On 5 November 2026: about 54 dated items with street sections; some ended items are "
            "still listed. Ask sekretariat@zdmk.krakow.pl for permission. Not connected."
        ),
    ),
    # --- Brazil -------------------------------------------------------------------------
    _researched(
        source_id="br-cor-rio-interdicoes",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="BR", region="Rio de Janeiro", city="brazil",
        source_name="COR Rio closures (Interdições) feed",
        organization="Centro de Operações Rio (COR), Prefeitura do Rio de Janeiro",
        authority_type="TRAFFIC_MANAGEMENT_CENTRE",
        source_type=SourceType.RSS,
        source_url="https://cor.rio/category/interdicoes/",
        endpoint="https://cor.rio/category/interdicoes/feed/",
        access_method="RSS feed; tunnels and street sections with times in the text, no coordinates; no key",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pt",
        licence=(
            "Terms (July 2023): 'nenhum material… pode ser copiado, reproduzido, republicado… salvo "
            "mediante o consentimento prévio, por escrito, do COR.rio'"
        ),
        notes=(
            "On 5 November 2026: 10 items (28 October to 4 November), all closures, about 1.4 a day, "
            "posted 3 to 48 hours ahead (night tunnel maintenance, stadium and race traffic schemes). "
            "Ask comunicacao@cor.rio for commercial reuse with credit, together with the COR "
            "occurrences dataset (rio-cor-ocorrencias). Not connected."
        ),
    ),
    _researched(
        source_id="br-dnit-service-alerts",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="BR", region="National", city="brazil",
        source_name="DNIT federal highway service alerts (Alerta de Serviços)",
        organization="Departamento Nacional de Infraestrutura de Transportes (DNIT)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_type=SourceType.HTML,
        source_url="https://www.gov.br/dnit/pt-br/central-de-conteudos/noticias-alerta-de-servicos",
        access_method="News listing on gov.br; road number, km and town in the text; no RSS",
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.FREE_PUBLIC,
        language="pt",
        licence="Creative Commons Atribuição-SemDerivações 3.0 Não Adaptada (CC BY-ND 3.0: no adaptations)",
        notes=(
            "On 5 November 2026: 30 alerts (15 October to 4 November), all federal-highway events, "
            "several in force (BR-470/RS fully blocked on 4 November). CC BY-ND forbids the "
            "adaptation REI makes. Ask imprensa@dnit.gov.br for permission. Not connected."
        ),
    ),
    # --- Malaysia -----------------------------------------------------------------------
    _researched(
        source_id="my-nadma-road-closures",
        source_class=SourceClass.AUTHORITATIVE_OFFICIAL, country="MY", region="National", city="malaysia",
        source_name="NADMA disaster portal road closures (Penutupan Jalan, from JKR)",
        organization="Agensi Pengurusan Bencana Negara (NADMA), with Jabatan Kerja Raya (JKR)",
        authority_type="NATIONAL_ROAD_AUTHORITY",
        source_url="https://portalbencana.nadma.gov.my/map/map_main.php",
        access_method=(
            "Not accessed: the map reads the closures from NADMA's internal API with a login; "
            "no public feed"
        ),
        integration_status=S.TERMS_REVIEW_REQUIRED,
        cost_category=CostCategory.UNKNOWN,
        language="ms",
        licence="'© 2026 Pusat Kawalan Bencana Negara (NDCC). Hak Cipta Terpelihara.'",
        notes=(
            "The portal's road-closure layer gives each closure's coordinates, state, district, road "
            "name, status and update date (field names seen in the map's code on 5 November 2026; "
            "the API was not called). Ask opsroom@nadma.gov.my, copying JKR, for permission and a "
            "public feed. Not connected."
        ),
    ),
)
