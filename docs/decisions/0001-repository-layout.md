# 0001 — Repository layout

**Status:** accepted, 2 October 2026

## Decision

One repository with `apps/` (web, api), `connectors/`, `services/`,
`packages/`, `database/`, `infrastructure/`, `tests/` and `docs/`.

- The pipeline stages are Python packages imported by the API process, not
  separate deployable services.
- Python packages are imported from the repository root (`connectors.rss`,
  `services.ingestion`, `packages.event_schema`). `apps/api/run.py`, the
  Dockerfile and `pyproject.toml` (for pytest) put the root and `apps/api` on
  the import path.
- Python folder names use underscores (`geo_resolution`, `event_schema`,
  `geo_models`, `source_models`) because hyphenated names cannot be imported.
- Folders for stages that are not built yet contain only a README.

## Why

The folder boundaries match the long-term pipeline, so a stage can later be
moved into its own worker without redesign. Running them as separate services
now would add queues, deployment and failure modes that a single-city PoC
does not need.

## Consequences

- Services must not import from `apps/api`; they receive what they need
  through small interfaces (for example `IngestionStore`).
- When a stage is split out, its package moves behind a queue or an HTTP
  boundary and the root-level import path is replaced by an installed package.
