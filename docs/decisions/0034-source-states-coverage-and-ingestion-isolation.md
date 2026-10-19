# 0034 — Every source's state, events from detection to the map, ingestion isolation, GDELT guard

**Status:** local only, 16 October 2026. Not committed, not deployed. Waits for
the user's review.

## Context

The user asked (16 October 2026) for a complete audit and for: all sources
visible in the dashboard with honest states, GDELT shown as disabled, the
difference between detected, validated, pending-review and map-displayed
events, one source's failure never stopping the others, bounded GDELT
requests, and more permitted official sources by country.

Audit (local and production, read-only, 16 October 12:19–12:20 UTC):

- The console asked the API for `integration_status=CONNECTED` only and
  derived "health" itself: GDELT, every source awaiting permission, blocked,
  removed or needing a key was invisible, and a source that polled well but
  found nothing looked the same as a healthy collecting one.
- `IngestionService._run` caught `ConnectorError` only. Any other exception
  (a parser or storage bug) escaped `run_due`, so the rest of that round was
  not polled, and the failure was not recorded on the source: it stayed due
  and failed first again every tick, starving the sources after it.
- Opening the console on a city by its link (`/?city=delhi`) left the map on
  the initial Hyderabad view: the map's city effect remembered the first
  render's city as "already there".
- Sources about no city (catalogue entries of other countries) were listed
  under every city.
- Locally the official feeds are connected but not scheduled
  (OFFICIAL_FEEDS_SCHEDULED_SOURCES is set only in production): their data is
  of 13–15 October. In production NYC's 3,568 rows are not merged (the
  merge runs after a successful NYC poll; NYC answered 503 on 16 October) and
  Toronto's feed answers HTTP 500 since 16 October.

## Decision

### One state per source, derived by the API (`app/services/source_status.py`)

`GET /api/sources` lists every registered source with `status`,
`status_label`, `status_reason`, `polled`, and real counts from its events:
`recent_event_count` (detected in the last 7 days), `pending_review_count`,
`validated_count`, `on_map_review_count`, `on_map_operations_count` (each
map counted on its own, decision 0035). States:

| Group | State | Means |
| --- | --- | --- |
| Polled by REI | COLLECTING | connected, switched on, last poll succeeded, road events in the last 7 days |
| | NO_RECENT_EVENTS | the same, but no road event in the last 7 days (not failing) |
| | FAILING | the last poll failed (reason: the recorded error) |
| | NOT_POLLED_YET | switched on, never polled |
| Connected, off here | NOT_SCHEDULED | connected, run by hand only on this installation |
| | DISABLED | connector built, switched off by configuration (GDELT; new integration status `DISABLED`) |
| Not connected | AWAITING_PERMISSION, BLOCKED_BY_TERMS, BLOCKED, REMOVED, NEEDS_CREDENTIALS, RESEARCHED, MANUAL_ONLY | from the registry's status and terms |

A disabled or not-connected source is never shown as healthy or offered a
"Check"; nothing is invented (no poll, no count) the database does not hold.

### Events from detection to the map (`GET /api/events/coverage`)

Per configured city: `detected` (not merged), `merged` (duplicate rows),
`rejected`, `closed`, `pending_review`, `validated`, `on_map_review` and
`on_map_operations` (exactly what the console's two views list; never added
up, decision 0035), and `hidden_review` / `hidden_operations` by the first
rule hiding each event awaiting review / validated event (no location, no
stated start, ended, reported over by the source, open-ended article older
than 30 days). `EventRepository.tally` computes both this and
the per-source counts in one pass.

### Console

All sources are fetched and grouped (polled / connected, off here / not
connected), each with its state in words, why, and its counts; a city lists
its own sources and those of its country or of none. A coverage line shows
how many events this view's map shows, then how many are detected, awaiting
review and validated, and why the rest are not on this map (decision 0035).
The map moves to the city a link opens on.

### Ingestion isolation

`_run` also catches any other exception: rolled back, logged with its
traceback, recorded on the source as `Unexpected error while reading the
source: <type>: <message>`, returned as a failed result. `run_due` guards
each source as well. A failed source waits for its interval like any other.

### GDELT (`connectors/discovery/gdelt.py`)

Still off by default. All GDELT requests in a process share a guard: 6 s
pace; identical searches answered from memory within GDELT's own
`Cache-Control: max-age` (15 minutes otherwise); after a refusal (HTTP
429/503, or its "limit requests" text) no request at all for 15 minutes,
doubling with each further refusal up to 24 hours, reset by an answer; every
error says when the next request may go. No retry loop.

### New official sources (verified, permitted, connected; run by hand until scheduled)

Research of 16 October 2026 (`docs/data-sources/europe-official-road-sources-2026-10-16.md`,
`americas-oceania-official-road-sources-2026-10-16.md`,
`asia-mea-official-road-sources-2026-10-16.md`). Each was fetched by the
research, built from its saved real response (test fixtures), and run once
locally on 16 October 2026 (one or two requests each):

| Source | Country / area | Licence | Live run 16 Oct |
| --- | --- | --- | --- |
| 11 WZDx work-zone feeds (`connectors/official/wzdx.py`): Delaware, Indiana, Kansas, Kentucky, Louisiana, Maricopa County AZ, Maryland, Minnesota, New Jersey, North Dakota, St. Charles County MO | United States (`united-states`) | CC0 1.0 in each feed (the WZDx specification requires CC0) | 3,982 events |
| Tokushima Prefecture road restrictions (`tokushima.py`) | Japan (`japan`) | CC BY, credit the Tokushima open-data portal | 211 events |
| Brussels Mobility traffic events (`brussels.py`) | Belgium (`brussels`) | CC0 1.0 | 184 events |
| Hamburg police traffic messages (`hamburg.py`) | Germany (`hamburg`) | dl-de/by-2-0, credit "Freie und Hansestadt Hamburg, Polizei Hamburg" | 259 events |

Like every official feed they are polled only when named in
OFFICIAL_FEEDS_SCHEDULED_SOURCES (decision 0028); nothing was switched on.
Commercial use is recorded "with attribution" even for CC0 (decision 0009:
no unconditional rights are claimed without a legal review).

Type mappings come from each source's own words (WZDx `vehicle_impact`;
Tokushima's restriction words; Brussels' DATEX II code; Hamburg's DATEX II
record type). Records about pavements (Tokushima) or traffic flow (Hamburg
AbnormalTraffic, Conditions, general messages) and WZDx detours (the route
traffic is sent along) are not taken. Directions are compass values only
where the source states one. Personal data in the Taiwanese and Viennese
feeds was one reason they were not connected now.

### Source geometry with GeoJSON's optional members (`services/extraction/source_event.py`)

A source geometry carrying a `bbox` member or a third (altitude) value per
position, both allowed by RFC 7946, was rejected as invalid and the event
left unlocated (80 Maryland and 17 North Dakota work zones). The shape is now
kept in longitude and latitude. No existing event was affected (checked: the
other official events without a location have no source geometry). The 97
events were re-derived as new versions.

### Counts, local database (`GET /api/events/coverage`)

| | 16 Oct 12:33 UTC (before) | 16 Oct 13:09 UTC (after) |
| --- | --- | --- |
| Events detected (not merged) | 6,961 | 11,597 |
| Awaiting review | 6,943 | 11,579 |
| Validated | 6 | 6 |
| On the map | 6,021 | 10,653 |
| Registered sources | 122 | 140 |
| Connected sources | 20 | 34 |

## Not done here

- No production change; no GDELT request; no source awaiting permission was
  contacted.
- The GDELT sources' `last_success_at` of 16 October 10:58 UTC in the local
  database came from replaying saved responses (decision 0033 evaluation),
  not from live answers; the console no longer shows it for a disabled
  source. Clearing it is a database change left for the user's approval.
  Done on 19 October 2026 at the user's request ("complete the pending
  tasks"), local database only: `last_poll_at` and `last_success_at` set to
  empty on gdelt-delhi, gdelt-kolkata, gdelt-mumbai, gdelt-pune and
  gdelt-south-africa (the five rows with the 10:58:43 replay time, nothing
  else); backup `backend/.data/backups/rei-2026-10-19-before-gdelt-replay-times.db`.
  The production rows were never polled and needed nothing.
