# 0023 — Backend, frontend and database folders

**Status:** accepted, 14 October 2026. Replaces the folder layout of
[0001](0001-repository-layout.md); its other rules stand.

## Context

The repository had grown to eleven top-level folders: the API and the console
under `apps/`, the Python pipeline spread over `connectors/`, `services/` and
`packages/`, tests in two places (`tests/` and `apps/api/tests/`), tools in
`tools/`, Dockerfiles in `infrastructure/docker/`, and `pyproject.toml` and
`conftest.py` at the root. The user asked for a `backend` folder holding all
the backend files, a `frontend` folder holding all the frontend files, and a
`database` folder, with a neat and clean flow.

## Decision

```
backend/      everything Python
  app/          FastAPI application (was apps/api/app)
  connectors/   services/   packages/
  cli/          command-line tools (were apps/api/*.py)
  tools/        developer tools (placement evaluation)
  tests/        all Python tests; the HTTP API tests are tests/api (was apps/api/tests)
  run.py        starts the API
  pyproject.toml  conftest.py  requirements*.txt  Dockerfile
  .data/        local runtime files, git-ignored (SQLite rei.db, backups, logs, caches, OSM)
frontend/     the Next.js console (was apps/web), with its Dockerfile
database/     Alembic configuration and migrations (unchanged)
docs/  scripts/  infrastructure/  docker-compose.yml  start-rei.cmd  stop-rei.cmd  .env
```

- `backend/` is the Python import root: imports are unchanged
  (`app.…`, `connectors.…`, `services.…`, `packages.…`, `tests.…`).
- `database/` stays a top-level folder of its own. It is never imported as
  Python; the API finds `database/alembic.ini` from `REPO_ROOT`, and
  `database/migrations/env.py` puts `backend/` on the import path.
- The local SQLite file stays with the backend's other runtime files in
  `backend/.data/`, so logs, caches, backups and the database move together
  and one ignore rule covers them. `app.core.config.DATA_DIR` names the folder.
- The root `.env` and the root `.venv` stay where they are; the API reads
  `REPO_ROOT/.env`.
- The API image builds from the repository root (`docker build -f
  backend/Dockerfile .`) because it also needs `database/`; the web image
  builds from `frontend/`.
- The stray, empty root `package-lock.json` (no `package.json` beside it) was
  removed.

## Path changes

| Before | After |
| --- | --- |
| `apps/api/app/` | `backend/app/` |
| `apps/api/run.py` | `backend/run.py` |
| `apps/api/<tool>.py` (reprocess, retention, backfill, search_sweep, ingest_source, match_events, ai_read, gis, seed_user, seed_worldwide) | `backend/cli/<tool>.py` |
| `apps/api/requirements*.txt` | `backend/requirements*.txt` |
| `apps/api/tests/` | `backend/tests/api/` |
| `apps/api/.data/` | `backend/.data/` |
| `connectors/`, `services/`, `packages/` | `backend/connectors/`, `backend/services/`, `backend/packages/` |
| `tests/` | `backend/tests/` |
| `tools/placement_eval/` | `backend/tools/placement_eval/` |
| `pyproject.toml`, `conftest.py` | `backend/pyproject.toml`, `backend/conftest.py` |
| `infrastructure/docker/api.Dockerfile` | `backend/Dockerfile` |
| `apps/web/` | `frontend/` |
| `infrastructure/docker/web.Dockerfile` | `frontend/Dockerfile` |

Decision records 0001–0022 and the dated reports keep the paths they were
written with; read them through this table. The README, the architecture
overview, the API reference, `database/README.md`, the source notes and the
GIS guide use the new paths.

## Consequences

- Run the tests with `cd backend && pytest`, the API with
  `python backend/run.py`, the console from `frontend/`.
- `scripts/windows/rei-watchdog.ps1` starts `backend\run.py` and runs
  `npm run dev` in `frontend\`; logs are in `backend\.data\logs\`. The
  scheduled tasks call the same watchdog path, so they need no change.
- A deployment configured outside the repository (for example a Railway or
  Vercel service with a root directory of `apps/api` or `apps/web`, or a
  Dockerfile path under `infrastructure/docker/`) must be pointed at the new
  paths before this layout is deployed.
