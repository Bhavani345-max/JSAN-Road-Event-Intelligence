# Google News search (Serper.dev)

- **Source id:** `google-news-serper` · **Type:** API · **Tier:** 4, discovery-only
- **Endpoint:** `POST https://google.serper.dev/news` (key in `SERPER_API_KEY`)
- **Connector:** `connectors/api/serper_news.py` · **Deeper sweep:** `apps/api/search_sweep.py`
- **Status:** CONNECTED when `SERPER_API_KEY` is set in `.env`; otherwise listed
  as REQUIRES ACCESS and never called.

## What it is

Serper returns Google News results for a search: headline, snippet, link,
publisher name and a relative date ("3 days ago"). It is a way to *find*
Hyderabad road articles from publishers whose feeds are not connected (The
Times of India, Hyderabad Mail, The New Indian Express, Urban Acres, …). It is
not a source of road events itself.

For each new result REI reads the article from the publisher's page (the
schema.org NewsArticle data, as for `apps/api/backfill.py`) and stores that
article as evidence, with the search result that led to it. If the page
carries no readable article, the search result alone is stored. Either way the
article then goes through the same detection, place and review steps as a
feed item.

## What Serper costs

Checked on 6 October 2026 against Serper's published pricing:

- Every new account gets **2,500 free credits**, with no card. There is no
  monthly free allowance after that; the next step is a paid pack
  (50,000 credits for USD 50, valid six months).
- A news search costs **1 credit for up to 10 results** and 2 credits for
  11–100 results.

REI's settings: 12 searches of the past week, every 8 hours — **36 credits a
day**, so the free credits last about two months of polling. A month-wide
sweep (`python apps/api/search_sweep.py`) costs 12 credits each time it is
run. With a paid pack the same polling costs about a dollar a month.

## Verified on 5 and 6 October 2026

- One query returns at most 10 results and costs 1 Serper credit.
- A plain search ("Hyderabad traffic diversions", past week) returned mostly
  Delhi, Bengaluru, Pune and Chennai articles: Google ranks the big cities'
  road news above Hyderabad's even when Hyderabad is the search term. Leaving
  those cities out of the search (`-Delhi -Bengaluru -Mumbai …`) and asking
  for the past month turned the same search into ten Hyderabad road articles
  out of ten (Ganesh immersion diversions, roads blocked around Tank Bund,
  the Khajaguda junction diversions, …).
- `site:` searches do not work in the news endpoint: they return a
  publisher's tag pages, without dates.
- Up to 6 October, with the earlier searches, 79 results had been stored and
  5 had become events. The month-wide sweep with the new searches on
  6 October brought 51 results, 36 new articles, 15 detected as road
  articles and 12 new events. Most of them describe measures that have since
  ended (the September Ganesh immersion diversions), so they are stored but
  not shown in the console.

## The searches

Each search names Hyderabad (or Secunderabad, Cyberabad, Rachakonda or the
GHMC) and one kind of measure in the words the papers use: diversions and
restrictions, traffic police advisories, roads closed or blocked,
waterlogging, flyover and ORR closures, GHMC/HYDRAA road works, processions
and festivals, VIP visits, Metro works, one-way systems and traffic alerts.
The eight cities that crowd Hyderabad out are excluded from every search.
The list is `DEFAULT_QUERIES` in the connector.

Before anything is stored, a result is left out if its headline names
another city (and not Hyderabad), if it does not mention Hyderabad at all,
or if its headline is not in Latin script.

## Windows

- Scheduled polls search the **past week**: enough to catch a new advisory
  within a day of publication.
- `python apps/api/search_sweep.py --window month` runs the same searches
  over the **past month** (or `year`, `week`, `day`), for measures announced
  earlier but still running. `--results 20` asks for 20 results a search at
  two credits each. Articles already held are not stored again.

## Limits

- Results come from any publisher Google lists. Their reliability is not
  assessed; the console shows the site each article is on.
- Google's dates are relative. The article's own publication time is used when
  its page states one.
- An article already stored from its publisher's feed is not stored again.
- Terms of use (Serper, Google, and each publisher) have not been reviewed.
- How many events a week this yields depends on what Hyderabad's papers
  publish, not on the number of searches. In the week to 6 October 2026 the
  papers reported few new road measures; the sweep's finds were mostly
  September's.
