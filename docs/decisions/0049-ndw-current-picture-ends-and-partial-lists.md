# 0049 — NDW's current picture ends what it stops listing; lists load the newest 1,000

**Status:** 29 October 2026. Code local, tested, for the user to push. No
migration and no Railway setting. After the push, the first run of the NDW
current-picture feed changes production data, as described under "First run".

## Context

After decision 0048 the API no longer crashed, but the user saw "Netherlands
points are not coming". The Netherlands review queue had about 34,000 events.

- The console loaded every one of them before showing anything. In desktop
  Chrome, with 24,785 events, the list and map stayed empty for 60 seconds.
  Then 24,785 cards, about 720,000 page elements, made the page sluggish. On a
  phone it may never get there.
- Most of those events were NDW current-picture situations: vehicle
  obstructions, bridge openings, accidents. NDW rebuilds that file every minute
  with only what is in force now and never sends an "ended" record: it simply
  stops listing a situation. REI's rule (decision 0011) never took absence as
  an end, so every situation NDW ever listed stayed "Ongoing · Until further
  notice" and awaiting review, about 7,000 more a day.
- In the normal Operations view the Netherlands shows no points by design: it
  shows validated events, and none there are validated yet.

The user decided both (29 October 2026, asked directly):

- treat "no longer in NDW's current picture" as the source reporting it over;
- load the newest 1,000 of a list first, with "Show 1,000 more".

## Decision

### 1. A source that lists only what is in force reports over what it stops listing

A connector can declare `lists_only_what_is_in_force`. Only
`NdwCurrentSituationsConnector` does. NDW's planned feed also lists future works,
so dropping out of it may mean a cancellation; it is not covered.

For such a source, `record_observation` already counts the refreshes in a row
without a record (decision 0011). Once an event has been missing for
`ABSENCE_REVIEW_AFTER` (3) refreshes, REI does the following, provided the
event is still in review:

- sets `detection.source_reports_ended`, so the event is reported over by its
  source and moves from the review queue and the map to history;
- records `observation.ended_by_absence`;
- writes one version: "Not in the source's current picture for N refreshes
  since <first missed refresh> UTC. The source lists only what is in force, so
  it is taken as over (decision 0049)."

What does not change:

- No end time is made up. The event keeps the start and end its source stated.
- Nothing is deleted.
- Waiting for 3 missed refreshes, rather than 1, keeps a single faulty or
  partial file from ending anything.
- A refresh that lists nothing ends nothing.
- If the source lists the record again, it is current again, with a version
  saying so. Only an end REI took this way is lifted, never one the source
  stated.
- An event a reviewer has decided on (approved and so on) is not changed. It
  is flagged for review as before, the same rule as for source revisions.

All other official sources work exactly as before: absence is counted and
flagged, never taken as an end.

### 2. A list loads its newest 1,000, with "Show 1,000 more"

`listEvents(view, city, limit)` loads pages until `limit` (`LIST_STEP`, 1,000)
or the end of the list, and returns the list's `total`. "Show 1,000 more" asks
for 1,000 more without clearing the screen. Another view or place starts again
at 1,000.

A list not loaded whole shows "Showing the newest 1,000 of 34,012 events, on
the list and the map."

- **Tiles:** with no filters they are the API's per-place counts, with the
  same rules as the list, so they stay exact. With filters, they count the
  loaded events, and the note says "The filters look through these 1,000."
- **Search:** it now shows the API's matching events themselves, at most
  1,000, newest first. Before, it marked which loaded events matched, so an
  older event was never found in a partial list.

### 3. A text search reads one batch at a time

For a console view, `EventRepository.list` with words now chooses the view's
events from a light scan, the same way as a list without words
(`_list_light`). It then reads them in full 500 at a time to match the words,
and lets each batch go before the next. Before, a search read every event of
the place in full, whatever its list, and only then applied the view.

Checked on a copy of the local data, 8 searches across views and places
(Netherlands, Hyderabad, India): the same events in the same order. Memory and
time:

| Search | Before | Now |
|---|---|---|
| Netherlands review queue | 970 MB | 28–173 MB |
| Netherlands history | 21 s | 3.5 s |
| Netherlands operations view | 18 s | 0.1 s |

A search of the Netherlands review queue itself still takes about 18 seconds
locally. It gets shorter as rule 1 empties that queue.

## First run after the push

The first NDW current-picture run, within 30 minutes of the deploy, takes as
over every situation in review that has been missing for 3 or more refreshes:
nearly all of the ~34,000. That is one version each, written in that run. The
Netherlands review queue should then hold what is in force now (a few hundred
situations) plus NDW's planned roadworks.

## Tests

- `backend/tests/unit/test_official_observation.py`, 6 new tests:
  - an unlisted event is taken as over after the threshold, not before, with
    one version and no changed end; it moves from the review queue to history;
  - an empty refresh ends nothing;
  - a record listed again is current again;
  - a decided event is flagged, not ended;
  - other official sources never end an event by absence;
  - only the NDW current picture declares the flag.
- Mutation check: the rule, the empty-refresh guard, the reviewed-event guard
  and "listed again" were each broken in turn, and a test failed each time.
- `frontend` tests:
  - the repository stops at the limit and asks only for what is still wanted
    (500 + 500 + 200 for 1,200);
  - `partialListNote` wording.
- Full suites:
  - backend: 1,662 passed, 2 skipped;
  - web: 244 tests, plus lint and type check.
- Browser checks with Playwright, against a copy of the local data
  (Netherlands review queue, 24,776 events):

  | | Desktop Chrome | Pixel 7 |
  |---|---|---|
  | List and map shown after | 3 s (was 60 s) | 2 s |
  | Page elements | 29,000 (was 720,000) | 29,000 |
  | Browser memory | 57 MB (was 386 MB) | 33 MB |

  - The tiles stayed exact: 24,776.
  - "Show 1,000 more" added 1,000 in 5 seconds.
  - A search for "MOS01" found all 698 matching events, where the loaded
    1,000 held 91.
