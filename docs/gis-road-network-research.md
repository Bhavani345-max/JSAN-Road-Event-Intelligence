# GIS road-network research for Hyderabad

Research only, 6 October 2026. Nothing was implemented, no database or
application code was changed, and no large dataset was downloaded. The OSM
figures come from small Overpass queries: two areas around Gachibowli and
Khajaguda and Tellapur, and count-only queries for the whole Hyderabad area.

**The goal:** move from "article → locality point" to "article →
road/junction → candidate road segment → geometry → confidence → human QC",
without overbuilding.

## 1. What the repository has today

| Item | What it is | Road network? |
| --- | --- | --- |
| `services/geo_resolution/data/hyderabad_places.json` | Gazetteer built from OpenStreetMap on 6 Oct 2026: 6,303 names (5,880 with a position). Kinds: 3,518 landmarks, 1,777 areas, 779 roads, 102 flyovers, 73 junctions, 54 wards. | **No.** |
| `services/geo_resolution/resolver.py` | Finds those names in article text; returns one point per name. | No. |
| `services/gis_resolution/` | The GIS Resolution Engine **interface only** (`resolve`, `apply_resolution`, `NullGisEngine`), with protection rules for source-provided and reviewer locations. | No data. |
| Event model | `detection.affected_locations` (several places per event, each with a resolution class), `location_class`, `GIS_RESOLVED` reserved. | Ready to receive results. |
| Database | Migration 0001 creates, on PostgreSQL only, a PostGIS `geom` column on events (generated from the GeoJSON, GiST-indexed); `docker-compose.yml` uses `postgis/postgis:16-3.4`. Locally the app runs on SQLite, which has no spatial functions. | PostGIS is wired in but not used. |

### Is the gazetteer sufficient for GIS resolution? No.

The earlier count was 4,788 names; it is now 6,303 after the 6 October
rebuild. Either way it is **not** a road network. Verified from the file:

- Every entry is a **single point** (`lat`, `lon`, one OSM id). No entry holds
  a line, a polygon, node lists or way ids. A "road" entry is the one OSM way
  nearest the middle of all ways sharing the name. 423 names have **no
  position at all**, because they are long roads or names shared by distant
  places (Necklace Road, Outer Ring Road, Begumpet, Kondapur).
- There is **no topology**: nothing says which roads meet where, so a
  junction cannot be found as the crossing of two roads. Only the 73 junctions
  OSM happens to name exist as points.
- There are **no segments, directions or lanes**: one-way tags, lane counts
  and road class are all dropped at build time.
- For the examples below: "IIIT Junction" is not in it (only "IIIT-H" and
  "IIIT Hyderabad", the campus). "Vaishali Nagar" is not in it. "Isnapur" is
  only an area.

It remains useful as a **name index**: it turns article words into OSM ids. It
cannot say which road segment an event affects.

## 2. The options compared

### Option A — OpenStreetMap road network

Measured in OSM for the Hyderabad area (bbox 17.18–17.68 N, 78.15–78.75 E):

| Measure | Count |
| --- | --- |
| Road ways (all drivable incl. residential and service) | 210,478 |
| Main roads (motorway … tertiary, with links) | 13,405 |
| Named main-road ways | 6,485 |
| Ways with a one-way tag | 14,815 |
| Traffic-signal nodes | 264 |

In the Gachibowli–Khajaguda area alone (about 4 × 4.4 km) there are 4,246
road ways and 610 named ones, with 1,275 one-way tags, 331 lane counts, 353
speed limits and 37 road numbers.

| Criterion | Finding |
| --- | --- |
| Road geometry | Yes: every way is a polyline (node by node). |
| Road names | Good on main roads ("Old Bombay Road", "DLF road", "Khajaguda Nanakramguda road", "Gachibowli - Miyapur Road", "ISB Road"); spelling varies ("DLF road" / "dlf gachibowli"); some local names missing. |
| Junctions | Topology is complete: roads that meet share a node. Named junctions are few (73 in the gazetteer; e.g. "Khajaguda Jn", "Gachibowli Circle", "Cyber Towers Junction", "TCS Junction"). **No "IIIT Junction".** |
| Road segments | Yes: ways split at junctions give segments; each has a stable OSM id. |
| Direction | One-way flags on 14,815 ways; carriageways of divided roads are often mapped as separate one-way ways ("DLF road" is). No turn restrictions were sampled. |
| Coverage | Whole city and worldwide. |
| Update frequency | Continuous edits; Geofabrik extracts daily (southern India: 532 MB `.osm.pbf`). |
| Format | `.osm.pbf` / OSM XML; Overpass JSON. |
| PostGIS import | Standard: `osmium extract` (cut the city out) → `osm2pgsql` (flex style, a few tables). Hyderabad only is tens of MB, minutes to import. |
| Licence | ODbL 1.0, attribution "© OpenStreetMap contributors". **Share-alike** applies to a *derivative database* that is distributed: a road-segment table built from OSM and published must be under ODbL. Maps and event outputs ("produced works") need attribution only. |
| Commercial REI | Usable commercially, with the share-alike point above to be designed around and reviewed (publish event references to OSM ids, not a redistributed road database). |
| Hyderabad | Good for main roads; the gap is **junction names** the press uses but OSM lacks. |
| Worldwide | The only option here that works in every city with the same code. |
| Complexity | Low to medium: one import, a few SQL queries. |

### Option B — Telangana / Government of India road data

| Source | What it is | Usable for REI? |
| --- | --- | --- |
| Open Data Telangana (data.telangana.gov.in) | No road network dataset found (checked 2 and 6 Oct 2026); the portal's API path returned 404. | No. |
| Telangana district and mandal shapefiles (AIKosh) | Administrative boundaries, Open Government Data Licence – India. | Boundaries only, not roads. |
| Telangana geospatial road-connectivity database | A 2016 state presentation describes "a geospatial database of habitations and road networks … for 589 mandals"; no public download was found. | Not publicly available. |
| TRAC / T-GIS ArcGIS services | Industrial plots and infrastructure; the server refused connections on 6 Oct 2026. | Blocked. |
| PMGSY GeoSadak | National rural roads, reported ODbL-compatible; may be reachable only from India. | Rural roads, not Hyderabad's city network. |
| Bhuvan (NRSC/ISRO) | Single-user licence; no internet hosting, no redistribution, no bulk feeds. | Not for REI. |
| Survey of India | Licensed digital data; the 2016 regime excluded commercial exploitation; the 2021 guidelines liberalised access, but terms need legal review. | Possible later, after legal review; not a free open road graph today. |

**Conclusion:** no government source gives Hyderabad a downloadable,
openly-licensed, routable road network today. It would also not help
worldwide expansion.

### Option C — Road data already in the project

| Data | Use for GIS |
| --- | --- |
| Hyderabad gazetteer (points) | A name index into OSM; not a network. |
| TfL street segments (London) | Line strings per street, from TfL; source-provided, London only. |
| Toronto polylines | Source-provided lines, Toronto only. |
| PostGIS `geom` column | Ready on PostgreSQL; not used locally. |

**Conclusion:** nothing in the repository is a Hyderabad road network.
London and Toronto data are the authorities' own geometry, which REI keeps
and never replaces. They are the right yardstick to validate an OSM-based
resolver against.

## 3. Engine choice

| Approach | What it adds | Needed now? |
| --- | --- | --- |
| **PostGIS only** | Spatial types, indexes, `ST_DWithin`, `ST_LineMerge`, `ST_LineSubstring`, `ST_Intersection`. No road data. | Necessary, not sufficient. |
| **PostGIS + OSM road data** | Named roads as lines, junctions as shared nodes, segments, one-way flags. Resolves a named road, a named junction, the crossing of two named roads, and a stretch "from X to Y" along one road. | **Yes: the smallest reliable step.** |
| PostGIS + pgRouting | Shortest paths on the same tables (GPL-2): a stretch that spans several roads, or diversion routes. | Later, only if multi-road stretches prove common. |
| Valhalla / OSRM | Routing engines with map matching (MIT / BSD-2); separate services, a few GB of RAM to build tiles. | No. Useful later for matching commercial or GPS feeds to OSM. Overbuilding now, and this machine has 2–3 GB free. |
| Commercial geocoders (Mappls, Google) | Better Indian junction names. | No (paid; out of scope). |

## 4. The five events

Real events in the stored data; OSM facts from the Overpass samples.

| # | Event | What the article names | What OSM offers | How it would resolve |
| --- | --- | --- | --- | --- |
| 1 | **IIIT Junction / DLF Road**: "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works" (Deccan Chronicle), "Traffic diversions at Gachibowli's IIIT Junction for 90 days" (Siasat). Stretch "DLF Gate No.1 to Gachibowli Traffic PS" | IIIT Junction (no such OSM name); DLF road; Gachibowli Traffic PS | "DLF road" (3 one-way ways, ~1.4 km) and "dlf gachibowli"; DLF road crosses Old Bombay Road at a single node (17.44556, 78.35223), which is probably IIIT Junction (inference, unconfirmed) | A reviewer-confirmed junction alias "IIIT Junction = DLF road × Old Bombay Road (node …)". The stretch is the part of DLF road between the projections of its two named ends onto the line (`ST_LineSubstring`). Confidence: high only after alias confirmation. |
| 2 | **Khajaguda Junction**: "Traffic diversions at Khajaguda junction for 60 days from September 26" (Telangana Today) + a Google News report | Khajaguda junction | Node "Khajaguda Jn" (node/3167952671) sits exactly where Khajaguda Nanakramguda road crosses Old Bombay Road (17.42266, 78.38197) | Named junction node → the segments that meet there. Directly resolvable; the approach roads affected need the article's wording or a reviewer. |
| 3 | **Tellapur road restriction** | **No such event is stored.** Tellapur appears only in a road-widening approval (CMC, Nallagandla–ORR radial road) and a plot-access complaint. | OSM has "Nallagandla-Tellapur Road", "tellapur road" and "Osman Nagar Road, Tellapur" (tertiary) | Cannot be tested on a real event yet. The road-widening article would resolve to the named road's geometry if detected. |
| 4 | **Multi-road diversion**: "Traffic diversions announced for Khairatabad Bada Ganesh" (12–24 Sept) | Rajeev Gandhi Statue, Rajdoot Lane, Mint Compound, Necklace Rotary, Khairatabad Post Office; congestion at Shadan College, Saifabad, NTR Marg, Secretariat Junction, KCP Junction, Masab Tank | Several are OSM roads or nodes (NTR Marg, Masab Tank); others are local names OSM may lack (Rajdoot Lane, Necklace Rotary) | Several affected locations, each resolved or left UNRESOLVED on its own. No single "geometry" is invented. |
| 5 | **Named junction, no coordinates**: "Traffic restrictions at Hyderabad's Vaishali Nagar underpass extended till October" (The Hindu); also "Isnapur Junction" (NH-65) and "Aparna Neo Mall junction" | Vaishali Nagar underpass | Not in the gazetteer; OSM coverage not established | Search OSM bridges/tunnels by name within the city; if absent, UNRESOLVED and sent to a reviewer, whose placement becomes a confirmed alias. |

## 5. Recommendation: the smallest reliable implementation

**PostGIS + an OSM road extract for Hyderabad, plus a reviewer-confirmed
junction alias table. No routing engine.**

1. **Data.** Cut Hyderabad's bbox from Geofabrik's southern-India extract
   with `osmium` and import roads with `osm2pgsql` (flex) into three tables:
   - `osm_roads`: way id, name, ref, class, one-way, lanes, line geometry;
   - `osm_road_nodes`: nodes where two or more named roads meet;
   - `osm_named_points`: named junctions, flyovers and underpasses.

   Refresh monthly, keeping the OSM data date with every result.
2. **Aliases.** Add `junction_aliases` for names the press uses that OSM
   lacks: "IIIT Junction" = a node or the crossing of two named roads. Each
   alias is proposed by REI and confirmed by a reviewer before use. A
   reviewer's "Correct location" can propose one.
3. **Resolver.** It implements the existing `GisResolutionEngine` interface,
   and for each affected location works through four cases:
   - named junction → its node;
   - "X and Y" or a crossing → the shared node of the two roads;
   - "from A to B on Road" → `ST_LineSubstring` of the merged road line;
   - a named road alone → the road's segments within the event's locality.

   Each result keeps the OSM ids, the OSM data date and a **stated** confidence
   rule: exact name match, alias confirmed, or ambiguous. These are rules, not
   a model. Ambiguity, such as two roads of the same name or more than one
   crossing, is left UNRESOLVED for a reviewer.
4. **Database.** Run PostGIS (already in `docker-compose.yml`). The app's
   SQLite stays for local use; GIS resolution needs PostGIS. Docker on this
   machine leaves under 1 GB free, so start it only while resolving.
5. **QC.** GIS results are proposals (`GIS_RESOLVED`). Source-provided and
   reviewer locations are never replaced, as the existing interface already
   enforces. The console shows the candidate segment for a reviewer to accept.
6. **Validation.** Run the resolver on London and match TfL's own street
   segments to OSM, to measure how often a name-based resolution lands on the
   authority's road.

This resolves examples 1 (after one alias confirmation), 2 and 4 (partly), and
sends 5 to review honestly. Example 3 has no real event to test on. pgRouting
can be added to the same database later, without changing the data, if
stretches spanning several roads turn out to be common.

## Sources

- OpenStreetMap / Overpass API queries, 6 October 2026 (overpass-api.de)
- [Geofabrik India extracts](https://download.geofabrik.de/asia/india.html)
- [How to access government GIS data for Indian cities and states (OpenCity)](https://opencity.in/how-to-access-government-gis-data-for-indian-cities-states/)
- [Telangana district and mandal shapefiles (AIKosh)](https://aikosh.indiaai.gov.in/home/datasets/details/telangana_district_and_mandal_geospatial_shapefiles.html)
- [Telangana SeMT GIS workshop (2016)](https://ncog.gov.in/documents/2016/Telangana%20SeMT%20GIS%20Workshop%20v%200.4.pdf)
- [OSM community: road classification data in Telangana](https://community-cdn.openstreetmap.org/t/wishlist-road-classification-data-in-telangana/116538/4)
- [Open Geospatial Data from Government of India (OSM wiki)](https://wiki.openstreetmap.org/wiki/Open_Geospatial_Data_from_Government_of_India)
- [Bhuvan user handbook](https://bhuvan-app1.nrsc.gov.in/2dresources/documents/1_Bhuvan_User_Handbook.pdf)
- [Survey of India national map policy guidelines](https://www.surveyofindia.gov.in/documents/guidelines-for-implementing-national-map-policy.pdf)
- [India's revised mapping policy (JSA)](https://www.jsalaw.com/?p=4345)
