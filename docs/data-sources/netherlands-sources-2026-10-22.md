# Netherlands: road-event sources beyond the two NDW feeds (22 October 2026)

REI already connects two NDW feeds (see
[netherlands-luxembourg-connectors-2026-10-21.md](netherlands-luxembourg-connectors-2026-10-21.md)):
the current picture (`actueel_beeld.xml.gz`) and the planned roadworks and
events feed (`planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz`). This pass
looks for every other Dutch road-event source:

- the rest of `opendata.ndw.nu`;
- municipal open data: Amsterdam, Rotterdam, Den Haag, Utrecht, Eindhoven, and
  whatever data.overheid.nl turns up;
- national and provincial sources that are not copies of NDW.

**Method.**
- **When:** every endpoint below was fetched live on 22 October 2026, between
  10:43 and 11:09 UTC (12:43–13:09 CEST).
- **User-Agent:** `JSAN-REI/1.0 (road event intelligence; source research)`.
- **Order and pace:** robots.txt was requested first on each host. Requests were
  sequential, about 2 seconds apart, and never more than 10 on one host.
  data.overheid.nl asks for `Crawl-delay: 10`; from its second API request on,
  its requests were 11 seconds or more apart.
- **What was not done:** no logins, keys, CAPTCHAs, proxies or browser disguise.
- **Scope:** research only. No code was changed, nothing was connected and
  nothing was committed.

**Verdicts** use REI's standard:
- **PERMITTED:** an explicit open licence or a commercial-use grant.
- **ASK_PERMISSION:** no terms found, or the terms say nothing about reuse.
- **RESTRICTED:** personal or non-commercial use only; or automated access,
  scraping or storage is forbidden; or robots.txt disallows the path.

This is a reading of published terms, not legal advice.

**Samples.** Every response was saved outside the repository, in
`C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\1f1e58d5-c7a5-480c-a06f-4cc65e0fa21f\scratchpad\nl-research\`
(called `nl-research\` below). The request log is `nl-research\requests-log.tsv`.

## Result in short

- **Nothing new is worth connecting as a main source.** The two connected NDW
  feeds already carry almost every open Dutch road event.
  - NDW's own documentation, confirmed by the data, says the current picture
    contains "Alle gegevens uit" the SRTI feed, the closures feed
    (`tijdelijke_verkeersmaatregelen_afsluitingen`) and the speed-limit feed
    (`tijdelijke_verkeersmaatregelen_maximum_snelheden`).
  - All 227 SRTI situations, all 103 speed-limit situations and 799 of the 800
    closure situations are in today's current picture with the same id. All
    but one of them also have the same version time. Those three files are
    subsets, not new sources.
- **Bridge openings (`planningsfeed_brugopeningen`) are PERMITTED (CC0) but are
  noise for REI.**
  - 1,657 openings at 80 bridges. 1,633 are forecasts that each last exactly
    6 minutes, about 1,600 a day.
  - They name no bridge and no road: only an ISRS code and a point.
  - The 24 openings in progress are already in the current picture.
  - Do not connect it as events.
- **Municipal sources:**
  - Every open municipal roadworks dataset found is either stale or a copy of
    Melvin, and Melvin already reaches REI through NDW's planned feed.
  - Amsterdam's WIOR works register (10,063 projects) stopped taking new
    registrations in 2024: only 59 projects end today or later. Amsterdam's
    events set holds 66 events from 2021–2022.
  - Hilversum's "Wegwerkzaamheden en evenementen" layer (CC BY 4.0) says it is
    built "o.b.v. het Melvin meldsysteem". 44 of its 49 notices have the same
    Melvin id as a situation in NDW's planned feed.
- **Most city portals block automated API access in robots.txt.** Den Haag,
  Rotterdam and Eindhoven run Opendatasoft portals whose robots.txt says
  `Disallow: /api/` for every agent except Googlebot: **RESTRICTED**.
  - Utrecht's open-data file server answered HTTP 403 to robots.txt and to the
    data file: blocked, not verified.
  - Utrecht's CC0 event-permit lists (with build-up and tear-down dates) could
    add event closures that NDW lacks; Utrecht has 13 event situations in NDW.
    They need a working download first.
- **Surprises:**
  1. **Amsterdam is under-represented in NDW.** The planned feed has 92
     situations from Gemeente Amsterdam against 722 from Rotterdam, 404 from
     Utrecht and 227 from Den Haag, and no open Amsterdam dataset fills the gap.
  2. **The Amsterdam data platform will require an API key.** Its API
     documentation says a key becomes mandatory for all DSO APIs at a date not
     yet set.
  3. **The KOOP traffic-decision repository is closed to robots.** Its
     robots.txt is `User-agent: * / Disallow: /`, although the data is CC0.
  4. **Provincie Utrecht and its municipalities (except the city of Utrecht) do
     not use Melvin** but an application called LTC. Their works still reach
     NDW, under the `AND01_` supplier prefix: Provincie Utrecht 24 situations,
     Nieuwegein 127, Veenendaal 32, Zeist 23.

## Summary table

| Source | Type | URL | HTTP | Items (22 Oct) | Dates? | Geometry? | robots.txt | Licence | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NDW planned bridge openings | DATEX II v3, gzip | `opendata.ndw.nu/planningsfeed_brugopeningen.xml.gz` | 200, 126 KB | 1,657 situations at 80 bridges (1,633 forecast, 24 in progress) | start on all; end on the 1,633 forecasts (always +6 min) | point on all (WGS 84) | 404, no rules | CC0 (NDW statement) | PERMITTED; noise, do not connect as events |
| NDW temporary closures | DATEX II v3, gzip | `opendata.ndw.nu/tijdelijke_verkeersmaatregelen_afsluitingen.xml.gz` | 200, 240 KB | 800 situations, 946 records | start on all; end on 760 | 799 of 800 located (lines 873 records, points 104) | 404 | CC0 | PERMITTED; duplicate (799 already in the current picture) |
| NDW temporary speed limits | DATEX II v3, gzip | `opendata.ndw.nu/tijdelijke_verkeersmaatregelen_maximum_snelheden.xml.gz` | 200, 26 KB | 103 | start on all; end on 98 | lines on all | 404 | CC0 | PERMITTED; duplicate (all in the current picture and the planned feed) |
| NDW SRTI safety messages | DATEX II v3, gzip | `opendata.ndw.nu/veiligheidsgerelateerde_berichten_srti.xml.gz` | 200, 28 KB | 227 | start on all; end on none | point 226, line 1 | 404 | CC0 | PERMITTED; duplicate (all in the current picture) |
| NDW emission zones | DATEX II v3 ControlledZone | `opendata.ndw.nu/emissiezones.xml.gz` | 200, 148 KB | 42 zones | validity periods | polygons | 404 | CC0 | PERMITTED; not road events |
| NDW variable message signs (DRIP) | DATEX II v3 VMS | `opendata.ndw.nu/dynamische_route_informatie_paneel.xml.gz` | 200, 593 KB | 686 sign controllers, 1,196 messages | time last set only | sign points | 404 | CC0, but images are excluded from CC0 | not road events |
| Other NDW files (MSI, flow, travel times, signs, charging, truck parking, VILD) | various | `opendata.ndw.nu/` | listing 200 | not fetched | — | — | 404 | CC0 | not road events |
| Amsterdam WIOR (works in public space) | DSO REST / GeoJSON | `api.data.amsterdam.nl/v1/wior/wior/` | 200, 20 MB (page 1 of 2) | 10,063 projects; 59 end today or later | start and end date (day only) | polygons | 404 | "public" | ASK_PERMISSION; stale since 2024, not worth asking |
| Amsterdam events | DSO REST / GeoJSON | `api.data.amsterdam.nl/v1/evenementen/evenementen/` | 200, 80 KB | 66, all 2021-09-24 to 2022-12-24 | start and end date; times on 35 | points | 404 | "public" | ASK_PERMISSION; stale |
| Amsterdam coach roadworks | DSO REST / GeoJSON | `api.data.amsterdam.nl/v1/touringcars/wegwerkzaamheden/` | 200, 7 KB | 11 street names | none | lines | 404 | none stated | ASK_PERMISSION; no dates, unusable |
| Amsterdam open geodata | map layer index | `maps.amsterdam.nl/open_geodata/` | 200 | no works or events layer | — | — | allows all | — | nothing to connect |
| Hilversum "Wegwerkzaamheden en evenementen" | ArcGIS FeatureServer | `services-eu1.arcgis.com/YcscSJ1XstO6iVhP/arcgis/rest/services/Wegwerkzaamheden_en_evenementen/FeatureServer` | 200 | 49 notices, 63 restriction lines, 28 diversion lines | start and end on all | points and lines | 403 "Invalid URL" (treated as none) | CC BY 4.0 (data.overheid.nl) | PERMITTED; Melvin copy, 44 of 49 already in NDW |
| Nijmegen "Wegwerkzaamheden" | catalogue entry | `data.overheid.nl/dataset/odn-wegwerkzaamheden` | 200 (catalogue) | only links `melvin.ndw.nu/public?branding=ge` | — | — | — | CC BY 4.0 | not a feed (Melvin viewer) |
| Melvin public viewer | Angular web app | `melvin.ndw.nu/public` | 200 | no documented API | — | — | robots.txt path returns the app HTML (no rules) | none found | ASK_PERMISSION; not needed, its data reaches NDW |
| Nijmegen events | JSON | `open.nijmegen.nl/eapi/nijmegen/dwh/open-dataportaal/evenementen?formaat=json` | 200; download stopped at REI's 50 MB cap | 169,432 objects read, 2,011 unique | start and end date-times | street name only | empty file (no rules) | dataset CC BY-NC 4.0; files CC BY 4.0 | RESTRICTED (NC); also stale (latest start 2025-12-19) |
| Den Haag events (permits) | Opendatasoft | `den-haag-opendata.opendatasoft.com/explore/dataset/evenementendenhaag/` | 200 (metadata only) | 22,309 permits; modified 2026-05-13 | start; end as text | point and shape | `Disallow: /api/` | CC0 (dataset), CC BY 4.0 (files) | RESTRICTED (robots) |
| Den Haag data platform | — | `denhaag.dataplatform.nl` | timeout | — | — | — | no answer | — | not reachable |
| Utrecht events 2026, street parties 2026 | XLSX | `open.utrecht.nl/sites/default/files/open-data/…` | 403 | not read | per catalogue: dates, times, build-up, tear-down | per catalogue: location text | 403 | CC0 (data.overheid.nl) | blocked; not verified |
| Rotterdam (old portal) | — | `rotterdamopendata.nl` | 200 "Shared IP" placeholder; API 404 | — | — | — | comments only, no rules | — | defunct |
| Rotterdam (data.rotterdam.nl) | Opendatasoft | `data.rotterdam.nl` | 200 (sitemap) | 1,434 assets, none on works, closures or events | — | — | `Disallow: /api/` | — | RESTRICTED (robots); nothing relevant |
| Eindhoven (data.eindhoven.nl) | Opendatasoft | `data.eindhoven.nl` | 200 (sitemap) | 138 datasets, none on works, closures or events | — | — | `Disallow: /api/` | — | RESTRICTED (robots); nothing relevant |
| Traffic decisions, all authorities (KOOP) | SRU XML | `zoekdienst.overheid.nl/sru/Search` | 200 | 314 decisions modified on or after 20 Oct; 1 in 50 is a temporary measure | publication date only | none in the metadata | 404 (none); `repository.overheid.nl`: `Disallow: /` | CC0 (KOOP) | metadata PERMITTED but low value; full documents RESTRICTED (robots) |
| Gelderland "Werkbare uren wegwerkzaamheden" | WFS | `geoserver.gelderland.nl/geoserver/ngr_bow/wfs` | not fetched | — | — | — | — | licence unknown | not road events (allowed working hours per road section) |
| ANWB, TomTom, HERE, Waze, Google, Be-Mobile/Flitsmeister | commercial | — | not fetched | — | — | — | — | commercial | not open |

## NDW: every file on opendata.ndw.nu

The directory listing at `https://opendata.ndw.nu/` (HTTP 200) showed 31 files
on 22 October 2026 at 12:43 CEST. The page also announces that the DATEX II
v2.3 traffic-flow files stop on 9 February 2027; this does not touch the
situation feeds.

| File | Size | What it is | Fetched |
| --- | --- | --- | --- |
| `actueel_beeld.xml.gz` | 403K | current picture (connected) | yes, for overlap |
| `planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz` | 16M | planned works and events (connected) | yes, for overlap |
| `planningsfeed_brugopeningen.xml.gz` | 123K | bridge openings, forecast and in progress | yes |
| `tijdelijke_verkeersmaatregelen_afsluitingen.xml.gz` | 234K | closures in force | yes |
| `tijdelijke_verkeersmaatregelen_maximum_snelheden.xml.gz` | 25K | temporary speed limits in force | yes |
| `veiligheidsgerelateerde_berichten_srti.xml.gz` | 28K | safety-related messages (SRTI) | yes |
| `emissiezones.xml.gz` | 145K | low- and zero-emission zones | yes |
| `dynamische_route_informatie_paneel.xml.gz` | 579K | variable message signs (DRIP) | yes |
| `Matrixsignaalinformatie.xml.gz`, `ndw_msi_shapefiles_latest.zip` | 1.0M, 1.0M | motorway lane signal states and their locations | no: lane signals, not events |
| `measurement*.xml.gz`, `trafficspeed.xml.gz`, `traveltime.xml.gz`, `reistijden_*`, `snelheden_en_intensiteiten_*`, `ndw_avg_meetlocaties_shapefile.zip` | 1–68M | traffic flow, speeds, travel times and their sites | no: traffic flow |
| `verkeersborden_actueel_beeld*.csv.gz/.geojson.gz` | 228–236M | national traffic-sign register | no: static signs |
| `charging_point_*` | 4–17M | EV charging points and tariffs | no |
| `Truckparking_Parking_Status.xml`, `Truckparking_Parking_Table.xml` | 18K, 49K | truck parking occupancy | no |
| `VILD6.13.A.zip`, `VILD6.14.A.zip` | 40M each | ALERT-C location tables | no: reference data |

**Update frequency:** the `Last-Modified` headers show that the situation files
are rebuilt every minute (10:44:10 UTC on all of them at 10:44). The planned
feed was rebuilt at 10:30:10. Emission zones are rebuilt once a day, at 04:10
UTC.

NDW's product page `https://docs.ndw.nu/producten/situatieberichten-v3/`
(updated 6 February 2026) lists what each feed contains. For the current
picture it says:

> "Alle gegevens uit Veiligheidsgerelateerde informatie ( SRTI ) / Alle
> gegevens uit Planningsfeed Wegwerkzaamheden & Evenementen / Alle gegevens uit
> Tijdelijke verkeersmaatregelen - Afsluitingen / Alle gegevens uit Tijdelijke
> verkeersmaatregelen - Maximum snelheden"

For the bridge feed it says: "Planningen en actuele brugopeningen met impact op
het wegverkeer".

### Overlap with the two connected feeds (measured)

Source files: `nl-research\analysis\*.summary.json`, made with
`nl-scripts\overlap.py`.

- **Current picture today:** 1,189 situations and 1,492 records.
  - 897 situations are planned works now in force; the connector skips them.
    Of their 1,187 `situationRecordCreationReference` values, 1,186 resolve to
    a record in the planned feed.
  - The connector keeps 292 situations: VehicleObstruction 187, lane or road
    management 38, GeneralObstruction 32, bridge openings 24, AbnormalTraffic
    16, Accident 8.
- **Planned feed today:** 15,020 situations and 64,233 records.
  - By supplier: NDW03 11,399, RWS01 2,059, AND01 1,562.
  - 374 distinct sources. 5,854 current, 8,294 upcoming, 872 ended.
- **Closures file:** 800 situations.
  - 799 have the same id and version time as in the current picture.
  - 759 are planned measures (every record made from a planned-feed record).
  - The 41 that are not planned measures are bridge openings (24) and
    unplanned closures (NLRWS 16, NDW14 1). All are in the current picture
    except `NLRWS_0005421208`, an accident closure started on 11 September
    2026 that is no longer in the current picture.
- **Speed-limit file:** 103 situations, all RWS01 `_WWA` copies of planned-feed
  records, all in the current picture.
- **SRTI file:** 227 situations, all in the current picture (226 with the same
  version time).
  - The current connector already keeps them: they are not planned measures.
  - By prefix: NDW06 175 ("NDW"), NDW08 27 ("RoadSafetyServices"), TSN01 24
    ("TSNED TrafficServiceTrack"), NLRWS 1.
  - None states an end, so REI's display rules hide them as unconfirmed.
- **Bridge-openings file:** 1,657 situations.
  - The 24 in progress (`probabilityOfOccurrence = certain`, no end) are the 24
    bridge openings in the current picture: same ids, same version times.
  - The 1,633 forecasts are not in either connected feed. No planned-feed
    record uses any of the 80 bridge points.

### planningsfeed_brugopeningen (planned bridge openings)

- `GET https://opendata.ndw.nu/planningsfeed_brugopeningen.xml.gz`: HTTP 200,
  126,257 bytes, `application/xml`. Sample: `nl-research\ndw\`.
- 1,657 situations, one `GeneralNetworkManagement` record each, all
  `generalNetworkManagementType = bridgeSwingInOperation`.
- **Suppliers:** BMS01 1,635, MOS01 18, ODS01 4. NDW's FAQ
  (`docs.ndw.nu/faq/brugopeningen/`) says the data comes from "Lora-sensoren
  (MobilitySensing, SkyLab) en ODS", and that planned openings come from BMS
  through BGV.
- **Forecasts:** 1,633 records with `probabilityOfOccurrence = riskOf`, each
  with a start and an end exactly 6 minutes apart.
- **In progress:** 24 records with `certain`, a start, and no end.
- **Window:** starts from 2026-10-13T17:56Z to 2026-10-23T10:43Z. 37
  situations start before 22 October and are stale leftovers. The rest cover
  the next 24 hours: 939 on 22 October and 681 on 23 October up to 10:43 UTC.
  - At analysis time: 41 current, 1,578 upcoming, 38 ended.
- **Location:** `PointLocation` with an ISRS ("RIS-index") code such as
  `NLDHR002350463400001` and WGS 84 coordinates. 80 distinct bridges, about 20
  openings per bridge per day. No bridge name, road name or comment.
- **Value to REI: noise.**
  - About 1,600 six-minute events a day at 80 points would bury real events.
  - The forecasts are probabilities (`riskOf`), not announcements.
  - The openings in progress are already read by the current-picture
    connector.
  - **If REI ever wants a bridge layer,** keep only `certain` records (already
    in the current picture) and never create an event per forecast.
- **Licence:** NDW's CC0 statement (see below). PERMITTED.

### tijdelijke_verkeersmaatregelen_afsluitingen (closures)

- HTTP 200, 240,424 bytes. 800 situations and 946 records.
  - **Record types:** RoadOrCarriagewayOrLaneManagement 849 (carriagewayClosures
    711, laneClosures 123, roadClosed 9, useOfSpecifiedLanesOrCarriagewaysAllowed
    6), ReroutingManagement 73, GeneralNetworkManagement 24 (bridge openings).
  - **Causes:** roadMaintenance 880, constructionWork 22, other 13,
    publicEvent 3, accident 3.
- **Prefixes:** NDW18 613 (municipal and provincial Melvin measures), RWS01 146,
  MOS01 18, NLRWS 16, ODS01 4, BMS01 2, NDW14 1. 169 distinct sources.
- **Dates:** start on all 800; end on 760. Starts range from 2024-06-28 to
  today; ends up to 2031-07-01.
- **Location:** `LinearLocation`, `ItineraryByIndexedLocations`,
  `SingleRoadLinearLocation`, `PointLocation`. 799 of 800 situations have
  coordinates.
- **Value:** none beyond the current picture. NDW's product page describes it
  as "tijdelijke brug-, weg-, rijbaan of rijstrook afsluitingen". Useful only as
  a lighter (240 KB) alternative to the current picture if REI ever wanted
  closures alone.

### tijdelijke_verkeersmaatregelen_maximum_snelheden (temporary speed limits)

- HTTP 200, 25,539 bytes.
- 103 `SpeedManagement` records (`speedRestrictionInOperation`), all with cause
  `roadMaintenance`. All are Rijkswaterstaat (16 districts), and all are copies
  of planned-feed records (`situationRecordCreationReference` RWS01_…).
- **Dates:** start on all; end on 98. **Location:** lines on all.
- **Value:** none. These are the speed limits of works REI already has from the
  planned feed.

### veiligheidsgerelateerde_berichten_srti (safety-related messages)

- HTTP 200, 28,279 bytes. 227 situations, all `safetyRelatedMessage = true`.
  - **Record types:** VehicleObstruction 187 (vehicleObstructionType `other` 176,
    `brokenDownVehicle` 11), GeneralObstruction 32 (`objectOnTheRoad` 5),
    Accident 8.
  - Comments are short, such as "Pijlwagen" (an arrow-board vehicle).
- **Dates:** start on all (earliest 2026-10-01); end on none.
  **Location:** points on 226, line on 1.
- NDW says the feed "heeft alleen betrekking op Rijkswegen" (national roads
  only). It is also delivered under the EU safety-related traffic information
  rules.
- **Value:** none beyond the current picture, which already holds and keeps
  them.

### emissiezones (emission zones)

- HTTP 200, 148,238 bytes. A `cz:ControlledZoneTablePublication` with 42
  `urbanVehicleAccessRegulation` entries, all `lowEmissionZone`, all `active`.
  - Examples: "ZE Amsterdam", "Milieuzone Amsterdam", "LEZ Rotterdam
    Maasvlakte", "ZE Den Haag", "ZE Utrecht".
- Each zone has a GML multipolygon and a traffic-regulation order id (for
  example `gmb-2024-198332`).
- Validity start dates run from 2020-01-01 to 2030-01-01; 37 of the 42 zones
  also state an end.
- **Value:** permanent access rules, not road events. It could become a static
  "restriction zones" map layer some day. PERMITTED (CC0).

### dynamische_route_informatie_paneel (DRIP variable message signs)

- HTTP 200, 593,494 bytes. A VMS table and status publication: 686 sign
  controllers with 1,372 signs and 1,196 current messages.
  - 540 of the messages are images (`imageData`).
  - 471 are text lines, 426 of them empty.
- Text seen: "A27 dicht ri Utrecht", "N325 dicht ri Kleve", "23 okt 22 h - 26
  okt 5 h", plus travel-time and campaign texts ("nietvoorniX.nl").
- **Value:** none.
  - The texts are a display of events NDW already publishes as situations.
  - They have no structured period.
  - The images fall under NDW's "Uitzondering voor beeld": CC0 does not apply
    to images.

### Not on opendata.ndw.nu

- `docs.ndw.nu/robots.txt` disallows the documentation of an "actueel beeld
  gevalideerd" (validated current picture) product. That product is not in the
  open listing and was not looked at.
- The documentation also mentions a "Vooraankondiging wegwerkzaamheden en
  evenementen" (advance notice of works and events) and the NCIS bridge
  service. NCIS needs an account through the NDW Servicedesk. Neither is open
  data.
- Dexter (`dexter.ndw.nu/opendata`) holds historical data, including historical
  bridge openings. It is not a live source.

## Municipal sources

### Amsterdam (api.data.amsterdam.nl)

- **robots.txt:** 404, so no rules.
- **Catalogue:** `GET https://api.data.amsterdam.nl/v1/?format=json` (redirected
  to `/v1`, HTTP 200, 173,723 bytes) lists 123 datasets.
  - Searched for werk, weg, verkeer, evene, hinder, afsluit, omleid, stremm,
    bereik, tvm, wior, moor, brug, vergunn.
  - Road-event candidates: `wior`, `evenementen`, `touringcars`.
  - Also present: `milieuzones2025` and `uitstootvrijeZones` (zones),
    `wegenbestand` (road register) and `vergunningen` (permits, licence null,
    not fetched).
- **API key notice** on every dataset documentation page
  (`https://api.data.amsterdam.nl/v1/docs/datasets/wior.html`):
  > "Het Dataplatform van gemeente Amsterdam gaat het gebruik van een API key
  > bij het gebruik van API's verplicht stellen. … Het gebruik van een API key
  > bij de aanroep van een API van het Dataplatform van gemeente Amsterdam is
  > vanaf half september optioneel. In overleg met de dataorganisatie wordt een
  > deadline vastgesteld voor het moment vanaf wanneer de API keys verplicht
  > worden."

  The OpenAPI documents describe the `X-Api-Key` header as "Api Key for
  statistical purposes, not for authentication". A key is requested through a
  form; none was requested.
- **Licence:** the catalogue gives `terms_of_use.license: "public"` for `wior`
  and `evenementen`, and `null` for `touringcars`. The documentation page says
  "Autorisatie: Geen; dit is openbare data. Licentie: public". The OpenAPI
  `info.license.name` is "public", with `termsOfService:
  https://data.amsterdam.nl/`.
  - "public" means open to read. It is not a reuse licence, so the verdict is
    ASK_PERMISSION.
  - The terms page at data.amsterdam.nl was not read.

**`wior` (Werken in de openbare ruimte):**
- **Requests:**
  - `GET https://api.data.amsterdam.nl/v1/wior/wior/?_format=geojson&_pageSize=10000`:
    HTTP 200, 20.3 MB, 10,000 features plus a `next` link.
  - Counts: `?_count=true&_pageSize=1` gives 10,063 in total, and adding
    `datumEindeUitvoering[gte]=2026-10-22` gives **59**.
- **Fields:** `wiorNummer`, `projectnaam`, `beschrijving`,
  `datumStartUitvoering` and `datumEindeUitvoering` (dates without times),
  `periodeGeplandeUitvoering`, `hoofdstatus` (Uitvoering 7,701, Projectaanpak
  1,882, Ontwerp 414), `typeWerkzaamheden`. The source system is named as
  "Victor".
- **Geometry:** Polygon 8,705, MultiPolygon 1,294, Point 1 (CRS84).
- **Stale.** The 10,000-feature page is ordered by UUID, so it is a random
  sample, and it shows:
  - WIOR numbers W20–W24 only (W24 1,114, nothing later);
  - start years 2021 1,786, 2022 1,767, 2023 3,485, 2024 2,471, 2025 47,
    2026 10.
  - The register stopped receiving new projects in 2024.
- **Content:** mostly cable, pipe and building works (Aansluiten, Aanleggen,
  Vervanging, Storing). Polygons are work areas, not closures.
- **Verdict:** ASK_PERMISSION, and not worth asking while the data is frozen.

**`evenementen`:**
- `GET https://api.data.amsterdam.nl/v1/evenementen/evenementen/?_format=geojson&_pageSize=5000`:
  HTTP 200, 80 KB.
- 66 events, all between 2021-09-24 and 2022-12-24 (exhibitions and similar).
  Points, links to `evenementen.amsterdam.nl`.
- **Verdict:** stale; not usable.

**`touringcars/wegwerkzaamheden`:**
- `GET https://api.data.amsterdam.nl/v1/touringcars/wegwerkzaamheden/?_format=geojson&_pageSize=5000`:
  HTTP 200, 6.7 KB.
- 11 lines with only a description (for example "Weesperstraat",
  "invalswegen / tunnels"). No dates.
- **Verdict:** not usable.

**maps.amsterdam.nl/open_geodata:**
- robots.txt says `User-agent: * / Disallow:` (everything allowed).
- The index page (HTTP 200) has no layer on works, closures or events. Its
  "Verkeer & Infrastructuur" layers are traffic-information systems, traffic
  lights, slow-traffic monitoring and traffic forecasts.

**Amsterdam in NDW:** Gemeente Amsterdam has 92 situations in the planned
feed, plus 1 each for Deelgemeente Amsterdam Zuid and Oost, and none of them
are events. For a city of Amsterdam's size this is low next to Rotterdam's 722.
REI has no open way to fill that gap today. Worth asking `datapunt@amsterdam.nl`
whether WIOR will be refreshed, and where Amsterdam's current works and closures
are published.

### Hilversum (ArcGIS, CC BY 4.0)

- **Catalogue:** data.overheid.nl dataset
  `hilversum-agol-wegwerkzaamheden-en-evenementen`, "Wegwerkzaamheden en
  evenementen".
  - Licence `http://creativecommons.org/licenses/by/4.0/deed.nl` on the dataset
    and every resource.
  - Frequency DAILY, modified 2026-07-06.
- **robots.txt:** `services-eu1.arcgis.com/robots.txt` answered HTTP 403 with
  "Invalid URL", treated as no robots file. `www.arcgis.com/robots.txt` says
  `User-agent: *` with no Disallow.
- **Requests:**
  - `GET …/FeatureServer?f=json`: three layers. 0 "Beperkingen" (polylines),
    1 "Meldingen" (points), 2 "Omleidingen" (polylines). `maxRecordCount`
    2000, query format JSON.
  - `GET …/FeatureServer/{0,1,2}/query?where=1%3D1&outFields=*&outSR=4326&f=json`:
    49 notices, 63 restriction lines, 28 diversion lines. All HTTP 200.
  - `GET https://www.arcgis.com/sharing/rest/content/items/36f8d8f62b4a4468b4556f44a92f6f81?f=json`:
    owner `MyCity_Hilversum`.
    - Snippet: "Beperkingen, meldingen en omleidingen o.b.v. het Melvin
      meldsysteem". Description: "Bron: MELVIN … Updatefrequentie van de
      data: Dagelijks".
    - `licenseInfo` links to `https://open-hilversum.hub.arcgis.com/pages/proclaimer`.
      That page was not read.
- **Notice fields:** `ID` (the Melvin id), `INFRA_BEHEERDER`, `WORKTYPE`,
  `IMPACTDESCRIPTION` (for example "Weg dicht in beide richtingen" 16,
  "Snelheidsbeperking" 5), `DELAY`, `IMPACT`, `STARTDATE`, `ENDDATE`,
  `LOCATION_ROAD`, `UITVOERPERIODE`, `EXTRA_REMARKS`, `EXTRA_CONTACTINFO`.
  - `EXTRA_CONTACTINFO` is filled on 36 of 49 notices with names and e-mail
    addresses.
  - Restriction and diversion lines carry `MELDING_ID` and `DIRECTION` (for
    example "Afsluiting in beide richtingen").
- **Dates:** start and end on all 49. 23 current, 26 upcoming; starts from
  2025-08-28, ends up to 2030-09-30.
  - **Time-zone trap:** the epoch values equal the local times written in
    `UITVOERPERIODE`, for example "van 2026-10-19 07:00" stored as 07:00 UTC.
    They are Dutch wall-clock times labelled as UTC.
- **Overlap:** 44 of the 49 notice ids appear as `NDW03_<id>` situations in
  NDW's planned feed (Hilversum has 53 there).
  - The 5 not in NDW: 532365 Diependaalselaan, 618795 Larenseweg, 621944
    Seinstraat, 632378 Kapittelweg, 637131 Willibrorduslaan.
  - Presumably Melvin notices not (yet) released to NDW.
- **Verdict:** PERMITTED (CC BY 4.0; the proclaimer was not read). It adds about
  5 events for one municipality and carries personal contact details. Low
  value.

### Nijmegen

- **Roadworks:** the data.overheid.nl dataset `odn-wegwerkzaamheden` ("current
  and planned roadworks … in the province of Gelderland", CC BY 4.0) has one
  resource: `https://melvin.ndw.nu/public?branding=ge`, the Melvin map with
  Gelderland branding. There is no data file. Melvin is already in NDW.
- **Events:** the data.overheid.nl dataset `odn-evenementen` gives the dataset
  licence `https://creativecommons.org/licenses/by-nc/4.0/deed.nl` and the
  resource licence CC BY 4.0.
  - **robots.txt:** `open.nijmegen.nl/robots.txt` is HTTP 200 with an empty
    body, so no rules.
  - `GET https://open.nijmegen.nl/eapi/nijmegen/dwh/open-dataportaal/evenementen?formaat=json`:
    HTTP 200. REI's download stopped at its 50 MB cap; the full size is not
    known.
  - The 50 MB read held 169,432 JSON objects but only 2,011 unique ones: the
    response repeats records.
  - Fields: `TITEL`, `STRAAT`, `BEZOEKERS`, `DD_EVENEMENT_START`,
    `DD_EVENEMENT_EINDE`, `SOORT`, `STATUS`, `CLASSIFICATIE`. Street name
    only, no coordinates.
  - Starts run from 2021-12-17 to 2025-12-19; none is upcoming. The metadata
    was last modified on 2024-03-05.
  - **Verdict:** RESTRICTED. The dataset-level licence is non-commercial, and
    the file-level CC BY 4.0 conflicts with it. The data is also stale.

### Den Haag

- `denhaag.dataplatform.nl`: the connection timed out (robots.txt request);
  nothing else was tried.
- **Events:** the data.overheid.nl dataset `evenementendenhaag` ("Evenementen
  Den Haag", CC0 on the dataset, CC BY 4.0 on the files) points to
  `den-haag-opendata.opendatasoft.com`.
  - That host's robots.txt says `User-agent: *` … `Disallow: /api/`; only
    Googlebot may use `/api/`, and not its exports.
  - **Rule breach:** one metadata request to
    `/api/explore/v2.1/catalog/datasets/evenementendenhaag` went out in the
    same step as the robots.txt request, before its rules were read. Nothing
    more was requested from that host.
  - What that request showed: 22,309 records, modified 2026-05-13. Fields
    `dossiernr`, `registr_oms`, `lokatie`, `ingangsdatum` (date-time),
    `einddatum` (text), `straat`, `huisnr`, `bezoekersaantal`, plus a point
    and a shape.
  - **Verdict:** RESTRICTED (robots.txt).
- No Den Haag roadworks dataset was found. Den Haag's works reach NDW through
  Melvin: 227 situations, 11 of them events.

### Utrecht

- data.overheid.nl lists CC0 datasets from Gemeente Utrecht, all modified on
  2026-10-05:
  - "Evenementen 2026": every event-permit application, with "de start en het
    einde van de opbouw en afbouw, de datum, begin- en eindtijd, de naam en
    locatie van het evenement".
  - "Meldingen straatfeest 2026" (street parties).
  - "Evenementenkalender 2026" and "Reserveringskalender 2026".
- The files are XLSX on `open.utrecht.nl`.
  - `https://open.utrecht.nl/robots.txt` answered HTTP 403.
  - One try at
    `https://open.utrecht.nl/sites/default/files/open-data/10-19-overzicht-aanvragen-evenementenvergunning-2026.xlsx`
    also answered HTTP 403.
  - Recorded as blocked; not retried.
- **Verdict:** not verified. The licence would allow it (CC0), but the content
  was not seen.
  - These lists could add event closures that NDW lacks: Utrecht has 404
    planned-feed situations but only 13 events.
  - The location is text (no geometry stated).
  - Asking Utrecht for access for REI's User-Agent is the next step.
- Utrecht city's roadworks are in Melvin. Provincie Utrecht and its
  municipalities use LTC, and their works reach NDW under `AND01_`.

### Rotterdam

- `rotterdamopendata.nl` is defunct.
  - Its robots.txt (HTTP 200, behind Cloudflare) is only Cloudflare's
    content-signal comment block, with no rules and no signals set.
  - `/api/3/action/package_search` answered HTTP 404, and the home page is a
    "Shared IP" placeholder.
- The current portal is `data.rotterdam.nl` (Opendatasoft). Its robots.txt says
  `Disallow: /api/` for every agent but Googlebot.
- Its sitemap (allowed; HTTP 200) lists 1,434 assets. None is about works,
  closures, diversions or events; the only match is a survey figure on festival
  attendance.
- **Verdict:** RESTRICTED (robots.txt), and nothing relevant. Rotterdam's
  works reach NDW through Melvin: 722 situations, 15 events.

### Eindhoven

- `data.eindhoven.nl` (Opendatasoft): robots.txt says `Disallow: /api/` for
  every agent but Googlebot.
- The sitemap (allowed; HTTP 200) lists 138 datasets, none on works, closures
  or events. The nearest are `ndw-verkeersborden-eindhoven` and
  `locaties-verkeerlichten`, both static.
- **Verdict:** RESTRICTED (robots.txt), and nothing relevant. Eindhoven's
  works reach NDW through Melvin: 267 situations, 20 events.

### data.overheid.nl searches

- **robots.txt:** allows `/data/api/`, with `Crawl-delay: 10`.
- **Searches** (`/data/api/3/action/package_search`):
  - `wegwerkzaamheden`: 5 results;
  - `afsluitingen`: 46;
  - `werkzaamheden`: 929, of which 200 were read;
  - `evenementen`: 46;
  - `verkeersmaatregelen`: 2.
  - Two queries with `OR` returned 0 results; CKAN did not accept that syntax.
- **Road-relevant results not covered above:**
  - Amsterdam, "Parkeervakken reservering als onderdeel van Tijdelijke
    Verkeersmaatregelen" (CC0, last modified 2019-03-01): parking bays, stale.
  - Gelderland, "Wegen- Werkbare uren wegwerkzaamheden" (licence unknown,
    WFS): allowed working hours per road section, not events. Not fetched.
  - Delft, "Evenementen locaties Delft" (CC BY 4.0): fixed event sites, not
    events. Not fetched.
  - RDW, "Open Data Parkeren: SPECIALE DAG": parking tariffs, not events.
  - KOOP, "Verkeersbesluiten in de Staatscourant": below.

## National and provincial sources

### Rijkswaterstaat

No separate open road-event feed exists:
- Rijkswaterstaat's districts publish through NDW: `RWS01_` in the planned
  feed, and `NLRWS_` and `RWS10_` in the current picture.
- The Rijkswaterstaat datasets on data.overheid.nl are network and condition
  data, for example the Wegkenmerkendatabase (CC0) and Staat van de
  Infrastructuur.
- The roadworks planning pages on rijkswaterstaat.nl are web pages that say
  they hold only the larger works.

### Provinces

- Provincial roadworks are in Melvin and so in NDW's planned feed: Provincie
  Zuid-Holland 335 situations, Noord-Holland 146, Groningen 115, Overijssel,
  Limburg, Gelderland and others.
- Provincie Utrecht uses LTC; its works reach NDW under `AND01_`.
- No province publishes its own open closure feed outside Melvin. The only
  provincial "works" dataset found, Gelderland's working hours, is not events.

### Traffic decisions (KOOP: Staatscourant, Gemeenteblad, Provinciaal blad)

- **Catalogue:** data.overheid.nl dataset `verkeersbesluiten-in-de-staatscourant`,
  publisher KOOP, licence `http://creativecommons.org/publicdomain/zero/1.0/deed.nl`.
  Its resource "Open data verkeersbesluiten" is `https://zoekdienst.overheid.nl/sru/Search`.
- **robots.txt:**
  - `zoekdienst.overheid.nl/robots.txt` is 404, so no rules.
  - `repository.overheid.nl/robots.txt`, the host of the full publications,
    says `User-agent: *` / `Disallow: /`.
- **Request:**
  `GET https://zoekdienst.overheid.nl/sru/Search?version=1.2&operation=searchRetrieve&x-connection=oep&query=dcterms.type="verkeersbesluit of -mededeling" and dcterms.modified>=2026-10-20&maximumRecords=50`
  (HTTP 200, 158,748 bytes). A first try with field `dt.type` returned the
  diagnostic "Invalid search field".
  - 314 decisions modified on or after 20 October 2026: about 100–125 a day,
    from every Dutch road authority.
  - In the 50-record page, by `overheidvb:typeverkeersbesluit`: "plaatsing of
    verwijdering van verkeerstekens" 37, physical measures 7, EV charging bays
    2, none 3, and 1 "tijdelijke verkeersmaatregel van kortere duur dan 4
    maanden". That one is "Tijdelijke verkeersmaatregel tijdens
    Sinterklaasintocht in het centrum van Nistelrode" (`gmb-2026-484515`).
  - The SRU metadata has no coordinates (`overheidop:idgeometrie` is empty)
    and no measure period.
  - Coordinates and dates sit in the full publication on
    `repository.overheid.nl`, which robots.txt closes to all agents. That was
    not fetched.
- **Verdict:**
  - Metadata: PERMITTED (CC0), but low value. Perhaps 2–3 temporary measures a
    day nationwide, as text, with no geometry.
  - Full documents: RESTRICTED (robots.txt), although the data is CC0.
  - Asking KOOP whether automated access to `repository.overheid.nl` is
    allowed would be needed before any use.

### Melvin

- `melvin.ndw.nu/robots.txt` returns the application's HTML, so there is no
  robots file. `/public` (HTTP 200) is an Angular single-page app.
- No public API is documented. NDW's FAQ describes Melvin as the registration
  system for road authorities and contractors, with accounts given out by
  province.
- Melvin's published output is NDW's planned feed, which REI already reads.
- **Verdict:** ASK_PERMISSION for any direct use (no terms found for the app's
  internal calls). Not needed.

## Licence: NDW (re-read today)

`https://www.ndw.nu/service/copyright` (HTTP 200; www.ndw.nu robots.txt has no
Disallow):

> "Tenzij anders vermeld is op de inhoud van deze website de Creative Commons
> Zero (CC0) verklaring van toepassing. Dit houdt in dat hergebruik van de
> inhoud van deze site is toegestaan, tenzij bij een bepaald onderdeel
> (bijvoorbeeld een document) staat aangegeven dat op dat onderdeel een
> auteursrechtelijke beperking van toepassing is."

> "Uitzondering voor beeld: Op foto's, video's, infographics en alle andere
> vormen van beeld is de CC0-verklaring niet van toepassing. … Daarnaast geldt
> dat bij het citeren van de inhoud niet de indruk gewekt mag worden dat NDW
> zonder meer de strekking van het afgeleide werk onderschrijft."

This covers every opendata.ndw.nu file above. The exception is the DRIP sign
images, which are images ("beeld").

## Recommended to connect

**No new Dutch source is recommended.** The two connected NDW feeds, read with
the current connector's rule that drops planned measures from the current
picture, already include everything the extra NDW files carry. Every municipal
source checked is stale, a Melvin copy, robots-restricted or blocked.

If the owner still wants to add something, these are the only PERMITTED
candidates, ranked by value. Neither is recommended.

1. **Hilversum Melvin layer (low value; optional).**
   - **Endpoint:** `GET https://services-eu1.arcgis.com/YcscSJ1XstO6iVhP/arcgis/rest/services/Wegwerkzaamheden_en_evenementen/FeatureServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=json`,
     joined to layers 0 and 2 on `MELDING_ID` = `ID`.
   - **Fields:** `ID`, `IMPACTDESCRIPTION`, `WORKTYPE`, `STARTDATE`, `ENDDATE`
     (local wall-clock time, see the trap above), `LOCATION_ROAD`,
     `UITVOERPERIODE`, restriction lines (layer 0) and diversion lines
     (layer 2).
   - **Mapping:** "Weg dicht in beide richtingen" / "Weg dicht in één richting"
     → PLANNED_ROAD_CLOSURE; "Verminderd aantal rijstroken beschikbaar" →
     LANE_RESTRICTION; otherwise ROAD_WORKS; layer 2 → TRAFFIC_DIVERSION
     geometry.
   - **Volume:** 49 notices in total, a few new per week.
   - **Filters:**
     - Drop every `ID` that already exists as `NDW03_<ID>` in the planned feed
       (44 of 49 today).
     - Drop `EXTRA_CONTACTINFO` and contact lines in `EXTRA_REMARKS`, as for
       NDW comments.
     - Attribution "Gemeente Hilversum, CC BY 4.0".
     - Read the proclaimer page before connecting.
2. **NDW planned bridge openings (not recommended as events).**
   - **Endpoint:** `GET https://opendata.ndw.nu/planningsfeed_brugopeningen.xml.gz`
     (the existing `datex3_nl_lu` reader parses it as is).
   - **Fields:** situation id, `probabilityOfOccurrence`,
     `overallStartTime`/`overallEndTime`, ISRS code, point.
   - **Mapping:** BRIDGE_TUNNEL_RESTRICTION.
   - **Volume:** about 1,600 forecast openings a day at 80 bridges, each 6
     minutes long.
   - **Filter:** keep only `probabilityOfOccurrence = certain`. That leaves the
     24 openings in progress, which the current-picture connector already
     has, so connecting adds nothing.
   - The forecasts belong in a separate bridge layer, if anywhere, never in
     the event list.

**Worth asking (ASK_PERMISSION or blocked, with possible value):**
- **Utrecht** (`open.utrecht.nl`, CC0 event permits and street parties, HTTP
  403 to REI). Ask Utrecht's open-data team to allow REI's User-Agent. The
  lists could add event closures; Utrecht has 13 events in NDW.
- **Den Haag** (`den-haag-opendata.opendatasoft.com`, 22,309 event permits).
  Ask for permission to use `/api/`, which robots.txt disallows.
- **Amsterdam** (`datapunt@amsterdam.nl`). Ask whether WIOR will be refreshed,
  what "license: public" allows, and where current works and closures are
  published. Amsterdam is under-represented in NDW.
- **KOOP.** Ask whether automated SRU and repository access is allowed for
  temporary traffic decisions.

## Not verified

- Hilversum's proclaimer page (`open-hilversum.hub.arcgis.com/pages/proclaimer`)
  and whether it adds conditions to CC BY 4.0.
- Amsterdam's terms page (`https://data.amsterdam.nl/`) and the date from which
  API keys become mandatory.
- The contents of Utrecht's event and street-party XLSX files (HTTP 403).
- Den Haag's data platform (`denhaag.dataplatform.nl`, timed out) and whether
  any Den Haag roadworks dataset exists there.
- The full size of the Nijmegen events response (stopped at 50 MB).
- NDW's "actueel beeld gevalideerd" product (documentation disallowed by
  robots.txt) and the "Vooraankondiging wegwerkzaamheden en evenementen".
- Groningen, Breda, Tilburg and other municipal portals were not searched one
  by one. Their works are in Melvin: Breda 1,330 records with 254 event
  situations, Groningen 241 situations.
- The NDW MSI, traffic-flow, sign, charging, truck-parking and VILD files were
  not downloaded, only judged from the listing and documentation.

## Requests made

68 requests in total, 22 October 2026, 10:43:45–11:09:20 UTC.
- **Results:** 60 × HTTP 200, 4 × 404, 3 × 403, 1 connection timeout.
- **Most on one host:** 10 (opendata.ndw.nu and api.data.amsterdam.nl).

| Host | Requests | Notes |
| --- | --- | --- |
| opendata.ndw.nu | 10 | robots.txt (404), listing, 8 files |
| api.data.amsterdam.nl | 10 | robots.txt (404), catalogue, 2 dataset OpenAPI documents, 1 doc page, 3 data downloads, 2 counts. The catalogue URL was redirected (`/v1/?format=json` → `/v1`); redirects were followed automatically. |
| data.overheid.nl | 9 | robots.txt, 7 searches, 1 dataset. The first search came 3 s after robots.txt, before its `Crawl-delay: 10` was read; the rest were 11 s or more apart. |
| docs.ndw.nu | 8 | robots.txt, 7 documentation pages (none disallowed) |
| services-eu1.arcgis.com | 5 | robots.txt (403), service metadata, 3 layer queries |
| zoekdienst.overheid.nl | 3 | robots.txt (404), 2 SRU queries |
| rotterdamopendata.nl | 3 | robots.txt, 1 API path (404), home page |
| www.ndw.nu | 2 | robots.txt, copyright page |
| www.arcgis.com | 2 | robots.txt, item metadata |
| open.utrecht.nl | 2 | robots.txt (403), 1 XLSX (403); stopped |
| open.nijmegen.nl | 2 | robots.txt (empty), events JSON (stopped at 50 MB) |
| melvin.ndw.nu | 2 | robots.txt (app HTML), `/public` |
| maps.amsterdam.nl | 2 | robots.txt, open-geodata index |
| den-haag-opendata.opendatasoft.com | 2 | robots.txt, 1 dataset metadata request to `/api/` (disallowed; sent before the rules were read; nothing more) |
| data.rotterdam.nl | 2 | robots.txt, sitemap |
| data.eindhoven.nl | 2 | robots.txt, sitemap |
| repository.overheid.nl | 1 | robots.txt only (`Disallow: /`) |
| denhaag.dataplatform.nl | 1 | robots.txt: connection timed out |

Web searches (a search engine, not the hosts) were used only to find candidate
datasets.
