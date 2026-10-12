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

## No seed data

Nothing is seeded. The database holds only what connected sources provided:
`sources` is filled from the code registry on start-up, and every row in
`source_artifacts`, `events` and `event_versions` comes from ingestion or
review. Test fixtures live under `tests/` and never reach this database.
