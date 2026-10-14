# Data sources

The application holds **real source data only**. There are no demo or seeded
events: every event comes from a connected source and the evidence stored
from it.

## Connected

| Source | Type | Tier | Feed window | Details |
| --- | --- | --- | --- | --- |
| Telangana Today (Hyderabad section) | RSS | 4 | about two weeks | [telangana-today.md](telangana-today.md) |
| The Hindu (Hyderabad city feed) | RSS | 4 | about two days | [the-hindu.md](the-hindu.md) |
| Deccan Chronicle (Telangana section) | RSS | 4 | under a day | [deccan-chronicle.md](deccan-chronicle.md) |
| NewsMeter (Hyderabad section) | RSS | 4 | about ten days | [hyderabad-source-research.md](hyderabad-source-research.md) |
| The Hans India (Hyderabad section) | RSS | 4 | under three hours | [hyderabad-source-research.md](hyderabad-source-research.md) |
| Mid-Day (Mumbai section) | RSS | 4 | about 20 hours | [../cities/mumbai-source-research.md](../cities/mumbai-source-research.md) |
| The Hindu (Bengaluru city feed) | RSS | 4 | about five days | [../cities/bengaluru-source-research.md](../cities/bengaluru-source-research.md) |

| Google News search (Serper.dev) | API | 4 | past week | [google-news-search.md](google-news-search.md) |

**Disconnected on 14 October 2026:** The Siasat Daily (Hyderabad section and
Mumbai tag). Its terms allow personal, non-commercial use only and forbid
automated access without written permission, so REI no longer reads its feeds,
its article pages (also when a Google search result links to one) or sends its
articles to an AI model. The articles stored before then are kept as evidence.
See [decision 0024](../decisions/0024-siasat-disconnected-by-its-terms.md).

Official sources of the international test cities (since 6 October 2026),
connected but run by hand during the test phase:

| Source | City | Class | Tier | Details |
| --- | --- | --- | --- | --- |
| Transport for London road disruptions | London | Official | 1 | [tfl-road-disruptions.md](tfl-road-disruptions.md) |
| City of Toronto road restrictions | Toronto | Official | 1 | [toronto-road-restrictions.md](toronto-road-restrictions.md) |
| Mumbai Traffic Police notifications (no coordinates; events located by named place) | Mumbai | Official | 1 | [mumbai-traffic-police-notifications.md](mumbai-traffic-police-notifications.md) |
| Bengaluru Traffic Police website: upcoming events and works (no coordinates) | Bengaluru | Official | 1 | [bengaluru-traffic-police-website.md](bengaluru-traffic-police-website.md) |

Google News RSS is built but **blocked by its own terms**; see
[google-news-rss.md](google-news-rss.md). Every source's class, cost, limits
and terms: [global-free-source-research.md](../global-free-source-research.md)
and [data-source-cost-model.md](../data-source-cost-model.md).

The Google News search needs `SERPER_API_KEY`; without it, it is not connected.
The six feeds run on the same generic connector (`connectors/rss/base.py`); each is a
definition file plus one line in `connectors/registry.py`. See
[decision 0004](../decisions/0004-multiple-rss-sources.md).

Live result on 2 October 2026:

| Source | Articles stored | Candidate events |
| --- | --- | --- |
| Telangana Today | 500 | 16 |
| The Hindu | 60 | 0 |
| Deccan Chronicle | 60 | 0 |
| The Siasat Daily | 40 | 1 |
| NewsMeter | 60 | 1 |
| The Hans India | 29 | 0 |

## Researched, not connected

Twenty-three further sources were investigated: police and traffic
authorities, GHMC, HYDRAA, rainfall and weather sources, road authorities,
transport operators, other news feeds and commercial traffic providers. The
full record, source by source, is in
**[hyderabad-source-research.md](hyderabad-source-research.md)**. Mumbai's
and Bengaluru's sources (7 October 2026) are in
[../cities/mumbai-source-research.md](../cities/mumbai-source-research.md) and
[../cities/bengaluru-source-research.md](../cities/bengaluru-source-research.md);
the ones not connected (BMC, MMRDA, MSRDC, Mumbai Police press notes, BBMP /
GBA, ASTraM, BMRCL, and the Hindustan Times, Times of India, Indian Express,
TV9 Kannada and Deccan Herald feeds) are in the registry with the reason.

In short: no Hyderabad authority publishes road closures or advisories in a
machine-readable form. They are in the registry with a status of `DISCOVERED`,
`MANUAL_ONLY`, `REQUIRES_ACCESS` or `NOT_USABLE`, are never fetched, and are
not shown in the console as sources.

## Source registry

Every source, connected or not, is declared in code (`connectors/registry.py`,
`connectors/discovered.py`), copied to the `sources` table on start-up, and
returned by `GET /api/sources`. Fields: `source_id`, `source_name`,
`organization`, `authority_type`, `source_tier`, `source_type`, `source_url`,
`endpoint`, `access_method`, `integration_status`, `active`,
`polling_frequency_minutes`, `language`, `events_supported`, `parser_type`,
`terms_reviewed`, `evidence_retention`, `notes`, plus the polling state
(`last_poll_at`, `last_success_at`, `last_failure_at`, `last_error`).

## Rules for adding a source

- Record the source in the registry; do not fetch from anywhere else.
- Only a `CONNECTED` source can be active. The model rejects anything else.
- Assign a tier only on evidence of what the organisation is. A commercial
  provider has no tier until it is an approved source.
- Do not record an endpoint that has not been fetched successfully.
- Credentials come from environment variables (see `.env.example`), never
  from source code.
- Check the publisher's terms of use before redistributing its content, and
  set `terms_reviewed` only when that has actually been done.
