# Official road-event sources: Asia, Middle East and Africa (16 October 2026)

Research only. Nothing was connected, changed or scheduled. India and South
Africa were not re-contacted (see
[India local and official sources](india-local-and-official-sources-2026-10-16.md)
and [South Africa sources](south-africa-sources-2026-10-16.md)); no news
publisher and no gdeltproject.org host was contacted.

**When and how.** 16 October 2026, 12:21-12:38 UTC. 59 requests to 21 hosts,
at most 8 on one host (data.ibb.gov.tr), one at a time per host, at least
2.5 s apart on a host (11 s on data.ibb.gov.tr, which sets `Crawl-delay: 10`).
User-Agent `JSAN-REI/1.0 (road event intelligence research)`. robots.txt was
requested first on every host. Redirects were not followed. TLS verified
(certifi plus the Windows store). No logins, registrations, key sign-ups,
CAPTCHAs, proxies or browser disguise. Candidate URLs were found by web search
(no fetching) and from official catalogue metadata (data.gov.hk and data.gov.tw
APIs, both allowed by robots.txt). Raw responses and scripts are in the
session scratchpad (`research/global/asia-mea-raw`, `research/global/asia-mea-tools`).

**Verdicts (REI standard).** PERMITTED = re-use including commercial use is
explicitly allowed (possibly with attribution). NEEDS_KEY = free key or
registration required (not done). ASK_PERMISSION = no licence, or terms
silent, or re-use only after asking. RESTRICTED = non-commercial only, or
automated access forbidden, or robots.txt disallows the needed path. This is
a reading of published terms, not legal advice.

## Main findings

1. **Eight PERMITTED, working sources in four places, six with coordinates
   and dates in the data.** Hong Kong (3), Taiwan (3 cities), Japan
   (Tokushima Prefecture) and Turkey (Istanbul). All were fetched without a
   key today.
2. **Best live sources for REI:** Tokushima road restrictions (234 current
   restrictions, every one with start, end and a point, refreshed every 10
   minutes, CC BY); Taipei today's road works (1,169 sites with points and
   lines, approved start/end, refreshed every 10 minutes); Taichung traffic
   maintenance plans (1,172 records, 883 with WGS84 points or lines);
   New Taipei excavation permits (2,150, all with points); Hong Kong
   road-closure notices (241, start date in data, no coordinates).
3. **Istanbul is the richest dataset, but it is an archive:** 262,909
   traffic-control-centre announcements since 2013, every row with
   coordinates and start and end times, under a licence that allows
   commercial use. The file was last updated 12 Oct 2026 and holds ended
   events, so it suits backfill and analysis, not live display.
4. **Keys needed:** Singapore LTA DataMall, Seoul TOPIS incidents, Taiwan TDX,
   Korea national ITS / data.go.kr.
5. **Nothing official and machine-readable was found** for Malaysia,
   Thailand, Philippines, Indonesia, Vietnam, Saudi Arabia, Abu Dhabi, Jordan
   or any African country researched (Kenya, Nigeria, Egypt, Morocco, Ghana,
   Rwanda, Namibia, Botswana). Dubai Pulse, the Taiwan police-broadcast feed
   and Tel Aviv GIS could not be reached from this network.
6. **Personal data:** the three Taiwanese works feeds carry site-contact
   names and mobile numbers. A connector must drop those fields.

## Summary table

"Records" = records in today's response. Start/end = event times in the data
(not publication time). Robots = result for the `*` group.

| Country | Source | URL | Format | Auth | Records | Geometry | Start/end | Licence | Commercial | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Japan (Tokushima Pref.) | Tokushima road restrictions (県土防災情報システム通行規制情報) | `https://bousai.pref.tokushima.lg.jp/00000_00000_00000.xml` + `/Symbol_08.xml` | XML (2 files) | None | 234 (as of 21:30 JST) | Point (WGS84) for all 234, joined by id | Start and end on all 234 | CC BY (resource) + portal terms | Yes, attribution | **PERMITTED** |
| Taiwan (Taipei) | Taipei today's construction (臺北市今日施工資訊) | `https://tpnco.blob.core.windows.net/blobfs/Todaywork.json` | GeoJSON (TWD97) | None | 1,169 | Point + MultiPolygon (709) / MultiLineString (460), EPSG:3826 | Approved start/end dates (ROC calendar) + hours text | Taiwan OGDL v1.0 | Yes, attribution | **PERMITTED** |
| Taiwan (Taichung) | Taichung traffic maintenance plans (臺中市交通維持計畫資料集) | `https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=c3bf6ac0-3e2a-4fc1-9bc1-dbf4ef43c30e` | JSON (CSV twin) | None | 1,172 | WGS84 point(s) in text field on 883 | Start/end date + start/end hour on all | Taiwan OGDL v1.0 | Yes, attribution | **PERMITTED** |
| Taiwan (New Taipei) | New Taipei road excavation permits (新北市政府道路挖掘資訊) | `https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv/file` | CSV | None | 2,150 | Point (TWD97) on all | Start/end date on all + period text | Taiwan OGDL v1.0 | Yes, attribution | **PERMITTED** |
| Hong Kong | TD notices on temporary road closure | `https://www.td.gov.hk/datagovhk_tis/traffic-notices/Notices_on_Temporary_Road_Closure.xml` | XML | None | 241 | None (road names, lamp-post numbers) | Start date in data; end date only in notice text | DATA.GOV.HK terms v1.2 | Yes, attribution + indemnity | **PERMITTED** |
| Hong Kong | TD/HyD roadworks location | `https://resource.data.one.gov.hk/td/roadworks-location/get_all_the_roadworks.geojson` | GeoJSON / JSON | None | 2 | Point (WGS84) | Start and end on both | DATA.GOV.HK terms v1.2 | Yes | **PERMITTED** |
| Hong Kong | TD Special Traffic News (2nd generation) | `https://www.td.gov.hk/en/special_news/trafficnews.xml` | XML | None | 1 | LATITUDE/LONGITUDE elements present, empty today | Announcement time only; no end | DATA.GOV.HK terms v1.2 | Yes | **PERMITTED** |
| Turkey (Istanbul) | IBB UYM traffic announcements (archive) | `https://data.ibb.gov.tr/dataset/.../download/ulasm_yonetim_merkezi_trafik_duyurular_verisi_20261012t120500.csv` | CSV, 61 MiB | None | 262,909 (2013-02 to 2026-10-12) | Point (WGS84) on all | Start and end on all | IBB Açık Veri Lisansı v1.0 | Yes, attribution | **PERMITTED** (historical; not live) |
| Singapore | LTA DataMall Traffic Incidents, Road Works, Faulty Traffic Lights, Flood Alerts | `https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents` | JSON | AccountKey | not read (404 without key) | Incidents: lat/lon (earlier REI research) | Not established | Singapore Open Data Licence v1.0 (earlier REI research) | Yes | NEEDS_KEY |
| South Korea (Seoul) | Seoul TOPIS real-time incidents (서울시 실시간 돌발 정보, AccInfo) | `http://openapi.seoul.go.kr:8088/{key}/xml/AccInfo/1/{n}/` | XML / JSON | Personal key (public `sample` key gives 5 rows) | 5 (sample cap) | GRS80 TM x/y | Occurrence and expected clearance date/time | KOGL Type 1 (search result) | Yes (search result) | NEEDS_KEY |
| Taiwan | TDX (national road/freeway data) | `https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/Freeway` | JSON | Key | 0 (HTTP 401 "Valid API Key Required") | — | — | not read | — | NEEDS_KEY |
| South Korea | National ITS / data.go.kr incident APIs | its.go.kr, data.go.kr 15126267, 15160258 | XML / JSON | serviceKey | not fetched | Coordinates (search results) | Incident and expected end (search results) | not read | — | NEEDS_KEY (not verified) |
| Taiwan | Police Broadcasting Service live road reports (警廣即時路況) | `https://rtr.pbs.gov.tw/NMP103_PbsWS/resources/roadData/opendata` | JSON | None (per catalogue) | — | x1/y1 per catalogue | happendate/happentime per catalogue | Taiwan OGDL v1.0 (catalogue) | Yes | Unreachable (2 timeouts) |
| UAE (Dubai) | Dubai Pulse traffic incidents | `https://www.dubaipulse.gov.ae/data/dp-traffic/dp_traffic_incidents-open` | CSV / API | API key for API (search result) | — | lat/lon (search result) | Accident time (search result) | not read | — | Unreachable (2 timeouts) |
| Israel (Tel Aviv) | Tel Aviv-Yafo GIS | `https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer` | ArcGIS REST | — | — | — | — | not read | — | Unreachable (HTTP 571, blocked outside Israel) |
| Israel | data.gov.il | `https://data.gov.il/` | CKAN | — | — | — | — | not read | — | RESTRICTED for automation (robots.txt `Disallow: /api/`; site search returned CloudFront 403) |
| Qatar | data.gov.qa (Opendatasoft) | `https://www.data.gov.qa/` | ODS | — | 1,953 datasets in sitemap; road-related ones are accident statistics only | — | — | not read | — | No event data; robots.txt disallows `/api/` and downloads for `*` |

## Per-source notes

### Japan: Tokushima Prefecture road restrictions (PERMITTED)

- **Catalogue page:** https://opendata.pref.tokushima.lg.jp/dataset/414.html
  ("徳島県県土防災情報システム通行規制情報", created 22 Apr 2015, updated
  20 May 2025). "規制情報現況（10分単位で更新）･･･ XMLで提供"; "※本日規制中である
  規制ランク「中」以上の規制情報を表示します" (shows today's restrictions of
  rank "medium" or higher: full closures, vehicle closures, weight, height and
  time closures, chain rules, and others; 16 types listed).
- **Endpoints:** `https://bousai.pref.tokushima.lg.jp/00000_00000_00000.xml`
  (restriction details) and `https://bousai.pref.tokushima.lg.jp/Symbol_08.xml`
  (map points). Both HTTP 200, `text/xml`, Last-Modified 12:30:11 GMT; the
  details file states `<cd>2026/10/16 21:30</cd>` (JST).
- **Content:** 234 restrictions (`trd`), grouped by road kind (`rkn`: 県道
  55 route groups, 国道 10) and route (`rn`). Each has `rid`, start and end
  section names (`ssn`, `sfn`), restriction (`rc`: 時間通行止 81, 片側交互通行
  71, 車両通行止 31, 車線規制 23, 全面通行止 13, ...), reason (`rr`: 道路工事のため
  136, 電気工事 52, 調査・点検 14, ...), start `lsd` and end `led`
  ("2026/03/16 10:00" to "2026/11/27 15:00"; present on all 234; newest start
  2026/11/04), excluded days (`ed`), direction (`rd`) and the managing office
  (`ofn`). `Symbol_08.xml` has 234 `<Reg>` with `<Pt>lon,lat</Pt>` (WGS84);
  `Id` characters 2-11 equal `rid` (all 234 joined). Language Japanese. The
  field definitions are in the catalogue's `OurOpenData_XML仕様.xlsx`
  (not downloaded; that file is CC BY-ND).
- **Licence:** the catalogue marks both XML resources "表示（CC BY）". Terms
  (https://opendata.pref.tokushima.lg.jp/kiyaku.html), 第２条: "コンテンツを
  利用する際は出典を記載してください。... 出典：徳島県オープンデータポータルサイト
  （当該ページのURL）"; when edited, state that it was edited and do not present
  it as made by the prefecture; prohibited use is limited to "法令、条例又は
  公序良俗に反する利用" and "徳島県及び県民の安全に脅威を与える利用". No ban on
  commercial or automated use. No rate limit published.
- **Robots:** opendata host `User-agent: * / Allow: /`; bousai host 404 (no rules).
- **Attribution to use:** "出典：徳島県オープンデータポータルサイト
  (https://opendata.pref.tokushima.lg.jp/dataset/414.html), CC BY".

### Taiwan: Taipei today's construction (PERMITTED)

- **Catalogue:** https://data.gov.tw/dataset/145614 (臺北市 今日施工資訊;
  catalogue API `https://data.gov.tw/api/v2/rest/dataset/145614`): updated
  every 10 minutes, licence code 1 (Taiwan Open Government Data License v1.0),
  cost free. Provider: Taipei City road excavation management.
- **Endpoint:** `https://tpnco.blob.core.windows.net/blobfs/Todaywork.json`,
  HTTP 200, 2.66 MB, Last-Modified 12:20:42 GMT. UTF-8 with BOM.
- **Content:** FeatureCollection of 1,169 features. Geometry is a Point in
  TWD97 TM2 (EPSG:3826, for example `[309050.617, 2770535.957]`); `Positions`
  holds the works area (709 MultiPolygon, 460 MultiLineString) in the same
  system. Fields: `Ac_no` (approval number), `AppMode` (5 = 道路維護 709,
  0 = 施工通報 460), `AppTime` (report time, ROC calendar; newest
  "115/10/16 14:20:47", 28 reported today), `C_Name` (district), `Addr`,
  `Cb_Da`/`Ce_Da` approved start/end (ROC dates, for example "113/01/24" to
  "115/12/31"), `Co_Ti` (hours text), `NPurp` (purpose), `IsBlock`
  (是 103, 否 1,066), `DLen`. 1,129 are within their approved dates today.
  Personal data: `Tc_Ma`/`Tc_Ma3` names are masked ("蔡ＯＯ") but `Tc_Tl`/
  `Tc_Tl3` are mobile numbers; drop them.
- **Licence (quoted from https://data.gov.tw/license):** "The Data Providing
  Organization grants User a perpetual, worldwide, non-exclusive, irrevocable,
  royalty-free copyright license to reproduce, distribute, publicly transmit,
  ... compile, adapt to the Open Data provided for any purpose, including but
  not limited to making all kinds of Derivative Works either as products or
  services." Attribution: "User ... must make an explicit notice of statement
  as attribution requested in the Exhibit ... If User fails to comply with the
  attribution requirement, the rights granted under this License shall be
  deemed to have been void ab initio." Exhibit format: "提供機關／單位 [年份]
  [開放資料釋出名稱與版本號] 此開放資料依政府資料開放授權條款 (Open Government Data
  License) 進行公眾釋出，使用者於遵守本條款各項規定之前提下，得利用之。政府資料開放授權
  條款： https://data.gov.tw/license". Compatible with CC BY 4.0. Section 五
  lets the provider stop supply where privacy may be infringed. No rate limit
  published.
- **Robots:** blob host answers robots.txt with HTTP 400 XML (no rules);
  data.gov.tw robots.txt answered HTTP 500 (no rules).

### Taiwan: Taichung traffic maintenance plans (PERMITTED)

- **Catalogue:** https://data.gov.tw/dataset/84900 (臺中市交通維持計畫資料集),
  daily, licence code 1, modified 2026-10-05. Description: "提供本市影響道路交通
  情形資訊" (works affecting road traffic). OpenAPI doc:
  https://datacenter.taichung.gov.tw/swagger/yaml/387290000H (not fetched).
- **Endpoint:** JSON `https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=c3bf6ac0-3e2a-4fc1-9bc1-dbf4ef43c30e`
  (CSV: `rid=8e577f22-7a25-4ff8-81d7-a2ccdab843c5`). HTTP 200, 504 KB.
- **Content:** 1,172 records; `Id`, `Type` (codes 4: 644, 1: 337, 6: 145,
  2: 38, 3: 8; meanings not in the metadata read), `Name`, `Address`,
  `Company`, `Contact`, `Telephone`, `StartDate`/`EndDate` (ISO dates; start
  2021-03-25 to 2026-10-25, end 2026-10-16 to 2031-10-16), `StartTime`/
  `EndTime` (hours, for example 9 and 16), `LatLng` (text such as
  `{lat:24.1547336,lng:120.6621501}`, several points for line works; present
  on 883), postal and area codes. 676 are within their dates today. Personal
  data: contact names and mobile numbers; drop them.
- **Licence:** Taiwan OGDL v1.0, as above. **Robots:** robots.txt returns the
  site's JavaScript app page (no rules).

### Taiwan: New Taipei road excavation permits (PERMITTED)

- **Catalogue:** https://data.gov.tw/dataset/122989 (新北市政府道路挖掘資訊),
  daily, licence code 1. OpenAPI: https://data.ntpc.gov.tw/api/v1/openapi/units/1060000
  (not fetched). A 10-minute variant, 新北市道路挖掘即時施工資訊
  (https://data.gov.tw/dataset/177913), was found by search but not fetched.
- **Endpoint:** `https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv/file`,
  HTTP 200, `text/csv`, 1.75 MB, UTF-8 with BOM.
- **Content:** 2,150 permits, all "已核發許可證" (permit issued); `casetype`
  一般 819, 民生 424, 新建房屋 422, 緊急 286, 計畫 199; `digsite` address;
  `casestartdate_yyymmddroc`/`caseenddate_yyymmddroc` (start 1111212-1151117,
  end 1130203-1170511); `workperiod` text ("時段性施工，115年10月12日起115年10月20日止，
  共9日。日間09時至16時"); `twd97x`/`twd97y` (EPSG:3826) on all 2,150; newest
  `examdate` 1151016 (today). 516 within their dates today. Excavation permits
  do not say whether traffic is closed. Personal data: `construction_man`,
  `supervise_man` (unmasked names) and phone fields; drop them.
- **Licence:** Taiwan OGDL v1.0. **Robots:** robots.txt answered HTTP 200 with
  a WAF page ("Request Rejected"), so no rules could be read; the CSV request
  itself was served.

### Hong Kong: Transport Department and Highways Department (PERMITTED)

- **Licence (all three):** DATA.GOV.HK Terms and Conditions of Use, Version
  1.2, last updated 26 May 2025 (https://data.gov.hk/en/terms-and-conditions):
  "You are allowed to browse, download, distribute, reproduce, hyperlink to,
  and print the Data for both commercial and non-commercial purposes on a
  free-of-charge basis on condition that:- ... you shall identify clearly the
  source of the Data and acknowledge the Government and the Relevant
  Organisations' ownership of the intellectual property rights in the Data
  ...; you shall indemnify the Government and the Relevant Organisations
  against any allegations or claims of infringement ...; you shall also give
  proper attribution to the Government, the Relevant Organisations and
  DATA.GOV.HK." Data "AS IS". No rate limit or storage restriction stated.
  robots.txt: 404 on data.gov.hk, www.td.gov.hk and resource.data.one.gov.hk.
  Suggested attribution: "Source: Transport Department / Highways Department,
  HKSAR Government, via DATA.GOV.HK".
- **Temporary road closure notices** (dataset hk-td-tis_22-traffic-notices,
  "Daily and as necessary"; spec
  https://www.td.gov.hk/datagovhk_tis/traffic-notices/dataspec/traffic_notices_dataspec.pdf,
  not fetched): 241 `<Notice>` with `TNID`, type and district ids, titles in
  EN/TC/SC, `StartEffectiveDate` (dd.mm.yyyy; 237 in 2026, newest start
  06.11.2026, TNID 89335) and the notice body as escaped HTML in `Content_EN/
  TC/SC`. End dates and hours are only in the body ("from 7.00 am to 7.00 pm
  daily on 25 October 2026 and 1, 8 and 15 November 2026 and from 9.00 pm to
  6.00 am the following day daily during the period from 22 October 2026 to
  13 November 2026"). Locations are named roads and lamp-post numbers, so
  geocoding is needed. Seven sibling XMLs on the same path: Prohibited Zone,
  Temporary Speed Limits, Clearways, Public Transports, Special Traffic and
  Transport Arrangement, Expressways, Other Notices (not fetched).
- **Roadworks location** (dataset hk-td-tis_18-roadworks-location, "As and
  when necessary"; spec
  https://static.data.gov.hk/td/roadworks-location/dataspec/roadworks_location_data_specification.pdf):
  HyD roadworks "involving lane closure on public roads with a speed limit of
  70km/hr or above", in progress or starting within 12 hours. Today 2
  features: Point, "Road resurfacing works", Tuen Mun Road near Belvedere
  Garden, `starttime` "2026-10-16 22:00", `endtime` "2026-10-17 06:00",
  `worksstatus` "Under Preparation", lane "Slow", `lastupdatetime`
  "2026-10-16 16:45:48" (HKT). Also on the CSDI portal as an API.
- **Special Traffic News, 2nd generation** (dataset
  hk-td-tis_19-special-traffic-news-v2, real-time; spec
  http://static.data.gov.hk/td/special-traffic-news/en/Data_Specification_for_STN_Eng_v4.0.pdf,
  not fetched): 1 message today, `IN-26-07590`, "Road Incident" / "Traffic
  Accident", Island Eastern Corridor (Central bound) near Quarry Bay Park,
  `ANNOUNCEMENT_DATE` 2026-10-16T19:59:00, status "UPDATED", "Part of the
  lanes ... which was closed due to traffic accident is re-opened to all
  traffic." `LATITUDE`/`LONGITUDE` exist but were empty. No end time.

### Turkey: Istanbul IBB traffic announcements (PERMITTED, historical)

- **Dataset:** https://data.ibb.gov.tr/dataset/ulasim-yonetim-merkezi-trafik-duyurulari-verisi
  ("Ulaşım Yönetim Merkezi(UYM) tarafından 2013'den beri yapılan anlık
  duyuruları, lokasyon bazında içeren veri setidir."). Data and metadata last
  updated 12 Oct 2026; no update frequency stated.
- **Endpoint:** the CSV link on the dataset page,
  `https://data.ibb.gov.tr/dataset/8d47d214-eca8-494d-9457-d134dde561ff/resource/1c043914-8a76-4793-bae9-c60a68c7d389/download/ulasm_yonetim_merkezi_trafik_duyurular_verisi_20261012t120500.csv`.
  The file name contains the upload time, so a connector must read the current
  link from the dataset page. HTTP 200, 64.2 MB.
- **Content:** 262,909 rows; columns `announcement_id`,
  `announcement_starting_datetime`, `announcement_ending_datetime`,
  `announcement_title` (Turkish text, for example "Kasımpaşa Tüneli, Kasımpaşa -
  Hasköy yönü, Bakım-Onarım Çalışması nedeni ile Tüm Şeritler trafiğe
  kapalıdır."), `announcement_type_desc`, `intervention_datetime`,
  `accident_type`, `accident_description`, `closed_lane`, `latitude`,
  `longitude`. Coordinates and both times on every row. Types: Kaza Bildirimi
  126,167; Araç Arızası 95,917; Bakım-Onarım Çalışması 27,036; Yoğun Trafik
  7,014; Yolun Trafiğe Kapanması 1,867; Çevre Düzenlemesi 1,704; Haber 1,072;
  Araç Yangını 914; Yol Yapım Çalışması 386; Alt Yapı Çalışması 280; Etkinlik
  117; Yolu Etkileyen Hava Koşulu 67; Kontrollü Kapama (Protokol) 15; others.
  20,728 rows in 2026; newest start 2026-10-12 02:24:49. Ended events only.
- **Licence** (https://data.ibb.gov.tr/license, İBB Açık Veri Lisansı v1.0):
  "Lisans Veren, aşağıdaki koşullara tabi bilgileri kullanmanız için size dünya
  çapında, telifsiz, daimi, münhasır olmayan bir lisans sunar." ...
  "Bilgiyi, ticari olarak ve ticari olmayan şekilde, örneğin diğer Bilgilerle
  birleştirerek veya kendi ürününüze veya uygulamanıza ekleyerek
  kullanabilirsiniz." Attribution: cite the source and link the licence; if
  the provider gives no wording, use "Atıf 4.0 Uluslararası (CC BY 4.0)
  kapsamında lisanslanan kamu sektörü bilgilerini içerir." Excludes personal
  data. Compatible with CC BY 4.0 and ODC-BY. Terms of use
  (https://data.ibb.gov.tr/terms_of_use): acceptance by download, KVKK
  compliance, "as is", "Veri kümelerinin eski sürümleri saklanmayacaktır" (old
  versions are not kept); no ban on automated or commercial use.
- **Robots:** `Disallow: /api/` (so the CKAN API and datastore must not be
  used), `Crawl-delay: 10`. Dataset pages and download links are allowed.
- Also seen: "İnşaat Aşamasındaki Kavşaklar" (junctions under construction),
  three static XLSX lists (03.2024 and later), not useful for live events.

### NEEDS_KEY

- **Singapore, LTA DataMall.** The dynamic-data page
  (https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html) lists
  Traffic Incidents ("Accidents, Vehicle Breakdowns, Road Blocks, Traffic
  Diversions etc.", real-time), Road Works ("approved road works to be carried
  out/being carried out", real-time), Faulty Traffic Lights and Flood Alerts
  (PUB). Access via "Request for API Access". Without a key,
  `https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents` answered
  HTTP 404 "The requested API was not found". Licence: Singapore Open Data
  Licence v1.0 per earlier REI research (see
  [global research](../global-free-source-research.md)); the website's own
  terms (https://datamall.lta.gov.sg/content/datamall/en/term-of-use.html)
  say "Except as otherwise provided, the Contents of this website shall not be
  reproduced ... without the prior written permission of LTA", which covers
  the website, not the licensed datasets. robots.txt (`Crawl-delay: 1`,
  `Disallow: /*.json`, `/*.pdf`) applies to the website host.
- **Seoul, TOPIS real-time incidents** (data.seoul.go.kr OA-13315). With the
  publicly documented `sample` key,
  `http://openapi.seoul.go.kr:8088/sample/xml/AccInfo/1/5/` returned 5 rows
  (the sample cap): `acc_id`, `occr_date`/`occr_time`, `exp_clr_date`/
  `exp_clr_time`, `acc_type`/`acc_dtype`, `link_id`, `grs80tm_x`/`grs80tm_y`,
  `acc_info` (for example 봉은교 "양방향 전면통제" from 2026-04-07 to 2027-02-28,
  and lane works on 창경궁로 on 16 Oct 20:03-23:00). Full access needs a
  personal key. Licence per search result: 공공누리 제1유형 (attribution,
  commercial use and modification allowed); the page was not fetched.
- **Taiwan, TDX.** `https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/Freeway?$top=5&$format=JSON`
  answered HTTP 401 "Valid API Key Required". Search results say anonymous
  use is limited and blocks tool user-agents; registration needs e-mail
  verification and approval.
- **South Korea, national ITS and data.go.kr** (Daegu incident API 15126267,
  MOLIT road disaster/control API 15160258): serviceKey required; not fetched.

### ASK_PERMISSION or RESTRICTED (from search results only; not fetched)

- **Niigata road restrictions (via SIP4D on the Miyazaki CKAN):** "災害対応を
  目的として公開しています。データの二次利用等については防災科研までお問い合わせください"
  → ASK_PERMISSION.
- **Miyazaki Prefecture road restrictions (MVT/PNG tiles):** licence shown as
  "Other (Non-Commercial)" → RESTRICTED.
- **Macau DSAT:** traffic data under a trial open-data policy that requires a
  written application and a confidentiality agreement → ASK_PERMISSION.
- **Shizuoka City "しずみちinfo"** (CC BY REST API): service ended 30 Sep 2026;
  successor is the prefecture's system, whose open-data terms were not found.

### Unreachable or blocked

- **Taiwan Police Broadcasting Service** (`rtr.pbs.gov.tw`): robots.txt timed
  out over HTTPS and over HTTP. The documentation host `od.moi.gov.tw` also
  timed out twice. The catalogue (data.gov.tw 15221) describes the last 1,000
  reports with `x1`/`y1`, `happendate`/`happentime`, `roadtype`, `comment`,
  licence OGDL v1.0: the strongest Taiwan candidate if it can be reached from
  another network.
- **Dubai Pulse** (`www.dubaipulse.gov.ae`): robots.txt timed out twice.
- **Tel Aviv-Yafo GIS** (`gisn.tel-aviv.gov.il`): HTTP 571 page: "access to
  certain information and digital services ... is restricted when connecting
  from outside Israel."
- **data.gov.il:** robots.txt `Disallow: /api/`; the website search page
  answered CloudFront HTTP 403.
- **Turkey KGM** (`www.kgm.gov.tr`): the guessed road-status page returned
  404; KGM's daily road-status bulletin was not located.

## Not found (web search only)

No official machine-readable road-event feed was found for: Japan nationally
(MLIT road-info system, xROAD publishes traffic volumes only; JARTIC terms not
read), Tokyo, Osaka, Malaysia (LLM), Thailand (BMA Traffic has no documented
API; Traffy Fondue is citizen reports), Philippines (MMDA), Indonesia
(Jakarta datasets are static), Vietnam, Saudi Arabia, Abu Dhabi (ITC posts
closures on social media), Qatar (Ashghal publishes news pages; the open-data
portal has accident statistics only), Jordan, Kenya (KeNHA/KURA notices via
press), Nigeria (LASTMA), Egypt, Morocco (ADM Trafic is an app), Ghana,
Rwanda, Namibia and Botswana.

## Sample files (PERMITTED, working)

In `C:\Users\JSANCO~1\AppData\Local\Temp\claude\C--Users-Jsan-Consulting-Desktop-JSAN-Road-Event-Intelligence\b9dd17db-5e5d-47c6-ab68-7a67344a5a5d\scratchpad\research\global\asia-mea\`
(request URL, time and headers for each are in `SAMPLES.txt` there):

- `jp-tokushima-road-restrictions_2026-10-16.xml` and `jp-tokushima-road-restriction-points_2026-10-16.xml`
- `tw-taipei-todaywork_2026-10-16.json`
- `tw-taichung-traffic-maintenance-plans_2026-10-16.json`
- `tw-new-taipei-road-excavation_2026-10-16.csv`
- `hk-td-temporary-road-closure-notices_2026-10-16.xml`
- `hk-td-hyd-roadworks-location_2026-10-16.geojson`
- `hk-td-special-traffic-news_2026-10-16.xml`
- `tr-istanbul-uym-traffic-announcements_2026-10-16.csv` (64 MB)

The scratchpad is session-specific; copy the files if they are needed later.

## Not verified

- Field definitions: Tokushima XML spec (XLSX), Hong Kong STN v4.0 and
  traffic-notices specs, Taichung `Type` codes, Taipei `AppMode` codes other
  than the two seen.
- Update frequencies stated only in catalogues (Taipei 10 min, Taichung and
  New Taipei daily, Tokushima 10 min); Istanbul's frequency is not stated.
- Whether Hong Kong STN messages ever carry coordinates.
- Singapore DataMall current endpoint paths (the 404 may reflect the missing
  key or a changed path) and whether the key is free.
- Seoul, Korea ITS, TDX and Dubai Pulse licence pages (search results only).
- Taiwan PBS feed content and Dubai Pulse content (unreachable from this
  network; a retry from another network may differ).
- New Taipei's 10-minute dataset (177913), Kaohsiung and Taoyuan works data,
  other Japanese prefectures, and İzmir or Ankara open data.

## Access-rule notes

- **Tel Aviv:** robots.txt answered HTTP 571 (a geo-block page, not a
  robots file). One further request (the ArcGIS layer list) was sent and also
  got 571. Under a strict reading, nothing beyond robots.txt should have been
  requested.
- **New Taipei, Taichung, TDX, data.gov.tw:** robots.txt returned an HTML
  page (WAF rejection, app shell) or HTTP 500. These were treated as "no
  rules", as in the earlier India research.
- **Seoul:** the request used the city's publicly documented `sample` key
  (5-row cap). No account or key was created.
- **Taiwan PBS:** the two attempts were HTTPS then HTTP; both timed out.
