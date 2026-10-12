# 0011 — Cross-source merging, and records that disappear from official feeds

**Status:** accepted, 6 October 2026. Follows [0010](0010-official-source-revisions.md).

## Official records that disappear

The user's decision: absence from an official feed is not proof that the
event has ended.

- Each official refresh records every id the feed listed, before the run's
  30-record limit is applied. For each open event of that source, REI notes
  whether its record was listed (`detection.observation`: last seen, missing
  since, refreshes missed).
- A missing record changes nothing about the event: no status, no end, no
  version.
- After `ABSENCE_REVIEW_AFTER` (3) refreshes in a row without it, the event
  is flagged for review, once, with a version saying it is not taken as ended.
  If the record comes back, the flag is lifted, with a version.
- A source that explicitly reports a record cleared (TfL: "Recently
  Cleared", "Cleared", "Cancelled", "Removed"; Toronto: `expired`) is a real
  source change. It is processed as a revision: an event in review records
  `source_reports_ended`, and the console stops showing it as current. A
  decided event is flagged, not changed.

## Cross-source merging

```
several reports -> pairwise matching -> clearly same / possible / different
  clearly same, nothing conflicting, nobody reviewed, same standing -> merged now
  anything else that may be the same                                -> candidate for review
```

**Matching** (`services/merging/matcher.py`) is rules, not scores. Every
reason is a stated fact a reviewer can check: the same article (an identical
headline or link), shared named places or roads, positions within 300 m, the
same stated period or start, the same type, and similar headlines (share of
words).

It says **different** for:
- different types;
- stated periods that do not overlap;
- reports more than two weeks apart with no periods;
- two different named junctions;
- precise positions more than 2 km apart;
- different cities;
- two records of one official source.

**Conflicts** are values both events state that differ: start, end,
direction, position, type, official status. They are kept, never resolved by
the matcher.

**Automatic merges** need a SAME match with no conflicts, neither event
touched by a reviewer, and the same standing. An official source and a news
report are never merged automatically.

**Merging links; it never deletes or rewrites.** The merged event keeps its
row, evidence and history, and is marked `merged_into` the canonical event.
It is no longer listed alone, but stays reachable by its id and with
`include_merged=true`. The canonical event:

- lists it in `detection.contributions` (source, evidence, link, publication
  time, how and by whom it was merged, which fields it supplied);
- records which event each field came from in `detection.provenance`;
- takes a field only where it has none;
- keeps both values in `detection.merge_conflicts` where the two differ, and
  sets `merge_review_required`.

The canonical event is the one from the most authoritative source; among
equals, the one furthest through review, then the better located, then the
first reported. So an official event is canonical over a news report, and its
geometry is never replaced by a news report's.

**Review.** Candidates are `PENDING` until a reviewer confirms (merge) or
rejects (they stay apart and the pair is never proposed again). The console
shows them on both events with the reasons and conflicts; the API is
`/api/merge-candidates`. A source revision never overwrites a field another
source contributed.

**When.** After every ingestion run, the new events are compared with the
city's open events. `python apps/api/match_events.py` compares everything.

## Consequences and limits

- Merges are not undone yet. A wrong confirmation needs a reviewer action that
  does not exist.
- Events reviewed before 6 October 2026 carry fewer named places. One KBR
  Park report (The Hans India) names KBR Park only as "KBR Park flyover" and
  is not matched.
- Matching uses every place an article names, including places in its body.
  This widens possible matches (for review only) and makes the listed reasons
  long.
- Pairwise comparison within a city is fine at this volume (2,152 pairs) but
  needs indexing by place or area as volumes grow.
