# 0054 — TomTom live incidents as a map layer, never stored

**Status:** 4 November 2026. Code local, tested, for the user to review and push.
`TOMTOM_API_KEY` is in the local `.env`; on Railway after the user's go.

## Context

The six countries without a usable source (Brazil, Estonia, Ireland, Latvia,
Malaysia, Poland) showed 0 events. The user gave a TomTom API key "for event
scraping" and, told why it could not be ingested, chose "make it work" as a live
map layer (asked directly, 4 November 2026).

TomTom's developer terms (docs.tomtom.com/legal/terms-and-conditions; the text is
in the page's script bundle `/_astro/LegalTabs.*.js`, read 4 November 2026):

- 11.4 "The caching or storing of any Results shall be prohibited", except in
  clients within the cache-control max-age; "Nothing under Clause 11.4 entitles
  any form of caching for the purpose of scaling results to serve multiple
  clients or users."
- 11.6.1 no "secondary or derived database populated wholly or partially with
  your data and/or data supplied … by any third party".
- 2.2 without a paid plan: "Evaluation Use only", "internal evaluation and
  testing by you of the Licensed Products".
- 17.3 attribution generated with "the TomTom Copyright API".

REI's ingestion stores events, keeps versions and merges sources: TomTom cannot
be an ingestion source. An evaluation that day (counts only, nothing stored)
found road events (no jams or weather) in force or planned: Warsaw 164,
Tallinn 49, Riga 58, Dublin 59, São Paulo 239, Kuala Lumpur 62. The key also
answers from the production server (HTTP 200, 695 incidents in Warsaw).

## Decision

- **Backend** `app/services/tomtom_live.py`, route `GET /api/live/tomtom-incidents?bbox=`
  (signed-in users only) and `/status`. One request per call to TomTom's Incident
  Details v5 for the box on screen (up to 10,000 km², TomTom's limit; larger is
  refused without asking TomTom), `categoryFilter` 1,3,7,8,9,11,14 (accident,
  dangerous conditions, lane closed, road closed, road works, flooding,
  broken-down vehicle: no jams or weather), `timeValidityFilter=present,future`,
  plus TomTom's caption from its Copyright API. The answer is passed through as
  GeoJSON with TomTom's own cache-control header (no-store on 4 November) and
  nothing else is kept: no event, no artifact, no file; only a count of requests
  made today (`TOMTOM_DAILY_REQUEST_LIMIT`, default 2,000) so the layer stays in
  the free daily allowance. Errors never show the key.
- **Console**: Layers → "TomTom live incidents" (off by default). When on and
  zoomed in to a city, the map asks for the area on screen once it settles
  (700 ms), draws incidents as purple dashed lines and points **under** REI's
  events (REI markers stay on top and clickable), shows TomTom's description on
  hover and click with "Live from TomTom, not an REI event: not stored, not in the
  list or counts", and a status pill: "TomTom live · N incidents here · © TomTom ·
  not stored", or "zoom in to a city". Switched off: drawn data dropped.
- TomTom incidents are **not** REI events: not in the list, the counts, the review
  queue, the analytics or any export.

## Conditions the user should know

- The free key's licence is internal evaluation and testing. REI's console is a
  signed-in internal tool; showing the layer to customers needs a paid TomTom
  plan (2.1), and storing incidents as REI events needs a written TomTom licence.
- TomTom's registry entry (`connectors/discovered.py`, `tomtom-traffic-incidents`)
  stays not connected, with the terms and the evaluation recorded.

## Verified

`tests/api/test_tomtom_live.py` (categories asked, jams dropped, area limit,
no key, daily allowance, refused key without the key in the message, route needs
a session, TomTom's cache header passed on, no event or artifact written);
`frontend/features/map/liveIncidents.test.ts`; a real call (central Warsaw:
48 road events, caption "© TomTom", cache-control no-store); a browser check on a
throwaway API and database (Poland at country zoom: "zoom in"; Warszawa Centralna:
10 incidents drawn under REI's layers; no console errors).
