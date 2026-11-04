# Sweden, Norway and Denmark: official road-event sources, 4 November 2026

The user asked for new countries and their sources. This note covers Sweden,
Norway and Denmark: the national road authorities and the open data of the
largest cities (Stockholm, Gothenburg, Malmö; Oslo, Bergen; Copenhagen,
Aarhus). It re-checks the research of 16 October 2026
(`europe-official-road-sources-2026-10-16.md`, rows DK/NO/SE and the
NEEDS_KEY notes), which had all three national authorities as NEEDS_KEY and
had not looked at the cities.

**Method.** Every candidate was fetched live on 4 November 2026 between 10:55
and 11:21 UTC with Python httpx and REI's User-Agent
`JSAN-REI/1.0 (road event intelligence; RSS reader)`. robots.txt was read
first on each host. No account, key, token or login was used or asked for; no
CAPTCHA or bot wall was met. Licence and documentation pages were read with a
web reader. Raw copies are outside the repo in the session scratchpad
(`…\scratchpad\nordic\raw\`).

Two slips, recorded as they happened:
- Open Data DK's catalogue API (`admin.opendata.dk`) took 8 search requests in
  about 30 s, more than the few per host intended (it has no robots.txt: the
  path redirects to a login page; `www.opendata.dk/robots.txt` allows all).
- Oslo's ArcGIS hub asks `Crawl-delay: 60`; one request followed its
  robots.txt about a second later (HTTP 400). Nothing more was sent there.

**Result.** Two sources are permitted, open and current, and are built:

| Country | Source id | Records fetched | Kept in a live dry run | Licence |
|---|---|---|---|---|
| Norway | `norway-vegvesen-datex-situations` | 2,395 records of 1,077 situations | 1,057 (1,055 with an end) | NLOD 2.0 |
| Denmark (Copenhagen) | `copenhagen-excavation-permits` | 2,994 shapes of 1,597 permits | 629 (all with an end) | CC BY 4.0 |

Sweden has no source that can be connected without a key.

## Request log

| UTC | Request | HTTP | What came back |
|---|---|---|---|
| 10:55:09 | `api.trafikinfo.trafikverket.se/robots.txt` | 404 | none |
| 10:55:10 | `datex-server-get-v3-1.atlas.vegvesen.no/robots.txt` | 401 | Basic/Bearer realm "Access to datex2/prod-1" |
| 10:55:12 | `nap.vd.dk/robots.txt` | 301 → 200 | the DU-portal's single-page app (no robots.txt) |
| 10:55:24 | `POST api.trafikinfo.trafikverket.se/v2/data.json` (Situation query, no key) | 401 | `"Invalid authentication"` |
| 10:55:26 | `…vegvesen.no/datexapi/GetSituation/pullsnapshotdata` | 401 | empty |
| 10:55:51 | `www.opendata.dk/robots.txt` | 200 | `User-agent: *` with no Disallow |
| 10:55:53 | `admin.opendata.dk/robots.txt` | 302 → login | no robots.txt |
| 10:55:55 | `data.norge.no/robots.txt` | 200 | Disallow `/api/` and `/*?` (so the catalogue was not searched) |
| 10:55:57 | `www.dataportal.se/robots.txt` | 200 | Allow `/` |
| 10:56:12–10:56:43 | `admin.opendata.dk/api/3/action/package_search` ×8 | 200 | road works, traffic, permits (Copenhagen, Aarhus, Vejle, Hedensted) |
| 10:56:54 | `wfs-kbhkort.kk.dk/robots.txt` | 404 | none |
| 10:56:56 | `mida.carto.com/robots.txt` | 200 | Disallow `/api/` for named search bots only |
| 10:57:00 | `kortservice.vejle.dk/robots.txt` | 404 | none |
| 10:57:08 | Copenhagen `gravetilladelser_aktiv_aabne` (GeoJSON) | 200 | 1,792,131 bytes, 2,994 features |
| 10:57:45 | Copenhagen `raaden_over_vej_events_anonym_aktuelt` (GeoJSON) | 200 | 11,826,207 bytes, 8,733 features |
| 10:58:40 | Aarhus CARTO table, schema only (`LIMIT 0`) | 200 | columns, no rows |
| 10:58:49 | Aarhus CARTO table, counts and newest dates | 200 | 2 rows of aggregates |
| 11:01:37 | `ogckart-sn1.atlas.vegvesen.no/robots.txt` | 404 | none |
| 11:01:39 | `git.vegvesen.no/robots.txt` | 200 | empty |
| 11:01:40 | Vegvesen DATEX `3.1/wfs-wms/README.md`, `LICENSE.txt` | 200 | 83 KB; Apache 2.0 (for the specification code, not the data) |
| 11:02:00 | Vegvesen WFS `SituationSimple_v2` | 200 | 9,554,690 bytes, 2,394 features |
| 11:02:53 | `data.norge.no/nlod/en/2.0` | 200 | licence text |
| 11:05:42–11:06:13 | `openstreetgs.stockholm.se` robots.txt, `/Home/Data`, `/Gs/` | 404, 200, 404 | dataset list |
| 11:06:24–11:06:34 | `data.goteborg.se` robots.txt, `/`, `/PublicWebservices.aspx` | 404, 200, 200 | service list |
| 11:07:10–11:07:21 | `opendata-api.malmo.se` robots.txt, `package_search` ×2 | login page, 200 | no road-event dataset |
| 11:07:45–11:07:58 | DU-portal robots.txt, `env.js`, distribution `/robots.txt` and `/api/` | 200, 200, 401, 401 | OAuth2 at `idp.vejdirektoratet.dk`; `WWW-Authenticate: Bearer` |
| 11:08:10–11:08:11 | `oslokommune-bym.opendata.arcgis.com` robots.txt, search | 200, 400 | Crawl-delay 60 (see slips) |
| 11:09:00 | `www.opendata.dk/city-of-copenhagen/gravetilladelser` | 200 | dataset page (licence not in the HTML) |
| 11:20:51 | Dry run: Vegvesen WFS | 200 | 2,395 records |
| 11:20:57 | Dry run: Copenhagen WFS | 200 | 2,994 shapes |

## Norway

### Statens vegvesen road traffic situations, WFS — PERMITTED, built

- **URL:** `https://ogckart-sn1.atlas.vegvesen.no/datex_3_1/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=datex_3_1:SituationSimple_v2&outputFormat=application/json`
- **Format and auth:** GeoJSON from a GeoServer (DATEX II 3.1 situations, one
  feature per situation record), WGS 84; no key. robots.txt: 404 (none).
- **What changed since 16 October:** the DATEX server still answers 401, but
  Statens vegvesen's own documentation says the same publication is open as a
  WFS: "NPRA publishes Datex II WFS/WMS pull services that are open available.
  We do encourage the consumer to identify themselves by sending an email to
  datex@vegvesen.no"
  (`git.vegvesen.no/projects/DATEX2/repos/datex2-spesifications/raw/3.1/wfs-wms/README.md`).
  The full layer `datex_3_1:Situation` holds "the same data as from SOAP/REST
  (Datex Server)"; the simplified `SituationSimple_v2` is used.
- **Licence:** NLOD. Statens vegvesen: "Informasjon i DATEX-format fra Statens
  vegvesen er gjort tilgjengelig under Norsk lisens for offentlige data"
  (<https://www.vegvesen.no/fag/teknologi/apne-data/et-utvalg-apne-data/hva-er-datex/bestille-tilgang-til-datex/>);
  the dataset lists "Norsk lisens for offentlige data (NLOD)"
  (<https://dataut.vegvesen.no/en/dataset/trafikkmeldinger>). NLOD 2.0 §2: the
  licensee "may use the information for any purpose and in all contexts"
  (<https://data.norge.no/nlod/en/2.0>). Attribution per NLOD §5: "Contains
  data under the Norwegian licence for Open Government data (NLOD) distributed
  by Statens vegvesen".
- **Conditions that come with DATEX access** (same page; treated as applying):
  credit Statens vegvesen ("skal den alltid oppgi Statens vegvesen som
  kilde"); **"Norske meldinger skal ikke oversettes til andre språk"** (do not
  translate the Norwegian messages); do not distort the information. REI keeps
  the Norwegian text as written and makes its English titles from the DATEX II
  codes only. If REI ever adds translation, these sources must be excluded.
- **Fetched:** 2,394 records of 1,075 situations (11:02), 2,395 of 1,077 in
  the dry run (11:20). Every record has a line or point and a start; 4 records
  (2 strong-wind closures) have no end. Types: MaintenanceWorks 997,
  RoadOrCarriagewayOrLaneManagement 538 (roadClosed 210), traffic lights or
  manual direction 447, speed limits 210, diversions 135, ferry notices 12,
  obstructions, an accident, events. Roads: county roads (Fv.) 678
  situations, national (Rv.) 115, European roads, and some municipal (Kv.) 19;
  37 situations in Oslo, 32 in Bergen.
- **Personal data:** none found (no phone numbers or e-mail addresses in the
  685 distinct description parts). A guard removes any line with a Norwegian
  phone number, an e-mail address or a contact word; it changes none of the
  685 parts. (The Dutch phone pattern of the shared DATEX reader took
  Norwegian dates such as "05.11.2026 08:00" for numbers, so it is not used.)
- **Dry run (11:20 UTC):** 1,077 situations → 12 ferry-only (not road events)
  → 1,065 records → 8 already ended → **1,057 kept**, all with geometry and a
  start, 1,055 with an end; 865 in force, 192 upcoming. Types: road works 734,
  planned closures 286, road hazards 11, emergency closures 8, lane
  restrictions 4, none 14 (9 winter closures, 4 weather closures, 1 weight
  limit: their words are kept, no type is invented).
- **Verdict:** PERMITTED, built (`connectors/official/norway_vegvesen.py`).

### Statens vegvesen DATEX server — NEEDS_KEY (not needed)

`datex-server-get-v3-1.atlas.vegvesen.no` still answers 401 (Basic or
Bearer). Access is ordered with a form on vegvesen.no asking for organisation,
organisation number, first and last name, e-mail, purpose and a comment; no
cost is stated. Not needed: the open WFS carries the same publication.

### Oslo and Bergen — NOT_A_SOURCE

No municipal road-event feed was found. Oslo's Bymiljøetaten ArcGIS hub has
road data such as one-way streets and speed limits (per an OpenStreetMap forum
post), but no works or closures layer showed in searches. Bergen's excavation
permit portal is for applicants only (per its help pages). Both
cities are covered by the national feed: national, county and some municipal
roads.

## Denmark

### Copenhagen excavation permits — PERMITTED, built

- **URL:** `https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:gravetilladelser_aktiv_aabne&outputFormat=json&SRSNAME=EPSG:4326`
- **Format and auth:** GeoJSON (WFS), WGS 84; no key. robots.txt: 404 (none).
- **Licence:** CC BY 4.0. Københavns Kommune's Open Data DK entry for the
  dataset states `license_id: CC-BY-4.0`, "Creative Commons Attribution 4.0",
  `license_url: https://creativecommons.org/licenses/by/4.0/`
  (<https://www.opendata.dk/city-of-copenhagen/gravetilladelser>, read
  through the catalogue API). Caveat: the rendered dataset page shows no
  licence text, and no current city-wide terms page was found (a 2013 terms
  PDF for another Copenhagen dataset, seen only in search results, said the
  city may change its terms).
  Questions: bydata@kk.dk.
- **Fetched:** 2,994 shapes (1,224 lines, 900 polygons, 870 points) of 1,597
  permits; all with first and last days (`29-06-26`) and daily hours; first
  days 2 December 2024 to 3 July 2028; none ended. Dug surfaces: pavement
  1,302 permits, carriageway 585, parking 269, cycle path 203, green areas 117.
- **Personal data:** the developer (`bygherre`) and contractor
  (`entreprenoer`) include private persons ("Lasse Karsholt", "… v/Jan Clausen
  Møller"): both fields are dropped before anything is stored. Fixtures carry
  placeholders.
- **What REI keeps:** one record per permit; only permits that dig the
  carriageway or a cycle path (642 of 1,597). Permits for pavement, parking or
  green areas only are not road events (as Málaga's parking-only cuts).
- **Dry run (11:20 UTC):** 1,597 permits → 955 not road events → 642 records
  → 13 starting more than a year ahead → **629 kept**, all with geometry, start
  and end; 491 in force, 138 upcoming. Geometry: 294 polygons, 26
  multipolygons, 167 lines, 31 multilines, 111 points.
- **Verdict:** PERMITTED (licence caveat above), built
  (`connectors/official/copenhagen_excavation.py`).

### Copenhagen use of road permits (råden over vej) — PERMITTED, not built

Same server, layer `raaden_over_vej_events_anonym_aktuelt`, CC BY 4.0 in its
Open Data DK entry, no key. 8,733 shapes: outdoor seating 2,818, temporary
road use (scaffolding, containers, huts) 2,859, excavations 2,390 (overlapping
the permits above), street trading 355, events 146, filming 97. 97 shapes are
flagged closed to car traffic (`veje_spaerret_for_biltrafik`). Mostly not road
events; a follow-up could take only the closures and events.

### Vejdirektoratet DU-portal (national access point) — NEEDS_KEY

`nap.vd.dk` redirects to a single-page app whose login is OAuth2 at
`idp.vejdirektoratet.dk`. The distribution service
`distribution.dataudveksler.app.vd.dk/api/` answered **401** with
`WWW-Authenticate: Bearer`. Datasets: 1208 "Road Works and Planned Events"
(snapshot, DATEX II, every 10 minutes, CC BY 4.0 per the 16 October reading),
1209 (its change feed), 222 (traffic messages), 1243 (Copenhagen roadworks).

### Aarhus excavation permits — NOT_A_SOURCE (stale)

Open Data DK lists a CC BY 4.0 GeoJSON from CARTO (`mida.carto.com`,
`vm_tilladelser_2`). The table stopped in 2018: newest start 29 July 2018,
last update 1 May 2018 (881 excavation and 205 equipment permits). It also
holds contact names and phone numbers. Only the schema and counts were read;
no rows.

### Not checked

Vejle publishes current excavation permits (ArcGIS, CC BY 4.0, "Ajourføres
dagligt"); not fetched (not one of the large cities).

## Sweden

### Trafikverket open API — NEEDS_KEY

`POST https://api.trafikinfo.trafikverket.se/v2/data.json` without a key:
**401** `{"ERROR":{"SOURCE":"Security","MESSAGE":"Invalid authentication"}}`.
robots.txt: 404. Licence: the API page links "Licens - senaste versionen" to
<https://creativecommons.org/publicdomain/zero/1.0/deed.sv> (CC0 1.0). How to
get access, from the API page: "Fyll nödvändiga uppgifter på
registreringssidan, då blir du kund hos Trafikverket", accept the API's
licence, verify the e-mail address. No cost or numeric limits are stated;
Trafikverket "will contact you" if traffic exceeds the documented limits.
Trafikverket's DATEX II service is registered the same way.

### Gothenburg — NEEDS_KEY

`data.goteborg.se/PublicWebservices.aspx` lists **TrafficInformation**
("Trafikpåverkan") and **StartPermissionService** ("Starttillstånd", permits
to start street works). Details and the key need a free account: register,
sign in, add an application under "Mina applikationer", and a key is made.
The city's statement: "Göteborgs Stads öppna data är fritt att använda, utan
avgifter eller licenser" (<https://goteborg.se/psidata>). Commercial use is
not named; confirm at registration.

### Stockholm — NOT_A_SOURCE (not published)

Trafikkontoret's open-data page (`openstreetgs.stockholm.se/Home/Data`) lists
"Gatuarbete - Schakt (ej publicerad i avvaktan på ny leverantör)" and
"Gatuarbete - Trafikanordningsplan (ej publicerad i avvaktan på ny
leverantör)": street works and traffic management plans are not published
while a new supplier is awaited. Its other layers are permanent traffic
regulations, parking and assets.

### Malmö — NOT_A_SOURCE

Malmö's CKAN (`opendata-api.malmo.se`) has no road works, closure or permit
dataset (19 "trafik" results: counts, parking, noise, statistics).

## What the user can do to get more data

- **Sweden (most needed):** register for Trafikverket's free API key at
  <https://data.trafikverket.se/get-started> (organisation details and e-mail;
  becomes a Trafikverket customer; accept the CC0 licence; verify the e-mail).
  The key then goes in REI's configuration as a secret, never in code. This
  gives national road situations for all of Sweden, Stockholm, Gothenburg and
  Malmö included. Optionally, register at <https://data.goteborg.se/> for
  Gothenburg's traffic impact and start permits, and ask
  support.digitalakanaler@goteborg.se to confirm commercial use.
- **Norway:** nothing is needed. Statens vegvesen asks consumers to identify
  themselves: a short e-mail to datex@vegvesen.no naming JSAN Road Event
  Intelligence would follow that request and get notice of changes. The
  simple v1 layers end during 2026; REI uses v2.
- **Denmark:** create a DU-portal profile at <https://nap.vd.dk/> and subscribe
  to datasets 1208 (road works and planned events), 222 (traffic messages)
  and 1243 (Copenhagen roadworks). REI would then need the bearer-token flow
  from `idp.vejdirektoratet.dk`. Optionally, ask bydata@kk.dk to confirm CC BY
  4.0 for the excavation permits.

## Update, 4 November 2026 (later): Sweden connected

The user registered with Trafikverket and gave the key (kept in `.env` as
`TRAFIKVERKET_API_KEY`, never in the repository). Verified with it: object type
`Situation` exists only in namespace `Road.TrafficInfo`, schema version 1.6 (1.4
and 1.5 refused). Unfiltered answer: 13.3 MB, 3,462 situations, 6,284 parts
(roadworks 3,333, traffic messages 2,837, obstructions 69, ferries 41,
accidents 4); every part with a start, 6,236 with a WGS 84 geometry (the rest
ferries); no phone number or e-mail in any message; creators Trafikverket and
municipalities. 2,070 situations had every part `Suspended`; with the filter
`NE Deviation.Suspended true` and the SWEREF 99 TM copies excluded: 4.8 MB,
1,391 situations. Connector: `connectors/official/trafikverket.py`; test
`tests/unit/test_trafikverket_situations.py` (fixture: seven real situations).
Ingested once locally: 1,329 events. Decision 0053.
