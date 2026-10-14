# 0027 — More official sources: NYC permitted events, DiaLog and Lyon

**Status:** accepted, 14 October 2026.

## Context

The user asked to remove failing sources, fix them if possible, and add more
working sources for every location. The research of 14 October
([source-research-2026-10-14.md](../data-sources/source-research-2026-10-14.md))
checked candidates for all eight configured locations. Three passed every
test: a live, keyless endpoint with current records, and terms that allow
REI's automated, commercial use. India has none: every news publisher checked
restricts such use, and the official sites need permission by email or have
nothing current.

## Decision

Three official sources are connected, tier 1, run by hand like the other
official feeds unless `OFFICIAL_FEEDS_SCHEDULED` is set:

- **NYC permitted events closing streets** (`connectors/official/nyc_events.py`,
  `nyc-permitted-events`): NYC Open Data `tvpp-9vvx`, only rows marked "Full
  Street Closure" or "Sidewalk and Street Closure", not yet ended. One record
  per row (one day of one event at one place, as the source lists it). Parades
  are processions, athletic races are marathons, the rest special events.
  Times without an offset are New York time, as for NYC DOT's closures. The
  places are street names only; New York has no place list, so these events
  stay unlocated until a reviewer places them.
- **DiaLog traffic orders** (`connectors/official/dialog.py`,
  `france-dialog-traffic-orders`): the national database of temporary traffic
  orders, current and upcoming. An order closing a road is a planned closure
  (an emergency closure when its subject is an incident); a diversion is a
  diversion; otherwise roadworks, a special event or a hazard by its subject.
  Orders that only ban parking are not road events. DiaLog's
  GeometryCollections become one MultiLineString of their lines, a MultiPoint
  its first point: shapes REI stores, from the source's own coordinates.
- **Métropole de Lyon works disrupting traffic** (`connectors/official/lyon.py`,
  `lyon-disruptive-works`): the works the Métropole lists as closing or
  reducing traffic, with the work site's polygon. "Circulation interdite" is a
  planned closure; reduced, alternating or one-way traffic a lane restriction.
  Dates are whole days in Paris time.

The two filtered queries (NYC, DiaLog) report no `observed_ids`: a record
leaving them has usually ended, and is not counted missing. Lyon's layer is the
full list and reports them, like TfL.

## Not decided here

- Six French Opendatasoft portals (Paris ×2, Rennes, Toulouse, Bordeaux,
  Loire-Atlantique) are disallowed by robots.txt (`Disallow: /api/`), as is
  the Digitraffic API already used for Finland. Whether robots.txt binds a
  documented open-data API is the user's call; Digitraffic is left as it was.
- Sources needing a free key or an access request (Ontario 511, National
  Highways, Street Manager, 511NY, Grand Lyon real time, Bison Futé Action b)
  wait for the user to register.
- Oulu's traffic announcements wait until their time zone is established.

## Applied

Local database, 14 October 2026, after a backup
(`backend/.data/backups/rei-2026-10-14-before-new-official-sources.db`): 74
NYC, 477 DiaLog and 361 Lyon events, all awaiting validation; no merge
candidates with the existing France events. Production gets the sources with
the next deployment of the API; they run there only when someone presses
Check, or every few hours once `OFFICIAL_FEEDS_SCHEDULED=true` is set.

Tests: `tests/unit/test_more_official_sources.py`, on real records of each
source (`tests/fixtures/nyc_permitted_events_2026-10-14.json`,
`dialog_regulations_2026-10-14.json`,
`lyon_chantiers_perturbants_2026-10-14.json`).
