# 0025 — One closure listed in several rows becomes one event

**Status:** accepted, 14 October 2026. Extends
[0011](0011-cross-source-merging-and-feed-absence.md).

## Context

The user reported map points holding several events. Measured on the local
database on 14 October 2026: in the review list, 3,121 of 5,099 located events
shared their marker with another event; 2,766 of them were New York City.

NYC DOT's dataset (Street Closures due to Construction Activities by Block,
i6b5-j7bu) lists a block's closure once per permit purpose: "place crane or
shovel on street", "occupancy of roadway as stipulated", "occupancy of
sidewalk as stipulated"... Each row has its own id, the block's segment id and
the work period. One block of Vanderbilt Avenue (segment 35822) had four rows
for 15 September - 15 October, eight for 26 September - 25 December, four for
15 October - 1 January. REI made an event of each row: 3,568 events for 2,277
closures.

Matching (0011) treats two records of one official source as separate events,
which is right for every other official source.

## Decision

- A source that lists one event in several rows is declared in
  `merge_service.LISTED_IN_SEVERAL_ROWS`, with what those rows share. For NYC
  DOT (`connectors/official/nyc.py`, `same_closure_key`): the same street
  segment and the same work start and end.
- `merge_service.merge_listed_rows` merges such rows as any automatic merge
  does: the rows nobody has reviewed are linked to one of them (`merged_into`),
  never deleted; the event lists the others under `contributions`, and every
  row stays as evidence. A row a reviewer has acted on is not merged
  automatically: it becomes a merge candidate for review. A pair a reviewer
  rejected stays apart.
- It runs after every ingestion run of the source and from
  `python backend/cli/match_events.py` (`--rows-only` runs only this step).
- Rows stay merged only while their periods agree: a source revision that
  changes a row's period lists it, and the rows of its source merged with it,
  on their own again; the next run merges again the rows that still share a
  period (`source_revision.py`).
- Rows of one block with different periods stay separate events: they are
  separate permits. On the map they share a marker; the list a click on it
  opens now shows each event's type, stated period and source, so events with
  the same title can be told apart.

## Not changed

- France (Bison Futé): one situation is published as several records of
  different types (planned closure, diversion, road hazards) at one point and
  period. Merging them would mean choosing one type for the situation; that is
  left for a later decision. They share a marker, listed with their types.
- News reports of one story (for example several articles about the KBR Park
  one-way system, all placed at the named place) are matched and proposed for
  review as before.

## Applied

- Local database, 14 October 2026, after a backup
  (`backend/.data/backups/rei-2026-10-14-before-nyc-row-merge.db`): 1,291 rows
  merged, none left for a reviewer; 2,277 NYC events listed. Events sharing a
  marker in the review list: 3,121 before, 1,071 after (716 of them New York:
  different periods on one block; 302 France).
- Production: not yet. After deployment, one run of the NYC source, or
  `python backend/cli/match_events.py --rows-only` in the API container,
  merges the existing rows.

Tests: `tests/api/test_listed_rows.py` (real rows of segment 35822),
`frontend/features/map/stacking.test.ts`.
