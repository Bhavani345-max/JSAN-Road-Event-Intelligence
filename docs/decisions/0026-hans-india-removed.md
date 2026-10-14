# 0026 — The Hans India removed from REI

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

Making it work in production would have needed a fixed server address and the
publisher's agreement. On 14 October 2026 the user decided not to pursue that
and not to use the source: "i don't want this hans".

## Decision

- The source stays **registered without a connector** (`REMOVED_SOURCES` in
  `connectors/registry.py`), as Siasat's do: it is polled by nothing, not the
  scheduler, not `POST /api/ingestion/run?source_id=the-hans-india`, not
  `cli/ingest_source.py` or `cli/backfill.py`.
- Its definition (`connectors/rss/the_hans_india.py`, through
  `connectors/rss/models.removed_from_rei`) says `NOT_USABLE`, inactive,
  commercial use `NOT_PERMITTED`, the licence and attribution in the terms'
  own words, and why it was removed. The terms were read, not formally
  reviewed: terms status `REVIEW_REQUIRED`, `terms_reviewed` false.
- `thehansindia.com` is **not** added to `RESTRICTED_PUBLISHERS`: its terms do
  not forbid automated access, and the user asked for the source to be
  removed. So a Google News search result linking to a Hans India article is
  still downloaded, and AI reading still accepts Hans India articles: those
  stored before 14 October that it has not read yet, and search results.
  Adding `the-hans-india` to `AI_EXCLUDED_SOURCES` (or the domain to
  `RESTRICTED_PUBLISHERS`) would stop that. Production has no AI or search
  key, so this concerns local copies only.

## What is kept

Nothing stored is deleted or changed: the feed items stored since 2 October
(337 locally on 14 October) and the events derived from them (5 locally) keep
their source and statuses. The source's database row is updated from the code
definition when the API starts (`sync_registry`); its polling history stays.

Tests: `tests/api/test_restricted_sources.py`
(`test_a_removed_source_cannot_be_run_and_says_why`); the connected-source
lists in `tests/unit/test_rss_sources.py`, `tests/api/test_real_data_only.py`,
`tests/api/test_multi_source_api.py`, `tests/api/test_merging_api.py` and
`tests/integration/test_multi_source_ingestion.py`.
