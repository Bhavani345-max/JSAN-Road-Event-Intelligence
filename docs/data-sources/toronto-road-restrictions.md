# City of Toronto road restrictions

- **Source id:** `toronto-road-restrictions` · **Class:** AUTHORITATIVE_OFFICIAL · **Tier:** 1 · **City:** Toronto
- **Endpoint:** `GET https://secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json` (no key)
- **Connector:** `connectors/official/toronto.py`
- **Status:** CONNECTED, run by hand in the test phase:
  `python apps/api/ingest_source.py toronto-road-restrictions`.

## What it gives

`{"Closure": [...]}`, about 2,000 records, each with:

- an id, the road, and a description of the stretch ("Victoria St at Shuter
  St to 45 m South of Shuter St");
- coordinates and a polyline;
- the type (ROAD_CLOSED, CONSTRUCTION), whether it is planned, and the work
  type;
- the directions affected (BOTH_DIRECTIONS, ONE_DIRECTION);
- start and end times in milliseconds since 1970;
- the City's impact level.

## How REI reads it

| City field | REI |
| --- | --- |
| type + stretch | title ("Road closed: …") |
| description | description |
| ROAD_CLOSED and planned → PLANNED_ROAD_CLOSURE; CONSTRUCTION → ROAD_WORKS; special event → SPECIAL_EVENT | event type |
| `geoPolyline` | geometry (LineString; a Point when it has one position), unchanged |
| `directionsAffected` | the location's direction; BOTH_DIRECTIONS also sets the event's direction (ONE_DIRECTION does not say which) |
| `startTime`, `endTime` | start, end |
| `currImpact` | kept in the City's words |
| — | attribution "Contains information licensed under the Open Government Licence – Toronto." |

Some records send the work type as a fragment of a JSON table; the name is
read out of it.

## Terms and limits

- Open Government Licence – Toronto (open.toronto.ca/open-data-licence): use
  "for any lawful purpose", with attribution.
- No rate limit is published. A run makes one request; the response is about
  3 MB.
- Read for testing; not formally reviewed by a lawyer.

## Verified 6 October 2026

2,047 records; a run keeps 30 (full closures first, most recently updated).
See the [international test report](../international-source-test-report.md).
