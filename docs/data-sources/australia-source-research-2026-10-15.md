# Source research, 15 October 2026: Australia

The user wants at least four working official sources for Australia. Each
candidate below was fetched live on 15 October 2026 between 08:17 and 08:47
UTC (18:17-18:47 in Brisbane, 16:17-16:47 in Perth) with the User-Agent
`JSAN-REI/1.0 (road event intelligence; source research)`, and its licence
or terms were read. Nothing was bypassed: no browser disguise, no proxies, no
guessed keys, no keys registered. The research machine's address is in India
(ipinfo.io: `IN`), which matters for South Australia (below). No code was
changed. Raw samples are in the session scratchpad under
`research/australia/` (file names in the tables).

"Current" means the start is not in the future and the end has not passed (or
there is no end); "upcoming" means the start is in the future; "ended" means
the end has passed but the record is still served.

**Result: five sources are GREEN** (Main Roads WA, City of Gold Coast, Roads
ACT, City of Wodonga and the national harmonised dataset), two of them with a
licence point for the user to decide. **Six are YELLOW**, including QLDTraffic
(its key is printed in its own specification) and the NSW and Victorian APIs
(registered key).

## GREEN

| Source | Authority | Endpoint | On 15 Oct | Location | Licence (where read) | robots.txt |
| --- | --- | --- | --- | --- | --- | --- |
| Main Roads WA WebEOC: events, incidents, roadworks, closures | Main Roads Western Australia | `services2.arcgis.com/cHGEnmsJ165IBJRM/arcgis/rest/services/WebEoc_*/FeatureServer` (same layers in `WebEocFeatureLayerViewPRD`) | 279 records: roadworks 248 (172 current, 76 upcoming); events 18 (5 current, 13 upcoming); incidents 11 (no dates, all live); closure lines 2. None ended | Points (roadworks, events, incidents); lines (closures). 100% located. `outSR=4326` works (native 3857) | CC BY 4.0: [WA catalogue](https://catalogue.data.wa.gov.au/dataset/mrwa-webeoc-roadworks) and the ArcGIS item licence | No robots file (`/robots.txt` answers 403 "Invalid URL") |
| City of Gold Coast temporary road closures | City of Gold Coast | `services.arcgis.com/3vStCH7NDoBOZ5zn/arcgis/rest/services/Temporary_Road_Closure/FeatureServer/0` | 1,275 records: 1,207 not ended, 68 ended. In the first 1,000: 899 current, 42 upcoming, 59 ended. 579 of the 1,275 are footpath or parking-lane only | Lines (995 LineString, 4 MultiLineString, 1 without geometry in the first 1,000). `outSR=4326` works (native EPSG:28356) | CC BY 3.0 Unported: [item info](https://services.arcgis.com/3vStCH7NDoBOZ5zn/arcgis/rest/services/Temporary_Road_Closure/FeatureServer/info/itemInfo?f=json) | No robots file (403 "Invalid URL") |
| Roads ACT planned road closures (Temporary Traffic Management plans) | ACT Government, Transport Canberra and City Services (Roads ACT) | `services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/Road_Closures_public_view_HISTORICAL/FeatureServer/0` | 140 records: 112 current, 28 upcoming, 0 ended. All 140 approved | Points, 140/140, WGS84 | **CC BY-SA 4.0** (share-alike): [ACT Open Data, gcdw-wgd8](https://www.data.act.gov.au/d/gcdw-wgd8) | No robots file (403 "Invalid URL") |
| City of Wodonga upcoming roadworks | City of Wodonga (Victoria) | `services-ap1.arcgis.com/w6r4LlwgJu8O0neQ/arcgis/rest/services/Traffic_management_plan_5_view/FeatureServer` | 16 works (12 current, 4 upcoming) with 11 closures, 10 disruptions, 7 detours. None ended | Polygons (works) and lines (closures, disruptions, detours), all located, WGS84 | CC BY 4.0: [ArcGIS item](https://www.arcgis.com/sharing/rest/content/items/166e7348dc5248a98ba8bd5123503457?f=json) | No robots file (403 "Invalid URL") |
| Harmonised National Roadworks and Road Closures ("RADAR") | Australian Government, DITRDCSA (National Freight Data Hub) | `spatial.infrastructure.gov.au/server/rest/services/Hosted/RADAR_Curated_Prod_roadworks/FeatureServer/0` | 10,833 records still in the state feeds (captured 15 Oct): 10,055 current, 634 upcoming, 144 ended. VIC 8,202; SA 979; NSW 906; QLD 476; ACT 149; NT 80; TAS 37; WA 4 | Points, 1,500/1,500 in the sample, WGS84 | **Conflict:** CC BY 4.0 on the [Digital Atlas of Australia item](https://www.arcgis.com/sharing/rest/content/items/347fff3d5d3746459cee8044e7995b16?f=json); "Licence not specified" on the [DITRDCSA catalogue](https://catalogue.data.infrastructure.gov.au/dataset/harmonised-national-roadworks-and-road-closures) | No robots file (`/robots.txt` 404) |

Samples: `mrwa-webeoc_2026-10-15.json` (194 KB),
`goldcoast-temp-road-closures_2026-10-15.geojson` (621 KB, first 1,000),
`act-roads-planned-closures_2026-10-15.geojson` (115 KB),
`wodonga-upcoming-roadworks_2026-10-15.json` (37 KB),
`radar-national-roadworks_2026-10-15.geojson` (1.3 MB, first 1,500 captured
today, ordered by state, so it holds only ACT, NSW, NT and QLD rows).

None of these endpoints needed a key, a login or a challenge. ArcGIS hosts
publish no rate limit for these services.

Two points for the user:

- **Roads ACT is CC BY-SA 4.0.** Commercial use is allowed, but adapted data
  must be shared under the same licence. This is the same kind of question as
  the ODbL portals in the [14 October research](source-research-2026-10-14.md).
- **The national dataset's licence is stated in only one of two official
  places.** The Digital Atlas item reads "License: Creative Commons
  Attribution 4.0 . Access rights: Open", credit "@ Commonwealth of Australia
  (Department of Infrastructure, Transport, Regional Development,
  Communications, Sport and the Arts)". The department's own catalogue says
  "Licence not specified", and the service's item says the information "includes
  material provided by parties other than the Commonwealth of Australia".
  It is also refreshed **nightly**, not live.

## Connector notes (GREEN)

### Main Roads WA WebEOC

- **Endpoints** (the catalogued ones; each answers the same records as the
  Travel Map view `WebEocFeatureLayerViewPRD`, checked for roadworks: 248 =
  248):
  - events `.../WebEoc_Events/FeatureServer/0/query`
  - road incidents `.../WebEoc_RoadIncidents/FeatureServer/1/query`
  - roadworks `.../WebEoc_Roadworks/FeatureServer/2/query`
  - road closures (lines) `.../WebEoc_RoadClosures/FeatureServer/4/query`
  - The view also has layer 3, traffic signal outages (not fetched).
- **Query used:** `query?where=1=1&outFields=*&outSR=4326&f=json` (or
  `f=geojson`). The sample is one request to the view's service-level query
  with `layerDefs={"0":"1=1","1":"1=1","2":"1=1","4":"1=1"}`.
- **Pagination:** maxRecordCount 2,000; today's counts are far below it.
- **Fields:**
  - Ids: `Id` is the WebEOC id; a closure line has the same `Id` as its
    incident (236828 is in both layers). `GlobalID` is also present. `FID`
    is per layer.
  - Text: `EventName`/`EventDescr` (events), `Location` (incidents),
    `Descriptio` (roadworks).
  - Type: `EventType` (Sports Event 12, Concert 3, Public Celebration 2,
    Exhibition 1), `IncidentTy`, `WorkType` (Maintenance, Upgrades, Utility
    works, Resurfacing, PTA Works).
  - Road: `Road`, `LocalRoadName`; also `Suburb`, `Region`.
  - Impact: `TrafficImp` (free text), `TrafficCon` (incidents: All Lanes
    Open, Road Closure, Reduced to single lane, Lane Closures Unknown) and
    `ClosureTyp` (Road open with caution, ...).
- **Times:** `DateTimeSt`/`DateTimeEn` (events) and `DateStarte`/`EstimatedC`
  (roadworks) are strings `dd/mm/yyyy HH:MM:SS` in WA local time (UTC+8), with
  no offset. Incidents have no start or end. Their `EntryDate`/`UpdateDate`
  were 15/10/2026 14:33:49-50 on every incident, which looks like the reload
  time rather than when each incident began.
- **Status, confirmation:** there is no status or verification field.
  `WorkStatus` is empty on all 248 roadworks; `publishExt` is "Yes" on all
  incidents. No ended records were served. No severity or direction field
  (direction appears only in text).
- **Update:** the item snippet says "Information updated every 5 min from
  WebEOC". The layer was last edited 2026-10-15 08:15 UTC.
- **Attribution** (ArcGIS item licence for
  [WebEOC Roadworks](https://www.arcgis.com/home/item.html?id=fd5f10e101a9415aa26884c403e16849)):
  "The Commissioner of Main Roads is the creator and owner of the data and
  Licenced Material, which is accessed pursuant to a Creative Commons
  (Attribution) Licence, which has a disclaimer of warranties and limitation
  of liability."
- **Examples** (trimmed):

```json
{"Id": 82807, "DateStarte": "06/04/2026 21:00:00", "EstimatedC": "06/04/2027 04:00:00",
 "WorkType": "Maintenance", "Road": "Mitchell Fwy", "Region": "Metro",
 "Descriptio": "Mitchell Fwy between Roe St and Butler Blvd, various suburbs - Maintenance\r\n9pm to 4am",
 "TrafficImp": "Lane closures and speed reduction in place",
 "geometry": {"x": 115.80126, "y": -31.88653}}
{"Id": 7284, "EventType": "Sports Event", "EventName": "Run Bibbulmun Track Stage Race",
 "Road": "South Coast Hwy (H009)", "DateTimeSt": "23/10/2026 07:45:00", "DateTimeEn": "25/10/2026 13:00:00",
 "Suburb": "Shire of Denmark", "geometry": {"x": 116.90360, "y": -34.99451}}
```

### City of Gold Coast temporary road closures

- **Endpoint:** `.../Temporary_Road_Closure/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&resultRecordCount=1000&f=geojson`
- **Pagination:** maxRecordCount 1,000 (`exceededTransferLimit: true` at
  1,000 of 1,275). Page with `resultOffset` and `orderByFields=OBJECTID`.
- **Fields:**
  - Id: `GlobalID` is the stable id. `TRC_ID` is the permit number, shared
    by several segments (232 permit numbers repeat in the first 1,000); 5
    have none.
  - Road: `STREET`, `SUBURB`. In at least one row `STREET` and `TRC_ID` are
    swapped (`STREET: "TRCI/2025/745"`, `TRC_ID: "Christensen Road South"`).
  - Type: `CLOSURE_CATEGORY` (Developer, Utilities, Construction,
    Maintenance, Road reseal rehabilitation, Special event, Filming).
  - Extent: `CLOSURE_EXTENT`, which is the nearest thing to severity. All
    1,275: Footpath 375, Part closure 294, Hold and release 293, Parking lane
    204, Full closure 101, Multiple long-term impacts 8.
  - Other: `OPERATION_TIMES` (free text such as "06:30 - 18:30"), `COMMENTS`.
- **Times:** `START_DATE`/`FINISH_DATE` are epoch ms. 992 of 1,000 starts
  are 14:00 UTC, which is local midnight (AEST, UTC+10), so treat them as
  dates. Daily hours are only in `OPERATION_TIMES`. 42 of the first 1,000
  have no finish date; 7 have no start.
- **Status:** `ACTIVE_CLOSURE` was "Yes" on all 1,000 sampled. Ended records
  are still served (68 of 1,275); filter with
  `FINISH_DATE >= TIMESTAMP '...' OR FINISH_DATE IS NULL`. There is no
  confirmation field; the records are permits.
- **Update:** layer last edited 2026-10-11 20:19 UTC.
- **Attribution:** licence text "This work is licensed under a Creative
  Commons Attribution 3.0 Unported License"; access information "City of
  Gold Coast". No set wording beyond that.
- **Examples:**

```json
{"GlobalID": "f1d7f300-5001-45c9-9b55-aed9a2221e2a", "TRC_ID": "TRC/2026/992", "STREET": "Proposed Road",
 "SUBURB": "Jacobs Well", "START_DATE": 1782828000000, "FINISH_DATE": 1877436000000,
 "OPERATION_TIMES": "00:00 - 23:59", "CLOSURE_CATEGORY": "SPECIAL EVENT", "CLOSURE_EXTENT": "FULL CLOSURE",
 "ACTIVE_CLOSURE": "Yes", "geometry": {"type": "LineString", "coordinates": [[153.33825, -27.76582], "..."]}}
{"GlobalID": "d966718d-78ca-48cd-bca2-4c1cfcf59a56", "TRC_ID": "Christensen Road South", "STREET": "TRCI/2025/745",
 "SUBURB": "Stapylton", "START_DATE": 1763906400000, "FINISH_DATE": 1793368800000,
 "CLOSURE_CATEGORY": "UTILITIES", "CLOSURE_EXTENT": "FULL CLOSURE",
 "COMMENTS": "Installation of DN800 sewer main ...", "geometry": {"type": "LineString", "coordinates": [[153.24656, -27.74564], "..."]}}
```

### Roads ACT planned road closures

- **Endpoint:** `.../Road_Closures_public_view_HISTORICAL/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
  The layer is named `ALL_TTM_Plan_Applications`. Despite "HISTORICAL" in
  the service name, it held only 140 records today, none ended. It is the
  "JSON Feed" of the ACT dataset *Temporary Traffic Management (TTM) -
  Planned Road Closures (Live Stream)*.
- **Pagination:** maxRecordCount 1,000.
- **Fields:**
  - Id: `globalid` (also `objectid`).
  - Text: `projectTitle`, `roadsClosed` (direction and extent only in this
    text), `reasonRoadClosure`, `describeActivity`, `suburb1`.
  - Type: `type`. Today: buildingConstruction 42, roadWorks 37, lightRail
    25, specialEvent 19, utilities 11, other 4, telecommunications 2.
  - No severity or direction field.
- **Times:** `startTimeClosure`/`endTimeClosure` are epoch ms (UTC) with real
  times (for example 20:00 UTC = 07:00 AEDT).
- **Confirmation:** `roadsDelegateClosure` and `tccsCommsClosure` were "yes"
  on all 140, and `roadsApprovalTimestamp` was present on all 140. This is
  the only GREEN source with an explicit approval mark.
- **Update:** ACT metadata says "Update Frequency: Real time". The layer was
  last edited 2026-10-15 05:49 UTC.
- **Attribution:** "Transport Canberra and City Services - Roads ACT" (the
  dataset's attribution field), under CC BY-SA 4.0.
- **Not used:** the companion "Unplanned Road Closures (Live Stream)",
  `Public_Temporary_Road_Closures/FeatureServer/0`. It has 11 records, all
  "untilFurtherNotice", started 2016 or earlier (for example a car park closed
  since 2016), last edited 2026-09-23. These are not live incidents.
- **Examples:**

```json
{"globalid": "179ebfa0-38f2-4b8f-aea7-c6950f290db8", "projectTitle": "The Golden Oar 2026", "type": "specialEvent",
 "roadsClosed": "John Cardiff Close - Northbound and southbound from the designated carpark adjacent to the Red Shed Rowing Club. ",
 "suburb1": "ACTON", "startTimeClosure": "2026-10-29T20:00:00Z", "endTimeClosure": "2026-11-01T06:00:00Z",
 "roadsDelegateClosure": "yes", "roadsApprovalTimestamp": "2026-06-25T22:23:18Z",
 "geometry": {"type": "Point", "coordinates": [149.10036, -35.29066]}}
{"globalid": "be8c9ad9-28b6-4ca4-865b-92a093006cfb", "projectTitle": "National Security Office Precinct (NSOP)",
 "type": "buildingConstruction", "roadsClosed": "Windsor Walk will be closed at Blackall Street.", "suburb1": "BARTON",
 "startTimeClosure": "2024-10-13T14:00:00Z", "endTimeClosure": "2029-12-30T14:00:00Z", "roadsDelegateClosure": "yes",
 "geometry": {"type": "Point", "coordinates": [149.13198, -35.30750]}}
```

(Times shown as ISO here; the feed gives epoch ms.)

### City of Wodonga upcoming roadworks

- **Endpoint:** `.../Traffic_management_plan_5_view/FeatureServer/query?layerDefs={"0":"1=1","2":"1=1","3":"1=1","4":"1=1"}&returnGeometry=true&outSR=4326&f=json`.
  Each layer is also available on its own, e.g. `/3/query` for closures.
- **Layers:**
  - 0, Impact area (polygons): the parent works record, with `application_ID`,
    `RW_location`, `RW_description`, `RW_traffic_impact`, `RW_start`,
    `RW_end`.
  - 2, Disruptions (lines): `DR_street`, `DR_lane_impact`, `DR_reason`, ...
  - 3, Closures (lines): `CL_street`, `CL_lane_impact`, `CL_access`, ...
  - 4, Detours (lines): `DT_street`, ...
  - Children link to the parent through `parentglobalid` = parent
    `globalid`.
- **Times:** epoch ms (UTC) with real times.
- **Confirmation:** none per record, but the description says "Only roadworks
  consented by council are included."
- **Volume:** small, as Wodonga is a regional city. The item was modified
  2026-03-05; the closures layer was last edited 2026-10-13 03:57 UTC.
- **Attribution:** "Licensed under CC BY 4.0"; access information
  "Wodonga council".
- **Examples:**

```json
{"layer": "Impact area", "globalid": "72011c3c-7e74-4af3-8e16-75def510ab66", "application_ID": "APP-2610131254-48",
 "RW_location": "Woodland Street, Wodonga Vic 3690", "RW_traffic_impact": "Short_term_mobile_works,Application_includes_speed_reduction",
 "RW_start": "2026-10-20T22:30:00Z", "RW_end": "2026-10-21T15:30:00Z", "geometry": {"rings": [[[146.88629, -36.12634], "..."]]}}
{"layer": "Closures", "CL_ID": "CL-2610131254-9", "CL_street": "WOODLAND STREET", "CL_lane_impact": "Alternating one way",
 "CL_description": "Single Lane Closure with Speed Reduction", "CL_access": "Local Access",
 "CL_start": "2026-10-20T22:30:00Z", "CL_ends": "2026-10-21T15:30:00Z", "parentglobalid": "72011c3c-7e74-4af3-8e16-75def510ab66",
 "geometry": {"paths": [[[146.88627, -36.12632], [146.87761, -36.12510], "..."]]}}
```

### Harmonised National Roadworks and Road Closures (RADAR)

- **Endpoint:** `.../RADAR_Curated_Prod_roadworks/FeatureServer/0/query?where=capture_date >= DATE '2026-10-15'&outFields=*&outSR=4326&resultRecordCount=2000&orderByFields=state,id&f=geojson`.
- **Pagination:** maxRecordCount 2,000; page with `resultOffset`. The
  [API user guide](https://aueprod01ckanstg.blob.core.windows.net/public-catalogue/c4a4a249-e2fb-4636-be4f-26bd448ba38b/Harmonised%20National%20Roadworks%20and%20Road%20Closures%20dataset%20API%20User%20Guide_Dec2024.pdf)
  says the dataset holds more than 170,000 records (history since 2016), so a
  `capture_date` filter is needed.
- **`capture_date`:** the guide calls it "the date the record was first
  captured", but every record still in today's state feeds had
  `capture_date` = 2026-10-15. That includes an ACT closure from 2005. It
  behaves like a "last seen" date: filter on it to get what the states list
  today.
- **Fields:**
  - Ids: `id` (NFDH), `unique_identifier` (source id, e.g. `qld-248797`,
    `nsw-95130`).
  - Category: `category`/`updated_category` (harmonised), `type` (source).
  - Text: `description`; road: `street_name`, `side_street`,
    `end_side_street`; `direction`; `state`; `source_url` (the upstream
    feed).
  - Times: `from_date`, `to_date`, `planned_start_date`, `planned_end_date`,
    `modified_date`, all epoch ms UTC.
  - `lv_access`/`hv_access`: derived 1/0, "based on Road Closure status".
  - `status` is "not harmonised". Today: NSW Open/Closed, QLD
    Published/Reopened, NT CURRENT, VIC Active/Pending/Reopened, ACT
    untilFurtherNotice or empty, SA/TAS/WA empty. No verification field.
  - No end date on 495 of the 1,500 sampled.
- **Upstream feeds** (`source_url` today): TfNSW `api.transport.nsw.gov.au`
  hazards (key-protected for us), Victoria's `api.opendata.transport.vic.gov.au`
  planned and unplanned (key-protected), SA `maps.sa.gov.au` TrafficSAOpenData
  (geo-blocked for us), QLDTraffic, NT Road Report, Tasmania's WFS, Roads ACT,
  and for WA only the Main Roads closures layer (4 rows; WA roadworks and
  events are missing). Its unique keyless value is VIC, NSW and SA; it
  overlaps the direct feeds elsewhere.
- **Update:** "Data is refreshed on a nightly basis"; last edit 2026-10-14
  16:50 UTC.
- **Examples:**

```json
{"unique_identifier": "nsw-95130", "state": "NSW", "status": "Open", "category": "Hazard",
 "type": "CHANGED TRAFFIC CONDITIONS", "street_name": "Lobs Hole Ravine Road", "side_street": "Snowy Mountains Highway",
 "from_date": 1550559600000, "to_date": 1801393200000, "direction": "Both directions",
 "source_url": "https://api.transport.nsw.gov.au/v1/live/hazards/incident/all",
 "geometry": {"type": "Point", "coordinates": [148.38606, -35.75316]}}
{"unique_identifier": "qld-248797", "state": "QLD", "status": "Published", "category": "Road Closure",
 "type": "Hazard, Road damage", "street_name": "Duck Creek Road", "from_date": 1504654740000, "to_date": null,
 "lv_access": 0, "hv_access": 0, "geometry": {"type": "Point", "coordinates": [153.08256, -28.17787]}}
```

## YELLOW

| Source | Authority | What it gives | The one problem | Sample |
| --- | --- | --- | --- | --- |
| QLDTraffic GeoJSON API `api.qldtraffic.qld.gov.au/v2/events` | Queensland Department of Transport and Main Roads | 529 events today: 459 current, 68 upcoming, 2 ended. Roadworks 344, hazards 118, flooding 61, crashes 4, special event 1, congestion 1. Includes 55 Transport for NSW and many council records. Geometry on 529/529 (MultiLineString 388, MultiPoint 133, GeometryCollection 8), EPSG:7844 (GDA2020 longitude/latitude) | **Needs a key**, but the publisher prints one for anyone. [API specification v1.10](https://qldtraffic.qld.gov.au/media/moreDevelopers-and-Data/qldtraffic-website-api-specification-v1-10.pdf?lang=en-AU), section 2.1.1.1: "A public API key, shown below, is available for developers who do not wish to register and receive their own API key: "apikey": "3e83add325cbb69ac4d8e5bf433d770b". This key is globally limited to 100 requests/minute." Without it: HTTP 401. Licence (section 2.1): "Use of the data must be in accordance with the Creative Commons Attribution 4.0 Australia (CC BY 4.0 AU) license." `qldtraffic.qld.gov.au/robots.txt` has only a Sitemap line; the API host has no robots file | `qldtraffic_2026-10-15.json` (2.4 MB, whole feed; the API has no limit parameter) |
| Transport for NSW Live Traffic Hazards `api.transport.nsw.gov.au/v1/live/hazards/...` | Transport for NSW | Incidents, roadworks, floods, fires, major events (per the [dataset page](https://opendata.transport.nsw.gov.au/data/dataset/live-traffic-hazards)) | **Registered key.** Keyless request today: HTTP 401 "The calling application is unauthenticated." Both resources say "Login to download". Licence page: CC BY 4.0 "on the condition that Transport for NSW is attributed as the source" ([datalicence](https://opendata.transport.nsw.gov.au/datalicence)) | none (401) |
| Victoria DTP planned and unplanned road disruptions `api.opendata.transport.vic.gov.au/...` | Victorian Department of Transport and Planning | Disruptions on DTP and council roads. The national dataset holds 8,202 Victorian records from these two feeds today | **Registered key.** Keyless request: HTTP 401, `WWW-Authenticate: ... "Failed to find key field: KeyId"`. [Dataset page](https://opendata.transport.vic.gov.au/dataset/unplanned-disruptions-road): "The API Key is to be used in the request header. Header name is 'KeyID'. This API endpoint has a rate limit of 20 calls per 60 seconds ... refreshed every 60 seconds." Licence: CC BY 4.0 | none (401) |
| NT Road Report `roadreport.nt.gov.au/api/Obstruction/GetAll` | NT Department of Logistics and Infrastructure (Road Report NT) | 82 records, all `status: CURRENT`, none with an end date. Restriction types: With Caution 38, Weight And Or Vehicle Type Restriction 20, Road Closed 13, High Clearance 4WD 5, Impassable 3, Lane Closure 2, 4WD 1. Obstruction types include Roadworks 32, Road Damage 11, Flooding 5. Every record has `startPoint` and `endPoint`, given as **[latitude, longitude]** | **Licence unclear.** The site's own JSON, listed in the national catalogue as "[Roadworks endpoint NT](https://catalogue.data.infrastructure.gov.au/dataset/roadworks-endpoint-nt)" with "Licence not specified". The [NT Government copyright notice](https://nt.gov.au/page/copyright-disclaimer-and-privacy): "No part of this website may be reproduced or reused for any purpose whatsoever, apart from: fair dealing ... or where expressly provided under a Creative Commons licence." No robots rules (`/robots.txt` returns the app's HTML page) | `nt-roadreport_2026-10-15.json` |
| Tasmania State Growth road works WFS `data.stategrowth.tas.gov.au/geoserver/ssg/ows` (`ssg:GEO_ROAD_WORKS`) | Department of State Growth (Transport Tasmania) | 36 roadworks on state roads: 35 current, 1 upcoming. Lines, 36/36. Native EPSG:28355; `srsName=EPSG:4326` works. Times are all `T00:00:00Z` (dates). Each record names a contractor and a mobile number | **Licence unclear.** National catalogue "[Roadworks endpoint Tas](https://catalogue.data.infrastructure.gov.au/dataset/roadworks-endpoint-tas)": "Licence not specified". The [Tasmanian Government copyright page](https://www.tas.gov.au/codi), linked from transport.tas.gov.au: "a licence to download, print and reproduce the information for non-commercial purposes only. If it is indicated on a website that specific information may be used for commercial purposes, users are licensed to the extent expressed." No robots file (404) | `tas-stategrowth-roadworks_2026-10-15.geojson` |
| South Australia TrafficSAOpenData `maps.sa.gov.au/arcgis/rest/services/DPTIExtTransport/TrafficSAOpenData/MapServer` (layers 0 and 1) | SA Department for Infrastructure and Transport | Roadworks, incidents, closures and detours in metropolitan Adelaide. The national dataset holds 979 SA records from it today | **Not testable from here.** Both `robots.txt` and the service answer HTTP 403 from CloudFront: "The Amazon CloudFront distribution is configured to block access from your country." `data.sa.gov.au` also answers 403. Search results give CC BY 3.0 AU (not read). Retry from an Australian or production host; nothing was bypassed | none (403) |

QLDTraffic connector notes, in case the user accepts the published key:

- `features[].properties`:
  - Id: `id` (integer).
  - `status`: only "Published" or "Reopened"; no verification flag.
  - Type: `event_type`, `event_subtype`, `event_due_to`.
  - Impact: `impact.direction`, `impact.impact_type` (Closures 75, Lanes
    affected 315, ...), `impact.impact_subtype`, `impact.delay`.
  - Times: `duration.start`/`duration.end`, ISO 8601 with `+10:00`; 180
    have no end.
  - Severity: `event_priority` (High 105, Medium 293, Low 131; "Red Alert"
    exists).
  - Road: `road_summary.road_name`, `locality`, `local_government_area`.
  - Source: `source.provided_by` (TMR 377, Transport for NSW 55, councils).
  - `last_updated`.
- Feed `rights.owner` says ownership follows each record's `provided_by`.
- `/v2/events/past-one-hour` gives changes for incremental polling.
- The developers page's "authority ... to be displayed will be on a case by
  case basis" refers to third parties **sending** events into QLDTraffic,
  not to reading the feed.

## RED

| Candidate | Reason |
| --- | --- |
| Brisbane City Council "Planned temporary road occupancies" (`data.brisbane.qld.gov.au`) | Two problems: `robots.txt` has `User-agent: *` / `Disallow: /api/` and `Disallow: /explore/dataset/*/download`, and the dataset has **no coordinates**. Its fields are street, cross streets, suburb, ward, closure type, direction, dates and times. It is otherwise current (258 records, modified 2026-10-14) and CC BY 4.0. Its copy on `data.qld.gov.au` answered with an AWS WAF challenge (`x-amzn-waf-action: challenge`), not bypassed |
| City of Melbourne "City Activities and Planned Works" | `data.melbourne.vic.gov.au/robots.txt` disallows `/api/` and every download link goes through `/api/`. The dataset page there now answers 404; the Victorian portal copy says "Last updated 13/06/2024" |
| City of Sydney | No road closure or roadworks dataset in its ArcGIS hub (searches "road closure", "roadworks": none; "traffic": parking, poles) |
| City of Perth | Hub search "closure": 0 results. The "XB Transport App" (CC BY 4.0 on the WA catalogue) is an ArcGIS web app, not a data layer |
| Adelaide City Council | No closure dataset found; metropolitan Adelaide is covered by the state feed (geo-blocked, above) |
| Gold Coast copy on `data.gov.au` GeoServer | `data.gov.au/robots.txt`: `User-agent: *` / `Disallow: /`. Use the City's own ArcGIS service (GREEN) instead |
| Roads ACT unplanned closures live stream | 11 long-term "until further notice" closures from 2016 or earlier; nothing live |
| Live Traffic NSW website JSON (`livetraffic.com`) | Not fetched. The site is a JavaScript app with no robots file, and the same data is offered officially only behind a registered key; reading the site's internal JSON would sidestep that. Its own terms could not be read (JavaScript page; `transport.nsw.gov.au` answered 403 from CloudFront) |
| VicEmergency public feed (`emergency.vic.gov.au/public/osom-geojson.json`) | Reachable and allowed by robots, but not a road-event feed: 39 items, of which 3 road accidents and 1 tree down; the rest fires, burn areas and warnings |
| Commercial providers (TomTom, HERE, Waze, Google, INRIX) | Excluded by the brief |

## Coverage if the GREEN five are connected

- **WA:** Main Roads (state roads).
- **QLD:** Gold Coast council roads only, unless the QLDTraffic key is
  accepted (state-wide, including council and some NSW border records).
- **ACT:** Roads ACT.
- **VIC:** Wodonga, plus the national dataset's 8,202 Victorian records
  (nightly).
- **NSW and SA:** only through the national dataset (nightly).
- **NT and TAS:** only through the national dataset, whose upstream licences
  for these two are themselves unspecified.

## Access-rule slips during this research

- The City of Sydney hub (`data.cityofsydney.nsw.gov.au`) has
  `Crawl-delay: 60`. Three search requests were sent within a few seconds.
- The Gold Coast hub (`data-goldcoast.opendata.arcgis.com`, also
  `Crawl-delay: 60`) got its robots.txt and one search request in the same
  second.
- `spatial.infrastructure.gov.au` got 11 requests, slightly over the "about
  10 per host" aim; one was wasted on a malformed statistics query.
  `services2.arcgis.com` got 10.
- Fetches made with the WebFetch tool (catalogue and documentation pages)
  carry that tool's own User-Agent, not JSAN-REI's.

None of these hosts asked REI to stop; no source was connected.
