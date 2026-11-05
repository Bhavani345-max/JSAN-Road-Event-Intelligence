# 0056 — Events near a place found with "Find place"

**Status:** 5 November 2026. Code local, tested, for the user to review and push.

## Context

The user, 5 November 2026: "in the find places in the dashboard it locating the
only place that we search, i want to find events in the place so, if i select
place then events in that place will be highlighted".

Decision 0055 only moved the map to the place and pinned it.

## Decision

- **What counts as in the place** (`frontend/features/map/placeArea.ts`):
  - **Its own area** when OpenStreetMap gives it one: the box of a suburb or
    ward (Gachibowli: about 4.4 × 4.2 km), when its longer side is 500 m or more.
  - Otherwise **a distance from its point**: a postcode has no boundary in OSM
    (its box is an estimate around a point: 10 × 10 km for PIN 500032, checked
    5 November 2026), a street comes back as one short piece of it (Road
    Number 1, Banjara Hills: 220 m), and REI's own place lists give points.
    Default 2 km for postcodes and areas (wards, suburbs, REI's "area" kind),
    1 km for anything else (landmarks, roads, junctions).
  - The user can switch between **Its area** (when there is one), **500 m**,
    **1 km**, **2 km** and **5 km**. Nothing is made up: the area or the circle
    is drawn on the map and named in the count ("4 events inside the outlined
    area", "7 events within 5 km").
- **Which events**: located events of the list (the same filters, view and
  search) whose road geometry crosses the area or whose marker is in it. A road
  passing through with no vertex inside counts, and so does an area event that
  covers the whole place. Unlocated events are never counted.
- **On the map**: the area is outlined (dashed) and lightly filled in the
  theme's colour, the map frames it, events in it get a ring in the theme's
  colour and are drawn on top, and the other events are drawn faint (30%), as
  are numbered circles whose events are all outside. The selected event is
  never faint. The pin's popup says how many events are in the place on the map.
  While a place is shown, a change in the list no longer moves the camera away.
- **In the sidebar**: "Near Gachibowli" with the count (and how many of them the
  map does not draw: ended, no stated start …), the distance choices, **List
  only these events** (on demand; the counts above it are unchanged) and **Clear
  place**. Cards of events in the place say "Near Gachibowli". While the events
  are loading it says so rather than "No events". With all countries shown it
  asks to open a country first. When the list holds only the newest events, it
  says how many were checked.
- **Backend** (`app/services/place_search.py`): an OSM geocoder answer at the
  same spot as an entry of the city's place list is the same OSM place. It is
  still not listed twice, but its box is now kept on the place-list entry, so
  choosing "Gachibowli" from REI's list gets Gachibowli's area rather than a
  point.

## Verified

`features/map/placeArea.test.ts` (own area vs postcode, street and listed points;
fall back to a distance; closed outline; counts in words; point by distance;
road crossing with no vertex inside; area covering the place; the place's box;
unlocated never counted; map flags: ringed, faint, selected never faint, none
without a place). `tests/api/test_place_search.py` (the geocoder's box kept on
the listed place, asked once and remembered). Frontend: all tests, type check,
lint. Browser check on the local console (review queue, Hyderabad, 27 events):
Khairatabad, 2 km → 2 events, 5 km → 7 (1 not on the map), rings and faint
markers as described, "List only these events" 27 → 7 and back; "Gachibowli
Hyderabad" (OSM area) → "Its area", 4 events inside the outline; PIN 500032 →
2 km; phone width; Clear place removes the outline, rings and tags. No console
errors from this feature. The backend change needs the API restarted to apply
(the local API runs without reload); it is covered by its test.
