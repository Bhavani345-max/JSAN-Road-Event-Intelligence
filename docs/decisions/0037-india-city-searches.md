# 0037 — Google News search for every Indian city, and the key in production

**Status:** 19 October 2026. The production key is set (the user's approval);
the code is local, tested, and left for the user to push.

## Context

After decision 0036 was deployed, the user reported that about 34 Indian
sources show as not connected and India gets almost no events, with people
asking why.

What the check found (19 October 2026):

- 71 sources are registered for India. Only three are collected: Telangana
  Today, NewsMeter and the Google News search (Hyderabad). The other 68 are a
  catalogue recorded on purpose, each with its reason on screen: publisher terms
  forbid automated use (16, e.g. Siasat, The Hindu, Mid-day, Google News RSS),
  research found no feed or service (21: researched or manual only), waiting for
  the publisher's permission because the terms are silent (10), removed by the
  user or giving no location (9), switched off (GDELT, 8), unreachable sites (3),
  a key REI does not have (1). None of these is broken.
- In production only two Indian feeds ran: `SERPER_API_KEY` was not set on
  Railway, so the Google News search, which finds most Hyderabad events
  locally, never ran there. Production held about 9 Indian events on the review
  map, with about 2 new ones a day.
- The other Indian cities (Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Pune,
  Ahmedabad) had place lists and searches configured (decision 0033) but no
  search source using them.

## Decision

- **Production key** (approved by the user): `SERPER_API_KEY` set on the API
  service on 19 October 2026 at 08:18 UTC, from the local `.env` through
  `railway variable set --stdin` (the value was never printed). Railway
  redeployed; the first production search ran at 08:19 UTC: 17 results, 15
  new, 7 events.
- **A search per city:** `google-news-serper-<city>` for each Indian city with
  a place list and searches of its own (`searched_cities()`), on the same key,
  once a day (`CITY_POLLING_FREQUENCY_MINUTES` 1440), a past-week window, the
  city's own searches (no cities left out: leaving out the other large cities
  cut Mumbai's and Ahmedabad's results to a few), results kept only if they name
  the city (short names such as "MCD" as whole words) and dropped if the
  headline names another city instead. Each city's events use its own place
  list and rules. Hyderabad's search is unchanged.
- **Article pages** (the user's choice): the city searches read the article
  pages as Hyderabad's search does, because Google's headline and snippet
  rarely state a date and an event without a stated start is not shown.
  Publishers whose terms forbid automated access (`RESTRICTED_PUBLISHERS`) and
  publishers the user removed (`REMOVED_PUBLISHERS`, The Hans India) are left
  out of every search, Hyderabad's included, result and page alike. A stricter
  mode (`read_any_publisher=False`: pages only from `READABLE_PUBLISHERS`)
  remains in the code.
- The eight feeds awaiting permission (New Indian Express x6, Millennium Post
  x2) stay off (the user's choice: wait for permission).

## Measured (live, 19 October 2026)

- Headline-only trial on the local database: 7 city searches, 166 new articles,
  38 located road-event leads (Delhi 10, Mumbai 9, Bengaluru 6, Ahmedabad 5,
  Pune 5, Kolkata 2, Chennai 1), none with a stated start.
- Reading pages (Delhi, Mumbai, Pune, on a copy of the database from before the
  trial): 29 events. One was shown at once. The rest describe past events
  (13 or 16 October), state only an end ("until 20 October"), or say a
  restriction "begins" without a date. They wait in the review queue.
- Serper credits: 1,855 at the start of the day. Production now uses about 36 a
  day for Hyderabad and about 61 for the other cities, plus place look-ups (at
  most 60 a day). The local API uses the same key.

## Not done here

- The display rule is unchanged: an event needs a location and a stated start
  to be shown. Reading "in place until 20 October" or "begins today" as
  starting at the article's publication is a rule change for the user to
  decide (open since decision 0033).
- The local database keeps the 38 headline-only leads of the trial (backup
  before them: `backend/.data/backups/rei-2026-10-19-before-india-city-searches.db`).
- No permission e-mails sent; no other source connected.
