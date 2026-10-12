# 0005 — Real source data only; a registry that also records unconnected sources

**Status:** accepted, 2 October 2026

## Decision

- **No demo data in the application.** The seeded demo events, their source,
  the seed file, the `is_demo` column and the related API parameter and UI
  labels are removed (migration `0002`). Every event comes from a connected
  source and has stored evidence.
- **Test data stays under `tests/`.** `tests/fixtures/` holds two real
  published articles used as regression cases (Khajaguda Junction, DLF / IIIT
  Junction) and a set of invented, located events used only to exercise
  geometry handling and the map. Nothing under `tests/` is loaded by the
  application.
- **No invented values.** Confidence, severity, direction, times and geometry
  stay empty until something real establishes them. The console shows "Not
  assessed", "Not available" or "Pending" instead.
- **The source registry records researched sources too.** Each source has an
  `integration_status`: `CONNECTED`, `DISCOVERED`, `MANUAL_ONLY`,
  `REQUIRES_ACCESS` or `NOT_USABLE`. Only `CONNECTED` sources can be active,
  are polled, and appear in the console's source health and source filter.
- **Tiers.** News publishers are tier 4 (discovery-only). Government, police
  and road authorities are tier 1; transport operators tier 2. Commercial
  providers have no tier until one is approved.
- **Search covers the evidence.** `GET /api/events?q=` searches the event, its
  source and the full text of the stored article.

## Why

Demo events mixed with operational events inflate counts and can be mistaken
for real ones; hiding them with a filter would leave them in the data. With
them gone the map is empty, which is the honest state: no event has a
confirmed location until GIS resolution exists.

Recording unconnected sources keeps the coverage picture in one place and
makes it explicit that, for example, the traffic police are a known source
that cannot yet be read by a program.

## Consequences

- A new installation shows no events until a source has been polled.
- The map shows nothing until events are located; the console says so.
- Text search runs in the API process over the stored evidence. That is fine
  at the PoC's volume and is to be replaced by a database full-text index.
- The scope check now also reads the dateline that opens an article body
  ("Hyderabad: …"), because Deccan Chronicle gives the city only there. A
  mention of the city elsewhere in the body does not count.
