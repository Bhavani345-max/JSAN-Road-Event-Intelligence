# Estonia, Latvia, Poland, Ireland: official road-event sources, 4 November 2026

The user asked to add new countries "and their sources". This note covers
Estonia, Latvia, Poland and the Republic of Ireland. It re-checks the
16 October research (`europe-official-road-sources-2026-10-16.md`) and adds the
city portals of Tallinn, Tartu, Riga, Warsaw, Kraków, Gdańsk, Poznań, Wrocław,
Dublin and Cork.

**Result: no source in these four countries passed every check.** Nothing was
connected. The four countries are configured as country entries with no source
of their own (`packages/cities/data/{estonia,latvia,poland,ireland}.json`).
Each blocking issue is something the user can resolve: a free key, a licence
question, or a host that did not answer this machine. See "What the user can
do" below.

## Method

- **When:** 4 November 2026, 10:56 to 11:18 UTC.
- **User-Agent:** `JSAN-REI/1.0 (road event intelligence; RSS reader)`, with
  Python httpx from the project venv.
- **robots.txt first:** read before anything else on each host, and obeyed.
  A 404 meant no rules. An unreadable robots.txt (timeout, DNS failure) meant
  the host was not fetched.
- **Request limits:** requests to one host were sequential, at least 2.5 s
  apart, and never more than 8 per host. The busiest hosts had 7.
- **What was not done:** no logins, registrations, key sign-ups or CAPTCHAs,
  and no retries of blocked hosts (one retry of a timed-out host).
- **Request log:** 73 lines, kept outside the repo in the session scratchpad
  (`…\scratchpad\log.tsv`).
- **Web tools:** WebSearch was used for documentation. WebFetch was used for
  one news page (geoportal.gov.pl) and was refused by two hosts.
- **Personal data:** none was kept. The raw copy of Tartu's stages table had
  its contact names, phones and e-mails replaced by `[removed]`.

"Current" means started and not yet ended at fetch time. "Upcoming" means it
starts later.

## Summary

| Country | Source | Format | Auth | robots.txt | Licence | Records (4 Nov) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LV | National Access Point: Road works, Road closures, Lane closures, Short term road works, Accidents and incidents (`transportdata.gov.lv`) | DATEX II 3.4 XML, REST API or MQTT | registration and API key | allows all except `/textual` | CC0 1.0 (NAP terms) | not fetched (key) | **NEEDS_KEY** |
| EE | Tark Tee DATEX II gateway (`tarktee.ee/api/v1/datex/`) | DATEX II 2.3 and 3.6 | API key after staff review | 404 | terms read; commercial use not stated | not fetched (key) | **NEEDS_KEY** |
| EE | Tartu traffic restrictions (`gis.tartulv.ee/…/PI_liikluspiirangud_avaandmed/FeatureServer`) | ArcGIS REST JSON | none | 404 | hub item says licence "none" | 153 closed-road lines; 124 stages with start and end (76 current, 48 upcoming) | **ASK_PERMISSION** |
| PL | GDDKiA National Access Point (KPD, `kpd.gddkia.gov.pl`) | DATEX II 3.4 | registration and client certificates | 404 | terms page unreachable (DNS) | not fetched (key) | **NEEDS_KEY** |
| PL | GDDKiA obstructions XML (`archiwum.gddkia.gov.pl/dane/zima_html/utrdane.xml`) | XML | none | timed out twice | CC0 1.0 (dane.gov.pl) | none: host unreachable | UNREACHABLE |
| PL | Warsaw "Utrudnienia w ruchu drogowym" (`dane.um.warszawa.pl`) | JSON, updated daily | none | timed out | CC BY 4.0 (dane.gov.pl) | none: host unreachable | UNREACHABLE |
| PL | Wrocław open data (`opendata.cui.wroclaw.pl`) | CKAN | — | HTTP 403 | — | — | BLOCKED |
| PL | Gdańsk open data (`ckan.multimediagdansk.pl`) | CKAN | — | `/api/` disallowed | — | no road-event dataset | NOT_A_SOURCE |
| PL | Kraków, Poznań | — | — | — | — | no machine-readable dataset found | NOT_A_SOURCE |
| IE | TII Traffic (`traffic.tii.ie`) | single-page map, Google reCAPTCHA | — | `Disallow: /images/` only | none published | — | **ASK_PERMISSION** |
| IE | Dublin City Council current road closures | HTML with RDFa | none | allows the page | site terms unclear | 4 closures, all with point, start and end | **ASK_PERMISSION** |
| IE | Fingal "Road Closures Temporary FCC" | CSV (ArcGIS Hub) | none | Crawl-delay 60 (obeyed) | CC BY 4.0 | permits 2022 to 2024; last updated 20 Sep 2024; no geometry | NOT_A_SOURCE |
| IE | Cork City "Road Closures Database" | — | — | — | catalogue: "Open Data: No" | — | NOT_A_SOURCE |
| EE | Tallinn (`tallinn.ee`) | — | — | HTTP 403, Cloudflare challenge | — | — | BLOCKED |
| LV | Riga | — | — | — | — | no feed found; event maps and press releases only | NOT_A_SOURCE |

## Latvia

### National Access Point "Transports. Mobilitāte" (NEEDS_KEY)

- **What changed since October:** the October hosts are gone.
  `data.lvceli.lv/opendata/EN/RealtimeTraffic/` returns HTTP 404 (IIS "File or
  directory not found"), and the data.gov.lv dataset `celu-buvdarbi` returns
  404. LVC's road-event data now sits in the National Access Point (NAP) at
  `transportdata.gov.lv`, which LVC operates. The single data.gov.lv entry,
  `nacionala-piekluves-punkta-datu-kopas` (CC0-1.0), only links to NAP cards.
- **Catalogue:** `GET /en/public/dataset-search` lists 56 datasets. These are
  the road-event ones (card UUID, NAP node id):
  - Road works: `35fa5c41-90ce-4b74-a4a3-08216d470134`, nid 17977
  - Road closures: `75611a36-…`, nid 7300
  - Lane closures: `82e20567-…`, nid 7301
  - Short term road works: `aacdd187-…`, nid 847
  - Accidents and incidents: `e8659cdd-…`, nid 126
  - Unmanaged blockage of a road: `c05b9c53-…`
- **Road works metadata** (`GET /en/api/v1/metadata/data/35fa5c41-…`):
  - Format: DATEX II 3.4 `SituationPublication`, XML. Access interface
    "HTTP/HTTPS|MQTT"; communication method "Push"; distribution mode "Data
    change flow"; update frequency "Continuous".
  - Visibility "Private"; 14 subscribers.
  - Location: georeferencing method "OpenLR", coordinate system "WGS84".
  - Licence field: "Creative Commons CC Zero". Last update 2026-08-28.
  - A sample file exists from 2024-08 (`npp-test/public/2024-08/roadworks.xml`).
    It was not fetched: it is not current data.
- **Terms** (`GET /en/api/v1/get/nppTOS`, "Terms of Use … Effective as of:
  6 January 2026"):
  - Section 4: "Unless specified otherwise, all datasets published on the NAP
    Platform are made available under the Creative Commons CC0 1.0 Universal
    licence. Users (data recipients) may copy, distribute, adapt, and re-use
    data published on the NAP Platform without restrictions…" The conditions
    are no misleading, malicious or safety-endangering use. Credit is
    optional: "Source: transportdata.gov.lv – National Access Point for
    Transport Sector Information".
  - Section 7: "Certain functionalities of the NAP Platform (such as data
    submission or API access) require user registration and the use of a user
    account."
- **Verdict:** NEEDS_KEY. The licence permits commercial use (CC0), but the
  API needs an account. The site's interactive map was not used: the terms
  make API access conditional on registration.
- **Open question:** the metadata names OpenLR. If the records carry OpenLR
  location references only, without WGS84 points, REI could not place them
  without an OpenLR decoder and a road map. Check this once access is granted.

### Riga

No machine-readable road-event source was found. Riga publishes event-specific
restriction maps and press releases (lvportals.lv). The data.gov.lv catalogue
search found no Riga road-works or closures dataset.

## Estonia

### Tark Tee DATEX II gateway (NEEDS_KEY)

These details come from `www.tarktee.ee`: the robots.txt (404), the page, its
script bundle and `/assets/i18n/en.json`.

- **Gateway:** `https://www.tarktee.ee/api/v1/datex/`.
  - DATEX II 2.3 services: `restrictions` ("Traffic restriction data") and
    `safetyData`.
  - DATEX II 3.6 SRTI services marked available: `srti/shortTermRoadWorks`,
    `srti/unmanagedBlockage`, `srti/unprotectedAccident` and
    `srti/animalObstacle`.
- **Access:**
  - "Registration is required if you want to use the data provided through the
    DATEX II services of Estonian Transport Administration."
  - "After registering, you will receive a unique API key … NB! The key will
    only become valid once an employee of the Transport Administration has
    reviewed your registration."
  - The form (`/en/datex-registration`) asks for the establishment name
    (required), registry code (optional), given name, surname, e-mail and
    purpose (all required), and comments (optional). It requires accepting the
    Terms of Use.
  - Contact: `tmc@transpordiamet.ee`.
- **Terms** ("Terms of Use of the Smart Road DATEX II data gateway", `/en/terms`):
  - 3.3.4: "It is compulsory to refer to or make hyperlinks for the Service
    and the Administrator…"
  - The site describes the gateway as providing data "for free use". Nothing
    is said about commercial use.
- **Not used:** the public map loads `api/v1/trafficRestrictions`, an internal
  map API. It is not offered as a data service and was not fetched.
- **Verdict:** NEEDS_KEY. On registration, state the commercial purpose and ask
  for written confirmation that commercial reuse is allowed.

### Tartu traffic restrictions (ASK_PERMISSION)

- **What it is:** the map `liikluspiirangud.tartu.ee` is an ArcGIS Experience
  Builder app. Its open-data layer is
  `gis.tartulv.ee/arcgis/rest/services/Sulgemised/PI_liikluspiirangud_avaandmed/FeatureServer`
  (ArcGIS 11.5). It serves the JSON query format only, and its native
  coordinates are L-EST97 (EPSG:3301). It answers in WGS 84 when asked with
  `outSR=4326`.
- **Layers:**
  - 0 Teavitus (points)
  - 1 Suletav tee tulevikus (roads to be closed, lines)
  - 2 and 5: parking closures (polygons)
  - 3 Sulgemisalad tulevikus and 6 Sulgemisalad (closure areas, polygons)
  - 4 Suletav tee (closed roads, lines)
  - Table 7 Etapid (work stages)
- **Fetched:**
  - Layer 4: 153 lines. Fields include the street name `Nimi`, passage per
    vehicle type `Labipaas`/`Rada_*`, and the stage link `Etapp_GID`.
  - Table 7: 124 stages, all with `Algus` and `Lopp` (start and end). 76 were
    current, 48 upcoming, none ended. For example, 2026-02-01 to 2027-01-31.
  - The stages name the contractor's responsible person, phone and e-mail
    (`Liiklus_vastutaja`, `Telefon`, `Epost`). These must be dropped.
- **Licence:** the open-data hub (`avaandmed.tartulv.ee`, robots Crawl-delay 60,
  obeyed) lists the item "PI liikluspiirangud avaandmed" with
  `license: "none"`, `structuredLicense: {"type": "none"}` and `openData: false`.
  No portal terms were found. Contact `gis@tartulv.ee`.
- **Verdict:** ASK_PERMISSION. The data is good: lines, start and end, current.
  It needs an open licence first.

### Tallinn (BLOCKED)

`www.tallinn.ee/robots.txt` and the operational-information page both
answered HTTP 403 with a Cloudflare "Just a moment…" challenge. Neither was
retried.

### Estonian open data portal

`avaandmed.eesti.ee` redirects to `andmed.eesti.ee`, a single-page app; its
robots.txt is 404. No road-works or traffic-restriction dataset was found
there through web search, and the app's API was not explored.

## Poland

### GDDKiA KPD (NEEDS_KEY)

- **Re-checked:** `kpd.gddkia.gov.pl` (robots.txt 404): the home page, "Dostawcy
  usług", "Usługa KPD" and the FAQ.
- **Access, per the FAQ:**
  - "Aby się zarejestrować należy wypełnić jeden z wniosków rejestracyjnych …
    należy odesłać pocztą elektroniczną na adres e-mail: kpd@gddkia.gov.pl"
    (or by post to GDDKiA, ul. Wronia 53, 00-874 Warszawa).
  - The organisation registers first, as "Dostawca Danych / Odbiorca Danych".
    Then a user is registered "z dostępem do API". That user receives a test
    certificate and a test-schedule link, completes a message-exchange test,
    and is then sent the production certificate.
- **Terms:** `kpd.gov.pl` did not resolve (DNS), so the regulamin was not read.
- **Verdict:** NEEDS_KEY.

### GDDKiA obstructions XML (UNREACHABLE, CC0)

- **Catalogue entry:** `api.dane.gov.pl/1.4/datasets/2752` "Utrudnienia na
  drogach", institution GDDKiA, licence "CC0 1.0". Description: "Publikujemy
  dla Państwa aktualne dane o utrudnieniach, bieżących warunkach przejazdu oraz
  prognozie warunków przejazdu."
- **Resource:** `https://www.archiwum.gddkia.gov.pl/dane/zima_html/utrdane.xml`,
  dated 2022-05-23.
- **What happened:** robots.txt on that host timed out twice (once retried),
  and `www.gddkia.gov.pl` timed out too. Whether the file is still current, and
  whether it carries coordinates, is unverified.
- **If it is live:** with CC0, it would be a PERMITTED source.

### Warsaw traffic disruptions (UNREACHABLE, CC BY 4.0)

- **Catalogue entry:** `api.dane.gov.pl/1.4/datasets/39523` "Utrudnienia w
  ruchu drogowym", Urząd m.st. Warszawy, licence "CC BY 4.0", format JSON.
  Harvested from "Otwarte dane Warszawy" (`dane.um.warszawa.pl`) with update
  frequency "codziennie" (daily); last import 2026-09-02.
- **What happened:** the file link answers 302 to
  `dane.um.warszawa.pl/pl/catalogue/f49d088a-00d3-4d5e-8aaf-1bc7092c706c`.
  That host timed out from this machine, and WebFetch from another network was
  refused (`ECONNREFUSED`). `infoulice.um.warszawa.pl` (the city's disruption
  portal) timed out too.
- **Not seen:** the records, so whether they have coordinates and times is
  unknown.
- **If reachable and located:** it would be a PERMITTED source with
  attribution.

### Other Polish candidates

- **Geoportal "Utrudnienia drogowe GDDKiA":** a map view in geoportal.gov.pl
  built on the KPD API. The news page gives no service URL or licence.
- **Wrocław:** `opendata.cui.wroclaw.pl` answered 403 to robots.txt and to the
  API. Not retried.
- **Gdańsk:** `ckan.multimediagdansk.pl` robots.txt disallows `/api/`
  (Crawl-Delay 10, obeyed). The catalogue page found 0 datasets for
  "utrudnienia". "ruch" found only population, border-crossing and cycling
  sets.
- **Kraków and Poznań:** web searches found no machine-readable road-event
  dataset. ZDMK (Kraków) publishes a works list on its website; it was not
  fetched.

## Ireland

### TII Traffic (ASK_PERMISSION)

- **Re-checked:** `traffic.tii.ie` robots.txt is `Disallow: /images/`. The page
  is a single-page app ("Please enable JavaScript") that loads Google reCAPTCHA
  (`recaptcha/api.js?render=…`).
- **No published feed:** there is no published feed or reuse licence. The
  older NRA DATEX II service is described as needing a username and password.
  (That is a datex2.eu directory listing, seen via search; `repo.datex2.eu`
  did not resolve for WebFetch.)
- **Not a substitute:** `data.tii.ie` (CC BY 4.0) has no events (16 October
  finding).
- **National portal:** the national real-time roadworks portal is still only
  planned. The Road Management Office was asked to build it, and work is
  "expected to begin in 2026" (echo.ie).
- **Verdict:** ASK_PERMISSION. Contact `opendata@tii.ie`.

### Dublin City Council current road closures (ASK_PERMISSION)

- **Fetched:** the page (robots allows it). It lists 4 closures, each with RDFa
  `latitude`/`longitude` and a range such as "07/09/2026 - 00:00 -
  08/11/2026 - 23:59". All 4 are current or upcoming.
- **Site terms** (`/using-dublincityie/terms-and-conditions`):
  - "Public sector information posted on Dublin City Council's web site may be
    downloaded subject to the terms and conditions of the latest PSI Licence
    available at https://data.gov.ie/pages/re-useofpublicsectorinformation"
  - The same page also says: "All rights to design, text, graphics and other
    material on this website are the copyright of Dublin City Council or other
    third parties."
- **PSI page on data.gov.ie:** "Circular 12/2016: Licence for Re-Use of Public
  Sector Information adopts CC-BY as the standard PSI licence".
- **Why ASK_PERMISSION:** the two clauses pull in different directions. DCC's
  own data.gov.ie "Road Network" entry says third parties building added-value
  applications must first seek permission. The source is also an HTML page,
  not a feed. Ask DCC to confirm that the PSI Licence (CC BY 4.0) covers
  automated reuse of this list.

### Other Irish candidates

- **Fingal "Road Closures Temporary FCC"** (data.smartdublin.ie; Fingal Hub API
  `data.fingal.ie/api/v3/datasets`): CC BY 4.0, but a CSV of road-closure
  permits for 2022 to 2024. It is "updated quarterly", was last updated
  2024-09-20, and the page says "There is no geolocation data for this
  resource". Not a source.
- **Cork City "Road Closures Database":** datacatalogue.gov.ie lists it as
  "Open Data: No", "API Available: No" (from search; not fetched). Not a
  source.
- **Galway County:** `gaillimh.ie/en/services/roads/closures` is 404. The page
  links only to the council's ArcGIS organisation.

## What the user can do

- **Latvia:** create a free account at <https://transportdata.gov.lv> and accept
  the Terms of Use. Subscribe to Road works, Road closures, Lane closures,
  Short term road works and Accidents and incidents, and take the API key.
  - Licence CC0 1.0; free; no rate limit published.
  - Ask `npp@lvceli.lv` whether records carry WGS84 points as well as OpenLR.
- **Estonia:**
  - Register at <https://www.tarktee.ee/en/datex-registration>: free; name,
    e-mail, organisation, purpose. Then wait for Transport Administration
    review. Ask `tmc@transpordiamet.ee` to confirm commercial reuse with credit
    to Tark Tee / Transpordiamet. Services to request: `restrictions` (2.3) and
    the SRTI 3.6 services.
  - For Tartu, e-mail `gis@tartulv.ee` asking for an open licence (CC BY 4.0)
    on `PI_liikluspiirangud_avaandmed`. It is ready to build once licensed.
- **Poland:**
  - Download the KPD registration form (FAQ at
    <https://kpd.gddkia.gov.pl/index.php/pl/faq>) and e-mail it to
    `kpd@gddkia.gov.pl` as a data recipient, then register a user with API
    access. Client certificates follow a test; there is no stated cost. Ask for
    the regulamin and the reuse terms.
  - Separately, have someone try `dane.um.warszawa.pl` (Warsaw, CC BY 4.0) and
    the GDDKiA `utrdane.xml` (CC0) from another network, such as production.
    Both licences already permit reuse.
- **Ireland:**
  - E-mail `opendata@tii.ie` asking for DATEX II event access and reuse terms.
  - Ask Dublin City Council to confirm that the PSI Licence covers its
    road-closures list.
  - Watch for the Road Management Office's national roadworks portal.

## Access-rule notes

- **data.gov.ie and data.smartdublin.ie:** both robots.txt files end with
  `Crawl-Delay: 10`, after a blank line and outside any `User-agent` group.
  Python's robots parser did not attach it, so one request on each host came
  2 s after robots.txt. Requests later in the session waited 10 s or more.
  data.gov.ie got 2 requests, data.smartdublin.ie 3.
- **www.tallinn.ee:** robots.txt answered 403, which was treated as no rules.
  The one page request then also got a 403 challenge, and nothing more was
  sent.
- **Script bundles:** to find documented service paths, one bundle was fetched
  from each of `transportdata.gov.lv` (2.5 MB) and `www.tarktee.ee` (2.3 MB).
- **dane.gov.pl:** one extra request, without following redirects, checked
  where the Warsaw file link pointed.

## Not verified

- Whether GDDKiA's `utrdane.xml` and Warsaw's JSON are current and located.
- The KPD regulamin.
- Whether the Latvian NAP records carry coordinates as well as OpenLR.
- Whether Tark Tee allows commercial reuse.
- Tartu's layers 0–3, 5 and 6.
- Riga's municipal data beyond data.gov.lv.
- Kraków's ZDMK works list.
- Poznań's own portal.
- Warsaw's keyed API (`api.um.warszawa.pl`) and whether it carries these
  disruptions.
- Irish councils other than Dublin City, Fingal, Cork City and Galway County.
