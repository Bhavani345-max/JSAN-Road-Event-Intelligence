# 0028 — Official feeds can be scheduled one at a time

**Status:** accepted in code, 15 October 2026. Nothing changes in production
until the user sets the variable on Railway.

## Context

The production audit of 15 October 2026
([production-audit-2026-10-15.md](../audit/production-audit-2026-10-15.md))
read the production database read-only. No official feed had been polled
there since 13 October 2026 12:55 UTC (the database import), and the three
feeds connected on 14 October (decision 0027) had never been polled. The
cause is configuration, not a fault: official feeds are registered with
`active = OFFICIAL_FEEDS_SCHEDULED`, the variable is not set on Railway, and
the scheduler (`IngestionService.run_due`) polls only active, connected
sources.

The only switch was all-or-nothing. Setting `OFFICIAL_FEEDS_SCHEDULED=true`
would start all ten official feeds at once, at intervals from 15 minutes (TfL)
to 24 hours (NYC DOT), five of them uncapped (NYC DOT alone lists about 3,600
rows), and including Finland's Digitraffic, whose robots.txt question is still
open with the user. The user's brief of 15 October says not to enable all
official feeds automatically.

## Decision

- New setting `OFFICIAL_FEEDS_SCHEDULED_SOURCES`: a comma-separated list of
  official source ids. A listed feed is registered as scheduled (active, with
  its "Polled every …" description); the others stay run-by-hand.
  `OFFICIAL_FEEDS_SCHEDULED=true` still schedules all of them.
- Names that are not official feeds (news feeds, restricted or removed
  sources, typos) are ignored and logged as a warning at startup. The setting
  can never connect Siasat or The Hans India: they have no connector.
- Default empty: production behaves exactly as before until the user sets it.
- `connectors/registry.py` exposes `OFFICIAL_SOURCE_IDS`, the names the
  setting accepts.
- NYC DOT's description said "polling is hourly when enabled"; its interval is
  1,440 minutes. The text now says daily.

## Consequences

- Turning a feed on is one Railway variable and a restart; turning it off is
  removing its id. The source row's `active` flag follows the registry at
  every startup (`sync_registry`), as before.
- NYC's row merging (decision 0025) runs after each NYC DOT poll, so naming
  `nyc-street-closures` also applies the merge to production's 3,568 unmerged
  rows at its first run.
- Tests: `backend/tests/api/test_official_feed_scheduling.py` (registry
  choices, settings parsing, the scheduler polling only the chosen feed, the
  polling interval respected, a removed source never polled, unknown names
  reported).
