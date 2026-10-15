# Railway changes planned on 15 October 2026

This is the plan; what was applied, and when, is recorded in the stage
reports. Each change waits for the user's approval. Order matters: A, B, C, D,
then E and F when decided.

**Recovery point (done, verified).** At 10:54 UTC, a full read-only
`pg_dump` was taken of the production database:
`backend/.data/backups/prod-railway-2026-10-15.dump`. It is 10,221,021 bytes,
SHA-256 `7c21b0f9ece79aba2ba24a955d33015d606e76768d571d822e581c1d2a93bd51`,
custom format, git-ignored. It was restored into a throwaway PostGIS 16 and
compared with production:

- Exact equal counts: events 5,148; source_artifacts 8,598;
  event_versions 5,608; sources 99; revisions 56; merge candidates 65;
  users 1.
- Same newest event and newest article; `events.geom` filled for 5,099
  events.
- The only restore messages were about PostGIS's own empty `topology`
  tables (the 3.4 test image's version differs from production's).

To restore: `pg_restore -d <new database> prod-railway-2026-10-15.dump`
(PostgreSQL 16 client).

Before B, also take a Railway backup: PostGIS service → Backups → Create backup.

## A. Deploy the security fixes (branch `security-fixes-2026-10-15`, commit `fdde608`)

- **Action:** merge the branch into `main` (fast-forward) and push. Railway
  deploys the API and web automatically.
- **Impact:** `/api/docs` and `/api/openapi.json` need a sign-in, and
  `/redoc` and `/docs` disappear. Sign-in limits become per account (8) and
  per visitor (30) in 15 minutes. Roles are enforced; the only production
  user is an admin, so no change for it. No database change, no new
  variables.
- **Verify:**
  - Both deployments SUCCESS and the healthcheck passes.
  - Without a session, `https://jsan-rei.up.railway.app/api/docs` gives 401
    and `/redoc` 404.
  - Signing in through the website works.
  - The log shows "Application startup complete" and no errors.
- **Rollback:** Railway → each service → Deployments → `42c9d5f` → Redeploy
  (both services). Or revert the merge and push.

## B. Pin the PostGIS image to the running digest

- **Setting:** PostGIS service → Settings → Source → Image:
  `postgis/postgis@sha256:afaf08e1937d753762cfdb943c69ed46296bf50faa80c5f89494e2d0d12980de`
  (now `postgis/postgis:16-master`).
- **Verified:**
  - It is the digest Railway recorded for the running deployment `8539661b`.
  - The full 64-character OCI index is still served by Docker Hub (HTTP 200),
    and the `16-master` tag points to it today.
  - Its amd64 image declares `PG_VERSION=16.15-1.pgdg13+2` and
    `POSTGIS_GIT_HASH=b8c7b014…`. The running server reports PostgreSQL
    16.15 (Debian 16.15-1.pgdg13+2) and PostGIS 3.6.0rc2-620-gb8c7b0142
    (3.7.0dev). The same build: no software changes.
- **Impact:**
  - Railway redeploys the PostGIS service, which restarts the database.
    Expect 10–60 seconds without a database.
  - During that time the API answers health and data requests with errors,
    and a poll may fail (it is retried at the next interval).
  - The API reconnects by itself (`pool_pre_ping`).
  - Do it at a quiet time.
- **Verify:**
  - The PostGIS deployment is SUCCESS and its `imageDigest` is `sha256:afaf08e1…80de`.
  - The database reports the same versions as above (read-only query through
    the TCP proxy, before C).
  - API `/api/health` gives 200 and the next news poll succeeds in the logs.
- **Rollback:**
  - Set the image back to `postgis/postgis:16-master`; today that is the same
    digest.
  - If the volume were ever damaged, restore the Railway backup or the dump
    above into a new PostGIS service.
- **Note:** pinning stops drift. An untagged development digest could
  someday disappear from Docker Hub. Copying it to a registry REI controls
  (for example GHCR) protects against that, and needs the user's approval.
  Moving to a stable PostGIS release is a separate, planned migration.

## C. Remove the database's public TCP proxy

- **Setting:** PostGIS service → Settings → Networking → Public Networking →
  TCP Proxy → delete.
- **Verified it would not interrupt production:**
  - The API's `DATABASE_URL` host is PostGIS's private domain
    (`*.railway.internal`, port 5432; hashes compared, values not printed).
  - The only live database connections are 3 from Railway's private network
    (`fd12:…`), opened right after the API's 10:36 deployment.
  - Neither the API's nor the web's variables point to the proxy.
  - The web service never connects to the database.
- **Impact:** the database is reachable only inside Railway's private
  network. Outside access stops, including this audit's read-only checks and
  `pg_dump` from this machine. Use a Railway backup, or re-enable the proxy
  temporarily for such work.
- **Verify:**
  - `railway variable list -s PostGIS` no longer has `RAILWAY_TCP_PROXY_DOMAIN`.
  - A connection from outside fails.
  - API `/api/health` gives 200 and polls keep succeeding.
- **Rollback:** add the TCP proxy again in the same panel. Railway may assign
  a new port.

## D. Feed activation (when approved)

- **Setting:** API service (`JSAN-Road-Event-Intelligence`) → Variables →
  add the line below. `OFFICIAL_FEEDS_SCHEDULED` stays unset.

```
OFFICIAL_FEEDS_SCHEDULED_SOURCES=tfl-road-disruptions,nyc-street-closures,toronto-road-restrictions,drivebc-events,ottawa-traffic-events,edmonton-traffic-disruptions,winnipeg-lane-closures,calgary-construction-detours,france-bison-fute-road-events,france-dialog-traffic-orders,lyon-disruptive-works,main-roads-wa-webeoc,gold-coast-temporary-road-closures,wodonga-roadworks
```

- **Validated against the code** (`connectors/registry.py`, decision 0028):
  - All 14 ids are official feeds, with no duplicates.
  - With this value the scheduler would poll exactly these 14 plus the 6 news
    feeds already polled.
  - Roads ACT, Finland, The Hans India, Siasat, the switched-off unlocated
    feeds and Google search stay off.
  - None needs a key.
  - Each is recorded as `PERMITS_TESTING` / `PERMITTED_WITH_ATTRIBUTION`.
  - New events are created `VALIDATION_REQUIRED` by every creation path;
    nothing in collection approves.
- **Impact:**
  - The API restarts (zero-downtime redeploy, about 1–2 minutes).
  - Within a minute every feed is due once: the first round runs one after
    another, for a few minutes.
  - Then: TfL every 15 minutes; Toronto, DriveBC, Ottawa and WA every 30;
    Bison Futé every 60; Edmonton and DiaLog every 6 hours; Winnipeg,
    Calgary, Lyon, Gold Coast and Wodonga every 12 hours; NYC daily. About
    330 polls a day.
  - About 2,200 new events go to review, and about 1,400 duplicate NYC and
    Bison Futé rows are merged.
  - About 30 MB more data (the volume uses 1.09 GB of 50 GB).
- **Verify:**
  - The deployment is SUCCESS.
  - Each feed's first run is in the log (`services.ingestion.pipeline: <id>: fetched=…`).
  - `sources.last_success_at` is set for the 14.
  - New events are all `VALIDATION_REQUIRED`.
  - The console's review queue shows Canada and Australia.
- **Rollback:** delete the variable. The feeds stop after the restart, and
  stored events and evidence stay.

## E. The API's public address (keep for now; proposed removal plan)

What uses it, from the API's access logs of every retained deployment
(13–15 October):

- Railway's healthchecks and this audit's checks.
- On 13 October (deployment `8aca5d01`), one sign-in and 16
  `POST /api/ingestion/run` calls, all 200. That matches the official feeds'
  last production run (12:45–12:55 UTC), most likely the user's own data
  load.
- The website reaches the API privately (`API_BASE_URL` is
  `http://*.railway.internal:8000`), never through this address.

Plan:

1. The user confirms nothing else uses
   `https://jsan-road-event-intelligence-production.up.railway.app`, and
   moves any script to `https://jsan-rei.up.railway.app/api/…` (same
   endpoints, same sign-in, through the website).
2. API service → Settings → Networking → remove the public domain.
3. **Verify:**
   - The website signs in and loads events.
   - `https://jsan-rei.up.railway.app/api/health` gives 200.
   - The old address answers Railway's "application not found".
   - The next API deployment's healthcheck still passes. This confirms the
     healthcheck does not need the public address; if it fails, add the
     domain back.
4. **Rollback:** generate the domain again in the same panel.

## F. External requests

The drafts for Western Cape, SANRAL and Montréal are in
docs/data-sources/permissions-and-activation-2026-10-15.md. None is sent.
