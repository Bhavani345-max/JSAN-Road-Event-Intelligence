# 0010 — Official sources' revisions are kept and followed

**Status:** accepted, 6 October 2026. Follows [0009](0009-multi-city-official-sources-and-location-classes.md).

## Context

Official feeds revise their records: TfL extends a disruption, the City of
Toronto marks a closure as now in effect. Until now a record whose id was
already held was skipped, so an event kept its first end date forever. This
had to be fixed before official feeds could run on a schedule.

## Decision

- **Evidence stays append-only.** The first version of a record stays in
  `source_artifacts`, unchanged. Each later version is a new row in
  `source_artifact_revisions` (migration 0004): revision 2, 3, … with the
  record exactly as the source sent it. Reprocessing reads the latest version.
- **Only a change of content is a revision.** Each official connector names
  the bookkeeping fields its source touches without changing anything (TfL:
  last-modified time, update time, display order; Toronto: last-updated time).
  Those are left out of the comparison. Without such a list, any change of the
  content hash counts.
- **An event in review follows the source.** It takes the new type, times,
  geometry, direction, title and description. A reviewer's extended end,
  corrected location and stated basis are kept. The change is a new event
  version by `source-update`, with what changed in plain words ("end
  2026-11-07 18:00 UTC → 2026-11-20 18:00 UTC"), and the event shows it.
- **A decided event is flagged, not changed.** An approved, rejected,
  cancelled or expired event keeps what the reviewer decided. The revision is
  recorded as `pending_source_revision`, the console shows it in amber, and a
  new version says it was not applied.
- A revision that changes nothing an event shows is stored as evidence and
  adds no event version.
- News is unchanged: an edited article is not a revision; the first version
  stands.

## Still not handled

- A record that disappears from a feed (TfL removes cleared disruptions) is
  not treated as an end. With a 30-record test limit, disappearing is also
  ambiguous. This needs a decision before scheduling: whether absence from
  the full feed ends an event, or only flags it.
