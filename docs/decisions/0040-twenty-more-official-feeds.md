# 0040 — Twenty more official feeds in six countries

**Status:** 21 October 2026. Code local, tested, for the user to push. In production
they run once named in `OFFICIAL_FEEDS_SCHEDULED_SOURCES` (see below).

## Context

The user: "we need tons of data for each country" and, asked how, "parallel agents".
The candidates came from the research of 16 October 2026
(`docs/data-sources/{europe,americas-oceania,asia-mea}-official-road-sources-2026-10-16.md`),
each marked PERMITTED there. Six agents built one region each on 21 October; every
licence and robots.txt was re-read live that day, with REI's User-Agent and at most a
few requests per host. Their notes, with the licence quotes, are in
`docs/data-sources/*-connectors-2026-10-21.md`.

## Decision

Registered in `connectors/registry.py` (`feature_feeds`), listed in their city files,
all CONNECTED, tier 1, government open data, recorded as permitted with attribution
(never as settled commercial rights: no legal review, decision 0009). Counts are one
live dry run on 21 October (records in force or upcoming, all with geometry and start
unless noted).

| Country | Source id | Licence | Kept |
|---|---|---|---|
| United Kingdom | `scotland-srwr-disruptions` | Open Government Licence v3 | 18,018 |
| Belgium | `flanders-gipod-hindrance` | Modellicentie Gratis Hergebruik v1.0 | 18,005 |
| Netherlands (new) | `nl-ndw-planningsfeed-wegwerkzaamheden` | CC0 (NDW) | 14,031 |
| Netherlands | `nl-ndw-actueel-beeld` | CC0 (NDW) | 278 (6 with an end) |
| Luxembourg (new) | `lu-cita-datex2-v36` | CC0 | 13 (start only) |
| Spain (new) | `dgt-spain-incidents` | "Creative Commons Attribution" (see below) | 1,384 |
| Spain | `barcelona-public-space-works` | CC BY 4.0 | 230 |
| Spain | `madrid-informo-incidents` | CC BY 4.0 | 10 |
| Spain | `euskadi-traffic-incidences` | CC BY 4.0 | 189 |
| Germany | `hamburg-roadworks` | dl-de/by-2-0 | 154 |
| Austria (new) | `vienna-roadworks` | CC BY 4.0 | 75 |
| Taiwan (new) | `taipei-todaywork` | Taiwan OGDL v1.0 | 850 |
| Taiwan | `new-taipei-road-excavation` | Taiwan OGDL v1.0 | 579 |
| Taiwan | `taichung-traffic-maintenance-plans` | Taiwan OGDL v1.0 | 480 |
| United States | `seattle-sdot-street-closures` | Public Domain | 112 |
| United States | `baton-rouge-road-closures` | Public Domain | 29 |
| Canada | `halifax-street-closures` | OGL – Halifax | 36 |
| Canada | `cambridge-on-road-closures` | Open Data Licence v2.0 Cambridge | 29 |
| Canada | `kitchener-traffic-closures` | OGL – Kitchener | 42 |
| Canada | `sherbrooke-travaux` | CC BY 4.0 | 33 |

New country and city entries: netherlands, luxembourg, spain (+ barcelona, madrid),
austria (+ vienna), taiwan (+ taipei, new-taipei, taichung). Each adds a Google News
RSS row, listed and never fetched, as for every entry.

How the feeds are read, in short (details in the notes):

- Personal data (contact names, phones, e-mails of people) is dropped before anything
  is stored, evidence included; fixtures use placeholders.
- Coordinates are the source's WGS84 values; Taiwan's TWD97 grid is converted by
  `connectors/official/twd97.py` (pure Python, within 1 cm of five published control
  points). Scotland's British National Grid shapes are kept as evidence, the export's
  own WGS84 point is used.
- One event per DATEX II situation (NDW, CITA, DGT); NDW's current picture leaves out
  the planned works the planned feed already holds.
- The DGT feed takes the id it was catalogued under (`dgt-spain-incidents`); the
  catalogue entry in `connectors/discovered.py` is removed.
- `connectors/official/common.py` exposes `get_with_retry` (the retrying GET) for the
  feeds that need raw bytes (NDW gzip, SRWR zip).

### Held: Spain's DGT feed

The NAP labels it "Creative Commons Attribution" (no version) and "free of charge",
but names DGT's legal notice as its condition of use, which forbids unauthorised
"reproducción, distribución, comercialización" of "este portal" unless stated
otherwise. Connected, but not proposed for the production schedule until the user
decides (or DGT confirms at nap@dgt.es).

### Not built

Traffic Wales (terms silent on commercial use: awaiting permission); TrafficwatchNI
(no coordinates); Charlotte (its licence changed to CC BY-NC-SA on 16 October);
Iowa DOT 511 (additional terms with an indemnity clause, behind a Cloudflare block);
Verkeerscentrum Vlaanderen (Lambert 72 coordinates; no projection library); Taiwan
TDX (needs a key); Servei Català de Trànsit ("No licence – No contract").

### Matching at this scale

A first real ingestion of Scotland's feed into a copy of the local database stored
its 18,000 events in about a minute, then spent over 7 minutes and 6.2 GB of memory
in the matching that follows every run (stopped by hand). `find_candidates` compared
each new event with every open event of every city and kept every compared pair in
memory: 18,000 x 31,000 pairs. Production's NYC runs (4,000 rows) already took about
70 s for the same reason.

`app/services/merge_service.py` now gives exactly the same candidates while
comparing only what can match. `compare()` finds two events anything but different
only when they are in one city, are not two records of one official source, and
share an article or link, a place or road name, or lie within 300 m. So:

- the pool is the open events of the run's own cities (`_open_events_of_cities`),
  loaded with their articles in one query and without the articles' raw content or
  the versions' snapshots (`_open_events_where`);
- events are filed per city by name, headline, link and 0.02-degree map cell
  (wider than 300 m in both directions up to 80 degrees of latitude); a new event is
  compared only with events filed under its keys or the eight cells around its own,
  in the pool's order as before; two records of one official source are skipped;
- after an automatic merge the canonical event is filed again under its new facts.

`tests/api/test_matching_scale.py` checks that a dense mix of 70 events (shared
articles, names far apart, near and far positions, two cities, unlocated events,
one official source) yields exactly the candidates that comparing every pair
yields, and that 1,550 events of a large feed are matched with fewer than 5,000
comparisons instead of about 1.2 million, in about a second.

## Volume and cost

The three largest feeds bring about 50,000 events awaiting review on their first runs
(Scotland and Flanders about 18,000 each, the Netherlands about 14,000).

## Measured (21 October 2026, real ingestion into a copy of the local database)

| Feed | Events created | First run | Peak memory | A later run |
|---|---|---|---|---|
| `scotland-srwr-disruptions` | 18,018 | 19.4 min | 0.9 GB | 28 s (all already held) |
| `flanders-gipod-hindrance` | 18,041 | 6.7 min | 1.6 GB | not measured |
| `nl-ndw-planningsfeed-wegwerkzaamheden` | 14,041 | 8.5 min | 1.0 GB | not measured |

Before the matching change the Scotland run had reached 6.2 GB after 7 minutes in
matching and was stopped. The scheduler polls one source at a time, so the first
round after these feeds are scheduled holds the other feeds back for about half an
hour, once; later runs only compare what is new.

Tests: 1,436 backend passed (2 skipped), 158 frontend, tsc and eslint clean.
