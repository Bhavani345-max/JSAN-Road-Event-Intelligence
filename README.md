# JSAN Road Event Intelligence (REI) v1.0

REI collects road events (closures, diversions, processions, flooding, road
works) from external sources, turns them into one canonical event format,
and shows them on a map for human review.

**Current coverage:** real-source news for Hyderabad, with official road feeds
in London, Toronto, Mumbai, Bengaluru, New York City, France and Finland. Since
16 October 2026 (decision 0033): Delhi, Chennai, Kolkata, Pune and Ahmedabad are
configured with place lists, South Africa has a place list over seven metro areas
and the SAnews feed, Mid-day is disconnected (personal-use terms), and a GDELT
news search is built but off by default (`GDELT_SEARCH_ENABLED`). Feeds whose
terms do not permit commercial use wait for written permission. The original
Hyderabad proof of concept began with six publisher feeds:

```
Telangana Today, NewsMeter,
The Hindu and Deccan Chronicle (disconnected 15 Oct 2026, decision 0032),
The Siasat Daily (disconnected 14 Oct 2026, decision 0024),
The Hans India (removed 14 Oct 2026, decision 0026)
   → generic RSS connector → ingestion → evidence stored
   → keyword detection + Hyderabad scope + a named place
   → REI event (VALIDATION_REQUIRED), located and dated from the article's own words
   → FastAPI → Next.js console → map
```

- Real articles are fetched from the connected news feeds, stored as evidence, and the
  traffic-related ones become events awaiting human review. Reports of the
  same real-world event from different sources are kept separate, not merged.
- Nothing is invented: an event only carries what the article states. It is
  placed on the map at the Hyderabad place its headline or summary names
  (position from OpenStreetMap, shown as approximate), and dated only when the
  article states a period in so many words ("for 60 days from September 26",
  "from October 10 to 18", "till October 18").
  Severity and confidence stay empty. An event that names no known place is
  listed as "Not located" and not drawn.
- An article becomes an event only when it carries a clear road signal
  (diversion, restriction, closure, waterlogging, road or flyover works) and
  names a road or place. Everything else is kept as evidence only.
- There is **no demo data**. Every event comes from a connected source.
- Access is protected by a sign-in page, with exactly two accounts and no
  sign-up (decision 0032): the Admin (`SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`)
  reviews and runs sources; the User (`SEED_USER_EMAIL`/`SEED_USER_PASSWORD`)
  views the console and changes nothing. Each is created once from the ignored
  root `.env` and never reset; see [database setup](database/README.md).
- To pull a current snapshot from all connected live feeds, run
  `python backend/cli/seed_worldwide.py` while the API is running. Set `REI_API_URL`
  to the API origin to seed a remote deployment. New source events enter the
  review queue and are never treated as approved by default.
- The console shows upcoming, ongoing and recently reported events only.
  Rejected events, ones whose stated end has passed, and reports that state no
  dates and are older than seven days (thirty for road works) are not shown
  anywhere in the console, whatever the filters say. They remain stored and
  are still returned by the API.
- A reviewer can **extend** an event that runs longer than its article said,
  and **add an event by hand** that no source reported. Both need the
  reviewer's reason, which is kept and shown with the event; see
  [decision 0007](docs/decisions/0007-reviewer-extensions-and-manual-entries.md).
- An event in QC is **approved** with the console's Approve button, which is
  enabled only when every QC requirement passes and otherwise lists why
  approval is blocked. The approval (reviewer, time, reason, version) is kept
  with the event and in its history; see
  [decision 0013](docs/decisions/0013-qc-approval-in-the-console.md).
- With a Serper.dev key (`SERPER_API_KEY` in `.env`), a **Google News search**
  source runs twelve Hyderabad road searches every eight hours (36 Serper
  credits a day) and reads each new article from its own page;
  `python backend/cli/search_sweep.py` searches the past month or year by hand.
  See [the source notes](docs/data-sources/google-news-search.md).
- When the headline names a locality and the headline or summary also names
  a junction, flyover or landmark inside it, the event is placed at that spot
  and the console says so ("within Gachibowli"); see
  [decision 0008](docs/decisions/0008-wider-search-and-more-exact-places.md).
- A further 23 sources (police, GHMC, HYDRAA, weather, commercial traffic
  APIs) have been researched and are recorded as not connected; see
  [the source research](docs/data-sources/hyderabad-source-research.md).

**Global source expansion (13 October 2026).**

- Cities are configuration (`backend/packages/cities/data/*.json`), including
  Hyderabad, London, Toronto, Mumbai, Bengaluru, New York City, France and Finland. The
  console opens on **All cities**; the header narrows it to one city
  (`/?city=london` opens one directly).
- Connected official feeds now include Transport for London, City of Toronto,
  NYC DOT, NYC permitted events, France's Bison Futé / Interdepartmental Road
  Directorate feed, DiaLog traffic orders, the Métropole de Lyon's works and
  Finland's Digitraffic ([decision 0027](docs/decisions/0027-more-official-sources.md)).
  NYC, France and Finland were fetched from live, keyless endpoints and keep the
  source's road geometry. Official feeds run by hand by default:
  `python backend/cli/ingest_source.py <source_id>`. Set
  `OFFICIAL_FEEDS_SCHEDULED=true` to poll every connected official feed on its
  own schedule, or list chosen feeds in `OFFICIAL_FEEDS_SCHEDULED_SOURCES`
  (comma-separated source ids) to switch them on one at a time
  ([decision 0028](docs/decisions/0028-official-feeds-scheduled-one-at-a-time.md)).
- Canada, Australia and South Africa are configured
  ([decision 0029](docs/decisions/0029-countries-and-confirmed-located-events.md)).
  - **Canada:** Toronto, plus DriveBC (British Columbia), Ottawa, Edmonton,
    Winnipeg and Calgary.
  - **Australia:** Main Roads WA, City of Gold Coast, City of Wodonga and
    Roads ACT (CC BY-SA, testing only).
  - **South Africa:** no source passes the checks yet.
  - Each country spanning several time zones shows each source's times in
    its own region's zone.
- The console shows only located events with a start stated by the source,
  and only until their end. An event with a start and no end runs until
  further notice: an official record until its source reports it over, an
  event read from an article for 30 days after its start (decision 0033).
  Expired, undated ("unconfirmed") and unlocated events are hidden, never
  deleted (`include_hidden=true` lists them). Feeds without locations (NYC permitted events, the Mumbai and
  Bengaluru traffic police listings) are switched off. Rows a source lists
  for one event are merged. Different events at one spot each get their own
  marker, spread around the spot with a line to it. Score the console against
  these rules with `backend/tools/requirements_eval/requirements_eval.py`.
- Additional sources are catalogued with their access and terms state,
  including Queensland QLDTraffic, Spain's National Access Point and Germany's
  Autobahn API. API keys, regional coverage or licence review still prevent
  those sources from being fetched. See the
  [global source research](docs/global-free-source-research.md).
- Every source states its class (official, open data, partner, publisher,
  discovery, commercial), cost, limits, licence and terms. News and search are
  never authoritative.
- Every event states how it was located: approximate (a named place, drawn
  as a hollow marker, and not approvable until a reviewer places it), source
  provided, GIS resolved, corrected by a reviewer, QC approved, or
  not located. An event may affect several places.
- Google News RSS is built but blocked by its own terms.
- When an official source revises a record, the new version is kept beside
  the original and an event still in review follows it; a decided event is
  only flagged ([decision 0010](docs/decisions/0010-official-source-revisions.md)).
- Reports of the same event from several sources are matched. Clear
  duplicates (the same article twice) are merged automatically. Possible
  matches wait for a reviewer ("Same event: merge" / "Different events").
  Merging links events and never deletes evidence; the canonical event shows
  every source and which source gave which field, and keeps disagreeing
  values side by side. An official record missing from its feed is counted
  and, after three refreshes, flagged for review, never ended
  ([decision 0011](docs/decisions/0011-cross-source-merging-and-feed-absence.md)).
  `python backend/cli/match_events.py` matches everything held.
- NYC DOT lists a block's closure once per permit purpose; rows with the same
  segment and work period are merged into one event, every row kept as
  evidence ([decision 0025](docs/decisions/0025-one-closure-listed-in-several-rows.md)).
  Events that still share a map point are listed, with their dates, when the
  point is clicked.
- **GIS Resolution Engine (Hyderabad):** junction, crossing and road-stretch
  names in a report are looked up in the OpenStreetMap road network (PostGIS)
  and, when exactly one place fits, proposed as the event's location with the
  OSM ids, the method, a confidence and the reasons. Ambiguous names are left
  unresolved with every candidate shown. Source geometry and reviewer
  placements are never replaced, and a GIS location needs a reviewer's
  approval. Not navigation-grade: no routing and no map matching
  ([the engine](docs/gis-resolution-engine.md),
  [decision 0012](docs/decisions/0012-gis-resolution-engine.md)).
- See [decision 0009](docs/decisions/0009-multi-city-official-sources-and-location-classes.md),
  [the global source research](docs/global-free-source-research.md),
  [the cost model](docs/data-source-cost-model.md) and
  [the international test report](docs/international-source-test-report.md).

## Run it locally

**On Windows, the everyday way:** double-click `start-rei.cmd` in the project
folder. It starts the API (port 8000) and the web console (port 3000), each
kept running by a watchdog that restarts it within seconds if it stops or
stops answering, and opens http://localhost:3000. `stop-rei.cmd` stops
everything. `scripts\windows\install-autostart.ps1` registers two hidden
scheduled tasks that start the watchdogs at logon and revive them within 5
minutes if they ever stop (`remove-autostart.ps1` undoes it). Logs: `backend\.data\logs\`.
If the API is briefly down, the console says so and reconnects by itself.

The manual way, for development:

Requirements: Python 3.12+, Node.js 22+.

```bash
# 1. API (terminal 1) — from the repository root
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements-dev.txt
python backend/run.py             # http://127.0.0.1:8000  (API docs at /api/docs)

# 2. Web console (terminal 2)
cd frontend
npm install
npm run dev                       # http://localhost:3000
```

With no configuration the API uses a local SQLite file and starts polling
the six feeds immediately, so real events appear within a few seconds.

### With PostgreSQL/PostGIS (the target database)

```bash
cp .env.example .env              # set POSTGRES_PASSWORD
docker compose up -d db           # PostGIS on localhost:5432 (REI_DB_PORT to change)
# in .env: DATABASE_URL=postgresql+psycopg://rei:<password>@localhost:5432/rei
python backend/run.py
```

`docker compose up --build` runs the database, API and web app together.

### GIS road network (optional)

The API runs without it; only GIS resolution needs it.

```bash
docker compose up -d db
docker compose exec db createdb -U rei rei_gis                 # once: a database for the road network
# in .env: GIS_DATABASE_URL=postgresql+psycopg://rei:<password>@localhost:5432/rei_gis
cd backend
python -m services.gis_resolution.import_osm --city hyderabad --snapshot 2026-10-06T00:00:00Z   # one pinned OSM snapshot; validated before loading
python cli/gis.py status                                        # what is loaded
python cli/gis.py resolve EVT-... --dry-run                     # what the engine would propose
```

### Maintenance commands

Run from `backend/` (the scripts in `backend/cli/` also run from anywhere).

```bash
cd backend
python cli/reprocess.py                    # re-derive events from stored articles after a rule change
python cli/retention.py [--apply [--vacuum]]   # drop the text of old non-road articles (preview by default)
python cli/backfill.py <source_id> <url>   # bring in one article its feed no longer carries
python cli/search_sweep.py --window month  # search Google News over a longer window (12 credits)
python cli/ingest_source.py tfl-road-disruptions   # run one connected source now (official feeds)
python cli/seed_user.py                    # create the Admin and User accounts from SEED_ADMIN_*/SEED_USER_* in .env
python cli/change_account_email.py OLD NEW --role admin [--apply]   # new sign-in email for an account (check only by default)
python -m services.geo_resolution.build_gazetteer --city hyderabad   # a city's place list
python -m services.geo_resolution.build_gazetteer   # refresh the place list from OpenStreetMap
python cli/gis.py propose-junction "NAME" --crossing "ROAD A" "ROAD B"   # a junction reference, UNCONFIRMED
```

### AI reading of articles (optional)

With `OPENROUTER_API_KEY` and `AI_MODEL` in `.env`, a language model on
OpenRouter reads each news article in batches and returns its intent, impact,
cause and places with their roles as JSON. REI keeps only what the article
itself contains, places names through the OpenStreetMap place list, and never
takes a position from the model. The API reads in the background every five
minutes within `AI_DAILY_REQUEST_LIMIT`. Details: `docs/decisions/0020-ai-reading-of-articles.md`.

```bash
python backend/cli/ai_read.py --status        # waiting articles and requests used today
python backend/cli/ai_read.py                 # read what is waiting now
python backend/cli/ai_read.py --days 7        # also older articles
```

Markers are placed by OpenStreetMap first and, with `SERPER_API_KEY`, Google
Maps for names OSM cannot place; the method and its scores are in
`docs/placement-evaluation-2026-10-09.md`. Rerun the rubric with
`python backend/tools/placement_eval/placement_eval.py PROD`.

## Tests

```bash
cd backend && pytest              # backend: connectors, detection, pipeline, database, sign-in, API
# PostGIS loader tests run only with REI_GIS_TEST_DATABASE_URL (a test database, never the real one)
cd frontend && npm test           # frontend: API mapping, filters, map data
cd frontend && npm run typecheck && npm run lint && npm run build
```

## Repository layout

```
backend/     Python: the API and everything behind it
frontend/    Next.js web console
database/    Database migrations (Alembic)
docs/        Architecture, API, data sources, decisions
scripts/     Windows start/stop watchdogs (start-rei.cmd, stop-rei.cmd at the root)
```

| Path | What it is |
| --- | --- |
| `backend/app/` | FastAPI service: routes, sign-in, database models, repositories, application services |
| `backend/connectors/` | One sub-package per acquisition method: `rss/`, `api/` (Serper), `official/` (city and national feeds), `html/` (single article pages), `discovery/`; `discovered.py` catalogues sources not connected |
| `backend/services/` | Pipeline stages: `ingestion`, `extraction`, `ai_reading`, `geo_resolution` (placing events), `gis_resolution` (road network), `lifecycle`, `merging`; `publishing`, `notifications`, `confidence`, `qc` are reserved |
| `backend/packages/` | Shared models and data: `event_schema`, `source_models`, `geo_models`, `cities` (city configuration), `common` |
| `backend/cli/` | Command-line tools: reprocess, retention, backfill, search sweep, one-source ingestion, AI reading, GIS, reviewer and snapshot seeding |
| `backend/tools/` | Developer tools: the placement evaluation rubric |
| `backend/tests/` | `unit`, `integration`, `geospatial`, `golden-events`, `fixtures`, `api` (the HTTP API) |
| `backend/run.py` | Starts the API for development |
| `backend/.data/` | Local runtime files, never committed: the SQLite database `rei.db`, backups, logs, caches, OSM snapshots |
| `backend/Dockerfile` | API image (built from the repository root, as it also needs `database/`) |
| `frontend/` | Next.js console: sign-in, event list, filters, map, review actions, extending and adding events; `frontend/Dockerfile` |
| `database/` | Alembic migrations and configuration; no synthetic event seed data |
| `infrastructure/` | Placeholders for Kubernetes and monitoring |
| `docs/` | Architecture, API, data sources, decisions |

Paths in the docs such as `services/...`, `connectors/...` or `packages/...`
are inside `backend/` (layout since 14 October 2026, see
[decision 0023](docs/decisions/0023-backend-frontend-database-layout.md)).
Python folders use underscores (`geo_resolution`, `event_schema`) because
Python cannot import names containing hyphens.

More detail: [architecture](docs/architecture/overview.md) ·
[API](docs/api/endpoints.md) · [data sources](docs/data-sources/README.md) ·
[decisions](docs/decisions/).
