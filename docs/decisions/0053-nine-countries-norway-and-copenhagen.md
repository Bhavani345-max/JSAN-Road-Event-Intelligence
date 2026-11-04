# 0053 — Nine more countries; Norway, Copenhagen and Sweden connected

**Status:** 4 November 2026. Code local, tested, for the user to review and push.
In production the three feeds run once named in `OFFICIAL_FEEDS_SCHEDULED_SOURCES`
(Sweden's also needs `TRAFIKVERKET_API_KEY` there).

## Context

The user, 4 November 2026: "add these cities and their sources": Sweden, Ireland,
Estonia, Poland, Brazil, Norway, Denmark, Latvia, Malaysia. Three agents checked
them live that day (Nordics; Baltics, Poland and Ireland; Brazil and Malaysia),
starting from the research of 16 October
(`docs/data-sources/{europe,americas-oceania,asia-mea}-official-road-sources-2026-10-16.md`),
under the rules since 16 October: connect only what the terms permit for REI's
use, record the rest with the reason, register nowhere, read robots.txt, few
requests per host. Their notes, with licence quotes and request logs:
`docs/data-sources/nordics-sources-2026-11-04.md`,
`baltics-poland-ireland-sources-2026-11-04.md`, `brazil-malaysia-sources-2026-11-04.md`.

## Decision

### Country and city entries

Ten new entries in `backend/packages/cities/data/`: `sweden`, `norway`, `denmark`
(+ city `copenhagen`), `estonia`, `latvia`, `poland`, `ireland`, `brazil`,
`malaysia`. Each country entry has its bbox, map view, time zone (Brazil's entry:
America/Sao_Paulo), language and scope words in English and the local language.
As for every entry, the registry lists a Google News RSS row for each, BLOCKED by
Google's terms and never polled. No place lists, so no GDELT searches.

### Connected (tier 1, government open data, permitted with attribution; no legal review, decision 0009)

| Country | Source id | Licence | Kept on 4 Nov |
|---|---|---|---|
| Norway | `norway-vegvesen-datex-situations` | NLOD 2.0, credit Statens vegvesen | 1,060 situations, all with geometry and start, 1,058 with an end |
| Denmark | `copenhagen-excavation-permits` | CC BY 4.0 (Open Data DK catalogue, city-of-copenhagen) | 629 permits, all with geometry, start and end |
| Sweden | `se-trafikverket-situations` | CC0 1.0 (Trafikverket's API page) | 1,329 situations, all with geometry and start, 1,267 with an end |

- **Norway:** Statens vegvesen's DATEX II 3.1 situations as served openly by
  its WFS (`ogckart-sn1.atlas.vegvesen.no/datex_3_1/ows`, layer
  `SituationSimple_v2`); its DATEX server needs an account, the WFS does not
  (NPRA: "open available"). One event per situation, read as the NDW/CITA DATEX
  feeds are; ferry-only situations are not road events. The Norwegian text is
  kept verbatim and never translated (Statens vegvesen's condition "Norske
  meldinger skal ikke oversettes til andre språk"); English titles come from the
  DATEX codes only. If REI ever translates source text, this source must be left
  out of it.
- **Copenhagen:** the city's active excavation permits (WFS
  `wfs-kbhkort.kk.dk/k101/ows`, `gravetilladelser_aktiv_aabne`). Only permits
  that dig the carriageway or a cycle path are kept (642 of 1,597; pavement,
  parking or green areas only are not road events, as for Málaga's parking-only
  cuts); 13 more than a year ahead are left out. Developer and contractor fields
  name private persons and are dropped before anything is stored.

- **Sweden** (added the same day, after the user registered and gave the key):
  Trafikverket's open API, object type `Situation` (namespace `Road.TrafficInfo`,
  schema 1.6), POST with the key in the request body; the key is read from
  `TRAFIKVERKET_API_KEY` (local `.env`; Railway after approval), never in code or
  logs; without it the source is listed as REQUIRES_ACCESS and never fetched.
  One event per situation, read by the shared DATEX II rules from Trafikverket's
  own DATEX terms (`MessageTypeValue`, `MessageCodeValue`); the Swedish words are
  kept. Municipalities report into the same feed (Gothenburg 87, Uppsala 34,
  Stockholm 18, Trollhättan 17 … of 1,331 on 4 November), credited in the title.
  Ferry notices are not road events. **Suspended parts are left out**: 2,070 of
  3,462 situations had every part `Suspended` (inactive now, mostly long works
  periods); the query asks only for situations with a part in force
  (`KEEP_SUSPENDED = False`, the user's call to change). Download under 5 MB a poll
  (13 MB unfiltered), every 30 minutes.

All three verified on 4 November: unit tests on real excerpts, a live dry run, and a
full ingestion into a throwaway database (1,060, 629 and 1,329 events, all
awaiting validation). I re-read both licences myself: the vegvesen dataset page states
"Norsk lisens for offentlige data (NLOD)"; Open Data DK's API gives
`license_id CC-BY-4.0` for `gravetilladelser` of `city-of-copenhagen`.

### Not connected (21, in `connectors/discovered_2026_11_04.py`)

- **Needs a free key or account (the user's to request):** Gothenburg (2; its own
  layers, though Gothenburg already reports into Trafikverket's feed), Denmark Vejdirektoratet DU-portal (2)
  and Copenhagen's DU roadworks, Norway's DATEX server (not needed: the WFS is
  open), Estonia Tark Tee (key after staff review), Latvia NAP (CC0, free
  account), Poland GDDKiA KPD (form and client certificate), Rio de Janeiro COR
  (Google BigQuery; licence CC BY-ND), PLUS Malaysia (no public programme).
- **Licence not settled (permission needed):** Tartu (licence "none"; 124 work
  stages ready to build once licensed), TII Ireland (reCAPTCHA, no licence),
  Dublin City Council closures (open-licence clause and full copyright clause
  both on the site), CET São Paulo (news pages, no terms), Malaysian Highway
  Authority disaster layer ("Hak Cipta Terpelihara").
- **Permitted but unreachable from this network:** Poland's road-obstruction
  file (CC0) and Warsaw's disruptions file (CC BY 4.0) timed out; worth one
  try from production.
- **Other:** Stockholm (layers not published), Copenhagen road-use permits
  (open, mostly not road events), Aarhus (stale since 2018, personal data).

## Not done

No registration anywhere; no keys used. Brazil and Malaysia have country entries
and no source: nothing found is both open and licensed for REI's use.
