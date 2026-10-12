# 0012 — GIS Resolution Engine (OpenStreetMap in PostGIS, no routing)

**Status:** accepted, 6 October 2026. Follows
[the road-network research](../gis-road-network-research.md) and
[0009](0009-multi-city-official-sources-and-location-classes.md).

## Decision

- The road network is OpenStreetMap, imported per city into PostGIS (a
  separate database, `GIS_DATABASE_URL`). Hyderabad first.
- A deterministic resolver turns junction, crossing, stretch and road names
  into OSM geometry with a confidence (HIGH, MEDIUM, LOW, UNRESOLVED) and the
  reasons. Ambiguous means unresolved; the nearest is never picked.
- Only one HIGH, unambiguous result from the headline or summary is applied,
  and only to an event whose location is approximate or unresolved. Source
  geometry and a reviewer's placement are never replaced.
- A GIS location is a proposal: the event cannot be approved until a reviewer
  approves it. Rejecting restores the previous location.
- Junction names OSM does not carry are kept as reviewer-confirmed junction
  references, proposed only at OSM nodes and UNCONFIRMED until confirmed.
- No routing engine and no map matching.

## Why

News reports name junctions and roads, not coordinates. The locality centre
REI used until now is often a kilometre or more from the event. OSM holds the
junctions and roads with their real geometry and is free to use with
attribution. Routing engines answer different questions (how to get round a
closure) and are not needed to place an event.

## Deviation

The importer reads the public Overpass API in tiles, not a Geofabrik extract
through osmium and osm2pgsql, which are not available on this machine. See
[the engine document](../gis-resolution-engine.md).

## Consequences

- Docker (PostGIS) must run to resolve; the API and console work without it
  (the resolve endpoint answers 503).
- Results depend on OSM's names; reviewers grow the junction reference list.
- Schema: migration 0006 adds `junction_references`; the `gis` schema is
  created by the importer in the GIS database.
