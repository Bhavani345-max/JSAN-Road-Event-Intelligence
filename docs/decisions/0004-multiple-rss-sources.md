# 0004 — Multiple RSS sources: one connector, per-source configuration, no merging

**Status:** accepted, 2 October 2026

## Decision

- Every RSS source is read by the same `RssConnector`. A source is a
  `SourceDefinition` (id, name, URL, polling frequency) in its own file under
  `connectors/rss/`, registered with `_rss(...)` in `connectors/registry.py`.
  Source files contain configuration only; a test fails if one starts to fetch
  or parse.
- All sources share the ingestion pipeline, the evidence store, the keyword
  rules and the canonical event. There is no per-source event model.
- Duplicate detection is per source: `(source_id, item id)`. The same story in
  two newspapers is two artifacts and, if relevant, two events.
- Events about what may be the same real-world event are **not** merged.

## Why

Adding The Hindu and Deccan Chronicle took two definition files and two
registry lines, with no change to the connector, the pipeline, the database
or the API. Keeping each report as its own evidence-backed event means
nothing is lost before a deliberate cross-source matching step exists, and a
wrong automatic merge cannot hide a real event.

## What did have to change

Publisher differences were absorbed by the generic code, with one exception:
Deccan Chronicle writes headlines in Title Case, which made the road-mention
pattern (it relies on capital letters) unusable on those headlines. Named-road
matching now skips text in which every longer word is capitalised. The keyword
rules themselves were not changed.

## Consequences

- Reviewers may see the same real-world event more than once, from different
  sources. Cross-source matching is a later phase.
- A source's item ids only need to be unique within that source.
