# 0041 — Retry sooner when a site could not be reached

**Status:** 27 October 2026. Code local, tested, for the user to push.

## Context

The user: "some api is not working, mainly netherland sources check those".

What the check found (27 October 2026):

- NDW's two feeds (current situations, planned works) and CITA Luxembourg all
  downloaded and read correctly: 301, 13,668 and 17 records. The local scheduler
  polled both NDW feeds at 12:54–12:58 IST (planned feed: 13,457 read, 949 new,
  234 revised). Nothing in the NL/LU records would be refused by PostgreSQL but
  accepted by SQLite (NaN, NUL characters, unencodable text, column lengths).
- The "Active: failing" seen locally came from this machine's connection: on 26
  October at 11:10 IST seven feeds failed in the same second with "getaddrinfo
  failed" (the site's name could not be looked up), and on 27 October the API
  started at log-on before the network was ready (Barcelona failed the same way).
- A failed feed then waited its full polling interval before the next try: three
  hours for NDW's planned feed, twelve for Barcelona. The machine was switched off
  in between, so NDW's planned feed showed "failing" from 26 October 11:10 IST until
  27 October 12:58 IST although the feed itself was fine.

## Decision

- A poll that failed **before the site answered** (an httpx transport error: no
  network, name not found, connection refused or dropped, no answer in time;
  `connectors.base.could_not_reach`) is tried again after 15 minutes, then 30, 60
  and so on, never later than the source's own interval
  (`app.services.ingestion_service.wait_before_next_poll`). A feed polled every 15
  minutes or less is not polled more often.
- A site that **answered** waits its full interval as before, whatever it said: a
  refusal (429, 503, 403), an error page or something unreadable. REI does not ask
  a site that asked it to wait any sooner (working rule of 16 October 2026).
- Google News search (Serper) fails a poll only when every search failed, without a
  network cause, so it keeps its interval and spends no extra credits.
- The failure note says so, and the console shows it as the reason the source is
  failing: "… getaddrinfo failed. The site could not be reached; REI tries again in
  15 minutes."
- The count of misses is kept in memory. A restart forgets it; each source then
  waits its own interval, and one whose interval has passed is polled at once.

No database change, no new setting.

## Tests

`tests/api/test_unreachable_retry.py`: 15 then 30 minutes after two misses; back to
the 180-minute interval after a success; a 503 waits the full interval, also after
an earlier miss; the doubling stops at the interval; and the real readers of the
official feeds (`datex3_nl_lu.fetch_bytes`, `common.fetch_json`) count a name
lookup failure, a connect or read timeout and a dropped connection as not reached,
and 503, 429, 403 and an unreadable answer as reached.

## Not checked

Production's source status: the Railway CLI on this machine has been logged out
since the 22 October security incident and the live API needs a sign-in.

## Update, 27 October 2026 (afternoon): every source, the searches included

The user asked whether the early retry covers every country's sources (RSS feeds
included) or only the Netherlands'. The retry is the scheduler's, for every source;
it depends only on the connector passing on the network error. A test now cuts the
network for every registered connector (`tests/unit/test_every_source_retries_when_offline.py`,
74 sources: RSS news, every country's official feeds, GDELT, the city searches):
66 already passed; the 8 Google News searches (Serper) did not, because a poll whose
every search failed raised a new error without its cause. Such a poll now passes on
the network error when no search reached Serper (no credit is used then); when
Serper itself answered (429, 5xx, a refusal) the poll waits its full interval as
before.
