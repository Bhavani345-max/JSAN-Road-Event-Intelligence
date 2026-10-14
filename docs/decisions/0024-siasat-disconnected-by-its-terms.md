# 0024 — The Siasat Daily disconnected: its terms forbid automated access

**Status:** accepted, 14 October 2026.

## Context

Two Siasat RSS feeds (`siasat`, Hyderabad section, since 2 October;
`siasat-mumbai`, Mumbai tag, since 8 October) were connected and polled every
30 minutes. Siasat was kept out of AI reading (decision 0020), and the phase
report of 8 October flagged its terms as the user's legal call. On 14 October
the user asked for the restricted acquisition path to be disabled if the terms
do not permit it, keeping historical evidence and never sending restricted
content to an AI model.

The terms at https://www.siasat.com/terms-conditions/ (read 14 October 2026;
page metadata says last modified 19 April 2026):

- s.4.1: a licence "solely for your personal, non-commercial use";
- s.4.2: it excludes any right to "use any data mining, robots, scrapers,
  crawlers, or similar data-gathering and extraction tools", to "make any
  derivative use", and to use the content for "training, developing, or
  fine-tuning any artificial intelligence, machine learning, large language
  model, or similar system";
- Prohibited Activities: "Use any robot, spider, scraper, or other automated
  means to access, extract, or index the Content without prior written
  permission".

RSS is not mentioned. robots.txt does not disallow the feed paths, but
robots.txt is not a licence. REI's use is automated and not personal, so it is
not permitted without written permission.

Besides the two feeds, Siasat pages could be reached three other ways: a manual
run or `backfill` of the source (these checked only for a connector, not
`active`), and the Google News search source, which downloads every new
result's page from its publisher. One siasat.com page was fetched that way, on
5 October 2026. No Siasat article has been sent to an AI model: AI reading
excluded the two Siasat source ids, but not a siasat.com article stored by
another source.

## Decision

- `backend/connectors/restricted.py` lists restricted publishers by domain
  (`siasat.com`, with the clauses above) and gives `restricted_publisher(url)`.
- Both Siasat sources stay **registered without a connector**
  (`RESTRICTED_SOURCES` in `connectors/registry.py`), so they are polled by
  nothing: not the scheduler, not `POST /api/ingestion/run?source_id=…`, not
  `cli/ingest_source.py` or `cli/backfill.py` (both answer "no ingestable
  source"). Their definitions say `TERMS_REVIEW_REQUIRED`, inactive, terms
  `RESTRICTED`, commercial use `NOT_PERMITTED`, with the clauses in the notes.
  `terms_reviewed` stays false: the terms were read, not reviewed by a lawyer.
- `download_page` (single-article reader, used by the Google News search and by
  backfill) refuses a restricted host before any request and follows redirects
  one at a time, so a link elsewhere cannot lead to a request to siasat.com.
- The Google News search drops results that link to a restricted publisher
  before anything is stored.
- AI reading skips an artifact whose URL is on a restricted publisher's site,
  whichever source stored it, in addition to the excluded source ids.

## What is kept

Nothing stored is deleted or changed: 300 + 44 Siasat feed items, the one
siasat.com page from the Google News search, and the 6 events derived from them
(5 + 1; statuses as they were). The database rows of the two sources are
updated from the code definitions when the API starts (`sync_registry`); their
polling history stays. The existing retention rule still strips the text of
non-road articles after 14 days, as for every source.

## Consequences

- Reconnecting needs Siasat's written permission; record it here and remove
  the domain from `RESTRICTED_PUBLISHERS`.
- A deployment (for example Railway) keeps polling Siasat until this code is
  deployed there.
- Tests: `tests/unit/test_restricted_publishers.py`,
  `tests/api/test_restricted_sources.py`, and an AI-reading test in
  `tests/api/test_ai_reading_service.py`. The shared multi-source fixtures no
  longer include Siasat.
