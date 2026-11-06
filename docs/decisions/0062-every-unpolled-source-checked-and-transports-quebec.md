# 0062 — Every unpolled source checked; Transports Québec road works connected

**Status:** 6 November 2026. Code local, tested, for the user to push. In production
the feed runs once `quebec-mtmd-road-works` is added to
`OFFICIAL_FEEDS_SCHEDULED_SOURCES` (a Railway change, after the user's go).

## Context

The user, 6 November 2026: "is everything working fine or in the tool there are
still 200+ sources are not connected check once every source and find the issue
and make solve it if possible".

Production at 20:28 IST: 305 source rows, 79 active and all 79 working (0
failing), 226 not polled. Each of the 226 was read from the registry with its
recorded reason, and those whose reason could have changed were tried again
from REI's server on Railway.

## The 226 unpolled sources

| Why not polled | Sources | Fixable here? |
| --- | --- | --- |
| Google News RSS, one per city: its terms allow personal use only | 59 | No |
| GDELT news search, one per city: switched off; refused (HTTP 429) from Railway on 6 Nov | 18 | No |
| Serper news search, one per city: paused, the account has no credits (decision 0061) | 17 | Credits |
| Terms silent, conflicting or restrictive: written permission needed (incl. 17 Indian news feeds, TomTom) | 44 | Permission |
| Needs a key, a registration or a contract (HERE, Mappls, NSW, Victoria, five Canadian 511s, Denmark, Tark Tee, Latvia's NAP, Poland's KPD, Gothenburg, Singapore, 511 SF Bay, 511NY …) | 23 | User's registration |
| Blocked: refused (403), robots.txt, down, or not published | 13 | Québec: yes (below) |
| Researched, cannot serve REI (no data, no location, history only) or published for people only | 28 | No |
| Found, not connected (mostly Hyderabad context pages; Poland's two hosts unreachable; DLR text only; ARTESP not yet published) | 15 | No, for now |
| Data checked, not connected (Montréal permits: time offsets unclear; Brampton: 6 closures; Copenhagen road-use permits: mostly not road events; TV9 Kannada: needs Kannada rules) | 4 | Later |
| Connected, switched off: TRK Karlsruhe and Basque Country (Railway blocked), DGT Spain (licence conflict), Roads ACT (CC BY-SA), Finland (robots.txt) | 5 | User's decision for three |

Tried again on 6 November 2026 from Railway: Québec MTMD (robots.txt now readable:
"User-agent: * / Allow: /"), South Australia (403, blocked by country), New Mexico
WZDx (503), Telangana GIS and BBMP (unreachable), Stockholm (layers still "not
published, awaiting a new supplier"), Digitraffic (robots.txt still
"Disallow: /api/"), Poland's GDDKiA and Warsaw hosts (connect timeout).

## Decision

Connect **Transports Québec road works** (`quebec-mtmd-road-works`,
`connectors/official/quebec_mtmd_roadworks.py`): the ministry's WFS layer
`ms:chantiers_mtmdet` as GeoJSON, the request Données Québec's own record
"travaux-routiers" links (CC BY 4.0). It was registered on 15 October 2026 as
blocked only because its robots.txt sat behind a Cloudflare challenge; on 6
November it was read from Railway and allows every client except named AI
crawlers. On 6 November: 361 segments of 265 works sites, every one with a line,
a start and an end (local Eastern time); a run keeps 352 (in force or coming):
243 lane restrictions, 100 closures, 9 road works. Polled hourly, one request.

The type is the strongest effect on road traffic the ministry's text (`entrave`)
states, at any hour, leaving out sections headed "Au besoin" (only if needed) or
for pedestrians and cyclists; the rules are in the module's docstring and tested
on real wording.

## Left for the user

- Finland (robots.txt "Disallow: /api/" on Digitraffic's documented open API), DGT
  Spain (dataset labelled CC BY, DGT's legal notice reserves commercial use) and
  Roads ACT (CC BY-SA share-alike): each is built and needs only a yes or no.
- Keys, registrations, credits and permission e-mails as listed in decision 0061
  and `docs/data-sources/zero-event-countries-recheck-2026-11-06.md`.

## Tests

`tests/unit/test_quebec_mtmd_roadworks_2026_11_06.py` on 8 real segments of 6
November 2026 (`tests/fixtures/quebec_mtmd_chantiers_2026-11-06.geojson`); the
official feed count in `tests/api/test_official_feed_scheduling.py` is 82.
