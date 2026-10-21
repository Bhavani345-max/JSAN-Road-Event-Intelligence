# Spain: four official connectors, 21 October 2026

**Status:** local only. The connectors, tests, fixtures and city files are
written and tested, but they are **not registered** (the registry snippet is
at the end). Nothing is committed, pushed or deployed, and no database was
written. This waits for the user's approval.

Research base: [europe-official-road-sources-2026-10-16.md](europe-official-road-sources-2026-10-16.md),
sources 4, 7, 11 and 14. Each licence and robots.txt was read again live on
21 October 2026.

| Source id | Authority | City entry | Licence (read 21 Oct 2026) | Live dry run, 11:21 UTC |
| --- | --- | --- | --- | --- |
| `dgt-spain-incidents` | Dirección General de Tráfico | `spain` | "Creative Commons Attribution" (no version stated) | 831 situations, 1,403 records; 1,384 kept, 1,355 in the area |
| `barcelona-public-space-works` | Ajuntament de Barcelona | `barcelona` | CC BY 4.0 | 1,939 rows, 1,766 works; 230 kept |
| `madrid-informo-incidents` | Ayuntamiento de Madrid | `madrid` | CC BY 4.0 | 113 incidents; 10 kept |
| `euskadi-traffic-incidences` | Gobierno Vasco (Open Data Euskadi) | `spain` | CC BY 4.0 | 203 incidences (202 distinct); 189 kept |

"Kept" means in force now or starting within the run window (`select_for_run`).
Every kept record has its own WGS 84 geometry and a stated start.

## How the checks were made

- **User-Agent:** `JSAN-REI/1.0 (road event intelligence; RSS reader)`, which is
  `Settings().http_user_agent`.
- **robots.txt first:** each host's robots.txt was read before anything else on
  that host.
- **Requests, sequential:** nap.dgt.es 6 (at least 10 s apart, as its
  `Crawl-Delay: 10` asks), www.dgt.es 2, opendata-ajuntament.barcelona.cat 7,
  informo.madrid.es 3, datos.madrid.es 3 (at least 10 s apart), api.euskadi.eus
  12 (robots.txt and the 11 pages of one live fetch), opendata.euskadi.eus 5 (one
  did not connect and was not retried), creativecommons.org 2.
- **What was not done:** no login, key, CAPTCHA, proxy or browser disguise.
  Barcelona's web pages answered 403 and were left alone.
- **Request log:** kept outside the repo, in the session scratchpad
  (`es-raw\log.tsv`).

## 1. DGT incidents, DATEX II 3.7 (`dgt-spain-incidents`)

- **Request:** `GET https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml`.
  HTTP 200, 6.4 MB, `Cache-Control: max-age=60`.
- **robots.txt:** `Disallow: /dataset`, `/dataset/rate/`, `/revision/`,
  `/dataset/*/history`, `/api/`, and `Crawl-Delay: 10`.
  - `/datex2/` is allowed.
  - The `/en/dataset/...` pages do not begin with `/dataset`, so under RFC 9309
    they are allowed. This is the same literal reading the 16 October research
    used.
- **Licence.** The dataset page
  (<https://nap.dgt.es/en/dataset/incidencias-dgt-datex2-v3-7>) says:
  - "License: Creative Commons Attribution". The link goes to
    `http://www.opendefinition.org/licenses/cc-by`. The resource page
    (`.../resource/1d36ea74-593d-4e45-acfa-fb8db5a460bc`) says the same.
  - "Contract or licence: Licence and Free of charge".
  - "Condition for use: https://www.dgt.es/contenido/aviso-legal/".
  - "Data owner: Dirección General de Tráfico".
- **DGT's legal notice** (<https://www.dgt.es/contenido/aviso-legal/>, updated
  10 February 2022) says: "Los derechos de propiedad intelectual de este portal
  de Internet, su diseño gráfico y los códigos que contiene, son titularidad de
  la Dirección General de Tráfico, a no ser que se indique otra diferente. La
  reproducción, distribución, comercialización o transformación no autorizadas
  de dichas obras, a no ser que sea para uso personal y privado, constituye una
  infracción…"
  - In English: the portal's works may not be reproduced, distributed or
    commercialised without authorisation, *unless stated otherwise*.
- **Assessment:**
  - The dataset is stated to be under CC BY, and every CC BY version allows
    commercial use with attribution. That statement is the "stated otherwise"
    the notice allows for, and the notice is written about the website ("este
    portal…, su diseño gráfico y los códigos").
  - On that reading the source was built, with
    `commercial_use=PERMITTED_WITH_ATTRIBUTION` and the credit "Dirección
    General de Tráfico (DGT)".
  - **Flag for the user:** the NAP's "condition for use" link points at a
    general website notice, and the licence version is not stated. If either
    gives doubt, keep the source inactive (as it is by default) and ask
    nap@dgt.es.
- **Format:**
  - DGT's DATEX II 3.7 profile, with namespaces `http://levelC/schema/3/…`.
  - Every time carries its offset.
  - Every record gives a WGS 84 point (`PointLocation`) or the from/to points of
    a section (`SingleRoadLinearLocation`). There is no line between them.
- **How the connector reads it:**
  - **Geometry:** the event is put at the point, or at the section's `from`
    point. Both points are kept as locations ("From: N-400 km 37.1, Ontígola
    (Toledo)" / "To: …"). Nothing is drawn between them.
  - **External id:** `situation:record`. This means Bison Futé's
    `same_situation_key` can group a situation's records (see the follow-ups at
    the end).
  - **Type, from DATEX codes only:**
    - A road, carriageway or intermittent closure caused by roadMaintenance is
      a planned closure; caused by anything else, an emergency closure.
    - Lane closures, alternating traffic, narrow lanes and lane changes are
      lane restrictions.
    - Otherwise: flooding is flooding, an accident an accident, roadworks
      road works, and obstructions, rockfalls, damaged surfaces and poor
      conditions road hazards.
    - AbnormalTraffic (slow traffic) is not taken, as for Hamburg.
    - "other / other" keeps its codes with no type.
  - **Direction:** only stated ones. `tpegDirectionRoad` "both" is
    BOTH_DIRECTIONS; northBound, southBound, eastBound and westBound map to the
    compass values. Intercardinal directions stay words.
  - **Speed limits:** `temporarySpeedLimit` is quoted without a unit. Some
    values (1.0, 2.0) cannot be km/h.
- **Live (11:21 UTC):**
  - 831 situations, 1,403 records.
  - 12 AbnormalTraffic records not taken, which leaves 1,391 listed.
  - 7 had ended, so 1,384 were kept. All have a start; 992 have an end.
  - 29 kept records are in the Canary Islands and fall outside the `spain`
    area, leaving 1,355 inside it.
  - Types: lane restriction 887, road hazard 183, planned closure 162, road
    works 103, emergency closure 26, accident 17, flooding 2, none 4.
  - At 11:10 UTC the same feed held 835 situations / 1,404 records.
- **Canary Islands:** left out of the `spain` area on purpose.
  - The console shows an entry's events in one time zone. `source_time_zones`
    is set per source, and this one source covers both zones.
  - Canary times would therefore appear in Madrid time, an hour off local
    clocks. Note that DGT stamps most Canary records with the mainland offset,
    +02:00.
  - Their records are still stored as evidence; no event is made.
  - To include them later, widen the bbox south to about 27.6° and west to
    about −18.2° once REI can show a zone per region.

## 2. Barcelona works in public space (`barcelona-public-space-works`)

- **Request:** `GET https://opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search?resource_id=4e6b3bfe-2f47-4d35-aa7d-3e4bcc930cea&limit=1000&offset=0|1000&sort=_id&fields=…`.
  Two pages; the ETRS89 copy of each site is not requested.
- **robots.txt:** HTTP 403, so there are no rules to read (RFC 9309).
  - The portal's terms page (`/en/node/52`) also answered 403 to REI's
    User-Agent and was not worked around.
  - The documented API answered 200.
- **Licence:** `package_show?id=obres`, read through the API on 21 October 2026,
  gives:
  - `"license_id": "CC-BY-4.0"`, `"license_title": "Creative Commons
    Attribution 4.0"`, `"license_url": "https://creativecommons.org/licenses/by/4.0/"`.
  - Title "Barcelona city's road works in public space"; author "Gerència de
    Mobilitat, Infraestructures i Serveis Urbans"; frequency DIARIA.
  - The CC BY 4.0 deed (<https://creativecommons.org/licenses/by/4.0/>, read
    the same day) says you may share and adapt "for any purpose, even
    commercially".
  - Credit "Ajuntament de Barcelona".
- **How the connector reads it:**
  - **One record per work code.** A work spanning several neighbourhoods is
    listed once per neighbourhood; only the district and neighbourhood
    columns differ between those rows. The rows become one record, which
    lists the neighbourhoods.
  - **Identity:** the datastore's `_id` is renumbered on reload (0 of 465
    codes kept theirs between 16 and 21 October). The work code is the
    identity, and `revision_key` ignores `_id`.
  - **Sites:** WKT POLYGON or MULTIPOLYGON is read as written, by a small
    parser (no new dependency). The result is validated against REI's GeoJSON
    model, and nothing is repaired.
  - **Days:** whole days in Madrid time (00:00 to 23:59:59).
  - **Status:** `estat` Finalitzada sets `reported_ended`.
  - **Type:** urbanisation, services, sewers, paving, mobility, lighting and
    school-surroundings works are road works. Building works, green spaces,
    cranes, transport infrastructure (often inside metro stations) and "Altres"
    keep their words with no type.
  - **Sites missing:** a work with no readable site is not taken (29 works).
- **Live (11:21 UTC):**
  - 1,939 rows, 1,766 works, 1,737 with a site.
  - 230 kept, all inside the Barcelona area: road works 124, no type 106.
  - Status: En execució 225, Finalitzada 3, Aturada 2.

## 3. Madrid Informo street incidents (`madrid-informo-incidents`)

- **Request:** `GET https://informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml`.
  UTF-8 with a byte-order mark.
- **robots.txt:**
  - `informo.madrid.es` answers 404 (a storage bucket's NoSuchKey), so there
    are no rules.
  - `datos.madrid.es` disallows `/api/`, resource downloads and any query
    string, with `Crawl-delay: 10`. Its dataset and conditions pages are
    allowed.
- **Licence:**
  - The dataset page (<https://datos.madrid.es/dataset/202062-0-trafico-incidencias-viapublica>)
    says "Licencia: Creative Commons Attribution 4.0 International (CC BY 4.0)".
  - The conditions page (<https://datos.madrid.es/pages/condiciones-de-uso>)
    says: "Las condiciones generales permiten la reutilización de los
    documentos para fines comerciales y no comerciales."
  - Credit "Ayuntamiento de Madrid".
- **How the connector reads it:**
  - **Times:** Madrid local time; the 7-digit fraction is dropped.
  - **Point:** `latitud`/`longitud` (the UTM copy is ignored).
  - **Type, from the code and flags only:** LCS "Carriles cortados" is a lane
    restriction; `es_accidente` S an accident; `es_obras` S road works.
  - **Description:** kept as the summary. It is never read into a type, a
    place or a time ("corte total", "de 10:00 a 15:00").
- **Live (11:21 UTC):**
  - 113 incidents, all with a start, an end and a point.
  - 10 in force or upcoming, all kept and inside the Madrid area: road works 8,
    lane restrictions 2.
- **Caveat:** the file was byte-for-byte the one fetched on 16 October, although
  its `Last-Modified` was 21 October 11:15 GMT. It is rewritten but its content
  had not changed in five days; 103 of its 113 incidents have ended. Watch
  whether it moves before relying on it.

## 4. Euskadi traffic incidences (`euskadi-traffic-incidences`)

- **Request:** `GET https://api.euskadi.eus/traffic/v1.0/incidences/byDate/<yyyy>/<mm>/<dd>?_page=<n>`
  for today in Madrid. 20 incidences a page; `totalPages` is followed.
- **robots.txt:**
  - `api.euskadi.eus` has none (404).
  - `opendata.euskadi.eus`: the legal, API catalogue and API documentation
    pages are allowed.
- **Licence:** Open Data Euskadi's legal page
  (<https://opendata.euskadi.eus/general/-/informacion-legal-opendata/>) says:
  - "la persona usuaria se acogerá en cada caso a la licencia claramente
    establecida para cada conjunto de datos. Esta licencia podrá ser de dos
    tipos: Licencia de reconocimiento de autoría (establecida en una licencia
    Creative Commons Reconocimiento 4.0) o licencia libre y gratuita de
    reutilización de la información pública."
  - Obligations: "Que el contenido de la información no sea alterado. Que no se
    desnaturalice el sentido de la información. Que se cite la fuente… Que se
    mencione la fecha de la última actualización."
  - Both licence types allow commercial reuse. The attribution names the source
    and the date the data was listed.
  - The API catalogue (<https://opendata.euskadi.eus/apis/-/apis-open-data/>)
    describes the traffic API as covering "Gobierno Vasco, Diputaciones Forales
    y Ayuntamientos de las tres capitales".
- **What the live data showed, which differs from the 16 October research
  (that read page 1 only):**
  - **Id collisions:** ids are unique only per `sourceId`. Id 1683 was both a
    Bilbao and a Donostia record. The external id is `<sourceId>-<incidenceId>`.
  - **sourceId 1:** 51 region-wide road incidences (road, km, cause), all
    started that day, with no end.
  - **sourceId 5, 6, 7:** all in Bilbao (110), Vitoria-Gasteiz (26) and
    Donostia (16). These are street works and occupations, many started weeks
    earlier (back to 2024), and every one has an `endDate`.
  - **Times at 00:00:** Bilbao and Donostia write every time at 00:00. They are
    read as written, so a work ending "2026-10-21T00:00" has ended for REI on
    21 October, although the API still lists it that day. This is the
    conservative reading; nothing is extended to the end of the day.
  - **Type spellings:** Obra, Obras, OBRA, Mantenimiento, Otros, OTRO, EVEN,
    and none.
  - **Text fields:** `incidenceName` carries HTML character references, which
    are decoded for titles. The raw data is stored as received.
- **How the connector reads it:**
  - **Type:** Obra/Obras/Mantenimiento are road works, Accidente an accident,
    Seguridad vial / Meteorológica / Vialidad invernal road hazards.
  - **Not taken:** Retención (queues), and "CORTE DE TRAFICO PEATONAL"
    (pedestrians only, as Tokushima's pavement restrictions).
  - **Everything else** keeps its words with no type.
  - **Kilometre points** are shown only with a road. Without one they are 0.0,
    or values like 2.52E7.
  - **No `observed_ids`:** sourceId 1's list holds only the day's starts, so
    dropping out of it does not mean an incidence ended.
- **Live (11:21 UTC):**
  - 203 incidences in 11 pages, 202 distinct.
  - 189 kept, all inside the `spain` area, all with a start; 138 have an end.
  - Types: road works 116, road hazard 13, accident 5, none 55.
  - The 51 sourceId 1 records state no end, so under the 15 October display rule
    they are unconfirmed.

## The Spain entry and its cities

- **`spain.json`:**
  - `"level": "country"`, ES, Europe/Madrid.
  - bbox 35.1, −9.5, 43.9, 4.4: the mainland, the Balearic Islands, Ceuta and
    Melilla. The Canary Islands are left out on purpose (see source 1).
  - Map centred on Madrid. Official sources: DGT and Euskadi.
- **`barcelona.json`:**
  - bbox 41.31, 2.04, 41.48, 2.24; Catalan.
  - The works' sites span 41.324–41.472 °N and 2.059–2.223 °E, all inside.
- **`madrid.json`:** bbox 40.30, −3.90, 40.65, −3.51.

## Registry snippet (for `connectors/registry.py`, not applied)

```python
from .official.spain_dgt import SpainDgtIncidentsConnector, dgt_source
from .official.barcelona import BarcelonaWorksConnector, barcelona_source
from .official.madrid import MadridInformoConnector, madrid_source
from .official.euskadi import EuskadiTrafficIncidencesConnector, euskadi_source
```

Add these entries to the `feature_feeds` tuple in `_official_sources`:

```python
            # Spain (21 October 2026, decision 0034).
            (dgt_source, SpainDgtIncidentsConnector),
            (barcelona_source, BarcelonaWorksConnector),
            (madrid_source, MadridInformoConnector),
            (euskadi_source, EuskadiTrafficIncidencesConnector),
```

All four take `(definition, user_agent)` like the other feature feeds.

**Overlap to resolve when registering:** `connectors/discovered.py` already lists
the same DGT feed as `dgt-spain-incidents` (TERMS_REVIEW_REQUIRED, no
connector). Remove that entry when DGT is registered, so the feed is not listed
twice. Alternatively, set `spain_dgt.SOURCE_ID` to `"dgt-spain-incidents"`, so
the existing sources row becomes the connected one. No other Spanish source is
listed there.

**Optional:** list the DGT source in `app/services/merge_service.py`
`LISTED_IN_SEVERAL_ROWS` with Bison Futé's `same_situation_key`, so a
situation's records at one spot and period merge. Its ids have the same
`situation:record` form.

## Not built, and why

- **Servei Català de Trànsit via DGT** (`infocar.dgt.es/datex2/sct/...`): the NAP
  page says "No licence – No contract". Awaiting permission (16 October
  research).
- **Madrid Calle 30, Barcelona `frase` incidents, Basque DATEX II on the NAP
  ("Incidents DT-GV")**: not researched or licence-checked here.

## Files

- `backend/connectors/official/spain_dgt.py`, `barcelona.py`, `madrid.py`, `euskadi.py`
- `backend/packages/cities/data/spain.json`, `barcelona.json`, `madrid.json`
- `backend/tests/unit/test_spain_sources.py` (25 tests)
- Trimmed fixtures in `backend/tests/fixtures/`:
  - `spain_dgt_datex2_v37_2026-10-21.xml`: 45 of 831 situations, unchanged.
  - `barcelona_obres_2026-10-21.json`: 21 works, 32 rows. Promoter and
    constructor are omitted for building, crane and "other" works, which may
    name private persons.
  - `madrid_informo_incidents_2026-10-21.xml`: 19 of 113 incidents.
  - `euskadi_traffic_incidences_2026-10-21.json`: 23 of 203 incidences, as one
    page.
