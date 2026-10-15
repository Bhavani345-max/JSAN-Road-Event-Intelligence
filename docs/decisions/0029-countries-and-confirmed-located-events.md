# 0029 — Canada, Australia, South Africa; only confirmed, located, current events

**Status:** accepted, 15 October 2026. Local only: nothing pushed or deployed.

## Context

The user asked (15 October 2026) to add Canada, South Africa and Australia
with at least four sources each, to avoid several events at one location
(a separate point for each event), to drop expired and unconfirmed events and
feeds without locations, "with changing previous data and UI", and to test
until each requirement scores well. Asked to clarify, the user said:

- **Unconfirmed** means the source states no start and end. They chose the
  strict rule: an event missing either is unconfirmed.
- Expired and unconfirmed events are **hidden, not deleted**.
- **Unlocated feeds are switched off**: NYC permitted events, the Mumbai
  Traffic Police notices and the Bengaluru Traffic Police listing. Every
  event without a location is hidden. Hyderabad news stays: it is placed at
  the places it names.

## Decision

### What the console shows

`services/lifecycle/current.is_shown`: an event is shown only with a
location, a stated start and a stated end, and only until that end (or
until its source reports it over). Operations (`current_upcoming`) and the
review queue (`validation`) list only such events. Nothing is deleted or
changed: `GET /api/events?include_hidden=true` lists the others for audit
and tools, and the `history` and `rejected` views are unchanged. A reviewer
can still give an event an end (decision 0007), which makes it shown again.

### Feeds without locations (registry `UNLOCATED_SOURCES`)

The three feeds are registered without a connector (`NOT_USABLE`, never
fetched), like The Hans India (0026). Their licence labels stay as read; the
reason is recorded in their notes. Their stored evidence is kept.

### One point per event

- **Rows of one event are merged** (decision 0025's `merge_listed_rows`,
  linked, never deleted; a reviewed row is left to a reviewer):
  - Bison Futé: the records of one DATEX II situation at one spot over one
    period (works + the closure they need + a diversion …). The record
    saying most about the road leads (closure, then works, …, hazard last).
  - Calgary: rows at the same point over the same period (one closure per
    direction or lane).
  - Every other official feed: rows identical to a reader (same type,
    title, position and period) listed under two ids.
- **Different events at one spot** (NYC permits on one block, DiaLog orders
  on one network) stay separate events. The map gives each its own marker on
  a small ring around the spot, a fixed number of pixels across at every
  zoom, with a thin line to the spot (`features/map/geojson.ts`
  `spreadStacks`). Only the drawing moves: the stored coordinates, the event
  geometry and the details panel are unchanged. The count badge is gone.

### Countries (`packages/cities/data/{canada,australia,south-africa}.json`)

Country-level configurations, like France and Finland. A country spanning
several time zones names each regional source's zone
(`source_time_zones`); its events' times are shown there.

Connected (tier 1, run by hand unless scheduled, `PERMITS_TESTING`, licence
recorded, not a legal review). Each was fetched live on 15 October 2026:

| Country | Source | Licence |
| --- | --- | --- |
| Canada | City of Toronto road restrictions (since 0009) | OGL – Toronto |
| Canada | DriveBC Open511 (British Columbia) | OGL – British Columbia |
| Canada | City of Ottawa traffic events | OGL – City of Ottawa |
| Canada | City of Edmonton traffic disruptions | OGL – Edmonton |
| Canada | City of Winnipeg lane closures | OGL – Winnipeg |
| Canada | City of Calgary construction detours | OGL – Calgary |
| Australia | Main Roads WA roadworks and events | CC BY 4.0 |
| Australia | City of Gold Coast temporary road closures | CC BY 3.0 |
| Australia | City of Wodonga roadworks | CC BY 4.0 |
| Australia | Roads ACT planned road closures | **CC BY-SA 4.0**: share-alike, commercial use left `UNKNOWN` for the user |
| South Africa | none | — |

Notes on reading the sources (in each module's docstring):
- **Times:** DriveBC's are UTC without an offset (checked against its own
  descriptions). Ottawa, Calgary, Winnipeg, Edmonton and Main Roads WA write
  local times. Gold Coast and Edmonton give whole days.
- **Winnipeg's 2099 end date** is the system's stand-in for "no end": read
  as no stated end.
- **Left out because they are not road events:** sidewalk, path, parking and
  loading-zone closures (Winnipeg, Gold Coast), and rest-area and washroom
  closures (DriveBC).
- **Edmonton** lists a disruption at both ends: it becomes one event at its
  from point, with the to point as a second location.
- **Roads ACT:** only approved plans are read.

Not connected (`connectors/discovered_2026_10_15.py`, research in
`docs/data-sources/*-source-research-2026-10-15.md`):
- **Montréal:** its times would have to be guessed.
- **Québec:** its robots.txt is behind a Cloudflare challenge.
- **Keys needed:** QLDTraffic (its public key), NSW, Victoria and the
  provincial 511s.
- **Licence conflict, nightly updates and overlap with the state feeds:**
  the national RADAR dataset.
- **Licence:** NT and Tasmania.
- **Blocked from India:** South Australia.
- **South Africa:**
  - Western Cape: no licence; commercial use needs a written request; every
    closure has no end date.
  - SANRAL i-TRAFFIC: needs a key and written consent.

### Measuring

`backend/tools/requirements_eval/requirements_eval.py` reads a database
read-only. It lists events exactly as the API does for the console, checks
each listed event against the requirements independently, and scores them
(`--before` lists the way the console did before).

## Consequences

- Local database (backup `backend/.data/backups/rei-2026-10-15-before-countries-and-display-rules.db`):
  - 112 Bison Futé records merged into their situations.
  - Calgary 16 rows merged; Ottawa, Lyon, Finland and DiaLog 1 each.
  - New events: Canada 1,332 and Australia 970.
  - The 205 Calgary rows created by a first run with a faulty key (it
    joined different rows) were removed, and the source was read again.
- Scores on the local database (15 October 2026). "Before" is the morning's
  backup listed with the old console rules. The tool reads today's
  configuration, so R1 before is counted by hand: only Canada existed, through
  Toronto.

  | Requirement | Before | After |
  | --- | --- | --- |
  | R1 countries configured | 33% (Canada only) | 100% |
  | R2 four located sources per country | 8% (1 of 12) | 67% (Canada 6, Australia 4, South Africa 0) |
  | R3 no duplicates (identical to a reader) at one spot | 99.4% | 100% |
  | R4 no expired event shown | 93.3% | 100% |
  | R5 no unconfirmed event shown | 93.2% | 100% |
  | R6 no unlocated event shown | 97.7%, with 3 unlocated feeds connected | 100%, none connected |

  418 spots are shared by 920 different events (NYC permits on one block,
  DiaLog orders on one network …); the map spreads them apart.
- Console list speed (local, all cities): a page of the review queue went
  from 9.3 s to 2.1 s, and the operations view from 8.9 s to 0.1 s. The
  database now applies the view's column rules (`EventRepository._list_shown`,
  tested equal to the rule in `tests/api/test_console_lists.py`).
- Production gets the code when deployed. The new feeds poll only when
  named in `OFFICIAL_FEEDS_SCHEDULED_SOURCES` (0028) or run by hand.
- For the user: Roads ACT's share-alike licence before any publishing;
  keys (QLDTraffic, NSW, Victoria, provincial 511s); permission requests in
  South Africa (Western Cape, SANRAL); Montréal's time format (ask the City);
  Québec's robots.txt.
