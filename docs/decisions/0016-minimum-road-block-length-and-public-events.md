# 0016 — A 200 m minimum for road blocks; public events at their exact location

Date: 2026-10-07. Status: **superseded on 2026-10-08** by [0018](0018-no-length-filter-no-invented-expiry-history-visible.md): the length minimum is withdrawn (the brief of 8 October 2026, s.8); the public-event rules stand.

## Context

The user pointed at two City of Toronto closures: "Sherbourne St 24 m North
of Gerrard St E to 45 m North of Gerrard St E" (about 20 m long) and "Nicholson
Lane at Berkeley St to 33 m East of Princess St" (whose line seemed to lie on
a building), said there were many like them, and asked for: a minimum length
of 200 m for road blocks, and, for road blocks for public events (meetings,
speeches), the exact location.

Measured on 7 October 2026: of 65 stored Toronto closures, 54 were under
50 m and only 3 reached 200 m. Most are utility cuts (gas, water, hydro) of a
few metres. The Sherbourne line is exactly what Toronto publishes (two points
21 m apart). The Nicholson Lane line follows the lane on OpenStreetMap within
about 1 m: the lane is a narrow alley between buildings, so a 4–6 px line
covers the buildings beside it at city zoom.

## Decision

- **Minimum length** (`packages/source_models/road_block.py`): a road block
  an official source draws shorter than 200 m is not an event. The length is
  the source's own: the stretches it marks closed (Toronto "ROAD_CLOSED", TfL
  "Closed") and draws as lines. Nothing is estimated: a closure drawn as a
  point or an area, or with no line, cannot be measured and is kept; a
  restriction that does not close the road (works, an open street) is not
  measured.
- **Public events are kept at any length**: SPECIAL_EVENT, PUBLIC_PROCESSION,
  MARATHON, SPORTING_EVENT, VIP_MOVEMENT (Toronto's `specialEvent: Yes` and
  TfL's "Special and planned events" are SPECIAL_EVENT).
- The connectors leave short road blocks out **before** the per-run limit
  (30 records), so the run's places go to closures that count. They are still
  counted as observed, so they are never reported "missing from the feed".
- Stored short closures were rejected by reprocessing, not deleted, with the
  reason "Road block N m long, under the 200 m minimum"; a reviewer can
  reopen one. Their records stay as evidence, classified
  `BELOW_MINIMUM_LENGTH`.
- **Meetings, speeches, roadshows, sabhas and protests** are now public
  events in the news rules (still only with a road measure and a Hyderabad
  place). "Parade Grounds" is a venue, not a parade. A specific kind (a VIP
  visit, a parade) wins over the general "public event".
- **Exact location**: the details panel of a public event's road block says
  where it is exactly (the stretch or venue the source gives), or, when the
  source names only a place, that the exact spot is not given and should be
  marked with "Correct location" before approval (approximate locations
  cannot be approved: QC rule, unchanged).

## Trade-off the user should know

A short full closure can still block a street completely: "McRoberts Ave at
St Clair Ave W to 3 m North" closes the mouth of McRoberts Ave. Under this
rule it is not an event. The minimum is one constant
(`MIN_ROAD_BLOCK_LENGTH_M`) if this needs revisiting.

## Result on 7 October 2026

Reprocessing rejected 64 short road blocks (62 Toronto, 2 London). A fresh
Toronto run brought 27 new closures of 200 m or more (30 in all). Backup:
`apps/api/.data/backups/rei-2026-10-07-before-200m-minimum.db`.

## Location check (7 October 2026)

Every one of the 30 remaining Toronto closures was checked against
OpenStreetMap's roads (Overpass: every road within 80 m, the drawn line
sampled every 10 m). All 30 lie on a road along their whole length (within
15 m); 28 lie on the road they name or its from/to streets. The other two are
expressway ramps (Gardiner and DVP), which OSM leaves unnamed; both are within
5 m of a road. No location needed changing. An earlier check with Nominatim
reported lines "off the road"; that was the check's fault (it returns only one
section of a long road), not the data's.
