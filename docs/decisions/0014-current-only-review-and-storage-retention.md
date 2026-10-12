# 0014 — Ask only about current events; keep less text

Date: 2026-10-07. Status: accepted; amended on 2026-10-08 by [0018](0018-no-length-filter-no-invented-expiry-history-visible.md): official records with no stated end stay current, and hidden events are reachable with "Show history".

## Context

The user asked why the console keeps asking whether one event is the same as
another, and asked to keep only latest, live and upcoming events, so that the
data is easy to filter, storage is saved and API use costs less.

Measured on 7 October 2026 (rei.db, 8.9 MB):

- 22 pending "same event?" candidates. Many involved events that were over
  (September's Ganesh immersion, Khairatabad Bada Ganesh, a mid-September
  waterlogging advisory, the IIIT Junction closure that ended 28 September).
  Eleven were pairs among six reports of one story (the KBR Park one-way
  decision), asked pair by pair.
- 88% of the database (4.7 MB) was the full text of 1,542 articles that are
  not road events at all. Events, their versions and the road articles took
  about 0.8 MB.
- Serper cost is per search (12 searches a poll), not per stored event.

## Decision

- **Only current events are matched and asked about.** "Current" is the
  console's rule (upcoming, ongoing, or reported within 7 days — 30 for road
  works — when no times are stated), now also in the API
  (`services/lifecycle/current.py`). An event that is over is not compared;
  a pending candidate involving one stays recorded (it comes back if the
  event is extended) but is not shown.
- **One decision per story.** When an event has several candidates, the
  console offers "All N are the same: merge all"
  (`POST /merge-candidates/confirm-all`). The candidates must share that
  event. Each merge is recorded as a single confirmation is.
- **The text of old articles that are not road events is removed** after
  `UNRELATED_ARTICLE_TEXT_DAYS` (default 14), automatically after each
  scheduled poll, or by `apps/api/retention.py`. A stub stays (id, link,
  headline, publication time, hash, classification) so the item is
  recognised and not stored again; the pipeline never compares article text
  for that. Reprocessing skips stubs. Road articles, structured records,
  manual entries, articles an event was made from, events and their history
  are never touched.

## Not done, and why

- **Events that are over are not deleted.** They take little space (about
  0.5 MB with their history), deleting them would lose the audit trail, and
  the console already hides them. A reviewer can still extend one (as with
  the DLF closure).
- **Article text is kept 14 days, not less**, so a rule change can still be
  re-applied to recent articles with `reprocess.py`.
- **Serper frequency is unchanged.** Fewer stored events do not lower its
  cost; fewer searches do, at the price of later or missed reports. That is
  the user's choice.

## Result on 7 October 2026

Questions asked: 22 → 12, of which 11 are one story (one click). Text of
164 articles removed (0.4 MB, all that was older than 14 days); file
8.9 → 8.3 MB after VACUUM. Growth is about 1 MB a day of unrelated text, so
the file now stays near two weeks' worth. Backup:
`apps/api/.data/backups/rei-2026-10-07-before-retention.db`.
