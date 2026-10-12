# 0006 — Events are located by the places they name, dated by the dates they state

**Status:** accepted, 5 October 2026. Supersedes the "times and geometry stay
empty" part of [0005](0005-real-source-data-only.md) and the test that kept
"for 60 days from September 26" unread.

## Decision

- **Location by named place.** An event is placed on the map when its
  article's headline or summary names a known Hyderabad place. The position is
  that of the OpenStreetMap feature of that name, from a gazetteer file built
  by `services/geo_resolution/build_gazetteer.py` (4,788 junctions, flyovers,
  landmarks, short roads and localities; © OpenStreetMap contributors, ODbL).
  `detection.location` records the place, the words as written, where they
  were found and the OSM feature. It is the location of the named place, not
  the surveyed extent of a closure, and the console says "approximate".
- **A name must point to one spot.** Long roads (NH-65, ORR, Necklace Road)
  and names shared by distant places (Indira Nagar, Lingampally) are left out
  of the gazetteer. A place named only in the article body does not locate the
  event. Such events stay "Not located" and are not drawn.
- **Dates only from explicit wording.** `start_time` / `end_time` are read
  from wording such as "for 60 days from September 26" or "from July 1 to July
  15", as whole days in IST, and the words are kept in
  `detection.stated_period`. Weekdays, "three months", "this weekend" and
  times of day are not read.
- **Attribution as the article gives it.** `detection.attributed_to` lists
  the authority the article says announced the measure. It is a second-hand
  report, shown as such; it is not confirmation.
- **Stricter detection.** An article becomes an event only if a clear signal
  matched (a rule of weight 3: diversion, restriction, closure, waterlogging,
  works on a road or flyover, …) *and* it names a road or a known Hyderabad
  place. General traffic words no longer add up to an event. Articles that
  fail stay stored as evidence.
- **Rule changes are applied to stored evidence** with
  `python apps/api/reprocess.py`. Events still awaiting validation are
  re-derived (each change is a new version); ones the rules no longer support
  are set to `REJECTED`, not deleted. A reviewer's decision is never touched.
- **One article can be brought in by its address** with
  `python apps/api/backfill.py <source_id> <url>`, for long-running measures
  announced before polling began. It is read from the page's schema.org
  NewsArticle data, stored as evidence, and goes through the same detection.

## Why

The console was to show current road events across Hyderabad on the map. With
no times and no geometry it could show neither, and keyword matches such as a
travel piece mentioning "traffic jams" appeared as events.

Looking a stated name up on a map and doing calendar arithmetic on a stated
period add nothing the article does not say, as long as where each value came
from is kept and shown. Estimating a closure's extent, or inferring dates from
vague wording, would add something, and is still not done.

## Consequences and limits

- Every event still starts as `VALIDATION_REQUIRED`. Severity, direction and
  confidence are still empty.
- A stated end date is the article's. A closure that overruns keeps its
  stated end until another article says otherwise: the DLF Gate No.1 –
  Gachibowli Traffic PS closure reads 1 July – 28 September 2026.
- News feeds remain the only connected sources (tier 4). No police or
  authority publishes these notices in machine-readable form.
- The console leaves out rejected events, ones whose stated end has passed,
  and undated reports older than 7 days (30 for road works). Since 5 October
  2026 they are not reachable through the date filter either; the API still
  returns them.
- Publisher terms of use are still unreviewed, for feeds and article pages alike.
