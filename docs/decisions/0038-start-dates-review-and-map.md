# 0038 — A missing start date: stored and reviewed, not mapped

**Status:** local only, 19 October 2026. Not committed, pushed or deployed;
no production data changed. Waits for the user's approval.

## Context

The user's brief of 19 October 2026: a missing start date must not stop a
genuine road event from being collected and stored; never invent dates, times,
geometry or status; no start from an end alone ("in place until 20 October");
"begins today" as a date-only value only where publication date, context and
time zone support it; separate storage from map eligibility, validation,
approval and publication; nothing automatically ACTIVE, APPROVED or SCHEDULED;
keep history, delete nothing.

What the check found: storage already kept every detected event, dated or not,
with its evidence, as VALIDATION_REQUIRED (every creation path), and only a
reviewer changes a status. Ingestion drops nothing for lack of a start (the
official feeds keep undated records; the start-and-end checks in the
connectors only decide which duplicate rows merge). The filter was in the
display: since 15 October (`is_shown`) an event without a stated start was
hidden from the review queue as well as from the maps, so a reviewer never saw
it.

## Decision

Four levels, each narrower than the one before (`services/lifecycle/current.py`):

| Level | Rule | Who sets it |
|---|---|---|
| Stored | every detected event, its evidence and history | ingestion |
| Listed for review | located, awaiting review (or approved anyway with no start), not known to be over: a stated start (as the map), or no start and either a stated end still ahead, or an official record its source does not report over, or a report from the last 7 days (road works 30) | `listed_for_review`, `review_listing` |
| On the map | located, a stated start, not past its end, not reported over, an article's open-ended event within 30 days of its start | `map_rule`, `is_shown` (unchanged) |
| Current and upcoming / active | on the map and an operational status (APPROVED and after), which only a reviewer gives; ACTIVE or SCHEDULED likewise | reviewer |

- No start is derived from an end. An event that states only an end is listed
  until that end, then is over: history keeps it.
- A report with no dates is listed only while recent (RECENT_REPORT_DAYS 7,
  RECENT_WORKS_REPORT_DAYS 30, the merge rule's windows), so a measure that has
  probably ended is not presented as current; after that it stays stored.
- An event approved anyway with no start (decision 0022) is back in the review
  queue (it was in no view at all); its status is unchanged.
- The API gives each event `map_eligible` and `off_map_reason` (no_location,
  no_start, ended, source_ended, open_end_lapsed). The console's maps draw only
  map-eligible events; the review list says "Not on the map: the source states
  no start date". Coverage gives `listed_review`; the review view's line says
  how many off-map events are listed below.
- The list, the per-city counts and the coverage tally use one rule per view
  (`_view_rule` in the repository: database conditions plus a test of the light
  columns, now including when the source published the event).
- Approval is unchanged: a start time is still required (unless a reviewer
  approves anyway, recorded as such).

### "Begins today", "from tomorrow"

`services/extraction/stated_period.py` reads "begins/starts/starting/
commencing/effective/comes into force/in force/from/with effect from" +
"today"/"tomorrow" as a start on the publication day or the next, as a whole
day in the city's time zone (no time), with an end if the same text states one
("from today till October 25"). Only:

- in the headline or summary, as for a bare "from <date>";
- when the publication time is the publisher's own: a result found through a
  search keeps the search engine's time ("3 days ago", GDELT's seen time)
  unless its article page stated one; the connectors now record
  `published_at_from` ("article" or "search_result"), and records without it
  that came from a search count as unknown;
- not when the words make it the day the measure ends ("lifted from today",
  "reopens from tomorrow", "eased", "withdrawn", "ends") and not for "Today's".

## Measured (local database, read-only, 19 October 2026)

| Country | Stored | Review queue before | Review queue now | On the review map |
|---|---|---|---|---|
| India | 205 | 19 | 82 | 19 |
| Canada | 1,454 | 1,055 | 1,060 | 1,055 |
| Australia | 970 | 887 | 892 | 887 |
| others | 9,018 | 7,544 | 7,544 | 7,544 |

No stored undated article's headline or summary has a "today"/"tomorrow" start,
so that rule changes no stored event; it applies to new articles (and to stored
ones only if the user runs a reprocess).

## Not done here

- No reviewer action to enter a start date from the evidence (a possible next
  step: a dated, attributed entry like "Extend end date").
- Unlocated events stay unlisted (the user's rule of 15 October).
- No reprocess of stored articles; no production change.
