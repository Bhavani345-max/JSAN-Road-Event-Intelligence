# 0060 — Washington State work zones, and the rest of the US WZDx registry

**Status:** 6 November 2026. Code local, tested, for the user to review. In
production the feed runs once `wzdx-wsdot` is added to
`OFFICIAL_FEEDS_SCHEDULED_SOURCES` on the API service (a Railway change, after the
user's go).

## Context

The user asked whether free sources like TomTom or HERE exist "without any
permissions from their official", then "ok lets check" the US work-zone feeds.
USDOT's WZDx feed registry (data.transportation.gov dataset 69qe-yiui, read
6 November 2026) listed 42 active feeds: 15 REI already reads (decision 0034 and
later), 13 need a key, 14 need no key and were new to REI.

Under the rule of 16 October 2026, a new source is connected only when its terms
permit REI's commercial use; silent terms mean asking first. REI's WZDx feeds are
connected because each states CC0 1.0 in its own `feed_info.license`.

Each of the 14 was checked once: robots.txt first, then one GET from this machine,
and one more from REI's server on Railway where the first was refused.

## Decision

Connect **Washington State DOT** (`wzdx-wsdot`), a new entry in
`connectors/official/wzdx.py` read by the existing WZDx reader, listed on the
`united-states` entry with the zone America/Los_Angeles. Its `feed_info.license`
states CC0 1.0. On 6 November 2026: 434 features, 431 work zones with their own
ids, every one with a line, a start and an end marked verified; 358 in force or
starting within a year (98 of them upcoming). Its impact is "unknown" throughout,
so each is road works. Polled hourly like the other WZDx feeds.

Record the other 13 in `connectors/discovered_2026_11_06.py`, inactive and without
a connector:

| Feed | Found 6 November 2026 | Status |
|---|---|---|
| Oklahoma, Utah, Iowa, Wisconsin DOTs | HTTP 403 from both places | Blocked |
| Missouri DOT | HTTP 403 here; host not resolved from Railway | Blocked |
| New Mexico DOT (Blyncsy) | HTTP 503 "no healthy upstream" from both | Blocked; check its dates if it returns |
| Hawaii DOT (Blyncsy) | CC0, 133 work zones, but every one starts at the feed's update time and ends 7 days later, none verified | Not usable: the periods are not the works' own |
| Idaho TD (511, Arcadis) | 723 work zones; no licence in the feed; the site's terms page has no text | Terms silent: awaiting permission |
| Florida DOT (one.network) | 106 MB, 3,176 work zones; no licence; fl511.com's terms page has no text | Terms silent: awaiting permission |
| NHDOT, VTrans, MaineDOT (New England Compass) | 198 work zones; no licence; the states' traveler-information terms expect users to "download, store, and use the data" but say nothing about commercial use | Terms silent: awaiting permission |
| Mississippi DOT | robots.txt `Disallow: /` | Blocked, not fetched |
| CivicLink CrewCast | a community app; robots.txt `Disallow: /` | Not usable, not fetched |
| PurposeBuilt Systems | a company's diary in CWZ 1.0, 1 work zone | Not usable: not a road authority |

Registry URLs that carry an access token or app key (Oklahoma, Florida) are
recorded without it.

## Not done

- No permission e-mails sent: Idaho, Florida and the three New England states are
  the user's to ask.
- The 13 keyed feeds (Colorado, Texas, Virginia, Ohio, Michigan, Oregon, North
  Carolina, Massachusetts, Pennsylvania Turnpike, Illinois Tollway, IDOT, National
  Park Service) need a key each: the user's registration.
- No Railway change: `wzdx-wsdot` goes on the schedule only after the user's go.

## Tests

`tests/unit/test_us_wzdx_sources_2026_11_06.py`, on 5 real WSDOT work zones of
6 November 2026 (`tests/fixtures/wzdx_wsdot_sample_2026-11-06.geojson`); the
parametrised checks in `tests/unit/test_wzdx.py` cover the new feed too.
