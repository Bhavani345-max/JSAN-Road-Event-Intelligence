# 0002 — Database: PostgreSQL/PostGIS, with a SQLite fallback for development

**Status:** accepted, 2 October 2026

## Decision

- PostgreSQL with PostGIS is the target database. `docker-compose.yml` runs it.
- If `DATABASE_URL` is not set, the API uses a local SQLite file
  (`apps/api/.data/rei.db`) so the project runs with no database setup.
- The schema is defined once, in Alembic migrations (`database/migrations`),
  and the same migrations run on both databases.
- Event geometry is stored as GeoJSON in `events.geometry` (JSONB on
  PostgreSQL). On PostgreSQL the migration also enables PostGIS and adds
  `events.geom`, a `geometry(Geometry, 4326)` column that the database
  generates from the GeoJSON, with a GiST index.

## Why

A developer or reviewer can start the system with two commands, while the
production path is still PostgreSQL/PostGIS. Keeping GeoJSON as the stored
value avoids a PostGIS-only data model in this phase; the generated `geom`
column means spatial queries are available as soon as events have geometry,
with nothing to keep in sync by hand.

## Consequences

- SQLite has no PostGIS: spatial queries only work on PostgreSQL. The GIS
  Resolution Engine will require PostgreSQL.
- A missing JSON value must be stored as SQL `NULL`, not the JSON literal
  `null`, or PostGIS cannot generate `geom`. The JSON column type is
  configured for this and a test guards it.
- Both paths were exercised on 2 October 2026: SQLite by the test suite, and
  PostgreSQL 16 / PostGIS 3.4 by running the migrations, seeding, ingestion,
  a review decision and a spatial query against a container.
