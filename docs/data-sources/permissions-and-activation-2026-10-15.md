# Feed activation and permission work, 15 October 2026

Prepared for the user's review. **Nothing here has been done:** no Railway
variable changed, no feed enabled, no email sent, no key registered.

## 1. Feed activation in production (on hold)

Production polls only the six news feeds. Every official feed is registered
but inactive: `OFFICIAL_FEEDS_SCHEDULED` is not set and
`OFFICIAL_FEEDS_SCHEDULED_SOURCES` (decision 0028) is empty. Both stay
unchanged until the user approves.

### A. Ready: technically working, licence permits use, configured

Each was fetched live by its connector on 13–15 October 2026. Each needs no
key, and its licence allows use including commercial use, with attribution
(recorded per source, not a legal review). Volumes are from local runs.

| Source id | Country | Licence | Polls a day | Records a run (local) |
| --- | --- | --- | --- | --- |
| `tfl-road-disruptions` | UK | OGL v2.0 with TfL amendments | 96 | 30 (capped by `OFFICIAL_FEED_MAX_RECORDS`) |
| `nyc-street-closures` | US | NYC Open Data terms | 1 | about 3,600 rows → about 2,300 events after row merging |
| `toronto-road-restrictions` | CA | OGL – Toronto | 48 | 30 (capped) |
| `drivebc-events` | CA | OGL – British Columbia | 48 | 276 |
| `ottawa-traffic-events` | CA | OGL – City of Ottawa | 48 | 128 |
| `edmonton-traffic-disruptions` | CA | OGL – Edmonton | 4 | 122 |
| `winnipeg-lane-closures` | CA | OGL – Winnipeg | 2 | 600 |
| `calgary-construction-detours` | CA | OGL – Calgary | 2 | 215 |
| `france-bison-fute-road-events` | FR | Licence Ouverte 2.0 | 24 | 658 records → about 546 events after situation merging |
| `france-dialog-traffic-orders` | FR | Licence Ouverte 2.0 | 4 | 477 |
| `lyon-disruptive-works` | FR | Licence Ouverte 2.0 | 2 | 361 |
| `main-roads-wa-webeoc` | AU | CC BY 4.0 | 48 | 230 |
| `gold-coast-temporary-road-closures` | AU | CC BY 3.0 | 2 | 606 |
| `wodonga-roadworks` | AU | CC BY 4.0 | 2 | 15 |

### B. Connected, held for the user's decision

| Source id | Why held |
| --- | --- |
| `roads-act-planned-closures` (AU) | CC BY-SA 4.0: commercial use allowed, but adapted data must be shared under the same licence. |
| `finland-digitraffic-road-events` (FI) | robots.txt `Disallow: /api/` (section 4). |

### C. Not connected (needs a key, permission or an answer)

QLDTraffic, Transport for NSW, Victoria DTP (section 2); Western Cape and
SANRAL (section 3); Montréal (section 3); Québec MTMD (section 4); Ontario,
Alberta, Manitoba, New Brunswick and Yukon 511, National Highways, 511NY,
Street Manager, Grand Lyon real-time and Bison Futé "Action b"
(keys or accounts, research of 14 October).

### The variable, when approved

Service `JSAN-Road-Event-Intelligence` (the API), environment `production`:

```
OFFICIAL_FEEDS_SCHEDULED_SOURCES=tfl-road-disruptions,nyc-street-closures,toronto-road-restrictions,drivebc-events,ottawa-traffic-events,edmonton-traffic-disruptions,winnipeg-lane-closures,calgary-construction-detours,france-bison-fute-road-events,france-dialog-traffic-orders,lyon-disruptive-works,main-roads-wa-webeoc,gold-coast-temporary-road-closures,wodonga-roadworks
```

`OFFICIAL_FEEDS_SCHEDULED` stays unset. To include the held sources later,
add `roads-act-planned-closures` and `finland-digitraffic-road-events`.

Expected impact:

- **Requests:** a restart of the API (Railway redeploys on a variable change,
  about 1 minute). Then about 330 polls a day across 14 hosts, mostly
  TfL (every 15 minutes) and four feeds every 30 minutes. Each poll is one
  to four requests.
- **New events:** within an hour, about 2,200 new events in the review
  queue: Canada about 1,340 and Australia about 850.
  - The NYC, French, TfL and Toronto feeds are already stored in production
    (imported 13 October); their runs add only records not yet held.
  - The row merges then take about 1,400 duplicate rows out of the queue
    (NYC about 1,290, Bison Futé about 112).
- **Storage:** about 30 MB more (production: 84 MB of data for 5,148 events,
  about 13 KB an event with its evidence). The volume uses 1.09 GB of 50 GB.
- **The operations map** is unchanged until events are approved.
- **Undo:** remove the variable; the feeds stop at the next restart. Stored
  evidence stays.

## 2. API keys needed (not registered)

| Source | Where | What the key needs | Notes |
| --- | --- | --- | --- |
| QLDTraffic (Queensland) | [Developer specification](https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api) | Either the **public key printed in the specification** ("for developers who do not wish to register", 100 requests a minute shared by all its users) or a registered key | 529 events on 15 Oct (459 current), CC BY 4.0, includes some NSW records. A connector is not written yet. |
| Transport for NSW Live Traffic | [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au/) (account, then an API key) | Registration; default plan 60,000 calls a day, 5 a second | CC BY 4.0, "on the condition that Transport for NSW is attributed". A connector is not written yet. |
| Victoria DTP road disruptions | [opendata.transport.vic.gov.au](https://opendata.transport.vic.gov.au/dataset/unplanned-disruptions-road) (account, `KeyID` header) | Registration | CC BY 4.0. About 8,200 Victorian records. A connector is not written yet. |

Keys would go in Railway variables (never in code), with a connector built
and tested first.

## 3. Drafts (not sent)

### 3.1 Western Cape Government: commercial reuse of the road closures layer

**To:** service@westerncape.gov.za  **Cc:** PDO@westerncape.gov.za
**Subject:** Request: permission to reuse the Public Road Closures map layer

> Dear Western Cape Government team,
>
> JSAN Consulting is developing JSAN Road Event Intelligence (REI), a platform
> that brings together official information on road closures, roadworks and
> traffic restrictions from road authorities, with each record attributed to
> its source.
>
> We would like to include the Department of Infrastructure's public road
> closures layer
> (https://gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer).
> The layer carries no licence, and the Western Cape Government's terms say
> commercial reuse may be granted on written request. We therefore ask:
>
> 1. May REI read this layer automatically (a few requests an hour) and show
>    the closures, with their source, to its users, including commercial use?
>    If so, which attribution wording should we use?
> 2. Alternatively, could the layer be published on the Western Cape
>    Government Open Data Portal under an open licence (as other layers there
>    are, CC BY)? (Copied to PDO@westerncape.gov.za, per the Open Data Policy.)
> 3. Many closures are listed without an end date. Is there a planned end
>    date we could read, or should these be treated as in force until removed?
>
> We will not use the layer until we hear from you.
>
> Kind regards,
> [Name], [Role], JSAN Consulting, [email], [phone]

### 3.2 SANRAL: i-TRAFFIC developer key and redistribution consent

**To:** via https://www.i-traffic.co.za/contact
**Subject:** Developer key and written consent for i-TRAFFIC road events

> Dear SANRAL i-TRAFFIC team,
>
> JSAN Consulting is developing JSAN Road Event Intelligence (REI), a platform
> that brings together official road closure, roadworks and incident
> information, each record attributed to its source.
>
> We would like to use the i-TRAFFIC API (GetEvents) for national roads, within
> the published limit of 10 calls every 60 seconds. Your terms prohibit
> redistribution or republication without SANRAL's written consent, so we ask:
>
> 1. Could you issue a developer key for REI?
> 2. Would SANRAL give written consent for REI to show i-TRAFFIC events to its
>    users, including commercial use, and on what conditions (attribution,
>    delay, fees)?
>
> We will not access the API until we have your answer.
>
> Kind regards,
> [Name], [Role], JSAN Consulting, [email], [phone]

### 3.3 Ville de Montréal: time format of "Entraves et travaux en cours"

**To:** donneesouvertes@montreal.ca
**Subject:** Question sur le format des dates, jeu « Entraves et travaux en cours » / Date format question

> Bonjour,
>
> Nous utilisons le jeu de données « Entraves et travaux en cours »
> (https://donnees.montreal.ca/dataset/info-travaux). Dans le fichier
> entraves-travaux-en-cours.csv, les champs duration_start_date et
> duration_end_date sont écrits en UTC (suffixe Z). Toutefois, chaque début est
> à 20:00:00Z (19:00:00Z en hiver) et chaque fin à 19:59:59Z (18:59:59Z).
>
> Pourriez-vous confirmer comment lire ces valeurs ? Par exemple, est-ce que
> « 2026-10-04T20:00:00Z » signifie le 5 octobre à 00 h, heure de Montréal ?
> Les permis valent-ils pour des journées entières ?
>
> Merci,
> [Nom], JSAN Consulting, [courriel]
>
> ---
>
> Hello, in the file entraves-travaux-en-cours.csv every start is at 20:00:00Z
> (19:00:00Z in winter) and every end at 19:59:59Z (18:59:59Z). Could you
> confirm how to read these values (for example, does 2026-10-04T20:00:00Z mean
> 5 October 00:00 Montréal time) and whether permits cover whole days?
> Thank you.

## 4. Robots.txt restrictions (unresolved)

| Source | What robots.txt says | What the terms say | Status |
| --- | --- | --- | --- |
| Fintraffic Digitraffic (Finland), `tie.digitraffic.fi` | `User-agent: *` / `Disallow: /api/` (checked 14 October 2026) | CC BY 4.0, "even commercially". The documentation describes the API for programmatic use. | Connected since 13 October, **not scheduled**. 564 events stored (local and production). |
| Québec MTMD map server, `ws.mapserver.transports.gouv.qc.ca` | Could not be read: a Cloudflare challenge answers instead (15 October 2026) | CC BY 4.0 | **Not connected.** 526 works and 19 warnings with lines seen on 15 October. |

Options for the user:

- Finland: (a) treat robots.txt as aimed at crawlers and keep using the
  documented API; (b) ask Fintraffic to confirm (support contact on
  digitraffic.fi); or (c) stop using it.
- Québec: (a) ask the Ministère des Transports for written confirmation and
  for a robots.txt readable without a challenge; or (b) leave it unconnected.

REI does not bypass either restriction.
