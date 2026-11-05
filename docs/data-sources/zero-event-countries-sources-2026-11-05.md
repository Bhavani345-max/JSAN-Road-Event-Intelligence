# The six countries with no event: a second search, 5 November 2026

The user asked for more free sources for every country with no event and no
working source. Read-only, production had none for **Brazil, Estonia, Ireland,
Latvia, Malaysia and Poland**. The 4 November search found nothing REI may
connect in any of them
(`baltics-poland-ireland-sources-2026-11-04.md`, `brazil-malaysia-sources-2026-11-04.md`).
This search looked only at sources those two notes had not checked.

**Result: one source connected, Tallinn (Estonia, 193 road events).**
Everything else of value needs a publisher's permission or a key. Decision 0058.

## Method

- **When:** 5 November 2026, about 08:30 to 09:10 UTC. Five agents worked in
  parallel: Poland; Estonia and Latvia; Ireland; Brazil; Malaysia.
- **User-Agent:** `JSAN-REI/1.0 (road event intelligence; RSS reader)`, Python
  httpx from the project venv.
- **Access rules:**
  - robots.txt was read first on each host and obeyed. A 404 meant no rules; a
    timeout meant the host was not fetched.
  - Crawl-delay was obeyed.
  - Requests to one host were sequential, at least 2.5 s apart, at most 8 per host.
  - No logins, registrations, key sign-ups, CAPTCHAs or challenge bypasses.
  - One retry only for a timeout; none for a 401 or 403.
- **Request logs:** kept outside the repo in the session scratchpad
  (`sources-2026-11-05/{pl,ee-lv,ie,br,my}/log.tsv`). The agents made 38 to 59
  direct requests each, plus web searches and page reads.
- **One breach:** after `api.um.warszawa.pl`'s robots.txt timed out twice, the
  Poland agent sent one WebFetch request to that host. That broke the "timeout
  means do not fetch" rule. The request was refused, nothing was received, and it
  is in the log.
- **Personal data:** none was kept. Contractor and applicant names, officials'
  names, phones and e-mails were replaced or deleted in the saved copies.
- **Report files:** the agents could not write their report files, so their
  findings are copied here.

## Connected

### Estonia: Tallinn street closures and works (PERMITTED, connected)

- **Feeds:**
  - `https://opinfo.tallinn.ee/objektid/xml/183ac3aa` (street closures)
  - `https://opinfo.tallinn.ee/objektid/xml/f2325e11` (works on city land)
  - Both are XML from the city's opinfo system. No key; robots.txt answers 404.
- **Licence:** the Estonian open data portal's entry
  `tallinna-tanavate-sulgemised-ja-teemaa-alal-toimuvate-toode-info-opinfo.tallinn.ee-infosusteemist`
  (API `andmed.eesti.ee/api/datasets/slug/…`) gives `"license": "CC_BY_3.0"` for
  both files. The publisher is Tallinna Linnavalitsus (Tallinn City Government).
- **Content:**
  - Each object has a work type, reason, description, start and end (Tallinn
    time), period type and daily hours, address, and places on the street
    (carriageway, pavement or green area, with total and closed width).
  - Its shape is given as KML in WGS 84. The GeoJSON field beside it is in
    L-EST97.
- **Fetched:** 209 closures (179 in force, 30 coming) and 580 works objects:
  610 objects in all.
- **Kept:** 193 events on the carriageway: 25 road closures, 91 lane restrictions
  and 77 excavations.
- **Production:** the API container fetched the closures file (HTTP 200, 3.2 s).
- **Personal data:** applicant, client, contractor and owner are dropped, and
  phones and e-mails are removed from the text.

## Not connected, by country

Verdicts: **ASK_PERMISSION** (good data; the terms are silent or forbid reuse
without permission), **NEEDS_KEY**, **NOT_A_SOURCE**, **UNREACHABLE**, **BLOCKED**.

### Estonia and Latvia

| Source | Verdict | Key fact |
| --- | --- | --- |
| Tark Tee DATEX II (EE) | NEEDS_KEY | The portal (`liikluspiirangute-andmed`) now lists **CC BY**. The key is valid only after staff review. Register at tarktee.ee/en/datex-registration. |
| Tark Tee ArcGIS (`tarktee.mnt.ee`) | UNREACHABLE | robots.txt timed out twice. |
| Tallinn static restrictions | NOT_A_SOURCE | Speed limits and one-way streets, not events. |
| Tartu (EE) | ASK_PERMISSION | No terms page found. Contact gis@tartulv.ee. |
| Land Board, road register, Pärnu, Narva | NOT_A_SOURCE | Nothing in the national catalogue or in web searches. |
| Latvian NAP (`transportdata.gov.lv`) | NEEDS_KEY | CC0. An account needs only an e-mail (Cabinet Regulation No. 188, point 8). Road works and Road closures are "Private" datasets that each need a subscription. Whether the key is instant was not verified. |
| Riga planned street repairs (data.gov.lv) | NOT_A_SOURCE | CC BY 4.0, but 70 records with no dates. |
| GeoRīga (`www.georiga.eu`) | UNREACHABLE | robots.txt timed out twice. |

- **Latvian samples:** the August 2024 sample files carry WGS 84 points and point
  chains inside their OpenLR fields. In one sample, latitude and longitude are
  swapped.
- **Reader work:** REI's DATEX 3 reader (`datex3_nl_lu.py`) does not read
  `openlrCoordinates` yet, so it needs that added.

### Poland

| Source | Verdict | Key fact |
| --- | --- | --- |
| ZDiTM Szczecin notices for drivers (Atom: `zditm.szczecin.pl/pl/atom/informacje/kierowca`) | ASK_PERMISSION | 30 entries, about 5–8 in force or coming. Streets and dates are in the text, with no coordinates. The developer page says "Dane udostępniane są bezpłatnie na licencji CC0 1.0, do wykorzystania w dowolnym celu", but this feed is listed separately. Contact zditm@zditm.szczecin.pl. |
| ZDiZ Gdynia road messages (dane.gov.pl #41278) | BLOCKED (401) | The catalogue licence is CC BY 4.0, but `api.zdiz.gdynia.pl` answered 401 even to robots.txt. Contact otwartedane@gdynia.pl. |
| Łódź `lodz.pl/remonty` | ASK_PERMISSION | 57 items, 22 with exact dates, some out of date. No licence stated. Contact redakcja_portal@biblioteka.lodz.pl. |
| Kraków ZDMK works list | ASK_PERMISSION | About 54 dated items in prose. No licence stated. Contact sekretariat@zdmk.krakow.pl. |
| Gliwice "Informacje drogowe", Bytom road-occupation permits (GZM) | UNREACHABLE | CC BY 4.0 in the catalogue; the host timed out twice. |
| Warsaw `api.um.warszawa.pl` | UNREACHABLE | robots.txt timed out twice (see the breach under Method). |
| GDDKiA `drogi.gddkia.gov.pl` | BLOCKED | Bot-protection challenge (Imperva); no attempt to get past it. |
| GDDKiA on gov.pl | NOT_A_SOURCE | Text under CC BY-SA 4.0, but press releases only; no structured list or RSS. |
| Poznań disruption map | BLOCKED by robots | robots.txt disallows the map pages. |
| Kraków GIS (MSIP), Łódź ITS portal | UNREACHABLE | Both timed out. |

Not checked by fetch: Lublin, Bydgoszcz, Toruń, Rzeszów, Białystok, Katowice and
the Mazovian regional road authority (MZDW). Web searches found no feed for any
of them.

### Ireland

| Source | Verdict | Key fact |
| --- | --- | --- |
| Meath road notices | ASK_PERMISSION | Service: `services-eu1.arcgis.com/33tCl0taHHdVAN9O/arcgis/rest/services/Road_Notices_County_View/FeatureServer`, layers 7 and 8. 721 notices (6 in force, 7 upcoming) with points, dates and 28 closure and diversion lines. Most closures appear twice, as proposal and as order. meath.ie allows reuse "subject to the latest Public Sector Information licence" but also says "Reproduction … is prohibited save with the prior written authorisation". Contact gisoff@meathcoco.ie. |
| Cork City RoadClosureAlerts | ASK_PERMISSION | Service: `services-eu1.arcgis.com/f0ZQOHXBIeLonX0V/arcgis/rest/services/RoadClosureAlerts/FeatureServer/0`. 59 points (32 in force, 1 upcoming), updated daily. corkcity.ie forbids reproduction "save with the prior written authorisation", and its reuse policy excludes "Other maps of any kind". Contact foi@corkcity.ie. |
| Limerick road-notices map | ASK_PERMISSION | 40 markers with coordinates; dates are in the text only. No terms beyond copyright. Contact web.content@limerick.ie. |
| Dún Laoghaire-Rathdown traffic news | Licence permits; too thin | Its Smart Dublin dataset is "Creative Commons Attribution". The page has 3 closures in force and 2 proposed, text only, no coordinates. The weekly PDF was not read. |
| Fingal temporary road closures page | ASK_PERMISSION | About 8 text items; "All Rights Reserved". |
| Fingal and SDCC road opening licences, Galway scheduled closures | NOT_A_SOURCE | Counts only, an old snapshot, and 0 records respectively. |
| MapRoad licensing (Road Management Office) | ASK_PERMISSION | Catalogue says "Open Data: No". |
| National roadworks portal | NOT_A_SOURCE yet | Work to begin "sometime in 2026". |
| MapAlerter, Tipperary | UNREACHABLE, BLOCKED | Timeouts; HTTP 403. |
| data.gov.ie search API | Not used | robots.txt disallows `/api/` and searches. |

### Brazil

| Source | Verdict | Key fact |
| --- | --- | --- |
| COR Rio closures feed (`cor.rio/category/interdicoes/feed/`) | ASK_PERMISSION | 10 items (28 Oct to 4 Nov), all closures, about 1.4 a day, posted 3 to 48 hours ahead. Terms: "nenhum material… pode ser copiado, reproduzido, republicado… salvo mediante o consentimento prévio, por escrito, do COR.rio". Contact comunicacao@cor.rio. |
| DNIT "Alerta de Serviços" (gov.br) | ASK_PERMISSION | 30 federal-highway alerts, several in force. Licence: CC BY-ND 3.0, no adaptations. Contact imprensa@dnit.gov.br. |
| Rio COR occurrences | NEEDS_KEY (unchanged) | BigQuery only; CC BY-ND 3.0. |
| Agência Brasil | NOT_A_SOURCE | 0 road items in 20. The footer now says "© Todos os direitos reservados pela EBC". |
| Agência Minas, Agência SP, Curitiba, Manaus, Goiânia news | NOT_A_SOURCE | 0 or 1 road items each. |
| Porto Alegre EPTC | NOT_A_SOURCE | Web page only, 1 closure. |
| ArcGIS Online search | NOT_A_SOURCE | 41 recent layers; none an official road-event layer. |
| CET-Rio, SIE-SC, DER-PR, DAER-RS, Recife | UNREACHABLE | Timeouts. |
| DER-MG, NitTrans, Salvador | UNREACHABLE | 403 or connection error. |
| EMDEC Campinas, PRF full news | BLOCKED | Access-check page; login. |

Many Brazilian state and city hosts seem to refuse networks outside Brazil.

### Malaysia

| Source | Verdict | Key fact |
| --- | --- | --- |
| NADMA disaster portal "Penutupan Jalan" (from JKR) | ASK_PERMISSION | The map reads coordinates, state, district, road name, status and update date from an internal API with a login. The login was not used. "Hak Cipta Terpelihara". Contact opsroom@nadma.gov.my, copying JKR. |
| Government map server (mygos.mygeoportal.gov.my), NADMA and maintenance folders | NEEDS_KEY | "Token Required"; no self-service key. |
| JKR resurfacing programme (ArcGIS `KERJA_BP`) | NOT_A_SOURCE | Year and phase only, no works dates, no licence. The layer allows anonymous edits. |
| MRT Corp traffic notices | BLOCKED | Cloudflare challenge. |
| LRT3 | UNREACHABLE | Site suspended. |
| Klang (MBDK) | ASK_PERMISSION | Text notices; "expressed written permission". |
| RTM, Bernama | ASK_PERMISSION | Written permission or "express consent" needed. |
| JPS Public Infobanjir | NOT_A_SOURCE | River levels, not road events. |

## What the user can do

1. **Schedule Tallinn in production.** Add `tallinn-street-closures-and-works` to
   `OFFICIAL_FEEDS_SCHEDULED_SOURCES` on the API service once this is pushed.
2. **Latvia:** create a free account at transportdata.gov.lv (e-mail only) and
   subscribe to Road works and Road closures (CC0). REI then needs
   `openlrCoordinates` support in its DATEX 3 reader.
3. **Estonia, Tark Tee:** register at tarktee.ee/en/datex-registration (staff
   review; CC BY).
4. **Ask permission** (one e-mail each):
   - Meath: gisoff@meathcoco.ie
   - Cork City: foi@corkcity.ie
   - Szczecin: zditm@zditm.szczecin.pl
   - COR Rio: comunicacao@cor.rio
   - DNIT: imprensa@dnit.gov.br
   - NADMA: opsroom@nadma.gov.my
   - LLM (from 4 November): korporat@llm.gov.my
5. **Poland, national data:** KPD registration with GDDKiA is still the only way
   to national road data (4 November note).

## Not verified

- Whether the Latvian key is issued instantly.
- What live Latvian records look like.
- The licences of Tark Tee's short-term roadworks and its ArcGIS service.
- The contents of the hosts that did not answer.
- The DLR weekly PDF.
- Irish councils found only through search results.
