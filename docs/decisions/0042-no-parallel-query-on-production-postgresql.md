# 0042 — No parallel query on production's PostgreSQL

**Status:** 27 October 2026. Code local, tested, for the user to push. No database
migration and no Railway setting.

## Context

The user's console screenshots of production (27 October 2026):

- NDW planned works: "Active: failing", last success 26 October 06:46 (IST),
  "Unexpected error while reading the source: OperationalError: (psycopg.errors.DiskFull)
  could not resize shared memory segment "/PostgreSQL.1927317290" to 16777216 bytes:
  No space left on device [SQL: SELECT events.event_id, …".
- NDW current situations: "Active: failing", last success 26 October 21:14; 13,390 events
  awaiting review. Basque Country traffic incidences: "Active: failing", no successful
  poll yet. Under both, "The REI API is not reachable … double-click start-rei.cmd".

What that means:

- The error is not the database disk. PostgreSQL's parallel workers share their work
  (a parallel hash join's table) through dynamic shared memory in `/dev/shm`, which a
  container keeps small. The query is `record_observation`'s (every open event of the
  source with its record id): about 15,000 events for NDW's planned feed and 13,000 for
  its current picture, joined with every source's records. On production's data the
  planner chose a parallel plan, and `/dev/shm` could not hold it. The largest sources
  (the Netherlands') failed first; others can follow as the tables grow.
- "The REI API is not reachable" under a source is what the console said when its
  Check button got no answer: a check runs inside the request, and the web server's
  proxy (Next.js rewrites) stops waiting after 30 seconds. NDW's feeds take minutes,
  and a check also waits for any scheduled run in progress. The API was up.

Reproduced on a throwaway PostGIS 16 container with `--shm-size=8m` (synthetic rows:
80,000 events, 300,000 records): with a parallel hash join the query failed with
"could not resize shared memory segment … No space left on device"; the same query in
a session without parallel workers returned its 20,000 rows. (With 1 MB, PostgreSQL's
own setup failed with the same message.) REI's migrations ran on that database with
the new session settings.

## Decision

- `app/core/database.py`: every PostgreSQL session REI opens (the API, the scheduler,
  migrations) starts with `-c max_parallel_workers_per_gather=0 -c
  max_parallel_maintenance_workers=0`. REI's queries are lookups and lists by indexed
  columns; they do not need parallel workers, and without them no query needs
  `/dev/shm`. SQLite is opened as before.
- `record_observation` also says that the records are the source's own
  (`SourceArtifact.source_id == source_id`), so PostgreSQL reads one source's records
  through their index instead of joining against every source's.
- The console's Check: when no answer comes, it says the check may still be running
  and to reload in a few minutes (`checkFailureMessage`), not that the API is down.

Not chosen: raising `/dev/shm` on Railway (no setting for it on the PostGIS service
found; it would need the user's approval and a database restart) and raising the
proxy's 30-second limit (reads would then hang as long when the API is really down).

## Not checked

Production itself: the Railway CLI on this machine is still logged out, so the fix is
verified on the reproduction, not on production's data. Basque Country's own error is
not visible in the screenshot (the Check message was shown in its place); it works from
this machine (188 incidences on 27 October). If it still fails after this deploy, its
line in the console will show why.
