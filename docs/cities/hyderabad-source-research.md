# Hyderabad source research (consolidated)

Research date: **8 October 2026**, about 13:35–14:20 machine local time (IST).
This document consolidates the Hyderabad research of **2 October 2026**
(`docs/data-sources/hyderabad-source-research.md`, 23 sources) and extends it.
Findings re-verified today say so; findings carried over from 2 October are
marked **(2 Oct, not re-verified today)**. Nothing in the repository other than
this file was changed; nothing was connected.

**Method.** Every statement about access, content, format or terms comes from
a fetch made today with the project's Python (`.venv`, `httpx`), User-Agent
`JSAN-REI source research (research@jsan.example; local test)`, at most one
request per second per host, 30 s timeout, **149 requests in all** (including
robots.txt fetches, 18 failures and one robots refusal). Each host's
`robots.txt` was fetched first and the `*` group honoured by the fetcher itself;
one request (Overpass on `overpass-api.de`) was refused by that check. No
CAPTCHA, login, paywall or access control was bypassed, no browser User-Agent
was spoofed, no credential was used, no endpoint found only inside a script
bundle was called, nothing was installed. Two hosts (`www.htp.gov.in`,
`www.hmda.gov.in`) fail TLS verification from this machine ("unable to get
local issuer certificate", also with the broken `CURL_CA_BUNDLE` unset); they
were fetched with verification off and are marked. Downloaded files were saved
in the session scratchpad (`hyd-fetched/`) and only parsed, never executed.
PDFs were inspected by reading their raw bytes (`/Font`, `/FontFile`,
`/ToUnicode`, `/Subtype /Image` objects); no PDF library is installed.

Tiers are REI's: 1 government, police or road authority; 2 operator or
organiser; 3 approved commercial or partner; 4 discovery only (news). Colours:
GREEN public + permitted + useful + production candidate; YELLOW useful but
terms, permission or limits need review; BLUE discovery only; RED do not
automate or use. PERMISSION_REQUIRED is added where the terms are unclear or
ask for permission. A newspaper reporting what the police announced is still
tier 4: "Cyberabad Traffic Police said" in an article is attribution, not
verification.

## 1. Summary

| Source | Tier | Colour | Access verified (how) | Geometry | Distance | Coordinates | Start/end | Update frequency | Terms (short) | Automation permitted? | Commercial reuse? | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hyderabad Traffic Police website `htp.gov.in` | 1 | RED | GET 200 (TLS unverified); static site, `Last-Modified` 16 Jan 2026; robots allows all | — | — | — | — | Static; "Traffic Updates" links to Facebook | None published | Nothing to automate | n/a | Official pointer only; advisories go to social media |
| Hyderabad City Police press notes `hyderabadpolice.gov.in` | 1 | YELLOW, PERMISSION_REQUIRED | GET 200; 12 PDFs linked from home page, newest 23 Dec 2025; robots allows all | Named roads in PDF (not extracted) | not verified | No | Issue date in file name | Stale: newest note 9.5 months old | "COPYRIGHT © 2022, HYDERABAD CITY POLICE"; no re-use statement | Not stated | Not stated | Would be the best Hyderabad source if current; PDFs have a text layer (English) |
| Cyberabad Police website `cyberabadpolice.gov.in` | 1 | RED (PERMISSION_REQUIRED for any re-use) | GET 200; Traffic pages hold organisation and phone numbers only; press releases are crime; `robots.txt` returns the login page | — | — | — | — | Latest-news ticker; no advisories | "may be reproduced free of charge after taking proper permission by sending a mail to us" | Permission by mail | Not stated | No advisories on the site |
| Cyberabad Traffic Pulse | 1 | RED | (2 Oct, not re-verified) OTP registration, personal alerts | — | — | — | — | — | Not reviewed | No | No | Personal subscription service |
| Rachakonda (Malkajgiri) Police | 1 | RED (unverified) | DNS fails for three host names | — | — | — | — | — | — | — | — | Could not be verified today |
| GHMC `ghmc.gov.in` | 1 | RED | GET 200; Engineering Works page lists 2015–16 PDFs/XLS, one link 404; T&T PDF is a 2017 one-page description; works monitoring is a login system (not touched); robots 404 | — | — | — | — | Nothing current | Standard portal T&C; "Copyright @ 2024. GHMC All Rights Reserved" | Nothing to automate | Not stated | No road-works, closure or waterlogging listing |
| HMDA `hmda.gov.in` | 1 | RED | GET 200 (TLS unverified); WordPress 7.1.3; `/feed/` is an empty channel; `wp-json/wp/v2/posts` returns `[]`; Notices page has one 2016 notice; Road Works and Flyovers pages are historical | Named places | Sometimes ("Length 1.10 km", "512.85 Mts") | No | Project dates (1998–2011) | None | "Copyright © 2026. All rights reserved by HMDA" | Nothing current to automate | Not stated | No current notices |
| Telangana R&B `roadbuild.telangana.gov.in` (TSROADS) | 1 | RED | GET 200 (redirects to `/home.do`); menus and notifications load by JavaScript (`getData(...)`); robots 404 | — | — | — | — | Latest news = tenders/policy | Not found | Not fetchable without a browser | Not stated | No restriction or works notices |
| R&B road-cutting / RoW portal `tg-roadcutting.cgg.gov.in` | 1 | RED | `/home.do` redirects to `/login` (CAPTCHA login); `/getInfo` is a public About page | — | — | — | — | — | Not found | No (login, CAPTCHA) | No | Permit system for applicants; do not touch |
| Telangana Open Data `data.telangana.gov.in` | 1 | BLUE (context) | DKAN React app; CKAN API 404; DKAN `/api/1/search` works (two 30 s timeouts, then 200); robots allows | — | — | — | — | Datasets monthly to yearly | Per dataset: "Government Open Data License - India", "Open Government License, India", "License Not Specified" | Yes for GODL datasets | GODL permits with attribution | No road-event, road-works or accident dataset; transport datasets only |
| TGRAC ArcGIS REST `tgrac.telangana.gov.in/arcgis/rest/services` — `RnB_Folder/RnB_Query` layer 1 `TS_Road_Network_300424`, `RnB_Roads` layers | 1 | YELLOW, PERMISSION_REQUIRED | Public ArcGIS 10.22 directory, JSON metadata and feature queries return 200; robots 404 | **Polylines (EPSG 4326 / 32644)** | `Length_km`, chainage | **Yes** | n/a (network, not events) | Layer name dates 30 Apr 2024; no `editingInfo` | No `copyrightText`; site disclaimer: "for non-commercial purpose such as teaching, research and extension" | Technically yes; permission not granted in writing | Not permitted by the disclaimer wording | State road network (NH/SH/MDR/ODR/PR); 0 features in the Gachibowli bbox, so not an urban-street network |
| TGRAC `GHMCNalas_Folder/GHMCNalas_vul` layer 1 "Inundation Areas" | 1 | YELLOW, PERMISSION_REQUIRED | Query returns 23 named points with coordinates | Points | — | **Yes** | n/a | Unknown (KML-derived fields) | As above | As above | As above | Waterlogging context: 23 named inundation spots (RUBs, junctions) |
| NDMA SACHET CAP feed (Telangana) | 1 | YELLOW (context only) | RSS 200, 10 items, newest 4 Oct 2026; robots 404 | District level | — | — | In CAP item | As alerts issue | None found | Not stated | Not stated | Weather/flood context, never a road event |
| TGDPS live GHMC rainfall | 1 | YELLOW (context only) | HTML 200 (`liveghmcrain.jsp`) | Station names | — | not verified | Current day | Through the day | None found | Not stated | Not stated | Rainfall context only |
| OpenStreetMap via Overpass (comparison) | community data | GREEN (data) / RED (endpoint) | `overpass-api.de` **robots-disallowed** `/api/`, not queried; `overpass.kumi.systems` and `overpass.private.coffee` HTTP 500; `overpass.osm.ch` is a Switzerland-only extract (0 ways); `maps.mail.ru` mirror 200: 164 named ways in the bbox, data of 08:39 UTC today | Polylines | n/a | Yes | n/a | Minutes behind live | ODbL (stated in the response) | Not via the public API in production | ODbL: yes with attribution and share-alike | Best urban road network; use an extract, not the public API |
| Telangana Today (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 500 items / 13.8 days, full body on 499; robots allows | Named places | Sometimes | No | In text | ~36 items/day | Terms page fetched but its text is script-rendered: **not verified** | Not established | Not established | Best English discovery feed |
| The Hindu Hyderabad (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 60 items / 42.6 h, 14 descriptions, no body; 37 of 60 tagged Telangana | Named places | — | No | In text | ~34/day | "you shall not … Use robots, spiders, scripts … to data mine or scrape the Content" | Prohibited without consent | Prohibited | Headline-only detection |
| Deccan Chronicle Telangana (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 60 items / 16.4 h, full body | Named places | Sometimes | No | In text | ~88/day | "limited license only for purposes of viewing"; "publishing any Website material in any other media" restricted | Not permitted by terms | Not permitted | Telangana-wide feed |
| The Siasat Daily Hyderabad (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 40 items / 40.2 h, full body | Named places | Sometimes | No | In text | ~24/day | "solely for your personal, non-commercial use"; excludes "data mining, robots, scrapers, crawlers" and AI training | Prohibited | Prohibited | Hyderabad-only |
| NewsMeter Hyderabad (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 60 items / 10.8 days, full body (avg 2,995 chars) | Named places | Sometimes ("4.3-km") | No | In text | ~6/day | **No terms page found** (home page footer has none) | Not established | Not established | Highest road-infrastructure density today |
| The Hans India Hyderabad (connected) | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 38 items / 19.3 h, full body | Named places | — | No | In text | ~47/day | "limited license to access and make personal use of this site but not for commercial purposes"; use "subject to due credit" and "non-commercial" | Not permitted for commercial use | Not permitted | Short window |
| Times of India Hyderabad | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 20 items / 12.9 h, 11 descriptions, no body, no tags | Named places | — | No | In text | rolling 20 | RSS page: "TIL forbids you from any attempts at displaying, hosting, aggregating, reselling or putting to commercial use … TIL's RSS feeds" | Prohibited | Prohibited | Not connected |
| Hindustan Times Hyderabad | 4 | RED | RSS 200 but an **empty channel** (`<title>null | Hindustan Times</title>`, 0 items) | — | — | — | — | — | "You shall not use any 'deep-link', 'page-scrape', 'robot', 'spider'…" | Prohibited | Prohibited | No usable Hyderabad feed |
| Indian Express Hyderabad | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 200 items / 320 days, **no description and no body**; newest 7 Oct | Named places | — | No | In text | < 1/day | `/terms-of-use/` 404 today; (7 Oct, Mumbai research) prohibits "automated tools, bots, crawlers, scrapers" | Prohibited | Prohibited | Sparse; titles only |
| Hyderabad Mail | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 10 items / 3.3 h, full body (avg 3,064 chars) | Named places | — | No | In text | ~70/day (10-item window) | Copyright compilation notice; "You must abide by all copyright notices / restrictions" | Not stated | Not stated | Reliability not assessed; very short window |
| Telangana Tribune | 4 | BLUE, PERMISSION_REQUIRED | RSS 200: 10 items / 45.5 h, description only | Named places | — | No | In text | ~5/day | "personal, non-commercial use only. You may not reproduce, distribute … without prior written permission" | Prohibited | Prohibited | Small outlet |
| NDTV | 4 | RED | `ndtv.com` 403 for robots.txt and pages; FeedBurner cities feed 200, 20 items mixed cities (1 Hyderabad road item) | — | — | — | — | — | Not reachable | — | — | Not usable for Hyderabad |
| News18 | 4 | RED | 403 "Access Denied" for robots.txt and `/rss/` | — | — | — | — | — | Not reachable | — | — | Not usable |
| TV9 Telugu Hyderabad | 4 | BLUE, PERMISSION_REQUIRED | RSS 200 (`/telangana/hyderabad/feed`, declared by the section page): 60 items / 4.9 days, full Telugu body (avg 2,239 chars); robots allows this path | Named places | Sometimes ("6 కిమీ", "4 కిలోమీటర్ల") | No | In text | ~12/day | Prohibits "unauthorized spidering, scraping, or harvesting of content"; commercial use needs "express written consent" | Prohibited | Prohibited | Telugu discovery feed; needs Telugu keyword rules |
| Sakshi (Telugu) | 4 | RED | Home and Hyderabad section 200; **no RSS link** found; terms page body not in HTML | — | — | — | — | — | Not readable | — | — | No feed found |
| Eenadu (Telugu) | 4 | RED | Home 200; **no RSS link** found; robots blocks five AI crawlers | — | — | — | — | — | Terms page not fetched | — | — | No feed found |

Carried over from 2 October 2026 and **not re-verified today**: HYDRAA (manual
only), IMD Hyderabad (PDF bulletins), NHAI (nothing consumable), TGSRTC
(nothing consumable), Hyderabad Metro Rail (corporate feed), RGIA airport
(nothing consumable), TomTom / HERE / Mappls (commercial, require access),
Waze for Cities (not eligible), Google News RSS (blocked by decision 0009).

**The main finding, unchanged since 2 October:** no Hyderabad government,
police or road authority publishes current closures or advisories in a form a
program can read. The only official pages that ever carried advisories
(Hyderabad City Police press notes) stopped in December 2025. What is new
today: (1) TGRAC's ArcGIS REST directory is public and queryable, with a dated
state road network and 23 named inundation points, but under a non-commercial
disclaimer and without urban streets; (2) the Hyderabad Police PDFs have a
text layer, so no OCR is needed for them; (3) TV9 Telugu has a working
Hyderabad feed with full Telugu text; (4) Hindustan Times' Hyderabad feed is
empty, and Hyderabad Mail's feed now carries full article bodies.

## 2. Official sources (A–I)

### A. Hyderabad Traffic Police — `https://www.htp.gov.in/`

- **City / authority:** Hyderabad; Hyderabad City Police (Traffic Wing).
- **Source type:** HTML (static site). **Tier 1.**
- **Verified today:** GET 200, `text/html`, 38.6 KB, `Last-Modified: Fri, 16
  Jan 2026`, fetched with TLS verification off (the server chain does not
  verify from this machine). `robots.txt`: `User-agent: * / Allow: /`.
- **Content:** navigation to About, Traffic, NOC forms, e-challan (external,
  not touched), campaigns, galleries. The home page's "Traffic updates" block
  reads "Click here to view Traffic Updates" and links to
  `https://www.facebook.com/HYDTP/`; other social links: X `@HYDTP`,
  Instagram, a WhatsApp channel, YouTube. No advisory, notice, PDF listing or
  feed exists on the site (all 50 distinct anchors were read).
- **Event categories / geometry / distance / coordinates / start–end:** none
  (nothing published on the site).
- **Update frequency:** static (January 2026).
- **Terms:** no terms or copyright statement found on the page.
- **Automation permission / commercial use:** nothing to automate; reading the
  social channels by program would need the platforms' own APIs (not
  evaluated).
- **Classification:** RED (nothing to automate). Registry status stays
  `MANUAL_ONLY`.
- **Connector recommendation:** none.
- **Sample events:** none on the site.

### G. Hyderabad City Police press notes — `https://hyderabadpolice.gov.in/`

- **City / authority:** Hyderabad; Hyderabad City Police (Commissioner's
  office; traffic items issued by the Traffic Wing).
- **Source type:** HTML list + PDF. **Tier 1.**
- **Verified today:** GET 200, 36.9 KB, `Last-Modified: 26 Sep 2026` (the page
  was touched 12 days ago, but its list was not extended). `robots.txt`:
  `User-agent: * / Allow: /`. The "Latest News" block links **12 PDFs** under
  `assets/news/2025/<month>/<ddmmyyyy>.pdf`, dated **5 Nov 2025 to 23 Dec
  2025**. One is a road event: `assets/news/2025/12Dec/21122025.pdf`, anchor
  text "TRAFFIC DIVERSIONS IN CONNECTION WITH THE COMMENCEMENT OF CONSTRUCTION
  OF SKY WALK AT RYTHU BAZAR, MEHDIPATNAM & etc...." The others are enforcement
  drives, arrests and ceremonies. `traffic_branch.html` (200, `Last-Modified`
  25 May 2026) holds contacts and "Visit Official Website of Hyderabad Traffic
  Police" only.
- **PDF check (raw bytes):** `21122025.pdf`, 478 KB, `%PDF-1.5`, 3 pages,
  Producer "Microsoft® Word 2016", **12 `/Font` objects, 5 `/FontFile`, 3
  `/ToUnicode`, 0 `/Subtype /Image`**, fonts `ABCDEE+Calibri` and
  `ABCDEE+Calibri Light` (subset-embedded). It is a born-digital English
  document with a text layer: a PDF library can extract it; **no OCR needed**.
  The text could not be decoded here (subset CID fonts; no library installed).
- **Event categories (from the anchor text):** diversion, construction.
- **Geometry / distance / coordinates / start–end:** named place in the title
  (Rythu Bazar, Mehdipatnam); the PDF body was not read, so roads, distances
  and dates are "not verified"; no coordinates.
- **Update frequency:** the listing is stale: newest note 23 December 2025,
  9.5 months before today; on 2 October it was already the newest.
- **Terms (quoted):** footer "COPYRIGHT © 2022, HYDERABAD CITY POLICE. Designed
  and developed by NIC, Telangana"; no re-use or copyright policy page found.
- **Automation permission:** not stated. **Commercial use:** not stated.
- **Classification:** YELLOW, PERMISSION_REQUIRED. Useful only if the listing
  resumes; today it delivers nothing current.
- **Connector recommendation:** the existing official **HTML listing + PDF
  notice** family (`connectors/official/mumbai_traffic_police.py` pattern) would
  fit: anchor text, file-name date, PDF link; text extraction with a PDF
  library (English, no OCR). Not worth building until the listing is current.
- **Sample event (real, read today):** "TRAFFIC DIVERSIONS IN CONNECTION WITH
  THE COMMENCEMENT OF CONSTRUCTION OF SKY WALK AT RYTHU BAZAR, MEHDIPATNAM" —
  `https://hyderabadpolice.gov.in/assets/news/2025/12Dec/21122025.pdf`, file
  dated 21/22 Dec 2025. It pairs with news item E7 below (the skywalk is now
  "in its final phase").

### H. Cyberabad Police — `https://www.cyberabadpolice.gov.in/`

- **City / authority:** Cyberabad Commissionerate (Gachibowli, HITEC City,
  Madhapur, Raidurgam, Financial District, Kokapet, Narsingi, Kondapur,
  Miyapur, Kukatpally and more). **Tier 1.**
- **Source type:** HTML (Spring-style web app, `Preview?page_id=N` pages).
- **Verified today:** home 200 (466 KB); `Preview?page_id=57` "Traffic wings"
  200; `Preview?page_id=38` "Traffic Control Room Details" 200;
  `Preview?page_id=37` "Website Policy" 200. **`robots.txt` returns HTTP 200
  with the site's login page (HTML), not a robots file**, so no crawl rules are
  published. The Traffic pages list the traffic police stations (Madhapur,
  Raidurgam, Gachibowli, Narsingi, Kollur, Miyapur, RC Puram, Patancheru,
  Kukatpally, KPHB, Balanagar, Medchal, Jeedimetla), the control-room numbers
  (8712663555, 8500411111) and a Traffic Pulse link. **No advisory, diversion
  or closure appears anywhere on the site.** The home page "Latest News" is
  "Durga Matha Application Form - 2026" (an immersion-procession permission
  form) and the press releases (`gallery/docs/<hash>.pdf`) are crime and
  community items. Social links: X, Facebook, Instagram, WhatsApp.
- **Event categories / geometry / distance / coordinates / start–end:** none
  published on the site.
- **Update frequency:** ticker items; no advisories.
- **Terms (quoted, Website Policy page):** "Material featured on this Portal
  may be reproduced free of charge after taking proper permission by sending a
  mail to us. However, the material has to be reproduced accurately and not to
  be used in a derogatory manner or in a misleading context. Wherever the
  material is being published or issued to others, the source must be
  prominently acknowledged." Footer: "COPYRIGHT © 2025 Cyberabad police
  commissionerate".
- **Automation permission:** permission by mail required for reproduction.
  **Commercial use:** not stated.
- **Classification:** RED for road events (nothing to read), PERMISSION_REQUIRED
  for any future re-use. Registry stays `MANUAL_ONLY`.
- **Connector recommendation:** none. The Cyberabad advisories that news
  reported today (Vaishali Nagar, counterflow bus lane) exist only on social
  media and in the press.
- **Cyberabad Traffic Pulse** (`cyberabadtrafficpulse.telangana.gov.in`): (2
  Oct, not re-verified today) OTP-protected personal registration, alerts to a
  phone, no feed. RED.
- **Sample events:** none on the site.

### I. Rachakonda / Malkajgiri Police

- `https://rachakondapolice.telangana.gov.in/`, `https://www.rachakondapolice.telangana.gov.in/`
  and `https://rachakondapolice.gov.in/` all fail DNS resolution today
  (`getaddrinfo failed`), as on 2 October. A web search says the
  commissionerate was renamed Malkajgiri and that the site was taken offline
  after a cyber-attack; **neither claim is verified by a fetch**.
- **Classification:** RED (unverified). Nothing could be checked.

### B. GHMC — `https://www.ghmc.gov.in/`

- **City / authority:** Greater Hyderabad Municipal Corporation. **Tier 1.**
- **Source type:** HTML (ASP.NET) + PDF/XLS downloads.
- **Verified today:** home 200 (105 KB); `Engineering_Works.aspx` 200;
  `Traffic.aspx` 200; `Documents/T_and_T.pdf` 200; `terms_conditions.aspx`
  200; `Engineering_Works/AbstBTList.pdf` ("Works sanctioned for repairs of
  damaged roads due to heavy rains…") **404**. `robots.txt` 404 (no rules).
- **Open data / API check (before any scraping consideration):** no open-data,
  GIS, API or dataset link exists on the home, Engineering or Traffic pages.
  The Engineering Works page offers `100daysactionplan.pdf`, `BTroads.xls`,
  `BusBaysStatus.xls`, `Desilting2016.xls`, three "Draft BT Roads works
  sanctioned 2015-16" PDFs and similar: **historical lists from 2015–2016**,
  not current works. The "WORKS MONITORING SYSTEM" and eight role logins point
  to `workmodule.ghmc.bloomsolutions.co.in` (a contractor/engineer login
  system; **not touched**). `Traffic.aspx` describes the Traffic &
  Transportation Division ("seamless traffic movement at junctions… free left
  movements… road safety infrastructure") and links `T_and_T.pdf`: a 5 KB
  one-page PDF (`Last-Modified` 17 Nov 2017, Arial fonts, text layer) listing
  work types ("Junction Improvements under Urban Junction Improvement Plan
  (UJIP)", "Construction of Foot Over Bridges", "Road Markings & Sign boards",
  "Precast RCC Divider Blocks", "Central Median", "Improving of road
  geometrics at Accident spots"); no locations or dates.
- **Event categories:** none published. GHMC's own current works (H-CITI
  flyovers/underpasses, KBR Park one-way, elevated corridors) are known today
  only through news (section 6).
- **Geometry / distance / coordinates / start–end:** none.
- **Terms (quoted, `terms_conditions.aspx`):** a standard portal T&C ("GHMC
  reserves the right, at their sole discretion, to change, modify, add or
  remove portions of these Terms of Use"; "You shall not… remove, alter,
  bypass, avoid, interfere with, or circumvent any copyright, trademark, or
  other proprietary notices"). Footer: "Copyright @ 2024. GHMC All Rights
  Reserved… Content owned, maintained and updated by Greater Hyderabad
  Municipal Corporation, Government of Telangana."
- **Automation permission / commercial use:** not stated; there is nothing
  current to automate. Page scraping is not assumed legal and is not
  recommended.
- **Classification:** RED. Registry stays `MANUAL_ONLY`.
- **Connector recommendation:** none.
- **Sample events:** none on the site.

### C. HMDA — `https://www.hmda.gov.in/`

- **City / authority:** Hyderabad Metropolitan Development Authority. **Tier 1.**
- **Source type:** HTML (WordPress 7.1.3) with RSS and WP REST exposed.
- **Verified today** (TLS verification off; the chain does not verify here):
  home 200; `/notices/` 200; `/feed/` 200 `application/rss+xml` but an **empty
  channel** (`lastBuildDate` 6 Oct 2026, `sy:updatePeriod hourly`, **no
  items**); `/wp-json/wp/v2/posts?per_page=5` 200 returns `[]`;
  `/hmda-projects/`, `/road-works/`, `/flyovers/` 200. `robots.txt` 404.
- **Content:** the Notices table holds **one row**, dated 18/03/2016 (an LRS
  notice). "Road Works" describes completed projects with lengths and costs
  ("Road from 8th Batallion Road (Kondapur Main Road) to NAC Road … (Length
  1.10 km)", "Widening of Existing Road from Judges Colony to Old Bombay Road:
  The road is widened to 24 Mts from 7.5 Mts", "Road connecting Palmakul
  Village on NH-7 to ORR near Golkonda Khurd (P1) … 9.34 Kms … opened to
  traffic in December, 2011"). "Flyovers" is a table of ten flyovers
  inaugurated 1998–2010 with lengths ("Hitech City Junction … 705.00 Mts").
  The Notices menu links "Road Cutting Permissions" to the R&B portal (D).
- **Event categories:** long-running construction, widening, flyover — but
  historical, with no traffic-impact statement.
- **Geometry:** named places and from–to. **Distance:** yes, in text.
  **Coordinates:** no. **Start/end:** project completion dates only.
- **Update frequency:** no current content; the feed has never carried an item
  in the window seen.
- **Terms (quoted):** "Copyright © 2026. All rights reserved by HMDA,
  Telangana." No re-use policy found.
- **Automation permission / commercial use:** not stated.
- **Classification:** RED today. If `/feed/` ever carries items the generic RSS
  connector would read it without change; re-check periodically.
- **Connector recommendation:** none now (RSS family if the feed fills).
- **Sample events:** none current. The current HMDA works read today
  (Mehdipatnam skywalk, Paradise–Suchitra and Gymkhana–Shamirpet elevated
  corridors) come from news (E7–E9).

### D. Telangana Roads & Buildings Department — `https://roadbuild.telangana.gov.in/`

- **Authority:** R&B Department, Government of Telangana (site "TSROADS",
  designed by Centre for Good Governance). Found via the state portal's
  department page. **Tier 1.**
- **Verified today:** `/` 200 redirects to `/home.do` (81 KB, title
  "TSROADS"); `robots.txt` 404. The menus (Road Network: lists of NH/SH/MDR/ODR
  by district, Road Maps, Projects; Important Notifications; Key G.O.s;
  Archives) are `javascript:getData(...)` / `getDataMenu(...)` calls, so **no
  list can be fetched without a browser**. The "Latest News" items visible in
  the HTML are consultancy/construction tenders, a Road Sector Policy and
  "Role of Intelligent Transport Systems (ITS) in Enhancing Road Safety and
  Productivity", each a `previewPage.do?fileName=<opaque>` link. No
  restriction, closure or works notice is visible.
- The related portal `https://tg-roadcutting.cgg.gov.in/` ("Road Cutting / ROW
  Permission For Electricity Connection", linked from HMDA): `/home.do`
  redirects to `/login` (username, password, CAPTCHA; district list includes
  "RADIAL ROADS HYDERABAD"); `/getInfo` is a public About page: "the road
  assets of the R&B Department comprise of 24,245 kms of road length with
  3,152 kms of State Highways, 12,079 kms of Major District Roads, and 9,014
  kms of Other District Roads" (this sentence was read on `/getInfo` today).
  It is an applicant system; **not touched beyond the public pages**.
- **Event categories / geometry / distance / coordinates / start–end:** none
  readable.
- **Terms:** none found on either site.
- **Classification:** RED (TSROADS: not fetchable; road-cutting portal: login).
- **Connector recommendation:** none. Open question 3.

### E. Telangana Open Data — `https://data.telangana.gov.in/`

- **Authority:** Government of Telangana (ITE&C). **Tier 1**, source class
  `GOVERNMENT_OPEN_DATA`.
- **Verified today:** home 200 is a 2.4 KB React shell (`@civicactions/
  data-catalog-app`, i.e. DKAN). `robots.txt` 200 (one Disallow, not on the
  paths used). CKAN-style `/api/3/action/package_search` **404**. The DKAN
  public API `/api/1/search?fulltext=…` timed out twice at 30 s and then
  answered 200 (`application/json`): `traffic` → 2 results (both "Hyderabad
  Domestic Air Traffic" spreadsheets, "License Not Specified"); `road` → 9
  results, all Transport-department datasets: RTA vehicle registrations,
  permits, fitness certificates, dealers, life tax, online sales
  (2014–2018, 2019–2026), "TSRTC Bus Fleet Details" and "Telangana State Road
  Transport Corporation (TGSRTC) – General Transit Feed Specification (GTFS)
  Data" (modified 2026-09-24, distribution listed as PDF); `accident` → **0**.
- **Licences (as stated per dataset):** "Government Open Data License - India"
  (RTA online sales, TGSRTC GTFS), "Open Government License, India" (RTA
  registrations, permits, fitness, dealers, life tax), "License Not Specified"
  (air traffic, bus fleet). `accrualPeriodicity` "2" on the RTA sets (monthly
  by DKAN's code list; not verified further).
- **Event categories:** none; no road-works, closure, waterlogging, GIS or
  accident dataset was found by these three searches.
- **Classification:** BLUE (context). Explicit GODL-India licences on the
  transport datasets are the only explicit reuse licences met today on an
  official Telangana site; none of those datasets is a road-event source.
- **Connector recommendation:** none now. The GTFS dataset is relevant to a
  future bus-diversion idea only if its distribution is really GTFS (listed as
  PDF; not downloaded).

### F. TGRAC / Telangana GIS — `https://tgrac.telangana.gov.in/arcgis/rest/services`

- **Authority:** Telangana State Remote Sensing Applications Centre (TGRAC /
  TRAC), Planning Department. **Tier 1.** (The older host
  `tgracgis.telangana.gov.in` named in a third-party guide timed out.)
- **Source type:** ArcGIS Server 10.22 REST (MapServer with Query, one
  FeatureServer). `robots.txt` 404.
- **Directory (verified):** 49 folders, including `RnB_Folder`, `HMDA_Folder`,
  `GHMCNalas_Folder`, `GHMCDockets_Folder`, `Hydra_Folder` (FTL tanks),
  `Master_Administrative_Folder`, `PoliceProperties_Folder`, `TGSRTC_Folder`,
  `RRR_Folder`, `Utilities`. Fetched: `RnB_Folder` (services `RnB_Admin`,
  `RnB_Query`, `RnB_Roads`), `HMDA_Folder/HMDA` (admin boundaries, cadastral),
  `GHMCNalas_Folder` (`GHMCNalas_Hyd_Raster`, `GHMCNalas_vul`), `Hydra_Folder`
  (11 services), `Master_Administrative_Folder`, `Utilities`.
- **`RnB_Folder/RnB_Roads/MapServer`:** `serviceDescription` "test",
  `copyrightText` **empty**, spatial reference **EPSG 32644** (UTM 44N),
  capabilities "Map,Query,Data", `maxRecordCount` 1000; 21 layers: 0 Existing
  R & B Roads, 1 National Highway (NH), 2 NH (Proposed), 3 State Highway (SH),
  4 District Major Road (DMR), 5 Other District Road (ODR), 6 Existing P R
  Roads, 7 BT Road, 8 CC Road, 9 WBM Road, 10 Gravel, 11 Earthen, 12 RB Lane
  Details, 13 RB Road Network Within RRR, 14–18 Gram Panchayat connectivity,
  19 Ongoing Road, 20 Proposed Road. Layer 13 fields include
  `Name_of_the_Road`, `Classification_of_Road`, `Connecting_Villages`,
  `ORR_Starting_Km`/`ORR_Ending_Km`, `Within_ORR_Length_in_Kms`,
  `Lane_Details_SL_DL_FL`, `Surface_Details`, `Authority_030524` (a date,
  3 May 2024, in the field name). Layer 3 (SH) fields: `Road_Name`,
  `Classification`, `Department`, `Road_ID`, chainage, `Road_Surface`,
  `Length_km`, `Mandal_Nam`, `Dist_Name`.
- **`RnB_Folder/RnB_Query/MapServer`:** EPSG **4326**; layers 0
  `TS_PR_RB_Road_Network_From_To`, 1 **`TS_Road_Network_300424`** (polyline;
  name dated 30 Apr 2024), 2 `TS_RB_Lane_Details_Revised_030524_Authority_DELETE`,
  3 `ORR_RRR_1`. Layer 1 fields: `Department`, `Road_ID`, `Road_Name`,
  `Classification`, `Classification_Text`, `Road_Surface`, `Surface_2`,
  `Road_Chainage_Start/End`, `Total_Road_Chainage`, `Length_km`, `Category2`,
  `Mandal_Nam`, `Dist_Name`, `Parlament`, `Ass_Name`, `XY_Mid`, DRRP/PMGSY
  ids, `Remarks`. `editingInfo` is `null` and no `lastEditDate` is exposed.
- **Counts (verified):** layer 1 `where=1=1` → **57,827** features statewide;
  envelope 78.2–78.8 E / 17.2–17.7 N (metro) → **2,227**; envelope
  **78.34–78.37 / 17.44–17.46 (Gachibowli, the brief's bbox) → 0** in layer 1
  and 0 in `RnB_Roads` layer 13; layer 13 in the metro envelope → 219.
- **Sample features:** the Gachibowli bbox returned none, so a wider envelope
  (78.25–78.45 / 17.38–17.52) was queried: it returned 130 features (the
  `resultRecordCount=5` limit was **not honoured** by this 10.22 server).
  Examples: `NH-44` "Nagpur – Hyderabad- Bangalore (Old NH-44 part by GHMC)",
  Department NHAI, BT, Balanagar mandal, 2.18 km, 12 vertices from
  (78.44594, 17.46680) to (78.46532, 17.46168); `NH-65` "Pune – Hyderabad -
  Vijayawada (Old NH-65 part by GHMC)", Serilingampalle mandal, Rangareddy,
  6.37 km, **39 vertices** from (78.37683, 17.49723) to (78.31763, 17.49510);
  `NH-765D` "Hyderabad (Junction at outer ring road) - Narsapur - Medak",
  Quthbullapur, 8.29 km, 73 vertices; Panchayati Raj Engineering "Road From
  Approached road to USMANNAGAR to Gopanpally Thanda via Huda Tellapur",
  CC/BT, chainage 0–500 and 500–1350 m, "Rural Roads".
- **`GHMCNalas_Folder/GHMCNalas_vul/MapServer`:** EPSG 4326, 14 layers
  (Area_Name, **Inundation Areas**, Nala, Proposed Width, Existing Width,
  Segments, Cadstral, GHMC ZONES, OUTER_RINGROAD, Hyderabad,
  OUTER_RINGROAD_BND_ROADS, CANAL_DRAIN, RIVER_STREAM, TANKS). Layer 1
  "Inundation Areas": points, KML-style fields (`Name`, `PopupInfo`, …),
  **23 features**, all returned with coordinates, e.g. "BALKAMPET RUB"
  (78.45129, 17.44878), "RETHIBOWLI JUNCTION" (78.43108, 17.39553),
  "LAKDIKAPUL" (78.46450, 17.40414), "MODEL HOUSE, PUNJAGUTTA", "KCP JUNCTION,
  NEAR RTA OFFICE, KHAIRATHABAD", "OLIPHANT BRIDGE, CHILKALGUDA X ROADS",
  "MALAKPET RUB", "CHILKALGUDA RUB", "SHAIKPET NALA", "NAMPALLY T JUMCTION".
  No date is exposed.
- **Terms (quoted, `trac/disclaimer.php`):** "Telangana State Remote Sensing
  applications Centre (TRAC) provides the https://trac.telangana.gov.in website
  as a service to the public, government and website owners. The information
  provided is for non-commercial purpose such as teaching, research and
  extension. While accessing the website, visitor agrees to all disclaimers
  related to the website. Though the information contained within the site is
  periodically updated, no guarantee is given that the information provided is
  complete and up-to-date." The REST services carry no `copyrightText`.
- **Automation permission:** technically open (no robots, no key); legally
  not granted in writing. **Commercial use:** the disclaimer says
  non-commercial; **PERMISSION_REQUIRED**.
- **Classification:** YELLOW, PERMISSION_REQUIRED (both services).
- **Connector recommendation:** not an event source. For GIS resolution a new
  **ArcGIS REST reference-layer reader** (query by envelope, EPSG 4326, paging
  by 1000) could cache NH/SH/MDR/ODR segments and the 23 inundation points
  under a permission from TGRAC. See section 4 for why it does not replace OSM.

### Context sources (re-verified today)

- **NDMA SACHET CAP feed (Telangana)** —
  `https://sachet.ndma.gov.in/cap_public_website/rss/rss_telangana.xml`: 200,
  10 items, 24 Sep – 4 Oct 2026, titles only (CAP XML per item), e.g. "River
  Godavari at Bhadrachalam … continues to flow in above normal flood situation"
  (27 Sep). `robots.txt` 404; no terms found. Tier 1; YELLOW, context only;
  district level; never a road event by itself.
- **TGDPS live GHMC rainfall** — `https://tgdps.telangana.gov.in/liveghmcrain.jsp`:
  200, 17 KB HTML table page (station rainfall; the page also lists
  "Monsoon-2026 SOUTHWEST" reports). `robots.txt` 404; no terms. Tier 1;
  YELLOW, context only.

## 3. News and discovery sources (J)

All feeds were fetched today; counts are from today's files. "Body" means
`content:encoded` present. All these publishers are tier 4 and BLUE by REI
policy; every one whose terms could be read restricts automated or commercial
use, so each carries PERMISSION_REQUIRED as a legal question for the user. The
robots.txt of every host allowed the feed path used (the fetcher checks this);
Telangana Today, The Hindu, Siasat, Hindustan Times, Indian Express and Eenadu
also name AI crawlers in their robots files.

| Outlet | Feed (verified) | Items / window | Body | Categories | Terms (quoted today) |
| --- | --- | --- | --- | --- | --- |
| Telangana Today | `https://telanganatoday.com/hyderabad/feed` | 500 / 13.8 d (24 Sep – 8 Oct 08:25 UTC) | Yes, 499/500 (avg 1,651 chars) | all tagged | `/terms-and-conditions` 200 but its text is rendered by script: **not verified** |
| The Hindu | `https://www.thehindu.com/news/cities/Hyderabad/feeder/default.rss` | 60 / 42.6 h | No; 14 descriptions | 37 Telangana, 21 Hyderabad | "Without prior written consent, you shall not: … Use robots, spiders, scripts, service, software or any manual or automatic device, tool, or process designed to data mine or scrape the Content" (`/termsofuse/`) |
| Deccan Chronicle | `https://www.deccanchronicle.com/category/southern-states/telangana/google_feeds.xml` | 60 / 16.4 h | Yes (avg 1,769) | "Southern States,Telangana" | "You are granted limited license only for purposes of viewing the material contained on this Website. Restrictions: … publishing any Website material in any other media; selling, sublicensing and/or otherwise commercializing…" (`/terms-and-condition`) |
| The Siasat Daily | `https://www.siasat.com/news/hyderabad/feed/` | 40 / 40.2 h | Yes (avg 2,203) | Hyderabad | "a limited, personal, non-exclusive … licence … solely for your personal, non-commercial use"; excludes "Use any data mining, robots, scrapers, crawlers, or similar data-gathering and extraction tools" and AI training (`/terms-conditions/`) |
| NewsMeter | `https://newsmeter.in/category/hyderabad/google_feeds.xml` | 60 / 10.8 d | Yes (avg 2,995) | Hyderabad | **No terms page found**; home page footer links none; site-wide feed `https://newsmeter.in/google_feeds.xml` declared |
| The Hans India | `https://www.thehansindia.com/category/news/cities/hyderabad/google_feeds.xml` | 38 / 19.3 h | Yes (avg 1,805) | Hyderabad | "HMHL grants you a limited license to access and make personal use of this site but not for commercial purposes. We permit the use of materials on this website subject to due credit is given to HMHL. The use shall also be subject to non-commercial use" (`/pages/terms-conditions`) |
| Times of India | `https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms` | 20 / 12.9 h | No; 11 descriptions; no tags | — | "TIL forbids you from any attempts at displaying, hosting, aggregating, reselling or putting to commercial use either directly or indirectly TIL's RSS feeds" (`/rss.cms`) |
| Hindustan Times | `https://www.hindustantimes.com/feeds/rss/cities/hyderabad-news/rssfeed.xml` | **0** (empty channel, title "null") | — | — | "You shall not use any 'deep-link', 'page-scrape', 'robot', 'spider' or other automatic device, program, algorithm or methodology … to access, acquire, copy or monitor any portion of the Platform" (`/terms-of-use`) |
| Indian Express | `https://indianexpress.com/section/cities/hyderabad/feed/` | 200 / 320 d (21 Nov 2025 – 7 Oct 2026) | No; no descriptions | Cities, Hyderabad | `/terms-of-use/` **404 today**; 7 Oct Mumbai research quoted a prohibition on "automated tools, bots, crawlers, scrapers" (URL not re-verified) |
| Hyderabad Mail | `https://hyderabadmail.com/feed/` | 10 / 3.3 h | Yes (avg 3,064) | Hyderabad/Telangana | "Our site … is protected by copyright as a collective work … You must abide by all copyright notices / restrictions on our site" (`/terms-conditions/`) |
| Telangana Tribune | `https://www.telanganatribune.com/feed/` | 10 / 45.5 h | No; description only | Hyderabad | "You may access and read the Content for personal, non-commercial use only. You may not reproduce, distribute, modify, or publicly display any Content without prior written permission" (`/terms-of-use/`) |
| NDTV | `ndtv.com` 403 (robots.txt and `/hyderabad-news`); `https://feeds.feedburner.com/ndtvnews-cities-news` 200 | 20 / 50 h, mixed cities | Summary (avg 165) | — | not reachable |
| News18 | `https://www.news18.com/rss/` 403 "Access Denied"; robots.txt 403 | — | — | — | not reachable |
| TV9 Telugu | `https://tv9telugu.com/telangana/hyderabad/feed` (declared by the section page's `<link rel="alternate">`) | 60 / 4.9 d | Yes, Telugu (avg 2,239) | హైదరాబాద్ (60) | "engage in unauthorized spidering, scraping, or harvesting of content … or use any other unauthorized automated means to compile information" prohibited; use "for any commercial or unauthorized purpose" needs "express written consent" (`/terms-and-conditions`) |
| Sakshi | no feed link on home or `/telangana/hyderabad` (1.1 MB page); `/termsofusage` 200 but the terms body is not in the HTML (meta description only) | — | — | — | not verified |
| Eenadu | no feed link on the home page; `/terms-conditions` exists (not fetched) | — | — | — | not verified |

Per-feed notes (all fields the brief asks for apply to every row above:
Hyderabad; source type RSS; geometry = named places in text; distance only
when the article states it; coordinates never; start/end only in text; tier 4;
BLUE; connector = the existing generic RSS connector, with Telugu keyword rules
needed for TV9):

- **Telangana Today** remains the richest: 101 title/summary keyword hits of
  500 items today; the only feed that reported the Vaishali Nagar diversions
  with routes. Its terms could not be read without a browser.
- **The Hindu** is largely statewide in this feed (37 of 60 items tagged
  Telangana); no bodies.
- **NewsMeter** had the most infrastructure items (KBR Park one-way,
  Jubilee Hills–NFCL corridor, counterflow lane) with full bodies and stated
  distances; it still has no terms page.
- **Hindustan Times**: the Hyderabad feed URL pattern that works for Mumbai
  returns an empty channel for Hyderabad; RED until a working feed is found.
- **Hyderabad Mail**'s feed now carries full bodies (on 2 Oct it did not) but
  its 10-item window spanned 3.3 hours today.
- **TV9 Telugu** is the first Telugu feed verified: Hyderabad-only, full
  Telugu text, 5-day window, and it carried the LB Nagar–Hayathnagar and
  Punjagutta–Jubilee Hills corridor items. REI's Hyderabad keyword rules are
  English; Telugu rules (ట్రాఫిక్, మళ్లింపు, ఫ్లైఓవర్, రహదారి) would be needed.
- **Sakshi / Eenadu**: no feed found by reading their pages; nothing was
  guessed.

## 4. TGRAC road network vs OpenStreetMap (Gachibowli bbox 17.44–17.46 N, 78.34–78.37 E)

**What was fetched.** TGRAC: layer `RnB_Query/1 TS_Road_Network_300424` and
`RnB_Roads/13` queried with that envelope (EPSG 4326) — **0 features each**;
a wider envelope (78.25–78.45 / 17.38–17.52) returned 130 features, 11 of
them NH segments. OSM: one Overpass query
`way["highway"]["name"](17.44,78.34,17.46,78.37); out geom;`. The brief named
`overpass-api.de`, whose `robots.txt` says `User-agent: * / Disallow: /api/`;
the fetcher refused it and no request was sent there. Two public mirrors
(`overpass.kumi.systems`, `overpass.private.coffee`; both `robots.txt` 404)
answered HTTP 500; `overpass.osm.ch` answered 200 with 0 elements (it is a
Switzerland-only extract); the VK/mail.ru mirror
`https://maps.mail.ru/osm/tools/overpass/api/interpreter` (its `/robots.txt`
URL returns the site's HTML app page, so no crawl rules are published)
answered 200 with `timestamp_osm_base 2026-10-08T08:39:35Z` and the ODbL
notice. Four Overpass requests in all; one succeeded.

| | TGRAC `TS_Road_Network_300424` | OSM (Overpass, 8 Oct 2026 08:39 UTC) |
| --- | --- | --- |
| Coverage in the bbox | **0 features** (also 0 in `RB Road Network Within RRR`) | **164 named ways**: primary 71, residential 49, secondary 22, service 11, motorway 3, motorway_link 2, path 3, tertiary 1, pedestrian 1, construction 1 |
| Coverage wider | 2,227 segments in the metro envelope; 57,827 statewide; NH-44/NH-65 city stretches are tagged "(Old NH-… part by GHMC)" | not measured |
| Names | Official long names: "Pune – Hyderabad - Vijayawada (Old NH-65 part by GHMC)", "Hyderabad (Junction at outer ring road) - Narsapur - Medak"; rural PR roads by village | 55 distinct names: Old Bombay Road, Gachibowli Flyover, DLF road, ISB Road, Gachibowli - Miyapur Highway, HITEC City–Madhapur Road, Hitec City - Kondapur Main Road, Gachibowli Kondapur Link Road, Kothaguda Underpass, Kothaguda-Kondapur Flyover, Shilpa Layout Flyover, PJR Flyover, Mindspace road, Masjid Banda Road, many "Lane Number N" and "Street N" |
| Geometry quality | Long segments, sparse vertices: NH-65 Serilingampalle segment 6.37 km with 39 vertices (≈160 m spacing); 2–12 vertices on 0.08–2.6 km NH pieces | Dense: Old Bombay Road way 157046148 has 43 nodes between (17.4545, 78.3422) and (17.4451, 78.3528) (≈1.5 km, ≈35 m spacing); 1,587 vertices across the 164 ways |
| Classification fields | `Classification`/`Classification_Text` (National Highway (NH), BT, CC Road…), `Category2` (National Highway NH, Rural Roads), `Department` (NHAI, Panchayati Raj Engineering Department), `Road_Surface`, chainage, `Length_km`, mandal/district, assembly/parliament constituency; layer 13 adds `Lane_Details_SL_DL_FL` and `Authority_030524` | `highway` class, `name`, `lanes` on 86 ways, `oneway=yes` on 101, `maxspeed` on 91, `surface` on 93; **no `ref`** and **no `name:te`** in the bbox |
| Update date | Layer name dated 30 Apr 2024; `editingInfo` null; no `lastEditDate` exposed | 8 Oct 2026 08:39 UTC (minutes behind live) |
| Licence | No `copyrightText`; site disclaimer "non-commercial purpose such as teaching, research and extension" | ODbL (stated in every response) |
| Commercial reuse | Not permitted by the disclaimer as written; permission required | Permitted with attribution and share-alike |

**Reading.** TGRAC's network is the R&B/NHAI/Panchayati Raj state network
with official road names, chainage, surface and authority: good for naming a
state highway or MDR outside the ORR and for the official classification of a
stretch, but it holds **no GHMC urban streets** (the Gachibowli grid, the IT
corridor flyovers and the link roads are absent), it is dated April–May 2024,
its geometry is coarse, and its reuse terms are non-commercial. OSM covers the
urban streets densely with lanes, one-way and speed attributes, is current and
has explicit terms. This is a comparison, not a recommendation to replace OSM:
the two are complementary (OSM for the city network; TGRAC, under permission,
for official names, classes and chainage of NH/SH/MDR/ODR and for the 23
inundation points). For production, OSM should come from an extract, not from
the public Overpass endpoints (the main instance disallows `/api/` for
crawlers and the mirrors were unreliable today).

## 5. OCR needs

- **Hyderabad City Police press notes:** no OCR. The one road-event PDF read
  today is a Word-generated English PDF with embedded subset fonts and
  `ToUnicode` maps (12 `/Font` objects, 0 image objects). A PDF text library
  is enough (none is installed here; pip is broken).
- **GHMC `T_and_T.pdf`:** English, text layer (Arial), no OCR; content is a
  2017 description, not events.
- **Cyberabad Police press PDFs (`gallery/docs/*.pdf`):** not opened (crime
  items); language and text layer **not verified**.
- **HMDA, R&B:** no notice PDFs were found to check.
- **Telugu:** no official Telugu PDF was met today. The only Telugu material
  is TV9's RSS (plain text, no OCR). Unlike Mumbai (scanned Marathi), **no
  Hyderabad source read today needs OCR**; the open question is only whether
  the police PDFs would stay born-digital if the listing resumed.

## 6. Real events available now (read today, 8 October 2026)

Quotes are verbatim from the feed bodies or page text fetched today;
attribution is as the article states it. Tier 4 items are leads, not
verified events. Up to 30 were allowed; **14** real items were found.

1. **E1 — Vaishali Nagar Railway Underpass diversions extended 8–14 Oct 2026
   (Kondapur/Hafeezpet).** Telangana Today, 6 Oct 2026,
   `https://telanganatoday.com/vaishali-nagar-traffic-restrictions-extended-till-october-14`:
   "The Cyberabad Traffic Police have extended the traffic restrictions around
   the Vaishali Nagar Railway Underpass for another week, from October 8 to 14,
   due to delays in ongoing road-widening and stormwater drain works."
   Diversions named by route, e.g. "My Home Mangala Apartments-Hafeezpet:
   Traffic will be diverted via My Home Mangala T-Junction, Raghavendra Nagar
   Colony, Hi-Tension Road, RTA Office Kondapur and Hafeezpet ROB/Flyover."
   Tier 4 (attributed to Cyberabad Traffic Police). Categories: diversion,
   construction, widening, utility (drain), long-running, underpass. Explicit
   start/end dates. **Current.**
2. **E2 — Bolarum roads in Secunderabad Cantonment closed since 31 Aug
   2026.** Telangana Today, 8 Oct 2026,
   `https://telanganatoday.com/firearms-heist-solved-but-bolarum-roads-in-scb-remain-shut-citizens-demand-immediate-reopening`:
   "LMA shut Richardson Road, Ammuguda Road, Holy Trinity Church Road, Protnee
   Road and Byam Road after an arms theft was reported at 20 Battalion, Madras
   Regiment, on August 31"; "The closures forced commuters to take detours of 5
   to 8 kilometres". Tier 4 (attributed to FNECS / Local Military Authorities).
   Categories: closure, long-running, emergency; **distance** (5–8 km detours);
   no end date. **Current.**
3. **E3 — KBR Park one-way system made permanent (Jubilee Hills / Banjara
   Hills).** NewsMeter, 6 Oct 2026,
   `https://newsmeter.in/hyderabad/hyderabad-why-has-one-way-traffic-system-around-kbr-park-been-made-permanent-776865`:
   "The experimental one-way traffic system around KBR Park will now become a
   permanent feature"; "The clockwise traffic arrangement was introduced in
   August 2026". Also Telangana Today 6 Oct
   (`…/hyderabads-kbr-park-project-gets-a-rethink-after-one-way-traffic-system`)
   and NDTV 6 Oct (FeedBurner item "Hyderabad's 'Elevated Corridor' Plan To
   Ease Traffic Around KBR National Park"). Tier 4 (attributed to GHMC
   Commissioner). Categories: one-way, long-running. **Two-source. Current.**
4. **E4 — Jubilee Hills Check Post – NFCL Junction elevated corridor, 4.3 km,
   two packages (planned).** NewsMeter, 5 Oct 2026,
   `https://newsmeter.in/hyderabad/western-hyderabad-set-for-rs-1090-crore-elevated-corridor-between-jubilee-hills-and-nfcl-junction-776810`:
   "GHMC is finalising a 4.3-km, six-lane elevated corridor from Jubilee Hills
   Check Post to NFCL Junction"; "Package 1 will connect Jubilee Hills Check
   Post Junction with Mugdha Junction. Package 2 will run from Mugdha Junction
   to Muffakham Jah College and include a dedicated connecting ramp to Banjara
   Hills Road No. 1." Also Telangana Tribune 6 Oct ("Jubilee Hills Steel
   Flyover to Connect Muffakham Jah College and Banjara Hills Road No. 1"),
   Telangana Today 3 Oct (Standing Committee approval) and TV9 Telugu 4 Oct
   ("పంజాగుట్ట నుంచి జూబ్లీహిల్స్ చెక్ పోర్ట్ వరకు … 4 కిలోమీటర్ల మేర … ఆరు లైన్లుగా"
   [Punjagutta to Jubilee Hills Check Post, 4 km, six lanes]). Categories:
   flyover, construction (planned), long-running; **distance** (4.3 km / 4 km).
   No start date. **Upcoming.**
5. **E5 — Counterflow bus lane trial, JNTU – HITEC City – Raidurgam –
   Financial District (planned).** NewsMeter, 2 Oct 2026,
   `https://newsmeter.in/hyderabad/what-is-new-traffic-experiment-that-cyberabad-police-is-trying-on-jntufinancial-district-route-776615`:
   "Cyberabad Traffic Police have ordered a trial on a counterflow lane,
   allowing buses to travel against the regular traffic direction between JNTU,
   HITEC City, Raidurgam and the Financial District." Also Telangana Today 3
   Oct (`…/cyberabad-police-to-test-counterflow-bus-lane-in-it-corridor`):
   "the proposed corridor covers JNTU Junction, Hitec City, Raidurgam Metro
   Station, Waverock and the Financial District". Tier 4 (attributed to Jt CP
   Traffic, Cyberabad). Categories: one-way (contraflow lane), multi-road.
   No dates. **Two-source. Upcoming.**
6. **E6 — H-CITI flyovers and underpass at IIIT Junction / Khajaguda /
   Gachibowli, works to April–May 2027.** Telangana Today, 28 Sep 2026,
   `https://telanganatoday.com/cmc-accelerates-h-citi-flyover-underpass-works-in-gachibowli`:
   "accelerated flyover and underpass works at IIIT Junction and Khajaguda
   after completing earth excavation at Gachibowli Junction … 40 per cent of
   the civil works had been completed"; "Flyovers and an underpass work taken
   up at a length of network: 3.3 Kilometres"; "4-lane Bi-directional Flyover
   (Level-1): From ISB Road to DLF Road"; "6-Lane Bi-Directional Underpass:
   Gachibowli (Indira Nagar) to Lingampally (Gachibowli Stadium)"; deadlines
   "April and May 2027". Tier 4 (attributed to CMC). Categories: construction,
   flyover, underpass, excavation, long-running; **distance** (3.3 km);
   end dates stated. **Current.** (The IIIT Junction closure of June 2026 in
   the 2 Oct research is this project.)
7. **E7 — Mehdipatnam pedestrian skywalk, 390 m, opening within one to two
   months.** Telangana Today, 2 Oct 2026,
   `https://telanganatoday.com/mehdipatnam-pedestrian-skywalk-likely-to-open-within-two-months`:
   "The 390-metre elevated skywalk … five entry and exit points at Rythu
   Bazaar, Defence compound wall at Military Garrison, Mehdipatnam bus bay,
   near Humayun Nagar Police Station and Gudimalkapur Junction"; "traffic
   diversions imposed at Mehdipatnam … also ended up extending the deadline".
   Tier 4 (attributed to HMDA). **Tier 1 pair:** Hyderabad City Police PDF of
   21 Dec 2025, "TRAFFIC DIVERSIONS IN CONNECTION WITH THE COMMENCEMENT OF
   CONSTRUCTION OF SKY WALK AT RYTHU BAZAR, MEHDIPATNAM"
   (`https://hyderabadpolice.gov.in/assets/news/2025/12Dec/21122025.pdf`; body
   not read). Categories: construction, diversion, long-running; **distance**
   (390 m). **Current.**
8. **E8 — Paradise–Suchitra Junction NH-44 elevated corridor: utilities being
   shifted between Paradise Circle and Bowenpally.** Telangana Today, 30 Sep
   2026, `https://telanganatoday.com/balamrais-historic-water-reservoir-dismantled-for-nh-44-project`:
   "cleared to pave way for the upcoming Paradise–Suchitra Junction elevated
   corridor"; "The shifting of underground utilities and the laying of new
   water transmission lines between Paradise Circle and Bowenpally are
   currently in progress." Tier 4 (attributed to SCB / HMDA). Categories:
   construction, utility, flyover, long-running. No dates. **Current.**
9. **E9 — Gymkhana Grounds – ORR Shamirpet elevated corridor on SH-1 (Rajiv
   Rahdari): war memorial relocation approved 6 Oct.** Telangana Today, 7 Oct
   2026, `https://telanganatoday.com/decades-old-secunderabad-war-memorial-set-to-move-for-elevated-corridor`:
   "set to be relocated to make way for an elevated corridor from Gymkhana
   Grounds to Outer Ring Road Shamirpet on State Highway-1, Rajiv Rahdari";
   "located on the right side of the road from Tivoli Junction to Gymkhana
   Ground X Road". Tier 4 (attributed to SCB / HMDA). Categories: construction
   (planned), flyover, long-running. **Upcoming.**
10. **E10 — LB Nagar – Hayathnagar double-decker elevated corridor, about
    6 km (proposal to MoRTH).** TV9 Telugu, 6 Oct 2026,
    `https://tv9telugu.com/telangana/lb-nagar-hayathnagar-double-decker-elevated-corridor-minister-komatireddy-urges-gadkari-for-project-approval-1927688.html`:
    "ఎల్‌బీనగర్‌–హయత్‌నగర్ డబుల్ డెక్కర్ ఎలివేటెడ్ కారిడార్‌ … సుమారు 6 కిలీ మీటర్ల మేర"
    [LB Nagar–Hayathnagar double-decker elevated corridor, about 6 km]. Tier 4
    (attributed to the R&B Minister). Categories: flyover, construction
    (proposed), **distance** (6 km). **Upcoming (proposal).**
11. **E11 — "Chalo Lok Bhavan" rally, Necklace Road to Lok Bhavan, 8 Oct
    2026.** Telangana Today, 8 Oct 2026,
    `https://telanganatoday.com/tension-at-chalo-lok-bhavan-protest-congress-ministers-arrested-in-hyderabad`:
    "Congress leaders and activists took out a massive rally from the Indira
    Gandhi statue on Necklace Road to Lok Bhavan." Also Deccan Chronicle 8 Oct
    ("Telangana Ministers, TPCC Chief Detained during March to Lok Bhavan"),
    Hyderabad Mail 8 Oct, Hans India 8 Oct. Categories: procession/gathering;
    no closure stated. **Multi-source. Today (over).**
12. **E12 — Tank Bund fatal accident, 4 Oct 2026 night.** Telangana Today, 4
    Oct 2026, `https://telanganatoday.com/birthday-outing-ends-in-tragedy-girl-relative-killed-in-tank-bund-accident`:
    "The family parked their car near the Maqdoom Mohiuddin statue and walked
    towards Hussainsagar … a speeding lorry coming from the Secunderabad side
    hit them". Categories: accident; no closure stated. **Past.**
13. **E13 — Ganesh immersion closures around Hussain Sagar, 25–26 Sep 2026.**
    Telangana Today, 26 Sep 2026,
    `https://telanganatoday.com/traffic-restrictions-to-continue-in-hyderabad-on-major-ganesh-immersion-routes-on-saturday`:
    "Traffic restrictions will continue on Saturday on major procession
    routes, including Tank Bund, Necklace Road, NTR Marg, PV Statue and areas
    around Indira Gandhi Rotary"; and `…/hyderabad-motorists-stranded-as-roads-around-hussain-sagar-remain-closed`:
    "roads around Hussain Sagar remained closed for the second consecutive day
    … Long queues … on roads leading towards Indira Park, Lower Tank Bund".
    Tier 4 (attributed to CP Hyderabad). Categories: closure, procession,
    festival, multi-road. **Past** (a lifecycle/expiry test case).
14. **E14 — Telangana road-safety corridors (context, not an event).** Siasat,
    8 Oct 2026, `https://www.siasat.com/telangana-flags-48-critical-road-corridors-230-high-fatality-spots-3554072/`:
    "Hyderabad Police have separately identified 80 critical accident-prone
    spots along the ORR. Hyderabad Growth Corridor Limited (HGCL) is appointing
    a safety consultant to audit the 158-km expressway." Also The Hindu 7 Oct
    ("'Zero Fatalities' goal puts 48 deadly corridors on Telangana's road
    safety radar"). Two-source context only.

Not listed as road events although read today: the Krishna Phase-II pipeline
shutdown (water utility, 24 km outside the city), HITEC City train halts,
Pushpak bus fares, Dussehra special buses, the 48-corridor review (E14 is
context). No Dussehra/Durga immersion advisory had been published yet in any
source read today (Cyberabad's "Durga Matha Application Form - 2026" shows the
processions are being permitted).

Tier 1 real events read today: **one** (E7's police PDF title, December 2025).
Everything else is tier 4.

## 7. Open questions

1. **Hyderabad City Police listing:** why it stopped in December 2025 and
   whether advisories now go only to X/WhatsApp. If it resumes, the PDFs are
   born-digital English and a listing + PDF connector fits.
2. **TGRAC terms:** the services carry no copyright text and the website
   disclaimer says non-commercial. A written permission (and the meaning of
   "test" in every service description, i.e. whether these services are
   production) is needed before any use, even for GIS resolution.
3. **R&B TSROADS:** the notification and road-network lists load by
   JavaScript; a browser session (not done here) is needed to see whether any
   restriction notice is ever published there.
4. **GHMC:** no works or closure page exists on the public site; the works
   monitoring system is a login. Whether GHMC publishes anything on X that
   the H-CITI contractor restrictions depend on is unknown.
5. **HMDA feed:** `/feed/` and the WP REST API are live but empty; is the
   site's news published as pages rather than posts (then no feed will ever
   fill)?
6. **Rachakonda/Malkajgiri:** DNS fails from this machine; re-test from
   another network and confirm the new domain.
7. **News terms:** every publisher whose terms were read restricts automated
   or commercial use; Telangana Today's and Sakshi's terms are script-rendered
   and unread; NewsMeter has none. Whether REI's internal discovery use is
   permitted is a legal question for the user, as in Mumbai.
8. **Hindustan Times Hyderabad:** the feed is an empty channel; a different
   feed id may exist (not searched further today).
9. **Telugu:** TV9's feed works, but REI's Hyderabad keyword rules are
   English; whether Telugu rules are worth adding depends on how often TV9
   carries advisories the English feeds miss (not measured).
10. **Overpass:** the main instance disallows `/api/` in robots.txt and two
    mirrors failed; production use of OSM must come from an extract, and the
    OSM-vs-TGRAC comparison rests on one mirror response.
11. **Open data GTFS:** the TGSRTC GTFS dataset's distribution is listed as
    PDF; whether a real GTFS zip exists was not checked.
12. **Dussehra 2026:** immersion/procession advisories for Durga Matha are
    expected (Cyberabad is accepting applications) but none has been published
    in any source read today; this is the next test window for the news feeds.

## 8. Counts

- **Sources researched today:** 31 (15 official/context/reference, 16 news);
  10 more carried over from 2 October without re-verification.
- **Colours (today's 31):** GREEN 1 (OpenStreetMap data, ODbL; not the public
  Overpass endpoints) · YELLOW 5 (Hyderabad City Police press notes, TGRAC
  road network, TGRAC inundation points, SACHET, TGDPS) · BLUE 12 (Telangana
  Open Data as context; 11 news feeds: Telangana Today, The Hindu, Deccan
  Chronicle, Siasat, NewsMeter, Hans India, Times of India, Indian Express,
  Hyderabad Mail, Telangana Tribune, TV9 Telugu) · RED 13 (HTP website,
  Cyberabad website, Cyberabad Traffic Pulse, Rachakonda, GHMC, HMDA, R&B
  TSROADS, road-cutting portal, Hindustan Times Hyderabad feed, NDTV, News18,
  Sakshi, Eenadu).
- **PERMISSION_REQUIRED:** 15 (Hyderabad City Police press notes, Cyberabad
  website for any re-use, TGRAC ×2, and the 11 news feeds).
- **Production candidates:** 1 unconditional (OSM extract for the road
  network, already REI's intended GIS basis); 2 conditional (Hyderabad City
  Police press notes if the listing resumes and permission is obtained; TGRAC
  reference layers under written permission). **No official Hyderabad source
  can be connected for live road events today.**
- **Discovery sources:** 6 connected feeds re-verified working; 5 additional
  usable feeds (TOI, Indian Express titles-only, Hyderabad Mail, Telangana
  Tribune, TV9 Telugu); all BLUE and all with terms to review.
- **Real events read today:** 14 (1 with a tier 1 pairing; 13 current,
  upcoming or recent from tier 4).
- **Requests:** 149 (18 failed: SSL ×2 hosts before retry, DNS ×4, timeouts
  ×3, HTTP 403 ×4, 404/500 ×5; 1 refused by robots).
