# 0021 — Events are placed by OpenStreetMap first, Google Maps when OSM cannot

Date: 2026-10-09. Status: accepted.

## Context

After the AI reading (decision 0020) the user asked how good the plotted
points were. A check found one AI event 22 km from where it is (a same-name
church), a diversion marker 7 km off (an abbreviation), and events left off
the map because OpenStreetMap does not know names such as "Lok Bhavan". The
user asked to use Google Maps through their Serper.dev key and to iterate
with a rubric until the best way of plotting was found. They accepted
Google's terms on using Maps data.

## Decision

- **One placer for every text event** (`services/geo_resolution/placement.py`),
  used for AI-read articles (the reading's names and roles) and keyword
  articles (the headline's and summary's whole names, then roads). Official
  feeds keep their own geometry.
- **The method** is the one that scored best in
  `docs/placement-evaluation-2026-10-09.md` (132 of 147 against 104 before,
  no wrong markers): OSM first with area-qualified same-name places and
  junction-word variants; Google Maps (Serper /places) only when OSM has
  nothing or only a weak match, and only for answers inside the city that
  carry the name's own words; spots far from the article's other places
  swapped or dropped; weak matches only with support nearby; Google /maps as
  a last resort when nothing else places the event; the first-named place
  of the highest role, never a diversion route.
- **Word lists are configuration**: `services/geo_resolution/config/placement.json`
  (junction and structure words, agency names, distances, role order).
- **Provenance.** Every marker is a named place's position, recorded as
  APPROXIMATE with its reference: "OpenStreetMap node/…" or
  "Google Maps (Serper.dev) place <cid>". Nothing is computed between places.
- **Cost.** Answers are cached on disk; each name is asked once.
  `PLACE_LOOKUP_DAILY_CREDITS` (60) caps Serper credits a day;
  `PLACE_LOOKUP_GOOGLE=false` turns Google off. Without a Serper key the
  placer uses OSM only (tests run this way).
- **Dates.** A closure that began on a day and continues ("shut on August
  31 … remain shut") now has an open end instead of a one-day period. The
  full-reading prompt says so and has its own version (`full.version`), so
  only road events already read in full are read again.
- **Applying it.** `python apps/api/reprocess.py` re-places stored events;
  events a person has touched are not changed. On 9 October: 5 markers
  moved to the right place, 3 events placed that had none, 1 wrong marker
  removed, 2 closures given an open end.

## Consequences

- More events are on the map, and in the right place; a few stay unplaced
  rather than being placed wrongly.
- Google answers are cached in `apps/api/.data/google_places_cache.json`;
  deleting it means asking again.
- The answer key was also the tuning set. `tools/placement_eval/` reruns the
  rubric; add newly read events to the key to test the method on fresh data.
