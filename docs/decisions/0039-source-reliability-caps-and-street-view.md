# 0039 — Sources keep working, no test-phase limits, more feeds, Street View

**Status:** 21 October 2026. Code local, tested, for the user to push. Production
variables set with the user's approval (see below); they take effect at the next
deploy (Railway had a platform outage with builds paused when they were set).

## Context

The user: "check all sources and APIs", "a lot of sources aren't working, all should
run in cron properly", "remove all caps", "we need tons of data for each country",
"add Street View".

What the check found (21 October 2026):

- Production (commit 0e280a8): every source it polls succeeded on its latest run.
  Recent failures were brief and fixed themselves at the next run: Bison Futé
  (connection reset, server disconnected), Main Roads WA (one dropped request), and
  TfL twice answering HTTP 200 with a GeoJSON object (keys crs, features, type)
  instead of its list of disruptions.
- A dry run of every connected connector from this machine (one fetch each, nothing
  stored): 31 of 33 fine; DiaLog answered 503 (its server asking to wait) and
  Minnesota's WZDx feed 504 after 61 s (its gateway), both on the source's side.
- What looked like "not working" in the console were mainly 16 connected feeds that
  production did not schedule (US work zones, Japan, Belgium, Germany), and the
  catalogue of sources that are not connected on purpose (terms, permission, no feed).
- Limits left from the first test phase (6 October): TfL and Toronto kept at most 30
  records a run (`OFFICIAL_FEED_MAX_RECORDS` 30); every official feed dropped planned
  closures starting more than 7 days ahead (`UPCOMING_WINDOW`). Google News search
  asked for 10 results a search, read at most 120 pages a poll, and looked up at most
  60 credits of places a day.
- Serper credits: 1,183 left, about 240 used a day (production and the local machine
  share the key).

## Decision

- **Retry:** `connectors/official/common.py` `_get`: a dropped connection, a timeout or
  HTTP 500/502/504 is tried once more after 3 s before a run fails; a refusal
  (429, 503) is not retried (the source asked REI to wait). Used by `fetch_json` and
  `fetch_text`, so by every official feed.
- **TfL:** an answer that is not the list (the GeoJSON object) is asked once more after
  5 s; the failure note says what TfL sent (`_unexpected_body_detail`).
- **No record limit:** `OFFICIAL_FEED_MAX_RECORDS` defaults to 0 (every record), as all
  other official feeds already did; TfL now keeps ~128 disruptions, Toronto all.
- **A year ahead:** `UPCOMING_WINDOW` 365 days (was 7): a planned closure is stored as
  soon as its source lists it. Ended records are still not stored.
- **Google News search:** 100 results a search (2 credits; five times the results per
  credit), every new page read (`MAX_ARTICLE_PAGES_PER_POLL` None), place look-ups
  with no daily limit unless `PLACE_LOOKUP_DAILY_CREDITS` sets one (0 = none). This
  roughly doubles credit use: with 1,183 credits left, the key runs out in about two
  to three days unless credits are bought (USD 50 for 50,000 at serper.dev); when
  they run out, Serper refuses and the searches show as failing.
- **New feeds (WZDx):** City of Austin (CC0 in its feed_info, 2,666 work zones on
  21 October) and SFMTA San Francisco (CC0 1.0 in the dataset's licence on DataSF,
  dataset 4ftp-yz2f; 3,524 closures). `WzdxFeed` gained `listed_on` and
  `licence_note`.
- **Street View:** the event panel has "Street View" and "Google Maps" buttons at the
  event's map point (Google's documented Maps URLs: no key, no cost); for an
  approximate point it says the panorama may not show the exact spot.

### Production (approved by the user, 21 October 2026)

- `OFFICIAL_FEEDS_SCHEDULED_SOURCES`: all 30 permitted official feeds (the 14 before,
  13 WZDx feeds incl. Austin and SFMTA, Tokushima, Brussels, Hamburg). Finland
  (robots.txt) and Roads ACT (commercial use not stated) stay held, by the user's
  choice.
- AI reading on: `OPENROUTER_API_KEY`, `AI_MODEL`, `AI_REASONING`,
  `AI_DAILY_REQUEST_LIMIT` copied from the local `.env` (values never printed). The
  free key's ~50 requests a day are shared with the local machine.
- Set at 10:5x UTC; `railway redeploy` answered "Deploys have been paused
  temporarily": Railway's status page reported a major outage (dashboard, API and CLI
  unavailable, builds paused in all regions). The variables apply at the next deploy.

## Not done here

- New connectors for other countries: being built separately (see the follow-up
  decision).
- Serper credits: buying them is the user's.
