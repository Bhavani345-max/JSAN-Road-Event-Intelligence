# Source research, 22 October 2026: South Africa (third pass)

This pass looks only for ground the first two passes did not cover
([15 October](south-africa-source-research-2026-10-15.md),
[16 October](south-africa-sources-2026-10-16.md)), plus a short re-check of
the Western Cape road closures layer. It covers open data portals not
searched before, event organisers that publish road closures, openly licensed
journalism, and other machine-readable feeds.

Every endpoint below was fetched live on 22 October 2026 between 10:44 and
11:08 UTC (12:44-13:08 South African time) with the User-Agent
`JSAN-REI/1.0 (road event intelligence; source research)`. robots.txt was
requested first on every host. Requests were sequential with a pause of at
least 2.2 seconds (60 seconds where a site asked for `Crawl-delay: 60`), at
most 7 on any one host, and redirects were not followed automatically. There
were no logins, keys, CAPTCHAs, proxies or browser disguise. Nothing was
connected, no code was changed and no e-mail or contact form was sent.

Verdicts use REI's standard: **PERMITTED** (published terms allow REI's
commercial use, such as Creative Commons or an open data licence);
**ASK_PERMISSION** (no terms found, or the terms are silent on reuse);
**RESTRICTED** (personal or non-commercial use only, or forbids automated
access, scraping or storage, or robots.txt disallows the path). This is a
reading of published terms, not legal advice.

## Result in short

- **No new South African source can be connected.** Nothing found today is
  both PERMITTED and carries road events. The only new PERMITTED source,
  The Conversation Africa (CC BY-ND 4.0), had 0 road events in its 50 latest
  articles, so it is not worth connecting. SAnews (already connected) stays
  the only permitted and useful South African source.
- **Western Cape road closures layer: live, maintained, still RESTRICTED.**
  45 closures today (29 No Access, 11 Partial Access, 5 Local Access Only),
  all `Approved`, every one with a start date, none with an end date, all
  with line geometry. Since 15 October one closure was added (19 October) and
  three disappeared without ever getting an end date, so reopened roads are
  removed from the public layer rather than end-dated. The start times look
  like data-entry defaults (see the notes). Licences are unchanged: all 15
  portal items have an empty `licenseInfo`, and the WCG Open Data Portal still
  has no road-closures layer (search "road closure": 0 matches).
- **Open data portals: nothing usable.** data.gov.za did not resolve (DNS
  timeout); the Gauteng GIS portal's robots.txt disallows everything;
  openAFRICA has no road-closure datasets; Ekurhuleni's ArcGIS portal shows
  only Esri stock templates; ArcGIS Online has no new openly licensed South
  African event layer. One genuinely new find: **Garden Route District
  Municipality** has set up Esri's "Road Closures" solution as a public layer,
  but it holds only three "Test feature" records from 27 May 2026.
- **Event organisers publish closures as web pages, PDFs and (once) a GPX
  route, never as a feed.** The Sanlam Cape Town Marathon's terms forbid
  commercial robot use (RESTRICTED). Comrades, Cape Town Cycle Tour, Two
  Oceans and Ride Joburg publish no reuse terms beyond "All rights reserved"
  (ASK_PERMISSION). The Soweto Marathon site answers every request with a 503
  maintenance page. Next event: **Ride Joburg, Sunday 22 November 2026**
  (finish at Kyalami); no closure schedule is published yet.
- **Openly licensed news:** GroundUp is unchanged (republication only with
  explicit permission since 1 April 2026). Health-e News and Bhekisisa are
  described in search results as Creative Commons outlets, but they cover
  health, not roads; they were not fetched.
- **Other feeds:** KZN Department of Transport is still unreachable;
  SANParks (Kruger road closures) and Cape Town Tourism answer robots.txt with
  a Cloudflare challenge; no SANRAL project map was found. The Gauteng Freeway
  Management System feeds i-TRAFFIC, which stays RESTRICTED.

## Summary table

HTTP = status of the main data URL. Items = items in the feed or list today.
"Dates?" = a date for the event in the data (not only a publication date).
"Coordinates?" = machine-readable positions.

| Source | Type | URL | HTTP | Items | Dates? | Coordinates? | robots.txt | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Western Cape DOI public road closures (re-check) | ArcGIS FeatureServer (JSON/GeoJSON) | `gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer` | 200 | 45 (29 + 11 + 5) | Start on 45 (see caveat); end on 0 | Yes (lines; start/end lon/lat) | 404 (no rules) | RESTRICTED (unchanged) |
| WCG GIS portal items "road closures" | ArcGIS portal search | `gis.westerncape.gov.za/portal/sharing/rest/search?q=road closures` | 200 | 15 items | n/a | n/a | 404 (no rules) | `licenseInfo` empty on all 15 |
| WCG Open Data Portal | ArcGIS Hub search API | `wcg-opendataportal-westerncapegov.hub.arcgis.com/api/search/v1/collections/all/items` | 200 | "road closure": 0; "road": 6 (health facilities, one dashboard) | n/a | n/a | Allowed; `Crawl-delay: 60` (honoured) | No closures layer |
| National open data portal | Portal | `data.gov.za` | DNS timeout (twice) | n/a | n/a | n/a | unreachable | UNREACHABLE |
| openAFRICA (Code for Africa) | CKAN API | `open.africa/api/3/action/package_search?q=road closures` | 200 | 0 datasets | n/a | n/a | `/api/` disallowed (see access notes) | No data |
| Gauteng Provincial GIS portal | ArcGIS Enterprise | `gisportal.gauteng.gov.za` | not requested | n/a | n/a | n/a | `Disallow: /` | RESTRICTED (robots.txt) |
| City of Ekurhuleni ArcGIS portal | ArcGIS Enterprise search | `gis.ekurhuleni.gov.za/arcgis/sharing/rest/search` | 200 | 28 items, all Esri stock templates | n/a | n/a | 404 (no rules) | No road-event layer |
| ArcGIS Online, South African searches | Search API | `www.arcgis.com/sharing/rest/search` | 200 | 4 searches; no new SA event layer | n/a | n/a | Allows all | No openly licensed SA event layer |
| Garden Route DM `RoadClosures_public` | ArcGIS FeatureServer | `services5.arcgis.com/G8Pqo3DzH8fIDN8F/arcgis/rest/services/RoadClosures_public_485f84e7bb9d4d1db7d8394740251c01/FeatureServer` | 200 | 3 (1 block, 1 closure, 1 detour), all "Test feature", 27 May 2026 | Start and end on all 3 (test data) | Yes (point and lines) | 403 "Invalid URL" (no file; no rules) | ASK_PERMISSION; nothing to connect |
| Garden Route DM `GRDM_Flooded_Roads_WFL1` | ArcGIS FeatureServer | `.../GRDM_Flooded_Roads_WFL1/FeatureServer/0` | 200 | over 300 road segments (2009 road network) | No | Yes | as above | Not events |
| Garden Route DM `District_Incidents` | ArcGIS FeatureServer | `.../District_Incidents/FeatureServer/0` | 200 | 5 (11-13 May 2026) | Reported and cleared dates | not requested | as above | Pilot data; not a source |
| Comrades Marathon | HTML blog post per race | `comrades.com/blogs/comrades2024-road-closures` | 200 | 1 table, 16 rows (2024 race) | Close/open time per area | No | Comment only (no rules) | ASK_PERMISSION |
| Cape Town Cycle Tour | PDF (7 pages) | `doueyfh6590m8.cloudfront.net/.../CTCT26_ Provisional Road Closures - new proposed times.pdf` | 200 | 7 pages of tables (2026 race) | Day and time ranges (year labels inconsistent) | No (route on Strava) | Site: comment only; CDN: 403 (no file) | ASK_PERMISSION |
| Two Oceans Marathon | 4 newspaper-advert PDFs; RSS | `twooceansmarathon.org.za/ultra-marathon/#road-closures`; `/feed/` | 200 | 4 PDFs (2026 race, not downloaded); RSS 10 items, 0 closures | In the PDFs | No | Allows all | ASK_PERMISSION |
| Sanlam Cape Town Marathon | HTML + PDF | `capetownmarathon.com/road-closures/` | 200 | 1 PDF, still the 2024 race | In the PDF | No | Allows all but `/wp-admin/` | RESTRICTED |
| Soweto Marathon | Website | `sowetomarathon.com` | 503 on every path, robots.txt included | n/a | n/a | n/a | unreadable | UNREACHABLE |
| Ride Joburg (formerly 947 Cycle Challenge) | GPX route + PDF map | `ridejoburg.co.za/documents/RJ26_Route96km.gpx.zip` | 200 | 1 track, 770 points | No (race date only on the web page) | Yes (route line) | 404 (no rules) | ASK_PERMISSION |
| Cape Town Tourism | WordPress articles | `www.capetown.travel` | 403 Cloudflare challenge on robots.txt | n/a | n/a | n/a | unreadable | UNREACHABLE |
| The Conversation Africa | Atom | `theconversation.com/africa/articles.atom` | 200 | 50 (2-21 Oct), full text; 0 road events | Publication only | No | Allowed for `*`; AI agents (ClaudeBot, Claude-User, GPTBot and others) `Disallow: /` | PERMITTED (CC BY-ND 4.0); not worth connecting |
| GroundUp (re-check) | Licence pages | `groundup.org.za/licencing/detail/2/` | 200 | n/a | n/a | n/a | Allowed | ASK_PERMISSION (unchanged) |
| SANParks (Kruger road closures) | News | `www.sanparks.org/news` | 403 Cloudflare challenge on robots.txt | n/a | n/a | n/a | unreadable | UNREACHABLE |
| KZN Department of Transport (retry) | Website | `www.kzntransport.gov.za` | connection timeout | n/a | n/a | n/a | unreachable | UNREACHABLE |

## Western Cape road closures, re-checked

**Data.** One query of the three line layers without geometry
(`https://gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer/query?layerDefs={"0":"1=1","2":"1=1","3":"1=1"}&returnGeometry=false&f=json`,
54,253 bytes):

- 45 closures, 45 unique `closureid`, all `status` = Approved. Layer 0
  "No Access" 29, layer 2 "Partial Access" 11, layer 3 "Local Access Only" 5.
- Reasons: Flood Damage 44, Hazard 1 (the two "Flooding" records seen on
  15 October are gone). Districts: Cape Winelands 15, Garden Route 14, Central
  Karoo 9, West Coast 6, Overberg 1; every record now has a district.
- `starttime` on all 45 (25 August to 19 October 2026); `endtime` on none; no
  start in the future. Records created 25 August to 19 October; last edit
  20 October 2026 08:26 UTC. The layer is actively maintained.

**Changes since 15 October** (compared with the 15 October sample by
`closureid`):

- Added: `LAO-000008`, road DR01681, Flood Damage, Local Access Only, start
  19 October 2026 11:09 UTC.
- Removed: `NA-000056` (DR1694) and `NA-000059` (DR1707), both "Flooding"
  with no district, and `PA-000019` (DR01681, "Middelpad, Residents only").
  `PA-000019` appears to have been replaced by `LAO-000008` on the same road.
- None of the three removed records was given an end date first. This
  answers an open question from 16 October: a closure that ends simply
  disappears from the public layer. (Whether it is deleted or hidden by a
  status change cannot be told from the public view.) A connector should end
  an event when its `closureid` disappears.

**Caveat on start times.** For all 45 records, `starttime` is either within
2 minutes of the record's `created_date` (15 records) or exactly 24 hours
before it (30 records). No record has an independent start time. The start
dates therefore look like editor defaults at data entry ("now" or "now minus
one day"), not the moment the road closed. If REI shows these closures, the
date should be labelled as "listed since" rather than an observed start, and
the question belongs in the permission e-mail.

**Licence (unchanged).** The portal search
(`https://gis.westerncape.gov.za/portal/sharing/rest/search?q=road%20closures&num=50&f=json`)
lists the same 15 public items as on 16 October (FeatureServer, MapServer,
detours view, web maps, dashboard, CSV, two web experiences and others). Every
one has an empty or null `licenseInfo`. The WCG terms of use quoted on
16 October still apply: non-commercial reuse is free; "Permission to
reproduce content for commercial purposes may be granted subject to a written
request to service@westerncape.gov.za".

**WCG Open Data Portal.** robots.txt allows the search API and asks for
`Crawl-delay: 60` (honoured: each of the two searches came about 61 seconds
after the previous request). `.../api/search/v1/collections/all/items?q=road%20closure`
returned `numberMatched: 0`. As a scope check, `q=road` returned 6 items: five
WCG Department of Health facility layers (four with `licenseInfo` "CC BY",
one empty) and the "Safety and Security Barometer" dashboard. No road-closures
layer has appeared there.

**Verdict:** RESTRICTED, unchanged. The draft request in
[permissions-and-activation-2026-10-15.md](permissions-and-activation-2026-10-15.md),
section 3.1, is still the right step (see the suggested updates under
"Recommended next steps").

## Per-source notes

### Open data portals

**data.gov.za (national portal, DPSA).** `https://data.gov.za/robots.txt`
failed with a DNS error (`getaddrinfo failed`), and two `nslookup` checks for
`data.gov.za` and `www.data.gov.za` timed out. Search results describe it as
a DPSA catalogue from the Open Government Partnership work; one civic-tech
directory lists it as "Inactive". Recorded as unreachable.

**openAFRICA (`open.africa`, Code for Africa CKAN).** The CKAN search for
"road closures" returned `count: 0`. The South African datasets seen in
search results are boundary files (Municipal Demarcation Board, CC BY). See
the access notes: robots.txt disallows `/api/` in its second `User-agent: *`
group.

**Gauteng Provincial GIS portal (`gisportal.gauteng.gov.za`).** robots.txt:

> `User-Agent: *` / `Disallow: /`

The portal search was not requested. RESTRICTED by robots.txt. (The Gauteng
City-Region Observatory data portal holds survey and planning data, not road
events; it was not fetched.)

**City of Johannesburg, Tshwane.** Search found no public open data portal
for Johannesburg (a 2024 City article describes an internal "Integrated
Spatial Data Portal" under development) and only a reference to a Tshwane
open data portal without a working address. Tshwane's e-GIS server disallows
everything in robots.txt (15 October). Nothing to fetch.

**City of Ekurhuleni ArcGIS Enterprise (`gis.ekurhuleni.gov.za`).** robots.txt
404 (no rules). The portal search for closure, roadworks, detour, traffic,
incident or event returned 28 public items, all Esri stock content (layer
templates such as "Road Closures" owned by `esri_apps`, "Civic Events"
feature collections, notebooks). No Ekurhuleni road-event layer is public.

**KwaZulu-Natal and Eastern Cape.** No provincial open data portal was found.
The Eastern Cape Department of Transport publishes closures through Facebook
and gov.za statements (search results); gov.za is RESTRICTED (16 October).
KZN Department of Transport: robots.txt timed out again (see the table).

**ArcGIS Online.** Four searches (`www.arcgis.com/sharing/rest/search`):

1. Closure/roadworks/detour terms with a South African bounding box: 1,084
   matches, but the bounding-box filter is swamped by items with world
   extents (mostly United States layers); no South African event layer in the
   newest 100.
2. Closure/roadworks/detour/traffic-incident terms AND South African place
   names (provinces, metros, SANRAL): 51 matches. South African items were
   mine-closure atlases, student story maps, "Limpopo 2021 Taxi incidents"
   (historical hotspot tiles; `licenseInfo` "Acnkowledge source"), the 2014
   Ekurhuleni traffic map (Esri commercial traffic) and "GRDM Alternative
   Routes" (below).
3. The same terms AND Western Cape towns, districts and event names
   (Comrades, Cycle Tour, Two Oceans, Soweto Marathon): 26 matches, none
   South African road events.
4. "Road Closures"/detours/roadworks AND "District/Local/Metropolitan
   Municipality", "Department of Transport", "Roads Agency": 247 matches; the
   newest 100 are all North American.

**Garden Route District Municipality (new).** Found through search 2 ("GRDM
Alternative Routes", owner `renier@EDENDM.CO.ZA_gardenroutedm`, snippet
"Alternative routes in the event of road closures in the Garden Route DM",
created June 2024, pre-planned routes, no licence). The organisation's public
services directory
(`https://services5.arcgis.com/G8Pqo3DzH8fIDN8F/arcgis/rest/services?f=json`)
lists 128 services, including:

- `RoadClosures_public_485f84e7bb9d4d1db7d8394740251c01` (FeatureServer;
  layers 0 Blocks (points), 1 Closures (lines), 2 Detours (lines);
  `maxRecordCount` 1000; Query only). Its portal item
  `072884665b8c4c13be050ba8d544d12f` ("RoadClosures_public", owner
  `GardenRouteGIS`, access public, `accessInformation` "Garden Route District
  Municipality") says: "A public feature layer view used to share current,
  planned, and past road blocks, closures, and detour routes." Tags include
  "ArcGIS Solutions". One query of all three layers returned **3 records, all
  test data** created 27 May 2026: a block at "Victoria Street & York Street"
  (description "Test feature"), a closure on "York Street" ("Test feature")
  and a detour on "Test". Start and end times were 28-30 May 2026. The
  service was last modified 27 May 2026. Fields follow Esri's Road Closures
  schema (`street`, `direction`, `reason`, `laneimpact`, `accessallowed`,
  `description`, `starttime`, `endtime`), the same family as the Western Cape
  layer.
- Its `licenseInfo` reads "Copyright 2026 Esri … Licensed under the Apache
  License, Version 2.0 …". This is the boilerplate of Esri's solution
  template (it licenses Esri's template, not the municipality's data), so it
  is not a data licence. Verdict: ASK_PERMISSION, and there is nothing to
  connect today.
- `GRDM_Flooded_Roads_WFL1` ("Roads in GRDM that is flooded because of heavy
  rain."): one layer, `Eden_PGWC_Roadnet_2009_09`, a 2009 road network.
  Fields `ROADNUMBER`, `ROADTYPE`, `DMC_DC`, `Status`; in the first 300 rows
  `Status` is empty for 299 and "C" for one. No dates. Last modified 25 May
  2026. Not an event layer.
- `District_Incidents`: 5 records reported 11-13 May 2026 (Flooding, Fallen
  Tree, Road Closure "Water damaged road.", …), entered by one staff member
  (`Reported_By` holds a first name; do not store). Last modified 13 May
  2026. A pilot, not a live source.
- Also listed but not opened: `Disaster_Incidents`, `Disaster_Management`,
  `Alternative_Routes`, `GRDM_Roads_Network`.

If Garden Route DM starts using its Road Closures layer for real, it would be
a second provincial-style source in the same format as the Western Cape
layer (its district also has 14 of the Western Cape layer's closures). It
would need permission first.

### Event organisers

None of these publishes closures as a feed. In 2026, SAnews (already
connected, PERMITTED) carried City-issued closure notices for at least the
Comrades Marathon ("Comrades Marathon road closures announced ahead of race
day", `sanews.gov.za/node/82167`) and the Cape Town Cycle Tour ("Road
closures ahead of the Cape Town Cycle Tour", `sanews.gov.za/node/79953`).
Those come from search results and were not fetched, but they show the
permitted route by which event closures already reach REI.

**Comrades Marathon (Comrades Marathon Association, KZN; next race June
2027).** robots.txt (Cloudflare) contains only a comment line, so no rules.
Closures are published as a blog post per race: search found
`comrades.com/blogs/comrades2022-road-closures`, `...comrades2023-road-closures`
and `...comrades2024-road-closures`, plus a 2024 "Road Closures.pdf"; no 2025
or 2026 post turned up. The 2024 post (182 KB HTML) says: "The Comrades
Marathon Association (CMA) has confirmed that the following road closures
and alert notification which will be effective over Comrades race weekend,
starting around 16h00 on Saturday 8th until 18h30 on Sunday, 9th June 2024."
It then gives a "Comrades Marathon Road Closure Schedule" table with 16 rows
of area, close time and open time (for example "Kloof (9 June) 05H00
10H00"). Text only, no coordinates. Terms: the only "Terms & Conditions" link
(`relay.niimble.io/terms/comrades`, "Last updated August 24, 2026") covers the
site's chatbot: "The Comrades GPT is an AI-based system and is intended to
provide general information and assistance …". No website reuse terms were
found. Verdict: ASK_PERMISSION.

**Cape Town Cycle Tour (next race March 2027).** robots.txt contains only a
comment line. The event page (`/events/the-cape-town-cycle-tour`) links "View
Road Closure Information", a PDF on a CloudFront CDN:
`https://doueyfh6590m8.cloudfront.net/system/refinery/resources/W1siZiIsIjIwMjYvMDEvMjAvMTQvMjQvMTIvZGIyOGRlZTAtODQ5MS00YWQyLWI1ZjAtYTYzY2U0ZWUwZGFhL0NUQ1QyNl8gUHJvdmlzaW9uYWwgUm9hZCBDbG9zdXJlcyAtIG5ldyBwcm9wb3NlZCB0aW1lcy5wZGYiXV0/CTCT26_%20Provisional%20Road%20Closures%20-%20new%20proposed%20times.pdf`
(591,111 bytes, 7 pages, a PowerPoint export modified 20 January 2026). It is
a table of area, street section and time window, for example "Chapman's Peak
Drive (M6) from Noordhoek Main Road (M6) to Princess Street — Saturday, 18h00
– Sunday, 18h00". The title says "Thursday, 5 March – Sunday, 8 March 2026",
but the day headings inside still read "Saturday, 8 March 2025" and "Sunday,
9 March 2025": a reused template, which shows why dates from such PDFs must
not be trusted automatically. The route is published on Strava and as PDF
maps. Terms: the "Terms and Conditions" PDF is the "2024 CTCT Combined Race
Entry Terms and Con[ditions]" (entrant rules only); the footer says "Cape
Town Cycle Tour © Copyright 2024 - All Rights Reserved". Verdict:
ASK_PERMISSION.

**Two Oceans Marathon (next race April 2027).** robots.txt (Yoast):
`User-agent: *` / `Disallow:` (everything allowed). Each race page has a
"Road Closures" section: "The road closures for Race Weekend will be
published here prior to the race." The 2026 closures are still linked as four
newspaper-advert PDFs, uploaded 31 March 2026: `TTOM_Road-Closures_Weekend-Argus_188x270.pdf`,
`..._False-Bay-Echo_264x200.pdf`, `..._Die-Burger_148x300.pdf`,
`..._Peoples-Post_270x200.pdf` (under
`media.twooceansmarathon.org.za/wp-content/uploads/2026/03/`; not
downloaded). The WordPress feed `https://www.twooceansmarathon.org.za/feed/`
has 10 press releases (30 June to 15 October 2026), none about closures.
Terms: footer "© 2026 Two Oceans Marathon. All rights reserved."; the "event
terms and conditions" PDF (8 July 2026, 5 pages) covers entry, risk and
personal information only. Verdict: ASK_PERMISSION.

**Sanlam Cape Town Marathon (moved to May; 2026 race 23-24 May).**
`www.capetownmarathon.com/robots.txt` redirects (301) to
`capetownmarathon.com/robots.txt`, which allows everything except
`/wp-admin/`. `https://capetownmarathon.com/road-closures/` is stale: "The
Sanlam Cape Town Marathon takes place the weekend of the 19 th and 20 th
October 2024", with "ROAD CLOSURES PDF DOWNLOAD" pointing to
`/wp-content/uploads/2024/09/SCTM24-Road-Closures-V8.pdf`. (For 2026 the City
of Cape Town issued its own guide, RESTRICTED under City terms.) Website
terms (`2025-Cape-Town-Marathon-Website-Privacy-Policy-and-Terms-Conditions-1.pdf`,
"updated on 3 July 2024"):

> "The following activities on or through the Website are expressly prohibited: ▪ Any non-personal or commercial use of any robot, spider, other automatic device or technology, or manual process to monitor or copy portions of the Website or the content contained thereon without the prior written authority of Cape Town Marathon"
>
> "Except as stated herein, none of the material may be copied, reproduced, distributed, republished, downloaded, displayed, posted or transmitted in any form or by any means … without the prior written permission of Cape Town Marathon or the copyright owner."

Verdict: RESTRICTED.

**Soweto Marathon (2026 date not published).** `www.sowetomarathon.com`
redirects to `sowetomarathon.com`, which answers every path, robots.txt
included, with HTTP 503 and a "coming soon" page still showing "Date:
29/11/2025". Nothing else was requested. Closures for the 2025 race were
announced by JMPD/City of Johannesburg (RESTRICTED, 16 October) and in the
news. Verdict: UNREACHABLE.

**Ride Joburg (formerly the 947 Cycle Challenge; Sunday 22 November 2026).**
The old domain `www.947ridejoburg.co.za` is a parked page (title only). The
current site is `ridejoburg.co.za` (robots.txt 404, no rules). The road race
page (`/road.html`, last modified 9 October 2026) says: "Join us for the Ride
Joburg road race, hosted by the City of Johannesburg, on Sunday 22 November
2026. Own the Streets of Joburg as you power along the iconic M1 highway
before returning to a spectacular finish at the legendary Kyalami Grand Prix
Circuit." It links a GPX file and a PDF map:

- `https://ridejoburg.co.za/documents/RJ26_Route96km.gpx.zip` (8,456 bytes;
  last modified 26 March 2026): one GPX 1.1 track, 770 points, longitude
  27.929 to 28.091 E, latitude 26.258 to 25.983 S, starting and ending near
  Kyalami. No timestamps. The GPX metadata names it "2025 Fliped route" with
  a link to gpsies.com/AllTrails, so the geometry was drawn in a third-party
  route tool.
- No 2026 road-closure schedule is published yet (search found only the 2025
  City of Johannesburg notice: full closures 03:00-17:00).

The route says where roads will be closed but not when. Terms: the "Legal"
section lists a withdrawal policy, participant agreement and rules; the
footer says "© Ride Joburg / All rights reserved". Nothing on reuse.
Verdict: ASK_PERMISSION.

**Cape Town Tourism (`www.capetown.travel`).** It republishes event closure
lists ("All the 2026 Cape Town Cycle Tour Road Closures", "Two Oceans
Marathon 2026: Road Closures and Travel Information", "Cape Town Marathon
2026 Road Closures"). robots.txt returned HTTP 403 with a Cloudflare challenge
(`Cf-Mitigated: challenge`). Nothing else was requested. UNREACHABLE.

### Openly licensed news and journalism

**The Conversation Africa.** robots.txt allows `*` except account, search and
metrics paths; a long list of AI agents (anthropic-ai, ClaudeBot, Claude-User,
Claude-Web, GPTBot, CCBot and others) gets `Disallow: /`. The feed
`https://theconversation.com/africa/articles.atom` is valid Atom with 50
entries (2 to 21 October 2026), each with full article text. None reports a
road closure, roadworks or traffic event; it is academic commentary (health,
economy, climate, elections). Licence
([republishing guidelines](https://theconversation.com/africa/republishing-guidelines)):

> "We believe in the free flow of information and so publish under a Creative Commons — Attribution/No derivatives license. This means you can republish our articles online or in print for free, provided you follow these guidelines"
>
> "You can't sell our material separately, but it's OK to put our articles on pages with ads." … "You can't systematically republish all of our articles, nor frame the content of our site."

Verdict: PERMITTED (CC BY-ND 4.0 allows commercial use, with attribution and
no derivatives). Not worth connecting: no road events, and its robots.txt
blocks AI agents, which matters if article text were sent to a model.

**GroundUp (re-check).** `https://groundup.org.za/licence-change/` is
unchanged: "From 1 April 2026, GroundUp will publish most of our articles
under a new licence … our articles will only be available for republication
with our explicitly granted permission." "Generally we will grant such
permission to any legitimate news publication that — if it is primarily aimed
at a South African audience — is a member of the South African Press
Council." The licence text (`/licencing/detail/2/`, "GroundUp Republication
Licence version 1.0", last modified 25 August 2026): "Articles may not be
re-published or copied unless approval is first obtained from GroundUp …".
Articles published before 1 April 2026 stay under CC BY-ND 4.0. Verdict:
ASK_PERMISSION; REI is unlikely to qualify.

**Health-e News and Bhekisisa.** Search results describe Health-e News as
CC BY-ND and Bhekisisa as "generally available CC BY-SA 4.0". Both are health
journalism outlets with no road coverage, so they were not fetched and their
current terms were not read.

**Wikinews.** A search returned no South African road-closure items; not
fetched.

### Other machine-readable feeds

**Gauteng Freeway Management System / provincial traffic management
centres.** These are SANRAL operations (Central Operations Centre, Samrand)
whose public output is i-TRAFFIC (key plus SANRAL's written consent;
RESTRICTED, 15 October). Not re-tested.

**SANRAL project or roadworks map.** None found. The SANRAL road layers in
search results are CSIR-hosted road-network data (`pta-gis-2-web1.csir.co.za`),
not events.

**SANParks (Kruger National Park road closures).** SANParks posts road
closures after heavy rain as news items and on Facebook (search results).
`https://www.sanparks.org/robots.txt` returned HTTP 403 with a Cloudflare
challenge; nothing else was requested. UNREACHABLE.

**KZN Department of Transport.** `https://www.kzntransport.gov.za/robots.txt`:
connection timed out (one attempt). Still unreachable, as on 16 October.

**Municipal ArcGIS servers.** Search found no South African municipal
road-closure service other than Garden Route DM's (above). Tshwane's server
disallows everything (15 October); Ekurhuleni's portal has nothing public.

## Recommended next steps

1. **Connect now: nothing new.** SAnews remains the only PERMITTED South
   African source with road content, and it already carries City-issued event
   closure notices. The Conversation Africa is PERMITTED but has no road
   events; connecting it would add load without events.
2. **Send the Western Cape request** (draft
   [3.1](permissions-and-activation-2026-10-15.md), to
   service@westerncape.gov.za, cc PDO@westerncape.gov.za). It is still the
   single most useful step for South Africa: 45 located, approved closures,
   maintained this week. Suggested updates before sending: the closure count
   (45 today), and a reworded question 3 asking whether `starttime` is the
   real closure start (30 of 45 are exactly 24 hours before the record was
   created, the rest within 2 minutes) and whether closures are deleted when
   a road reopens.
3. **SANRAL i-TRAFFIC:** draft [3.2](permissions-and-activation-2026-10-15.md)
   is unchanged and remains the only route to national-road events.
4. **Optional, lower priority (no drafts written yet):**
   - *Garden Route District Municipality:* a short question on whether it
     plans to use its public Road Closures layer and under what licence. Worth
     asking only if the user wants more Western Cape coverage; today the layer
     holds test data.
   - *Event organisers* (Ride Joburg, Comrades Marathon Association, Cape Town
     Cycle Tour, Two Oceans): each publishes once a year, as text, PDF or a
     route line, so permission would add a handful of events a year. One
     template could cover all four (permission to show published closure
     schedules and route lines with attribution). Ride Joburg is the soonest
     (22 November 2026). The Sanlam Cape Town Marathon would need written
     authority because its terms forbid commercial robot use.
5. **Do not retry:** the Gauteng GIS portal (robots.txt disallows all),
   Cloudflare-challenged sites (Cape Town Tourism, SANParks), and the Soweto
   Marathon site until it is back up.

## Not verified

- Whether the three Western Cape closures that disappeared were deleted or
  only hidden from the public view by a status change.
- The content of the Two Oceans newspaper-advert PDFs (not downloaded) and
  whether Comrades published 2025 and 2026 closure posts on comrades.com
  (search found none).
- Whether data.gov.za still exists (DNS failed throughout).
- Current licences of Health-e News and Bhekisisa (not fetched; off-topic).
- The SAnews closure items for Comrades and the Cycle Tour come from search
  results; they were not fetched.
- Garden Route DM's plans for its Road Closures layer; the services
  `Disaster_Incidents`, `Disaster_Management` and `Alternative_Routes` were
  not opened.

## Requests made

- **65 HTTP request attempts to 25 hosts**, 10:44:43 to 11:08:24 UTC, robots.txt
  requests and redirects included. Two failed to connect (data.gov.za DNS,
  kzntransport.gov.za timeout). Ten further requests were refused by the
  fetch script before sending (robots.txt disallowed, unreadable or
  redirected) and are not counted.
- Per host: services5.arcgis.com 7; www.arcgis.com 6; ridejoburg.co.za 5;
  www.capetowncycletour.com 4; www.twooceansmarathon.org.za 4;
  capetownmarathon.com 4; gis.westerncape.gov.za 3;
  wcg-opendataportal-westerncapegov.hub.arcgis.com 3; comrades.com 3;
  theconversation.com 3; groundup.org.za 3; open.africa 2; relay.niimble.io 2;
  doueyfh6590m8.cloudfront.net 2; www.947ridejoburg.co.za 2;
  gis.ekurhuleni.gov.za 2; media.twooceansmarathon.org.za 2; data.gov.za 1;
  gisportal.gauteng.gov.za 1; www.capetownmarathon.com 1;
  www.sowetomarathon.com 1; sowetomarathon.com 1; www.capetown.travel 1;
  www.sanparks.org 1; www.kzntransport.gov.za 1.
- 24 web-search queries were used for discovery (search engine only; no
  requests to the hosts themselves).

### Access-rule notes

- **openAFRICA:** robots.txt has two `User-agent: *` groups. The fetch
  script's parser read only the first (Cloudflare-managed, `Allow: /`), so one
  request was sent to `/api/3/action/package_search`. The second group
  (`Disallow: /api/`, `Crawl-Delay: 10`) disallows that path, and under
  RFC 9309 the groups combine. That one request breached the rule; the script
  was then corrected to merge groups, and nothing more was sent to `/api/`.
- **403 robots.txt without a challenge:** `doueyfh6590m8.cloudfront.net` and
  `media.twooceansmarathon.org.za` (Amazon S3 "AccessDenied" XML for a
  missing file) and `services5.arcgis.com` ("Invalid URL", ArcGIS Online's
  answer for any non-service path) returned 403 for robots.txt with no bot
  challenge. RFC 9309 treats a 4xx robots.txt as "no rules", so one PDF, one
  PDF and six ArcGIS requests respectively were sent after an explicit
  override. Cloudflare challenges (capetown.travel, sanparks.org) were
  treated as blocks and nothing further was requested.
- **WCG Open Data Portal:** `Crawl-delay: 60` was honoured.
- **Redirects:** `www.capetownmarathon.com` and `www.sowetomarathon.com`
  redirected robots.txt to the bare domain; each redirect was counted, and
  robots.txt was then requested on the bare domain.
- **Soweto Marathon:** after the 503 on robots.txt nothing else was requested.
- No AI-crawler user agent was used. REI's agent name is not listed in any
  robots.txt seen.
- Samples are in the session scratchpad, not in the repository:
  `C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\1f1e58d5-c7a5-480c-a06f-4cc65e0fa21f\scratchpad\za-research\`
  (`data\` for responses, `robots\` for robots.txt files), with the request
  log in the sibling `za-scripts\log.tsv`.
