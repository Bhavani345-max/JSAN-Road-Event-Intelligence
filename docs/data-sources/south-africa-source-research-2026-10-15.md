# Source research, 15 October 2026: South Africa

The user asked for at least four working official sources for South Africa.
Every candidate below was searched for and, where an endpoint exists, fetched
live on 15 October 2026 between about 08:17 and 08:34 UTC (10:17-10:34 South
African time) with the User-Agent
`JSAN-REI/1.0 (road event intelligence; source research)`. robots.txt and the
licence or terms were read for each endpoint. Nothing was bypassed: no browser
disguise, no proxies, no keys registered or guessed. Nothing was connected and
no code was changed.

**Result: no South African source is GREEN today.** One is YELLOW: the Western
Cape Department of Infrastructure's public road closures layer passes every
test except the licence (commercial use needs written permission). The only
other real feed, SANRAL's i-TRAFFIC API, needs a developer key and SANRAL's
written consent. The metros (Cape Town, Johannesburg, eThekwini, Tshwane,
Ekurhuleni, Nelson Mandela Bay, Buffalo City) publish no machine-readable
road events: only news releases, PDFs and social media posts.

## GREEN

None.

## YELLOW

| Source | Authority | Endpoint | On 15 Oct | Location | Licence | robots.txt | Missing |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Western Cape public road closures | Western Cape Government, Department of Infrastructure (DOI Transport) | `gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer` (ArcGIS 11.5) | HTTP 200; 47 closures, all current (in force, no end time); 0 upcoming; 0 ended | Lines, 47 of 47 (each closure also as a point); `outSR=4326` works, stored in UTM zone 34S (Hartebeesthoek94) | No licence on the layer's portal item. WCG terms of use: non-commercial reuse free; "Permission to reproduce content for commercial purposes may be granted subject to a written request to service@westerncape.gov.za" ([terms](https://www.westerncape.gov.za/terms-of-use)) | `gis.westerncape.gov.za/robots.txt` returns 404: no rules | Commercial-use permission |

### Connector notes: Western Cape public road closures

- **What it is.** The data behind the DOI Transport "Public Road Closures
  Viewer" (portal web experience `41552d95f9ea448baa1f6ccb6ea5d50c`, and V2
  `c797a8cfb3884fbaa1d33589b199628e`, whose web map reads this service and a
  detours layer). The Western Cape Minister of Infrastructure's release of
  12 October 2026 says the Roads4U app now lets users "view verified road
  closures across the network via the official Road Closure Map"
  ([release](https://www.westerncape.gov.za/infrastructure/article/new-roads4u-features-improve-communication-and-accelerate-service-delivery)).
  Found through the public search of the WCG GIS portal
  (`gis.westerncape.gov.za/portal/sharing/rest/search?q=closure`); it is not
  in ArcGIS Online's public search or on the WCG Open Data Portal.
- **Coverage.** Provincial roads managed by DOI (main, divisional, trunk and
  minor roads, numbered like `MR00547`, `DR01461`, `TR07501`, `OP05728`).
  Not City of Cape Town streets, not SANRAL's national roads. Today almost all
  are flood damage after the late-August 2026 storms: Cape Winelands 15,
  Garden Route 12, Central Karoo 9, West Coast 6, Overberg 1, no district 4.
  The reason domain also allows `Construction` and `Event`.
- **Request used** (one call, all layers, 670,897 bytes):
  `GET https://gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer/query?layerDefs={"0":"1=1","2":"1=1","3":"1=1","4":"1=1","9":"1=1","10":"1=1"}&returnGeometry=true&outSR=4326&f=json`.
  For a connector, query the three line layers one by one:
  `.../FeatureServer/{0|2|3}/query?where=status='Approved'&outFields=*&outSR=4326&f=geojson`.
- **Layers.** 0 "No Access" (31 lines), 2 "Partial Access" (12 lines),
  3 "Local Access Only" (4 lines). Layers 4 (named "No Acccess"), 10 and 9
  repeat the same closures as one point each (same `closureid`); use them only
  if a point is wanted. Layers 1 and 5-8 were not listed.
- **Pagination.** `maxRecordCount` 2000; `supportsPagination` true
  (`resultOffset`, `resultRecordCount`). 47 records today. Formats: JSON,
  geoJSON, PBF.
- **Fields.**
  - Stable id: `closureid` (`NA-000025`, `PA-000011`, `LAO-000004`; the prefix
    is the closure type; 47 unique across the three line layers). Also
    `globalid` (GUID) and `OBJECTID`.
  - Text: `description` (free text, empty for 6 of 47); `altroute` and `url`
    empty today.
  - Type: `reason` (domain Construction, Event, Hazard, Flood Damage; today 44
    Flood Damage, 2 "Flooding" (not in the domain), 1 Hazard);
    `closuretype` (No Access, Partial Access, Local Access Only);
    `accesstype` (No Access 31, Proceed When Safe 11, Local Access Only 4,
    Stop and Go 1); `laneimpact` (All Lanes, Some Lanes, One Lane Open);
    `accessallowed` (Local Access, Critical Services, Police and Fire, No
    Access; empty for 17).
  - Times: `starttime`, `endtime`, epoch milliseconds; the layers declare
    `dateFieldsTimeReference` = UTC. Today every `endtime` is null
    (open-ended); start times run from 25 August to 9 October 2026.
  - Status / verification: `status` with domain Pending, Approved,
    Disapproved. All 47 are `Approved` today; filter on it. `activeincid`
    (Yes/No) is null for all.
  - Geometry: polyline `paths` (WGS84 lon/lat with `outSR=4326`; bounding box
    18.08 to 23.93 E, 31.49 to 34.02 S). Also `startx`, `starty`, `endx`,
    `endy` (lon/lat degrees) and `STARTKM`, `ENDKM`.
  - Road: `road_number` / `RID` (provincial road number, all records);
    `street` (7 of 47, e.g. `R363`, `Voortrekker Street`);
    `district_municipality`.
  - Direction and severity: none (closure type and lane impact are the
    nearest).
  - Do not store: `pocname` (district office codes), `pocemail`, `pocphone`
    (empty today), `created_user`, `last_edited_user` (staff accounts).
- **Ended records.** None today, and no end times are set, so it is not known
  whether a reopened road is end-dated or deleted. A connector should end an
  event when its `closureid` disappears, and skip any record whose `endtime`
  is in the past.
- **Update frequency.** Not published. Records were created between 25 August
  and 9 October 2026; the last edit was 9 October 2026 10:51 UTC; the service
  item was last modified 14 September 2026.
- **Rate limit.** None published.
- **Detours.** `gis.westerncape.gov.za/hosting/rest/services/Hosted/Road_Closures_Detours_Public_View/FeatureServer/0`
  (fields `detourid`, `closureglobalid`, `starttime`, `endtime`, line
  geometry): 0 records today.
- **Attribution.** The WCG terms ask, for non-commercial reuse: "The source
  must be acknowledged including the URL and copyright status of the
  material." Commercial reuse needs written permission, which would set its
  own wording.
- **Ways to fix the licence.** (1) Ask service@westerncape.gov.za for written
  permission for commercial reuse, as the terms say. (2) Ask for the layer to
  be published on the WCG Open Data Portal
  (`wcg-opendataportal-westerncapegov.hub.arcgis.com`), where four of the five
  layers seen carry "CC BY" in their licence field; the WCG Open Data Policy (April 2023,
  section 8.5) says dataset requests go to PDO@westerncape.gov.za.
- **Sample:** `wcg-doi-road-closures_2026-10-15.json` (research scratchpad,
  `research/south-africa/`).

Two records (trimmed; times converted in the notes):

```json
{"layer": 0, "attributes": {"closureid": "NA-000025", "RID": "MR00547", "road_number": "MR00547",
 "street": "R363", "reason": "Flood Damage", "description": "Bridge overtopping / Structure Damage ",
 "laneimpact": "All Lanes", "closuretype": "No Access", "accesstype": "No Access", "status": "Approved",
 "starttime": 1787641742850, "endtime": null, "STARTKM": 1.66, "ENDKM": 2.00,
 "district_municipality": "West Coast", "globalid": "{AB2ABA50-90D6-49A2-8ED5-C28667393653}"},
 "geometry": {"paths": [[[18.620355, -31.778171], [18.620249, -31.778146], "..."]]}}
```

Start 25 August 2026 07:09 UTC; no end.

```json
{"layer": 2, "attributes": {"closureid": "PA-000011", "RID": "TR07501", "road_number": "TR07501",
 "street": null, "reason": "Flood Damage", "description": "Oudtshoorn to Holgate, One lane open\n\n",
 "laneimpact": "One Lane Open", "closuretype": "Partial Access", "accesstype": "Stop and Go",
 "status": "Approved", "starttime": 1787654660589, "endtime": null, "STARTKM": 23.23, "ENDKM": 21.61,
 "district_municipality": "Garden Route", "globalid": "{DFC5EF71-AEF2-402F-96AD-112D6276B217}"},
 "geometry": {"paths": [[[22.25837, -33.684814], [22.258078, -33.684793], "..."]]}}
```

Start 25 August 2026 10:44 UTC; no end.

## RED

| Source | Authority | What was found | Why not usable |
| --- | --- | --- | --- |
| i-TRAFFIC REST API | SANRAL (national roads; regions Gauteng, KwaZulu-Natal, Western Cape, Eastern Cape) | [API page](https://www.i-traffic.co.za/developers/help): GetEvents, GetRoadways, GetCameras, GetMessageSigns, GetAlerts; "Requires a developer key"; "Throttling is enabled. 10 calls every 60 seconds." Without a key `/api/v2/get/event?format=json` returns HTTP 400 `Invalid Key`. | Two blockers. Key needed (not registered). [Terms](https://www.i-traffic.co.za/termsandconditions): "Redistribution or republication of any part of i-traffic.co.za or its content is prohibited ... without the prior express written consent of SANRAL"; users may not "distribute or otherwise use the content for any personal, public or commercial purpose" or "Use any robot, spider or other similar kind of automatic programme". robots.txt disallows `/list/getdata/` and `/eventdetails/` (the website's own data calls), not `/api/`. Would need a key and SANRAL's written consent. |
| City of Cape Town Open Data Portal and `citymaps.capetown.gov.za` ArcGIS server | City of Cape Town | Portal search "road": 24 items; organisation search for closure, incident, event, traffic: 43 items; server folders `Theme_Based/Transport`, `Facility_Booking_Streets`, `BU_Film_Permitting`, `AT_EVNT_TBL` | No closure, roadworks or event layer. Nearest: Traffic Accidents (Crash Data) statistics 2019-2024 (historical), Service Requests Jan 2023 to present (residents' fault reports, not confirmed road events), film permitting sites (static). City closures appear as media releases and PDFs (e.g. SONA 2026 road closures schedule), without coordinates. |
| eThekwini Open Data Portal | eThekwini (Durban) | 81 public items of `opendata_ethekwini`; portal search "road": Street Address, Informal Units | No road events. The "eThekwini Municipality Traffic" web map (2018) shows Esri's World Traffic Service (a commercial subscription layer) and an origins-to-destinations layer. |
| Tshwane e-GIS server | City of Tshwane | `e-gis001.tshwane.gov.za/robots.txt`: `User-agent: *` / `Disallow: /`. Items seen: Road Centerlines, Road Master Plan | robots.txt disallows everything; no road-event layer seen. |
| Ekurhuleni "Live Traffic" web map | City of Ekurhuleni | Web map from 2014 | Its only layer is Esri's World Traffic Service (commercial). |
| Johannesburg Roads Agency | JRA | Search found traffic advisories as PDFs (e.g. Modderfontein Road carriageway closure, 23 January 2024; M1/M2 closures 2024); the home page links a WordPress news feed (`jra.org.za/feed/`); robots.txt 404 | Text and PDF only, no coordinates. |
| Western Cape road closure notices | WCG Department of Infrastructure | News articles on `westerncape.gov.za/infrastructure` ("Western Cape road closures due to storm") | Text; the GIS layer above is the machine-readable version. |
| Esri Community Maps road closures | Esri (local governments contribute) | Contributors layer queried with a South Africa bounding box: 0 contributors | No South African data. |
| Road Traffic Management Corporation | RTMC | Home page: traffic reports (calendar, Easter, festive) and social media links | No event feed. |
| Arrive Alive; trafficinformation.co.za | Road-safety information sites | News articles and an RSS subscription page | News/text; out of scope. |
| N3 Toll Concession, TRAC N4 | Toll-road concessionaires | Search found only traffic advisories as news posts, helplines and X accounts (pages not fetched) | Text only; no feed found. |
| KwaZulu-Natal and Gauteng transport departments; Nelson Mandela Bay; Buffalo City | Provinces and metros | Searches found only news articles and SAnews notices (e.g. Tshwane Metro Police closures for a march on 30 June 2026) | No machine-readable feed found. |
| CSIR-hosted RAMS road networks (`pta-gis-2-web1.csir.co.za`) | CSIR for Johannesburg, Tshwane, Ekurhuleni, Sedibeng | Seen in search results: road-network layers; the Johannesburg one is a 2015 snapshot | Static road assets, not events. |

Excluded without testing, as commercial providers: TomTom, HERE, Waze,
Google, INRIX, Esri's World Traffic Service, and the third-party aggregator
ourpower.co.za.

## What four GREEN sources would need

Even with every permission granted, South Africa has two official
machine-readable road-event sources today, not four:

1. **Western Cape public road closures:** written permission for commercial
   reuse from service@westerncape.gov.za, or publication on the WCG Open Data
   Portal (CC BY), requested via PDO@westerncape.gov.za.
2. **SANRAL i-TRAFFIC:** a developer key and SANRAL's written consent to
   redistribute (contact through `i-traffic.co.za/contact`). This is the only
   source for national roads and the Gauteng, KwaZulu-Natal and Eastern Cape
   regions.

Cape Town, Johannesburg, eThekwini, Tshwane and the other metros would first
have to publish closures as data; today they publish text, PDFs and social
media posts only.

## Access-rule notes

- Tshwane: the services directory root was fetched in the same command as
  robots.txt, which disallows everything (one request). Nothing else was
  fetched there.
- `www.arcgis.com`: about 65 small requests to the public search and item API
  while looking for South African layers across many organisations, above the
  guideline of about 10 per host.
- `citymaps.capetown.gov.za`: 11 requests (robots.txt, directory listings,
  one portal search that returned 404).
- The Cape Town ArcGIS Hub asks for `Crawl-delay: 60`; its one search came
  about a minute after robots.txt and may have been slightly early.
- i-TRAFFIC: one call to `/api/v2/get/event?format=json` without a key, to
  confirm the key requirement. The path is the usual one for this 511 platform
  and is not printed on the documentation page. No key was tried.
