# Global free/public road-event source research

Researched 6–13 October 2026. Every fact is tied to a source page or live
endpoint checked on the date shown, or marked as unverified. "Not established"
means it could not be found. This is source due diligence, not a formal legal
review.

The registry (`connectors/registry.py`, `connectors/official/`,
`connectors/discovered.py`) records each source with the same states.

## Integration states

| State | Meaning |
| --- | --- |
| CONNECTED | Fetched by REI. |
| VALIDATED | Real data fetched from the documented endpoint without credentials; not connected. |
| READY_FOR_INTEGRATION | Validated, terms allow the use, a connector could be written. |
| REQUIRES_ACCESS | Needs a key, an account, a contract or a partnership. |
| TERMS_REVIEW_REQUIRED | Reachable; its terms must be reviewed before use. |
| BLOCKED | Something other than credentials stops use (its own terms, a refused connection). |
| NOT_USABLE / MANUAL_ONLY | Not publicly available in machine-readable form. |

## Summary table

| Source | Country | City/Region | Authority | Source type | URL | Access method | Authentication | Cost | Rate limit | Terms status | Commercial use | Real-time | Coordinates | Road geometry | Road segments | Directions | Event types | Integration status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Transport for London road disruptions | GB | Greater London | Transport for London | AUTHORITATIVE_OFFICIAL | api.tfl.gov.uk/Road/all/Disruption | REST JSON | None (optional free app key) | Free | 50/min without key; ≤500/min per feed (terms) | Licence read: OGL v2.0 with TfL amendments | Permitted, with attribution | Yes | Yes (point) | Polygon / MultiPolygon on some | Yes (street segments as lines) | Yes (per street) | Works, collisions, asset faults, police activity | **CONNECTED** (run by hand) |
| City of Toronto road restrictions | CA | Toronto | City of Toronto, Transportation Services | AUTHORITATIVE_OFFICIAL | secure.toronto.ca/opendata/cart/road_restrictions/v3 | JSON / XML / CSV | None | Free | None published | Licence read: Open Government Licence – Toronto | Permitted ("any lawful purpose"), with attribution | Yes ("Real-time") | Yes | Polyline | No | Yes (both / one direction) | Road closed, construction | **CONNECTED** (run by hand) |
| NYC street closures (construction) | US | New York City | NYC DOT via NYC Open Data | GOVERNMENT_OPEN_DATA | data.cityofnewyork.us/resource/i6b5-j7bu.geojson | Socrata GeoJSON | None | Free | No numeric limit published; public API may throttle | NYC Open Data public-use policy | Permitted, with source attribution | No (work permits; updated periodically) | In geometry | MultiLineString | Yes (segment id) | No | Full construction closures | **CONNECTED** (run by hand) |
| France national road events (non-concession network) | FR | France | Ministry of Transport / Interdepartmental Road Directorates | GOVERNMENT_OPEN_DATA | transport.data.gouv.fr/resources/79174/download | DATEX II XML | None | Free | No request limit published; aggregate updated hourly | Licence Ouverte / Open Licence 2.0 | Permitted with attribution | Yes | DATEX point | No line geometry in checked records | No | Works, closures, diversions, accidents, hazards | **CONNECTED** (run by hand) |
| Fintraffic Digitraffic national road events | FI | Finland | Fintraffic / Digitraffic | GOVERNMENT_OPEN_DATA | tie.digitraffic.fi/api/traffic-message/v2 | Simple JSON / GeoJSON | None; app identification header | Free | 60/min per IP without app header; provider recommends identification | CC BY 4.0 | Permitted with attribution | Yes | Yes | Line and area geometry | Yes | Some records | Road works, traffic announcements, exceptional transports | **CONNECTED** (run by hand) |
| 511NY events API | US | New York State | NYSDOT | AUTHORITATIVE_OFFICIAL | 511ny.org/developers | REST JSON / XML | Developer key after access request and agreement | Stated "free" in a search snippet only | 10 calls / 60 s (search snippet) | Agreement text not retrievable | Not established | Yes | Yes | Encoded polyline | No | Yes | Events by type and severity | **REQUIRES_ACCESS** |
| Transport for NSW Live Traffic hazards | AU | New South Wales (Sydney) | Transport for NSW | AUTHORITATIVE_OFFICIAL | opendata.transport.nsw.gov.au | GeoJSON over HTTPS | API key after Hub registration | Not established (no page says free) | 60,000/day, 5/s (default plan) | Licence read: CC BY 4.0 | Permitted, with attribution | Yes | Yes | Point; polygons since v1.6 | No (roads listed) | Yes (lane level) | Incidents, roadworks, floods, fires, major events, alpine | **REQUIRES_ACCESS** |
| QLDTraffic GeoJSON | AU | Queensland | Queensland Department of Transport and Main Roads | AUTHORITATIVE_OFFICIAL | data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api | GeoJSON API | API key in developer specification | Key registration; price not established | Not established | Dataset listing says CC BY 4.0; endpoint terms to confirm | Attribution required | Yes | Yes | Feed-dependent | Not established | Hazards, crashes, congestion, floods, works, events | **REQUIRES_ACCESS** |
| Germany Autobahn roadworks, warnings and closures API | DE | Germany | Die Autobahn GmbH des Bundes | AUTHORITATIVE_OFFICIAL | verkehr.autobahn.de/o/autobahn | REST JSON by route | No key shown in checked endpoint docs | Unknown | Not established | Re-use terms not established | Not established | Yes | Point / extent fields | Not established | Not established | Works, warnings, closures | **TERMS_REVIEW_REQUIRED** |
| Spain DGT incidents (DATEX II 3.7) | ES | National roads, excluding Basque Country and Catalonia | Dirección General de Tráfico | AUTHORITATIVE_OFFICIAL | nap.dgt.es/en/dataset/incidencias-dgt-datex2-v3-7 | DATEX II | Access path not validated | Unknown | Not established | Re-use terms not established | Not established | Yes | In feed | DATEX location references | Not established | Incidents, affected sections | **TERMS_REVIEW_REQUIRED** |
| 511 SF Bay WZDx | US | San Francisco Bay Area | Metropolitan Transportation Commission / 511 SF Bay | GOVERNMENT_OPEN_DATA | api.511.org/traffic/wzdx | WZDx API | Free 511 key | Key registration | Not established | Feed/portal terms need review | Not established | Yes | Yes | WZDx work zones and closures | Detours | Work zones, closures, detours | **REQUIRES_ACCESS** |
| LTA DataMall traffic incidents / road works | SG | Singapore | Land Transport Authority | AUTHORITATIVE_OFFICIAL | datamall.lta.gov.sg | REST JSON | AccountKey for registered subscribers | Not established | 10 million calls/day; 500 records/call | Licence read: Singapore Open Data Licence v1.0 | Permitted, with attribution | Yes (2 min) | Incidents only | No | No | In text only | Accident, roadwork, breakdown, diversion, … | **REQUIRES_ACCESS** |
| Google News RSS search | Global | Any (per search) | Google | DISCOVERY | news.google.com/rss/search | RSS 2.0 | None | Free | None published | Feed notice: personal, non-commercial use in a feed reader only | **Not permitted** ("any other use … expressly prohibited") | Near | No | No | No | No | News headlines | **BLOCKED** (by its own terms) |
| Google News via Serper.dev | Global | Any (per search) | Serper (Google results) | DISCOVERY | google.serper.dev/news | REST JSON | API key | 2,500 free credits once, then paid | 1 credit per ≤10 results | Not reviewed | Not established | Near | No | No | No | No | News results | **CONNECTED** (Hyderabad) |
| Hyderabad Traffic Police | IN | Hyderabad | Hyderabad City Police | AUTHORITATIVE_OFFICIAL | htp.gov.in | Social media (X, Facebook, WhatsApp) | — | — | — | Not established | — | — | No | No | No | No | Advisories (text) | **MANUAL_ONLY** |
| Cyberabad Police / Traffic Pulse | IN | Hyderabad (Cyberabad) | Cyberabad Police | AUTHORITATIVE_OFFICIAL | cyberabadpolice.gov.in | Social media; Traffic Pulse is a personal alert sign-up | — | — | — | Not established | — | — | No | No | No | No | Advisories (text) | **MANUAL_ONLY** |
| Rachakonda (Malkajgiri) Police | IN | Hyderabad east | Rachakonda Police | AUTHORITATIVE_OFFICIAL | rachakondapolice.telangana.gov.in | None reachable | — | — | — | — | — | — | — | — | — | — | — | **NOT_USABLE** (3 addresses do not resolve) |
| Telangana State Police | IN | Telangana | Telangana State Police | AUTHORITATIVE_OFFICIAL | tspolice.gov.in | Website news only | — | — | — | Not established | — | — | No | No | No | No | — | **MANUAL_ONLY** |
| GHMC | IN | Hyderabad | Greater Hyderabad Municipal Corporation | AUTHORITATIVE_OFFICIAL | ghmc.gov.in | Website, PDF of division works | — | — | — | Not established | — | — | No | No | No | No | — | **MANUAL_ONLY** |
| HYDRAA | IN | Hyderabad | HYDRAA | AUTHORITATIVE_OFFICIAL | hydraa.telangana.gov.in | Website, social media | — | — | — | Not established | — | — | No | No | No | No | — | **MANUAL_ONLY** |
| TGiCCC | IN | Hyderabad | Telangana Police | AUTHORITATIVE_OFFICIAL | No public site found | — | — | — | — | — | — | — | — | — | — | — | — | **NOT_USABLE** (not publicly available) |
| Open Data Telangana | IN | Telangana | Government of Telangana | GOVERNMENT_OPEN_DATA | data.telangana.gov.in | Web portal; API path not found | Not established | — | — | Not established | — | No | — | — | — | — | No road-event dataset found | **DISCOVERED** |
| Telangana GIS (TRAC ArcGIS) | IN | Telangana | TRAC | GOVERNMENT_OPEN_DATA | tgracgis.telangana.gov.in | ArcGIS REST (per a third party) | Not established | — | — | Not established | — | — | — | — | — | — | Not established | **BLOCKED** (connection refused) |
| HMDA | IN | Hyderabad region | HMDA | AUTHORITATIVE_OFFICIAL | hmda.gov.in | Website notices | — | — | — | Not established | — | — | No | No | No | No | — | **DISCOVERED** |
| NHAI | IN | India | NHAI | AUTHORITATIVE_OFFICIAL | nhai.gov.in | None found | — | — | — | Not established | — | — | — | — | — | — | — | **MANUAL_ONLY** |
| TomTom Traffic Incidents | Global | 60+ supported markets | TomTom | COMMERCIAL | docs.tomtom.com/traffic-api | REST, API key | Account key | 2,500 incident requests/month free, then usage-based | Default QPS limits; 10,000 km² max bbox | Provider says commercial apps are allowed; product terms and data retention need review | Commercial use per plan terms | Yes | Yes | Yes | — | Yes | Jams, incidents, closures, works | **REQUIRES_ACCESS** (no key configured) |
| HERE Traffic | Global | Any | HERE | COMMERCIAL | docs.here.com | REST, API key | Key | Not established | Not established | Not reviewed | Contract terms | Yes | Yes | Yes | — | — | Incidents | **REQUIRES_ACCESS** |
| Waze for Cities | Global | Partner cities | Google (Waze) | COMMERCIAL | waze.com | Partner data exchange | Partnership | Partner only | — | — | Not permitted outside the programme | Yes | Yes | Yes | — | — | Jams, incidents, closures | **NOT_USABLE** |

## Hyderabad and Telangana

No Hyderabad or Telangana authority publishes road closures, diversions or
works in machine-readable form. This is unchanged since 2 October 2026 and was
re-checked on 6 October:

- the traffic police forces publish advisories only on X, Facebook and
  WhatsApp, and in press reports;
- the municipal and disaster bodies publish no feed, API or dataset of road
  events;
- the state open-data portal has no road-event dataset, and the state GIS
  service refused connections;
- TGiCCC, the command centre, has no public interface.

For Hyderabad, news (publisher feeds and search) therefore remains the only
machine-readable route, and all of it is discovery: tier 4, never confirmation.

## London: Transport for London (chosen first international city)

Fetched without a key on 6 October 2026: `GET /Road/all/Disruption` returned
115 to 116 disruptions. Every record has an id, a category and sub-category,
TfL's severity, a status, start and end times, a location and a point. 24 had
an area polygon or multipolygon. 26 listed streets, each with its direction
and closure, and segments as line strings.

Terms (tfl.gov.uk/corporate/terms-and-conditions/transport-data-service): the
Open Government Licence v2.0 with TfL's amendments. It grants a "worldwide,
royalty-free, perpetual, non-exclusive Licence", and allows exploiting the
information "commercially and non-commercially". Attribution required:
"Powered by TfL Open Data" and the Ordnance Survey and Geomni notices. Limits:
50 requests a minute without a key; at most 500 calls a minute per data feed.
The terms permit REI's testing, so London was chosen as the brief asked.

Not established: the feed's update frequency, and whether expired
disruptions can be retrieved later.

## Third city: Toronto

Chosen over New York, Sydney and Singapore because it is the only candidate
that is, at the same time, keyless (validated with real data), under a clear
licence that permits any lawful use, and rich enough for REI: coordinates, a
polyline, type, planned flag, directions affected, start and end.

- **New York** (NYC Open Data) was initially left for terms review. The public
  FAQ and policy were checked on 13 October; the keyless construction-closure
  dataset is now connected. Its scope is planned/full construction closures,
  not all traffic incidents.
- **Sydney** (Transport for NSW) has the richest data and a clear CC BY 4.0
  licence, but needs a registered key, and no page says the key is free.
- **Singapore** (LTA DataMall) needs a registered key; incidents have no id,
  no start or end, and direction only in text.

## Google News RSS

Every feed carries Google's notice: "This XML feed is made available solely
for the purpose of rendering Google News results within a personal feed
reader for personal, non-commercial use. Any other use of the feed is
expressly prohibited." news.google.com's robots.txt also disallows automated
access outside a short allow-list that does not include `/rss`. Google's
Terms of Service prohibit automated access "in violation of the
machine-readable instructions on our web pages (for example, robots.txt
files …)".

REI's use is neither personal nor a feed reader. The connector was built and
tested on a saved feed, but the source is registered as BLOCKED by its terms
and is never fetched. No official rate limit was found.

## What could not be verified

- TfL: update frequency; historical availability; whether the 500-a-minute
  key is free of charge (the page says "apply online", with no price).
- Toronto: any rate limit; historical availability.
- New York: Socrata throttle numbers and any contractual service guarantees.
- Sydney and Singapore: whether their keys cost anything.
- Hyderabad: Cyberabad Traffic Pulse content (malformed server response); any
  Rachakonda or Malkajgiri website; any dataset on the state portal; the state
  GIS services.
- Google News RSS: any official rate limit or current feed-specific terms
  page other than the notice in each feed.

## Research checked 13 October 2026

- **New York City:** fetched the live Socrata GeoJSON endpoint
  (`/resource/i6b5-j7bu.geojson`) without a key. It returned 3,895 features;
  the checked record had a MultiLineString, work start/end dates, a street and
  cross streets. NYC DOT describes the dataset as full street closures for
  construction. NYC's open-data FAQ says there are no restrictions on use;
  the public-policy page says city datasets are published without
  registration, licence or use restrictions unless an exception is stated.
  The city and source are connected; the source itself is inactive unless
  run manually or official-feed scheduling is enabled. [Dataset](https://catalog.data.gov/dataset/street-closures-due-to-construction-activities-by-block),
  [NYC FAQ](https://www.nyc.gov/opendata/get-started/FAQs),
  [NYC Open Data policies](https://cityofnewyork.github.io/opendatatsm/publicpolicies.html).
- **France:** downloaded the 4.38 MB public Bison Futé aggregate feed. It
  contained 371 DATEX II situations and 775 records, including roadworks,
  closures, diversions, accidents, obstructions and hazards. The aggregate is
  updated hourly; the source connector keeps a source-provided point where
  present and leaves records without a point unresolved. It covers the
  non-concession national road network. Concessioned motorways use a separate
  access-restricted feed. The dataset is under Licence Ouverte 2.0. [Dataset
  and feed](https://transport.data.gouv.fr/datasets/evenements-routiers-sur-le-reseau-routier-national-non-concede/),
  [Bison Futé data access](https://www.bison-fute.gouv.fr/donnees-sur-la-circulation-du%2Clanges.html).
  First REI ingestion on 13 October stored 3,568 New York and 658 France
  events awaiting validation. Remaining records were duplicates, outside the
  active/upcoming window or excluded by the road-block rules.
- **United States:** the FHWA WZDx page listed active feeds from Texas, Iowa,
  Maricopa County, Massachusetts and North Carolina. WZDx standardizes work
  zone details, but each jurisdiction has its own endpoint and terms. The
  511 SF Bay feed requires a free API key. These are regional sources, not a
  single nationwide feed. [FHWA WZDx](https://ops.fhwa.dot.gov/wz/wzdx/index.htm),
  [511 SF Bay FAQ](https://511.org/open-data/faqs).
- **Europe:** EU rules use DATEX II and National Access Points for exchanging
  road and traffic information. This is a network of national/regional feeds,
  not one centralized EU event API. Spain's DGT NAP lists a DATEX II 3.7
  incidents feed, but this pass did not establish its current direct URL or
  licence. Germany's Autobahn API exposes route-based current works, warnings
  and closures; its re-use terms and rate limits need review. [EU
  regulation](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R0670),
  [DGT NAP](https://nap.dgt.es/en/dataset?organization=dgt&tags=incidencias),
  [Autobahn alerts](https://www.autobahn.de/betrieb-verkehr/verkehrsmeldungen).
- **Australia:** Queensland's official open-data catalogue describes GeoJSON
  feeds for hazards, crashes, congestion, flooding, works and events and lists
  CC BY 4.0. Its developer specification requires an API key; the live
  endpoint and key conditions still need validation. NSW also has a richer
  real-time API that requires a registered key. [Queensland listing](https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api).
- **Global commercial option:** TomTom's current incident documentation
  supports 60+ countries and its pricing page lists 2,500 free incident
  requests per month before usage-based pricing. Each incident request is
  limited to a 10,000 km² bounding box, so large regions require multiple
  requests and can exceed the free allowance quickly. A key and service-term
  review are needed before enabling it. [Market coverage](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/market-coverage),
  [pricing](https://docs.tomtom.com/pricing),
  [incident API](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-incidents/incident-details).

- **Finland, now connected:** Fintraffic publishes national road-work and
  traffic-announcement feeds in Simple JSON with source geometry. A live
  snapshot checked on 13 October 2026 returned 554 road-work features, 12
  traffic announcements and one exceptional transport before REI's current
  and upcoming window is applied. The feeds are keyless and licensed under
  CC BY 4.0; REI records attribution and keeps derived events in the human
  validation queue. References: [Digitraffic road traffic documentation](https://www.digitraffic.fi/en/road-traffic/),
  [API instructions](https://www.digitraffic.fi/en/support/instructions/),
  and the [Fintraffic data catalogue](https://catalog.digitraffic.fi/en/dataset/21ef7ded-01bc-47ac-a534-1fe3ede030df/resource/92c0578f-3a44-4047-95cf-e3c8522b9aff).

## Current integration limits

Connected sources now include municipal and national feeds across North
America, Europe and India, plus Finland's national road network. No single
public feed provides complete worldwide coverage. TomTom and account-key
sources remain unconfigured; TomTom also needs service-term review before REI
stores its incident data. Run one source with
`python backend/cli/ingest_source.py <source_id>`, or seed a current snapshot from
all connected, non-discovery sources with `python backend/cli/seed_worldwide.py`;
set `REI_API_URL` to the API origin when seeding a remote deployment.
`OFFICIAL_FEEDS_SCHEDULED=true` enables the sources' individual schedules.
