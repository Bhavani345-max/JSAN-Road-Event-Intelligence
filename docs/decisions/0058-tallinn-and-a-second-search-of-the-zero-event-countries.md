# 0058 — Tallinn connected; a second search of the six countries with no event

**Status:** 5 November 2026. Code local, tested, for the user to review and push.
In production the Tallinn feed runs once `tallinn-street-closures-and-works` is
added to `OFFICIAL_FEEDS_SCHEDULED_SOURCES` on the API service (a Railway change,
after the user's go).

## Context

The user, 5 November 2026: "try for more free sources for all the countries which
has no events and no sources are working". Read-only, production had no event at
all for six countries: Brazil, Estonia, Ireland, Latvia, Malaysia and Poland
(South Africa had 2, from SAnews). The 4 November search (decision 0053;
`docs/data-sources/{baltics-poland-ireland,brazil-malaysia}-sources-2026-11-04.md`)
had found nothing REI may connect in any of them.

Five research agents searched again the same day, only where the 4 November
search had not looked, under the rules since 16 October: connect only what the
terms permit for REI's use, record the rest with the reason, register nowhere,
read robots.txt first, at most 8 requests per host, 2.5 s apart. The full record
is `docs/data-sources/zero-event-countries-sources-2026-11-05.md`.

At the same time another session added a Portuguese Google News search for
Brazil through Serper (decision 0057), the user's choice there; nothing here
changes it.

## Decision

### Connected: Tallinn street closures and works (Estonia)

- `connectors/official/tallinn_opinfo.py`, source `tallinn-street-closures-and-works`,
  tier 1, government open data, a new city entry `tallinn` (within Estonia).
- Two XML files from the city's opinfo.tallinn.ee system, no key, no robots.txt:
  street closures (`objektid/xml/183ac3aa`) and works on city land
  (`objektid/xml/f2325e11`), read as one by object id (the closures are in both).
- Licence: **CC BY 3.0**, as the Estonian open data portal states for both files
  (`andmed.eesti.ee`, publisher Tallinna Linnavalitsus). Recorded as permitted with
  attribution, never as settled: no legal review (decision 0009).
- Only events on the carriageway, as for Copenhagen (decision 0053):
  - a closure whose own widths close the whole carriageway is a road closure,
    part of it a lane restriction; a closure of the pavement or a square only, or
    of 0 m of the carriageway, is not kept;
  - an excavation (or emergency excavation) in the carriageway is road works;
    one in the pavement or a green area only is not kept;
  - road works that give no place on the street, haulage, weight-limit and
    night-work permits, heating interruptions and street-lighting maintenance
    are not kept.
- Times are Tallinn time; how the period runs ("pidev", "iga päev" with its hours)
  is kept in the stated period, not read as the period.
- Shapes come from the KML field (WGS 84); the GeoJSON field is in L-EST97 and is
  not read. A first coordinate above the second (latitude first) stops the run.
- Personal data: applicant, client, contractor and owner are dropped before
  anything is stored; telephone numbers and e-mail addresses are removed from the
  free text.
- Live on 5 November 2026 (09:07 UTC): 610 objects, **193 kept** (25 road
  closures, 91 lane restrictions, 77 excavations), 170 in force and 23 coming, all
  with a shape, a start and an end. Production reached the feed (HTTP 200 in 3 s).

### Recorded, not connected (`connectors/discovered_2026_11_05.py`)

| Country | Source | Why not |
| --- | --- | --- |
| IE | Meath County Council road notices (ArcGIS) | No licence on the service; meath.ie forbids reproduction without written authorisation |
| IE | Cork City Council road closure alerts (ArcGIS) | No licence; corkcity.ie forbids reproduction without written authorisation |
| IE | Limerick road notices map | No terms beyond copyright; no feed |
| IE | Dún Laoghaire-Rathdown traffic news | Licence permits reuse, but 5 text-only closures, no coordinates |
| PL | ZDiTM Szczecin notices for drivers (Atom) | CC0 is stated for the developer data, not clearly for this feed |
| PL | ZDiZ Gdynia road messages | Data host answered HTTP 401 |
| PL | Łódź road works page, Kraków ZDMK works list | No licence stated; web pages only |
| BR | COR Rio closures feed (RSS) | Terms forbid copying without COR's written consent |
| BR | DNIT federal highway alerts (gov.br) | CC BY-ND 3.0: no adaptations |
| MY | NADMA disaster portal road closures | Behind a login; "Hak Cipta Terpelihara" |

The 4 November entries for Tark Tee (Estonia: the open data portal now lists
CC BY) and the Latvian NAP (sample files carry WGS 84 points; an account needs
only an e-mail) were brought up to date. Both still need the user to register.

## Consequences

- Estonia is no longer empty once Tallinn is scheduled in production. Brazil,
  Ireland, Latvia, Malaysia and Poland still have no source REI may use without a
  key or a publisher's permission; the report lists who to write to.
- Fastest further gains: the Latvian NAP (free account, CC0; REI's DATEX 3 reader
  needs `openlrCoordinates` added) and Tark Tee (registration, staff review, CC BY).
- The research agents could not write their own report files; their findings are
  copied into the report. One agent sent one request to a Warsaw host after its
  robots.txt had timed out (against the rule); it was refused and nothing was
  received. This is noted in the report.

## Verified

`tests/unit/test_tallinn_opinfo.py` on real excerpts of both files (12 objects,
6 kept): city and bounds, source definition, registration, which objects are
kept and their types, Tallinn time and stated periods, KML shapes, no personal
data and contact details, a cut, miscounted or swapped file refused, and
ingestion into events awaiting validation. Official feed count 56 → 57
(`tests/api/test_official_feed_scheduling.py`). A live fetch (two requests,
nothing stored) gave the counts above.
