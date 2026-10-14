# Source research, 14 October 2026: more sources for every city

The user asked to remove failing sources, fix them if possible, and add more
working sources for every location. Each candidate below was fetched live on
14 October 2026 (about 15:25-16:00 UTC) with the User-Agent
`JSAN-REI/1.0 (road event intelligence; ...)`, and its licence or terms were
read. Nothing was bypassed: no browser disguise, no proxies, no keys guessed.
Connected only when the endpoint returned real current records, needed no key,
and its terms allow REI's automated, commercial use.

## Failing sources

| Source | Where it fails | What was done |
| --- | --- | --- |
| The Hans India | Production: HTTP 403 from Cloudflare on every poll | Removed by the user's decision ([0026](../decisions/0026-hans-india-removed.md)) |

Every other connected source answered normally, locally and in production
(Railway logs of 14 October). The official feeds were not failing in
production: they were never run there, because `OFFICIAL_FEEDS_SCHEDULED` is
not set on Railway.

## Connected ([decision 0027](../decisions/0027-more-official-sources.md))

| Source | City | Endpoint | On 14 Oct | Location | Licence |
| --- | --- | --- | --- | --- | --- |
| NYC permitted events closing streets (NYC Office of Citywide Event Coordination and Management) | New York | `data.cityofnewyork.us/resource/tvpp-9vvx.json` | 179 full-closure rows of 129 events | Street names only: unlocated | NYC Open Data FAQ: "There are no restrictions on the use of Open Data." |
| DiaLog traffic orders (Ministry of Transport, DGITM) | France | `dialog.beta.gouv.fr/api/regulations/json` | 482 current + 284 upcoming temporary orders from about 50 authorities | Source lines and points | Licence Ouverte / Etalab 2.0 |
| Métropole de Lyon works disrupting traffic | France | `data.grandlyon.com/geoserver/metropole-de-lyon/ows` (layer `pvochantierperturbant`) | 417 works: 272 under way, 145 to come | Work-site polygons | Licence Ouverte 2.0 (Métropole's data.gouv.fr record) |

First local run (14 October): 74, 477 and 361 events, all awaiting
validation. DiaLog and Lyon events are all located by the source's own
geometry; NYC events stay unlocated.

## Need a free key or an access request (the user's decision)

| Source | City | What it gives | Access | Licence |
| --- | --- | --- | --- | --- |
| Ontario 511 developer API | Toronto / Ontario | Provincial events and construction (401, QEW, DVP, Gardiner) | Developer key; request states organisation and intended use; 10 calls a minute | Open Government Licence – Ontario |
| National Highways road and lane closures v2.0 | London (M25 and strategic roads) | Planned and unplanned closures, DATEX II | Free subscription key; 10 calls a minute; charges possible later with 6 months' notice | Based on OGL v2.0, commercial use allowed; "Powered by National Highways Transport Data Feeds" |
| DfT Street Manager live open data | London / England | Roadworks permits, near real time | Push to an endpoint REI would host, after registration | Open-data feed may be used commercially (OGL v3.0) |
| 511NY data feeds and NYSDOT WZDx | New York State | Traffic events, work zones | Access request form, reviewed weekly | Redistribution allowed; "powered by 511NY", publication time shown |
| Grand Lyon real-time road events | Lyon | Traffic-control events | Grand Lyon account (HTTP 401) | — |
| Bison Futé "Action b" | France (concession motorways) | Closures and works on toll motorways | Credentials (HTTP 401) | — |

## Blocked by robots.txt (a decision for the user)

The Opendatasoft portals of Paris, Rennes, Toulouse, Bordeaux, Nantes and
Loire-Atlantique serve `User-agent: * / Disallow: /api/`, and their downloads
go through `/api/`. Their data is good and openly licensed:

| Source | On 14 Oct | Licence |
| --- | --- | --- |
| Paris: works disrupting traffic (`chantiers-perturbants`) | 120 works, polygons | ODbL (share-alike) |
| Paris: planned closures of the ring road, tunnels and riverside roads (`fermetures-voirie`) | 139 records, 66 planned, lines | ODbL |
| Rennes: roadworks for the next 30 days | 499 records, lines | ODbL |
| Toulouse: roadworks under way | 1,092 records, lines | Licence Ouverte 2.0 |
| Bordeaux: works on Bordeaux and Mérignac roads | 319 records | Licence Ouverte |
| Loire-Atlantique: departmental road messages | 40 sign-panel messages, dates in text | Licence Ouverte |

Fintraffic's Digitraffic, connected since 13 October for Finland, has the same
line (`tie.digitraffic.fi/robots.txt`: `User-agent: * / Disallow: /api/`,
checked 14 October), while its terms of service license the data under CC BY
4.0 "even commercially" and its documentation describes this API for
programmatic use. Whether robots.txt binds a documented open-data API, or only
crawlers, is for the user to decide; until then Digitraffic stays connected as
before and the six portals above are not connected.

UK Power Networks' street and roadworks (CC BY 4.0) and the City of Toronto's
festivals and events file are disallowed the same way.

## Not connected, other reasons

- **Oulu traffic announcements** (City of Oulu GraphQL, freely usable): times
  carry no time zone, and the end times fit neither UTC nor Finnish time
  consistently (21:00 and 22:00 ends in both summer and winter). Not connected
  until the zone is established.
- **Mumbai Police press releases** (re-use allowed with prominent credit:
  "Material featured on this portal may be reproduced free of charge ...
  the source must be prominently acknowledged"): the notices are scanned PDFs
  that need OCR (a later phase), and the traffic ones repeat the Mumbai
  Traffic Police notifications already connected.
- **Duplicates of connected feeds:** TfL street-level disruptions (the same
  records as Road/all/Disruption); NYC DOT closures by intersection (478a-yykk)
  and by block and intersection (ezy6-djsf).
- **No exact dates or no current data:** Toronto road resurfacing and
  reconstruction (quarter-year timelines), Toronto utility cut permits
  (addresses not the work's location), Street Manager monthly archives (a
  month old, about 1 GB each), The Gazette road traffic notices (dates only in
  the notice text; mostly permanent orders), NYC Open Streets (nothing
  current), Digitraffic weight restrictions (none in force; seasonal).
- **Indian news publishers** (Hyderabad Mail, Citizen Matters, Mumbai Live,
  Lokmat, Bangalore Mirror, New Indian Express, TV9 Kannada, The News Minute,
  Deccan Herald, Hindustan Times, Free Press Journal): every one restricts
  automated or commercial use (personal, non-commercial use only; no robots,
  scrapers or data mining; viewing only).
- **Indian official sites:** Hyderabad Traffic Police, the Malkajgiri
  (formerly Rachakonda) Police and MMRDA allow re-use only after permission by
  email, and had no current road events; Hyderabad City Police press notes
  stop at 23 December 2025; Bengaluru's GBA/BBMP sites are JavaScript-only or
  unreachable; data.gov.in's robots.txt now disallows everything.

## Access-rule slips during this research

The research agents made a few requests before reading a site's rules:
about six requests to The Gazette during UK business hours (its fair-use
policy asks bots to run between 9pm and 7am UK); one catalogue request to UK
Power Networks' `/api/` and one Toronto CKAN download URL, both disallowed by
robots.txt; one data.gov.in home page in the same batch as its robots.txt (the
copy was deleted); two MMRDA requests with certificate checking off. None of
these sources is connected.
