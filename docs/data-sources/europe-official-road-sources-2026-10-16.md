# Europe: official road-event sources, 16 October 2026

The user asked for official, machine-readable European sources of road
closures, roadworks, diversions, accidents and incidents, weather road impacts
and traffic-affecting events, each with its own geometry and stated start and
end times. REI is commercial, so each licence had to allow commercial use.

**Method.** Every candidate was fetched live on 16 October 2026, between about
12:20 and 12:46 UTC.
- **User-Agent:** `JSAN-REI/1.0 (road event intelligence research)`.
- **robots.txt first:** each host's robots.txt was read before anything else
  on that host.
- **Request limits:** requests to one host were sequential, at least 2 s apart,
  and never more than 10 per host. The busiest host had 9.
- **What was not done:** no logins, registrations, key sign-ups, CAPTCHAs,
  proxies or browser disguise. No request went to any gdeltproject.org host or
  to a news publisher.
- **Request log:** 260 lines, kept outside the repo at
  `…\scratchpad\eu-scripts\log.tsv`.
- **Scope:** research only. No code was changed.

**How records are counted.** *Current* means started and not yet ended at
fetch time. *Upcoming* means it starts later. *Ended* means its end time has
already passed but it is still in the feed.

**What REI's display rules mean here.** Under the 15 October rules, an event
with no source start or end is shown as *unconfirmed* and hidden. A feed with
no location stays off. So a feed with no end times, or with no geometry, is
worth less to REI than its volume suggests.

**Already connected (not re-researched):**
- TfL (London)
- France Bison Futé (DATEX II)
- France DiaLog
- Grand Lyon disruptive works
- Finland Digitraffic: held, because robots.txt disallows `/api/`

**Samples.** One raw sample for each PERMITTED working source was saved
outside the repo, in
`C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\b9dd17db-5e5d-47c6-ab68-7a67344a5a5d\scratchpad\research\global\europe\`
(referred to below as `europe\`). Every file there was re-parsed and is valid
JSON, XML or CSV.

## Summary table

Ranked within each verdict by usefulness for REI: coverage, then geometry,
then start/end, then volume.

| Country | Source | URL | Format | Auth | Records (16 Oct) | Geometry | Start/end | Licence | Commercial | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NL | NDW current picture (*actueel beeld*) | `opendata.ndw.nu/actueel_beeld.xml.gz` | DATEX II v3 XML, gzip | none | 1,123 situations / 1,367 records | 1,358 of 1,367 records: lines 1,099, points 289 (WGS84) | start all; end on 823 of 1,123 situations | CC0 (NDW site-wide statement) | yes | **PERMITTED** |
| NL | NDW planned roadworks and events | `opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz` | DATEX II v3 XML, gzip | none | 14,553 situations / 62,630 records | lines on 48,630 records, points on 26,931 | both on 14,541 of 14,553 | CC0 | yes | **PERMITTED** |
| GB-SCT | Scottish Road Works Register (SRWR) disruptions export | `downloads.srwr.scot/disruptions-export/api/v1/files` | CSV in zip, daily | none | 22,157 current activities | all: WGS84 point plus British National Grid WKT line/polygon/point | both on all | Open Government Licence v3 | yes | **PERMITTED** |
| BE-VLG | GIPOD planned hindrance (`HINDER`) | `geo.api.vlaanderen.be/GIPOD/ogc/features/collections/HINDER/items` | GeoJSON (OGC API Features) | none | ≥ 10,000 zones (server count cap) | MultiPolygon on all | both on all 1,000 checked | Modellicentie Gratis Hergebruik v1.0 | yes | **PERMITTED** |
| ES | DGT incidents DATEX II 3.7 | `nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml` | DATEX II 3.7 XML | none | 837 situations / 1,101 records | WGS84 on all (point, or from/to points of a linear section) | start all; end 462 | "Creative Commons Attribution" (no version) | yes | **PERMITTED** |
| BE-BRU | Bruxelles Mobilité traffic events | `data-mobility.irisnet.be/datasets/v1/traffic/collections/traffic_events/items/` | GeoJSON (OGC API Features) | none | 233 | point on all | both on all | CC0 | yes | **PERMITTED** |
| DE-HH | Polizei Hamburg traffic messages (current) | `api.hamburg.de/datasets/v1/verkehrsinformation/collections/hauptmeldungen_aktuell/items` | GeoJSON (OGC API Features) | none | 275 | point on all | start 275, end 240 | Datenlizenz Deutschland Namensnennung 2.0 | yes | **PERMITTED** |
| ES-BCN | Barcelona works in public space (*obres*) | `opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search?resource_id=4e6b3bfe-…` | CKAN JSON | none | 1,930 works | WKT polygon or multipolygon on 977 of 1,000 | dates (no times) on both | CC BY 4.0 | yes | **PERMITTED** |
| BE-VLG | Verkeerscentrum Vlaanderen DATEX II v3 | `www.verkeerscentrum.be/uitwisseling/datex2v3` | DATEX II v3 XML | none | 83 situations / 105 records | lines on 89 (Lambert 72), WGS84 points on 16 | end on 43 of 83 | Modellicentie Gratis Hergebruik v1.0 | yes | **PERMITTED** |
| DE-HH | Hamburg roadworks (Bauweiser) | `api.hamburg.de/datasets/v1/baustellen/collections/baustelle/items` | GeoJSON (OGC API Features) | none | 161 | point on all | dates on all | Datenlizenz Deutschland Namensnennung 2.0 | yes | **PERMITTED** |
| AT-W | Vienna roadworks affecting traffic | `data.wien.gv.at/daten/geo` WFS, layers `BAUSTELLENLINOGD` and `BAUSTELLENPKTOGD` | GeoJSON (WFS) | none | 78 | 53 lines, 25 points | dates on all | CC BY 4.0 (portal terms) | yes | **PERMITTED** (licence caveat) |
| ES-MAD | Madrid Informo street incidents | `informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml` | XML | none | 113 (only 10 current or upcoming) | point on all | both on all | CC BY 4.0 | yes | **PERMITTED** |
| GB-WLS | Traffic Wales roadworks RSS | `traffic.wales/feeds/roadworks/rss.xml` | RSS 2.0 + GeoRSS | none | 31 | point on all | on all, in description text | credit "Traffic Wales" | not stated | **PERMITTED** (caveat) |
| LU | CITA DATEX II 3.6 | `cita.lu/info_trafic/datex/situationrecord36` | DATEX II 3.6 XML | none | 14 situations / 19 records | line on all | start only | CC0 | yes | **PERMITTED** (no end times) |
| ES-PV | Euskadi traffic incidences | `api.euskadi.eus/traffic/v1.0/incidences/byDate/2026/10/16` | JSON | none | 194 for the day | point on all | start only | CC BY 4.0 | yes | **PERMITTED** (no end times) |
| GB-NIR | TrafficwatchNI roadworks RSS | `rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml` | RSS 2.0 | none | 1,807 | **none** | in text, parsable on 1,497 | DfI feed terms (commercial allowed) | yes | **PERMITTED** (no geometry) |
| DE | Autobahn GmbH API | `verkehr.autobahn.de/o/autobahn/{road}/services/{roadworks\|closure\|warning}` | JSON | none | A1: 263 roadworks, 29 closures, 18 warnings; A7: 296, 37; national estimate about 3,500–4,500 roadworks | LineString on all | structured start on about 50%; end in German text only | none found | unknown | ASK_PERMISSION |
| LT | Via Lietuva restrictions | `restrictions.eismoinfo.lt/` | JSON | none | 308 | polyline on all | both on all | none found | unknown | ASK_PERMISSION |
| ES-CT | Servei Català de Trànsit (via DGT) | `infocar.dgt.es/datex2/sct/SituationPublication/all/content.xml` | DATEX II 1.0 | none | 230 | point on 198 | start only | "No licence – No contract" | unknown | ASK_PERMISSION |
| DE-BE | Berlin VIZ roadworks and closures | `api.viz.berlin.de/daten/baustellen_sperrungen.json` | GeoJSON | none | 387, frozen since 2 Jul 2025 | GeometryCollection 338, point 49 | from/to as text | not readable (bot wall) | unknown | ASK_PERMISSION (stale) |
| IE | Dublin City current road closures | `dublincity.ie/travel-and-transport/read-latest-traffic-news/current-road-closures` | HTML with RDFa | none | 5 | point on all | both | none read | unknown | ASK_PERMISSION |
| IE | TII traffic events | `traffic.tii.ie` | single-page app, reCAPTCHA | — | — | — | — | — | — | ASK_PERMISSION |
| DK | Vejdirektoratet DU-portal | `nap.vd.dk` | DATEX II | account and token | — | — | — | CC BY 4.0 | yes | NEEDS_KEY |
| NO | Statens vegvesen DATEX | `datex-server-get-v3-1.atlas.vegvesen.no` | DATEX II 3.1 | access request (HTTP 401) | — | — | — | NLOD | yes | NEEDS_KEY |
| SE | Trafikverket API | `api.trafikinfo.trafikverket.se` | JSON/XML | key | — | — | — | CC0 1.0 | yes | NEEDS_KEY |
| GB-ENG | National Highways closures v2.0 | `developer.data.nationalhighways.co.uk` | DATEX II | key | — | — | — | based on OGL | yes | NEEDS_KEY |
| CH | opentransportdata.swiss (FEDRO) | `opentransportdata.swiss` | DATEX II | registration; access limited to 6 months | — | — | — | FEDRO terms | yes, cite source | NEEDS_KEY |
| EE | Tark Tee DATEX gateway | `tarktee.ee` | DATEX II 3.6 / 2.3 | key after staff review | — | — | — | not read | — | NEEDS_KEY |
| PL | GDDKiA KPD | `kpd.gddkia.gov.pl` | DATEX II 3.4 | registration and client certificate | — | — | — | `kpd.gov.pl/regulamin` | — | NEEDS_KEY |
| SI | Slovenia NAP | `nap.si` | DATEX II | registration of a business entity | — | — | — | general terms | — | NEEDS_KEY |
| AT | ASFINAG DATEX II | `contentportal.asfinag.at` | DATEX II | contract | — | — | — | contract | contract | NEEDS_KEY |
| DE | Mobilithek | `mobilithek.info` | DATEX II | registration | — | — | — | per offer | per offer | NEEDS_KEY |
| GB-SCT | Traffic Scotland DATEX II | `traffic.gov.scot` | DATEX II | approved subscribers | — | — | — | — | — | NEEDS_KEY (and RSS unreachable) |
| GB-WLS | Traffic Wales DATEX II | `traffic.wales/developers` | DATEX II | access application | — | — | — | — | — | NEEDS_KEY |
| GB-ENG | DfT Street Manager | — | push JSON | registration | — | — | — | OGL v3 | yes | NEEDS_KEY |
| GB-MAN | Transport for Greater Manchester (TfGM) | developer portal | — | key | — | — | — | — | — | NEEDS_KEY |
| GB-LDS | Leeds live roadworks API | `services.roadworks.org/sdep-publication/v5.2/sdep.asmx` | SOAP (Elgin) | login | — | — | — | commercial provider | — | RESTRICTED |
| DE-K | Köln roadworks WFS | `geoportal.stadt-koeln.de` | WFS | — | — | — | — | dl-zero-de/2.0 (from search) | — | BLOCKED (robots `Disallow: /`) |
| CH-BS | Basel-Stadt | `data.bs.ch` | Opendatasoft | — | — | — | — | — | — | BLOCKED (robots `/api/`) |
| PT | dados.gov.pt; Lisboa open data | `dados.gov.pt`; `dadosabertos.cm-lisboa.pt` | — | — | — | — | — | — | — | BLOCKED (robots 500; `/api/` plus Cloudflare challenge) |
| GB-NIR | DfI temporary traffic restrictions (ArcGIS) | `mappingportal.infrastructure-ni.gov.uk/…/External_Viewer_TTR/FeatureServer/0` | ArcGIS REST | — | — | — | — | none stated | — | UNREACHABLE |
| GB-SCT | Traffic Scotland RSS | `traffic.gov.scot`, `trafficscotland.org` | RSS | — | — | — | — | — | — | UNREACHABLE (HTTP 403) |
| CZ | NDIC / ŘSD | `registr.dopravniinfo.cz` | DATEX II | — | — | — | — | — | — | UNREACHABLE |
| DE-M | München roadworks | `opendata.muenchen.de` | WFS | — | — | — | — | dl-de/by-2.0 (from search) | — | UNREACHABLE (HTTP 503) |
| CH-BE | Bern roadworks WFS | `map.bern.ch` | WFS | — | — | — | — | — | — | UNREACHABLE |
| LV | Latvian State Roads situation feed | `fits2-datex-lvc-prod.azurewebsites.net` | DATEX II | — | — | — | — | — | — | UNREACHABLE (DNS) |
| BE-WAL | Wallonia, Belgian NAP | `transportdata.be` | — | — | — | — | — | — | — | UNREACHABLE (HTTP 502); no Walloon feed found |
| CH-ZH | Zürich VBZ_Baustellen | `ogd.stadt-zuerich.ch/wfs/geoportal/VBZ_Baustellen` | GeoJSON (WFS) | none | 5 | point | none | terms_open | yes | not useful |
| IT | 5T Torino; Open Data Hub (South Tyrol) | `opendata.5t.torino.it/get_events`; `mobility.api.opendatahub.com` | JSON | none | 0 (`null`); 2,368 (stale since 13 Oct 2025) | points | — | not read | — | not useful |
| IE | TII open data | `data.tii.ie` | DATEX II | none | no events (travel times, weather, VMS only) | — | — | CC BY 4.0 (from search) | yes | not a road-event source |

## PERMITTED sources: connector notes

### 1. NDW, Netherlands (`nl-ndw-actueel-beeld`, `nl-ndw-planningsfeed-wegwerkzaamheden`)

Authority: Nationaal Dataportaal Wegverkeer (NDW), national road traffic data
for all Dutch road authorities. The situation feeds come from Rijkswaterstaat
districts, provinces and municipalities.

- **Requests:**
  - `GET https://opendata.ndw.nu/actueel_beeld.xml.gz`: the current picture,
    rebuilt every minute. 358 KB compressed, 4.13 MB unpacked.
  - `GET https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz`:
    planned roadworks and events. 17.1 MB compressed, 214.5 MB unpacked.
  - Subsets of the current picture: `tijdelijke_verkeersmaatregelen_afsluitingen.xml.gz`
    (733 closure situations) and `veiligheidsgerelateerde_berichten_srti.xml.gz`
    (217 safety messages, points, start only).
  - No key and no parameters. All return HTTP 200.
- **robots.txt:** `opendata.ndw.nu/robots.txt` is 404, so no rules apply.
- **Format:** gzipped DATEX II v3 `SituationPublication`. Times are UTC (`Z`).
  Free-text comments are in Dutch.
- **Current picture:**
  - 1,123 situations: 1,112 current and 11 ended; 823 have an end time and 300
    do not. They hold 1,367 records.
  - Record types: RoadOrCarriagewayOrLaneManagement 955 (closures 632, lane
    closures 120), VehicleObstruction 190, SpeedManagement 96,
    ReroutingManagement 43, AbnormalTraffic 37, GeneralNetworkManagement 19
    (bridge openings), Accident 14, GeneralObstruction 13.
  - Newest record: 2026-10-16T12:19:43Z.
- **Planned feed:**
  - 14,553 situations: 5,588 current, 8,572 upcoming, 393 ended; 14,541 have
    both start and end. They hold 62,630 records.
  - Record types: lane management 26,044, rerouting 14,114, MaintenanceWorks
    12,780, speed 7,550, PublicEvent 1,489, ConstructionWorks 286.
- **Geometry:** `gmlLineString srsName="WGS 84"` with the `posList` in
  **lat lon** order, plus `pointByCoordinates` and AlertC.
  - Current picture: 1,358 of 1,367 records have coordinates.
  - Planned feed: lines on 48,630 records, points on 26,931.
- **Licence:** the portal's "Copyright & disclaimer" link leads to
  <https://www.ndw.nu/copyright>: "Tenzij anders vermeld is op de inhoud van
  deze website de Creative Commons Zero (CC0) verklaring van toepassing. Dit
  houdt in dat hergebruik van de inhoud van deze site is toegestaan …".
  - Images are excluded.
  - Do not suggest that NDW endorses the derived product.
  - Commercial use: yes. Attribution is not required; "Bron: NDW" is a
    courtesy.
- **Rate limits and storage:** no rate limit or storage restriction published,
  and no availability guarantee.
- **Samples:** valid XML subsets that keep the envelope, chosen round-robin by
  record type.
  - `europe\nl-ndw-actueel-beeld_2026-10-16.xml`: 1.90 MB, 365 of 1,123
    situations; the full file is 4.13 MB.
  - `europe\nl-ndw-planningsfeed-wegwerkzaamheden_2026-10-16.xml`: 1.90 MB,
    122 situations; the full file is 214.5 MB.
- **Connector notes:**
  - Stream-parse the planned feed (214 MB unpacked) and keep only REI's
    current and upcoming window.
  - Reverse the `posList` pairs to lon/lat.
  - Group records by situation: one situation can hold many records
    (lane management, rerouting, speed).
  - NDW ends its DATEX v2.3 *measurement* files on 9 Feb 2027; the situation
    feeds are already v3.

### 2. Scottish Road Works Register disruptions export, Scotland (`uk-scotland-srwr-disruptions`)

Authority: Office of the Scottish Road Works Commissioner. It covers every
Scottish road authority, including Edinburgh (2,464 rows) and Glasgow (1,918).

- **Requests:** three steps, all HTTP 200, no auth.
  1. `GET https://downloads.srwr.scot/disruptions-export/api/v1/files` returns
     JSON listing the last 7 daily zips, about 7 MB each.
  2. `GET https://downloads.srwr.scot/disruptions-export/api/v1/file/SRWRDisruptionsExport20261016.zip`
     returns `{"url": "<Azure SAS URL on srwrexport.blob.core.windows.net>"}`.
     The link expires after about 10 minutes.
  3. `GET` that URL returns the zip.
- **robots.txt:** `roadworks.scot` is a standard Drupal file (only `/admin`,
  `/search`, `/user` disallowed). `downloads.srwr.scot` has none (404). The
  blob host answers 400.
- **Format:** a zip holding `CurrentActivities.csv` (25 MB),
  `CompletedActivities.csv` and `PotentialBusConflicts.csv`. Updated daily
  overnight. A full export is also at `downloads.srwr.scot/export/daily` (not
  fetched).
- **Records:** 22,157 current activities.
  - 5,815 in force now, 15,114 upcoming (8,904 within 30 days), and 1,228 whose
    end time has passed but which are not closed.
  - Newest `LastUpdatedDateTimeUTC`: 2026-10-16T00:30:52Z.
- **Geometry:** on every row.
  - `Latitude` and `Longitude` (WGS84).
  - `GeometryFull` as WKT in British National Grid (EPSG:27700): LINESTRING
    8,811, POLYGON 6,081, POINT 4,900, MULTILINESTRING 1,268, MULTIPOLYGON 630,
    MULTIPOINT 467.
- **Times:** `StartDateTimeUTC` and `EndDateTimeUTC` on every row. Also
  `EarliestStartDateTimeUTC`, `LatestPossibleEndDateTimeUTC`, and
  `ActualStartDateTimeUTC` (filled on 3,409 rows).
- **Types:**
  - `Category`: Major 6,360, Standard 5,388, Minor With Excavation 3,097, Road
    Restriction 1,508, Permission 1,476, Temporary Traffic Restriction 1,233,
    Event 838, Emergency 291, Urgent 279.
  - `TrafficManagement`: Road Closure 5,886 (845 in force now), Portable
    Traffic Lights 4,877, Give and Take 4,790, Lane Closure 1,178, Slip
    Closure 307, Contraflow 54.
  - `ActivityStatus`: Proposed 9,347, Advance Planning 4,940, In Progress
    3,409, Recorded 2,316, Commenced 1,638, Potential 507.
  - Language: English.
- **Licence:** <https://roadworks.scot/publications/scottish-road-works-register-open-data>:
  "Open Data from the SRWR is available under the Open Government Licence v3".
  - Commercial use: yes.
  - Attribution: OGL v3 requires one, but no wording is given. Suggested:
    "Contains Scottish Road Works Register data, Office of the Scottish Road
    Works Commissioner, licensed under the Open Government Licence v3.0".
- **Rate limits and storage:** no rate limit published, but the site's script
  handles HTTP 429. No storage restriction found.
- **Samples:**
  - `europe\uk-scotland-srwr-disruptions_2026-10-16.csv`: 1.90 MB, 1,669 rows
    with the header, In Progress and Commenced first.
  - `europe\uk-scotland-srwr-disruptions_2026-10-16_full.zip`: 7.37 MB, the
    full export.
- **Connector notes:**
  - This is a daily batch, not real time.
  - Filter on `TrafficManagement` and `Category`, because many rows are
    footway or minor works.
  - Treat `ActivityStatus=Potential` as tentative.
  - The id is `ActivityReference` + `PhaseNumber`.
  - Reproject `GeometryFull` from EPSG:27700.

### 3. GIPOD planned hindrance, Flanders (`be-flanders-gipod-hinder`)

Authority: Digitaal Vlaanderen (GIPOD, the Flemish register of works and
events in the public domain).

- **Request:** `GET https://geo.api.vlaanderen.be/GIPOD/ogc/features/collections/HINDER/items?f=json&limit=1000`.
  Page on with `startIndex`, using the `next` link. HTTP 200, GeoJSON, WGS84,
  no key.
- **robots.txt:** 404, so no rules apply.
- **Volume:** WFS `resultType=hits` returns `numberMatched=10000`, the server's
  cap, so there are at least 10,000 zones.
- **First page:** 1,000 zones for 983 hindrances.
  - Geometry: all MultiPolygon.
  - Times: `HindranceStart` and `HindranceEnd` (UTC) on all 1,000: 581 current,
    415 upcoming, 4 ended.
  - `SevereHindrance` true on 348. `ZoneType`: HinderZone 819, WerfZone 181.
  - `HindranceConsequenceOf`: works 479, groundworks 334, events 187.
  - Newest modification: 12:35Z.
- **Related collections:** `OMLEIDING` (diversions, MultiLineString),
  `INNAME` (occupations, ≥ 10,000) and `*_PUNT` (point versions).
- **Language:** `Consequences` is Dutch text. Many entries are pedestrian or
  parking only ("Parkeerverbod"). Keep traffic effects such as "Geen doorgang
  voor gemotoriseerd verkeer", "Afgesloten in 1 rijrichting" and "Vermindering
  van rijstroken".
- **Licence:** the dataset metadata record `2b4b3bb7-cadc-41a0-b5ae-796a84a20b52`
  names the "Modellicentie voor gratis hergebruik" v1.0
  (<https://www.vlaanderen.be/digitaal-vlaanderen/onze-diensten-en-platformen/open-data/voorwaarden-voor-het-hergebruik-van-overheidsinformatie/modellicentie-gratis-hergebruik>).
  - Art. 3: "De licentienemer krijgt het niet-exclusieve en wereldwijde recht
    om het product te hergebruiken voor elk rechtmatig doeleinde, met inbegrip
    van het reproduceren, doorgeven, publiceren, aanpassen en commercieel
    exploiteren van het product."
  - Art. 4: attribution as the licensor specifies. The fallback wording is
    "bevat overheidsinformatie, verkregen onder de modellicentie voor gratis
    hergebruik Vlaanderen v1.0". REI must not suggest official status.
- **Service terms:** "De service kan door iedereen gebruikt worden". IP
  addresses are kept for 90 days. No rate limit published.
- **Sample:** `europe\be-flanders-gipod-hinder_2026-10-16.geojson`: 1.94 MB,
  the first 800 features of the 1,000-feature page (the full page is 2.31 MB).

### 4. DGT incidents DATEX II 3.7, Spain (`es-dgt-datex2-v37`)

Authority: Dirección General de Tráfico. It covers national roads except the
Basque Country and Catalonia.

- **Request:** `GET https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml`,
  with gzip accepted and no parameters. HTTP 200, 4.69 MB, `Cache-Control:
  max-age=60`. The feed updates every minute.
- **robots.txt:**

  ```
  User-agent: *
  Disallow: /dataset
  Disallow: /dataset/rate/
  Disallow: /revision/
  Disallow: /dataset/*/history
  Disallow: /api/
  Crawl-Delay: 10
  ```

  - `/datex2/` is allowed, and 10 s was kept between requests.
  - The licence was read from the English page
    `/en/dataset/incidencias-dgt-datex2-v3-7/resource/1d36ea74-…`. The rule
    `Disallow: /dataset` literally covers only paths that *begin* with
    `/dataset`, but it may be meant to cover the English pages too.
- **Format:** DATEX II 3.7, profile "DGT (Spain) Profile RTTI
  SituationPublication 3.7_1.0". The namespaces are `http://levelC/schema/3/…`,
  not datex2.eu. Times carry an offset (+02:00). Codes are DATEX; the feed is
  `lang="es"`.
- **Records:** 837 situations holding 1,101 situation records, all
  `validityStatus` active.
  - Newest `versionTime`: 2026-10-16T14:21:10+02:00.
  - 22 records have a `versionTime` before 2026.
- **Geometry:** WGS84 lat/lon on every record.
  - `PointLocation` gives a single point.
  - `SingleRoadLinearLocation` gives from and to points with the road, km
    point, municipality and province. There is no line.
- **Times:** `overallStartTime` on all records; `overallEndTime` on 462.
- **Types:**
  - Records: RoadOrCarriagewayOrLaneManagement 608 (laneClosures 222,
    carriagewayClosures 122, roadClosed 29), GenericSituationRecord 375,
    AbnormalTraffic 62, GeneralObstruction 21, SpeedManagement 18.
  - Causes: roadMaintenance 543, vehicleObstruction 339, accident 36,
    rockfalls 25.
- **Licence:** the NAP resource page
  (<https://nap.dgt.es/en/dataset/incidencias-dgt-datex2-v3-7/resource/1d36ea74-593d-4e45-acfa-fb8db5a460bc>)
  says "License: Creative Commons Attribution". No version or attribution
  wording is given; credit "Dirección General de Tráfico (DGT)". Commercial
  use: yes.
- **Rate limits:** none published beyond the 10 s crawl delay.
- **Sample:** `europe\es-dgt-datex2-v37_2026-10-16.xml`: 1.90 MB, the first
  245 situations as valid XML; the full file is 4.69 MB.
- **REI caveat:** 639 of 1,101 records have no end time, so REI would show
  them as unconfirmed.

### 5. Bruxelles Mobilité traffic events, Brussels (`be-brussels-traffic-events`)

Authority: Bruxelles Mobilité / Brussel Mobiliteit ("Chantiers et incidents").

- **Request:** `GET https://data-mobility.irisnet.be/datasets/v1/traffic/collections/traffic_events/items/?limit=1000&crs=http://www.opengis.net/def/crs/EPSG/0/4326`.
  OGC API Features, GeoJSON, HTTP 200, no key.
- **robots.txt:** 404 on `data-mobility.irisnet.be` and on
  `data.mobility.brussels`.
- **Records:** `numberMatched` 233.
  - `datex_codes`: RWK (roadworks) 230, RCA (road closed) 2, BKD (broken-down
    vehicle) 1.
  - Point on all.
  - `start_time` and `end_time` on all: 136 current, 92 upcoming, 5 ended.
  - Text in French and Dutch: location, direction, consequences, importance,
    impacted lanes.
  - Newest update: 14:25 local time.
- **Time zone:** this API returns naive *local* time (Europe/Brussels). The
  WFS copy (`data.mobility.brussels/geoserver/bm_traffic/wfs`, layer
  `bm_traffic:events`) wrongly labels the same local times "Z".
- **Licence:** the DCAT record
  (`…/collections/traffic_events/dcat/`) gives `"dct:license":"CC0"`.
  Commercial use: yes. Suggested credit "Bruxelles Mobilité / Brussel
  Mobiliteit".
- **Rate limits:** the WFS response headers show 6 concurrent requests per
  user and 10 per IP.
- **Not useful:** the layer `worksites_comm` has 120 points, no dates, and was
  last updated 2024-11-26.
- **Sample:** `europe\be-brussels-traffic-events_2026-10-16.geojson`, 251 KB,
  the full response.

### 6. Polizei Hamburg traffic messages, Hamburg (`de-hamburg-polizei-verkehrsinformation`)

Authority: Freie und Hansestadt Hamburg, Polizei Hamburg (Landesmeldestelle).

- **Request:** `GET https://api.hamburg.de/datasets/v1/verkehrsinformation/collections/hauptmeldungen_aktuell/items?f=json&limit=10000`.
  HTTP 200, GeoJSON (OGC API Features), no key. 276 matched, 275 returned.
  - Other collections: `hauptmeldungen` (33,898 rows including history),
    `meldungen_linien` and `meldungen_punkte`.
- **robots.txt:** only `User-agent: spatineo` is disallowed; `*` is allowed.
- **Geometry:** point on all, WGS84.
- **Times:**
  - `start` on all 275; `end` on 240. Newest start: 2026-10-16 11:55.
  - The values are UTC but carry no zone marker. In 83 records checked, the
    time in the German description is 1–2 hours later than the field.
  - Some long-open items are stale, such as a fire-brigade closure open since
    18 Feb 2026 with no end.
- **Types:** `status` BAUSTELLE 184, SPERRUNG 61, WARTUNG 14, STAU 12,
  SCHLECHTE_FAHRBEDINGUNG 3, HINWEIS 1. `art` holds a DATEX-like class and
  `art_detail` a subtype (e.g. roadClosed 48). `description` is in German.
- **Licence:** the API's `license` link reads "Datenlizenz Deutschland
  Namensnennung 2.0" (<https://www.govdata.de/dl-de/by-2-0>).
  - The API's `attribution` field: "Freie und Hansestadt Hamburg, Polizei
    Hamburg". Credit that and name the licence with its link.
  - Commercial use: allowed under DL-DE BY 2.0. The licence page itself was
    not fetched, because govdata.de's robots.txt disallows all agents.
- **Rate limits:** none published.
- **Sample:** `europe\de-hamburg-polizei-verkehrsinformation_2026-10-16.geojson`,
  130 KB.

### 7. Barcelona works in public space (`es-barcelona-obres`)

Authority: Ajuntament de Barcelona (source system GIAT).

- **Request:** `GET https://opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search?resource_id=4e6b3bfe-2f47-4d35-aa7d-3e4bcc930cea&limit=1000&sort=data_inici%20desc`.
  HTTP 200, CKAN JSON, no key. Total 1,930 works; page with `offset`.
- **robots.txt:** HTTP 403, so there are no rules to read. Under RFC 9309 an
  unavailable robots file places no restriction.
  - The direct file download
    (`/data/dataset/fd9f355f-…/resource/089bcf9e-…/download`) also returned 403
    to REI's User-Agent; the documented CKAN API answered 200.
  - A firewall may sit in front of the site, so watch for blocks once a
    connector runs.
- **Latest 1,000:**
  - Status: Finalitzada 722, En execució 275, Aturada 3. 220 are current by
    date.
  - Geometry: `geometria_wgs84` as WKT POLYGON 774, MULTIPOLYGON 203, none
    23. ETRS89 geometry is also given.
  - `data_inici` and `data_fi` are dates only. Newest start: 2026-10-18.
  - `tipusobra`: Urbanització 284, Serveis 273, Clavegueram 142,
    Infraestructura del transport 77.
- **Scope:** works in public space, not traffic impact as such. Text is in
  Catalan.
- **Licence:** `package_show?id=obres` gives `license_id` CC-BY-4.0 ("Creative
  Commons Attribution 4.0"). Commercial use: yes, with attribution
  ("Ajuntament de Barcelona").
- **Updates and limits:** updated daily (DIARIA); no rate limit published.
- **Sample:** `europe\es-barcelona-obres_2026-10-16.json`: 1.78 MB, 500 of the
  1,000 rows; the full response is 3.6 MB.
- **Not checked:** the dataset `frase` (5-minute updates, CC BY 4.0) looks like
  the text "Avís d'incidències" feed.

### 8. Verkeerscentrum Vlaanderen DATEX II v3, Flanders motorways (`be-flanders-verkeerscentrum-datex2v3`)

Authority: Verkeerscentrum Vlaanderen (Agentschap Wegen en Verkeer).

- **Request:** `GET https://www.verkeerscentrum.be/uitwisseling/datex2v3`.
  HTTP 200, DATEX II v3 XML, 284 KB, no key.
- **robots.txt:** `/uitwisseling/` is allowed.
- **Records:** 83 situations (81 current, 2 ended; 43 with an end) holding 105
  records.
  - Lane management 56 (new roadworks layout 33, narrow lanes 17, road closed
    6), AbnormalTraffic (queues) 26, MaintenanceWorks 19, Accident 3.
- **Geometry:** `gmlLineString` in **EPSG:31370 (Belgian Lambert 72)** on 89
  records, which needs reprojection. WGS84 points on 16. AlertC codes on 90.
- **Text:** there is no free text and there are no road names. Names would
  need the Belgian AlertC location table.
- **Times:** local, with an offset (+02:00).
- **Licence:** the Flemish catalogue distribution
  (`vlaanderen.be/DataCatalogRecord/8af79acb-…`) names the Modellicentie
  Gratis Hergebruik v1.0, the same licence as GIPOD. Commercial use: yes. No
  guarantee of quality or availability.
- **Sample:** `europe\be-flanders-verkeerscentrum-datex2v3_2026-10-16.xml`,
  284 KB, the full file.

### 9. Hamburg roadworks (Bauweiser) (`de-hamburg-baustellen`)

Authority: Freie und Hansestadt Hamburg, Behörde für Verkehr und
Mobilitätswende.

- **Request:** `GET https://api.hamburg.de/datasets/v1/baustellen/collections/baustelle/items?f=json&limit=10000`.
  HTTP 200, GeoJSON, no key, 161 records. The collection
  `tns_steckbrief_visualisierung` holds the same 161 points.
- **Geometry:** point on all, WGS84 (stored as EPSG:25832).
- **Times:** `baubeginn` and `bauende` on all, as dates only (`dd.mm.yyyy`):
  143 current, 18 upcoming, 0 ended. `letzteaktualisierung` runs from
  2021-08-20 to 2026-10-16 13:54.
- **Content:** large works projects only (`titel`, `organisation`, `anlass`,
  `umfang`, `umleitungsbeschreibung`, `isthotspot` on 9). The work lines and
  closure type exist only in German text.
- **Licence:** "Datenlizenz Deutschland Namensnennung 2.0". Attribution
  (`attribution` field): "Freie und Hansestadt Hamburg, Behörde für Verkehr und
  Mobilitätswende". Commercial use: yes.
- **Sample:** `europe\de-hamburg-baustellen_2026-10-16.geojson`, 321 KB.

### 10. Vienna roadworks affecting traffic (`at-wien-baustellen-linien`, `at-wien-baustellen-punkte`)

Authority: Stadt Wien.

- **Requests:** both HTTP 200, GeoJSON, no key.
  - `GET https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:BAUSTELLENLINOGD&srsName=EPSG:4326&outputFormat=json`
    (lines)
  - The same request with `typeName=ogdwien:BAUSTELLENPKTOGD` (points).
  - The native CRS is EPSG:31256; `srsName=EPSG:4326` works.
- **robots.txt:** 404.
- **Records:** 53 LineStrings (50 current, 3 upcoming) and 25 points (20
  current, 2 upcoming, 3 ended).
  - `OBJEKT_BEGINN` and `OBJEKT_ENDE` on all, as dates (`2026-10-19Z`).
    Newest start: 2026-10-22.
  - `BEHINDERUNGSART`: road construction 30, pipe laying 20, track works 9,
    U-Bahn works 7, sewer works 6, bridge works 2.
  - `BEZEICHNUNG` and `PRESSETEXT` hold German text, including diversions.
- **Personal data:** `ANSPRECHPERSON` and `ANSPRECHPERSON_TEL` hold named
  contact people and phone numbers. The connector must drop both fields.
- **Licence:** <https://digitales.wien.gv.at/ogd-nutzungsbedingungen/>
  (redirected from `data.wien.gv.at/nutzungsbedingungen`):
  - "Open Government Data der Stadt Wien stehen unter einer 'Creative Commons
    Namensnennung 4.0 Lizenz' (CC BY 4.0). LizenznehmerInnen dürfen die Daten …
    kommerziell nutzen …"
  - Attribution: "Datenquelle: Stadt Wien – data.wien.gv.at".
- **Licence caveat:** the same page says some datasets are under CC BY-NC
  4.0, and the WFS capabilities still name CC BY 3.0 AT. The dataset-level
  licence (data.gv.at entry) was not confirmed.
- **Samples:** `europe\at-wien-baustellen-linien_2026-10-16.geojson` (65 KB)
  and `europe\at-wien-baustellen-punkte_2026-10-16.geojson` (22 KB).

### 11. Madrid Informo street incidents (`es-madrid-informo-incidencias`)

Authority: Ayuntamiento de Madrid, DG Gestión y Vigilancia de la Circulación.

- **Request:** `GET https://informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml`.
  HTTP 200, plain XML (`Incidencias/Incidencia`), no key. Updated about every
  5 minutes.
- **robots.txt:** 404 on `informo.madrid.es`. `datos.madrid.es` disallows
  `/api/` and the `/dataset/*/resource/*` downloads; its dataset page is
  allowed.
- **Records:** 113, all with `fh_inicio`, `fh_final` and WGS84
  `latitud`/`longitud` (UTM also given).
  - Types: Obras de mantenimiento 95, Obras en la vía 10, Obras de larga
    duración 6, Carriles cortados 2. Latest start: 2026-11-10.
  - Only 9 are current and 1 upcoming. 103 have an end time already passed but
    are still listed with `incid_estado`=1.
  - 37 have the same start and end.
  - Times have no zone (Europe/Madrid). Text is in Spanish.
- **Licence:**
  - Dataset page (<https://datos.madrid.es/dataset/202062-0-trafico-incidencias-viapublica>):
    "Creative Commons Attribution 4.0 International (CC BY 4.0)".
  - Conditions (<https://datos.madrid.es/pages/condiciones-de-uso>): "Las
    condiciones generales permiten la reutilización de los documentos para
    fines comerciales y no comerciales."
  - Credit "Ayuntamiento de Madrid".
- **Sample:** `europe\es-madrid-informo-incidencias_2026-10-16.xml`, 108 KB.
- **Not fetched:** the Calle 30 incidents dataset.

### 12. Traffic Wales roadworks RSS, Wales (`uk-traffic-wales-roadworks`)

Authority: Welsh Government, Traffic Wales. It covers motorways and trunk
roads only.

- **Requests:**
  - `GET https://traffic.wales/feeds/roadworks/rss.xml`: HTTP 200, RSS 2.0, 31
    items. Updated every 5 minutes.
  - `https://traffic.wales/feeds/incidents-events/rss.xml`: HTTP 200 but empty
    at fetch time.
  - Welsh-language versions: `traffig.cymru/porthiad/gwaith-ffordd/rss.xml`
    and `…/achlysuron-digwyddiadau/rss.xml`.
- **robots.txt:** standard Drupal file; `/feeds/` is allowed.
- **Records:** 12 in force, 19 upcoming. Newest `pubDate`:
  2026-10-16T11:51:06Z.
- **Geometry:** `georss:point` ("lat lon") on all 31.
- **Times:** only in the description text, e.g. "Start time: 18/10/2026 20:00 ,
  End Date: 20/10/2026 6:00". These are UK local times with no zone.
- **Other fields:** "Severity:" is Road closure 26, Moderate 4, Slight 1. The
  `guid` looks like `RNMDA_2026132667`.
- **Terms:**
  - <https://traffic.wales/developers>: "Traffic Wales traffic information is
    available to use in third party applications. Terms and conditions apply
    and vary according to the type of data feed … Traffic Wales must be
    credited as the data source." Access may be revoked if usage degrades the
    service. For RSS: "No registration is required."
  - <https://traffic.wales/copyright-statement>: OGL "(excluding logos, maps
    and data therein)", with source credit such as "Traffic Wales © Crown
    copyright".
- **Caveat:** neither page says "commercial" either way. Confirming with
  Traffic Wales is advisable.
- **Sample:** `europe\uk-traffic-wales-roadworks_2026-10-16.xml`, 22 KB.

### 13. CITA DATEX II 3.6, Luxembourg (`lu-cita-datex2-v36`)

Authority: Administration des ponts et chaussées (CITA), Luxembourg motorways.

- **Request:** `GET https://cita.lu/info_trafic/datex/situationrecord36`.
  HTTP 200, DATEX II 3.6 XML (datex2.eu namespaces), no key.
- **robots.txt:** `User-agent: *` with no `Disallow` lines.
- **Records:** 14 situations, 19 records. Newest `versionTime`:
  2026-10-16T14:34:22+02:00.
  - Types: MaintenanceWorks 11, ConstructionWorks 3, EquipmentOrSystemFault 3,
    obstructions 2.
  - Geometry: `gmlLineString` `posList` (lat lon order) on all 19, plus
    points.
  - Times: `overallStartTime` only; no record has an end. Under REI's rules
    every record would be unconfirmed.
- **Licence:** the data.public.lu API for
  <https://data.public.lu/fr/datasets/cita-evenements-trafic-en-datex-ii-v3-6/>
  reports `license: cc-zero`. Commercial use: yes; no attribution required.
- **Sample:** `europe\lu-cita-datex2-v36_2026-10-16.xml`, 73 KB.

### 14. Euskadi traffic incidences, Basque Country (`es-euskadi-traffic-incidences`)

Authority: Gobierno Vasco. It gathers incidents from 7 administrations.

- **Request:** `GET https://api.euskadi.eus/traffic/v1.0/incidences/byDate/2026/10/16?_page=1`.
  HTTP 200, JSON, no key.
  - 194 records for the day (`totalItems`), over 10 pages of 20. `_pageSize` is
    ignored.
  - The whole archive (`/incidences`) holds 382,901 records.
- **robots.txt:** none on `api.euskadi.eus`. The catalogue and legal pages on
  `opendata.euskadi.eus` are allowed.
- **Fields:** `incidenceType`, `cause`, `road`, `pkStart`/`pkEnd`, `direction`,
  `province`, `cityTown`, `incidenceLevel`, `latitude`/`longitude` (all have
  points). Text is in Spanish.
  - On page 1: Obras 11, Seguridad vial 5, Accidente 4.
- **Times:** `startDate` only, with no zone. There is no end date, even on
  records from 9 October, so every event would be unconfirmed under REI's
  rules.
- **Licence:**
  - The schema.org licence is <https://creativecommons.org/licenses/by/4.0/>.
  - Legal page (<https://opendata.euskadi.eus/general/-/informacion-legal-opendata/>):
    "licencia Creative Commons Reconocimiento 4.0 … Que el contenido de la
    información no sea alterado … Que se cite la fuente … Que se mencione la
    fecha de la última actualización."
- **Sample:** `europe\es-euskadi-traffic-incidences_2026-10-16.json`, 7 KB,
  page 1.

### 15. TrafficwatchNI roadworks RSS, Northern Ireland (`uk-trafficwatchni-roadworks`)

Authority: Department for Infrastructure (DfI) Roads, Traffic Information and
Control Centre.

- **Request:** `GET https://rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml`.
  HTTP 200, RSS 2.0, 1.04 MB, 1,807 items. The feeds say they update every 5
  minutes.
  - Other feeds held 1 item (incidents, cleared 4 Oct), 0 (events), 1
    (roadworks Belfast) and 0 (incidents Belfast).
- **robots.txt:** 404 on both hosts.
- **Records:** newest `pubDate` 2026-10-16T13:00+01:00.
  - Titles give the type: Lane closure 1,161, Road closure 566, One Way
    closure 31.
  - `guid` is `TWNIRoadwork<id>`. The text gives the reason and the diversion
    routes.
- **Geometry: none.** The location is only the title, "ROAD NO, STREET, TOWN".
- **Times:** only in text, e.g. "Roadworks will operate from 09:30 on Mon 19th
  Oct 2026 to 16:30 on Sun 25th Oct 2026". 1,497 items parse (332 in force,
  1,165 upcoming); 310 give only daily hours.
- **Licence:**
  - <https://www.trafficwatchni.com/twni/terms-and-conditions>: "Traffic feeds
    may be freely used on commercial sites subject to the following
    conditions: DfI Traffic Information and Control Centre is credited as the
    information source. All URLs in the feed are preserved and remain
    functional…". DfI may withdraw access if the feeds degrade its service.
  - OpenDataNI also lists the roadworks dataset under the UK OGL.
- **REI caveat:** with no geometry it fails REI's own-geometry rule. It is
  usable only if REI geocodes the road and town names.
- **Sample:** `europe\uk-trafficwatchni-roadworks_2026-10-16.xml`, 1.04 MB,
  the full feed.

## Not PERMITTED: notes

### ASK_PERMISSION

- **Autobahn GmbH API (DE).**
  - **Requests:**
    - `GET https://verkehr.autobahn.de/o/autobahn/` returns 117 road ids; one is
      a duplicate, `"A60 "`.
    - `GET /o/autobahn/{road}/services/roadworks|closure|warning`.
    - `GET /o/autobahn/details/roadworks/{id}`.
    - robots.txt is 404; HTTP 200 JSON, no key.
  - **Data:** a LineString on every record, plus `coordinate` and `extent`.
    - `startTimestamp` is on only about half the roadworks, and there is no
      structured end. Start and end can be parsed from German text ("Beginn:
      10.08.26 um 11:00 Uhr / Ende: 26.10.26 um 20:00 Uhr") for 233 of 263 A1
      roadworks and 27 of 29 closures.
    - Warnings carry `"source":"inrix"`, which is commercial third-party data.
  - **Why ASK_PERMISSION:** no licence or terms were found. The community
    OpenAPI description at autobahn.api.bund.dev has none; its contact is
    kontakt@autobahn.de. The autobahn.de imprint is silent.
  - **Raw files** (no sample, since not PERMITTED): `…\scratchpad\eu-raw\de-autobahn\`.
  - Worth asking: this is the best German national source.
- **Via Lietuva restrictions (LT).** `GET https://restrictions.eismoinfo.lt/`
  returns JSON without a key.
  - 308 records: CONSTRUCTION 232, HAZARD 76.
  - Every record has a WGS84 polyline (lat lon), road and km, direction, and
    start and end with offsets.
  - No licence was found, and data.gov.lt's firewall refused the request.
  - Raw copy: `…\scratchpad\eu-raw\lt-eismoinfo\root.json`.
- **Servei Català de Trànsit via DGT (ES-CT).**
  `GET https://infocar.dgt.es/datex2/sct/SituationPublication/all/content.xml`
  returns 1.2 MB of DATEX II 1.0: 230 records (MaintenanceWorks 212), start
  only, a point on 198. The NAP page `nap.dgt.es/en/dataset/incidencias-sct`
  says "Contract or licence: No licence – No contract", and its metadata says
  "No se especificó la licencia".
- **Berlin VIZ (DE-BE).** `GET https://api.viz.berlin.de/daten/baustellen_sperrungen.json`
  returns 387 features (338 GeometryCollection, 49 Point) with
  `validity.from` and `validity.to`. But `Last-Modified` and the newest
  `tstore` are 2 Jul 2025, so the feed has been frozen for 15 months.
  daten.berlin.de and datenregister.berlin.de answered 403 with a bot
  challenge, so the licence was not read.
- **Dublin City Council current road closures (IE).** An HTML page, not a feed.
  It lists 5 closures with RDFa latitude and longitude and date ranges such as
  "17/10/2026 - 08:00 - 17/10/2026 - 19:59". No data licence was read.
- **TII traffic (IE).** `traffic.tii.ie` is a single-page app behind Google
  reCAPTCHA, with no documented API. The legacy NRA DATEX II events service
  needed a username and password. Per South Dublin County Council minutes, a
  national real-time roadworks portal is planned "over the course of 2026".

### NEEDS_KEY (no registration was made)

- **Denmark, Vejdirektoratet:** data is in the DU-portal (`nap.vd.dk`).
  Downloads need a bearer token from Vejdirektoratet's login service and a
  subscription.
  - Dataset 1208 "Road Works and Planned Events (snapshot)" shows CC BY 4.0,
    DATEX II, every 10 minutes.
  - Also: 1209 (change feed), 222 (traffic messages), 1243 (Copenhagen
    roadworks).
- **Norway, Statens vegvesen:**
  `datex-server-get-v3-1.atlas.vegvesen.no/datexapi/GetSituation/pullsnapshotdata`
  returns HTTP 401; access must be requested. "Use is subject to the Norwegian
  Licence for Open Government Data (NLOD)". Free of charge; credit "Norwegian
  Public Roads Administration".
- **Sweden, Trafikverket:** an API key after registration. The licence link
  goes to CC0 1.0.
- **National Highways (England):** a free subscription key and 10 calls a
  minute. Terms are in `source-research-2026-10-14.md`. Portal:
  <https://developer.data.nationalhighways.co.uk/>.
- **opentransportdata.swiss / FEDRO (CH):** registration required. The FEDRO
  terms say "Access to the data is limited to six months" for standard users,
  with request limits. Cite "opentransportdata.swiss".
- **Estonia, Tark Tee:** a DATEX II gateway (versions 3.6 and 2.3: closures,
  roadworks, detours, safety messages). The key is issued after Transport
  Administration staff review the registration.
- **Poland, GDDKiA KPD:** "Access requires registration and client-certificate
  authentication". Terms at `kpd.gov.pl/regulamin`. The old public XML is 404.
- **Slovenia NAP:** "Access to data is enabled upon prior registration of the
  business entity user, and acceptance of the general terms and conditions of
  use."
- **ASFINAG (AT):** a contract through `contentportal.asfinag.at`.
- **Mobilithek (DE):** registration; the Bavarian offers there are "restricted
  use".
- **Traffic Scotland DATEX II:** approved subscribers only, per search
  summaries.
- **Traffic Wales DATEX II:** events, roadworks and VMS need an access
  application.
- **DfT Street Manager:** registration, and data is pushed to an endpoint REI
  would host. Already covered in the 14 October research.
- **TfGM (Greater Manchester):** the developer portal needs a key, and no
  roadworks or incident API was found.

### RESTRICTED

- **Leeds live roadworks API (Data Mill North):** a SOAP service at
  `services.roadworks.org`, run by Elgin, a commercial provider. It needs a
  login, which was not used. The portal shows it as 404 and last updated
  2017-02-23.
- **one.network** (named by Bristol and the West Midlands): a commercial
  platform. Note only.

### BLOCKED by robots.txt

- **Köln roadworks WFS:** `geoportal.stadt-koeln.de/robots.txt` is
  `User-agent: * / Disallow: /`. The licence per search results is
  dl-zero-de/2.0.
- **Basel-Stadt:** `data.bs.ch` disallows `/api/` and downloads.
- **dados.gov.pt:** robots.txt returned HTTP 500, so the site is treated as
  fully disallowed.
- **Lisboa open data:** robots.txt disallows `/api/`, and the dataset page
  served a Cloudflare challenge. Search suggests the yearly CSVs end in 2022.
- **data.gov.ie and data.smartdublin.ie:** `/api/` and `?q=` search are
  disallowed, so the catalogues were not searched.

### UNREACHABLE

| Source | What happened |
| --- | --- |
| Traffic Scotland (`traffic.gov.scot`, `trafficscotland.org`) | HTTP 403 from the load balancer on robots.txt and the developer hub. Archived pages describe free RSS feeds credited to Traffic Scotland. |
| Northern Ireland DfI temporary traffic restrictions ArcGIS | robots.txt timed out twice. |
| Czechia NDIC (`registr.dopravniinfo.cz`) | Timed out twice. |
| Bern roadworks WFS (`map.bern.ch`) | Timed out twice. |
| München open data | HTTP 503 twice; GeoServer layer not found. |
| Latvia (`fits2-datex-lvc-prod.azurewebsites.net`) | DNS does not resolve; `data.lvceli.lv` page is 404. |
| Belgian NAP (`transportdata.be`) | HTTP 502 three times. robots.txt, loaded on the second try, says `Disallow: /api/`, Crawl-Delay 10. No Walloon feed was found. |
| ckan.open.nrw.de | Timed out once; not retried. |

### Not useful

| Source | Why |
| --- | --- |
| Zürich VBZ_Baustellen | 5 points, no dates, one test record. |
| 5T Torino `get_events` | Returned `null`. |
| Open Data Hub, South Tyrol | 2,368 points, but the newest transaction is 2025-10-13; licence not read. |
| Brussels `worksites_comm` | No dates; last updated 2024-11-26. |
| TII open data | No events: travel times, weather, VMS and VDS data only. |
| Donostia road closures | The CC BY-SA 3.0 URL now returns 403; it may have moved to a CKAN portal. |

## Access-rule notes from this research

- **Vienna:** the terms URL `data.wien.gv.at/nutzungsbedingungen` redirected
  to `digitales.wien.gv.at`, whose robots.txt was not checked first. One page
  was read.
- **Czechia:** a second request to `registr.dopravniinfo.cz` was sent before
  its robots.txt had been read. Neither request connected.
- **Latvia:** the content request went out in the same command as robots.txt.
  DNS failed for both, so no server was reached.
- **DGT:** the English dataset page was read under a literal reading of
  `Disallow: /dataset` (see source 4).
- **Barcelona:** robots.txt answered 403, which was treated as no rules (see
  source 7).
- **data.public.lu:** its robots.txt was requested once by each of two
  research passes.
- **Counts:** no host received more than 9 requests.

## Not verified

- A licence written specifically for NDW's situation feeds. Only the
  site-wide CC0 statement was found; data.overheid.nl does not list the feeds.
- The DL-DE BY 2.0 licence text: govdata.de's robots.txt blocks all agents.
- Vienna's dataset-level licence (CC BY 4.0, BY-NC 4.0 or BY 3.0 AT).
- Whether Traffic Wales allows commercial use explicitly.
- DGT's CC BY version and attribution wording. The DGT DATEX II v3.6 feed was
  not fetched.
- Autobahn national totals (estimated from A1 and A7 only), its licence, and
  the redistribution rights of its INRIX warnings.
- GIPOD totals beyond the 10,000 cap, and the `OMLEIDING` and `INNAME`
  totals.
- Update frequency of Hamburg, Vienna and GIPOD; NDW `planningsfeed_brugopeningen`.
- Brussels' general terms page.
- SRWR rate-limit figures and its data specification file.
- Barcelona's `frase` incidents feed; Madrid's Calle 30 feed; the Donostia
  replacement.
- Italy: CCISS/Viabilità Italia, ANAS, Autostrade per l'Italia, Milan and Rome
  portals.
- Portugal's national access point (IMT).
- Hungary (Magyar Közút DATEX II), Croatia, Romania, Greece, Prague Golemio.
- Any Walloon feed.
- Danish download contents and the Copenhagen set's licence.
- Estonian terms of use; the Lithuanian licence; Latvian access-point pages.
- Traffic Scotland's current RSS terms; the NI DfI TTR FeatureServer;
  Dublin City Council's licence.
- Rate limits for almost every source: none is published except Brussels WFS
  (6 concurrent per user, 10 per IP), DGT (crawl-delay 10 s) and National
  Highways (10 a minute with a key).
