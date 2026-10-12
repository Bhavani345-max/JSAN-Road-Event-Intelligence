# 0019 — REI severity is set by a reviewer

Date: 2026-10-08. Status: accepted.

## Context

Every event has had an empty REI severity since the rule of 2 October that
REI never invents severity. The console's Severity filter therefore found
nothing. Official feeds (London, Toronto) carry their own severity words,
kept verbatim as `detection.source_severity`; the Indian sources carry none.
The user asked for REI severity to become a human-reviewed field assigned
during validation, kept separate from the source's words, never derived from
text, never mapped from the source's severity, and never filled in for the
existing events.

## Decision

- **The field.** The existing `events.severity` column (nullable, 16 chars)
  and the `ReiEvent.severity` enum (LOW, MEDIUM, HIGH, CRITICAL, or null)
  are reused. No migration. Meaning: LOW little or limited disruption; MEDIUM
  noticeable but manageable; HIGH significant; CRITICAL major, needing
  urgent attention.
- **Who sets it.** A reviewer, either with a review decision
  (`POST /api/events/{id}/status` now takes an optional `severity`) or on its
  own (`POST /api/events/{id}/severity` with `severity` and an optional
  `reason`). Not allowed on an event that is rejected, cancelled, superseded
  or expired. Never required.
- **Audit.** The existing mechanism: every change is a new event version
  with the reviewer and reason, and `detection.severity_assessment` records
  the latest severity, who set it, when, why and the version it created (the
  same shape as `qc_approval`). Reprocessing keeps it; a reviewer's version
  already stops reprocessing from touching the event.
- **Separate from the source.** `detection.source_severity` is never written
  by this change. The console shows "REI severity" and "Severity as the
  source states it" as two fields.
- **Filter.** The console's Severity filter matches `event.severity` only;
  the API's event list gained the same `severity` parameter. The source's
  words never match.
- **Console.** The review panel has an "REI severity" radio group (Low,
  Medium, High, Critical) with nothing preselected until a reviewer has
  chosen; "Save severity" records it alone, and a choice not yet saved goes
  with the next decision (Confirm road event, Approve, …).
- **Not done, on purpose.** No mapping from London's Minimal/Moderate/
  Serious/Severe or Toronto's Low/Medium/High; no keyword rule; the 270
  existing events stay unset.

## Result on 8 October 2026

Before and after: 270 events, severity null on all 270, 600 versions, source
severities on 165 events unchanged. Tests: 665 Python (8 new in
`apps/api/tests/test_severity.py`), 86 console (5 new), type-check and lint
clean.
