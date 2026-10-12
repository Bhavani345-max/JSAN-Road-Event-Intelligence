# GIS Resolution Engine

**Status:** built 6 October 2026, Hyderabad only. Follows
[the road-network research](gis-road-network-research.md) and
[decision 0012](decisions/0012-gis-resolution-engine.md).

> **This is not navigation-grade map matching.** The engine finds the
> OpenStreetMap junction or road a news report names, when the name leads to
> one place without doubt. It does not know lanes, turn restrictions or
> carriageway direction, does not route, and does not snap GPS traces. Its
> positions are as good as OpenStreetMap's, and every proposal waits for a
> reviewer before an event using it can be approved.

## What it does

A news report says "diversions at Khajaguda Junction" or "DLF road closed
from IIIT Junction to Gachibowli flyover". Until now REI could only place such
an event at the locality's centre, as an approximate (hollow) marker. The
engine looks the names up in the OpenStreetMap road network of the city and,
when exactly one junction or stretch of road fits, proposes it as the event's
location, with the OSM ids, the method and the reasons.

```
event text ──> mentions (junctions, crossings, stretches, roads, places)
           ──> each mention resolved on its own against the road network
           ──> HIGH / MEDIUM / LOW / UNRESOLVED, ambiguous or not, with every candidate
           ──> one defensible HIGH result from the headline or summary
               and nothing of higher precedence ──> GIS_RESOLVED proposal
           ──> reviewer: approve / reject / choose a candidate / place by hand
```

## Data

| | |
|---|---|
| Road network | OpenStreetMap, drivable public road classes (motorway to residential, living streets, links). Service roads, tracks and paths are left out. |
| Named points | OSM features named as junctions: junction tags, named traffic signals, names ending in Junction, Jn, X Road(s), Cross Road(s), Circle, Chowrasta, Rotary. Bus stops are excluded. |
| Fetched from | overpass-api.de only, every query pinned to one OSM snapshot (Overpass `[date:…]`); Hyderabad: **OSM snapshot: 2026-10-06T00:00:00Z**. The city's area in a 6 × 6 grid of tiles; a tile too heavy for the server is fetched in quarters. Every answer is verified (no Overpass remark, every element's own timestamp at or before the snapshot). Files are named with the snapshot, under `apps/api/.data/osm/<city>/snapshot-<stamp>/`, so the import repeats from saved data with `--from-cache` and gives the same result. |
| Stored in | PostGIS (`gis` schema of a separate database, `GIS_DATABASE_URL`): `osm_roads` (one row per OSM way, geometry, names, ref, one-way, lanes, node ids), `osm_named_points`, `osm_junction_nodes` (every node two or more road ways share, derived in SQL) and `import_runs` (what was loaded, when, from which OSM data date). |
| Junction references | `junction_references` in the REI database: a reviewer-maintained list of junction names OSM does not carry (for example "IIIT Junction"), each with its aliases, OSM node, roads and status. |
| Licence | © OpenStreetMap contributors, Open Database Licence 1.0. The console shows the attribution with every GIS result. |

The 6,303-place gazetteer stays what it was: a dictionary of place names. It
is not the road network. The engine uses it only to recognise localities
(which stay LOW) and, as a stretch end, a named landmark or flyover.

**Deviation from the research.** The research proposed a Geofabrik extract
cut with osmium and loaded with osm2pgsql. Neither tool is installed on this
Windows machine, so the import uses the Overpass API in tiles instead. The
data is the same OSM data; the cost is that the one public server used is
sometimes busy (the importer waits, splits heavy tiles and retries). For another city, or a server with the tools, the extract route is
still the better one.

## Import

```bash
docker compose up -d db                       # PostGIS (REI_DB_PORT, default 5432)
docker compose exec db createdb -U rei rei_gis   # once
# .env: GIS_DATABASE_URL=postgresql+psycopg://rei:<password>@localhost:<port>/rei_gis
S=2026-10-06T00:00:00Z
python -m services.gis_resolution.import_osm --city hyderabad --snapshot $S --download-only  # download + validate
python -m services.gis_resolution.import_osm --city hyderabad --snapshot $S --validate       # validate saved files
python -m services.gis_resolution.import_osm --city hyderabad --snapshot $S --from-cache     # validate, then load
python apps/api/gis.py status                 # what is loaded
```

Nothing is loaded unless validation passes: all 36 tiles present, every file
of the one snapshot and from overpass-api.de, no partial answer, quarter
pieces joining exactly into their tile, every copy of a way that crosses a
tile edge identical, every such way present in each tile it enters, and
valid geometry. The report is saved beside the tiles. The load replaces the
city's rows in one transaction; running it twice gives the same tables.

**Why one pinned snapshot.** A first download (6 October 2026) rotated
between three public Overpass servers. They answered from different
databases, dated 6 May to 6 October 2026, and 62 roads had a different shape
on each side of a tile edge. Those 28 tiles were never loaded; they are kept
in `apps/api/.data/osm/archive/`.

## How a mention is resolved

The engine (`services/gis_resolution/resolver.py`, `OsmGisEngine`) first lists
the mentions in the headline, summary and article text:

- a **stretch**: "closed from X to Y", "between X and Y";
- a **crossing**: "the junction of A and B", "A and B junction";
- a named **junction**, flyover or other structure; a **road** by name or by
  number (NH-65, SH1); a reviewer's **junction reference** by name or alias;
- a **place** from the gazetteer.

A name inside a stretch or crossing is resolved as part of it, not again on
its own. Each remaining mention is resolved on its own:

| Mention | Method | Confidence |
|---|---|---|
| Junction reference, confirmed by a reviewer | `JUNCTION_REFERENCE` (`ALIAS_MATCH` when named by an alias) | HIGH, at its OSM node |
| Junction reference not yet confirmed | the same | MEDIUM: a candidate only |
| Junction named in OSM, standing on a node two road ways share (or within 20 m of two differently named roads) | `OSM_NAMED_JUNCTION` | HIGH; the name at places more than 150 m apart: ambiguous |
| Two named roads that share an OSM node | `ROAD_INTERSECTION` | HIGH; several different shared places: ambiguous |
| A named flyover, bridge or underpass that is one structure (its pieces within 400 m) | `EXACT_ROAD_NAME` | HIGH |
| A road named with no stretch | `EXACT_ROAD_NAME` | MEDIUM, never applied: the report does not say which part |
| A stretch whose two ends are both known (confirmed reference, OSM junction, or a gazetteer junction, landmark or flyover) and one road passing within 80 m of both | `ROAD_STRETCH` | HIGH: the part of the road between the two ends |
| A locality only | `LOCALITY_ONLY` | LOW |
| No match, an unknown stretch end, or a candidate outside the city's bounding box | | UNRESOLVED |

Rules that never bend:

- **Never invented.** Every coordinate the engine returns is an OSM node, an
  OSM way's own geometry (or a piece of it cut at the projections of two
  known points), or a reviewer-confirmed reference. There is no fallback to
  "somewhere near".
- **Ambiguous is unresolved.** When one name fits separate places (two
  roads called "Twin Road" more than 700 m apart, a junction name on two
  crossings more than 150 m apart),
  the result is ambiguous: every candidate is kept, none is chosen, nothing
  is applied. The engine never picks the nearest.
- **Deterministic.** The same text and the same network give the same
  answer, in the same order. Running the resolver twice on an event changes
  nothing the second time.

## Precedence and what is applied

```
SOURCE_PROVIDED  >  HUMAN_CORRECTED / QC_APPROVED  >  GIS_RESOLVED  >  APPROXIMATE  >  UNRESOLVED
```

- An event whose geometry its source publishes (TfL, Toronto) or a reviewer
  placed is never changed. The engine still records what it found, marked
  "not applied: the event already has a higher-precedence location".
- An approximate event becomes `GIS_RESOLVED` only through one HIGH,
  unambiguous result from its headline or summary. A result from the article
  body alone is shown but not applied. A MEDIUM or LOW result never promotes
  anything.
- The location the proposal replaced is kept (`detection.gis.previous`), and
  each change is a new event version by `gis-resolver`.
- Each place the event names keeps its own result in
  `affected_locations[].gis`; a HIGH result resolves that place, the others
  stay as they were. The event's own geometry is the first defensible place
  in the headline, never a merged shape.

## Human review (QC)

| Action | Effect |
|---|---|
| **Approve GIS location** | The proposal stands; the event can now be approved. |
| **Reject** | The previous location is restored. The same candidate is not proposed again. |
| **Use …** (choose a candidate) | For an ambiguous or MEDIUM result: the reviewer's choice becomes the location (`REVIEWER_CONFIRMED`), approved. |
| **Confirm junction** | A proposed junction reference becomes CONFIRMED and is used from then on. A reference without a position cannot be confirmed. |
| **Correct location** (unchanged) | The reviewer places the event by hand; the GIS proposal is marked SUPERSEDED and the resolver does not touch the event again. |

An event whose location is `GIS_RESOLVED` cannot be approved, scheduled or
published until its GIS proposal is approved. For a critical closure, no
publication is preferred over an uncertain location.

Junction references are proposed only from the road network
(`gis.py propose-junction NAME --crossing ROAD_A ROAD_B`, which stores the
node the two roads share) and always start UNCONFIRMED. No coordinate is
typed in.

## Commands and API

```bash
python apps/api/gis.py status
python apps/api/gis.py junctions
python apps/api/gis.py propose-junction "IIIT Junction" --crossing "DLF road" "Old Bombay Road" --alias "IIIT Jn"
python apps/api/gis.py resolve EVT-... [EVT-...] [--dry-run]
```

| Endpoint | |
|---|---|
| `GET /api/junctions?city=` | junction references |
| `POST /api/junctions/{id}/confirm`, `/reject` | reviewer decision (reason required) |
| `POST /api/events/{id}/gis/approve`, `/reject`, `/choose` | review of a proposal |
| `POST /api/events/{id}/gis/resolve` | run now; 503 without `GIS_DATABASE_URL`, 409 for a city with no road network |

## On the map

| Marker | Meaning |
|---|---|
| Solid dot, white ring | geometry from the source |
| Solid dot, teal ring | GIS resolved (a proposal until approved) |
| Solid dot, black ring | placed by a reviewer |
| Hollow ring | approximate: a locality's position, not the event's |
| Grey dashed line or white dot with grey ring | a GIS candidate not applied, shown for the selected event only |

The event panel lists every mention with its confidence, method, OSM links
and reasons.

## Limitations

- **Not navigation-grade**, as above. No lanes, no direction of travel, no
  turn restrictions, no carriageways told apart.
- **OSM coverage decides.** Many junction names used in Hyderabad news
  ("IIIT Junction", "Cyber Towers junction") are not in OSM; they need a
  reviewer-confirmed reference. OSM road names vary ("Old Mumbai Highway" /
  "Old Bombay Road"); only names and alternative names in OSM match.
- **A road named alone** is not placed: the report does not say which part.
- **Stretches** need both ends known and one road through both.
- **Hyderabad only.** The tables hold one city per id; an OSM way id is
  stored once, so overlapping city areas would need a per-city key.
- **Refresh by hand.** The import is a snapshot; it is re-run, not updated
  live.
- **One snapshot.** The network is OSM as of the pinned moment; later OSM edits are not in it until a new snapshot is imported.
- **Overpass** is a shared public service; a large city import can take an
  hour when it is busy.

## Later

- Routing (pgRouting, Valhalla, OSRM, GraphHopper) and map matching are not
  part of this. They would be needed for detour lengths, travel-time impact
  or matching GPS traces, and would sit on the same `gis` tables.
- Other cities: the importer takes any configured city; London and Toronto
  publish their own geometry and are used only to check that the engine
  leaves source geometry alone.
