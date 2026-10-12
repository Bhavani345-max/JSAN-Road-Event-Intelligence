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

## What exists today

```
connectors/rss            fetch + parse a feed → RawSourceRecord
        ↓
services/ingestion        skip items already stored; store every new item as evidence
        ↓
services/extraction       keyword rules → RELEVANT_TRAFFIC_ARTICLE / NOT_RELEVANT
        ↓                 relevant → canonical ReiEvent, status VALIDATION_REQUIRED
apps/api                  persists sources, source_artifacts, events, event_versions
        ↓                 REST API
apps/web                  console: list, filters, details, review actions, map
```

| Stage | Module | Status |
| --- | --- | --- |
| Source acquisition | `connectors/rss` | Implemented: six news feeds |
| Source registry | `connectors/registry.py`, `connectors/discovered.py` | Connected and researched sources |
| | `connectors/api`, `html`, `pdf`, `email` | Reserved |
| Ingestion | `services/ingestion` | Implemented |
| Extraction | `services/extraction` | Rule-based keyword detection; no AI |
| Canonical event | `packages/event_schema` | Implemented |
| GIS resolution | `services/geo_resolution` | Named-place location from an OpenStreetMap gazetteer; no road-network matching yet |
| Confidence | `services/confidence` | Reserved — confidence stays empty |
| Human review | `services/lifecycle`, `apps/web/features/qc` | Basic: confirm / reject / reopen |
| Lifecycle monitoring | `services/lifecycle` | Transition rules only |
| Publishing, notifications | `services/publishing`, `services/notifications` | Reserved |

## Design rules

1. **Dependencies point inwards.** `packages` depends on nothing. `connectors`
   and `services` depend on `packages`. `apps/api` depends on all three.
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
