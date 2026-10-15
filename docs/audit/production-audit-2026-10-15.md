# Production audit — 15 October 2026

Read-only audit of REI production on Railway after the API service was deployed
at commit `da223be`. Checked between 07:39 and 08:10 UTC.

**How production was read.** `railway status`, `railway logs` and variable
*names* (never values). Database counts came from read-only SQL: the session
was opened with `default_transaction_read_only=on` and confirmed with
`show transaction_read_only = on`. The connection went through the PostGIS
service's public TCP proxy, with credentials injected by `railway run` and not
printed. Nothing in production was written: no sign-in (that would create a
session row), no source run, no variable or setting change. `railway ssh` was
not used: it needs an SSH key added to the Railway account.

## A. Production status

| Check | Result | Evidence |
|---|---|---|
| Deployed commit | PASS | API deployment `0e8b18d7` SUCCESS 07:33 UTC from `da223be`; web `cf127ae3` from `da223be`; `origin/main` = `da223be`. |
| API health | PASS | `GET /api/health` 200 directly and through the web domain. The route runs `SELECT 1`. |
| Frontend → API | PASS | `jsan-rei.up.railway.app/api/health` returns the API's `{"status":"ok"}`; `/api/events` returns the API's 401 JSON. Both services run the same commit. A signed-in payload was not fetched (signing in writes a session row). |
| Database | PASS | Health check; read-only queries; `alembic_version` = `0007` = newest migration; startup log ran no migration. API and PostGIS use the same database (`railway`, private network). |
| Scheduled collection: news | PASS | 6 RSS feeds polled 07:35–07:36 UTC, `last_success_at` set, no errors. |
| Scheduled collection: official | FAIL | 0 of 10 official feeds polled since 13 Oct 12:55 UTC; `nyc-permitted-events`, `france-dialog-traffic-orders`, `lyon-disruptive-works` never polled. All have `active = false`. |
| Event ingestion | PASS for news, FAIL for official | News runs succeed (0 new road events today). No official records collected since 13 Oct. Google News search is not connected in production (no `SERPER_API_KEY`), as configured. |
| Map data | PASS (as designed) | The API's own view rules give `current_upcoming` = 4 events (3 current, 1 upcoming). |
| Map rendering | NOT VERIFIED | Needs a signed-in browser session. |

## B. Root causes

Confirmed:

1. **Official feeds do not run in production.** Every official source is
   registered with `active = OFFICIAL_FEEDS_SCHEDULED` (`connectors/registry.py`),
   the variable is not set on Railway, and `IngestionService.run_due` polls only
   active, connected sources. Setting it would switch on all ten at once
   (fixed: decision 0028 allows one at a time).
2. **NYC row merging (decision 0025) has not reached production data.** It runs
   after each NYC DOT poll, and NYC DOT has not been polled since the code was
   deployed. Production has 3,568 NYC rows, all `VALIDATION_REQUIRED`, none merged.
3. **The map is nearly empty because few events were ever approved.** Only
   reviewed events in an operational status with stated times are shown. 10
   events are approved: 4 are past their end, 2 state no times, 4 remain.
   5,097 events wait in validation and 13 in QC. This is the review rule working,
   not a fault.
4. **Web image cache cannot be written.** The web container runs as `node`
   but `/app` belongs to root: `EACCES: permission denied, mkdir
   '/app/.next/cache/images'` (4 times in the current deployment's log, one as
   an unhandled rejection). Fixed in `frontend/Dockerfile`.

Possible (not verified):

- The API service's GitHub auto-deploy may still be off (three pushes on 14 Oct
  did not deploy it; today's deployment was started by hand). Not readable
  through the CLI. Check after the next push.
- During a deployment the old and new containers overlap, so two schedulers can
  run for a short time. The unique keys `(source_id, external_id)` on articles
  and one event per article prevent duplicates; a collision would fail one run
  and be logged. No sign of it in the logs read.

## C. Data integrity (production, read-only)

| Measure | Count |
|---|---|
| Events stored | 5,148 |
| Merged into another event (kept, linked) | 8 |
| Validation required | 5,097 |
| QC pending | 13 |
| Approved | 10 (4 past their end, still `APPROVED`) |
| Rejected | 20 |
| Expired | 0 (no `APPROVED → EXPIRED` transition exists) |
| Map-eligible (`current_upcoming`) | 4 |
| API views | validation 5,112 · history 324 · rejected 20 |
| Merge questions | 24 pending · 3 auto-merged · 5 confirmed · 5 rejected · 28 superseded |
| Event versions | 5,608; 0 events without version history |

- **Severity:** 11 events carry an REI severity, and all 11 have a reviewer's
  `severity_assessment`. Source severity stays in `detection.source_severity`.
  No invented severity.
- **Missing data stays missing:** of the 5,097 in validation, 45 state no times,
  10 have no geometry, 20 have neither.
- **Merges** keep both events, `merged_into`, and a version naming the merge.
- **Forced approvals (decision 0022):** 4 of the 10 approved events were
  approved anyway. `EVT-4ED82DF52D0F` is on the map with an **approximate**
  location (ends 21 Oct). `EVT-B42A3E4743BC` (Mumbai) has no location and no
  dates. `EVT-2E814196CB04` is approximate with no dates. `EVT-7CFBC109F33D`
  has no start time. This conflicts with the rule "approximate or unverified
  locations must not be approved as navigation-grade". The user decides.
- **Removed and restricted sources:** The Hans India is `NOT_USABLE`, inactive,
  with no connector. Its last poll was 07:21 UTC by the previous deployment, and
  there has been none since. Siasat is `TERMS_REVIEW_REQUIRED`, inactive, with
  no poll since 14 Oct. Evidence is kept (301 + 348 articles). **One Hans India
  event and one Siasat event are still `QC_PENDING`**: approving them would
  publish content from publishers whose terms forbid this use.

## D. Security and reliability (audited, not changed)

- `/api/docs`, `/redoc` and `/api/openapi.json` are public on both domains.
- Login rate limit: 8 attempts per 15 minutes per `request.client.host`.
  Behind the web proxy every user shares the proxy's address, so failed
  attempts by anyone can lock out everyone for 15 minutes.
- Roles: `require_user` checks only for a session; the `role` field is not used.
- The PostGIS service has a public TCP proxy (internet-reachable, password-protected).
- PostGIS image `postgis/postgis:16-master` is a development tag. Python
  dependencies are version ranges, not pins.
- Feed failures: `last_error` / `last_failure_at` on the source, a log warning,
  and a retry at the next interval. No alerting.
- The in-process scheduler assumes one API replica (`app/services/scheduler.py`).
- `GET /api/events` loads every event of the filter into memory to apply the view
  rules. That is fine at about 5,000 rows, but it grows with uncapped feeds.

## E. Fixes made on 15 October (not pushed)

- `OFFICIAL_FEEDS_SCHEDULED_SOURCES` (decision 0028): `backend/app/core/config.py`,
  `backend/connectors/registry.py`, `backend/app/services/ingestion_service.py`,
  `.env.example`, `README.md`.
- NYC DOT description: "daily", not "hourly" (`backend/connectors/official/nyc.py`).
- `frontend/Dockerfile`: `.next/cache` owned by `node`. Not built locally.
- Tests: `backend/tests/api/test_official_feed_scheduling.py` (9). Backend suite:
  772 passed, 2 skipped.
