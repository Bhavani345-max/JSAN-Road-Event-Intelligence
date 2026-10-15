# 0031 — API documentation behind sign-in, per-visitor sign-in limits, roles

**Status:** accepted in code, 15 October 2026. Not deployed. The Railway
settings below are proposals awaiting the user's approval.

## Context

The production audit (docs/audit/production-audit-2026-10-15.md), rechecked
on 15 October 2026, found:

1. `/api/docs`, `/redoc` and `/api/openapi.json` answer without sign-in, on
   the API's public domain and through the console's proxy. They list every
   route and field.
2. Sign-in limits counted attempts per connection. Every request reaches the
   API from a proxy (Railway's edge, then the console's `/api` proxy, which
   adds no X-Forwarded-For), so all visitors shared one bucket. Eight wrong
   passwords from anyone locked everyone out for 15 minutes.
3. Users have a role (only `admin` exists; one user in production), but no
   route checked it.
4. The PostGIS service has a public TCP proxy: the database answers on the
   internet. It is protected by its password (scram-sha-256, SSL on).
5. The PostGIS image is `postgis/postgis:16-master`, a development tag
   (PostGIS 3.7.0dev, GEOS 3.15.0dev). The `events.geom` column is computed
   by PostGIS functions on every event write, so a newer development build
   pulled on a restart could break writes.

## Decision (code)

- **Documentation:** FastAPI's public documentation is off. `/api/docs` and
  `/api/openapi.json` are served to signed-in users only
  (`app/api/routes/api_docs.py`); `/redoc` and `/docs` are gone.
- **Sign-in limits:** failures only, counted per account (8 in 15 minutes)
  and per visitor address (30 in 15 minutes, across accounts). The address
  is the last X-Forwarded-For entry (the one the edge appends; entries a
  visitor writes come before it), else the connection's. A successful
  sign-in clears its account's failures.
- **Roles:** `viewer` reads; `reviewer` also records review decisions
  (status, severity, extensions, locations, merges, GIS choices, manual
  entries); `admin` also runs sources (`POST /api/ingestion/run`). Any
  other role reads only. All production users today are `admin`, so
  nothing changes for them.
- Tests: `backend/tests/api/test_security.py`.

## Proposed Railway settings (not done; each needs the user's approval)

| Change | Where | Effect | Risk / undo |
| --- | --- | --- | --- |
| Remove the PostGIS TCP proxy | PostGIS → Settings → Networking | The database is reachable only on Railway's private network, which the API already uses | Read-only checks from outside (as in the audits) stop working. Re-add it temporarily when needed. |
| Pin the PostGIS image to the running digest | PostGIS → Settings → Source image: `postgis/postgis@sha256:afaf08e1937d753762cfdb943c69ed46296bf50faa80c5f89494e2d0d12980de` | No new development build on restart; the binaries stay exactly as now | None to the data. Moving to a stable release is a separate, planned step (below). |
| Remove the API's public domain (optional) | API → Settings → Networking | Only the console (private network) reaches the API; docs and sign-in are no longer exposed directly | Anything calling the API's public address directly stops. Nothing in the repository does. |

Moving to a stable PostGIS needs a plan: the database's extension is at
3.7.0dev. Either wait for the stable `16-3.7` image and update the
extension, or restore a `pg_dump` into a new service on a stable tag
(about 1.1 GB). Back up first; this one is not a one-click change.
