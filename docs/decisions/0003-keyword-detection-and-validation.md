# 0003 — Rule-based detection; every detected event requires validation

**Status:** accepted, 2 October 2026

## Decision

- News articles are classified by configurable keyword rules
  (`services/extraction/config/traffic_keywords.json`), not by AI.
- An article is `RELEVANT_TRAFFIC_ARTICLE` when its weighted keyword score
  reaches the threshold **and** it is within the location scope (Hyderabad).
  General words such as "procession" or "closed" only support a stronger
  match; they cannot make an article relevant by themselves.
- A relevant article becomes an event with status `VALIDATION_REQUIRED` and
  only the fields the article states. It is never approved automatically.
- An event cannot become `APPROVED`, or any live status, without a resolved
  location and a start time.

## Why

Keyword rules are transparent, cheap and easy to tune, and the matched
keywords can be shown to the reviewer. They are also imprecise: on the live
feed about 10 of 16 detections were genuinely road-related. Treating every
detection as a lead for a human, and blocking approval of unlocated events,
keeps an imprecise detector from ever publishing a road closure that is not
real.

## Consequences

- Reviewers see false positives and reject them. Rejections are recorded in
  `event_versions` and can later be used to tune the rules.
- Articles that describe a road event without the configured keywords are
  missed. Extraction of times, and better recall, are left to a later
  extraction stage (which may use AI) behind the same interface.
