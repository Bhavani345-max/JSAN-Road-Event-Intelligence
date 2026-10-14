# Google News RSS (discovery) — blocked by its terms

- **Source ids:** `google-news-rss-<city>`, one per configured city · **Class:** DISCOVERY · **Tier:** 4
- **Endpoint:** `https://news.google.com/rss/search?q=<query> when:7d&hl=<lang>-<CC>&gl=<CC>&ceid=<CC>:<lang>`
- **Connector:** `connectors/discovery/google_news_rss.py`
- **Status:** BLOCKED. Never fetched.

## Why it is blocked

Every feed carries this notice (read 6 October 2026):

> This XML feed is made available solely for the purpose of rendering Google
> News results within a personal feed reader for personal, non-commercial use.
> Any other use of the feed is expressly prohibited.

news.google.com's robots.txt also disallows automated access outside a short
allow-list that does not include `/rss`. REI's use is neither personal nor a
feed reader, so the source is registered with terms `RESTRICTED` and
commercial use `NOT_PERMITTED`.

## What was built anyway

The connector is complete and tested on a saved feed
(`backend/tests/fixtures/google_news_rss_sample.xml`):

- one feed per search from the city's configuration, in its country and
  language;
- a pause between requests, and polling every six hours;
- a refusal (429, 503) stops the poll;
- results naming another city, or not in Latin script, are left out;
- the same result from several searches is one record;
- a headline already held from any source is not stored again.

It stores the headline, publisher and publication time only. Google's link
leads to a page that runs only script, so the article itself cannot be read
from it by documented means.

`GOOGLE_NEWS_RSS_ENABLED=true` switches it on. Do that only with written
permission from Google, or a legal opinion that REI's use is allowed.
