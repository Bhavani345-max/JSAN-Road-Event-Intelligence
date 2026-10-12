# Data source cost model

As of 6 October 2026. Figures come from each provider's published pages,
fetched that day, or are marked "not established".

**The honest summary:** free and open data can support substantial
development and proof-of-concept testing, but worldwide authoritative
real-time coverage may require partnerships, paid providers, or additional
infrastructure. Worldwide road data is not free. Where an authority
publishes open data (London, Toronto, New York), the data costs nothing.
Where none does (Hyderabad, much of India), there is no free authoritative
source at all, and news is the only machine-readable route.

## Cost categories

| Category | Meaning |
| --- | --- |
| FREE_PUBLIC | No key, no charge. |
| FREE_WITH_LIMITS | No charge up to a stated limit or allowance. |
| REGISTRATION_REQUIRED | Needs an account or key; whether it is free is stated where known. |
| PAID | Needs payment. |
| PARTNER_ONLY | Only through a partnership or programme. |
| UNKNOWN | Not established. |

## Data cost per source

| Source | Category | Limits | Attribution required | Commercial use |
| --- | --- | --- | --- | --- |
| Publisher RSS feeds (6, Hyderabad) | FREE_PUBLIC | None published | Not established | Not established; terms not reviewed |
| Transport for London road disruptions | FREE_WITH_LIMITS | 50 req/min without key; ≤500/min per feed | "Powered by TfL Open Data" + OS and Geomni notices | Permitted (OGL v2.0 with TfL amendments) |
| City of Toronto road restrictions | FREE_PUBLIC | None published | "Contains information licensed under the Open Government Licence – Toronto." | Permitted ("any lawful purpose") |
| NYC Open Data street closures | FREE_PUBLIC | Throttling possible without a token | Not established | Not established |
| 511NY | REGISTRATION_REQUIRED | 10 calls / 60 s (search snippet) | Not established | Not established |
| Transport for NSW | REGISTRATION_REQUIRED | 60,000/day, 5/s | "Transport for NSW" as source | Permitted (CC BY 4.0) |
| LTA DataMall (Singapore) | REGISTRATION_REQUIRED | 10 million/day | SODL attribution sentence | Permitted (SODL v1.0) |
| Google News RSS | FREE_PUBLIC, but **blocked** | None published | — | **Not permitted** by the feed's notice |
| Serper.dev (Google News) | FREE_WITH_LIMITS | 2,500 credits once; then USD 50 per 50,000 (6 months) | Not established | Not established |
| TomTom Traffic Incidents | FREE_WITH_LIMITS, then PAID | 2,500 requests/month free (docs, 2 Oct) | Per contract | Per contract |
| HERE Traffic | UNKNOWN | Not established | Per contract | Per contract |
| Waze for Cities | PARTNER_ONLY | — | — | Programme members only |
| Hyderabad / Telangana authorities | — | No machine access exists | — | — |

## REI's current consumption

| Source | Requests | Data cost |
| --- | --- | --- |
| Six publisher feeds | 1 request each every 30 min: 288 a day | None |
| Serper (Hyderabad) | 12 searches every 8 hours: 36 credits a day | Free credits last about two months; then about USD 1 a month |
| Transport for London | 1 request per run; by hand in the test phase (96 a day if scheduled every 15 min) | None; far under 50 a minute |
| City of Toronto | 1 request per run; by hand in the test phase (48 a day if scheduled every 30 min) | None |
| Article pages (Serper results) | Up to 120 per poll | None; publisher terms unreviewed |

## Costs other than data

Data is only one of the costs. They are separate, and the free sources above
remove only the first.

| Cost | What drives it | Today (PoC) | At scale |
| --- | --- | --- | --- |
| **Data** | Source fees | Zero, apart from Serper credits | Paid providers or partnerships wherever no authority publishes open data |
| **Infrastructure** | API server, scheduler, database | One laptop | A hosted API, worker and PostgreSQL/PostGIS; cost grows with the number of cities and polling frequency |
| **Storage** | Evidence is kept for every item | About 6.6 MB SQLite for ~1,450 items | Toronto alone publishes ~2,000 records, about 3 MB a fetch; keeping every version of every record in many cities needs a retention policy |
| **Map / tiles** | Basemap and imagery for the console | OpenFreeMap tiles and Esri imagery, free for this use | Heavy public use needs a tile plan (MapTiler, Mapbox, Esri, or self-hosted tiles) with its own terms and attribution |
| **Processing** | Parsing, detection, place lookup, future GIS matching | Negligible | Road-network matching (PostGIS, OSM extracts per city) is the main future cost; OSM extracts are free but processing them is not |
| **Commercial licensing** | Terms of each source | None reviewed formally | A legal review per source before any commercial use; paid licences for commercial providers; publisher terms for news |

## Licensing and attribution in the product

- Official open data must show its attribution wherever its data appears.
  REI stores it with each event (`detection.attribution`), and the console
  shows it in the event details.
- OpenStreetMap data (the place lists) needs "© OpenStreetMap contributors"
  under the ODbL; the map shows it.
- The basemap and imagery providers' attributions are shown on the map.
- No source's terms have had a formal legal review. Licences that have been
  read are recorded as `PERMITS_TESTING`, not as cleared for commercial use.
