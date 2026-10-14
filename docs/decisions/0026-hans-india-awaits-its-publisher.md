# 0026 — The Hans India disconnected until its publisher agrees

**Status:** accepted, 14 October 2026. Follows
[0024](0024-siasat-disconnected-by-its-terms.md).

## Context

The Hans India's Hyderabad feed
(`https://www.thehansindia.com/category/news/cities/hyderabad/google_feeds.xml`)
was connected on 2 October 2026 and polled every 15 minutes.

- **Production:** the feed is behind Cloudflare, which answered HTTP 403 to
  REI on Railway on every deployment since 12 October except one (about 400
  refused polls). The same request from an office connection gets 200.
  Cloudflare judges the network address a request comes from; Railway's
  changes between deployments. This was not worked around (no browser
  disguise, no proxies, no redeploying for a luckier address).
- **Terms:** https://www.thehansindia.com/pages/terms-conditions (found by the
  research of 8 October, read again 14 October 2026): "Users are prohibited
  from ... using any content available on or through the Site for commercial
  or public purposes. HMHL grants you a limited license to access and make
  personal use of this site but not for commercial purposes. We permit the use
  of materials on this website subject to due credit is given to HMHL." There
  is no clause on robots or automated access, and robots.txt allows the feed.
  The source research of 2 October said no terms page was found; that was
  wrong, and on 14 October it was repeated in the production note and to the
  user before being corrected.

The user decided to write to The Hans India and, in the meantime, to stop
using the source: "remove that hans india source if it works when we really
sends email".

## Decision

- The source stays **registered without a connector**
  (`AWAITING_PUBLISHER_SOURCES` in `connectors/registry.py`), as Siasat's do:
  it is polled by nothing, not the scheduler, not
  `POST /api/ingestion/run?source_id=the-hans-india`, not
  `cli/ingest_source.py` or `cli/backfill.py`.
- Its definition (`connectors/rss/the_hans_india.py`, through
  `connectors/rss/models.awaiting_publisher`) says `TERMS_REVIEW_REQUIRED`,
  inactive, terms `REVIEW_REQUIRED`, commercial use `NOT_PERMITTED`, the
  licence and attribution in the terms' own words, and why it was
  disconnected. `terms_reviewed` stays false.
- Unlike Siasat, `thehansindia.com` is **not** added to
  `RESTRICTED_PUBLISHERS`: its terms do not forbid automated access, and the
  user asked only for the source to be removed. So a Google News search result
  linking to a Hans India article is still downloaded, and AI reading still
  accepts Hans India articles: those stored before 14 October that it has not
  read yet, and search results. Adding `the-hans-india` to
  `AI_EXCLUDED_SOURCES` (or the domain to `RESTRICTED_PUBLISHERS`) would stop
  that; it is for the user to decide. Production has no AI or search key, so
  this concerns local copies only.

## What is kept

Nothing stored is deleted or changed: the feed items stored since 2 October
and the events derived from them keep their source and statuses. The source's
database row is updated from the code definition when the API starts
(`sync_registry`); its polling history stays.

## Reconnecting

When The Hans India agrees (permission for REI's use and, for production, an
allowed fixed server address such as Railway's Static Outbound IPs), record
their answer here, move `THE_HANS_INDIA` back to `CONNECTED_SOURCES` with its
plain `news_rss_source` definition, and restore it in the shared test
fixtures (`tests/support.py`).

Tests: `tests/api/test_restricted_sources.py`
(`test_a_source_awaiting_its_publisher_cannot_be_run_and_says_why`); the
connected-source lists in `tests/unit/test_rss_sources.py`,
`tests/api/test_real_data_only.py`, `tests/api/test_multi_source_api.py`,
`tests/api/test_merging_api.py` and
`tests/integration/test_multi_source_ingestion.py`.
