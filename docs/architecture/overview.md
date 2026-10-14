# Architecture overview

## Long-term pipeline

```
Data sources
  → Source acquisition (API / RSS / HTML / PDF / CSV / email / partner feeds)
  → Event extraction
  → Canonical REI event
  → GIS resolution (PostGIS / road network)
  → Confidence / validation
  → Human QC
  → Lifecycle / monitoring
  → Publishing / adapters → customers
```

## What exists today (14 October 2026)

The repository has three parts: `backend/` (all Python), `frontend/` (the
Next.js console) and `database/` (migrations). Module paths below are inside
`backend/`.

```
connectors/               rss, api (Google News via Serper), official feeds,
                          html (one article page) → RawSourceRecord
        ↓
services/ingestion        skip items already stored; store every new item as evidence
        ↓
services/extraction       keyword rules for text; the source's own fields for official records
services/ai_reading       optional: a model reads articles, every answer checked against the text
        ↓                 relevant → canonical ReiEvent, status VALIDATION_REQUIRED
services/geo_resolution   placed at a named place: OpenStreetMap first, Google fallback
services/merging          reports of the same event matched; possible matches asked of a reviewer
        ↓
app/ (FastAPI)            persists sources, evidence, events and versions; reviewer sign-in;
        ↓                 REST API under /api
frontend/ (Next.js)       sign-in, list, filters, details, review actions, map;
                          calls /api on its own origin, proxied to the API
```

| Stage | Module | Status |
| --- | --- | --- |
| Source acquisition | `connectors/rss`, `connectors/api`, `connectors/official`, `connectors/html` | Implemented: news feeds and Google News search on a schedule; official feeds run by hand unless `OFFICIAL_FEEDS_SCHEDULED=true` |
| Source registry | `connectors/registry.py`, `connectors/discovered.py` | Connected and researched sources |
| | `connectors/pdf`, `connectors/email` | Reserved |
| Ingestion | `services/ingestion` | Implemented |
| Extraction | `services/extraction`, `services/ai_reading` | Keyword rules, structured official records, optional AI reading ([0020](../decisions/0020-ai-reading-of-articles.md)) |
| Canonical event | `packages/event_schema` | Implemented |
| Placing events | `services/geo_resolution` | OpenStreetMap place lists (Hyderabad, Mumbai, Bengaluru), Google fallback ([0021](../decisions/0021-placement-osm-first-google-fallback.md)) |
| GIS resolution | `services/gis_resolution` | Hyderabad road network in PostGIS, run on demand; proposals need a reviewer ([0012](../decisions/0012-gis-resolution-engine.md)) |
| Merging | `services/merging` | Cross-source matching ([0011](../decisions/0011-cross-source-merging-and-feed-absence.md)) |
| Confidence | `services/confidence` | Reserved — confidence stays empty |
| Human review | `services/lifecycle`, `app/services/review_service.py`, `frontend/features/qc` | Confirm, reject, QC approval (and approve anyway), severity, extend, correct location, add by hand |
| Sign-in | `app/services/auth_service.py`, `frontend/features/auth` | Reviewer accounts; every API route except health and sign-in needs a session |
| Lifecycle monitoring | `services/lifecycle` | Transition rules and list views; no automatic status changes |
| Publishing, notifications | `services/publishing`, `services/notifications` | Reserved |

## Design rules

1. **Dependencies point inwards.** `packages` depends on nothing. `connectors`
   and `services` depend on `packages`. The API (`backend/app`) depends on all three.
   Services never import from the API: the ingestion pipeline is given a
   connector and a store (`IngestionStore`) and knows nothing about RSS or SQL.
2. **Evidence before interpretation.** Every fetched item is written to
   `source_artifacts` (original markup, content hash, timestamps) before
   anything is derived from it, whether or not it turns out to be relevant.
3. **Nothing is invented.** A canonical event field is `null` unless the source
   stated it. Events without geometry are not drawn on the map.
4. **Fail-safe publishing.** New events start as `VALIDATION_REQUIRED`. An
   event cannot reach `APPROVED` or any later live status without a resolved
   location and a start time (`services/lifecycle/transitions.py`).
5. **One data path to the UI.** The web app reads events only from the API.
6. **Real data only.** Nothing is seeded. Test fixtures live under `tests/` and
   never reach the application database.

## Adding a source

- **Another RSS feed:** add a `SourceDefinition` next to
  `connectors/rss/telangana_today.py` and list it with `_rss(...)` in
  `connectors/registry.py`. Nothing else changes; this is how The Hindu and
  Deccan Chronicle were added.
- **Another source type (e.g. an incidents API):** implement the
  `SourceConnector` protocol (`connectors/base.py`) in `connectors/api/`,
  returning `RawSourceRecord`s, and register it. A source that already
  provides structured events with coordinates will also need its own
  record-to-event step in `services/extraction`, in place of keyword detection.

## Running as one process, for now

The stages are Python modules inside the API process, and polling is an
in-process background task. That is deliberate at this scale. The module
boundaries are what a later split into separate workers would follow; no
queue, cache or orchestrator is introduced until there is a concrete need.
