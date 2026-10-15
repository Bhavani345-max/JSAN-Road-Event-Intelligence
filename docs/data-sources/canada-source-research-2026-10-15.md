# Canada source research, 15 October 2026

The user asked for at least four working Canadian sources. REI already
connects one: the City of Toronto road restrictions
([toronto-road-restrictions.md](toronto-road-restrictions.md)); Ontario 511
needs a developer key ([source-research-2026-10-14.md](source-research-2026-10-14.md)).
Every candidate below was fetched live on 15 October 2026 between about
08:17 and 08:41 UTC with the User-Agent
`JSAN-REI/1.0 (road event intelligence; source research)`, and its licence or
terms page was read. Nothing was bypassed: no browser disguise, no proxies,
no keys requested or guessed. No code was changed.

How records are counted: **current** = started and not yet ended at fetch
time; **upcoming** = starts later; **ended** = end time already passed (but
still in the feed). Where a feed gives times without a zone, the zone used
for the count is stated.

One raw response per GREEN or YELLOW source was saved (outside the repo) in
the session scratchpad, folder `research/canada/`, as
`<source-id>_2026-10-15.<json|geojson|csv>`.

## GREEN: no key, current records, own geometry, commercial reuse allowed

| Source | Authority | Endpoint | Records on 15 Oct (current / upcoming / ended) | Location | Licence (where read) | robots.txt |
| --- | --- | --- | --- | --- | --- | --- |
| DriveBC Open511 events | Province of British Columbia (DriveBC) | `api.open511.gov.bc.ca/events` | 298: 220 / 78 / 0 | Every record: 207 lines, 91 points, WGS84 | Open Government Licence – British Columbia ([API help](https://api.open511.gov.bc.ca/help), [licence](https://www2.gov.bc.ca/gov/content?id=A519A56BC2BF44E4A008B33FCF527F61)) | None (HTTP 404) |
| Ottawa traffic events | City of Ottawa (Traffic Services) | `traffic.ottawa.ca/map/service/events` | 129: 122 / 2 / 0, plus 5 with no schedule | Every record: 100 multilines, 29 points, WGS84 | Open Government Licence – City of Ottawa, v2.0 ([licence page on the City's open-data hub](https://www.arcgis.com/sharing/rest/content/items/ffbfd6dac7e4483fac63c172806d9122/data?f=json)) | None (HTTP 404) |
| Edmonton traffic disruptions (`k4tx-5k8p`) | City of Edmonton | `data.edmonton.ca/resource/k4tx-5k8p.json` | 1,197 disruptions in 1,788 rows: 108 / 26 open; 1,063 ended, completed or cancelled | Every row: a point (two rows, from and to, for 591 disruptions), WGS84 | Open Government Licence – Edmonton, v1.0 July 2022 ([terms page](https://data.edmonton.ca/stories/s/City-of-Edmonton-Open-Data-Terms-of-Use/msh8-if28/)) | `/resource/` not disallowed |
| Winnipeg lane closures (`h367-iifg`) | City of Winnipeg (Public Works) | `data.winnipeg.ca/resource/h367-iifg.json` | 794: 593 / 108 / 93 | Every row: a multiline, WGS84 | Open Government Licence – Winnipeg ([licence](https://data.winnipeg.ca/open-data-licence)) | `/resource/` not disallowed |
| Calgary construction detours (`w8zq-79bq`) | City of Calgary (Mobility) | `data.calgary.ca/resource/w8zq-79bq.json` | 235: 177 / 50 / 8 | Every row: a point, WGS84 | Open Government Licence – City of Calgary, v2.1 ([terms](https://data.calgary.ca/stories/s/u45n-7awa/)) | `/resource/` not disallowed |
| Montréal works and obstructions (Entraves et travaux en cours) | Ville de Montréal | `donnees.montreal.ca/dataset/667342f7-…/resource/cc41b532-…/download/entraves-travaux-en-cours.csv` | 2,209 permits: 1,895 / 111 / 203 | Every row: a point (lon/lat, WGS84) | CC BY 4.0 ([licence page](https://donnees.montreal.ca/pages/licence-d-utilisation)) | Download path not disallowed (`/api/` is, and is not used) |
| Brampton road closures (BramptonWorks) | City of Brampton | `services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/BramptonWorks_OpenData/FeatureServer/3` | 6: 6 / 0 / 0 | Every record: a line; `outSR=4326` works | "CC BY" (licence field of the City's GeoHub item `2fa980a7a5b04ffca5d19673e0d823b0`) | None (HTTP 403 "Invalid URL") |

That is seven, six of them substantial. Brampton is real but tiny (six
long-running closures).

## Connector notes

### DriveBC Open511 events (`drivebc_2026-10-15.json`)

- **Endpoint:** `GET https://api.open511.gov.bc.ca/events?format=json&status=ACTIVE&limit=500`.
  The help page: default 50 events, maximum 500 per request, `limit` and
  `offset` for paging; filters `status`, `severity`, `event_type`,
  `event_subtype`, `area_id`, `road_name`, `bbox`, `created`, `updated`,
  `in_effect_on`. One call returned all 298 events (804 KB); `pagination`
  was `{"offset": "0"}`.
- **Fields:** id `id` (`drivebc.ca/RIDE-102765`); `headline` holds only the
  type word ("CONSTRUCTION"), so the title must be built from `description`
  and `roads`; type `event_type` (CONSTRUCTION 268, INCIDENT 19,
  ROAD_CONDITION 11) and `event_subtypes` (PLANNED_EVENT 172,
  ROAD_MAINTENANCE 65, ROAD_CONSTRUCTION 31, HAZARD 21, FIRE 4, …);
  `severity` MINOR 270 / MAJOR 28; `roads[]` with `name`, `from`,
  `direction` (BOTH, N, S, E, W) and `state` (CLOSED 16, ALL_LANES_OPEN 281);
  `areas[]` (district); `created`, `updated` (ISO with offset, e.g.
  `2026-09-24T11:02:28-07:00`); geometry `geography` (GeoJSON Point or
  LineString).
- **Times:** `schedule.intervals[]` = `"start/end"`, end empty when open
  (61 events). The values carry no offset. They are **UTC**: "Starting Mon
  Sep 28 until Fri Oct 30. From 7:30 AM to 5:30 PM PDT" is
  `2026-09-28T14:30/2026-10-31T00:30`. The jurisdiction resource names
  `America/Vancouver` as the default zone, which does not match the values.
- **Status:** `ACTIVE` covers both ongoing and planned events (78 of today's
  start later); `ARCHIVED` events are left out unless `status=ARCHIVED` is
  asked for (a test call returned 2019–2023 records). No field says whether
  an event is confirmed; everything is published by DriveBC.
- **Limits:** none published on the help page; the
  [API terms](https://www2.gov.bc.ca/gov/content?id=D1EE0A405E584363B205CD4353E02C88)
  say the provider "may, without notice, impose and or adjust limits".
  Update frequency is not stated.
- **Attribution (OGL-BC):** "Contains information licensed under the Open
  Government Licence – British Columbia." The help page states: "Use of the
  Information provided by this API is governed by the Open Government
  Licence – British Columbia".

```json
{"id": "drivebc.ca/RIDE-103581", "headline": "CONSTRUCTION", "status": "ACTIVE",
 "created": "2026-10-13T09:51:37-07:00", "updated": "2026-10-13T09:54:02-07:00",
 "description": "Road construction from Canyon Road, At Canyon Road and Pumphouse Road to At Canyon Road and Dunwoodie Road and Jackpine Road. Starting Tue Oct 13 until Tue Oct 20. From 8:30 AM to 2:30 PM PDT, every day. Road closure. …",
 "schedule": {"intervals": ["2026-10-13T15:30/2026-10-20T21:30"]},
 "event_type": "CONSTRUCTION", "event_subtypes": ["ROAD_CONSTRUCTION"], "severity": "MINOR",
 "geography": {"type": "LineString", "coordinates": [[-119.1468, 50.53206], [-119.14745, 50.5318], "…"]},
 "roads": [{"name": "Other Roads", "from": "Canyon Road", "direction": "BOTH", "state": "CLOSED"}],
 "areas": [{"name": "Okanagan-Shuswap District", "id": "drivebc.ca/5"}]}
{"id": "drivebc.ca/RIDE-100539", "headline": "INCIDENT", "status": "ACTIVE",
 "description": "Washrooms closed at Highway 1, In Revelstoke and at Revelstoke Rest Area. Until Sat Oct 31. …",
 "schedule": {"intervals": ["2026-07-15T17:52/2026-10-31T23:00"]},
 "event_type": "INCIDENT", "event_subtypes": ["HAZARD"], "severity": "MINOR",
 "geography": {"type": "Point", "coordinates": [-118.21026086, 51.01062005]},
 "roads": [{"name": "Highway 1", "from": "Trans-Canada Highway W", "direction": "BOTH", "state": "ALL_LANES_OPEN"}]}
```

The second example shows that some events are not road events at all (rest
areas, washrooms); `roads[].state` and the subtype help filter them.

### Ottawa traffic events (`ottawa-traffic-events_2026-10-15.json`)

- **Endpoint:** `GET https://traffic.ottawa.ca/map/service/events?accept-language=en&version=v2&format=geojson`
  (documented on [traffic.ottawa.ca/en/opendata](https://traffic.ottawa.ca/en/opendata);
  `accept-language=fr` for French). Without `version=v2` the legacy feed is
  returned; the page warns "legacy feeds may be removed in future updates".
  One call, no paging, 134 KB.
- **Fields (documented on that page):** `id` (unique across event types for
  ids of 10000 and above); `headline`; `message`; `eventType`
  (CONSTRUCTION 126, SPECIAL_EVENT 2, INCIDENT 1); `cause`; `closureType`
  (LANES_CLOSED 69, ROAD_CLOSED 42, OTHER 16, BUS_LANE_CLOSED 2);
  `closureFlow` (BOTH_DIRECTIONS, FROM, AT, UNKNOWN); `mainStreet`,
  `crossStreet1`, `crossStreet2`; `lanes`; `priority` (LOW, MEDIUM, HIGH,
  UNKNOWN); `generation_source` (CITY 115, MTO 10, LRT 2, NCC 1,
  GATINEAU 1); `created`, `updated` (`2026-03-13 15:25:00`); geometry is the
  feature's GeoJSON geometry (Point or MultiLineString).
- **Times:** `schedule[]` with `startDateTime`, `endDateTime`
  (`2026-03-23T06:00`) and optional `days` and `hours`. No offset; the FAQ
  says "All time and time information is presented in local Ottawa time
  (EST/EDT)". Five City records (4 construction, 1 incident) have no
  schedule.
- **Status:** documented values ACTIVE ("ACTVE" in the page), SCHEDULED and
  ARCHIVED; today the feed returned only ACTIVE, including 2 events whose
  schedule starts later. No archived events were present. No confirmed or
  unconfirmed field. The FAQ: planned events "are entered in advance by
  Traffic Management staff … the event ends up being cancelled or following
  a different schedule" sometimes.
- **Limits:** none published; update frequency not stated.
- **Terms:** the FAQ: "Can I use data for my own applications? Yes! The
  data is posted in JSON that can be re-used by 3rd party developers." The
  City's open-data catalogue item for this API
  ([Traffic Services API](https://open.ottawa.ca/datasets/traffic-services-api-webcam-images-traffic-flow))
  names "Open Data Licence Version 2.0", whose text grants use "including
  for commercial purposes". Attribution: "Contains information licensed
  under the Open Government Licence – City of Ottawa." (The licence page on
  ottawa.ca is behind an Incapsula bot check; the same text was read from the
  City's open-data hub page linked in the table.) MTO-sourced events come
  from Ontario 511, which is itself under the Open Government Licence –
  Ontario.

```json
{"geometry": {"type": "MultiLineString", "coordinates": [[[-75.750756, 45.387277], [-75.750721, 45.387288], "…"]]},
 "properties": {"id": 26267, "status": "ACTIVE", "eventType": "CONSTRUCTION", "generation_source": "CITY",
  "headline": "Clare E/B between Churchill and Kirkwood", "closureType": "ROAD_CLOSED", "closureFlow": "FROM",
  "mainStreet": "Clare", "crossStreet1": "Churchill", "crossStreet2": "Kirkwood", "priority": "MEDIUM",
  "message": "Clare eastbound closed between Churchill and Kirkwood due to construction. Follow the signed detour. From 6am Monday, March 23 to 7pm Tuesday December 1. ",
  "schedule": [{"startDateTime": "2026-03-23T06:00", "endDateTime": "2026-12-01T19:00"}],
  "created": "2026-03-13 15:25:00", "updated": "2026-09-04 08:08:00"}}
{"geometry": {"type": "Point", "coordinates": [-75.80572, 45.34548]},
 "properties": {"id": 26539, "status": "ACTIVE", "eventType": "CONSTRUCTION", "generation_source": "MTO",
  "headline": "(MTO) HWY 417 Westbound Off-ramp [  - RICHMOND RD (IC 130)/BAYSHORE DR ] - Daily Construction",
  "closureType": "OTHER", "closureFlow": "UNKNOWN", "priority": "UNKNOWN",
  "schedule": [{"startDateTime": "2026-04-22T08:00", "endDateTime": "2026-11-27T08:00"}]}}
```

### Edmonton traffic disruptions (`edmonton-traffic-disruptions_2026-10-15.json`)

- **Endpoint:** `GET https://data.edmonton.ca/resource/k4tx-5k8p.json?$limit=5000`
  (Socrata SODA; `$limit`/`$offset` for paging, `$where` for filters). One
  call returned all 1,788 rows (1.4 MB). To fetch only open disruptions:
  `$where=status in('Current','Revised','Emergency') AND finish_date >= '2026-10-15'`.
- **Fields (from the dataset's column descriptions):** id `disruption_id`
  (not unique per row: 591 disruptions have two rows, one at the from point
  and one at the to point, with identical text); `on_street`, `from_street`,
  `to_street`; `details` (free text, often with the hours); `description`
  (work type, e.g. UTILITY REPAIR); `activity_type` (Construction 1,509,
  Special Event 166, Traffic Incident 99); `impact` (Total Closure 733,
  Travel Delays 554, Increased Travel Time 194, Directional Closure 123,
  Major Delays 108, …); `infrastructure`; `traffic_district`; `point`
  (GeoJSON Point, WGS84; metadata "Coordinate System: LL-WGS84").
- **Times:** `date_issued`, `start_date`, `finish_date` are **dates only**
  (always `T00:00:00.000`, no zone; Edmonton local). Hours, when given, are
  in `details` ("closed Jan 29th 10 pm - Jan 30th 5am"). 27 rows have no
  finish date.
- **Status:** `status` = Complete 1,451, Current 284, Revised 39, Canceled 7,
  Hold 4, Emergency 1 (rows). It is not reliable on its own: 77 disruptions
  marked Current and 9 marked Revised have a finish date before today, and Current is also used
  for disruptions that start later. Filter on status **and** dates. The
  dataset metadata says "Verified for Accuracy: Yes"; there is no per-record
  confirmation field. Seven old rows have the text "Test" (all Complete).
- **Update frequency:** "X times per day", automated (metadata); the data
  was last updated 2026-10-15 07:48 UTC. No rate limit is stated on the
  pages read.
- **Attribution:** "Contains information licensed under the Open Government
  Licence – City of Edmonton." The licence grants use "including for
  commercial purposes".

```json
{"disruption_id": "1099", "date_issued": "2026-09-21T00:00:00.000", "start_date": "2026-09-25T00:00:00.000",
 "finish_date": "2026-10-24T00:00:00.000", "status": "Current", "on_street": "Aspen Drive East NW",
 "from_street": "121 Street NW", "to_street": "40 Avenue NW", "impact": "Total Closure", "duration": "30",
 "details": "Starts Sept 25th. Aspen Drive East from 121 Street to 40 Avenue will be closed due to utility repair. Local Access maintained.",
 "description": "UTILITY REPAIR", "activity_type": "Construction", "traffic_district": "Southwest", "infrastructure": "Road",
 "point": {"type": "Point", "coordinates": [-113.53979519026993, 53.47634694166428]}}
{"disruption_id": "1211", "date_issued": "2026-10-13T00:00:00.000", "start_date": "2026-10-23T00:00:00.000",
 "finish_date": "2026-10-30T00:00:00.000", "status": "Current", "on_street": "36A AVENUE",
 "from_street": "66 STREET NW", "to_street": "WOODVALE ROAD W NW", "impact": "Total Closure",
 "details": "36A Avenue will be completely closed from 66 Street to Woodvale Rd W from October 23 to October 30. Please follow the detour.",
 "description": "ROAD CONSTRUCTION", "activity_type": "Construction",
 "point": {"type": "Point", "coordinates": [-113.43337887879947, 53.47135109788343]}}
```

### Winnipeg lane closures (`winnipeg-lane-closures_2026-10-15.json`)

- **Endpoint:** `GET https://data.winnipeg.ca/resource/h367-iifg.json?$limit=5000`
  (Socrata; one call, 794 rows, 1.6 MB; the `kml` column repeats the
  geometry and can be left out with `$select`). Open closures only:
  `$where=status != 'Expired'`.
- **Fields:** id `lane_closure_id` (unique); `primary_street`,
  `cross_street`, `boundaries` ("Graham Av to St Mary Av"); `direction`
  (Westbound, Northbound & Southbound, …); `traffic_effect` (free text);
  `complete_closure` (Yes 145 / No 649); `organization` (who works);
  `inserted_date`, `modified_date`; `geometry` (GeoJSON MultiLineString,
  WGS84, every row); also `latitude`/`longitude` and projected `x`/`y`
  (metre values; the zone is not stated in the metadata).
- **Times:** `date_closed_from`, `date_closed_to` are dates at
  `T00:00:00.000` (Winnipeg local, no zone) plus `time_closed_from`,
  `time_closed_to` as text ("12:00 AM", "09:00 AM"). An indefinite closure
  uses `2099-01-01` (the Arlington Bridge record says "End date is not
  applicable but is a requirement of the lane closure system").
- **Status:** `status` = Current 550, Today 41, Future 131, Expired 72.
  By dates: 593 current, 108 upcoming, 93 ended (72 Expired plus 21 still
  marked Current or Today whose end date is past). No confirmed field.
- **Mixed content:** many closures are sidewalk or back-lane only (96 rows
  mention neither a lane nor a street in `traffic_effect`); filter on the
  text or keep only `complete_closure = Yes` for full closures.
- **Update frequency:** "Daily" (metadata); data updated 2026-10-14 09:33
  UTC. No rate limit stated.
- **Attribution:** "Contains information licensed under the Open Government
  Licence – Winnipeg." The licence grants use "including for commercial
  purposes".

```json
{"lane_closure_id": "523407", "primary_street": "Arlington Bridge", "cross_street": "Logan Av",
 "boundaries": "Logan Av to Dufferin Av", "direction": "Northbound & Southbound",
 "date_closed_from": "2023-11-21T00:00:00.000", "date_closed_to": "2099-01-01T00:00:00.000",
 "traffic_effect": "The bridge is closed indefinitely. End date is not applicable but is a requirement of the lane closure system.",
 "organization": "Bridges", "status": "Current", "complete_closure": "Yes",
 "geometry": {"type": "MultiLineString", "coordinates": [[[-97.16262469168292, 49.911163104972616], "…"]]}}
{"lane_closure_id": "544829", "primary_street": "Dartmouth Dr", "cross_street": "Pembina Hw",
 "boundaries": "Pembina Hw to Snow St", "direction": "Eastbound",
 "date_closed_from": "2026-10-25T00:00:00.000", "date_closed_to": "2026-10-25T00:00:00.000",
 "traffic_effect": "Heritage Classic game at the stadium. Travel in both directions and sidewalks will be maintained, but expect additional traffic control …",
 "organization": "City of Winnipeg Film and Special Events Office", "time_closed_from": "12:00 AM",
 "time_closed_to": "12:00 AM", "status": "Future", "complete_closure": "No",
 "geometry": {"type": "MultiLineString", "coordinates": [[[-97.15452552735702, 49.8073038279303], "…"]]}}
```

### Calgary construction detours (`calgary-construction-detours_2026-10-15.json`)

- **Endpoint:** `GET https://data.calgary.ca/resource/w8zq-79bq.json?$limit=5000`
  (Socrata; one call, 235 rows, 145 KB). Description: "scheduled road
  closures due to construction, planned maintenance and utility work …
  updated twice a day. (3 am and 3 pm)".
- **Fields:** `construction_info` (location, e.g. "Edmonton Trail at 1
  Avenue NE"), `description` (what is closed; missing in 1 row; some contain
  stray `¿` characters where bullets were), `start_dt`, `end_dt`,
  `latitude`, `longitude`, `point` (GeoJSON Point, WGS84). There is **no
  type, status, severity or direction field**, and **no stable id**: the
  Socrata row id (`:id`) exists, but every row's `:created_at` was
  2026-10-14, so the table is rebuilt at each refresh. A connector has to
  derive its own key (for example location + start + point).
- **Times:** `start_dt`, `end_dt` are local Calgary time without offset
  (`2026-07-13T07:00:00.000`); counted here as UTC−6 (MDT).
- **Status:** none; ended rows are kept (8 today). Filter with
  `$where=end_dt > '<local now>'`. No confirmed field; the dataset is the
  City's own schedule ("How Data is Collected": ATIS).
- **Attribution:** the dataset's attribution is "The City of Calgary"; the
  licence's default statement is "Contains information licensed under the
  Open Government Licence – City of Calgary." The licence grants use
  "including for commercial purposes".

```json
{"construction_info": "Edmonton Trail at 1 Avenue NE", "description": "Right lane closed north bound on 1 AV NE  ",
 "start_dt": "2025-06-01T09:00:00.000", "end_dt": "2026-12-31T15:00:00.000",
 "longitude": "-114.05028321045208", "latitude": "51.053268688758585",
 "point": {"type": "Point", "coordinates": [-114.05028321045208, 51.053268688758585]}}
{"construction_info": "8 Avenue and 7 Street SW",
 "description": "Eastbound 8 St parking lane and cycle track closure at 7 St SW. Bike share the road. Drive with caution.",
 "start_dt": "2026-07-13T07:00:00.000", "end_dt": "2026-10-30T17:00:00.000",
 "point": {"type": "Point", "coordinates": [-114.07879351646045, 51.04599302279869]}}
```

### Montréal works and obstructions (`montreal-entraves-travaux_2026-10-15.csv`)

- **Endpoints:** two CSV files of the dataset
  [Entraves et travaux en cours](https://donnees.montreal.ca/dataset/info-travaux)
  (updated "Quotidien"):
  - permits: `https://donnees.montreal.ca/dataset/667342f7-f667-4c3c-9837-65e81312cd8d/resource/cc41b532-f12d-40fb-9f55-eb58c9a2b12b/download/entraves-travaux-en-cours.csv` (2,209 rows, 982 KB);
  - street impacts: `…/resource/a2bc8014-488c-495d-941b-e7ae1999d1bd/download/impacts-entraves-travaux-en-cours.csv` (2,337 rows), joined by `id_request` = `id`.
  Whole files, no paging. The portal asks for `Crawl-Delay: 10`.
- **Fields (data dictionary on the dataset page):** `id` (unique per permit
  request), `permit_permit_id` (OCC-…), `boroughid`, `permitcategory`
  (all "Travaux"), `currentstatus` (all "Permis émis"), `reason_category`
  (work type), `occupancy_name` ("Sainte-Catherine entre Plessis et
  Papineau"), `submittercategory`, `organizationname`, per-weekday activity
  flags and hours, `load_date`, `longitude`, `latitude` (WGS84, every row).
  Impacts file: `name`, `fromname`, `toname`, `streetimpacttype` (Rue barrée
  352 rows, Voie de circulation obstruée 404, parking lane only 927, …),
  `streetimpactwidth`, `isarterial`, `length`, and sidewalk, bike-path and
  bus-stop impacts. 2,026 permits have impact rows; 287 include a "Rue
  barrée" (street closed) segment.
- **Times (needs care):** `duration_start_date` and `duration_end_date` are
  ISO with `Z`, but every start is `20:00:00Z` (summer) or `19:00:00Z`
  (winter) and every end `19:59:59Z` or `18:59:59Z`. That is the pattern of
  Montréal local day boundaries written with the offset's sign reversed: the
  start `2026-10-04T20:00:00Z` reads as 5 October 00:00 local and the end
  `2026-10-16T19:59:59Z` as 16 October 23:59:59 local. This is inferred from
  the pattern, not documented; ask the City (donneesouvertes@montreal.ca)
  before relying on it. The counts in the table use the raw values.
- **Status:** permits only ("Permis émis"); 203 permits with an end already
  past are still in the file. A permit is an authorised occupation of the
  street, not proof that work is under way that day.
- **Attribution (CC BY 4.0):** credit the Ville de Montréal, say if the data
  was modified, no implied endorsement. The licence page allows use "y
  compris commerciale" and suggests the credit "Données ouvertes de la Ville
  de Montréal".

```json
{"id": "69ea792220e2850012c69c69", "permit_permit_id": "OCC-2604TO25705312", "boroughid": "Ville-Marie",
 "currentstatus": "Permis émis", "duration_start_date": "2026-05-10T20:00:00Z", "duration_end_date": "2026-10-22T19:59:59Z",
 "reason_category": "Autre", "occupancy_name": "Sainte-Catherine entre Plessis et Papineau",
 "organizationname": "Société de développement commercial Village Montréal",
 "longitude": "-73.55332912107531", "latitude": "45.52154215091506",
 "impact": {"name": "rue Sainte-Catherine Est", "fromname": "rue Plessis", "toname": "avenue Papineau",
            "streetimpacttype": "Rue barrée", "isarterial": "t", "length": "275.14"}}
{"id": "6ab57b608c75940013ef97ca", "permit_permit_id": "OCC-2609SF25578914", "boroughid": "Ville-Marie",
 "currentstatus": "Permis émis", "duration_start_date": "2026-10-04T20:00:00Z", "duration_end_date": "2026-10-16T19:59:59Z",
 "occupancy_name": "Crescent entre René-Lévesque et Sainte-Catherine", "organizationname": "Telecon",
 "longitude": "-73.57425413456119", "latitude": "45.49650511400704",
 "impact": {"name": "rue Crescent", "streetimpacttype": "Voie de stationnement et voie de circulation obstruées"}}
```

(Rows are CSV; shown as JSON with the joined impact row for readability.)

### Brampton road closures (`brampton-road-closures_2026-10-15.geojson`)

- **Endpoint:** `GET https://services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/BramptonWorks_OpenData/FeatureServer/3/query?where=1%3D1&outFields=*&outSR=4326&f=geojson`
  (6 records, 6 KB).
- **Fields:** `LIST_ID` (id), `STREET`, `FROM_`, `TO_`, `PROJECTLOCATION`,
  `DESCRIPTION` (all "Construction"), `DIRECTION` (BOTH_DIRECTIONS,
  ONE_DIRECTION), `BODY` (notice text), `LISTINGSTARTDATETIME`,
  `LISTINGENDDATETIME` (epoch milliseconds, UTC), `START_DATE_TEXT`,
  `END_DATE_TEXT`, `MORE_INFO` (link to the notice), `LAST_EDITED_DATE`
  (2026-10-15 02:30 UTC). No status field; filter on the end time.
- The City's Waze layer (`maps1.brampton.ca/…/Waze_Road_Closures/FeatureServer/0`)
  holds the same closures (5 records, ISO times with offset).
- **Licence:** the GeoHub item's licence field reads "CC BY" (no version
  given), owner City of Brampton. Credit the City of Brampton.

```json
{"LIST_ID": "4393", "STREET": "Heart Lake Rd S", "FROM_": "Glidden Ave", "TO_": "341 Heart Lake Road S",
 "DESCRIPTION": "Construction", "DIRECTION": "BOTH_DIRECTIONS",
 "BODY": "The Region of Peel has been approved a long term road closure of Heart Lake Rd at Glidden Rd …",
 "LISTINGSTARTDATETIME": 1762776000000, "LISTINGENDDATETIME": 1819753200000,
 "START_DATE_TEXT": "NOVEMBER 10, 2025", "END_DATE_TEXT": "AUGUST 31, 2027"}
{"LIST_ID": "4388", "STREET": "Clarkway Dr", "PROJECTLOCATION": "Countryside Dr to Mayfield Rd",
 "DESCRIPTION": "Construction", "DIRECTION": "ONE_DIRECTION",
 "LISTINGSTARTDATETIME": 1760958000000, "LISTINGENDDATETIME": 1793577600000,
 "START_DATE_TEXT": "OCTOBER 20, 2025", "END_DATE_TEXT": "NOVEMBER 1, 2026"}
```

## YELLOW: one item missing

| Source | What it gives (15 Oct) | Missing item | Sample |
| --- | --- | --- | --- |
| Québec MTMD road works, layer `ms:chantiers_mtmdet` (`ws.mapserver.transports.gouv.qc.ca/swtq?service=wfs&version=2.0.0&request=getfeature&typename=ms:chantiers_mtmdet&srsname=EPSG:4326&outputformat=geojson`) | 526 works on provincial roads: 414 current, 107 upcoming, 5 ended (times local, no offset); every record a line; ids `identifiant`; bilingual descriptions; CC BY 4.0 ([Données Québec record](https://www.donneesquebec.ca/recherche/dataset/travaux-routiers), "Temps réel") | **robots.txt unreadable:** `/robots.txt` on this host answered HTTP 403 with a Cloudflare challenge (`cf-mitigated: challenge`) twice. The data URL itself answered 200 with no challenge, and Données Québec publishes it as the official download link. Under RFC 9309 a 4xx robots.txt means no restriction, but the file could not be read. | `quebec-mtmd-travaux_2026-10-15.geojson` |
| Québec MTMD road warnings, layer `ms:evenements` (same host) | 19 current warnings (closures, lane closures, alternating traffic, two ferry notices), every record a line; start `enVigueurDepuis`, no end field (`duree` is "Indéterminée" 13 times, empty 4 times, a date range in words twice) | Same robots.txt issue | `quebec-mtmd-avertissements_2026-10-15.geojson` |
| Calgary current traffic incidents (`data.calgary.ca/resource/4jah-h97u.json`) | 1 incident, a point, start time in UTC | **Unconfirmed:** the City describes the data as including "unverified, unreported traffic collisions" and says it "is based off unrecorded imagery" | `calgary-current-incidents_2026-10-15.json` |
| Alberta 511, Manitoba 511, New Brunswick 511, Yukon 511 (`/api/v2/get/event`) | Provincial events | **Developer key:** each `/developers/doc` page: "Requires a developer key … Ten calls every 60 seconds"; a registered account is needed | none |
| Ontario 511 | Provincial events | Developer key (as found on 14 October) | none |
| City of Vancouver "Road Ahead" current closures (`opendata.vancouver.ca`, dataset `road-ahead-current-road-closures`) | Closures with line geometry (seen only in a search-engine copy) | **robots.txt:** `User-agent: *` has `Disallow: /api/` and `Disallow: /explore/dataset/*/download` (Googlebot is allowed `/api/`). Not fetched. | none |
| Saskatchewan Highway Hotline, ArcGIS copy (`services.arcgis.com/wjcPoefzjpzCgffS/…/Saskatchewan_Highway_Hotline/FeatureServer/1` and `/2`) | 47 event points (incidents 18, restrictions 18, roadwork 7, closures 4), WGS84; some `LastUpdated` 2025-12-15 | **Licence unclear:** a copy hosted outside the Province, copyright "Saskatchewan Highway Hotline, Esri Canada", no licence stated; the Hotline's own `/developers/doc` returned 404 today | `saskatchewan-hotline-esri-mirror_2026-10-15.geojson` |
| Halifax sidewalk closures and disruptions (`services2.arcgis.com/11XBiaBYA9Ep0yNJ/…/Development_Street_Closures_Active/FeatureServer/0`) | 79 current lines from development permits; 66 are sidewalk types (`SW_CLOSED`, `SW_TEMP`), 13 have a street-closed type (`S_CLOSED_*`) | **Mostly not road events, and the licence of this layer was not confirmed** in the HRM catalogue | `halifax-sidewalk-street-closures_2026-10-15.geojson` |

## RED: unusable

| Source | Reason |
| --- | --- |
| Montréal real-time obstructions, CIFS feed (`api.montreal.ca/api/transportation/traffic-events-api/v1/export-cifs?type=json`, linked from [entraves-circulation](https://donnees.montreal.ca/dataset/entraves-circulation)) | HTTP 404 `{"message":"no Route matched with those values"}` today |
| Ontario "Today's roadwork: closures" ([data.ontario.ca](https://data.ontario.ca/dataset/todays-roadwork-closures)) | The only resource is a link to the 511on.ca map; no data file (the data is Ontario 511's keyed API) |
| City of Ottawa open-data catalogue | Only historical emergency road closure files (2018, 2019); the live data is the traffic.ottawa.ca feed above |
| Nova Scotia 511 | `/developers/doc` returned 404; no public API found |
| Brampton Waze layer (`maps1.brampton.ca`) | Duplicate of the BramptonWorks layer |
| Hamilton, Mississauga, York Region | Web searches found no current road-closure dataset; not fetched |
| TomTom, HERE, Waze, Google, INRIX; news sites | Excluded: commercial providers and news are out of scope for this list |

## Access-rule notes from this research

- **Données Québec:** one request went to
  `/recherche/api/3/action/package_show?id=travaux-routiers`, which its
  robots.txt disallows (`Disallow: /recherche/api/`), in the same command as
  the robots.txt request (inside its `Crawl-Delay: 10`). The copy was
  deleted; the licence and download links were then read from the allowed
  dataset page.
- **Québec MTMD map server:** the data layers were fetched four times
  (5-record test, full works layer, capabilities, warnings layer) although
  the host's robots.txt could not be read (Cloudflare challenge).
- **data.calgary.ca:** about 11 requests including one malformed query
  (HTTP 400), slightly above the target of 10 per host.
- **ottawa.ca:** robots.txt and the licence page answered with an
  Incapsula bot check; nothing was retried or bypassed. The licence text was
  read from the City's open-data hub page instead.
- The licences of Calgary and Edmonton were read from their story pages
  (Edmonton's text is a document embedded from the portal's storage).
