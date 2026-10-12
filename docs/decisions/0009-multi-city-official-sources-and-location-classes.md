# 0009 — Several cities, official sources, source classes and location classes

**Status:** accepted, 6 October 2026. Extends [0006](0006-named-place-location-and-stated-dates.md)
and [0008](0008-wider-search-and-more-exact-places.md).

## Context

The brief of 6 October 2026: collect and test real road-event data from
Hyderabad and, eventually, cities elsewhere, from free and public sources,
without breaking what works and without inventing anything. London was to be
the first international city if Transport for London's data was accessible
and its terms permitted testing. A further city was to be chosen on evidence.
The GIS road-network engine was to stay out of this phase, with only its
interfaces prepared.

## Decision

**Source classification.** Every source states what kind of body it is
(`source_class`):

- `AUTHORITATIVE_OFFICIAL`
- `GOVERNMENT_OPEN_DATA`
- `PARTNER`
- `PUBLISHER`
- `DISCOVERY`
- `COMMERCIAL`

This is separate from its format (`source_type`: RSS, API, …) and from REI's
tier. The registry also records country, region and city, cost category, rate
limit, terms status, licence, attribution, commercial use, and whether its
records carry geometry, segments and direction, and whether they are real time.

Publishers and search are always `discovery_only` and tier 4, which the
model enforces. A newspaper reporting what the police announced is still a
newspaper. Migration 0003 adds these columns; existing rows keep working.

**Cities are configuration.** `packages/cities/data/<city>.json` states each
city's country, time zone, language, area, map view, scope words, place list,
keyword rules and discovery searches. The classifier, the stated-date reader
(whole days in the city's zone), the place resolver, the Serper searches, the
API (`/api/cities`, `?city=`) and the console all read it. Hyderabad's file
reproduces the behaviour from before. Adding a city means adding a file and
registering its sources.

**Official sources build events from their own fields.** A structured
source's connector fills `RawSourceRecord.structured` with what the source
states: type, category, severity, status, start, end, geometry, affected
locations, direction and attribution. The event is built from that, not
detected from text. The source's geometry is kept exactly as published
(points, lines, polygons, and now multi-part shapes). Its severity is kept in
its own words, and REI's severity stays empty.

A record whose geometry lies outside the city's area is stored as evidence but
makes no event. Tier 1 is not approval: every event still starts as
`VALIDATION_REQUIRED`.

**Connected: London and Toronto.**

- Transport for London road disruptions: keyless; OGL v2.0 with TfL's
  amendments, which permit commercial use with attribution.
- City of Toronto road restrictions: keyless; Open Government Licence –
  Toronto.

Toronto was chosen over New York, Sydney and Singapore on the research in
[global-free-source-research.md](../global-free-source-research.md). During
this test phase both are connected but run by hand
(`OFFICIAL_FEEDS_SCHEDULED=false`), with at most 30 records per run.

**Google News RSS is built and blocked.** Its feeds state they are for
"personal, non-commercial use" in a feed reader, and that "any other use of
the feed is expressly prohibited". The connector exists and is tested on a
saved feed, but the source is registered as `BLOCKED`, and its terms as
`RESTRICTED`. Serper remains the Hyderabad discovery source.

**Location classes.** Every event's location is one of:

- `APPROXIMATE`: a named place's position.
- `SOURCE_PROVIDED`
- `GIS_RESOLVED`: reserved for the future engine.
- `HUMAN_CORRECTED`
- `QC_APPROVED`
- `UNRESOLVED`

The console draws an approximate location as a hollow marker, labels it, and
explains it. **An event whose location is approximate cannot be approved**: a
reviewer places it first ("Correct location"). Approval records `QC_APPROVED`.

**Several affected locations.** `detection.affected_locations` lists every
place an event affects: the junctions an article names in its headline or
summary, or the streets an official source lists. Each carries its own
resolution, geometry (if any), direction and closure. A name that cannot be
placed stays a name, `UNRESOLVED`. The drawn geometry is still one per
event (the first located place, or the source's own).

**GIS Resolution Engine: the interface only.** `services/gis_resolution`
defines the engine's contract (`resolve` returns one result per affected
location) and the rules for applying it. Source-provided, reviewer-corrected
and QC-approved locations are never replaced; nothing unresolved is guessed.
`NullGisEngine` resolves nothing.

**More event types:** `ROAD_WORKS`, `WATERLOGGING`, `ACCIDENT`,
`SPECIAL_EVENT`, `BRIDGE_TUNNEL_RESTRICTION`, `LANE_RESTRICTION` and
`ROAD_HAZARD`, as official sources state them. The keyword rules for news are
unchanged.

## Consequences

- Hyderabad behaves as before. Its feeds, rules, place list and time zone are
  the same. The reprocess tool now uses the same classifier as live ingestion,
  which created two events on 6 October (one a false positive; see the test
  report).
- An official source's later revision of a record it already sent is not
  re-read yet. This needs an update path before official feeds are scheduled.
- Reports of the same event from several publishers are still separate
  events; merging is still held back.
- No source's terms have had a formal legal review. Licences that were read
  are `PERMITS_TESTING`, never cleared for commercial use.
