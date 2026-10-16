# Americas and Oceania: official road-event sources, 16 October 2026

Research only: no code or configuration was changed and nothing was
connected. Every candidate below was fetched live on 16 October 2026 between
12:20 and 12:47 UTC with the User-Agent
`JSAN-REI/1.0 (road event intelligence research)`. robots.txt was read first
on every host and every licence or terms page was read with the same client.
The logged total is 255 requests to 97 hosts, never more than 9 to one host
(`www.arcgis.com`). Nothing was bypassed: no browser disguise, no proxies, no
CAPTCHAs, no logins, and no keys registered or guessed. No request went to
any gdeltproject.org host, to news publishers or to South African sources.

The research machine's address is in India. Several US hosts block it by
country or by bot rules (Wisconsin, Oklahoma, Utah, Iowa's WZDx host, the
Maryland CHART hosts). They are listed as unreachable from here, not as
refusing REI. A US or production host may get a different answer.

Already covered elsewhere and not repeated: NYC DOT, Toronto, DriveBC,
Ottawa, Edmonton, Winnipeg, Calgary, Main Roads WA, City of Gold Coast,
Wodonga and Roads ACT (connected), and the keyed 511s (Ontario, Alberta,
Manitoba, New Brunswick, Yukon, 511NY developer API, QLDTraffic, Transport for
NSW, Victoria DTP) ([Canada](canada-source-research-2026-10-15.md),
[Australia](australia-source-research-2026-10-15.md),
[14 October](source-research-2026-10-14.md)).

How records are counted: **current** = started and not ended at fetch time;
**upcoming** = starts later; **ended** = end already past but still served.

Verdicts: **PERMITTED** = the licence allows commercial use (possibly with
attribution); **NEEDS_KEY** = free key or registration (not requested);
**ASK_PERMISSION** = no licence, or the licence is silent; **RESTRICTED** =
terms or robots.txt rule it out; **UNREACHABLE** = no usable answer from this
machine.

## Result in brief

- **The US WZDx feeds are the main find.** The USDOT registry
  (public domain) lists 43 work-zone feeds, and the WZDx specification
  requires public feeds to be CC0. Twelve keyless feeds declare CC0 in their
  own `feed_info.license`: Maricopa County/ADOT, Austin, Indiana, Minnesota,
  Kansas, New Jersey, Kentucky, MoDOT (St. Louis), Maryland, North Dakota,
  Delaware and Louisiana. Together they serve about 8,200 work zones and
  detours with line or point geometry and ISO start and end times on every
  record. Hawaii also declares CC0, but its feed is stale.
- **Five more WZDx feeds are keyless but silent on licence:** North Carolina
  (6,493 rows), Florida (27,539), Idaho, WSDOT and New England. They are
  ASK_PERMISSION, with low risk because the specification asks for CC0.
- **Other US PERMITTED sources:** SFMTA temporary street closures
  (PDDL/CC0), Chicago CDOT permits (with conditions), Iowa DOT 511 events
  (CC BY 4.0), Charlotte street closures (CC BY 4.0), Maryland CHART road
  closures (public domain), Baton Rouge road closures (public domain), and
  three of low value (DC occupancy permits, Seattle event closures, Austin
  incidents). Boston is public domain but has no coordinates.
- **Canada, new and PERMITTED:** Halifax street closures (OGL–Halifax),
  Cambridge ON road closures, Kitchener traffic closures (both OGL) and
  Sherbrooke works (CC BY 4.0, French).
- **Latin America: nothing usable.** Mexico City and Bogotá portals timed
  out, Medellín is blocked by its robots answer, Chile's UOCT sells its data,
  Buenos Aires needs credentials, and Brazil publishes only historical
  accident files.
- **Oceania:** Auckland Transport roadworks (CC BY 4.0, from the AT portal's
  general statement) is PERMITTED. Moreton Bay weather closures is permitted
  but has no dates. NZTA's national highway feed is keyless and the best NZ
  data, but its terms bar commercial use without a licence (RESTRICTED;
  ask NZTA).

## Summary table

| Country | Source | URL | Format | Auth | Records (16 Oct) | Geometry | Start/end | Licence | Commercial | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US | USDOT WZDx Feed Registry | `data.transportation.gov/resource/69qe-yiui.json` | Socrata JSON | None | 43 feeds | Agency point | n/a | Public Domain U.S. Government | Yes | PERMITTED (index only) |
| US (AZ) | Maricopa County DOT regional WZDx (incl. ADOT statewide, Phoenix, Mesa, …) | `wzdxapi.aztech.org/construction` | WZDx 4.2 GeoJSON | None | 2,514 (1,376 / 560 / 578 ended) | Lines 1,807, MultiPoint 707 | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (TX) | City of Austin TPW WZDx | `data.austintexas.gov/download/d9mm-cjw9` | WZDx 4.2 GeoJSON | None | 2,655 (2,149 / 506 / 0) | Lines | Yes, all | CC0 (in feed); portal public domain | Yes | PERMITTED |
| US (IN) | Indiana DOT WZDx (CARS) | `in.carsprogram.org/carsapi_v1/api/wzdx` | WZDx 4.0 GeoJSON | None | 1,235 (938 / 297 / 0) | Lines 983, MultiPoint 252 | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (MN) | Minnesota DOT WZDx (CARS) | `mn.carsprogram.org/carsapi_v1/api/wzdx` | WZDx 4.0 GeoJSON | None | 471 (414 / 57 / 0) | Lines 313, MultiPoint 158 | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (KS) | Kansas DOT WZDx (CARS) | `ks.carsprogram.org/carsapi_v1/api/wzdx` | WZDx 4.0 GeoJSON | None | 421 (356 / 65 / 0) | Lines 362, MultiPoint 59 | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (NJ) | NJDOT WZDx (NJIT, TRANSCOM data) | `smartworkzones.njit.edu/nj/wzdx` | WZDx 4.1 GeoJSON | None | 365 (358 / 0 / 7) | MultiPoint | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (KY) | Kentucky Transportation Cabinet WZDx | `storage.googleapis.com/kytc-its-2020-openrecords/public/feeds/WZDx/kytc_wzdx_v4.1.geojson` | WZDx 4.1 GeoJSON | None | 269 (118 / 8 / 143) | Lines | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (MO) | MoDOT St. Louis area WZDx (registry: St. Charles County) | `scc.ridsi-dash.com:5000/wzdx.geojson` | WZDx 4.1 GeoJSON | None | 100 (96 / 0 / 4) | Lines | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (MD) | Maryland SHA WZDx (via RITIS) | `filter.ritis.org/wzdx_v4.1/mdot.geojson` | WZDx 4.1 GeoJSON | None | 99 (95 / 0 / 4) | Lines 67, MultiPoint 32 | Yes, all | CC0 (in feed) | Yes | PERMITTED |
| US (ND) | North Dakota DOT WZDx | `travelfiles.dot.nd.gov/geojson_nc/wzdx_geojson.json` | WZDx 4.0 GeoJSON | None | 79 (51 / 0 / 28) | Lines 27, MultiPoint 52 | Yes (dates) | CC0 (in feed) | Yes | PERMITTED |
| US (DE) | DelDOT WZDx (HaulHub) | `wzdx.e-dot.com/del_dot_feed_wzdx_v4.1.geojson` | WZDx 4.1 GeoJSON | None | 19 (19 / 0 / 0) | Lines | Yes (2-hour windows) | CC0 (in feed) | Yes | PERMITTED |
| US (LA) | Louisiana DOTD WZDx (HaulHub) | `wzdx.e-dot.com/la_dot_d_feed_wzdx_v4.1.geojson` | WZDx 4.1 GeoJSON | None | 5 (4 / 0 / 1) | Lines | Yes (2-hour windows) | CC0 (in feed) | Yes | PERMITTED |
| US (HI) | Hawaii DOT WZDx (Blyncsy) | `ai.blyncsy.io/wzdx/hidot/feed` | WZDx 4.1 GeoJSON | None | 66, all ended | Lines | Yes | CC0 (in feed) | Yes | PERMITTED, stale (no current records) |
| US (NC) | NCDOT DriveNC WZDx | `drivenc.gov/api/wzdx` | WZDx 4.1 GeoJSON | None | 6,493 rows (484 / 5,987 / 22) | Lines 5,056, MultiPoint 1,437 | Yes, all | None in feed; site disclaimer only | Unclear | ASK_PERMISSION |
| US (FL) | FDOT WZDx (one.network) | `us-datacloud.one.network/fdot/feed.json?app_key=…` (key printed in the registry) | WZDx 4.2 GeoJSON, gzip | Registry-published app_key | 27,539 (1,541 / 9,904 / 16,094) | Lines 25,967, MultiPoint 1,572 | Yes, all | None in feed | Unclear | ASK_PERMISSION |
| US (ID) | Idaho ITD 511 WZDx | `511.idaho.gov/api/wzdx` | WZDx 4.1 GeoJSON | None | 628 (139 / 483 / 6) | Lines 367, MultiPoint 261 | Yes, all | None in feed | Unclear | ASK_PERMISSION |
| US (WA) | WSDOT WZDx | `wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed` | WZDx 4.2 GeoJSON | None | 467 (305 / 162 / 0) | Lines | Yes (dates) | None in feed or on the API page | Unclear | ASK_PERMISSION |
| US (ME/NH/VT) | New England Compass WZDx | `api.dx.ne-compass.com/wzdx-latest/` | WZDx 4.2 GeoJSON | None | 222 (208 / 7 / 7) | Lines 149, MultiPoint 73 | Yes, all | None in feed | Unclear | ASK_PERMISSION |
| US (CA) | SFMTA Temporary Street Closures | `data.sfgov.org/resource/8x25-yybr.geojson` (WZDx copy `/download/4ftp-yz2f`) | Socrata GeoJSON; WZDx 4.2 | None | 4,279 lines from 364 cases (43 / 3,657 / 579) | Lines | Yes (UTC and local) | PDDL (dataset); CC0 (WZDx copy) | Yes | PERMITTED |
| US (IL) | Chicago CDOT Transportation Department Permits | `data.cityofchicago.org/resource/pubx-yq2d.json` | Socrata JSON | None | 1,791 rows, 1,305 permits with a street closure (1,127 / 664 / 0) | Point | Yes (local, no zone) | City data terms: disclaimer, termination right, indemnity | Yes, with conditions | PERMITTED (with conditions) |
| US (IA) | Iowa DOT 511 traveler events (ArcGIS) | `services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/CARS511_Iowa_View/FeatureServer/0` | ArcGIS GeoJSON | None | 647 rows, 329 events | Point (line layer separate) | Yes (strings, local) | CC BY 4.0 (item); extra terms unreadable | Yes | PERMITTED |
| US (NC) | Charlotte "Street Closures (Public)" | `gis.charlottenc.gov/arcgis/rest/services/CDOT/StreetClosuresAndDetours/MapServer/0` | ArcGIS GeoJSON | None | 241 (32 / 30 / 179) | Lines | Yes (4 no start, 5 no end) | CC BY 4.0 (hub item) | Yes | PERMITTED |
| US (MD) | Maryland Road Closures from MDOT CHART | `opendata.maryland.gov/resource/nigh-m2sg.json` | Socrata JSON | None | 70 current | Point | Start in text only; no end | Public Domain | Yes | PERMITTED |
| US (LA) | Baton Rouge Road Closures | `data.brla.gov/resource/ra2i-eye8.geojson` | Socrata GeoJSON | None | 20 current | MultiLineString | Yes (UTC) | Public Domain | Yes | PERMITTED |
| US (DC) | DDOT Occupancy Permits, last 30 days | `maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/16` | ArcGIS GeoJSON | None | ≥1,000 (430 / 260 / 310 in first page) | Point | Dates only | CC BY 4.0 | Yes | PERMITTED (low value) |
| US (WA) | Seattle SDOT Street Closures | `data.seattle.gov/resource/ium9-iqtc.json` | Socrata JSON | None | 115 (37 / 77 / 1) | Lines | Dates | Public Domain | Yes | PERMITTED (events only) |
| US (TX) | Austin Real-Time Traffic Incident Reports | `data.austintexas.gov/resource/dx9v-zd7x.json` | Socrata JSON | None | 3 active (5,000 rows mostly archived) | Point | Start only | Austin portal: public domain | Yes | PERMITTED (no end time) |
| US (MA) | Boston PWD Active Work Zones | `data.boston.gov/dataset/f9f57091-…/download/tmp_nbii4sq.csv` | CSV | None | 460 | **None** | End only | PDDL | Yes | PERMITTED, not usable (no coordinates) |
| US (DE) | DelDOT advisories | `tmc.deldot.gov/json/advisory.json` | JSON | None | 22 | Point | Start; end in text | None found | Unclear | ASK_PERMISSION |
| US (WA) | WSDOT Highway Alerts KML | `wsdot.wa.gov/traffic/api/HighwayAlerts/kml.aspx` | KML | None | 125 | Point | None | Not found | Unclear | ASK_PERMISSION |
| US (VA) | Norfolk Right of Way permits | Socrata `mi4h-8pn3` | Socrata JSON | None | 1,310 open, 206 closures | Point | Yes | None on dataset | Unclear | ASK_PERMISSION |
| US (PA) | Philadelphia Street Lane Closures (StreetSmartPHL) | `services.arcgis.com/fLeGjb7u4uXqeF9q/…/LaneClosure_Master/FeatureServer/0` | ArcGIS | None | >2,000 | Lines | Dates | City of Philadelphia License ("reserves all rights") | No grant | ASK_PERMISSION |
| CA (NS) | Halifax Street Closures | `services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Street_Closures/FeatureServer/0` | ArcGIS GeoJSON | None | 41 not ended (25 / 13); history to 2019 | Lines | Dates (hours in text) | OGL – Halifax | Yes | PERMITTED |
| CA (ON) | Cambridge Road Closures | `maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1` | ArcGIS GeoJSON | None | 129 current (98 parking lane only) | Lines | Yes (UTC) | Open Data Licence v2.0 (Cambridge) | Yes | PERMITTED |
| CA (ON) | Kitchener Traffic_Closures | `services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Closures/FeatureServer/0` | ArcGIS GeoJSON | None | 48 (36 / 5 / 7) | Lines | Partly (15 no start, 21 no end) | OGL – Kitchener v1.0 | Yes | PERMITTED |
| CA (QC) | Sherbrooke Travaux | `services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/Travaux/FeatureServer/0` | ArcGIS GeoJSON | None | 52 (51 / 1) | Point | Yes (UTC) | CC BY 4.0 | Yes | PERMITTED |
| CA (ON) | City of Waterloo Public Closures | `gis.waterloo.ca/maps/rest/services/Public/Public_Closures/MapServer/0` | ArcGIS | None | 47 (15 / 2 / 30) | Lines | Yes | None on item | Unclear | ASK_PERMISSION |
| CA (ON) | Oakville Road Closure | `maps.oakville.ca/oakgis/rest/services/SBS/Road_Closure/FeatureServer/0` | ArcGIS | None | 81 (20 / 6) | Lines (no street names) | Yes | None on item | Unclear | ASK_PERMISSION |
| CA (BC) | Abbotsford transportation layer 230 | `services8…/Transportation_Layers_External_Feature/FeatureServer/230` | ArcGIS | None | >2,000 history; 24 current, 12 upcoming in first page | Lines | Yes | None on item | Unclear | ASK_PERMISSION |
| CA (SK) | Saskatchewan Highway Hotline (Esri copy) | `services.arcgis.com/wjcPoefzjpzCgffS/…` | ArcGIS | None | 47 (15 Oct) | Point | Partly | saskatchewan.ca copyright: commercial use needs written permission | No, without permission | ASK_PERMISSION |
| AR | Buenos Aires API Transporte (tránsito) | `apitransporte.buenosaires.gob.ar` | API | client_id/secret | — | — | — | Site content CC BY 2.5 AR | — | NEEDS_KEY |
| CL | UOCT (Santiago traffic control) | — | Sold by quotation | Contract | — | — | — | Paid (Decreto Exento 41) | — | RESTRICTED |
| CO | Medellín `VM_Cierres_Movilidad` | Medellín MapServer | ArcGIS | — | not fetched | — | — | — | — | RESTRICTED (robots answered HTTP 500 firewall page) |
| MX, CO | CDMX `datos.cdmx.gob.mx`; Bogotá `datosabiertos.bogota.gov.co` | — | — | — | timed out twice | — | — | — | — | UNREACHABLE |
| NZ | Auckland Transport Roadworks (MyWorksites) | `services2.arcgis.com/JkPEgZJGxhSjYOo0/ArcGIS/rest/services/PJ_Roadworks_MS/FeatureServer/0` | ArcGIS GeoJSON | None | >1,000 (first page: 646 ended) | Polygons | Yes (dates) | CC BY 4.0 (AT data portal statement) | Yes | PERMITTED |
| AU (QLD) | Moreton Bay Weather Impacted Road Closures | `services-ap1.arcgis.com/152ojN3Ts9H3cdtl/arcgis/rest/services/RoadClosureProdView/FeatureServer/0` | ArcGIS GeoJSON | None | 732 sites, 1 closed | Point | **None** | CC BY 4.0 | Yes | PERMITTED (no dates; low value) |
| NZ | NZTA traffic and travel REST v4 | `trafficnz.info/service/traffic/rest/4/events/all/10` | JSON (WKT geometry) | None | 302 (124 / 109 / 69) | Point 204, MultiLineString 98 | Yes (`endDate` on 282) | NZTA API terms: no commercial use without a licence | No | RESTRICTED (ask NZTA) |
| NZ | Whangārei RAMM Road Closures | `services1.arcgis.com/RfTgcgHraFPg7Fq4/…/RAMM_Road_Closures_and_Restrictions_-_All/FeatureServer/0` | ArcGIS | None | 5 | Point | End only | Disclaimer, no licence | Unclear | ASK_PERMISSION |
| NZ | Wellington City planned works | `gis.wcc.govt.nz/…/PlannedWorks/MapServer/1` | ArcGIS | None | 510 resurfacing polygons | Polygons | Month only | Copyright, no licence | Unclear | ASK_PERMISSION (not event data) |
| AU (TAS, NT) | Tasmania State Growth WFS; NT Road Report | (15 Oct report) | WFS; JSON | None | — | — | — | Unchanged: no commercial licence found | Unclear | ASK_PERMISSION |
| US | Mississippi DOT WZDx | `api.mdottraffic.com/prod/v3/data/wzdx` | — | — | not fetched | — | — | — | — | RESTRICTED (robots `Disallow: /`) |
| US | MoDOT statewide WZDx | `traveler.modot.org/timconfig/feed/desktop/mo_wzdx.json` | — | — | HTTP 403 Incapsula | — | — | — | — | RESTRICTED (bot wall) |
| US | Caltrans CWWP2 lane closures, chain controls | `cwwp2.dot.ca.gov` | — | — | not fetched | — | — | — | — | RESTRICTED (robots HTTP 500) |
| US | Pittsburgh WPRDC DOMI Street Closures | `data.wprdc.org` | CSV | — | not fetched | — | — | CC BY | — | RESTRICTED (robots disallows `/datastore/dump/`) |
| US | NWS alerts API (weather road impacts) | `api.weather.gov` | — | — | not fetched | — | — | Public domain | — | RESTRICTED (robots `Disallow: /`) |
| US | Wisconsin, Oklahoma, Utah, Iowa WZDx hosts; New Mexico; 511NY WZDx; Maryland CHART hosts | see below | — | — | 403/503/HTML | — | — | — | — | UNREACHABLE |

## United States: WZDx work-zone feeds

### The registry

- **Endpoint:** `GET https://data.transportation.gov/resource/69qe-yiui.json?$limit=1000`
  (Socrata, no key). 43 rows; rows last updated 2026-10-14 17:10 UTC. Fields:
  `state`, `issuingorganization`, `feedname`, `url.url`, `format`, `active`,
  `needapikey`, `apikeyurl`, `version`, `datafeed_frequency_update`, `sdate`.
- **Licence of the registry** (metadata at `/api/views/69qe-yiui.json`):
  "Public Domain U.S. Government" (`https://www.usa.gov/government-works`).
  Recommended citation: "U.S. Department of Transportation Intelligent
  Transportation Systems Joint Program Office. (2020). Work Zone Data
  Exchange (WZDx) Feed Registry. [Dataset]. Provided by ITS DataHub through
  Data.transportation.gov." The registry's licence covers the list only, not
  the feeds it points to.
- **robots.txt:** `User-agent: *`, `Crawl-delay: 1`; `/resource/` and
  `/api/views/` are not disallowed.
- **Sample:** `wzdx-feed-registry_2026-10-16.json`.

### What licence a WZDx feed carries

The WZDx specification (USDOT ITS JPO, GitHub `usdot-jpo-ode/wzdx`,
`spec-content/objects/FeedInfo.md`, fetched) defines `feed_info.license`:

> "The URL of the license that applies to the data in the WZDx feed. This
> *must* be the string "https://creativecommons.org/publicdomain/zero/1.0/"
> … Data in all public WZDx feeds must be licensed under the Creative
> Commons - Public Domain License (CC0) which permits consumers to freely
> publish the enclosed information. This property is currently optional but
> *will be required in a future release*."

A feed whose own `feed_info.license` holds the CC0 URL is the publisher's
machine-readable CC0 dedication: commercial use is allowed and no
attribution is required (crediting the agency is still good practice, e.g.
"Work zone data: Indiana DOT, WZDx feed, CC0"). A feed without the field is
silent. The specification says it should be CC0, but the publisher has not
said so, so it is ASK_PERMISSION (low risk).

### Feeds checked (fetched 12:25-12:29 UTC)

| Feed (publisher) | Request URL | Features (current / upcoming / ended) | Geometry | Types | Newest update | robots.txt | Licence in feed | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Maricopa County DOT regional (AZTech) | `https://wzdxapi.aztech.org/construction` | 2,514 (1,376 / 560 / 578) | LineString 1,807, MultiPoint 707 | work-zone | feed 2026-10-16 12:25 UTC | 404 | CC0 | PERMITTED |
| Indiana DOT (Castle Rock CARS) | `https://in.carsprogram.org/carsapi_v1/api/wzdx` | 1,235 (938 / 297 / 0) | LineString 983, MultiPoint 252 | work-zone 1,047, detour 188 | 2026-10-16 12:22 UTC | 404 | CC0 | PERMITTED |
| Minnesota DOT (CARS) | `https://mn.carsprogram.org/carsapi_v1/api/wzdx` | 471 (414 / 57 / 0) | LineString 313, MultiPoint 158 | work-zone 347, detour 124 | 2026-10-16 12:18 UTC | 404 | CC0 | PERMITTED |
| Kansas DOT (CARS) | `https://ks.carsprogram.org/carsapi_v1/api/wzdx` | 421 (356 / 65 / 0) | LineString 362, MultiPoint 59 | work-zone 360, detour 61 | 2026-10-15 23:08 UTC | 404 | CC0 | PERMITTED |
| NJDOT (NJIT; TRANSCOM data) | `https://smartworkzones.njit.edu/nj/wzdx` | 365 (358 / 0 / 7) | MultiPoint 365 | work-zone | 2026-10-16 12:00 UTC | 404 | CC0 | PERMITTED |
| Kentucky Transportation Cabinet | `https://storage.googleapis.com/kytc-its-2020-openrecords/public/feeds/WZDx/kytc_wzdx_v4.1.geojson` | 269 (118 / 8 / 143) | LineString | work-zone | 2026-10-15 20:13 UTC | 404 | CC0 | PERMITTED |
| MoDOT, St. Louis area | `https://scc.ridsi-dash.com:5000/wzdx.geojson` | 100 (96 / 0 / 4) | LineString | work-zone | feed 2026-10-16 12:22 UTC | 404 | CC0 | PERMITTED |
| Maryland SHA (RITIS) | `https://filter.ritis.org/wzdx_v4.1/mdot.geojson` | 99 (95 / 0 / 4) | LineString 67, MultiPoint 32 | work-zone | 2026-10-16 12:22 UTC | 404 | CC0 | PERMITTED |
| North Dakota DOT | `https://travelfiles.dot.nd.gov/geojson_nc/wzdx_geojson.json` | 79 (51 / 0 / 28) | LineString 27, MultiPoint 52 | work-zone | 2026-10-15 22:36 UTC | 404 | CC0 | PERMITTED |
| DelDOT (HaulHub) | `https://wzdx.e-dot.com/del_dot_feed_wzdx_v4.1.geojson` | 19 (19 / 0 / 0) | LineString | work-zone | feed 2026-10-16 12:13 UTC | 404 | CC0 | PERMITTED |
| Louisiana DOTD (HaulHub) | `https://wzdx.e-dot.com/la_dot_d_feed_wzdx_v4.1.geojson` | 5 (4 / 0 / 1) | LineString | work-zone | feed 2026-10-16 12:13 UTC | 404 | CC0 | PERMITTED |
| Hawaii DOT (Blyncsy) | `https://ai.blyncsy.io/wzdx/hidot/feed` | 66 (0 / 0 / 66) | LineString | work-zone | feed_info 2024-02-22 | 404 | CC0 | PERMITTED, stale |
| NCDOT DriveNC | `https://drivenc.gov/api/wzdx` | 6,493 rows (484 / 5,987 / 22) | LineString 5,056, MultiPoint 1,437 | work-zone | 2026-10-16 12:20 UTC | `/api/` allowed | none | ASK_PERMISSION |
| FDOT (one.network) | `https://us-datacloud.one.network/fdot/feed.json?app_key=c4090b04-26de-c9ee-873b2bd9a38c` | 27,539 (1,541 / 9,904 / 16,094) | LineString 25,967, MultiPoint 1,572 | detour 24,256, work-zone 3,283 | 2026-10-16 12:27 UTC | 401 | none | ASK_PERMISSION |
| Idaho ITD (511 Idaho) | `https://511.idaho.gov/api/wzdx` | 628 (139 / 483 / 6) | LineString 367, MultiPoint 261 | work-zone | 2026-10-15 21:58 UTC | `/api/` allowed | none | ASK_PERMISSION |
| WSDOT | `https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed` | 467 (305 / 162 / 0) | LineString | work-zone | 2026-10-15 19:54 UTC | 404 | none | ASK_PERMISSION |
| New England Compass (ME, NH, VT) | `https://api.dx.ne-compass.com/wzdx-latest/` | 222 (208 / 7 / 7) | LineString 149, MultiPoint 73 | work-zone | feed 2026-10-16 12:28 UTC | 403 (JSON "Forbidden") | none | ASK_PERMISSION |
| City of Austin (fetched by the city research) | `https://data.austintexas.gov/download/d9mm-cjw9` | 2,655 (2,149 / 506 / 0) | LineString | work-zone | feed 2026-10-16 12:00 UTC | `/download/` allowed | CC0 | PERMITTED |

Not working, from the same registry:

| Feed | Result | Verdict |
| --- | --- | --- |
| Mississippi DOT `api.mdottraffic.com/prod/v3/data/wzdx` | robots.txt `User-agent: * / Disallow: /`; not fetched | RESTRICTED |
| MoDOT `traveler.modot.org/timconfig/feed/desktop/mo_wzdx.json` | HTTP 403 "Request unsuccessful. Incapsula incident ID …"; not retried | RESTRICTED (bot wall). The St. Louis-area MoDOT feed above works |
| Wisconsin `511wi.gov/api/wzdx` | robots.txt HTTP 403: "The Amazon CloudFront distribution is configured to block access from your country" | UNREACHABLE (geo-block) |
| Oklahoma `oktraffic.org/api/Geojsons/workzones?access_token=…` | robots.txt and feed HTTP 403, Cloudflare "Attention Required" (CF-RAY …-BOM) | UNREACHABLE (blocked here) |
| Utah `udottraffic.utah.gov/wzdx/udot/v40/data` | robots.txt and feed HTTP 403 | UNREACHABLE |
| Iowa `iowa-atms.cloud-q-free.com/api/rest/dataprism/wzdx/wzdxfeed` | robots.txt and feed HTTP 403 (awselb) | UNREACHABLE; Iowa's 511 events are available on ArcGIS (below) |
| New Mexico `ai.blyncsy.io/wzdx/nmdot/feed` | HTTP 503 "no healthy upstream" twice | UNREACHABLE |
| Québec City `quebec.gewi.com/wzdx/pull` (WZDx 3.1) | timed out twice (45 s), although its robots.txt answered 404 at once | UNREACHABLE |
| NYSDOT `511ny.org/api/wzdx` | HTTP 200 but the new 511NY web app's HTML, not a feed; robots.txt returns the same HTML | Not working (registry entry outdated) |
| CivicLink CrewCast (replit app), PurposeBuilt Systems CWZ | Not government publishers | Not fetched |
| Colorado (WZDx and CWZ), National Park Service, MTC 511 SF Bay, VDOT SmarterRoads, Pennsylvania Turnpike, TxDOT DriveTexas, Illinois Tollway, Ohio OHGO, Michigan DOT, MassDOT CWZ, Illinois DOT CWZ, Oregon DOT | `needapikey: true` in the registry | NEEDS_KEY (not requested) |

### Connector notes (all WZDx feeds)

- **Shape:** GeoJSON `FeatureCollection` with `feed_info` (New England also
  repeats it as `road_event_feed_info`). Per feature: `id`;
  `properties.core_details` with `data_source_id`, `event_type` (`work-zone`
  or `detour`), `road_names[]`, `direction`, `description`, `name`,
  `creation_date`, `update_date`, `related_road_events`/`relationship`; and
  on `properties`: `start_date`, `end_date`, `is_start_date_verified`,
  `is_end_date_verified`, `vehicle_impact`, `lanes[]`,
  `beginning_cross_street`, `ending_cross_street`, mileposts,
  `types_of_work`, `worker_presence`, `reduced_speed_limit_kph`,
  `restrictions`. Geometry is WGS84 `LineString` or `MultiPoint` (a point
  work zone is a two-point MultiPoint).
- **Times:** ISO 8601 with `Z` or an offset on every record of every feed.
  Several feeds put dates at midnight: Maricopa 834 of 2,514 (local
  midnight, −07:00), North Dakota all 79 (−05:00), WSDOT 418 of 467 (UTC
  midnight). Treat those as dates.
- **Open-ended work:** the CARS feeds give far-future ends (end in 2030 or
  later: Kansas 184, Indiana 182, Minnesota 67). Treat them as "until
  further notice".
- **Bad ranges:** end before start in Idaho 20, Maryland 4, Kentucky 4,
  Maricopa 3.
- **Ended records:** most feeds drop them, but Maricopa (578), Kentucky
  (143), North Dakota (28) and Florida (16,094) keep serving them. Filter on
  `end_date`.
- **Verification flags:** `is_start_date_verified` is true on all Maryland,
  Maricopa, WSDOT and HaulHub records and false or absent elsewhere. Nothing
  in WZDx says whether work is happening right now except `event_status`
  (Kansas, North Dakota) and `worker_presence`.
- **Per feed:**
  - Maricopa (contact alemka@maricopa.gov): 10 data sources: Phoenix 1,152,
    Buckeye 550, ADOT 346 (statewide Arizona; the extent reaches
    −114.5..−109.4), Chandler 159, plus Goodyear, MCDOT, Mesa, Peoria,
    Scottsdale and Tempe. `vehicle_impact` is always "unknown"; impact is in
    `description`. 3.8 MB.
  - Indiana, Minnesota, Kansas (Castle Rock CARS): detours are separate
    `detour` features linked through `relationship`. Kansas uses older
    property names (`start_date_accuracy`, `event_status`). Indiana 4.4 MB.
  - New Jersey: all MultiPoint, `vehicle_impact` always "all-lanes-open"
    (not meaningful; lanes are in `description`). Served as `text/plain`.
  - Kentucky: ids such as `TRIMARC-303284`; contact kytcits@ky.gov; refreshed
    about every 30 minutes (registry).
  - MoDOT St. Louis: the feed's publisher is "Missouri Department of
    Transportation" (source `tms_work_zone`), although the registry names St.
    Charles County. Extent: St. Louis region only. Exactly 100 features,
    possibly a cap.
  - Delaware and Louisiana (HaulHub): rolling two-hour windows that start at
    the time of the last update (for example 12:05-14:05 UTC), probably from
    connected work-zone devices; not confirmed.
  - North Carolina: recurring work is expanded into one feature per day
    (6,343 distinct feature ids; the description ends with the works id,
    "Id: NNN"), so most "upcoming" rows are future days of the same works.
  - Florida: gzip-encoded (1.65 MB → 103 MB). 47 data sources, including
    contractors, counties, cities and FDOT. The `app_key` is printed in the
    USDOT registry with `needapikey: false`; using it is a choice for the
    user, like the QLDTraffic public key.
  - WSDOT: listed on the [Traveler Information API page](https://wsdot.wa.gov/traffic/api/)
    under "Additional Interfaces: Work Zone Data Exchange (WZDx) Version 4.2
    Current Work Zones". The page states no licence; its REST/SOAP services
    need an Access Code.
  - Idaho and North Carolina are the same 511 platform (publisher
    "Arcadis"). The developer pages describe WZDx as making "harmonized work
    zone data available for third-party use" and link the specification; no
    licence. [DriveNC disclaimer](https://drivenc.gov/about/disclaimer): "By
    accessing this website, you understand and agree to the following Terms
    of Use: … This website and all of its content are provided "As Is"" (a
    warranty and liability disclaimer only, no grant or restriction).
  - New England Compass: contact fields read "PLACEHOLDER"; ids such as
    `ME26-001712:em:event:Maine…`.

## United States: other state and city sources

### PERMITTED

**SFMTA Temporary Street Closures (San Francisco)**
- Request: `GET https://data.sfgov.org/resource/8x25-yybr.geojson?$limit=50000`.
  The WZDx copy is `https://data.sfgov.org/download/4ftp-yz2f` (WZDx 4.2,
  UTF-8 BOM). HTTP 200, no key.
- 4,279 lines from 364 cases (43 current, 3,657 upcoming, 579 ended).
  Newest `data_as_of` 2026-10-15 00:03; WZDx `update_date` 2026-10-15T20:00Z.
  Refreshed daily.
- Times: `start_utc`/`end_utc` (UTC) plus local `start_dt`/`end_dt`.
- Types: Roadway Shared Spaces 2,959 (recurring), Special Event 1,094,
  Special Traffic Permit 226; `veh_imp` all-lanes-closed 4,029.
- Status: Permitted 3,920, Application In Review 246, Submitted 92 and
  others, although the description says permitted closures only. Filter to
  Permitted.
- Licence: dataset metadata "Open Data Commons Public Domain Dedication and
  License" (PDDL); the WZDx copy "Creative Commons 1.0 Universal (Public
  Domain Dedication)". Credit SFMTA. No rate limit published.
- Sample: `sf-sfmta-temporary-street-closures_2026-10-16.geojson`.

**Chicago CDOT Transportation Department Permits (`pubx-yq2d`)**
- Request: `GET https://data.cityofchicago.org/resource/pubx-yq2d.json` with
  `$select` (personal contact columns left out),
  `$where=applicationenddate>='2026-10-16T00:00:00' AND streetclosure in('Full','Partial','Intermitte')`
  and `$limit=5000`. An unfiltered ordered query timed out once.
- 1,791 rows from 1,305 permits: 1,127 current, 664 upcoming.
  `streetclosure` Full 1,213, Partial 572; `applicationstatus` Open 1,352,
  Closed 439 (filter to Open). Point (lat/long) on 1,790 rows. Newest
  `applicationissueddate` 2026-10-15T17:15. Updated daily.
- Times: `applicationstartdate`/`applicationenddate`, Chicago local time
  without a zone, on every row.
- Types: work occupancy, street openings, block parties, athletic events,
  festivals.
- Terms ([City data disclaimer](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html))
  do not forbid commercial use, but:
  - an application using the data must show: "This site provides
    applications using data that has been modified for use from its original
    source, www.cityofchicago.org, the official website of the City of
    Chicago. The City of Chicago makes no claims as to the content,
    accuracy, timeliness, or completeness of any of the data provided at
    this site…";
  - "The City may require a user of this data to terminate any and all
    display, distribution or other use… for any reason";
  - there is an indemnity clause.
- Verdict: PERMITTED with these conditions (the user should accept them).
- Sample: `chicago-cdot-permits-closures_2026-10-16.json`.

**Iowa DOT 511 traveler events (ArcGIS)**
- Request: `GET https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/CARS511_Iowa_View/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
  HTTP 200, no key.
- 647 rows but only 329 distinct `ID`s (rows are duplicated). `STYLE`:
  roadwork 294, warning 128, future_event 102, closure 72, lane_closure 38,
  restriction 11. Point, WGS84. Newest `gisupdated` 20261016 072303 (local;
  about 12:23 UTC). Updated every 10 minutes.
- Times: `IssueDate`/`IssueTime` and `ExpireDate`/`ExpireTime` as yyyymmdd
  strings in Central time. `StartTime`/`EndTime` are daily hours only. For
  future events the start date is only in the headline ("Starts Sunday
  October 18").
- Line layer `511_IA_Event_Lines_View/FeatureServer/0`: 394 lines from 221
  events with epoch `IssueDT`/`ExpireDT`. Its geometry is declared as wkid
  102100 but holds lon/lat degrees, so `outSR=4326` returns points near
  (0,0). Query it without `outSR` and read the coordinates as WGS84.
- Licence (ArcGIS item `5e924db11ba94ce4bda1b38dfe0cdcdf`): "This work is
  licensed under a Creative Commons Attribution 4.0 International License."
  Access information: "Iowa Department of Transportation - Office of Traffic
  Operations". The item also links "Additional Terms and Conditions" on
  iowadot.gov (GIS and CARS-Hub terms). Those pages answered "Sorry, you have
  been blocked" (Cloudflare) and could not be read.
- The same owner publishes Nebraska, Missouri and Minnesota 511 copies, also
  CC BY 4.0; not fetched.
- Sample: `iowa-511-events-arcgis_2026-10-16.geojson`.

**Charlotte "Street Closures (Public)"**
- Request: `GET https://gis.charlottenc.gov/arcgis/rest/services/CDOT/StreetClosuresAndDetours/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson`.
  HTTP 200, no key. `maxRecordCount` is 300, so page with `resultOffset` if
  the layer grows.
- 241 lines: 32 current, 30 upcoming, 179 ended (4 have no start, 5 no
  end). `BLOCKTYPE`: Construction 167, Event 51, Festival 19.
  `ClosureType`: Street 192, Lane 49. `FULLCLOSE`: Yes 176. `ACTIVE` (Yes 217,
  No 22) does not match the dates; filter on `ENDDATE`. Newest
  `last_edited_date` 2026-10-15 23:43 UTC.
- Times: `STARTDATE`/`ENDDATE` epoch ms; many are local midnight (04:00 or
  05:00 UTC), with the hours in `StartHour`/`StartMinute`/`StartAMPM` and
  `EndHour`/`EndMinute`/`EndAMPM`.
- Other fields: `BLOCKNM` (street), `LOCDESC` (from/to), `COMMENT`,
  `DIRECTION`, `ALTROUTE`, `ClosureID`. **`CONTACT` holds names, e-mail
  addresses and phone numbers: drop it.**
- The service description says "This is used for editing street closures
  and detours", but the City's open-data hub item "Street Closures (Public)"
  (`24b353a2e9894b3abf8d73fa0805673d`, owner CharlotteNC, source "City of
  Charlotte") points to exactly this layer. Licence (hub item
  `licenseInfo`): `https://creativecommons.org/licenses/by/4.0/` (CC BY 4.0).
  Attribution: City of Charlotte. A detours layer (1) and an ArcGIS Online
  copy (`services.arcgis.com/9Nl857LBlQVyzq54/…/CharlotteStreetClosuresAndDetours/FeatureServer`,
  CC BY 4.0) were not fetched.
- robots.txt: `gis.charlottenc.gov` 404. `data.charlottenc.gov` has
  `Crawl-delay: 60`, which was respected.
- Sample: `charlotte-street-closures_2026-10-16.geojson`.

**Maryland Road Closures from MDOT CHART (`opendata.maryland.gov`, `nigh-m2sg`)**
- Request: `GET https://opendata.maryland.gov/resource/nigh-m2sg.json?$limit=5000`.
- 70 current closures on state roads, mostly planned shoulder and lane
  closures. Point (`location`, `lat`/`long`). Newest `updated`
  2026/10/16T08:20:01 (EDT). Updated every 20 minutes.
- Times: the start only as text in `created` ("Created: 10/16/2026 08:02 AM
  by TOC7."). **No end field.**
- Licence: metadata "Public Domain". Attribution: "Maryland Department of
  Transportation Coordinated Highways Action Response Team".
- The CHART hosts themselves (chart.maryland.gov, chartexp1 and chartimap1
  .sha.maryland.gov) answered "Sorry, you have been blocked" (Cloudflare)
  even for robots.txt; nothing more was fetched there.
- Sample: `maryland-chart-road-closures_2026-10-16.json`.

**Baton Rouge Road Closures (City-Parish DOTD Traffic Engineering, `ra2i-eye8`)**
- Request: `GET https://data.brla.gov/resource/ra2i-eye8.geojson?$limit=5000`.
- 20 active closures, all current: CONSTRUCTION 17, BRIDGE 3; Full 11,
  Partial 6, Bridge 3. MultiLineString. `start_date`/`end_date` in UTC on
  every row; newest start 2026-09-28. Fields follow the Waze CIFS layout
  (severity, direction, cross streets, recurring).
- Licence: "Public Domain". The history dataset `5bmt-pt5h` (since 2015) is
  also public domain.
- Sample: `baton-rouge-road-closures_2026-10-16.geojson`.

**DDOT Occupancy Permits (Washington DC), low value**
- Request: `GET https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/16/query?where=1=1&outFields=*&outSR=4326&resultRecordCount=2000&f=geojson`
  (layer 16 = last 30 days; layer 49 = 2026).
- 1,000 returned with the transfer limit hit: 430 current, 260 upcoming,
  310 ended. Point. `EFFECTIVEDATE`/`EXPIRATIONDATE` are dates (04:00Z).
  Newest `ISSUEDATE` 2026-10-16T10:38Z.
- Content: mostly construction staging, reserved parking and Lead Free DC,
  plus parades, marathons, block parties and filming. Status includes
  Rejected and Withdrawn.
- Licence: CC BY 4.0 ([data.gov record "Occupancy Permits in 2026"](https://catalog.data.gov/dataset/occupancy-permits-in-2026),
  publisher DCGISopendata); service copyright "DDOT and DC GIS".
- DC's `DDOT/HSEMA_RoadClosures/MapServer/1` is stale (one record from 2024).
- Sample: `dc-ddot-occupancy-permits-last30_2026-10-16.geojson`.

**Seattle SDOT Street Closures (`ium9-iqtc`), events only**
- Request: `GET https://data.seattle.gov/resource/ium9-iqtc.json?$limit=50000`.
- 115 rows (37 current, 77 upcoming, 1 ended): block parties, farmers
  markets, temporary activations and play streets. **No construction.**
  LineString. `start_date`/`end_date` are dates; hours are in weekday
  columns.
- Licence: "Public Domain"; attribution Seattle Department of
  Transportation.
- Sample: `seattle-sdot-street-closures_2026-10-16.json`.

**Austin Real-Time Traffic Incident Reports (`dx9v-zd7x`)**
- Request: `GET https://data.austintexas.gov/resource/dx9v-zd7x.json?$limit=5000&$order=published_date DESC`.
  A connector should use `$where=traffic_report_status='ACTIVE'`.
- 5,000 rows from 9 September to 16 October; only 3 were ACTIVE, the rest
  ARCHIVED. Point on 4,992. Newest `published_date` 2026-10-16T12:02:59Z.
  Updated every 5 minutes.
- Times: start `published_date`; **no end field**
  (`traffic_report_status_date_time` is when the status changed).
- Types: Crash Urgent, Traffic Hazard, COLLISION, Stalled Vehicle, debris,
  livestock.
- Terms ([Austin portal](https://data.austintexas.gov/stories/s/ranj-cccq)):
  "Data available through the City of Austin Open Data Portal are offered
  free and without restriction… Unless otherwise noted in metadata, datasets
  … are in the public domain." "Please provide attribution to both the City
  of Austin and the City Department that is the source of the cited data."
- Sample: `austin-traffic-incidents_2026-10-16.json`. The Austin WZDx feed
  (`austin-wzdx_2026-10-16.geojson`) is under the same terms and also
  declares CC0; its source is the AMANDA right-of-way and excavation
  permits; `vehicle_impact` some-lanes-closed 2,261, all-lanes-closed 394;
  updated hourly.

**Boston Public Works Active Work Zones, not usable**
- Request: `GET https://data.boston.gov/dataset/f9f57091-92f3-463a-8f1c-93e46361296d/resource/36fcf981-e414-4891-93ea-f5905cec46fc/download/tmp_nbii4sq.csv`.
- 460 rows, Last-Modified 2026-10-15. **No coordinates** (street and
  address only), no start date (`ExpirationDate`,
  `Estimated_Completion_Date`). Licence PDDL; the page calls it a "legacy
  dataset". robots.txt disallows `/api/` and `/datastore/` and sets
  `Crawl-delay: 10` (respected).
- Sample (for reference): `boston-pwd-active-work-zones_2026-10-16.csv`.

### ASK_PERMISSION, NEEDS_KEY, RESTRICTED (US, other)

- **DelDOT advisories** `https://tmc.deldot.gov/json/advisory.json`: 22
  points (construction, closures, flooding); start = publication
  `timestamp`, end only in text ("UNTIL OCTOBER 20, 2026"). No licence found.
  ASK_PERMISSION.
- **Norfolk VA Right of Way permits** (`mi4h-8pn3`): 1,310 open, 206 of
  type Closure, points with dates. No dataset licence; the city's page only
  says "Open Data is data that can be used, reused and redistributed by
  anyone without restriction or cost". ASK_PERMISSION.
- **WSDOT Highway Alerts KML** `https://wsdot.wa.gov/traffic/api/HighwayAlerts/kml.aspx`:
  keyless, 125 points, no start or end times; licence not found.
  ASK_PERMISSION.
- **Philadelphia Street Lane Closures** (layer behind StreetSmartPHL,
  `services.arcgis.com/fLeGjb7u4uXqeF9q/…/LaneClosure_Master/FeatureServer/0`):
  more than 2,000 lines (first page: Full Closure 761, Partial 1,142) with
  `effectivedate`/`expirationdate` as dates. Licence "City of Philadelphia
  License", whose text says "The City of Philadelphia reserves all rights in
  the database". No commercial grant: ASK_PERMISSION.
- **NEEDS_KEY:** DriveNC events (the old NCDOT TIMS endpoint now points to
  `drivenc.gov/help/endpoint/event`, which lists `key` as required); Georgia
  511 ("Requires a developer key… Ten calls every 60 seconds… A registered
  account is needed"); WSDOT Traveler Information API ("you must be assigned
  an Access Code"); Idaho 511 events API (developer key, ten calls a
  minute); and the registry's keyed WZDx feeds listed above.
- **RESTRICTED:** Pittsburgh WPRDC "DOMI Street Closures" (CC BY, hourly):
  the CSV is under `/datastore/dump/`, which robots.txt disallows. Caltrans
  CWWP2 lane closures and chain controls: robots.txt answered HTTP 500 twice
  on `cwwp2.dot.ca.gov` and once on `cwwp2-ssl.dot.ca.gov`; under RFC 9309 a
  5xx means assume full disallow, so nothing was fetched. NWS alerts
  (`api.weather.gov`, public-domain weather warnings): robots.txt is
  `User-agent: * / Disallow: /`.
- **Unreachable or gone:** Maryland CHART hosts and iowadot.gov terms pages
  (Cloudflare block); `data.iowa.gov` is now an "Iowa Data Hub" app and the
  Socrata dataset `deny-f47t` answers 404; Mesa AZ "Traffic Barricades"
  answers 404 (its permit data has no geometry). Los Angeles: no current
  closure dataset found.

## Canada (new)

### PERMITTED

**Halifax Street Closures (Halifax Regional Municipality, `opendata_HRM`)**
- Request: `GET https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Street_Closures/FeatureServer/0/query?where=END_DATE >= DATE '2026-10-15'&outFields=*&outSR=4326&orderByFields=START_DATE&f=geojson`.
  HTTP 200, no key.
- 41 not yet ended (25 current, 13 upcoming). The unfiltered layer holds
  more than 2,000 rows of history back to 2019 (pages of 2,000). Newest
  `MODDATE` 2026-10-15 14:56 UTC. LineString, WGS84 via `outSR`.
- Times: `START_DATE`/`END_DATE` are epoch ms at local midnight (03:00 or
  04:00 UTC); hours only in `START_TIME`/`END_TIME` text ("8:00am").
- Types: Construction, Development, Special Event, Utility, Block Party,
  Other. `CLOSURE_STAGE` is "Approved" on every row. Street, from/to,
  `COMMENTS`. English.
- Licence: OGL – Halifax ([licence page](https://data-hrm.hub.arcgis.com/pages/open-data-licence)):
  "grants you a worldwide, royalty-free, perpetual, non-exclusive licence to
  use the Information, including for commercial purposes … for any lawful
  purpose." Attribution: "Contains information licenced under the Open
  Government Licence – Halifax."
- Also available: `Street_Closures_Active` and `Street_Closures_Upcoming`.
  This is a different dataset from the sidewalk layer found on 15 October.
- Sample: `halifax-street-closures_2026-10-16.geojson`.

**City of Cambridge (Ontario) Road Closures**
- Request: `GET https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- 129 records, all current; newest `LAST_UPDATED` 2026-10-15 10:37 UTC
  (refreshed every 3 hours). LineString 117, MultiLineString 12.
- Times: `DATE_FROM`/`DATE_TO` epoch ms UTC with real times, on all 129.
- `REASON` mostly "Site Construction"; `STATUS` LOW / MODERATE / HIGH /
  FULL CLOSE; `DETAILS` gives the lanes and direction. **98 of 129 are
  parking-lane only.**
- robots.txt answers an HTML page (no rules).
- Licence: Open Data Licence v2.0 ([PDF](https://maps.cambridge.ca/images/opendata/Open%20data%20licence.pdf)):
  "licence to use the Information including for commercial purposes."
  Attribution: "Contains information licensed under the Open Government
  Licence – City of Cambridge."
- `CONTACT` holds names and phone numbers, which the licence excludes; drop
  it.
- Sample: `cambridge-on-road-closures_2026-10-16.geojson`.

**City of Kitchener Traffic_Closures**
- Request: `GET https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Closures/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- 48 records (36 current, 5 upcoming, 7 ended); newest `UPDATE_DATE`
  2026-10-14 21:01 UTC (hourly). LineString.
- Times: `DATE_FROM`/`DATE_TO` epoch ms UTC; 15 rows have no start and 21 no
  end.
- `STATUS`: Closed, Local Access Only, No Through Traffic, Partially Closed
  and similar. `REASON`: road reconstruction, water repair, special event.
- Licence (quoted in the item): OGL – The Corporation of the City of
  Kitchener v1.0, "worldwide, royalty-free, perpetual, non-exclusive licence
  to use the information, including for commercial purposes … No credit is
  required." Optional credit: "Contains information licensed under the Open
  Government Licence - The Corporation of the City of Kitchener."
- `CONTACT` holds staff names and phone numbers; drop it. The City's own
  `mapserver.kitchener.ca` answers 499 "Token Required"; use this ArcGIS
  Online copy.
- Sample: `kitchener-traffic-closures_2026-10-16.geojson`.

**Ville de Sherbrooke "Travaux"**
- Request: `GET https://services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/Travaux/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- 52 records (51 current, 1 upcoming; one empty row without geometry).
  Point. Newest `DATE_DEBUT` 2026-10-16 13:00 UTC; catalogue frequency
  "Quotidien".
- Times: `DATE_DEBUT`/`DATE_FIN` epoch ms UTC; `DATEDEBUTHE`/`DATEFINHE`
  repeat them as local-time strings.
- `TYPE`, `CIRCULATION` ("Route fermée" 11, alternating traffic 12, "Aucun
  impact" 17). Some rows are new streets being opened, not road events.
  French.
- Licence: "Licence Attribution (CC-BY 4.0)"
  ([Données Québec record](https://www.donneesquebec.ca/recherche/dataset/04880bdf6ffa40ababfa900c2ef45b3c_0)).
  Recommended citation: "VILLE DE SHERBROOKE - DONNÉES GÉOMATIQUES. Travaux,
  [Jeu de données], dans Données Québec, 2019, mis à jour le 01 juin 2026."
- Sample: `sherbrooke-travaux_2026-10-16.geojson`.

### Other Canadian results

- **ASK_PERMISSION:**
  - City of Waterloo `gis.waterloo.ca/maps/rest/services/Public/Public_Closures/MapServer/0`:
    47 lines with dates (15 current, 2 upcoming, 30 ended). Empty
    `licenseInfo`, and the layer is not in the City's catalogue
    (`opendata.waterloo.ca` timed out).
  - Oakville `maps.oakville.ca/oakgis/rest/services/SBS/Road_Closure/FeatureServer/0`:
    81 lines (20 current, 6 upcoming) without street names; no licence.
  - Abbotsford (`Transportation_Layers_External_Feature/FeatureServer/230`):
    history since 2018, 24 current and 12 upcoming in the first page; no
    licence.
  - Saskatchewan Highway Hotline: its own `/developers/doc` answered 404
    again. The Esri copy falls under [saskatchewan.ca/copyright](https://www.saskatchewan.ca/copyright):
    "Reproduction of any materials for commercial purposes requires the
    advance written permission of the Government of Saskatchewan."
- **NEEDS_KEY:** Manitoba 511, Alberta 511 and Québec 511 (as on 15
  October).
- **Unreachable:** Region of Waterloo (`gis.regionofwaterloo.ca`) and Barrie
  (`gispublic.barrie.ca`) timed out twice.
- **Gone or not found:** Nova Scotia 511 `/developers/doc` 404 again; Surrey's
  Open511 endpoint (`data.surrey.ca/open511/events`) now returns the City's
  ArcGIS Hub home page; no closure dataset found for Saskatoon, Regina,
  Hamilton (HTML listing only), Mississauga, York, Durham, Peel, Halton,
  Victoria, Kelowna, Laval, Gatineau or Longueuil.
- **Unchanged from 15 October (not re-researched):** Montréal VALIDATED;
  Québec MTMD YELLOW (robots unreadable); Vancouver blocked by robots.txt;
  Halifax sidewalk layer; Brampton VALIDATED.

## Latin America

Nothing usable was found.

- **Mexico City** (`datos.cdmx.gob.mx`, C5 road incidents): timed out
  twice. UNREACHABLE.
- **Bogotá** (`datosabiertos.bogota.gov.co`): timed out twice. UNREACHABLE.
  The Secretaría de Movilidad `Desvios_Piloto` and PMT layers carry no
  licence and were not fetched.
- **Medellín** `VM_Cierres_Movilidad` MapServer: robots.txt answered HTTP
  500 with a firewall "Web Page Blocked" page. Under RFC 9309 that means
  assume full disallow. RESTRICTED.
- **Chile, UOCT:** data is sold by quotation in UF (Decreto Exento 41;
  contact ventasrm.uoct@mtt.gob.cl). No open API. RESTRICTED.
- **Buenos Aires** API Transporte (closures under "tránsito"): the City's
  workshop repository says `client_id`/`client_secret` must be requested.
  Site content is CC BY 2.5 AR. NEEDS_KEY.
- **Brazil:** PRF and ARTESP publish historical accident CSVs only (not
  current events). Nothing found for São Paulo CET, Rio de Janeiro COR /
  data.rio or DNIT.
- **Peru** (MTC, Sutran): interactive maps only.

## Oceania

### PERMITTED

**Auckland Transport Roadworks (MyWorksites corridor-access and traffic-management worksites)**
- Request: `GET https://services2.arcgis.com/JkPEgZJGxhSjYOo0/ArcGIS/rest/services/PJ_Roadworks_MS/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&resultRecordCount=2000&f=geojson`.
  HTTP 200, no key. 1,000 features came back with `exceededTransferLimit:
  true`. Page with `resultOffset`; the total was not counted.
- Polygons (975 Polygon, 25 MultiPolygon), WGS84.
- Times: `ProjectStartDate`/`ProjectEndDate` on 1,000/1,000, epoch ms at UTC
  midnight (treat as dates). `WorkStartDate` on 698 (12:00Z = local
  midnight). `WorkCompletionDate` on 43.
- **646 of the first 1,000 have `ProjectEndDate` in the past while `Status`
  is "Active".** Filter on the end date.
- Fields: `WorksiteType` (Excavation 765, Non-Excavation 212, Event 23),
  `WorkStatus` (Started 635, Ready to start 302, …), `WorksiteCode`,
  `WorksiteName`, `PrincipalOrganisation`. English. Refreshed daily (FME,
  per the item).
- Licence: the item's `licenseInfo` is blank. The [AT data sources page](https://at.govt.nz/about-us/at-data-sources)
  says: "The data we release is free to use by developers, researchers and
  open data enthusiasts and is licensed under a Creative Commons licence:
  This work is licensed under a Creative Commons Attribution 4.0
  International License." The item is tagged "open data". Attribution:
  Auckland Transport. **Caveat:** the licence is the portal-wide statement,
  not set on the item itself.
- Sample: `auckland-transport-roadworks_2026-10-16.geojson`.

**City of Moreton Bay Weather Impacted Road Closures (QLD), low value**
- Request: `GET https://services-ap1.arcgis.com/152ojN3Ts9H3cdtl/arcgis/rest/services/RoadClosureProdView/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson`.
- 732 points: closure sites with a status, not events. `STATUS`: Open 731,
  Closed 1 (Dugandan Road, flooded since 2026-05-29). `REASON`: Flooded 651,
  Obstruction 61, Road Works 13, Smoke 4, Landslip 3. **No start or end**;
  only `UPDATETIME` (newest 2026-10-06T20:10Z). `TMR` flags state roads.
- Licence (item info): "This work is licensed under a Creative Commons
  Attribution 4.0 International License." Access information: "Moreton Bay
  Regional Council 2022".
- Under REI's display rules its events would stay hidden as "unconfirmed"
  (no source start or end).
- Sample: `moreton-bay-weather-road-closures_2026-10-16.geojson`.

### RESTRICTED: NZTA traffic and travel (the best NZ data)

- Request: `GET https://trafficnz.info/service/traffic/rest/4/events/all/10`
  with `Accept: application/json` (`10` is the required `{zoomlevel}`; WADL
  at `/rest/4?_wadl`). HTTP 200, no key.
- 302 `roadevent` records with unique ids: Active 124, Scheduled 109,
  Resolved 69 (status matches the dates). `eventType`: Road Work 118, Area
  Warning 98, Scheduled Road Work 79, Road Hazard 7. `impact`: Caution 242,
  Delays 43, Road Closed 16, Vehicle Restrictions 1. Newest `eventModified`
  2026-10-17T00:31:09+13:00.
- Geometry: WKT string in lon/lat (WGS84); POINT 204, MULTILINESTRING 98.
  `startDate` on 302, `endDate` on 282, ISO with +13:00. State highways
  only; sources NZTA, Police, NMC, Fire.
- robots.txt: `trafficnz.info` 404 (no rules); `www.nzta.govt.nz` serves an
  Incapsula check instead of robots.txt (not bypassed).
- Licence conflict:
  - The NZTA ArcGIS item for the same data
    ([itemInfo](https://services.arcgis.com/CXBb7LAjgIIdcsPt/ArcGIS/rest/services/NZTA_Highway_Information/FeatureServer/info/itemInfo?f=json))
    has `licenseInfo: "NZTA 4.0 BY CC"`.
  - The API terms of use ([nzta.govt.nz/…/use-our-data/terms-of-use](https://nzta.govt.nz/traffic-and-travel-information/use-our-data/terms-of-use)):
    "Other than as expressly permitted in these Terms of Use, these Terms of
    Use do not allow you to use the Travel Information for commercial
    purposes. If you wish to obtain a licence that allows you to charge
    users for the Travel Information you should contact the owner…" This
    was read from a search-engine excerpt, because the page is behind
    Incapsula.
  - The Journey Planner terms ([journeys.nzta.govt.nz/about-this-site](https://www.journeys.nzta.govt.nz/about-this-site),
    read directly): "may be reproduced for personal use without permission,
    as long as you attribute the work to Waka Kotahi NZ Transport Agency,
    and abide by the licence terms under the Creative Commons Attribution
    4.0 International licence … For permission to reproduce information on
    this website for any purpose other than personal use, contact the
    Information Team … informationteam@nzta.govt.nz".
- Verdict: RESTRICTED for commercial use until NZTA grants a licence
  (informationteam@ or opendata@nzta.govt.nz). The raw response is kept
  outside the samples folder: `scratchpad\aor\raw\C_trafficnz_events_all_10.json`.

### Other Oceania results

- **ASK_PERMISSION:** Whangārei District Council "RAMM Road Closures and
  Restrictions – All" (5 points, `cause`, `road_status`, `estimated_outage`;
  disclaimer "general information only … You indemnify Whangarei District
  Council…", no licence). Wellington City planned works (510 resurfacing
  polygons with programme months; copyright, no licence; not event data).
  Tasmania WFS: `GetCapabilities` has empty Fees and AccessConstraints; new
  layers `ssg:GEO_ROAD_WORKS_POINT` and `ssg:HVAMS_ROAD_WORKS`; still no
  commercial licence. NT Road Report: still no licence found.
- **NEEDS_KEY:** Auckland Transport developer portal (free registration,
  `Ocp-Apim-Subscription-Key`; per search excerpts 600 calls a minute,
  35,000 a week; mainly public transport and parking).
- **Empty now:** Christchurch `OpenData/CivilDefence` layers 3 and 4 (0
  records; filled only in emergencies); Environment Canterbury emergency
  road closures (0); Waikato CDEM "Local Road Status" (0); ACT "Major Road
  Works public view" (0). Christchurch `OpenData/Road/FeatureServer/3` is a
  works programme without dates.
- **Unchanged:** South Australia (`data.sa.gov.au/robots.txt` HTTP 403,
  awselb; geo-blocked earlier); Brisbane (robots.txt blocks `/api/` and
  downloads; no ArcGIS alternative found; a `road-restrictions` dataset was
  last updated 2025-11-06); City of Melbourne (only a 2024 copy); City of
  Sydney (none; TfNSW "Major_Events" layers are one-off maps without a
  licence).
- **Not found:** Sunshine Coast (map app only; its Socrata portal not
  checked), Logan, Ipswich, Newcastle, Parramatta, Geelong, Hobart, Darwin,
  Townsville, Cairns, Hamilton NZ, Tauranga, Dunedin. Ballina's EPAR
  roadworks layer has no licence and was not fetched. Pacific islands: Fiji
  Roads Authority closures appear only in news and situation reports;
  nothing for PNG or Samoa.
- `catalogue.data.govt.nz` pages answered an Imperva "Pardon Our
  Interruption" check; not bypassed.

## Samples

All in the session scratchpad, outside the repository:
`C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\b9dd17db-5e5d-47c6-ab68-7a67344a5a5d\scratchpad\research\global\americas-oceania\`.
Each is the raw response of the request shown (GET, no headers other than
the User-Agent unless stated).

| File | Request |
| --- | --- |
| `wzdx-feed-registry_2026-10-16.json` | `https://data.transportation.gov/resource/69qe-yiui.json?$limit=1000` |
| `wzdx-maricopa-mcdot_2026-10-16.geojson` | `https://wzdxapi.aztech.org/construction` |
| `austin-wzdx_2026-10-16.geojson` | `https://data.austintexas.gov/download/d9mm-cjw9` |
| `wzdx-indiana-indot_2026-10-16.geojson` | `https://in.carsprogram.org/carsapi_v1/api/wzdx` |
| `wzdx-minnesota-mndot_2026-10-16.geojson` | `https://mn.carsprogram.org/carsapi_v1/api/wzdx` |
| `wzdx-kansas-kdot_2026-10-16.geojson` | `https://ks.carsprogram.org/carsapi_v1/api/wzdx` |
| `wzdx-newjersey-njdot_2026-10-16.geojson` | `https://smartworkzones.njit.edu/nj/wzdx` |
| `wzdx-kentucky-kytc_2026-10-16.geojson` | `https://storage.googleapis.com/kytc-its-2020-openrecords/public/feeds/WZDx/kytc_wzdx_v4.1.geojson` |
| `wzdx-stcharles-modot_2026-10-16.geojson` | `https://scc.ridsi-dash.com:5000/wzdx.geojson` |
| `wzdx-maryland-sha_2026-10-16.geojson` | `https://filter.ritis.org/wzdx_v4.1/mdot.geojson` |
| `wzdx-northdakota-nddot_2026-10-16.geojson` | `https://travelfiles.dot.nd.gov/geojson_nc/wzdx_geojson.json` |
| `wzdx-delaware-deldot_2026-10-16.geojson` | `https://wzdx.e-dot.com/del_dot_feed_wzdx_v4.1.geojson` |
| `wzdx-louisiana-ladotd_2026-10-16.geojson` | `https://wzdx.e-dot.com/la_dot_d_feed_wzdx_v4.1.geojson` |
| `sf-sfmta-temporary-street-closures_2026-10-16.geojson` | `https://data.sfgov.org/resource/8x25-yybr.geojson?$limit=50000` |
| `chicago-cdot-permits-closures_2026-10-16.json` | `https://data.cityofchicago.org/resource/pubx-yq2d.json` with `$select` (no contact columns), `$where=applicationenddate>='2026-10-16T00:00:00' AND streetclosure in('Full','Partial','Intermitte')`, `$limit=5000` |
| `iowa-511-events-arcgis_2026-10-16.geojson` | `https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/CARS511_Iowa_View/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson` |
| `charlotte-street-closures_2026-10-16.geojson` | `https://gis.charlottenc.gov/arcgis/rest/services/CDOT/StreetClosuresAndDetours/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson` |
| `maryland-chart-road-closures_2026-10-16.json` | `https://opendata.maryland.gov/resource/nigh-m2sg.json?$limit=5000` |
| `baton-rouge-road-closures_2026-10-16.geojson` | `https://data.brla.gov/resource/ra2i-eye8.geojson?$limit=5000` |
| `dc-ddot-occupancy-permits-last30_2026-10-16.geojson` | `https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/FeatureServer/16/query?where=1=1&outFields=*&outSR=4326&resultRecordCount=2000&f=geojson` |
| `seattle-sdot-street-closures_2026-10-16.json` | `https://data.seattle.gov/resource/ium9-iqtc.json?$limit=50000` |
| `austin-traffic-incidents_2026-10-16.json` | `https://data.austintexas.gov/resource/dx9v-zd7x.json?$limit=5000&$order=published_date DESC` |
| `boston-pwd-active-work-zones_2026-10-16.csv` | `https://data.boston.gov/dataset/f9f57091-92f3-463a-8f1c-93e46361296d/resource/36fcf981-e414-4891-93ea-f5905cec46fc/download/tmp_nbii4sq.csv` (reference only; no coordinates) |
| `halifax-street-closures_2026-10-16.geojson` | `https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Street_Closures/FeatureServer/0/query?where=END_DATE >= DATE '2026-10-15'&outFields=*&outSR=4326&orderByFields=START_DATE&f=geojson` |
| `cambridge-on-road-closures_2026-10-16.geojson` | `https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1/query?where=1=1&outFields=*&outSR=4326&f=geojson` |
| `kitchener-traffic-closures_2026-10-16.geojson` | `https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Closures/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson` |
| `sherbrooke-travaux_2026-10-16.geojson` | `https://services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/Travaux/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson` |
| `auckland-transport-roadworks_2026-10-16.geojson` | `https://services2.arcgis.com/JkPEgZJGxhSjYOo0/ArcGIS/rest/services/PJ_Roadworks_MS/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&resultRecordCount=2000&f=geojson` (first 1,000 only) |
| `moreton-bay-weather-road-closures_2026-10-16.geojson` | `https://services-ap1.arcgis.com/152ojN3Ts9H3cdtl/arcgis/rest/services/RoadClosureProdView/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson` |

Raw responses of the ASK_PERMISSION and RESTRICTED sources that were
fetched (North Carolina, Florida, Idaho, WSDOT and New England WZDx, NZTA,
and others) are kept separately in `scratchpad\aor\raw\` and are not samples
for connectors.

## Not verified

- **Licences:**
  - Whether WSDOT, NCDOT, ITD (Idaho), FDOT/one.network and New England
    Compass intend their WZDx feeds to be CC0 as the specification requires.
    A one-line confirmation from each would settle it.
  - Iowa DOT's "Additional Terms and Conditions" (Cloudflare-blocked).
  - The NZTA API terms page, read only through a search-engine excerpt, and
    whether the "NZTA 4.0 BY CC" item licence overrides it.
  - FL511, 511PA, Mass511, Minnesota 511 and UDOT developer terms
    (`/developers/doc` 404 or host blocked).
- **Rate limits:** none is published for the PERMITTED sources. Socrata
  hosts may throttle without an app token; ArcGIS hosts publish no limit.
- **Update frequency:** Halifax, Charlotte, Baton Rouge and most WZDx
  feeds (the registry gives a nominal frequency per feed).
- **Totals:** the Auckland Transport total (first 1,000 read), Philadelphia,
  DC layer 16, and the MoDOT St. Louis feed (exactly 100: possibly capped).
- **Not fetched:** Iowa owner's Nebraska, Missouri and Minnesota 511 copies;
  Charlotte detours; Strathcona County, Wood Buffalo, Longueuil-area and
  Beaupré layers; Bogotá SDM layers; Brisbane `road-restrictions`; Sunshine
  Coast Socrata portal; Denver, Portland, Houston TranStar, San Diego (the
  web-search budget of the city research ran out).
- **From this machine only:** the Wisconsin, Oklahoma, Utah, Iowa (WZDx) and
  Maryland CHART blocks may be country-based; South Australia is known to
  be. Retry them from a US or production host before ruling them out.

## Access-rule notes

- Hosts whose robots.txt answered 4xx were treated as having no rules
  (RFC 9309) and their data URL was tried once: `oktraffic.org`,
  `udottraffic.utah.gov`, `iowa-atms.cloud-q-free.com` (all still 403),
  `us-datacloud.one.network` (robots 401, feed 200) and
  `api.dx.ne-compass.com` (robots 403 JSON, feed 200). Hosts whose robots.txt
  answered 5xx (Caltrans, Medellín) were treated as fully disallowed.
- `511ny.org/robots.txt` returns the web app's HTML (no rules); one feed
  request was made.
- The first robots.txt request to `scc.ridsi-dash.com:5000` failed locally
  (file name with a colon) and was repeated; both count against the host.
- `www.nzta.govt.nz`: robots.txt was unreadable (Incapsula), and one request
  for the terms page was still made; it also returned the check and was not
  retried.
- `data-hrm.hub.arcgis.com` sets `Crawl-delay: 60`; its licence page was
  fetched about 2 seconds after its robots.txt. Crawl delays on
  `data.charlottenc.gov` (60 s), `catalog.data.gov`, `data.boston.gov`,
  `data.wprdc.org`, `www.donneesquebec.ca`, `catalogue.data.govt.nz` and
  `journeys.nzta.govt.nz` (10 s) were respected.
- One discovery request to `catalog.data.gov/api/3/action/package_search`
  answered 404 (the catalogue's API has moved); it was not repeated.
- Busiest shared hosts: `www.arcgis.com` 9, `services.arcgis.com` 7,
  `services2.arcgis.com` 6. No host reached 10.
- Web search was used for discovery only. All page and data reads used the
  JSAN-REI client; the WebFetch tool was not used.
- The Florida feed was fetched with the `app_key` printed in the USDOT
  registry (`needapikey: false`). No key was requested or guessed anywhere.
