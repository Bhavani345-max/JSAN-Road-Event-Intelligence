# 0007 — A reviewer can extend an event and enter one by hand

**Status:** accepted, 5 October 2026

## Decision

- **Extend.** `POST /api/events/{id}/extend` records that an event runs longer
  than recorded: a new last day (a whole day in IST) or "until further
  notice", with the reviewer's reason, which is required. The previous end,
  the reason, who and when are kept in `detection.period_revision`; what the
  article stated stays in `detection.stated_period`; the change is a new
  version in the event's history. Extending does not change the status: it is
  not approval.
- **Manual entry.** `POST /api/events` adds an event that no connected source
  reported. It needs a title and the reviewer's basis ("seen on site on 5
  October"); type, place, dates, details and a link are optional. The entry is
  stored as evidence first, under the source "Manual entry"
  (`connectors/manual.py`), then the event is derived from it with
  `detection.method = "manual_entry"`. It starts as `VALIDATION_REQUIRED` like
  every event.
- **A manual entry is located like an article**, by a known Hyderabad place
  name that points to one spot (`GET /api/places?q=` suggests them). Its
  location can then be corrected on the map like any other event's.
- **Correct location.** `POST /api/events/{id}/location` puts an event at the
  spot a reviewer clicked on the map, with the name they give the spot and
  their reason, both required. `detection.location.method` becomes
  `reviewer_placed` and `detection.location_revision` keeps the name the event
  was located by before. This is the one case where a point is not looked up
  by name: the lookup can only be as good as the map's names, and it placed
  the Gachibowli flyover works at the locality's label on ISB Road because
  OpenStreetMap has no feature called "IIIT Junction". The point must lie in
  Greater Hyderabad.
- **Reprocessing never touches a person's work.** An event that any person
  has changed (reviewed, extended, entered) is skipped by
  `apps/api/reprocess.py`, and manual entries are never reclassified.

## Why

A closure's article states an end; closures overrun, and nobody publishes the
overrun. The DLF Gate No.1 – Gachibowli Traffic PS closure read 1 July – 28
September 2026 and was hidden as ended while a reviewer who passes it knew it
was still closed. The honest record of that is the reviewer's own statement,
attributed and dated, next to what the article said — not a silent edit and
not a guess by the system.

The same goes for events no feed or search finds. The alternative to a manual
entry is the event not being in REI at all.

## Consequences and limits

- There is no authentication yet, so every such change is attributed to
  `local-reviewer`. Real attribution needs the authentication phase.
- A manual entry is exactly as reliable as its stated basis, and has no source
  tier. The console labels it "Manual entry" and shows the basis.
- An extended end is the reviewer's knowledge on the day it was entered. The
  console says who extended it and when, and still shows the article's dates.
- Dates entered by a reviewer are whole days; times of day are not captured.
