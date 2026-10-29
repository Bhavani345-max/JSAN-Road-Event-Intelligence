# 0048 — The API's out-of-memory restarts: 3.5 million faulty pairs, and limits

**Status:** 29 October 2026. The production data change was made that day
with the user's approval. The code is local and tested, for the user to push.
No migration.

## Context

From 27 October the production API restarted about once a day. Railway's
memory graph and the request logs showed the same thing at each crash (28 Oct
07:09 and 15:42 UTC, 29 Oct 07:18 UTC):

- Someone opened the review queue for the Netherlands (once also the United
  Kingdom). The console loads a list 500 events at a time.
- One of those pages did not answer. The website gave up after 30 seconds,
  but the API kept working on it.
- The API's memory rose from about 1 GB to 20–21 GB within 4–5 minutes.
  Railway stopped it at the 24 GB limit and started it again; no error was
  logged.

The cause was in the data. Production held **3,513,864 pending
possible-duplicate pairs** ("merge candidates"). 3,513,360 of them were made in
one hour, on 22 October 2026 10:00–11:00 UTC, by the matching fault that
f78ec91 fixed: every NDW record gave the same link (https://opendata.ndw.nu/),
and the link was taken as "the same article". As a result:

- 252 NDW live-feed situations (`nl-ndw-actueel-beeld`) were each paired with
  about 14,000 NDW planned roadworks (`nl-ndw-planningsfeed-wegwerkzaamheden`);
- the 14,085 roadworks were each paired with those 252;
- 302 more pairs were between live-feed situations.

Every pair was classified SAME, with the reasons "the same article (identical
headline or link)" and "the sources disagree: merged only by a reviewer".

A list page loads the pending pairs of its events and the other event of every
pair, in full. A review-queue page holding some of those 252 situations
therefore loaded hundreds of thousands of rows. Only 202 pending pairs had
nothing to do with the fault. No event had more than 14 rows merged into it, so
merged rows were not the problem.

## Decision

### 1. Production data: the faulty pairs are superseded, not deleted

The user chose this (29 October 2026). The pairs chosen were:

- status PENDING;
- made 22 October 2026, 10:00–11:00 UTC;
- with both events from NDW feeds;
- with the reason "the same article (identical headline or link)".

That is **3,513,662** pairs. They were set to `SUPERSEDED` with:

- `decided_by` "REI maintenance (29 Oct 2026 clean-up)";
- `decision_reason` "Made by the matching fault of 22 October 2026: every NDW
  record gave the same NDW link, which was taken as the same article (fixed in
  f78ec91). Not a reviewer's decision.";
- `decided_at` the time of the change.

The update ran in batches of 50,000. No event, evidence or pair was deleted.
The 202 other pending pairs were not touched.

Before the change, the ids of the chosen pairs were saved on the developer's
PC: `backend/.data/backups/prod-merge-candidates-superseded-2026-10-29.txt.gz`
(one id per line, not in Git). To undo it, set `status = 'PENDING'` and
`decided_at`, `decided_by` and `decision_reason` to NULL for those ids.

A superseded pair is not proposed again for the same two events. A reviewer can
still merge any of those events by hand.

The script used: session scratchpad `prodlogs/prod_supersede_bad_pairs.py`.
It has a dry-run mode, and it refuses to change anything when the count is
outside the expected range.

### 2. Event lists load a limited number of pairs per event

`to_event_outs` loads at most `LISTED_MATCHES_PER_EVENT` (10) pending pairs per
event as either event of a pair: the earliest recorded, chosen by the database
(`row_number()` per event). An event with more is logged as a warning, naming
it.

A reviewer is asked about a few possible matches. A future fault that pairs one
event with thousands now makes the page incomplete, but no longer able to run
the API out of memory.

### 3. Matching refuses to pair one event with more than 100

In `find_candidates`, before recording anything for an event of the run, REI
counts how many open events it may be the same as. If that is more than
`MAX_MATCHES_PER_EVENT` (100), it records **no** pair for that event, logs a
warning naming the event and its source, and lists it in `MatchRun.too_many`.
One real event is not reported a hundred times; that many matches means a
match rule has gone wrong.

At 100 or fewer, matching works exactly as before. The checks for which pairs
are compared at all now live in one helper, `comparable`, used by both the count
and the recording.

## Tests

`backend/tests/api/test_match_limits.py` (4 tests):

- a list page loads 10 of an event's 15 pairs and logs the event;
- an event with 3 pairs lists all 3 with no warning;
- an event that may match 101 open events gets no pair and is logged;
- at exactly 100 the event is matched as before.

Each safeguard was switched off in turn (mutation check), and its test then
failed. The full backend suite passes.
