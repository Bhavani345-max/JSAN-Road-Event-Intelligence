# Sources that need only a free key or account (5 November 2026)

The user asked for this list on 5 November 2026 to take REI past 100 working
sources. Each source below publishes road events REI can use, and needs a key or
account that the user registers (REI never registers on the user's behalf). Facts
come from the registry entries (`backend/connectors/discovered*.py`, the 16 October
and 4 November research) and the 5 November research. A connector is built only
after the key exists; the key goes into `.env` locally and into the API service's
Railway variables, never into code.

Left out on purpose: HERE and Mappls (commercial contracts), SANRAL i-TRAFFIC (its
terms forbid commercial use and redistribution), Poland's KPD (organisation
registration and client certificates), Rio's COR (Google BigQuery, CC BY-ND),
PLUS Malaysia (no developer programme), Norway's DATEX server and Copenhagen's
DU-portal copy (the same data is already connected without a key).

| # | Source | Country | What it has | Where to register | Licence / terms | Notes |
|---|---|---|---|---|---|---|
| 1 | QLDTraffic events (hazards, crashes, flooding, roadworks, special events) | AU (Queensland) | 529 events on 15 Oct (459 in force), GeoJSON | No registration: the specification prints a shared public key "for developers who do not wish to register" (100 requests a minute, shared); a personal key is optional (data.qld.gov.au dataset 131940) | Conflicting: the data.qld.gov.au listing says CC BY 4.0, but each feed's copyright field points to the QLDTraffic website, whose Terms of Use "take precedence and prevail over any other terms", allow personal use only and say "use of the Site for commercial gain is strictly prohibited" (read 6 November 2026) | **Not connectable yet** (corrected 6 November 2026; this row first said only the user's go-ahead was needed). Needs written confirmation of commercial reuse from copyright@tmr.qld.gov.au |
| 2 | Transport for NSW Live Traffic (incidents, roadworks, floods, major events) | AU (NSW) | GeoJSON with planned start/end, lanes, roads | opendata.transport.nsw.gov.au: create an account, create an application, copy its API key | CC BY 4.0 | No page states the key is free; check at sign-up |
| 3 | Victoria DTP disruptions | AU (Victoria) | Road disruptions | opendata.transport.vic.gov.au: account, then a KeyID | CC BY 4.0 | HTTP 401 without the key |
| 4 | LTA DataMall traffic incidents and road works | SG | Incidents and road works with coordinates | datamall.lta.gov.sg: "Request for API access" form (free AccountKey by e-mail) | Singapore Open Data Licence v1.0 (commercial use with attribution) | |
| 5 | 511 SF Bay work zones and closures (WZDx) | US (California) | Local streets, freeways, state highways | 511.org/open-data/token: free token by e-mail | Terms shown at registration; confirm | WZDx: REI's existing WZDx reader fits |
| 6 | 511NY events | US (New York) | State-road events, start/end, coordinates, polylines | 511ny.org/developers: access request and Developers Access Agreement | Agreement not readable without signing in | Read the agreement before accepting |
| 7–11 | Ontario, Alberta, Manitoba, New Brunswick, Yukon 511 events (`/api/v2/get/event`) | CA | Provincial road events | 511on.ca/developers, 511.alberta.ca/developers, manitoba511.ca/developers, 511.gnb.ca/developers, 511yukon.ca/developers: a developer key each | Ontario: Open Government Licence – Ontario; others: shown at registration | "Ten calls every 60 seconds" per key |
| 12 | Korea MOLIT disaster road-situation information (재난상황정보) | KR | Road closures from floods, subsidence, fire: coordinates, road, closure type, lanes | data.go.kr: account, then 활용신청 (apply for use) on dataset 15160258; development keys approved automatically, production use reviewed | "이용허락범위 제한 없음" (no use restriction); free | Field names to verify once the key works |
| 13 | Latvian NAP road works, closures, lane closures, incidents (DATEX II 3.4) | LV | State roads (LVC) | transportdata.gov.lv: free user registration | CC0 1.0 (NAP terms, section 4) | Location may be OpenLR only: check after access |
| 14–15 | Vejdirektoratet road works and planned events (1208/1209); traffic messages (222) | DK | National road works and events, DATEX II, every 10 minutes | nap.vd.dk (DU-portal): profile, then subscribe to each dataset | 1208: CC BY 4.0; 222: not readable without an account | The login is reported to use MitID (Danish digital ID), which may rule out a foreign account |
| 16–17 | Göteborgs Stad traffic impact (Trafikpåverkan); start permits (Starttillstånd) | SE | City street works and their traffic impact | data.goteborg.se: free account, application key (APPID) | Shown at registration | Whether records carry locations and periods is seen only with the key |
| 18 | Tark Tee DATEX II (Estonia: traffic restrictions, SRTI) | EE | National traffic restrictions | tarktee.ee/en/datex-registration: form; key valid after staff review | Terms require credit; silent on commercial use ("for free use") | Ask about commercial use in the form |

Sources 2–5 and 12–13 have the clearest terms; source 1 waits on Queensland's written
confirmation (see its row). If all 18 were connected, REI would
gain 18 working sources; registry entries `qld-traffic-geojson`/`qldtraffic-events`
and `tfnsw-live-traffic-hazards`/`transport-nsw-live-traffic` describe the same
two services and would be one source each.
