# Mumbai source research

**Research dates: 7 October 2026 (19:45–20:20 IST) and 8 October 2026
(13:30–15:10 IST).** This document rewrites the 7 October report in the format
the source-research brief asks for, keeps every finding of 7 October with its
date, and extends it with what was re-verified and newly found on 8 October.

**Method.** Every statement about access, content, format or terms below comes
from a fetch made by the project's Python (`.venv`, `httpx`) with the
User-Agent `JSAN-REI source research (research@jsan.example; local test)`, at
most one request a second per host, 30 s timeout, following each host's
`robots.txt` (`*` group) fetched first. 132 requests on 7 October; **100
requests on 8 October** (log: scratchpad `mum-fetched/_log.txt`). No logins, no
CAPTCHA, no paywalls, no credentials, no paid APIs, no browser User-Agent
spoofing. The BMC disaster-management API, whose credentials sit inside its
JavaScript bundle, was **not called** on either day. Nothing was connected,
changed or built from this research: this is Phase 1 and Phase 2 (research and
verification) only.

**Dating rule.** Findings marked *(7 Oct)* were established on 7 October and
not re-fetched on 8 October; findings marked *(8 Oct)* were fetched today.
Where something could not be established, it says "not verified" and why.

**What is already connected from the 7 October research.** Phase 2 on 8 October
built, from the 7 October report: the Mumbai city configuration and place list,
the connector `mumbai-traffic-police-notifications` (the HTML listing only),
and the Mid-Day Mumbai and Siasat Mumbai RSS feeds as discovery-only sources.
See [decision 0017](../decisions/0017-mumbai-and-bengaluru-official-listings.md)
and [the source page](../data-sources/mumbai-traffic-police-notifications.md).
**The notice PDFs are still not read** (no OCR library on this machine), so
roughly half the stored notices are placed only by a locality guessed from the
PDF file name, which the brief says is not an exact location. Two findings
today bear directly on that gap (bilingual PDFs; the archive's richer English)
and one bears on what is connected (the Siasat terms now explicitly prohibit
scrapers and AI/LLM use).

Tiers are REI's: 1 government, police or road authority; 2 operator or
organiser; 3 approved commercial or partner; 4 discovery only (news). Colours
are the brief's: GREEN production candidate, YELLOW useful but terms/limits
need review, BLUE discovery-only, RED do not automate or use.
PERMISSION_REQUIRED marks a source whose terms are unclear or require written
permission. A newspaper reporting what the police announced is still a
newspaper: attribution, never verification.

---

## 1. Summary table

| Source | Tier | Colour | Access verified (how) | Geometry | Distance | Coordinates | Start/end | Update frequency | Terms (short) | Automation permitted? | Commercial reuse? | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mumbai Traffic Police "Public Notice List" (`mtperp.mahatrafficechallan.gov.in/PublicNotice.htm`) | 1 | YELLOW, PERMISSION_REQUIRED | GET 200, 36 KB static HTML table, 50 rows (8 Oct); one POST with the page's own `fDate`/`tDate` form returned **1,605 rows back to 21/02/2009** (8 Oct) | Road and junction names in words; "from X to Y"; none drawn | Stated in words in 72 of 1,605 rows ("100 meter") | **None** | In the notice text; 507 of 1,605 rows state a `dd/mm/yyyy` date in their English column, only 12 of the 207 rows of 2026 | Near-daily in festival season; newest row 05/10/2026 on both days | No terms on the host; departmental policy asks for permission by e-mail | Not stated; no robots.txt (404) | Unresolved | **Best Mumbai source. Already connected for the listing. Full value needs the PDFs (OCR) and a terms answer** |
| Mumbai Traffic Police departmental site (`trafficpolicemumbai.maharashtra.gov.in`) | 1 | BLUE | GET 200 (8 Oct); Notices page carries **no notice items**, only navigation | — | — | — | — | Last updated "August 07, 2023" on the Notices page | "may be reproduced free of charge after taking proper permission" | robots.txt allows the paths used | Permission + attribution | Not a source; the authoritative pointer to the listing above |
| Mumbai Police press releases (`mumbaipolice.gov.in/PressRelease`) | 1 | YELLOW, PERMISSION_REQUIRED | GET 200, static table, **51 rows, 17-Sep to 07-Oct-2026** (8 Oct); 4 PDFs downloaded and inspected | Named roads and junctions inside scanned PDFs | In the PDF ("५०० मिटर") | None | Issue date in the row; period inside the PDF | Several rows a day, mostly crime bulletins; ~4 traffic notes a month | robots.txt 404; disclaimer only, no re-use statement | Not stated | Unknown | Discovery-only; a confirmed **second source** for notifications 203, 204 and 205 |
| BMC / MCGM portal (`portal.mcgm.gov.in`, `www.mcgm.gov.in`) | 1 | RED | GET 200 but the body is 1.9 KB: "Could not open iView. The iView is not compatible with your browser…" (8 Oct) | — | — | — | — | — | None reachable | robots.txt 404 | Unknown | Nothing a plain HTTP client can read; do not automate |
| BMC Disaster Management (`dm.mcgm.gov.in`) | 1 | RED | JavaScript app on a Basic-auth API with credentials in the bundle; **not called** *(7 Oct)* | — | — | — | — | — | — | No | No | Never call; its "traffic updates" are transit status anyway |
| BMC road-works / concretisation dashboard | 1 | — | **Not verified.** Three web searches (8 Oct) describe a public dashboard "Cement Concretization Roads in Mumbai" open since 4 September and a live pothole-complaint dashboard, but **no search result gave a URL**, and none was fetched | — | — | — | — | — | — | — | — | Exists per press reports only; address unknown. Top open question |
| MMRDA (`mmrda.maharashtra.gov.in`) | 1 | YELLOW, PERMISSION_REQUIRED | GET 200 (TLS chain incomplete, verification off); news listing 7 rows + **archive page 21 rows, 20 of them 2026** (8 Oct); 4 PDFs inspected, all with a **text layer** | Project names and places in prose | In prose ("1.14 Lakh Metres of Barricades") | None | Project periods, not event periods | A few press releases a month (05-10, 30-09, 16-09, 13-09 in the last 30 days) | "documents and information displayed in this website are for reference purposes only"; "Copyright © 2026 MMRDA" | robots.txt allows the paths used | Not stated | Discovery-only. **No press release of the last 60 days states a road closure or diversion** |
| MSRDC (`msrdc.in`) | 1 | RED | HTTPS 500 "Runtime Error" at `/App_Error.aspx` (8 Oct; connection reset on 7 Oct) | — | — | — | — | — | — | — | — | Not usable. `msrdc.org` is an unrelated **real-estate blog**: exclude |
| MMRC / Metro Line 3 (`mmrcl.com`) | 1/2 | RED | GET 200, 4.5 KB React shell, no content in the HTML (8 Oct) | — | — | — | — | — | — | robots allows | — | Not usable without a browser |
| data.gov.in (and `api.data.gov.in`) | 1 | RED | `GET /search?title=mumbai road` → **HTTP 403 "Access Denied"**, robots.txt itself 403; `api.data.gov.in` refuses the connection (8 Oct) | — | — | — | — | — | Could not be read | Blocked to this client | Unknown | Blocked from this machine on both days |
| Maharashtra Commissionerate of Economics and Statistics (`mahades.maharashtra.gov.in` → `mahaces…`) | 1 | BLUE | Reachable only with certificate verification off; page says "This site is under construction"; a "Maharashtra Data Repository" table with PDF/Excel downloads (8 Oct) | — | — | — | — | — | None found | robots.txt unreachable (TLS) | Unknown | Statistics publications; no road-event data found |
| OpenCity "Mumbai Traffic and Road Safety Reports" (`data.opencity.in`) | 3 | YELLOW, PERMISSION_REQUIRED | GET 200 CKAN dataset page: 5 annual PDF reports 2019–2023, "License Other (Public Domain)", "Source https://trafficpolicemumbai.maharashtra.gov.in" (8 Oct) | — | — | — | Annual | Updated 27 Nov 2025 | "Other (Public Domain)" on the dataset page | robots.txt allows the page; `Disallow: /api/`, `Crawl-Delay: 10` | Unclear | Background statistics, not events |
| Mid-Day Mumbai RSS (`/Resources/midday/rss/mumbai.xml`, `mumbai-news.xml`) | 4 | BLUE, PERMISSION_REQUIRED | Both GET 200; **30 items each, full `content:encoded` (avg 3,699 and 3,882 chars), Mumbai-only** (8 Oct) | Place names in prose | Sometimes | None | In prose | ~30 items a day | "No part of any content … may be reproduced … other than for your personal use" | No bot clause found; robots.txt allows the feed | **No** | Connected. Technically the best Mumbai feed; terms allow personal use only |
| Indian Express Mumbai RSS | 4 | RED | GET 200, **200 items over 21 days, description and body empty on all 200** (8 Oct) | — | — | — | — | ~10 a day | "Use automated tools, bots, crawlers, scrapers … to access, extract, download, store or index any portion of the Content" is prohibited; "we may require a per-crawl fee and/or licensing agreement" | **Explicitly not** | Not without a licence | Richest road coverage but titles only, and automated access is prohibited |
| Hindustan Times Mumbai RSS | 4 | RED | GET 200, 50 items, 34 h window, one-line summaries (8 Oct) | — | — | — | — | ~35 a day | "you must not use robots, spiders, crawlers, scrapers, or similar tools to access, copy, cache, archive, or index the Services"; applies expressly to "RSS feeds" | **Explicitly not** | "not … for commercial gain without explicit written permission" | Do not automate |
| Times of India Mumbai RSS | 4 | RED | GET 200, 20-item rolling window, 16 of 20 with short summaries (8 Oct) | — | — | — | — | Rolling, ~20 h | "TIL forbids you from any attempts at displaying, hosting, aggregating, reselling or putting to commercial use … TIL's RSS feeds" | **Explicitly not** | **No** | Do not automate |
| Siasat Mumbai RSS (`/news/mumbai/feed/`, `/tag/mumbai/feed/`) | 4 | RED | Both GET 200, 40 items each, full text, mostly PTI (8 Oct) | Place names in prose | Sometimes | None | In prose | ~1 a day | "Use any data mining, robots, scrapers, crawlers, or similar data-gathering and extraction tools" prohibited; also prohibits use "for the purpose of training … any artificial intelligence, machine learning, large language model" | **Explicitly not** | "personal, non-commercial use" only | **Currently connected. Its terms now forbid what the connector does: a decision for the user** |
| Free Press Journal (`stories.rss`) | 4 | RED | GET 200, 106 items over 7 days, full text, site-wide (8 Oct) | Place names in prose | Sometimes | None | In prose | ~15 a day, ~25 % Mumbai | "Neither this website nor any part of it may be downloaded, reproduced, stored, distributed … without prior permission of Free Press Journal" | **Not without permission** | No | Do not automate without written permission |
| Mumbai Live (`/rss/en/latest.xml`) | 4 | BLUE, PERMISSION_REQUIRED | GET 200, 20 items, 2-day window, full text in `description` (avg 3,087 chars) (8 Oct) | Place names in prose | Sometimes | None | In prose | ~10 a day | **No terms page found** (`/terms-and-conditions` 404); the privacy policy names the operator "Zenlive Media Private Limited" | robots.txt **explicitly allows** AI assistants, `Crawl-delay: 5`, and everyone else `Crawl-delay: 10` | Unknown | **New this round.** The most permissive robots rules of any publisher checked, and genuinely Mumbai-infrastructure-heavy; terms unverified |
| Lokmat Mumbai (`/rss/mumbai.xml`) | 4 | BLUE, PERMISSION_REQUIRED | GET 200 but **only 10 items, all 29 September 2026** — the feed is stale by 9 days (8 Oct) | Place names in Marathi prose | Rarely | None | In prose | Stale | "personal and non-commercial use only"; no automated-tools clause found | Not stated | No | Marathi; stale feed, low value |
| Loksatta Mumbai | 4 | RED | `/mumbai/feed/` **redirects to the HTML section page**: no feed (8 Oct) | — | — | — | — | — | Same wording as Indian Express: automated tools prohibited | **Explicitly not** | No | No feed, and automation prohibited |
| The Print (`/tag/mumbai/feed/`) | 4 | RED | **HTTP 403 Forbidden** (8 Oct) although robots.txt allows | — | — | — | — | — | Not read | Blocked | — | Not usable |
| Scroll.in | 4 | BLUE | `/feed` redirects to `/page/1`; the only feed advertised is the site-wide FeedBurner one; **no Mumbai feed** (8 Oct) | — | — | — | — | — | Not read | robots allows the paths used | — | No Mumbai feed: not useful |
| News18 | 4 | RED | **403 "Access Denied"** on `/rss/` and on robots.txt (8 Oct, same as 7 Oct) | — | — | — | — | — | Could not be read | Blocked | — | Not usable |
| NDTV | 4 | RED | `ndtv.com/rss` **403**; `feeds.feedburner.com/ndtvnews-cities-news` 200 but mixed-city, 20 items, 1 road item (Noida) (8 Oct) | — | — | — | — | — | Could not be read | ndtv.com blocked | — | Not usable for Mumbai |

**The main finding, unchanged and now firmer.** Mumbai's traffic police publish
every order made under s.115 of the Motor Vehicles Act on one public page, as a
static HTML table with a PDF of the signed order. The table is the only Mumbai
source that states real road events with roads, junctions, dates and clock
times. It carries **no coordinates and no geometry**, and the detail lives in
the PDFs. BMC and MMRDA publish nothing a program can read as a road event.

**Three new findings on 8 October**, each material:

1. **The newest notice PDFs are bilingual.** Notification 209 (05/10/2026) is
   six scanned pages: pages 1–2 the Marathi order, **pages 3–4 the same order
   in English**, page 5 an **English press release**, page 6 its Marathi twin.
   The English pages name the road, the bridge, the end date and both
   alternative routes in full. If the division keeps this habit, the hardest
   part of the OCR problem (Devanagari) is not needed for the newest notices.
2. **The public date filter is still not honoured, and that is useful.** One
   POST of the page's own form (`fDate=01/09/2026`, `tDate=08/10/2026`) to
   `PublicNotice.htm` returned **the entire archive, 1,605 rows, "Total :1605",
   back to 21/02/2009** — not the 37 rows of the requested range. One request
   therefore yields the whole history (1.5 MB).
3. **The English column used to be much better.** Of the 1,605 archived rows,
   507 state a `dd/mm/yyyy` date in their English text and many read as full
   sentences ("the entire Jagannath Bhatankar road will remain closed from
   14/02/2026 to 31/05/2026 due to construction work of Sewri-Worli Elevated
   connector Bridge"). In 2024, 107 of 259 rows carried a date; in 2026 only
   12 of 207 do. The quality of the free English text has fallen sharply this
   year, which is exactly why the connector finds so little.

---

## 2. Sources, one by one

### 2.1 Mumbai Traffic Police notifications — "Public Notice List"

- **Source name:** Mumbai Traffic Police Public Notice List (orders under
  s.115, Motor Vehicles Act 1988, read with Rule 59, Central Motor Vehicles
  Rules 1989).
- **Official URL:** https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm
- **City:** Mumbai (Brihanmumbai). **Authority:** Traffic Control Branch,
  Brihanmumbai Police; orders signed by the Addl. CP (Traffic) and the five
  DCPs (Traffic). Hosted on the Maharashtra Traffic Police e-challan platform.
- **Source type:** HTML table (server-rendered, no JavaScript needed) + linked
  scanned PDFs. **No API, no RSS, no GeoJSON.** No feed was found and none is
  claimed.
- **Access verified (8 Oct):** `GET` → 200, `text/html;charset=UTF-8`, 36,246
  bytes, title "Public Notice List", `Total :50`. Columns: Sr. No. | Notice Id
  | Date | Valid Till | Subject | Notice | Download. **50 rows, newest
  05/10/2026, oldest 03/07/2026** — identical to 7 October, so **no new notice
  was issued on 6, 7 or 8 October**. "Valid Till" is "Till Next Order" on all
  50 rows and on all 1,605 archive rows.
- **The date filter, tested once (8 Oct):** the page carries two forms. The
  first (`action="PublicNotice.htm"`, `method="post"`, fields `fDate`, `tDate`,
  placeholder `DD/MM/YYYY`) is the public filter. One POST with
  `fDate=01/09/2026`, `tDate=08/10/2026` returned **HTTP 200, 1,505,418 bytes,
  "Total :1605", 1,605 rows, newest 05/10/2026, oldest 21/02/2009** — the range
  was ignored. Per year: 2009: 1, 2014: 3, 2015: 2, 2016: 13, 2017: 111,
  2018: 88, 2019: 173, 2020: 60, 2021: 55, 2022: 185, 2023: 215, 2024: 259,
  2025: 233, 2026 to 5 Oct: 207. Notice ids: 1,325 Temp, 183 Permanent.
  The second form posts to `PublicNoticeHandler.htm`; that URL **redirects to a
  login page** and was not pursued.
- **Event categories seen in the archive** (counted per notice over the 1,605
  rows, on subject + English summary): works/repair 356, closure 317, no
  parking 232, bridge 191, diversion 184, metro 131, heavy-vehicle 115,
  odd-even parking 104, procession/visarjan 66, one-way 63, flyover 46,
  excavation 39, marathon 28, VIP/VVIP 27, Coastal Road 23, subway/underpass
  15, rally 14, widening 4. Waterlogging and flooding: **0** — this source
  never publishes weather events.
- **Geometry availability:** none. Roads, junctions ("chowk"), bridges and
  "from X to Y" stretches are written in words only.
- **Distance availability:** sometimes, in words. 72 of 1,605 rows state a
  distance in their English text ("to 100 meter Natioan muton shop"); the PDFs
  state more ("५०० मिटरचा रस्ता", notification 203).
- **Coordinates availability:** **none**, on any row, in any year.
- **Start/end availability:** in the notice text. 507 of 1,605 rows state a
  `dd/mm/yyyy` date in the English column — but only **12 of the 207 rows of
  2026**. The issue date is not the start date. The PDFs state both dates and
  clock times.
- **Update frequency:** 207 notices in 2026 to 5 October ≈ one every 1.4 days;
  near-daily in festival season; nothing new in the three days to 8 October.
- **Terms / licensing (quoted):** no terms and no `robots.txt` on this host
  (404 on both days). The parent e-challan site's footer reads "© 2024
  Copyright: Maharashtra Traffic Police". The nearest policy is the
  department's, verified again today at
  https://trafficpolicemumbai.maharashtra.gov.in/en/website-policies/ :
  > "Material featured on this website may be reproduced free of charge after
  > taking proper permission by sending a mail to us. However, the material has
  > to be reproduced accurately and not to be used in a derogatory manner or in
  > a misleading context. Wherever the material is being published or issued to
  > others, the source must be prominently acknowledged."
  Whether that policy reaches this separately hosted listing, and whether REI's
  intended use needs the e-mail, is **unresolved**.
- **Automation permission:** nothing prohibits it and nothing permits it. No
  robots.txt, no rate limit published. One page view per run is 36 KB.
- **Commercial-use suitability:** **unknown**; the policy's "free of charge
  after taking proper permission" points to asking.
- **Classification:** Tier 1, **YELLOW, PERMISSION_REQUIRED**. It is not GREEN
  only because of the permission question; technically it is production-ready.
- **Connector recommendation:** the HTML listing connector already exists and
  is CONNECTED. Three additions are worth considering, in this order:
  1. **Read the English pages of the PDF** (see §3): for notification 209 the
     English pages give road, bridge, end date and both alternative routes —
     everything the listing lacks.
  2. **One archive fetch** (the POST above) to backfill 1,605 rows; 507 of them
     carry a stated date in English and far better prose than 2026's rows.
  3. Keep the PDF href percent-encoded byte for byte: the hrefs contain a
     double-encoded narrow no-break space (U+202F as `C3 A2 C2 80 C2 AF`), and
     a re-encoded link 404s. Verified again today: the four PDFs downloaded
     with byte-exact encoding all returned 200.
- **Sample events (real, read today):** see §4 items R1–R8.

### 2.2 Mumbai Traffic Police departmental website

- **URL:** https://trafficpolicemumbai.maharashtra.gov.in/ (Marathi default,
  `/en/` mirror; NIC S3WaaS WordPress). **Access verified (8 Oct):** home page
  200 (143 KB); `/en/notices/` 200 (95 KB) but its body holds **no notice
  items at all** — only the menu, the share buttons and "Last Updated: August
  07, 2023 01:03 PM". The NOTIFICATION menu entry links straight out to
  `https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm`.
- *(7 Oct)* `/feed` and `/rss` return HTTP 500 "No feed available!";
  `/wp-json/wp/v2/types` returns 401; the Excavation and Rally pages are NOC
  application forms for organisers, not public notices.
- **robots.txt (8 Oct):** `User-agent: * / Disallow: /wp-admin/ / Allow:
  /wp-admin/admin-ajax.php` — everything used is allowed.
- **Terms:** the copyright policy quoted in §2.1. **Tier 1, BLUE.** Not a
  source; the official pointer to the listing. No connector.

### 2.3 Mumbai Police (Brihanmumbai Police) press releases

- **URL:** https://mumbaipolice.gov.in/PressRelease — **access verified (8
  Oct):** 200, 69 KB, static table, **51 rows from 17-Sep-2026 to
  07-Oct-2026**, each with a PDF at `/files/PressRelease/<n>.pdf` (ids 3955 to
  4004). Most rows are police-station crime bulletins and "Preventive Orders";
  the traffic ones are the DCP (Traffic) press notes.
- **Four PDFs downloaded and read today** (raw-bytes evidence in §3). They are
  the press-note twins of notifications the Traffic Police listed:
  - `3959.pdf` (18-09-2026, DCP HQ & Central Traffic) = **permanent
    notification No. 203**: Old Cadell Road / Swatantryaveer Savarkar Road,
    "माहिम जंक्शन ते हरिओम जंक्शन" (Mahim Junction to HariOm Junction), "असा
    अंदाजे ५०० मिटरचा रस्ता" [a road of about 500 metres], declared odd-even
    parking permanently from 19/09/2026 00:01.
  - `3962.pdf` (19-09-2026) = **notification No. 205**, Dadar Traffic Division,
    Angarki Sankashti Chaturthi on 29/09/2026, 06:00–24:00: six roads listed
    (Swatantryaveer Savarkar Marg, S. K. Bole Road, Gokhale Road south and
    north, Kakasaheb Gadgil Marg, Sayani Road, Appasaheb Marathe Marg) with
    five specific turn and entry closures around Siddhivinayak temple.
  - `3963.pdf` (19-09-2026) = **notification No. 204**, Worli: G. M. Bhosale
    Marg (Pra. Ke. Kurane Chowk to Acharya Atre Chowk), 24-hour no parking for
    taxis/commercial/heavy vehicles plus odd-even parking for two- and
    four-wheelers, **from 20/09/2026 00:01 to 18/12/2026 24:00**.
  - `3970.pdf` (23-09-2026) = Anant Chaturdashi press note for the 25/09/2026
    visarjan processions: deployment numbers only, no roads.
  This settles open question 6 of the 7 October report: those press notes **do**
  duplicate notifications 203–205, and they carry the same roads, distances and
  dates as the orders.
- **Geometry/coordinates:** none. **Distance:** in the PDF text ("५०० मिटर").
  **Start/end:** in the PDF text, precise, with clock times. **Update
  frequency:** several rows a day overall; roughly four traffic notes a month.
- **robots.txt:** 404 (8 Oct). **Terms:** a disclaimer only; **no re-use
  statement found**, so permission status is unknown.
- **Classification:** Tier 1, **YELLOW, PERMISSION_REQUIRED**, discovery and
  corroboration only. **Connector recommendation:** none for now. Its value is
  as the second source for an event already taken from the notification list,
  and as an easier-to-OCR copy of the same order (the press notes are 200 dpi
  scans of printed Marathi, see §3).

### 2.4 BMC / MCGM

- **URLs tested (8 Oct):** https://portal.mcgm.gov.in/ and
  https://www.mcgm.gov.in/ both 200 but both redirect to
  `/irj/portal/anonymous` and return a **1,872-byte SAP page** whose entire
  body is: "Could not open iView. The iView is not compatible with your
  browser, operating system, or device. Contact your system administrator for
  more information." There are no links, no data and nothing to parse. A
  browser User-Agent was **not** spoofed. robots.txt: 404 on both hosts.
- *(7 Oct)* A deep-linked PDF (the 2023 Comprehensive Trench Policy, 2 MB, 101
  pages) is fetchable under `/irj/go/km/docs/documents/…`, which shows that
  documents are reachable when their exact path is known. No index of those
  paths is reachable.
- **Road-works / pothole dashboards: not verified.** Three web searches today
  returned consistent press reporting that BMC opened a public dashboard
  "Cement Concretization Roads in Mumbai" on 4 September and a live
  pothole-complaint dashboard, with road lists, mapping, photographs and
  contractor contacts. **No search result gave a URL**, the Business Standard
  article about it returned 403 to a fetch, and I will not guess an address.
  No BMC open-data portal, trench-permission dashboard or monsoon/flooding page
  was reachable. Every one of these remains **unverified**.
- **Disaster Management (`dm.mcgm.gov.in`)** *(7 Oct)*: an Angular app whose
  data comes from a private API with credentials embedded in its JavaScript.
  **Not called, credentials not recorded, and it must never be called.** Its
  "Traffic Updates", by the bundle's own variable names, are
  airline/BEST/monorail/rail/metro status, not roads.
- **Geometry, distance, coordinates, start/end, frequency, terms:** none
  obtainable. **Classification:** Tier 1, **RED** (nothing automatable; the
  disaster-management API off limits). **Connector recommendation:** none.
  A browser session, done by a person, is the only way to settle whether the
  dashboards exist at a public address.

### 2.5 MMRDA

- **URL:** https://mmrda.maharashtra.gov.in/ (Drupal; Marathi default, `/en/`).
  The server sends an incomplete TLS chain, so fetches need certificate
  verification off — recorded as a defect of the source, not a workaround of
  any access control.
- **Access verified (8 Oct):** `/en/other-services/news-and-announcements` 200
  (112 KB): 7 rows, the newest three dated 05-10-2026. The archive is at
  `/en/news-and-announcements/archive` (200, 145 KB; the path in the 7 October
  report, `…/other-services/news-and-announcements/archive`, is a 404 — noted
  as a correction): **21 rows, 20 of them 2026**, newest 30-09-2026, with
  `?page=0…12` pagination.
- **Titles of the last 60 days** (the brief asks specifically): 05-10 "UCL …
  Partnership with MMRDA"; 05-10 "From Mapping to Master Planning … Mumbai 3.0
  and Mumbai 4.0 ELU Reports"; 05-10 "MMRDA Makes PAP Rehabilitation More
  Transparent and Digital through 'e-Punarvasan'"; 30-09 "MMRDA establishes a
  Safety & Response Co-ordination Centre (SRCC)"; 16-09 "600 TPD Integrated
  Solid Waste Processing Facility Achieves 60% Progress"; 13-09 "Metro Line 9
  Phase 2 Nears Commissioning; Special Morning Block". **None states a traffic
  diversion or a road closure.** The only item that restricts anything is a
  *rail* measure (Metro services starting at 6:30 AM, 15–25 September).
- **PDFs have a text layer** (new, verified today): all four MMRDA PDFs
  inspected are "Microsoft: Print To PDF" documents with `/Type /Font`,
  `/FontDescriptor` and embedded `/FontFile` objects and no page images (or
  only photographs). English text extracts cleanly with nothing but `zlib` and
  the font's own ToUnicode map; the Marathi half of each release uses legacy
  encodings that come out garbled. So MMRDA needs **no OCR**, only a PDF text
  reader.
- **Geometry/coordinates:** none. **Distance:** occasionally in prose.
  **Start/end:** project periods, not event periods. **Update frequency:** a
  few releases a month.
- **Terms (quoted, fetched today,
  https://mmrda.maharashtra.gov.in/en/terms-and-conditions):**
  > "The documents and information displayed in this website are for reference
  > purposes only and does not purport to be a legal document. MMRDA does not
  > warrant the accuracy or completeness of the information…"
  Footer: "Copyright © 2026 MMRDA ® All Rights Reserved". The disclaimer adds:
  "MMRDA does not take responsibility on how this information is used or the
  consequences of its use." No licence, no re-use grant.
- **robots.txt:** Drupal defaults; every path used is allowed.
- **Classification:** Tier 1, **YELLOW, PERMISSION_REQUIRED**, discovery-only.
  **Connector recommendation:** none now. If MMRDA is wanted later, a listing
  connector over the archive table plus a text-layer PDF read is
  straightforward — but on 60 days of evidence it would produce **no road
  events**, only project context.

### 2.6 Others checked (8 Oct unless stated)

- **MSRDC:** `https://msrdc.in/` now answers **HTTP 500, "Runtime Error"**
  (`/App_Error.aspx?aspxerrorpath=/`) instead of resetting. The authority's own
  site is therefore still unreadable. `msrdc.org`, fetched today, is a
  **real-estate marketing blog** ("Atal Setu to Alibaug: Why Mumbai Buyers Are
  Looking at Land Differently") with a WordPress feed: **not the authority,
  exclude it, and make sure nothing in REI ever points at it.** RED.
- **MMRC / Metro Line 3:** `mmrcl.com` 200 but a 4,535-byte React shell with no
  content in the HTML. RED (needs a browser).
- **data.gov.in:** `GET /search?title=mumbai%20road` → **403 "Access Denied"**,
  384 bytes; its robots.txt is itself 403; `api.data.gov.in` refuses the
  connection. Identical to 7 October. Nothing about licences could be read, so
  the Government Open Data License India is **not verified** for any dataset.
  RED.
- **Maharashtra state open data:** the state's statistics portal
  `mahades.maharashtra.gov.in` redirects to `mahaces.maharashtra.gov.in` and is
  reachable only with certificate verification off; the page states "This site
  is under construction" and offers a "Maharashtra Data Repository" with PDF
  and Excel downloads of economic indicators. **No roads, traffic or accident
  dataset was found.** No other Maharashtra open-data portal was found. BLUE.
- **OpenCity (`data.opencity.in`), Tier 3:** a civic data portal, not a
  government one. Its dataset "Mumbai Traffic and Road Safety Reports" (200,
  CKAN) lists the Mumbai Road Safety Annual Reports 2019–2023 as PDFs, with
  "License: Other (Public Domain)", "Source: https://trafficpolicemumbai.maharashtra.gov.in",
  "Last Updated: November 27, 2025". robots.txt allows dataset pages,
  disallows `/api/`, `Crawl-Delay: 10`. Background statistics, no events.
  YELLOW, PERMISSION_REQUIRED (a third party's "Public Domain" label is not
  the authority's licence).

### 2.7 News and discovery sources (Tier 4)

All feeds below were fetched today, their robots.txt checked first, and their
terms pages fetched and quoted. **Every publisher's terms restrict use to
personal, non-commercial reading.** Six go further and prohibit automated
access outright; those are RED, whatever their robots.txt allows. This is a
legal question for the user; I am recording the words, not advising.

| Outlet | Feed verified today | Items / window | Body in feed | robots.txt (`*`) | Terms (quoted) | Colour |
| --- | --- | --- | --- | --- | --- | --- |
| **Mid-Day** | `/Resources/midday/rss/mumbai.xml` and `/mumbai-news.xml` | 30 each; `mumbai.xml` ~20 h | Full `content:encoded`, avg 3,699 / 3,882 chars | Allows the feed | "No part of any content, form or document may be reproduced in any form … other than for your personal use (but not for resale or redistribution)" | BLUE, PERMISSION_REQUIRED |
| **Indian Express** | `/section/cities/mumbai/feed/` | 200 / 21 days | **Empty on all 200** | Allows | "Use automated tools, bots, crawlers, scrapers … to access, extract, download, store or index any portion of the Content" prohibited; "In the case of approved access, we may require a per-crawl fee and/or licensing agreement" | **RED** |
| **Hindustan Times** | `/feeds/rss/cities/mumbai-news/rssfeed.xml` | 50 / 34 h | One-line summaries (avg 170 chars) | Allows | "These terms apply to … RSS feeds"; "you must not use robots, spiders, crawlers, scrapers, or similar tools to access, copy, cache, archive, or index the Services" | **RED** |
| **Times of India** | `/rssfeeds/-2128838597.cms` | 20 rolling / 20 h | 16 of 20 short summaries | Allows | "TIL forbids you from any attempts at displaying, hosting, aggregating, reselling or putting to commercial use either directly or indirectly TIL's RSS feeds" | **RED** |
| **Siasat** | `/news/mumbai/feed/` (newest 29 Sep), `/tag/mumbai/feed/` (newest 6 Oct) | 40 each | Full text, avg ~3,000 chars | Allows | "Use any data mining, robots, scrapers, crawlers, or similar data-gathering and extraction tools" prohibited; and no use "for the purpose of training, developing, or fine-tuning any artificial intelligence, machine learning, large language model, or similar system" | **RED** (and connected today) |
| **Free Press Journal** | `/stories.rss` (site-wide; `/*/feed` is robots-disallowed and was not fetched) | 106 / 7 days | Full text | Allows `stories.rss` | "Neither this website nor any part of it may be downloaded, reproduced, stored, distributed, adapted, translated or transmitted in any form … without prior permission of Free Press Journal" | **RED** |
| **Mumbai Live** | `/rss/en/latest.xml` | 20 / 2 days | Full text in `description` | **Explicitly allows AI assistants** (`ClaudeBot`, `GPTBot`, `PerplexityBot` … `Crawl-delay: 5`); everyone else `Crawl-delay: 10`; only `/search` closed | **No terms page**: `/terms-and-conditions` 404; `/policy` is a privacy policy for "Zenlive Media Private Limited" | BLUE, PERMISSION_REQUIRED |
| **Lokmat** | `/rss/mumbai.xml` | 10, **all 29 Sep 2026** (stale) | Titles + 150-char summaries, Marathi | Allows | "a personal, limited, non-exclusive … license to use the Services for the personal and non-commercial use only" | BLUE, PERMISSION_REQUIRED |
| **Loksatta** | `/mumbai/feed/` → **redirects to the HTML page**; no feed | — | — | Allows | Same clause as Indian Express (same publisher group) | **RED** |
| **The Print** | `/tag/mumbai/feed/` | **403** | — | Allows (but the server refuses) | Not read | **RED** |
| **Scroll.in** | `/feed` → `/page/1`; only a site-wide FeedBurner feed exists | — | — | Allows | Not read | BLUE (no Mumbai feed) |
| **News18** | `/rss/` **403**, robots.txt **403** | — | — | Unreadable | Not read | **RED** |
| **NDTV** | `ndtv.com/rss` **403**; FeedBurner `ndtvnews-cities-news` 200, 20 items, mixed cities, 1 road item (Noida) | — | Summary only | ndtv.com unreadable | Not read | **RED** for Mumbai |

**Connector view.** Mid-Day and Mumbai Live are the only two Mumbai publishers
whose feeds carry full text *and* whose terms do not prohibit automated access
in so many words — and both still restrict use to personal reading, so both are
PERMISSION_REQUIRED and neither is clean for a commercial product. Mumbai Live
is new in this round and is the most Mumbai-infrastructure-focused feed read on
either day (three of 20 items in two days were road or excavation items).
**The Siasat feed, connected on 8 October, is RED by its own current terms**:
the user should decide whether to keep it connected, ask Siasat, or drop it.

---

## 3. PDFs and OCR

### 3.1 Raw-bytes evidence for the PDFs sampled today

No PDF library is installed on this machine and pip is broken, so each file was
inspected byte by byte with the standard library only (`re`, `zlib`): page
objects (`/Type /Page`), font objects, image XObjects with `/Width` and
`/Height`, `/MediaBox`, and text operators in inflated streams. Page images
were then written out unchanged (JPEG) for reading, into
`scratchpad/mum-fetched/pdf-extract-3/`. *(An earlier extraction run wrote
truncated files into `pdf-extract-2/` and `_images/` because indirect
`/Length` references were mishandled; those directories are left in place and
are wrong — use `pdf-extract-3/`.)*

| PDF | Pages | Fonts | Page images | Estimated DPI on A4 | Text layer? |
| --- | --- | --- | --- | --- | --- |
| Notification **209**, 05/10/2026 (`…823622_DocScanner 6 Oct 2026…pdf`, 1,888,433 B) | 6 | **0** | 6, 1797×2563 to 2024×2852, DCTDecode + FlateDecode, RGB 8-bit | **~217–245 dpi** | **No** — scanned images |
| Notification **199**, Lalbaugcha Raja, 09/09/2026 (`…823358…pdf`, 1,896,897 B, "Epson Scan 2") | 8 | **0** | 8, ~1,665×2,352 | **~201 dpi** | **No** |
| Notification **187**, Coastal Road permanent, 25/08/2026 (`…823227…pdf`, 581,221 B, "iLovePDF") | 8 | **0** | 8, ~583×842 (JPEG inside Flate) | **~70 dpi** | **No**, and far too low to OCR reliably |
| Notification **168**, Belasis ROB, 18/07/2026 (`…822776_BELASIS ROAD signed.pdf`, 383,639 B, "Microsoft® Word 2010") | 4 | **10** (`DVOT-SurekhMR`, `Kruti`, `Calibri`, `Times`; 7 `/FontFile*`) | 8 small logos/signatures | n/a | **Yes**, but the Marathi is in **legacy non-Unicode fonts**: 941 `TJ` operators decode to mojibake ("eg kjk\"V\ª") without a font-specific mapping |
| Mumbai Police press notes **3959, 3962, 3963** (Epson Scan 2) | 4 each | **0** | 4 each, ~1,663×2,337 | **~200 dpi** | **No** |
| Mumbai Police press note **3970** (intsig.com) | 1 | **0** | 1 page image 2,248×3,004 | **~257–272 dpi** | **No** |
| MMRDA press releases (4 inspected, "Microsoft: Print To PDF") | 1–10 | 4–10 with `/FontFile*` | 0–2 photographs | n/a | **Yes** — English extracts cleanly with `zlib` + ToUnicode; Marathi garbles |

**What this means.** The Mumbai Traffic Police orders and the Mumbai Police
press notes are **scans with no text layer**: nothing short of OCR will read
them. Resolution is adequate for OCR in most cases (200–272 dpi for A4, which
is at or above the 200 dpi that OCR engines usually want for printed text), but
notification 187 at ~70 dpi would be unreliable. One older order (168) is a
true Word-made PDF, yet its Marathi is in legacy Kruti/Surekh fonts, so it is
**no easier** than a scan without a font mapping. MMRDA's PDFs need no OCR at
all.

**The bilingual discovery (8 Oct).** Notification 209's six pages are: 1–2 the
Marathi order, **3–4 the English order**, 5 an **English press release**, 6 its
Marathi twin. Read today from page 3:
> "WHEREAS, the Municipal Corporation of Greater Mumbai has proposed to demolish
> the existing Mogra Nala Bridge on Caesar Road, within the jurisdiction of
> D. N. Nagar Traffic Division … hereby impose the following temporary traffic
> arrangements … with effect from date of issuance of this notification until
> 31/05/2027."
and from page 4:
> "All vehicles proceeding northbound from Caesar Road towards J. P. Road
> shall, near Gateway Building, enter Azad Nagar Lane No. 3, proceed straight
> up to Omkar Food Court, and thereafter proceed towards J. P. Road via Veera
> Desai Road."

If newer notices keep this pattern, **English-only OCR (Latin script) would
recover road names, junctions, dates and alternate routes for the newest
orders** — a much easier problem than Devanagari. How widespread the pattern is
has **not** been measured: it was found in one of the four PDFs sampled today.

### 3.2 OCR engine options (desk research, nothing installed)

This machine has **Smart App Control ON** (it already blocks an unsigned
SQLAlchemy `.pyd`) and **pip is broken**, so any option that needs a pip
install of compiled wheels is, in practice, unavailable here today. Nothing
below was installed, run or benchmarked.

| Engine | Devanagari / Marathi support | What installing it needs on Windows | Fit on this machine |
| --- | --- | --- | --- |
| **Tesseract 5** | `mar` (Marathi), `hin` (Hindi) and a `Devanagari` script model in `tessdata`; the project documents that accuracy depends heavily on matching the training font to the scan's font | A signed **binary installer** (the UB Mannheim build is the usual Windows source) plus traineddata files; a Python wrapper (`pytesseract`) only shells out to the exe | **The only realistic option.** An installer is a signed executable, not a pip wheel, so Smart App Control is far less likely to block it; the Python side is pure Python |
| **EasyOCR** | Devanagari models cover `mr`, `hi`, `ne` (added in 1.1.5) | pip install of EasyOCR **plus PyTorch** (large compiled wheels) | Not available: pip is broken, and Smart App Control blocks unsigned compiled modules |
| **PaddleOCR** | A `devanagari` recognition model in its multilingual set | pip install of PaddlePaddle + PaddleOCR (compiled wheels) | Not available, same reasons |
| **Google Cloud Vision / Azure AI Vision** | Both market Devanagari support | No local install; an account, a key and **payment** | Ruled out by the brief: no paid APIs, no credentials |

**Accuracy: not measured, and not claimed.** No engine was run on these files,
so this report states **no accuracy figure** for Marathi, Devanagari or
English on these scans. Published accounts of Devanagari OCR vary with scan
quality, font and layout; Marathi orders on 200 dpi scans with stamps, tables,
handwritten numerals in the notice number, and a signature overlay are the hard
end of that range. The handwritten parts (the outward number, sometimes the
notification number and the date) will **not** be read reliably by any engine.

**Fields that could be extracted** if OCR is added, taken from what the sampled
PDFs actually contain: road and bridge names; junction ("chowk"/"junction")
names; from–to stretch endpoints; the division and jurisdiction; start and end
dates; clock-time windows; a stated distance ("५०० मिटर", "100 meter");
direction (north/south-bound, "दक्षिण वाहिनी"); the restriction type (closed,
no entry, no parking, odd-even, one-way, reverse lane, heavy-vehicle ban); the
numbered **alternative routes**; and the issuing officer.

**Validation rule (the brief's, restated so it cannot be lost).** OCR output is
**extracted evidence, not fact**. Any event built from OCR must be stored with
the page image and the PDF link, start as VALIDATION_REQUIRED, and never be
approvable without a human reading the order. Low-confidence output must be
flagged for review rather than silently accepted, and the source's own words
must be kept verbatim beside anything REI derives from them. Nothing read by
OCR should ever be presented as an exact location.

---

## 4. Real events available now

Everything below was **read today, 8 October 2026**, in the source named.
Quotes are verbatim; bracketed glosses are mine. "Current" means in force or
upcoming as of today; past items are marked.

**From the Mumbai Traffic Police notifications (Tier 1)**

- **R1 — Mogra Nala Bridge on Caesar Road, Andheri West: closed to all
  vehicles until 31/05/2027, with two alternative routes. CURRENT,
  LONG-RUNNING.** Notification No 209/DCP/Traffic/Western Suburbs/Temp/2026,
  dated 05/10/2026, signed by Ajit Borhade, DCP Traffic (Western Suburbs).
  Listing row: "Traffic Restrictions and Alternative Routes". PDF page 3:
  "The Mogra Nala Bridge on Caesar Road shall remain completely closed to all
  vehicular traffic during the period specified in this notification, for the
  demolition of the existing bridge and construction of the new bridge." PDF
  page 4 gives both alternative routes (quoted in §3.1).
  URL: https://mtperp.mahatrafficechallan.gov.in/PublicNotice.htm → PDF
  `GetPublicNotice/823622/202610050000_823622_DocScanner 6 Oct 2026 10-51 am.pdf`.
  Categories: **closure, construction, bridge, diversion, long-running.**
  *Correction to the 7 October report: the road is written "Caesar Road" in the
  English pages; "Seezer Road" there was a transliteration of the Marathi
  "सीझर रोड". Same road.*
- **R2 — Coastal Road and Rajiv Gandhi Sea Link: permanent restrictions on
  entry and exit points, vehicle types, speed, stopping and filming. CURRENT,
  LONG-RUNNING.** Notification No 187/ADD-CP/Traffic/Permanent/2026,
  25/08/2026, signed Mokshada Patil, Addl. CP (Traffic). The PDF lists entry
  and exit points per carriageway in a table (southbound entries: "बांद्रा टोल
  प्लाझा", "र.के. कपूर सर्कल अंडरपास", "स्व. बिंदू माधव ठाकरे चौक", "बॅरिस्टर
  रजनी पटेल चौक (लोटस जंक्शन)", "वत्सलाबाई देसाई चौक (हाजी अली जंक्शन)",
  "अमरसन्स गार्डन"). Listing text: "Restrictions apply on Dharmveer Swarajya
  Rakshak Chhatrpati Sambhaji Maharaj Mumabai costal Road and Rajiv Gandhi Sea
  Link regarding Entry and Exit Points, vehicles restricted from entry, speed
  limits, and restrictions on stopping or filming." PDF
  `GetPublicNotice/823227/202608250000_823227_Costal Road  permanent Notification -187_1.pdf`.
  Categories: **long-running, lane/entry restriction, junction.**
- **R3 — G. M. Bhosale Marg, Worli: 24-hour no parking plus odd-even parking,
  20/09/2026 00:01 to 18/12/2026 24:00. CURRENT (parking only).**
  Notification No 204/DCP/Central HQ/Traff/Temp/2026, 19/09/2026, read today in
  Mumbai Police press note https://mumbaipolice.gov.in/files/PressRelease/3963.pdf :
  "जी.एम. भोसले मार्ग दक्षिण वाहिनी व उत्तर वाहिनी — २४ तास — टॅक्सी/ व्यवसायिक
  चारचाकी वाहने/ अवजड वाहने". Two-source pair with the listing row
  "Traffic Arrangement" (PDF `…823456_51. Worli - G.M. Bhosale rd…`).
  Categories: **parking (evidence, not a road event by REI's rule), two-source.**
- **R4 — Old Cadell Road / Swatantryaveer Savarkar Road, Mahim Junction to
  HariOm Junction, about 500 m: permanent odd-even parking from 19/09/2026.
  CURRENT (parking only).** Permanent notification No 203, 18/09/2026, read in
  press note https://mumbaipolice.gov.in/files/PressRelease/3959.pdf :
  "ओल्ड कॅडल रोड/स्वातंत्रवीर सावरकर रोड (माहिम जंक्शन ते हरिओम जंक्शन) असा
  अंदाजे ५०० मिटरचा रस्ता सम विषम पार्किंग घोषित". Categories: **distance
  (500 m), junction, stretch, long-running, two-source.**
- **R5 — Belasis ROB (Poonya Shlok Ahilyabai Bridge), southbound, Mumbai
  Central Junction to the bridge: closed. STATUS UNCERTAIN — "Till Next
  Order".** Notification No 168/DCP/South traffic/Temp/2026, 18/07/2026.
  Listing text, read today: "Poonya Shlok Ahilyabai Bridge (Belasis ROB), South
  bound- Mumbai Central Junction to Poonya Shlok Ahilyabai Bridge closed for
  traffic." The PDF has a text layer but in legacy Marathi fonts (§3.1), so the
  end date could not be read. Categories: **closure, bridge, stretch,
  junction.**
- **R6 — Mansukh Naka to Kanjurmarg Railway Station (East): 24-hour no parking
  on both sides. CURRENT (parking only).** Notification No 167/DCP/East
  Traffic/Temp/2026, 17/07/2026, listing text read today. Categories:
  **stretch, parking.**
- **R7 — BKC Connector Bridge northbound to Nehru Nagar Kurla Bridge
  southbound: reverse lane, permanent. CURRENT, LONG-RUNNING.** Notification No
  166/DCP/Central HQ traffic/Permanent/2026, 16/07/2026: "Reverse Lane Started
  From BKC Connector Bridge North Bound Upword Slope Up To South Bound Nehru
  Nagar Kurla Bride." Categories: **lane restriction, stretch, bridge.**
- **R8 — Sakinaka Junction to Disha Hospital, Andheri–Ghatkopar Link Road:
  peak-hour no parking, both channels. CURRENT (parking only).** Notification
  No 160/Dcp/East traffic/Temp/2026, 03/07/2026. Categories: **junction,
  stretch, parking.**
- **R9 — Dadar division, Angarki Sankashti Chaturthi: six roads under
  restriction and five turn/entry closures, 29/09/2026 06:00–24:00. PAST.**
  Notification No 205, 19/09/2026, read today in press note
  https://mumbaipolice.gov.in/files/PressRelease/3962.pdf : "गोखले रोड दक्षिण
  वरुन पोर्तुगीज चर्च जंक्शन येथून एस. के. बोले मार्गावर उजवे वळण बंद"
  [right turn from Gokhale Road south at Portuguese Church junction onto
  S. K. Bole Marg closed], and four more. This is the PDF behind the listing
  row "Closure of roads in Dadar Division" that REI stored with no location and
  no dates — **the single best illustration of what OCR would add**.
  Categories: **closure, diversion, procession/festival, junction, multi-road.**
- **R10 — Jagannath Bhatankar Road, Dadar: entire road closed 14/02/2026 to
  31/05/2026 for the Sewri–Worli Elevated Connector Bridge. PAST (from the
  archive).** Notification No 57/DCP/HqCentral/Temp/2026, 13/02/2026, English
  listing text read today in the 1,605-row archive. Categories: **closure,
  construction, long-running.** Quoted here because it shows what the English
  column used to carry and what the archive fetch would recover.
- **R11 — Andheri Subway: closed to all vehicles 01:00–05:00 nightly,
  16/01/2026 to 18/01/2026, for repair work. PAST (archive).** Notification No
  14/DCP/West/Temp/2026, 12/01/2026. Categories: **closure, underpass,
  maintenance, night window.**
- **R12 — Zaveri Bazaar / Sheikh Memon Street, Badshah Junction to Surti Hotel
  Junction: 24-hour no-parking zone. PAST/UNCERTAIN (archive).** Notification
  No 76/ADDLCP/Traff/Temp/2026, 13/03/2026. Categories: **stretch, junction,
  parking.**

**From news (Tier 4, discovery only; attribution as the article states it)**

- **R13 — Thane, Navratri: traffic restrictions at Tembhi Naka and Bhawani
  Chowk, 11 to 20 October 2026, 16:00 to midnight daily. UPCOMING.** Mid-Day,
  8 October 2026: "Traffic restrictions will be imposed in parts of Thane from
  October 11 to 20 as large crowds are expected to visit the Durga Devi temple
  at Tembhi Naka during Navratri celebrations. The restrictions will be in
  force daily from 4 pm to midnight around Bhawani Chowk and Tembhi Naka …
  Thane Traffic Police said."
  https://www.mid-day.com/mumbai/mumbai-news/article/navratri-2026-thane-police-announce-traffic-restrictions-at-tembhi-na
  Attribution: Thane Traffic Police (outside Brihanmumbai's notification
  system). Categories: **festival, gathering, restriction, upcoming.**
- **R14 — Thane: hydraulic crane collapses at an MMRDA elevated-road site near
  Siddheshwar Talao; an auto-rickshaw damaged, two injured. TODAY.** Free Press
  Journal, 8 October 2026: "A hydraulic crane fell at the MMRDA Elevated Road
  construction site on the service road near Siddheshwar Talao, Thane (West)
  damaging an auto-rickshaw."
  https://www.freepressjournal.in/mumbai/thane-crane-accident-hydraulic-crane-collapses-at-mmrda-elevated-road-constructio
  Categories: **accident, construction, emergency.**
- **R15 — Yari Road–Lokhandwala flyover, Andheri West: completion targeted
  December 2027. CURRENT WORKS.** Mumbai Live, 6 October 2026: "The
  long-delayed flyover connecting Yari Road with Lokhandwala Back Road in
  Andheri West is now targeted for completion by December 2027, with the
  Brihanmumbai Municipal Corporation (BMC) directing officials to accelerate
  construction". Attribution: BMC Additional Municipal Commissioner (Projects).
  https://www.mumbailive.com/en/infrastructure/yari-road-lokhandwala-flyover-in-andheri-west-set-for-december-2027-complet
  Categories: **flyover, construction, long-running.** Corroborated by Indian
  Express, 6 October, title only: "25 years, three times the cost:
  Versova-Yari Road bridge gets a December 2027 deadline".
- **R16 — BMC proposes a Comprehensive Trenching and Reinstatement Policy 2026
  with five-times fines for unauthorised digging. POLICY, NOT AN EVENT.**
  Mumbai Live, 6 October 2026: "The proposed Comprehensive Trenching and
  Reinstatement Policy 2026 includes stricter penalties for unauthorised
  digging, longer defect-liability periods and mandatory digital mapping of
  underground utilities."
  https://www.mumbailive.com/en/infrastructure/bmc-proposes-five-times-fine-for-unauthorised-road-excavation-across-mumbai
  Categories: **excavation, utility (context).** Notable for REI because
  "mandatory digital mapping of underground utilities" is the kind of dataset
  that might one day be public.
- **R17 — Navi Mumbai: nine-point plan for Palm Beach Road after repeated
  crashes; four black spots identified. CURRENT.** Mumbai Live, 7 October 2026:
  "Navi Mumbai traffic police have submitted a nine-point action plan to the
  civic administration to curb frequent accidents on Palm Beach Road, including
  installing more rumblers, AI-based speed cameras and improved road signage."
  https://www.mumbailive.com/en/civic/navi-mumbai-traffic-police-propose-new-measures-to-curb-palm-beach-road-accidents-94
  Categories: **accident black spots, stretch.** No closure stated.
- **R18 — Coastal Road BMW crash follow-up. PAST EVENT, CURRENT REPORTING.**
  Times of India, 7 October 2026: "BMW crash on Coastal Road: Lone survivor
  says he remembers nothing".
  https://timesofindia.indiatimes.com/city/mumbai/bmw-crash-on-coastal-road-lone-survivor-says-he-remembers-nothing/
  Categories: **accident.** No closure stated. (TOI is RED: read once for this
  report, not to be fetched by a connector.)
- **R19 — Goregaon–Airoli double-decker bridge, "1.6km-long". LONG-RUNNING
  WORKS.** Indian Express, 2 October 2026, title only (the feed carries no
  body): "Changing City: Now, Goregaon-Airoli in 20 mins with Mumbai's
  1.6km-long double-decker bridge".
  https://indianexpress.com/article/cities/mumbai/changing-city-goregaon-airoli-20-mins-mumbai-double-decker-bridge-10903565/
  Categories: **construction, distance, long-running.**
- **R20 — Worli: flyover and subway linking Nehru Science Centre and
  Planetarium, "likely by January 2027". LONG-RUNNING WORKS.** Indian Express,
  1 October 2026, title only.
  https://indianexpress.com/article/cities/mumbai/worli-flyover-subway-nehru-science-centre-and-planetarium-january-2027-1
  Categories: **flyover, underpass, construction, long-running.**
- **R21 — "275 roads, Rs 380 crore work pending as BMC moves to drop two
  contractors". LONG-RUNNING WORKS, CITYWIDE.** Indian Express, 28 September
  2026, title only.
  https://indianexpress.com/article/cities/mumbai/275-roads-rs-380-crore-work-pending-mumbai-civic-body-bmc-contractors-10
  Categories: **road works, multi-road, no location.**

**Categories covered by the real events above:** closure (R1, R5, R9, R10,
R11), diversion (R1, R9), long-running (R1, R2, R4, R7, R10, R15, R19, R20,
R21), construction (R1, R10, R14, R15, R19, R20, R21), flyover (R15, R20),
underpass/subway (R11, R20), excavation/utility (R16), widening (none found),
procession/festival (R9, R13), gathering (R13), marathon (notification 208,
04/10/2026, now past), emergency/accident (R14, R17, R18), maintenance (R11),
one-way / lane restriction (R2, R7), parking (R3, R4, R6, R8).
**Waterlogging and flooding: no current event found in any source today** — the
monsoon has withdrawn (Indian Express, 3 October: "Maharashtra monsoon
withdraws early as 21 districts record rain deficit"), and the notification
archive contains no waterlogging notices at all.

---

## 5. Open questions

1. **BMC's dashboards.** Press reporting says a public road-concretisation
   dashboard and a live pothole-complaint dashboard exist. **No URL was found
   and nothing was fetched.** Only a person with a browser can settle this; if
   a public address exists it would be the first Mumbai source with road-level
   works data.
2. **Re-use permission for the Traffic Police listing** is still unresolved
   (the department's policy asks for an e-mail). Nobody has asked. Until
   somebody does, the source stays YELLOW/PERMISSION_REQUIRED and commercial
   use is unknown.
3. **The Siasat feed is connected but its terms now prohibit scrapers and AI
   use in so many words.** A decision is needed: keep, ask, or disconnect.
   Mid-Day's terms allow personal use only, which also does not obviously cover
   REI.
4. **How common are the bilingual PDFs?** One of four sampled notices had
   English pages. If most recent notices do, English-only OCR solves most of
   the gap; if it was a one-off, Devanagari OCR is unavoidable. This can be
   answered by downloading, say, 20 recent PDFs and counting — about 20
   requests, not done today to stay well inside the budget.
5. **Can Tesseract be installed here at all?** It is the only option that does
   not need pip. Whether its Windows installer runs under Smart App Control on
   this machine is **untested** and is a decision for the user, not something I
   would do inside a research task.
6. **No OCR accuracy is known** for these scans, in any script. Any plan that
   depends on OCR quality is, at present, a plan with an unmeasured step.
7. **Notification 187 is a ~70 dpi scan.** Even with OCR installed, some orders
   will be unreadable; the review path must stay.
8. **The archive backfill** (1,605 rows in one POST) is attractive but changes
   the shape of the data: 507 dated rows, mostly historical. Whether REI wants
   history is the user's call.
9. **data.gov.in and the state portals** gave nothing on either day; whether
   that 403 is geographic, UA-based or permanent is not known. No Maharashtra
   roads/traffic dataset has been seen, so no Government Open Data License
   India text has been read.
10. **MSRDC** (the state road development corporation, owner of the Sea Link,
    Atal Setu approaches and several Mumbai corridors) **has no readable
    website**: HTTP 500 today. Its notices, if any, are invisible to REI.
11. **MMRDA publishes no road-impact notices.** 60 days of press releases
    contain none. If MMRDA's works matter to REI, the information will have to
    come from the Traffic Police orders that implement them.
12. **Thane, Navi Mumbai and the rest of MMR** have their own traffic police
    (R13, R17) outside the Brihanmumbai notification system. Whether REI's
    "Mumbai" includes them is a scope question for the user.

---

## 6. Counts

- **Sources researched: 25.** Tier 1: 11 (Traffic Police listing, Traffic
  Police website, Mumbai Police press releases, BMC portal, BMC disaster
  management, BMC dashboards [unverified], MMRDA, MSRDC, MMRC, data.gov.in,
  Maharashtra statistics portal). Tier 3: 1 (OpenCity). Tier 4: 13 news
  publishers (Mid-Day, Indian Express, Hindustan Times, Times of India, Siasat,
  Free Press Journal, Mumbai Live, Lokmat, Loksatta, The Print, Scroll,
  News18, NDTV).
- **GREEN: 0.** No Mumbai source is both clearly permitted and useful. The
  Traffic Police listing is the only production-grade source and its terms are
  unresolved.
- **YELLOW: 4** — Mumbai Traffic Police Public Notice List; Mumbai Police press
  releases; MMRDA; OpenCity.
- **BLUE: 6** — Mumbai Traffic Police departmental website; Maharashtra
  statistics portal; Mid-Day; Mumbai Live; Lokmat; Scroll.
- **RED: 14** — BMC portal; BMC disaster management; MSRDC (`msrdc.in`, and
  `msrdc.org` excluded as an impostor); MMRC; data.gov.in; Indian Express;
  Hindustan Times; Times of India; Siasat; Free Press Journal; Loksatta; The
  Print; News18; NDTV. (BMC's unverified dashboards are counted in neither.)
- **PERMISSION_REQUIRED: 7** — Traffic Police listing; Mumbai Police press
  releases; MMRDA; OpenCity; Mid-Day; Mumbai Live; Lokmat.
- **Production candidates: 1** — the Mumbai Traffic Police Public Notice List
  (already connected for its listing; YELLOW until the permission question is
  answered, and only partly useful until the PDFs are read).
- **Discovery sources: 6** usable today — Mumbai Police press releases, MMRDA,
  Mid-Day, Mumbai Live, Lokmat (stale), OpenCity (reference).
- **Real current or upcoming events read today: 12** (R1–R8 Tier 1, R13–R17
  Tier 4, minus the ones marked past); **21 real events in all**, including the
  past and archival ones quoted as evidence.
- **Sources with exact coordinates: 0. Sources with source-provided geometry:
  0. Sources with a distance in words: 2** (Traffic Police listing and PDFs;
  Mumbai Police press notes). **Sources with explicit start/end dates: 2**
  (Traffic Police notifications — in the PDFs always, in the English listing
  rarely; Mumbai Police press notes).
