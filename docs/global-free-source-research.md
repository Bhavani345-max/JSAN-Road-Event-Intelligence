# Global free/public road-event source research

Researched 6 October 2026. Every fact comes from a page or an endpoint that
was actually fetched that day, or is marked as coming from a search result or
a third party. "Not established" means it could not be found. Nothing here is
a legal review: "terms read" means the licence text was read, not that a
lawyer has approved REI's use of it.

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
| NYC street closures (construction) | US | New York City | NYC DOT via NYC Open Data | GOVERNMENT_OPEN_DATA | data.cityofnewyork.us (i6b5-j7bu) | Socrata JSON / GeoJSON / CSV | None (optional free app token) | Free | Not published; may throttle without a token | Not established: licence "not specified"; terms pages 404 | Not established | No (weekly) | In geometry | MultiLineString | Yes (segment id) | No | Full closures for works | **VALIDATED** (terms review needed) |
| 511NY events API | US | New York State | NYSDOT | AUTHORITATIVE_OFFICIAL | 511ny.org/developers | REST JSON / XML | Developer key after access request and agreement | Stated "free" in a search snippet only | 10 calls / 60 s (search snippet) | Agreement text not retrievable | Not established | Yes | Yes | Encoded polyline | No | Yes | Events by type and severity | **REQUIRES_ACCESS** |
| Transport for NSW Live Traffic hazards | AU | New South Wales (Sydney) | Transport for NSW | AUTHORITATIVE_OFFICIAL | opendata.transport.nsw.gov.au | GeoJSON over HTTPS | API key after Hub registration | Not established (no page says free) | 60,000/day, 5/s (default plan) | Licence read: CC BY 4.0 | Permitted, with attribution | Yes | Yes | Point; polygons since v1.6 | No (roads listed) | Yes (lane level) | Incidents, roadworks, floods, fires, major events, alpine | **REQUIRES_ACCESS** |
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
| TomTom Traffic Incidents | Global | Any | TomTom | COMMERCIAL | docs.tomtom.com | REST, API key | Key | Free tier with limits, then paid | 2,500 requests/month free (docs, 2 Oct) | Not reviewed | Contract terms | Yes | Yes | Yes | — | Yes | Incidents incl. closures, works | **REQUIRES_ACCESS** (not integrated: paid phase) |
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

- **New York** (NYC Open Data) is keyless and validated, but its licence is
  not stated and its terms pages could not be reached; records have no
  direction and no incident category. 511NY needs an access agreement that
  could not be read.
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
- New York: licence and terms; Socrata throttle numbers; the 511NY agreement.
- Sydney and Singapore: whether their keys cost anything.
- Hyderabad: Cyberabad Traffic Pulse content (malformed server response); any
  Rachakonda or Malkajgiri website; any dataset on the state portal; the state
  GIS services.
- Google News RSS: any official rate limit or current feed-specific terms
  page other than the notice in each feed.
