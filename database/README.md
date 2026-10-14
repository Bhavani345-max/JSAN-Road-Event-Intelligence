# Database

PostgreSQL with PostGIS is the target. Without `DATABASE_URL` the API uses a
local SQLite file for development (see `docs/decisions/0002-database.md`).

## Tables

| Table | Purpose |
| --- | --- |
| `sources` | Source registry (connected and researched sources) plus polling state (`last_poll_at`, `last_success_at`, `last_failure_at`, `last_error`) |
| `source_artifacts` | The original item fetched from a source, kept as evidence. Unique per `(source_id, external_id)`, which is what prevents duplicates |
| `events` | Canonical REI events. `geometry` is GeoJSON; on PostgreSQL, `geom` is the PostGIS geometry generated from it |
| `event_versions` | A snapshot of an event for every version (creation and each review decision) |

## Migrations

Migrations live in `migrations/versions` and are applied automatically when
the API starts (`AUTO_MIGRATE=true`). To run them yourself, from the
repository root:

```bash
alembic -c database/alembic.ini upgrade head
alembic -c database/alembic.ini revision -m "describe the change"   # new migration
```

The database URL is read from `DATABASE_URL`; it is never stored in a file
that is committed.

Migrations so far: `0001` initial schema; `0002` removes the demo events and
the `is_demo` flag and extends the source registry.

## Seeded accounts and live data

There are no sample or synthetic road events. `sources` is filled from the
code registry on start-up, and every row in `source_artifacts`, `events` and
`event_versions` comes from a connected source or a reviewer action. Test
fixtures live under `tests/` and never reach this database.

The first reviewer account is provisioned once when both
`SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` are set. The password is stored as
a salted PBKDF2 hash. Existing accounts are never reset by startup. To create
the account manually, run `python apps/api/seed_user.py` from the repository
root. To ingest a current snapshot from all connected feeds while the API is
running, run `python apps/api/seed_worldwide.py`; set `REI_API_URL` to the API
origin to target a remote deployment. New events remain in the validation
queue until a reviewer accepts them.
