# Worldwide source research, 5 November 2026

The user, 5 November 2026: "check for other sources i need atleast 100 active
working sources from all over the world".

Production on 5 November (read-only query of the `sources` table): 219 sources
registered, **55 working**, 9 failing (8 Serper searches "Not enough credits",
Basque Country timeouts), 3 connected but not scheduled (DGT Spain, Finland,
Roads ACT), the rest awaiting permission, needing a key, blocked, removed or
researched only.

Three researchers searched regions the earlier research had not reached, skipping
everything already recorded in `docs/data-sources/` and `backend/connectors/`.
Every row below was fetched live on 5 November 2026 with REI's User-Agent,
robots.txt read first. Verdicts follow REI's rules: **READY** = keyless, no bot
wall, robots allows, an explicit licence permitting commercial use, current or
upcoming events with locations and dates. Terms silent = **ASK_PERMISSION**.

The user chose to build the 23 strong READY sources (marked ✔) and to get the list
of free API keys (`free-api-keys-2026-11-05.md`).

## READY

| | Country / area | Source | Endpoint | Current + upcoming (5 Nov) | Licence |
|---|---|---|---|---|---|
| ✔ | DE (Baden-Württemberg) | MobiData BW roadworks (NVBW) | `api.mobidata-bw.de/datasets/traffic/roadworks/roadworks_geojson.json` | 697 + 196 | dl-de/by-2-0 |
| ✔ | DE (Karlsruhe region, Alsace) | TechnologieRegion Karlsruhe roadworks (WFS `baustellen_aktuell`, `baustellen_vorschau`) | `mobil.trk.de/geoserver/TBA/ows` | 845 + 135 (≤30 d) | CC BY 4.0 |
| ✔ | DE (München) | Landeshauptstadt München roadworks, next 4 weeks (WFS) | `geoportal.muenchen.de/geoserver/mor_wfs/ows` | ~1,130 carriageway works | dl-de/by-2-0 |
| ✔ | AT (Salzburg) | Stadt Salzburg roadworks (WFS) | `data.stadt-salzburg.at/geodaten/wfs` | 85 + 3 | CC BY 3.0 AT |
| ✔ | CH (Canton of Zürich) | Tiefbauamt, works on cantonal roads (WFS) | `maps.zh.ch/wfs/TbaBaustellenZHWFS` | 52 + 3 | opendata.swiss "Freie Nutzung" |
| ✔ | CH (Zürich city) | Tiefbauamt, current projects on public ground (WFS) | `ogd.stadt-zuerich.ch/wfs/geoportal/…` | 123 + 10 | "Freie Nutzung" |
| ✔ | CH (Schwyz) | Canton of Schwyz roadworks (WFS, GML, LV95) | `map.geo.sz.ch/mapserv_proxy` | 26 | "Freie Nutzung", credit required |
| ✔ | CH (Geneva) | SITG Infomobilité major works (ArcGIS) | `vector.sitg.ge.ch/arcgis/rest/services/INFOMOB_CHANTIER_POINT` | 63 + 1 | "Freie Nutzung" |
| ✔ | IT (South Tyrol) | Provincia di Bolzano traffic centre: works/closures + current situation (WFS) | `geoservices2.civis.bz.it/geoserver/pczs-Traffic/ows` | 107 + 31 | CC0 1.0 |
| ✔ | LU | CITA current and future works (DATEX II 2.2) | `cita.lu/info_trafic/datex/chantier{Actuel,Futur}Datex.xml` | 179 + 128 | CC0 (data.public.lu) |
| ✔ | GB (England) | National Highways planned roadworks (weekly XML, BNG) | `s3.eu-west-2.amazonaws.com/webdata.nationalhighways.co.uk/ha-roadworks/…` | 533 + 895 | OGL |
| ✔ | FR (Côtes d'Armor) | Department traffic orders for works (Data Fair) | `datarmor.cotesdarmor.fr/data-fair/api/v1/datasets/cd22arreteschantiers` | 114 + 53 | Licence Ouverte |
| ✔ | FR (Brest) | Brest métropole temporary traffic orders (ArcGIS) | `geo.brest-metropole.fr/arcgis/rest/services/public/GPB_DEP/MapServer/1718004` | 2 | Licence Ouverte 2.0 |
| ✔ | US (DC) | DDOT construction permits, last 30 days (ArcGIS) | `maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/12` | ~1,432 | CC BY 4.0 |
| ✔ | US (Louisville) | Louisville Metro ROW construction permits (ArcGIS) | `services1.arcgis.com/79kfd2K6fskCAkyg/…/Louisville_KY_ROW_Construction_Permits_new` | 243 + 3 | PDDL |
| ✔ | US (Cambridge MA) | Excavation permits (Socrata `nuxx-d95m`) | `data.cambridgema.gov/resource/nuxx-d95m.json` | 91 | PDDL |
| ✔ | CA (Québec City) | Entraves en temps réel (WZDx 3.1) | `quebec.gewi.com/wzdx4waze/pull` | 266 + 89 | CC BY 4.0 |
| ✔ | CA (Longueuil) | Info-travaux et entraves (ArcGIS) | `geomatique.longueuil.quebec/public/rest/services/Communication/Gestion_des_entraves_Diffusion` | 24 + 2 | CC BY 4.0 |
| ✔ | CA (Saguenay) | Chantiers 511 (GeoJSON) | `donneesquebec.ca/…/sag_chantiers511.geojson` | 13 + 2 | CC BY 4.0 |
| ✔ | CA (Region of Waterloo) | Road closures current and future (ArcGIS MapServer 24/25) | `utility.arcgis.com/usrsvcs/servers/…/OpenData/MapServer/24,25` | 62 + 25 | Region of Waterloo Open Data Licence v2.0 (commercial use) |
| ✔ | CA (Burlington) | Road closures (ArcGIS) | `services1.arcgis.com/xbWF6o8qyXoMFa8L/…/Road_Closures_Open_Date_View/FeatureServer/1` | 6 | CC BY 4.0 |
| ✔ | TW (Taichung) | Same-day road excavation (data.gov.tw 105203) | `newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=d5adb71a-…` | 1,350 permits valid | OGDL v1.0 |
| ✔ | NZ (New Plymouth) | NPDC Corridor Access Requests (ArcGIS layers 2–4) | `services2.arcgis.com/JthOmqz8HxPqljUO/…/OpenData_Infrastructure_Transport` | 269 CARs | CC BY 4.0 |
| | US (Hawaii) | HDOT WZDx (Blyncsy) | `ai.blyncsy.io/wzdx/hidot/feed` | 133 | CC0; dates generated (detection + 7 days, unverified) |
| | DE (Baden-Württemberg) | LMS BW traffic messages (DATEX II 2.0) | `api.mobidata-bw.de/datasets/traffic/incidents/incidents_lmsbw.datex2.xml` | 42 situations | dl-de/by-2-0; no end times |
| | NZ (Tararua) | RAMM road status | `services-ap1.arcgis.com/ry1jWJjaLhqVCFK6/…/tdc_ramm_road_status` | 12 | CC BY; no end dates |
| | TW (New Taipei) | Real-time works (data.gov.tw 177913) | `data.ntpc.gov.tw/api/datasets/e4014a7a-…/csv/file` | 40 | OGDL; an upgrade of the connected New Taipei feed |
| | FR (Montpellier) | Temporary traffic orders | `data.montpellier3m.fr/…/MMM_MMM_ArretesTemp.json` | 351 + 92 | **ODbL (share-alike)**: the user's decision |

## NEEDS_FREE_KEY

Korea MOLIT 재난상황정보 (data.go.kr 15160258, "이용허락범위 제한 없음"). See
`free-api-keys-2026-11-05.md` for the full list with earlier finds.

## ASK_PERMISSION (terms silent, blank or disclaimer only)

| Country / area | Source | Current records | Why |
|---|---|---|---|
| US (Nashville) | NDOT Active Right-of-Way Permits (ArcGIS) | 2,207 | Licence field points to Executive Order FO018 (403) |
| US (Dallas) | ROW Permits – Lines (Socrata `xd3q-ipis`) | 2,069 | `license: null` |
| US (Nebraska, Missouri) | 511 events copies by Iowa DOT (ArcGIS) | 200 / 1,162 | CC BY 4.0 plus "Additional Terms" (Cloudflare-blocked) |
| US | Raleigh, Madison, Spokane, IDOT, Detroit, Houston, SAWS, Fresno, Austin events, Mesa | — | Disclaimers only, blank licence, or "See Terms of Use" |
| AU (Melbourne) | City of Melbourne Disruptive Road Closures | 16 | `licenseInfo` blank |
| AU (Moreton Bay) | MBRC Road Works (Open) | 15 | Blank |
| NZ | Selwyn (2), Hastings, Manawatū, Queenstown Lakes | 2–188 | Blank |
| AR | Vialidad Nacional "Estado de rutas" | — | Site CC BY 4.0, but data via the site's own Google Sheets key; ask for a feed |
| AE | Dubai Pulse traffic incidents | — | "License not specified" / "Request Permission"; unreachable |
| DE (Herne) | Stadt Herne roadworks (WFS) | 22 | "Keine Lizenz angegeben" |
| FR (Drôme) | Works feed for Waze | — | `notspecified`; unreachable |

## REJECT

| Country / area | Source | Reason |
|---|---|---|
| US (Pittsburgh) | WPRDC DOMI Street Closures | robots disallows `/api/` and `/datastore/dump/` (its comments say apps may ignore them: the user's call) |
| US / CA | Boulder, Cambridge block parties, LA BOE, Montgomery Co MD, Santa Clara Co, NOLA, Dallas ROW restrictions, Windsor, Novi, Honolulu, PurposeBuilt CWZ | No geometry, no work dates, not events, prohibitive terms or one record |
| TW | Taoyuan (WAF), Hsinchu (yearly statistics), Taipei messages (no location) | as stated |
| JP | Wakayama (403) | blocked |
| TH | data.go.th (403) | blocked |
| AU | Mitcham, Palmerston, Scenic Rim | asset inventories, not events |
| FR | La Rochelle (bot wall); Sarthe, Aude, CapAtlantique, CARENE (robots `Disallow: /api/`) | as stated |
| IT | Bologna (robots); Lombardy Pavia/Cremona/Rho (stale 2018–2024) | as stated |
| LU | Esch-sur-Alzette RSS | no locations |
| DE | Düsseldorf (login), Heidelberg (404) | as stated |
| AT | Tirol (per-order documents, not a feed) | as stated |

## Unreachable from REI's network (retry from production)

New Mexico WZDx (503), CDMX open data, Tainan, Taiwan Police Broadcasting,
Highway Bureau (DNS), Kaohsiung, Hong Kong HyD excavation permits, Clutha DC,
Bonn, Münster, Meuse/GéoGrand Est (certificate), Frankfurt (certificate), Helsinki,
Valencia, Zaragoza, Warsaw, NRW CKAN.

## Nothing usable found

Mexico beyond CDMX, Japan beyond Tokushima, Brisbane, Sunshine Coast, Montevideo,
Peru, Colombia, İzmir and datos.gob.ar (robots `/api/`), Victoria's portal (robots
`/api/`), Porto, Slovenia, Czechia, Budapest, Iceland, Dresden, Leipzig, Vilnius.
Wallonia's road-works service is reserved for the region's own applications.

## Requests

Request logs and samples are in the session scratchpad (`research-americas/`,
`research-europe/`, `research-world/`). Three rule slips were reported and not
repeated: one request to `opendata.muenchen.de/api/…` (robots disallow, misread by
Python's parser), one to `datos.gob.ar/api/…` (disallowed, answered 502), and two
redirects that landed on disallowed paths (responses discarded).
