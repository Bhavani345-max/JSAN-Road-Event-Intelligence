# US and Canadian city connectors, 21 October 2026

Six connectors were built from the PERMITTED city feeds in
[americas-oceania-official-road-sources-2026-10-16.md](americas-oceania-official-road-sources-2026-10-16.md).
Two more on that list were **not** built: Charlotte and Iowa (see "Not built"
below). Every licence page and robots.txt was read again on 21 October 2026
between 10:59 and 11:22 UTC with REI's own User-Agent
(`JSAN-REI/1.0 (road event intelligence; RSS reader)`): 52 requests to 15
hosts (the live dry run included), at most 7 to one host (`www.arcgis.com`).
Crawl delays were respected (`data-hrm.hub.arcgis.com` and
`opendata-cityofcambridge.hub.arcgis.com` 60 s, `www.donneesquebec.ca` 10 s,
Socrata hosts 1 s). Nothing was bypassed and no key was used. Two web
searches were used for discovery only (Iowa's terms, Cambridge's catalogue).

The connectors are registered nowhere yet: they need the registry entry and
the city-file additions listed at the end. Until then nothing fetches them.

## Built

| Source id | Feed | Licence (read 21 Oct 2026) | Live, 21 Oct 2026 |
| --- | --- | --- | --- |
| `seattle-sdot-street-closures` | Seattle SDOT Street Closures, Socrata `ium9-iqtc` | Public Domain | 117 rows; 112 kept (5 start more than a year ahead, one in "2924"); all with start and end |
| `baton-rouge-road-closures` | Baton Rouge Road Closures, Socrata `ra2i-eye8` | Public Domain | 30; 29 kept (1 ended); all with start and end |
| `halifax-street-closures` | Halifax `Street_Closures` FeatureServer/0 | OGL – Halifax | 37 asked (ending yesterday or later); 36 kept; all with start and end |
| `cambridge-on-road-closures` | Cambridge `RoadClosuresPingStreet` MapServer/1 | Open Data Licence v2.0 – City of Cambridge | 145; 116 parking-lane-only left out; 29 kept; all with start and end |
| `kitchener-traffic-closures` | Kitchener `Traffic_Closures` FeatureServer/0 (ArcGIS Online) | OGL – City of Kitchener v1.0 | 44; 42 kept (2 ended); 27 with start, 21 with end |
| `sherbrooke-travaux` | Sherbrooke `Travaux` FeatureServer/0 | CC BY 4.0 | 54; 20 with no effect on road traffic left out; 33 kept (1 ended); all with start and end |

All kept records are located by the source's own geometry (lines, or points
for Sherbrooke) inside the country's area. Counts are from one live `fetch()`
per connector (11:21 UTC); nothing was written to any database.

### Seattle SDOT Street Closures

- Request: `GET https://data.seattle.gov/resource/ium9-iqtc.json?$limit=5000&$where=end_date >= '<today, Seattle>'`.
- Licence: dataset metadata (`/api/views/ium9-iqtc.json`): `"license": {"name": "Public Domain"}`,
  `licenseId: PUBLIC_DOMAIN`, attribution "Seattle Department of Transportation".
- robots.txt: `Crawl-delay: 1`; `/resource/` and `/api/views/` are not disallowed.
- Content: only permitted **non-construction** closures (description: "These permits are only the
  closures permitted for non-construction activities, including Block Parties, Play Streets, Farmers
  markets and Cafe Streets. This dataset does not include closures for parades, festivals, or
  construction related activities"). Block Party 39, Farmers Market 29, Temporary Activation 28,
  Play Street 21. All are `SPECIAL_EVENT`.
- Times: `start_date`/`end_date` are days (Seattle local, no offset): a record runs from 00:00 of
  the first day to 23:59:59 of the last, `America/Los_Angeles`. The hours are in one column per
  weekday and are kept as text in the summary ("Sat 4PM-10PM").
- Id: permit, segment (`segkey`) and the two dates; one permit closes several segments, some on
  several periods.

### Baton Rouge Road Closures

- Request: `GET https://data.brla.gov/resource/ra2i-eye8.json?$limit=5000` (the dataset holds only the
  active closures).
- Licence: dataset metadata: `"license": {"name": "Public Domain"}`, `licenseId: PUBLIC_DOMAIN`,
  attribution "Department of Transportation and Drainage Services - Traffic Engineering Division".
- robots.txt: as Seattle (Socrata). The data dictionary (`city.brla.gov/gis/metadata/ROAD_CLOSURE.html`)
  lists the fields without definitions.
- Times: written with `Z` and read as UTC; a time without a zone would not be taken.
- Types: `full_closure` Full → planned road closure, Partial → lane restriction, Bridge → bridge
  restriction. Source severity ("MAJOR") is kept as the source's word. Direction: only "BOTH" is
  read as both directions; "ALL", "NORTH", "EAST" are kept as written on the location. `sidewalk`
  (Yes/No, undefined) is kept as "Sidewalk: Yes", not interpreted.
- No id in the data (incident and permit columns empty): a row is known by street, cross streets,
  dates and line. The `contact` column (names of people or firms) is not kept.

### Halifax Street Closures

- Request: `GET …/Street_Closures/FeatureServer/0/query?where=END_DATE >= DATE '<yesterday, Halifax>'&outFields=*&outSR=4326&f=geojson`
  (the layer holds history back to 2019).
- Licence: item `6dc3953c5c32483d9f574382de804864` links "Open Data Licence"
  (<https://data-hrm.hub.arcgis.com/pages/open-data-licence>), which reads: "The information provider
  grants you a worldwide, royalty-free, perpetual, non-exclusive licence to use the Information,
  including for commercial purposes, subject to the terms below." Attribution: "Contains information
  licenced under the Open Government Licence–Halifax." Exempt: personal information (the layer has
  no contact column).
- robots.txt: `services2.arcgis.com` answers 403 ("Invalid URL"), treated as no rules (RFC 9309);
  the Hub host sets `Crawl-delay: 60` (respected).
- Times: `START_DATE`/`END_DATE` are days at the local midnight: whole days in `America/Halifax`.
  `START_TIME`/`END_TIME` ("7:00AM", "N/A", "6PM on Weekdays. 9AM on Weekends.") and the alternate
  (rain) dates `ALT_START_DATE`/`ALT_END_DATE` are kept as text, not taken as the period.
- Types: Special Event and Block Party → special event; the rest → planned road closure (it is the
  street-closure layer). `CLOSURE_STAGE` ("Approved" on all 37) is kept as the status.

### Cambridge (Ontario) Road Closures

- Request: `GET https://maps.cambridge.ca/arcgispub03/rest/services/RoadClosuresPingStreet/MapServer/1/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- Licence: the City's open-data catalogue lists "Road Closures" (item
  `57f26d74f53f4078842c08833f20971a`, owner cambridge.ca) at exactly this layer, with licence "Open Data
  Licence" linking <https://maps.cambridge.ca/images/opendata/Open%20data%20licence.pdf>: "The Information
  Provider grants you a worldwide, royalty-free, perpetual, non-exclusive licence to use the Information
  including for commercial purposes subject to the terms below." Required attribution: "Contains
  information licensed under the Open Government Licence – City of Cambridge." Exempt: "Personal
  Information". The City's web page (<https://www.cambridge.ca/mayor-city-council-government/open-data/>)
  now prints the same text as "Open Data License Version 2.1".
- robots.txt: `maps.cambridge.ca/robots.txt` redirects to an HTML page (no rules); the catalogue host
  sets `Crawl-delay: 60` (respected).
- Times: `DATE_FROM`/`DATE_TO` milliseconds (UTC instants).
- `DETAILS` is "<impact> - <lanes> - <direction>". Parking Lane only (116 of 145) closes no traffic
  lane and is left out. All Lanes / FULL CLOSURE → planned road closure; One Lane → lane restriction;
  N/A → road works. Direction from the third part. `STATUS` (LOW/MODERATE/HIGH/FULL CLOSURE…) is kept
  as the source's severity word.
- `CONTACT` (people, phone numbers) and `ORGANIZATION` (contractor names with staff names) are not
  kept: the licence excludes personal information.

### Kitchener Traffic Closures

- Request: `GET https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Closures/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- Licence: item `c500d56ecbec41a6b96e3e264ce65d22` (owner KitchenerGIS) `licenseInfo`: "The information
  provider grants you a worldwide, royalty-free, perpetual, non-exclusive licence to use the
  information, including for commercial purposes, subject to the terms below. … No credit is required
  … if you choose to do so, please use this text …: Contains information licensed under the Open
  Government Licence - The Corporation of the City of Kitchener." Exempt: personal information.
- robots.txt: `services1.arcgis.com` 403, no rules.
- Times: `DATE_FROM`/`DATE_TO` milliseconds (UTC). Checked against the text: the special event "closed
  at 12:00pm Friday, October 30" is `DATE_FROM` 16:00 UTC. 15 of 44 have no start, 21 no end: left
  unstated (such records are hidden on the map until the source gives both).
- Types: Closed / No Through Traffic / Local Access Only → planned road closure; Partially Closed /
  Lane Reduced → lane restriction; reason Special Event → special event; Emergency → emergency
  closure; Tentative or no status → road works. Sidewalk, Trail and status Open are left out.
- `CONTACT`, `ALTERNATE_CONTACT` (staff names and phones), `CREATE_BY`, `UPDATE_BY` (staff accounts)
  are not kept.

### Sherbrooke Travaux

- Request: `GET https://services3.arcgis.com/qsNXG7LzoUbR4c1C/arcgis/rest/services/Travaux/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson`.
- Licence: Données Québec record
  <https://www.donneesquebec.ca/recherche/dataset/04880bdf6ffa40ababfa900c2ef45b3c_0>: "Licence
  Attribution (CC-BY 4.0)"; recommended citation "VILLE DE SHERBROOKE - DONNÉES GÉOMATIQUES. Travaux,
  [Jeu de données], dans Données Québec, 2019, mis à jour le 01 juin 2026." The ArcGIS item
  (`04880bdf6ffa40ababfa900c2ef45b3c`) says "CC BY". robots.txt of Données Québec disallows
  `/recherche/api/`, so the dataset page itself was read (allowed); `services3.arcgis.com` 403.
- Times: `DATE_DEBUT`/`DATE_FIN` milliseconds (UTC); they equal `DATEDEBUTHE`/`DATEFINHE` read as
  Eastern time (checked on every sample row).
- Only works that state an effect on traffic: "Route fermée" → closure; "Circulation en alternance",
  "Perte d'une voie dans une direction", "Deux voies fermées…" → lane restriction; "Ralentissement à
  prévoir" → road works. "Aucun impact sur la circulation" and "Trottoir ou voie cyclable fermé" are
  left out. One work id (10147) named two works at two places: a record is the id and its point.

## Not built

- **Charlotte "Street Closures (Public)"** (`gis.charlottenc.gov/…/StreetClosuresAndDetours/MapServer/0`).
  The City's hub item `24b353a2e9894b3abf8d73fa0805673d` now states
  `licenseInfo: https://creativecommons.org/licenses/by-nc-sa/4.0/` (CC BY-NC-SA 4.0, **non-commercial,
  share-alike**). The item was modified on 16 October 2026 at 14:04 UTC, after the research of that
  day read CC BY 4.0. The ArcGIS Online copy
  (`services.arcgis.com/9Nl857LBlQVyzq54/…/CharlotteStreetClosuresAndDetours/FeatureServer`) now
  answers 499 "Token Required". Not permitted for commercial use: ask the City.
- **Iowa DOT 511 traveler events** (`services.arcgis.com/8lRhdTsQyJpO52F1/…/CARS511_Iowa_View/FeatureServer/0`).
  The item (`5e924db11ba94ce4bda1b38dfe0cdcdf`) states CC BY 4.0 **and** "Additional Terms and
  Conditions": Iowa DOT's GIS Data Terms of Use and the Iowa 511 (CARS-Hub) Terms of Use. Both pages
  and iowadot.gov's robots.txt answered a Cloudflare block ("Attention Required!", HTTP 403) and
  were not retried. Search-engine excerpts of the CARS-Hub terms mention an indemnity clause and
  access by vendor request form, the kind of condition for which Chicago was skipped. The terms
  cannot be read, so they do not clearly permit commercial reuse: ask Iowa DOT, or read the pages
  from a US host.
- Chicago permits and every ASK_PERMISSION or no-coordinates source: skipped as instructed.

## To connect

Registry (`backend/connectors/registry.py`): imports, and six entries in the `feature_feeds` tuple
of `_official_sources`:

```python
from .official.baton_rouge import BatonRougeRoadClosuresConnector, baton_rouge_source
from .official.cambridge_on import CambridgeRoadClosuresConnector, cambridge_source
from .official.halifax import HalifaxStreetClosuresConnector, halifax_source
from .official.kitchener import KitchenerTrafficClosuresConnector, kitchener_source
from .official.seattle import SeattleStreetClosuresConnector, seattle_source
from .official.sherbrooke import SherbrookeTravauxConnector, sherbrooke_source

            # US and Canadian city feeds (21 October 2026).
            (seattle_source, SeattleStreetClosuresConnector),
            (baton_rouge_source, BatonRougeRoadClosuresConnector),
            (halifax_source, HalifaxStreetClosuresConnector),
            (cambridge_source, CambridgeRoadClosuresConnector),
            (kitchener_source, KitchenerTrafficClosuresConnector),
            (sherbrooke_source, SherbrookeTravauxConnector),
```

`tests/api/test_official_feed_scheduling.py` counts the official sources
(`len(OFFICIAL_SOURCE_IDS) == 32`): add 6.

`packages/cities/data/united-states.json`: `official_sources` += `seattle-sdot-street-closures`,
`baton-rouge-road-closures`; `source_time_zones` += `"seattle-sdot-street-closures": "America/Los_Angeles"`,
`"baton-rouge-road-closures": "America/Chicago"`.

`packages/cities/data/canada.json`: `official_sources` += `halifax-street-closures`,
`cambridge-on-road-closures`, `kitchener-traffic-closures`, `sherbrooke-travaux`; `source_time_zones` +=
`"halifax-street-closures": "America/Halifax"`, `"cambridge-on-road-closures": "America/Toronto"`,
`"kitchener-traffic-closures": "America/Toronto"`, `"sherbrooke-travaux": "America/Toronto"`.

## Files

- Connectors: `backend/connectors/official/{seattle,baton_rouge,halifax,cambridge_on,kitchener,sherbrooke}.py`,
  and `feed_text.py` (joining a feed's text fields; used by the six).
- Tests: `backend/tests/unit/test_americas_city_feeds.py` (56 tests, no network).
- Fixtures: `backend/tests/fixtures/<source id with underscores>_2026-10-21.json`, 8–9 real items
  each, with the request and fetch time; contact columns removed.

## Not verified

- Update frequency of Baton Rouge ("Periodically") and Halifax (none stated); polling is set to
  6 hours for both.
- Whether Kitchener's "Tentative" closures happen; they are kept with their status.
- Seattle's records span whole days although the activity runs a few hours (hours in the summary).
