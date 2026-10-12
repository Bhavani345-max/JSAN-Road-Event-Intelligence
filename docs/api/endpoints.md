# REI API

Base URL in development: `http://127.0.0.1:8000`. Interactive documentation
(generated from the code) is at `/api/docs`; the OpenAPI document is at
`/api/openapi.json`.

There is no authentication yet. Do not expose the API beyond a trusted network.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness, including a database check |
| GET | `/api/cities` | Configured cities: country, time zone, area, map view |
| GET | `/api/cities/{city_id}` | One city |
| GET | `/api/events` | List events |
| GET | `/api/events/{event_id}` | One event with its version history |
| POST | `/api/events/{event_id}/status` | Record a review decision |
| POST | `/api/events/{event_id}/severity` | Record a reviewer's REI severity (LOW, MEDIUM, HIGH, CRITICAL) |
| GET | `/api/sources` | Source registry with polling state and counts |
| GET | `/api/sources/{source_id}` | One source |
| POST | `/api/ingestion/run` | Fetch sources now |

## GET /api/cities

Every configured city, the default (Hyderabad) first: `id`, `name`,
`country`, `region`, `timezone`, `language`, `bbox` (south, west, north,
east), `map_center` ([longitude, latitude]), `map_zoom`, `scope_terms`,
`official_sources` and `has_gazetteer` (whether events can be located by the
places they name).

## GET /api/events

Query parameters: `status`, `severity` (REI's own severity: LOW, MEDIUM, HIGH or
CRITICAL; never the source's words), `source_id`, `q` (text search), `limit`
(1–500, default 200), `offset`.

`q` finds events containing every word given, searching the event (title,
description, road, city, type), its source, and the stored article it came
from (title, summary and full text).

Returns `{ "items": [...], "total": n }`, most recently published first. Every
event comes from a connected source; there are no demo events.

Each event has the canonical fields (`event_id`, `source_id`,
`source_reference`, `title`, `event_type`, `description`, `city`,
`affected_road`, `start_time`, `end_time`, `status`, `severity`, `direction`,
`geometry`, `confidence`, `created_at`, `updated_at`) plus:

- `detection` — how the event was derived: `method`, `score`,
  `matched_keywords`, `road_mentions`; `places` (known Hyderabad places the
  article names); `location` (the place the geometry comes from: `place_name`,
  `place_kind`, `precision`, `mention`, `found_in`, `reference`), or `null`;
  `stated_period` (the article's words the times were read from);
  `attributed_to` (authorities the article says announced the measure).
- `source` — `{source_id, source_name, source_type}`.
- `evidence` — the stored source artifact (`url`, `title`, `published_at`,
  `retrieved_at`, `content_hash`).
- `version` — current version number.

A field is `null` when the source did not state it. `geometry` is GeoJSON
(`Point`, `LineString` or `Polygon`), or `null` when the article names no place
the event can be located by. A `Point` with `detection.location` set is the
position of the named place, not the extent of the event.

## POST /api/events/{event_id}/status

Body: `{ "status": "QC_PENDING", "reason": "optional text" }`.

Applies the change if the lifecycle rules allow it and records a new version.
Returns the updated event.

- `404` — no such event.
- `409` — transition not allowed, or the event lacks the location and start
  time required for an approved/live status.

From `VALIDATION_REQUIRED` the allowed moves are `QC_PENDING` and `REJECTED`.

## GET /api/sources

The whole source registry: connected sources and sources that were researched
but are not connected. Optional `integration_status` (`CONNECTED`,
`DISCOVERED`, `MANUAL_ONLY`, `REQUIRES_ACCESS`, `NOT_USABLE`).

Each source has its descriptive fields (`organization`, `authority_type`,
`source_tier`, `source_type`, `source_url`, `endpoint`, `access_method`,
`integration_status`, `active`, `polling_frequency_minutes`, `language`,
`events_supported`, `parser_type`, `terms_reviewed`, `evidence_retention`,
`notes`), its polling state (`last_poll_at`, `last_success_at`,
`last_failure_at`, `last_error`) and counts (`artifact_count`, `event_count`).

## POST /api/ingestion/run

Optional query parameter `source_id`; without it every connected, active
source is fetched. Sources that are not connected are never fetched. Returns one result per source:

```json
{ "results": [ { "source_id": "telangana-today", "status": "ok", "error": null,
  "fetched": 500, "new_artifacts": 3, "duplicates": 497, "relevant": 1,
  "events_created": 1, "started_at": "...", "finished_at": "..." } ] }
```

A source that cannot be reached is reported with `"status": "failed"` and an
`error` message (HTTP 200), and the failure is recorded on the source.
`404` if `source_id` is unknown or has nothing to fetch.

## POST /api/events/{event_id}/extend

Body: `{ "end_date": "2026-12-31", "reason": "Still closed on 5 October, seen on site" }`.

Records that an event runs longer than recorded. `end_date` is the new last
day (a whole day in IST), or `null` for "until further notice"; `reason` is
required. The previous end and the reason are kept in
`detection.period_revision` and the change is a new version. The status does
not change.

- `404` — no such event.
- `409` — not an extension (the date is not later than the current end, or is
  before the start), or the event is rejected, cancelled, superseded or expired.

## POST /api/events/{event_id}/location

Body: `{ "longitude": 78.3519, "latitude": 17.4455, "place_name": "IIIT Junction", "reason": "The works are at the junction itself, seen on site" }`.

Puts an event at the spot a reviewer picked on the map. All four fields are
required. The geometry becomes that point, `detection.location.method` becomes
`reviewer_placed`, and `detection.location_revision` records the reason and
the name the event was located by before. The status does not change.

- `404` — no such event.
- `409` — the spot is outside Greater Hyderabad, or the event is rejected,
  cancelled, superseded or expired.

## POST /api/events

Adds an event that no connected source reported. Returns `201` and the event.

```json
{
  "title": "DLF Road closed between Gate No.1 and Gachibowli Traffic PS",
  "basis": "Seen on site on 5 October 2026",
  "event_type": "PLANNED_ROAD_CLOSURE",
  "place": "DLF road",
  "start_date": "2026-07-01",
  "end_date": "2026-12-31",
  "description": "Barricades in place; traffic diverted via Gachibowli Junction.",
  "reference_url": "https://…"
}
```

Only `title` and `basis` are required. The entry is stored as evidence under
the source `manual-entry`; the event has `detection.method = "manual_entry"`
and `detection.basis`, starts as `VALIDATION_REQUIRED`, and has a geometry
only if `place` is a known Hyderabad place name.

## GET /api/places?q=

Up to eight known Hyderabad places whose name starts with or contains `q`
(at least two characters): `[{ "name": "DLF road", "kind": "road" }]`. Only
places an event can be located by are returned.

## Added 6 October 2026

- `GET /api/events?city=london`: events of one configured city (422 for an
  unknown city).
- `GET /api/places?q=…&city=london`: place suggestions from that city's
  place list (empty for a city without one).
- Each event's `source` now also carries `source_class`, `source_tier` and
  `discovery_only`. Its `detection` carries `location_class`,
  `affected_locations` (each with `resolution`, `geometry`, `direction`,
  `closure`), and, for an official source's event, `source_category`,
  `source_severity`, `source_status` and `attribution`. `detection.score` is
  null for an event an official source states itself.
- Each source carries `source_class`, `country`, `region`, `city`,
  `cost_category`, `rate_limit`, `terms_status`, `licence`, `attribution`,
  `commercial_use`, `provides_geometry`, `provides_segments`,
  `provides_direction`, `real_time` and `discovery_only`.
- `POST /api/events/{id}/status` with `APPROVED` is refused (409) while the
  event's location is approximate. Approval records the location as
  `QC_APPROVED`.
- `POST /api/events/{id}/location` checks the spot against the event's own
  city, and records the location as `HUMAN_CORRECTED`.
