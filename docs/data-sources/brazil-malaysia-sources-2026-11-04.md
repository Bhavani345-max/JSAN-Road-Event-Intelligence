# Brazil and Malaysia: official road-event sources (4 November 2026)

**Result: nothing to connect in either country.** No official feed of Brazil or
Malaysia was found that is keyless, carries current or upcoming road events with
coordinates and a start time, *and* has terms that permit REI's commercial reuse.
Both countries get a country entry (`brazil.json`, `malaysia.json`) with no source.

The 16 October research (`americas-oceania-…-2026-10-16.md`, `asia-mea-…-2026-10-16.md`)
was web-search only for these two countries. This pass checked live: CKAN APIs,
ArcGIS REST and Hub search, GeoServer WFS, the national catalogues and the agencies'
own sites, with REI's User-Agent `JSAN-REI/1.0 (road event intelligence; RSS reader)`,
robots.txt read first on every host (Python httpx; a 4xx robots answer read as
"allow all", a timeout or 5xx as "disallow all", per RFC 9309), crawl delays obeyed
(data.rio 60 s, ARTESP and Porto Alegre 10 s). Licence pages were read with WebFetch.
No registration, key or login was used. All times below are 4 November 2026, UTC.

Two finds are worth the user's follow-up:

1. **Malaysia: LLM's highway disaster layer** (`llm-highway-incident-reports`) is live,
   keyless and exactly REI's kind of data (flood closures on NKVE/GCE reported this
   morning, WGS 84 points, report times, active/inactive). It is not published as open
   data and the site says "Hak Cipta Terpelihara": **ASK_PERMISSION**.
2. **Brazil: Rio de Janeiro's COR occurrences** (`rio-cor-ocorrencias`) are daily, with
   WGS 84 coordinates, open/close times and status, but only through Google BigQuery,
   and under **CC BY-ND 3.0** (no adaptations): **NEEDS_KEY**, and the licence needs
   the city's confirmation.

## Summary

| Country | Source | Format / access | Records (4 Nov) | Verdict |
|---|---|---|---|---|
| MY | LLM highway disaster reports ("Bencana" layer) | ArcGIS FeatureServer, no key | 89 (3 active, all today) | ASK_PERMISSION |
| MY | LLM mandatory-exit diversions (PWS/ManExit) | ArcGIS FeatureServer, no key | 61 lines, 0 active | ASK_PERMISSION (with the above) |
| MY | LLM highway events layer (BPO/EvenT) | ArcGIS MapServer, no key | 10 (2018–2022) | NOT_A_SOURCE (stale; personal data) |
| MY | PLUS incidents API | JSON, HTTP 401 | – | NEEDS_KEY (no public programme) |
| MY | data.gov.my catalogue (CC BY 4.0) | Next.js catalogue / API | 356 datasets, 0 road events | NOT_A_SOURCE |
| MY | DBKL Kuala Lumpur | HTML, news RSS | RSS 50 items, 0 closures | NOT_A_SOURCE |
| MY | ITIS (Kuala Lumpur traffic system) | site "under maintenance" | – | UNREACHABLE |
| MY | JKR (www, bencana, bencanaalam) | – | timeouts | UNREACHABLE |
| MY | MBPJ / MBSA / archive.data.gov.my | – | TLS chain incomplete / refused / timeout | UNREACHABLE |
| BR | Rio COR occurrences (datario.adm_cor_comando.ocorrencias) | BigQuery; API host unreachable | not fetched | NEEDS_KEY (+ licence ND) |
| BR | CET São Paulo closure notices | HTML news pages | 4 notices dated 3 Nov linked | ASK_PERMISSION (no coordinates) |
| BR | GeoSampa "Controle de uso de vias públicas – Obras" | WFS GeoJSON, no key | 1,902 points, no dates, load of 31 Jan 2026 | NOT_A_SOURCE |
| BR | ARTESP Ocorrências / Programação de Obras | CKAN CSV / XLSX | monthly history; templates only | NOT_A_SOURCE (watch) |
| BR | Curitiba open data (32 datasets) | CSV | SIGMU log, events agenda | NOT_A_SOURCE |
| BR | data.rio Hub, Rio ArcGIS server pgeo3 | Hub API / ArcGIS REST | 0 traffic datasets | NOT_A_SOURCE |
| BR | São Paulo city CKAN (dados.prefeitura.sp.gov.br) | CKAN | robots `Disallow: /` | RESTRICTED (automated access) |
| BR | Porto Alegre CKAN (dadosabertos.poa.br) | CKAN | API disallowed; listing shows no road data | NOT_A_SOURCE |
| BR | dados.gov.br | API key (gov.br login) | robots.txt itself 401 | NEEDS_KEY (catalogue) |
| BR | PRF, ANTT, ARTESP accidents | CSV | historical | NOT_A_SOURCE |
| BR | Belo Horizonte (ckan.pbh, bhmap.pbh) | – | HTTP 403 "Acesso Bloqueado" | UNREACHABLE (blocked) |
| BR | ANTT dados.antt.gov.br | – | F5 "Request Rejected" | UNREACHABLE (blocked) |
| BR | DNIT servicos.dnit.gov.br, DER-SP | – | timeout / robots answered 202 | UNREACHABLE |
| BR | Brasília dados.df.gov.br, Recife dados.recife.pe.gov.br, Fortaleza | – | timeouts / DNS failure | UNREACHABLE |

## Malaysia

### LLM highway disaster and closure reports — ASK_PERMISSION

- Found through LLM's public highway map ("Peta Lebuh Raya Malaysia", web app
  `https://gis02.llm.gov.my/geosmpt/apps/webappviewer/index.html?id=ca1c4ab5d0c34e36a1dd556d9aedccf6`,
  linked from www.llm.gov.my). Its web map (item `5e60f4f6c48e4ba597fcd9449892a4e4`) lists
  the layers below.
- Request: `GET https://gis02.llm.gov.my/llmsmpt/rest/services/Hosted/survey123_6394fa57dfe34fc28d78d6db7bf41ad5/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=json&resultRecordCount=500`
  at 11:02:12, HTTP 200, no key. robots.txt of gis02.llm.gov.my: 404 (allow).
- 89 points, all with WGS 84 geometry (wkid 4326). Fields: `lebuhraya` (E1_PLUS,
  E35_GCE …), `nama_lebuhraya`, `arah`, `jenis_bencana` (Banjir 60, Cerun_Runtuh 12,
  Jalan_Memdap 4, Penutupan Jalan 1, blank 12), `km_start`/`km_end`,
  `tarikh_dan_masa_laporan` (74 of 89; 2021-12-18 to 2026-11-04), `catatan` (free-text
  status log), `status` (Tidak_Aktif 74, Aktif 3, blank 12).
- The 3 active reports are this morning's flash floods: GCE ramps at the NKVE/ELITE
  interchange (00:22), NKVE km 8.7–9.1 both directions closed (00:44), GCE to Shah Alam
  toll plaza closed (00:57). No end time field: an inactive status is the only end.
- Personal data: `pegawai_pelapor` (reporting officer), `created_user`,
  `last_edited_user`. A connector must drop them; the free text was checked for phone
  numbers and e-mails (none found).
- Same map: `PWS/ManExit/FeatureServer/1` (mandatory exits/alternative routes, 61 lines,
  57 NOT ACTIVE, 2 TERMINATED, 2 blank, last edit 9 Dec 2024; has `PIC` and user fields),
  and `BPO/EvenT/MapServer/0` (10 highway events, 2018–2022, with applicants' names,
  e-mails, addresses and phones: NOT_A_SOURCE). Also CCTV, toll plazas, rest areas.
- Licence: the layer's `licenseInfo` and `copyrightText` are empty. LLM's open-data page
  (`https://www.llm.gov.my/awam/data`) lists only "Panjang Lebuh Raya Bertol Di Malaysia"
  and "Pencapaian KPI Lembaga Lebuhraya Malaysia", and says "Penggunaan data atau
  penggunaan semula data hendaklah mematuhi terma dan syarat : Terma Penggunaan Data
  Terbuka Kerajaan 1.0". The site footer: "Hak Cipta Terpelihara © 2026 Lembaga
  Lebuhraya Malaysia" and "Lembaga Lebuhraya Malaysia tidak bertanggungjawab atas
  kehilangan atau kerosakan yang diakibatkan oleh penggunaan maklumat yg dicapai di laman
  portal ini." The privacy policy (`/dasar/privasi`) says nothing on reuse.
- Verdict: ASK_PERMISSION (precedent: "All rights reserved" with no other terms,
  `south-africa-sources-2026-10-22.md`). Requests to this host: 9 (map item, app data,
  web map, two layer metadata, three queries, two 404 guesses), more than usual because
  the layers had to be found through the map.

### PLUS incidents API — NEEDS_KEY

- The traffic page `https://www.plus.com.my/?Itemid=239` (robots 404, HTTP 200) calls
  `https://plusprodaio.azurewebsites.net/poi/incidents` (robots answered 401). One GET at
  11:05:32: HTTP 401, JSON `{code, msg, data}`. Not retried.
- No developer programme or terms were found; footer: "Copyright © 2024 PLUS Malaysia
  Berhad (Registration no. 201001039714 (923639-A))". Lane closures are announced as PDF
  media statements and on X (@plustrafik).
- PLUS is a concessionaire, not an authority (tier 2). Access would need an agreement.

### data.gov.my — NOT_A_SOURCE

- robots.txt `Allow: /`. `GET https://data.gov.my/data-catalogue` (11:01:06, 200): the
  page's data lists 356 catalogue entries; none is about road closures, works, incidents,
  traffic or accidents (closest: JPJ vehicle registrations, public-transport ridership).
- Licence of the portal's data and API: developer.data.gov.my footer "License: CC BY 4.0"
  (WebFetch). The real-time APIs are GTFS/GTFS-R (buses, trains) and weather only.
- The national terms for agency open data, "Terms of Use Government Open Data 1.0",
  permit "Use of data for commercial and non-commercial purposes" on condition that users
  "Mention the data sources in the products or applications based on the statement given
  by the owner of the data", and grant no rights to "Personal data"
  (`https://data.sarawak.gov.my/home/article/view/20`; the same text is on DOSM and
  Penang agency sites). That would cover an LLM layer if LLM published it as open data.

### DBKL (Kuala Lumpur) — NOT_A_SOURCE

- robots.txt allows all agents except GPTBot. `/maklumat-trafik` (200) offers forms,
  guidelines and the road-closure *permit application* (`/maklumat-trafik/permit-tutup-jalan`),
  no list of closures. The news RSS `https://www.dbkl.gov.my/feed/news` (200, 50 items,
  newest 30 Oct 2026) has no closure notices and no geo tags.

### Not reachable or nothing found

- **JKR** (www.jkr.gov.my, bencana.jkr.gov.my, bencanaalam.jkr.gov.my): robots.txt timed
  out on all three; not retried. JKR's flood road-closure lists are reported in the press
  from these portals; they could be the best federal-road source if reachable from Malaysia.
- **ITIS** (itis.com.my, DBKL's traffic information system): "We are under maintenance".
- **MBPJ** (www.mbpj.gov.my): TLS certificate chain incomplete (CERTIFICATE_VERIFY_FAILED);
  not bypassed. **MBSA**: connection refused. **archive.data.gov.my** (old CKAN with Penang
  state data): timeout.
- **ArcGIS Online** search for Malaysian closure layers: nothing official (the extent
  filter does not exclude world-extent items; results were dominated by US layers).
- Penang (MBPP, state portals): web search found closure notices as press statements only.
- LLM traffic page (`/awam/traffic`): CCTV, highway map, hotline; X @llmtrafik.

### What the user must do for Malaysia

1. **E-mail LLM** (korporat@llm.gov.my; Ketua Pegawai Digital listed at
   `https://www.llm.gov.my/corporate_info/cio`, not fetched: robots disallows
   `/corporate_info/`) asking permission for REI to read the "Bencana" and "ManExit"
   layers of Peta Lebuh Raya Malaysia commercially, with attribution, or to publish them on
   data.gov.my under the Terms of Use Government Open Data 1.0 or CC BY 4.0. Say that REI
   drops the officer names. If yes, a `feature_feed.py` connector is a small job (one
   layer, WGS 84 points, `Aktif` = current).
2. **PLUS Malaysia Berhad**: only by agreement (no developer programme). Optional.
3. **JKR**: check `bencana.jkr.gov.my` from a Malaysian network or ask JKR whether its
   road-closure (flood) data can be published as open data.

## Brazil

### Rio de Janeiro COR occurrences — NEEDS_KEY (and licence to confirm)

- Catalogue item: `https://www.data.rio/documents/4b21231ce02243e99b5f080b8a0ff821`, read
  through `GET https://www.arcgis.com/sharing/rest/content/items/4b21231ce02243e99b5f080b8a0ff821?f=json`
  (11:12:32, 200; owner escritorio_dados, modified 24 Jan 2024).
- Content (item description): "Ocorrências disparadas pelo COR desde 2015 … Por exemplo,
  Buraco na pista, bolsão d'água, enguiço mecânico." Updated "Diário". Columns:
  `data_inicio`, `data_fim` ("vazio quanto o evento está aberto"), `bairro`, `status`
  (ABERTO, FECHADO), `gravidade`, `prazo`, `latitude`/`longitude` ("formato WGS-84"),
  `id_evento`, `descricao`, `tipo`.
- Access: BigQuery `SELECT * FROM datario.adm_cor_comando.ocorrencias`, with a Google
  Cloud billing project ("billing_project_id = <id_do_seu_projeto_gcp>"); the API
  `https://api.dados.rio/v1/` and `docs.dados.rio` reset the connection (httpx and WebFetch);
  the CSV link opens a page saying "Esse dado não está disponível para download!".
- Licence (item `licenseInfo`): "This work is licensed under a Creative Commons
  Attribution-NoDerivatives 3.0 Unported License"
  (`https://creativecommons.org/licenses/by-nd/3.0/deed.pt_BR`). Commercial use is allowed;
  distributing adapted material is not. REI's normalised events may count as adaptations.
- The item's description names a person and her e-mail as publisher; not kept.

### CET São Paulo closure notices — ASK_PERMISSION

- `https://www.cetsp.com.br/` (robots 404, 11:09:11, 200). CET publishes each
  interdição as a news page, e.g. `/noticias/2026/11/03/tunel-jose-roberto-f-melhem-sera-interditado-para-limpeza-(19).aspx`;
  four were linked from the home page. No feed, no API, no coordinates. The page
  `/consultas/eventos/.aspx` describes CET's event authorisations; `sslcetsp1.cetsp.com.br/monitransmapa/IMG5/ocorrencias.asp`
  (linked from the home page) answered 404.
- Terms: only privacy policies (PDF) are linked; nothing on reuse. Even with permission
  the notices are text without coordinates (unlocated feeds are off).

### GeoSampa works occupying public roads — NOT_A_SOURCE

- `wfs.geosampa.prefeitura.sp.gov.br` (robots 404). GetCapabilities (11:08:05, 200): 485
  layers; `ows:Fees NONE`, `ows:AccessConstraints NONE` (not a licence). Candidate layer
  `geoportal:controle_uso_via_publica_geoinfra` "Controle de uso de vias públicas – Obras
  (Geoinfra)": GetFeature GeoJSON EPSG:4326 (11:08:45, 200): 1,902 points, all
  `tx_tipo_obra` EMERGENCIA, `tx_status_obra` ENCERRADA 977 / INFORMADA 925, utility
  companies (Sabesp, Comgás, Eletropaulo, Claro), `dt_carga` 2026-01-31 on every row.
  No start or end: a nine-month-old snapshot. Other layers (accidents, flooding
  occurrences, feiras livres) are historical or recurring.

### ARTESP (São Paulo state concessions) — NOT_A_SOURCE, watch

- robots.txt: `Disallow: /api/`, `Crawl-Delay: 10` (dataset pages and downloads allowed).
- "Ocorrências" (`/dataset/ocorrencias`): CSVs of vehicle breakdowns per year (2020–2026)
  and floods/erosion; updated monthly: history, not live.
- "Programação de Obras e Serviços de Conservação" (`/dataset/programacao-de-obras`):
  only circulars, XLSX templates, JSON schemas and *example* GeoJSON for concessionaires'
  annual and monthly works programmes. If ARTESP publishes the real programmes, they
  would be a good PERMITTED source.
- Terms (`/terms`, "Última atualização: Junho de 2025"): "Todos os dados publicados neste
  Portal são considerados públicos, salvo indicação em contrário, e são disponibilizados
  para uso gratuito, reprodução e redistribuição sob as seguintes condições: Atribuição …
  Integridade dos Dados … Não Endosso". Datasets show "Creative Commons Attribution". The
  footer's "não podem ser reproduzidos … sem permissão expressa" covers the site's other
  content (section 6 of the terms).

### Curitiba — NOT_A_SOURCE (terms permissive)

- `dadosabertos.curitiba.pr.gov.br` (robots 404). 32 datasets. Rules
  (`/informacoes/regrasutilizacao/5`): "O Portal de Dados Abertos de Curitiba não
  estabelece restrições específicas relativas ao uso dos dados sendo, portanto, livre para
  qualquer finalidade ou atividade", with citation of the source and a set statement.
- Nothing fits: SIGMU is a relational dump of maintenance service orders since 2016
  (street codes, no coordinates; worker and driver names), "Eventos PMC" a city events
  agenda (addresses, not road closures). GeoCuritiba ArcGIS (`geocuritiba.ippuc.org.br`):
  base maps and cycleways only.

### Rio de Janeiro portals — NOT_A_SOURCE

- data.rio Hub search API (robots `Crawl-delay: 60`, obeyed): "interdição" 0, "transito" 0,
  "ocorrencias" 3 (land-cover layers). Rio's ArcGIS server `pgeo3.rio.rj.gov.br`:
  `Transporte_Trafego` has cycle network and public transport only; `Conservacao`,
  `GeoVias`, `Infraestrutura` empty; `Defesa_Civil` not opened.

### Others

- **São Paulo city CKAN** `dados.prefeitura.sp.gov.br`: robots.txt "User-agent: * /
  Disallow: /". Not queried. RESTRICTED for automated access.
- **Porto Alegre CKAN** `dadosabertos.poa.br`: robots `Disallow: /api/`; the HTML listing
  (62 datasets) ignored the search and page parameters and showed the same 20 finance and
  administration datasets each time. Not exhaustive.
- **dados.gov.br**: robots.txt answered 401. Third-party guides say the API
  (`https://dados.gov.br/dados/api/publico/conjuntos-dados`) needs a key in the header
  `chave-api-dados-abertos`, generated after logging in with a gov.br account (CPF).
- **PRF, ANTT, ARTESP "Acidentes"**: historical accident files (as on 16 October).
- **ArcGIS Online** (Brazil terms): 12 "interdição" items, 8 "bloqueio/desvio/obras
  viárias" items: personal or survey layers, DNIT disaster-response layers of the 2024
  Rio Grande do Sul floods (last modified January 2025), no current official feed.
- **Unreachable from this network**: Belo Horizonte (`ckan.pbh.gov.br` and
  `bhmap.pbh.gov.br`: 403 "Acesso Bloqueado"), ANTT (`dados.antt.gov.br`: "Request
  Rejected"), DNIT (`servicos.dnit.gov.br`: timeout; WebFetch: connection refused), DER-SP
  (robots answered 202, treated as disallow), Brasília `dados.df.gov.br` and Recife
  `dados.recife.pe.gov.br` (timeouts, two tries each), Fortaleza `dados.fortaleza.ce.gov.br`
  (DNS failure). Several Brazilian government hosts seem to refuse non-Brazilian networks.

### What the user must do for Brazil

1. **Rio COR**: write to the Escritório de Dados (Prefeitura do Rio) asking (a) whether
   REI may use the COR occurrences commercially given the CC BY-ND 3.0 licence (REI turns
   records into events), or offer them under CC BY, and (b) for keyless access (the
   `api.dados.rio` endpoint, or a public file). Otherwise BigQuery needs a Google account
   and a Google Cloud project with billing (BigQuery bills queries beyond its free tier).
2. **CET São Paulo**: ask CET for permission and a machine-readable list of interdições
   with locations.
3. **Retry from a Brazilian network** (or ask the bodies): DNIT road conditions, Belo
   Horizonte BHTrans, Brasília and Recife portals, ANTT. These could not be checked.
4. **dados.gov.br** search needs a gov.br login and API key (the user's decision).
5. **Watch ARTESP**'s "Programação de Obras" for real programme files (terms permit use).

## Requests

Request log with every URL, time and status: `requests.log` in the session scratchpad
(`…/scratchpad/br_my/`). Scratch copies of the LLM layers were cleaned of officer,
applicant and editor names, phones and e-mails; the Curitiba pages that named people were
deleted.
