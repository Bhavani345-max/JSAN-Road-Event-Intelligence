# Telangana Today (RSS)

| | |
| --- | --- |
| Source id | `telangana-today` |
| Feed | `https://telanganatoday.com/hyderabad/feed` (the publisher's Hyderabad section) |
| Format | RSS 2.0 (WordPress) |
| Polling | Every 30 minutes; the feed declares hourly updates |
| Definition | `connectors/rss/telangana_today.py` (configuration only; read by the generic RSS connector) |
| Authority type, tier | Not assigned |

## What the feed provides

About 500 items covering roughly the last two weeks. Each item has a title,
link, GUID, publication time, author, category tags, a short summary
(`description`) and the full article HTML (`content:encoded`).

## What REI does with it

1. **Fetch and parse** every item. The GUID identifies the item; an item
   already stored is skipped.
2. **Store evidence** for every new item in `source_artifacts`: URL, title,
   publication and retrieval times, the original summary and article HTML,
   and a SHA-256 content hash.
3. **Detect** traffic articles with keyword rules applied to the title and
   summary (`services/extraction/config/traffic_keywords.json`).
4. **Create an event** for each relevant article, with status
   `VALIDATION_REQUIRED`.

What an event gets from an article:

| Field | Value |
| --- | --- |
| `title` | Article title |
| `description` | Article summary (up to 600 characters) |
| `source_reference` | Article URL |
| `city` | `Hyderabad`, when the publisher tags or mentions it |
| `event_type` | Suggested only when the keywords make it clear; otherwise empty |
| `affected_road` | Road names the title or summary states verbatim (e.g. "Khajaguda junction", "NH-65"); unverified |
| `start_time`, `end_time`, `severity`, `direction`, `geometry`, `confidence` | Empty |

## Observed results

On the feed as of 2 October 2026: 500 articles stored, 16 detected as traffic
candidates. Reading the 16 titles, roughly 10 concern roads or traffic; the
rest are false positives such as festival coverage that mentions traffic in
passing. That is expected of keyword rules and is why every event starts in
human validation.

## Known limits

- Detection reads the title and summary only, so an article that mentions a
  closure only in its body is missed.
- An article edited by the publisher after ingestion is not re-processed.
- Dates and times in the text ("from September 26", "for 60 days") are not extracted.
- Several articles about the same real-world event produce several events,
  whether from this source or from different sources; there is no matching
  across articles yet.

## Terms of use

REI stores article content internally as evidence and shows the title, the
summary and a link back to the original. Review Telangana Today's terms
before any commercial redistribution of its content.
