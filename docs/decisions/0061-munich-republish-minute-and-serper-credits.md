# 0061 — München's republish minute, and why Serper still fails

**Status:** 6 November 2026. München: code local, tested, for the user to push.
Serper: paused in production the same day (below).

## Context

The user, 6 November 2026: "fix the 17 serper failures and investigate on
munchen failures make it works". At 16:53 IST production had 96 active sources:
78 working, 17 Serper news searches failing and `de-muenchen-roadworks` failing.

### München

Every scheduled poll of München's WFS layer since it went live, from the API
service's logs (times UTC):

| Poll | Answer |
| --- | --- |
| 5 Nov 14:12, 17:13, 20:13, 23:15; 6 Nov 02:17, 05:19 | HTTP 200, 1,120–1,128 works |
| 6 Nov 08:20:16 | HTTP 200 with an empty body ("did not return JSON") |
| 6 Nov 11:20:30 | HTTP 404 |

REI polls a source when its interval has passed since the last poll, checked
once a minute, so each 3-hourly poll starts a minute or two later than the last:
by 08:20 it had drifted onto 20 minutes past the hour, and every poll there
failed while every poll before it, and every request made by hand that day (from
this machine and from the production container, with the connector's own
parameters and user agent), worked. The layer was listed in GetCapabilities
throughout. Without a change the next polls (14:20, 17:21 …) would fail the
same way.

A probe from this machine, one request for a single record every 15 seconds from
12:18:30 to 12:26 UTC on 6 November 2026 (30 requests), showed the window is hourly
and how long it lasts: the layer answered until 12:19:48, then HTTP 404 at
12:20:03–12:20:35, the layer at 12:20:50–12:21:37, 404 at 12:21:53, the layer at
12:22:09, 404 at 12:22:24–12:22:40, and the layer at every request from 12:22:55 to
12:25:48. München's server republishes the layer from 20 minutes past each hour and
answers 404 on and off for about three minutes. The city's road works page
(stadt.muenchen.de, "Servicekarte Baustellen") draws the same Mobilitätsreferat
data from the same geoportal, so it is not a second source.

## Decision

- München's connector (`connectors/official/muenchen.py`) treats an HTTP 404 or
  an answer that is not JSON as the layer being republished: it asks again after
  60 seconds and, if needed, after a further 150, within the same run
  (`REPUBLISH_PAUSES_SECONDS`), so the last request goes at least 3.5 minutes
  after the first, past the window the probe measured. A third such answer fails
  the run as before.
- Any other failure fails at once, as before. A refusal (403, 429, 503) is never
  asked again sooner (decision 0041 stands: a site that answered waits its full
  interval).
- A run that succeeds after a pause is recorded at its own time, so the next
  3-hourly poll falls a few minutes after the republish minute and keeps drifting
  away from it.
- At most 2 extra requests and 3.5 minutes of waiting, and only when München
  answers this way. The scheduler runs one poll at a time, so other feeds wait that
  long; with the poll pushed past the window, it happens about once a week.

### Serper (no code change)

- The API service's `SERPER_API_KEY` is the same key as the local `.env` (same
  SHA-256 prefix). Serper's account endpoint answered `{"balance": -2,
  "rateLimit": 5}` on 6 November 2026: the account has no credits, which is what
  every search's "HTTP 400 (Not enough credits)" says. Nothing in REI can change
  that; only credits, or a key with credits, can.
- The free stand-in REI already has, GDELT (`GDELT_SEARCH_ENABLED`, built for the
  same 17 cities plus South Africa, terms permitting commercial use with a
  citation), was refused at its first request from the production container on
  6 November 2026: HTTP 429 "Please limit requests to one every 5 seconds".
  Railway's shared addresses are evidently over GDELT's limit already, so it is
  not a working replacement there and stays off.
- The 17 searches use about 212 credits a day when funded.
- **Paused** at the user's choice ("go with opt 2"), 6 November 2026: `SERPER_API_KEY`
  removed from the API service at 12:40 UTC (it is the switch: without it the
  searches are registered as needing access and never polled; place lookups use
  OpenStreetMap only), then a redeploy of the same code at 12:49 UTC (deleting a
  variable started none). Checked after: the 17 searches inactive, their 172 stored
  events kept, no event gone, 299 sources as before, 78 working, only München
  failing. To resume once credits are bought: set the key again from the local
  `.env` (`railway variable set SERPER_API_KEY --stdin`, which redeploys).

## Tests

`tests/unit/test_de_at_sources_2026_11_05.py`: München waits out an empty 200 and
a 404 and reads the layer on the third request, after exactly the two pauses; it
still fails after three 404s; a 403, 429 or 503 is asked only once.
