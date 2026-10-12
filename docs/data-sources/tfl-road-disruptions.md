# Transport for London road disruptions

- **Source id:** `tfl-road-disruptions` · **Class:** AUTHORITATIVE_OFFICIAL · **Tier:** 1 · **City:** London
- **Endpoint:** `GET https://api.tfl.gov.uk/Road/all/Disruption` (no key; optional `TFL_APP_KEY`)
- **Connector:** `connectors/official/tfl.py`
- **Status:** CONNECTED, run by hand in the test phase:
  `python apps/api/ingest_source.py tfl-road-disruptions`, or the source's
  "Check" button in the console with London selected.

## What it gives

Disruptions on the roads TfL manages, each with:

- id, category and sub-category (Works / Utility works, Collisions /
  Vehicle collision, Asset issues / Traffic signal fault, …);
- TfL's severity (Minimal, Moderate, Serious, No impact) and status;
- start and end times;
- a location ("[A13] NEWHAM WAY (E14, E16) (Newham)"), comments and a current
  update;
- a point, and on some records an area polygon or multipolygon;
- on some records, the streets affected, each with its direction, whether it
  is closed, and its segments as lines.

## How REI reads it

| TfL field | REI |
| --- | --- |
| `id` | external id; the event id is derived from it |
| sub-category + location | title |
| comments + current update | description |
| category | event type: Works → ROAD_WORKS, Collisions → ACCIDENT, Asset issues → ROAD_HAZARD, Special and planned events → SPECIAL_EVENT; anything else → none |
| `startDateTime`, `endDateTime` | start, end |
| `geometry` (area), else `point` | geometry, unchanged; location class SOURCE_PROVIDED |
| `streets[]` | affected locations, each with its segments (MultiLineString), direction and closure |
| street directions, when all the same | event direction |
| `severity`, `status` | kept in TfL's words; REI's severity stays empty |
| — | attribution "Powered by TfL Open Data" and the OS / Geomni notices |

## Terms and limits

- Open Government Licence v2.0 with TfL's amendments
  (tfl.gov.uk/corporate/terms-and-conditions/transport-data-service).
  Commercial and non-commercial use is permitted, with attribution.
- 50 requests a minute without a key; at most 500 calls a minute per data
  feed under the terms. A run makes one request.
- Read for testing; not formally reviewed by a lawyer.

## Verified 6 October 2026

116 disruptions; the test runs stored 31. See the
[international test report](../international-source-test-report.md).
