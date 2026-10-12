# Bengaluru source research (Phase 1 + Phase 2: find, verify terms, verify technical access)

> **Status:** research only. Nothing in this document was connected, modified or
> scheduled. What is already connected (built 8 October 2026, decision
> [0017](../decisions/0017-mumbai-and-bengaluru-official-listings.md)): the
> Bengaluru Traffic Police home-page **"Upcoming Events / Press Notes"** list
> ([source page](../data-sources/bengaluru-traffic-police-website.md),
> connector `connectors/official/bengaluru_traffic_police.py`, run by hand, terms
> REVIEW_REQUIRED) and **The Hindu Bengaluru RSS** (discovery-only, tier 4). The
> home-page **"Traffic Alerts"** panel is *not* read (the user's decision).

## 1. Research dates, method, rules

- **Dates:** 7 October 2026 (19:45–20:15 IST, 143 requests, first pass) and
  **8 October 2026** (13:57–14:30 IST, second pass: re-verification and
  extension). Each finding below carries the date it was verified; a finding
  marked "7 Oct" was not re-fetched on 8 Oct unless the text says so.
- **Method (8 Oct):** the project's Python 3.12 with `httpx` 0.28, User-Agent
  `JSAN-REI source research (research@jsan.example; local test)`, one request
  per second per host, 30 s timeout, redirects followed, **REQUEST_COUNT
  requests in all** (budget 160). Every host's `robots.txt` was fetched first
  and its `*` group honoured; no fetch in this report was disallowed by it. The
  fetcher, parsers and every fetched file are kept under the session scratchpad
  (`blr-research/`, `blr-fetched/`); nothing fetched was executed.
- **Legal rules followed:** public pages only; no CAPTCHA, login, paywall or
  access control bypassed; no browser User-Agent spoofing; no endpoint called
  that was only found inside a JavaScript bundle (the GBA bundle names
  `api.bbmpgov.in` routes: only the **host root** was tested, with a plain GET);
  no mobile/private API examined (ASTraM app); no paid API, no credentials. One
  host (`gba.karnataka.gov.in`) fails certificate validation on this machine
  only (the known local CA-store problem); it was fetched once with
  verification off to read its public shell and public bundle, nothing else.
- **Tiers** (REI): 1 government / police / road authority; 2 operator or
  organiser; 3 approved commercial; 4 discovery-only (news). **Colours:** GREEN
  public + permitted + useful + production candidate; YELLOW useful but terms,
  permission or API limits need review (never auto-connected); BLUE
  discovery-only; RED do not automate / use. PERMISSION_REQUIRED is added when
  terms are unclear or require prior consent. News is evidence and leads, never
  authority: "the traffic police said" in an article is attribution, not
  verification.

**The main finding is unchanged from 7 October:** Bengaluru's traffic police
publish their actual advisories (diversions, one-ways, no-parking, VVIP
movements) on X (@blrcitytraffic) and through the press, not on their website.
The website exposes a works/events calendar with dates (most items without a
place) and a small transient alerts panel with coordinates. **New on 8
October:** the alerts panel does change during the day (cadence evidence in
§4); BBMP's hosts are still unreachable; the Karnataka GIS ArcGIS REST server
is reachable but forbids commercial use and exposes no road layer in the
folders checked; two more Kannada publishers were checked (one Quintype feed
found, one with no feed); Deccan Herald still has no Bengaluru feed; two
"current" closures suggested by web search turned out to be 2025 and July
2026 stories once their pages were read.

## 2. Summary table

| Source | Tier | Colour | Access verified (how) | Geometry | Distance | Coordinates | Start/end | Update frequency | Terms (short) | Automation permitted? | Commercial reuse? | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bengaluru Traffic Police website, "Upcoming Events / Press Notes" (btp.karnataka.gov.in) | 1 | **YELLOW, PERMISSION_REQUIRED** | 8 Oct: HTTP 200 ×5 fetches, static HTML, robots allows all; 39 items parsed each time | Named place or "near None" (24 of 39) | None | None | Yes: `Start : HH:MM Hrs DD-MM-YYYY and End : DD-MM-YYYY` | List unchanged across 5 fetches over 33 min and vs 7 Oct (39 vs 40 items); maintained at least weekly | CeG: re-publication "only with prior permission … through email" | robots yes; terms: prior permission | Unknown (not stated); permission needed | Already connected, run by hand; stays discovery-grade until CeG/BTP permission is obtained |
| BTP website, "Traffic Alerts" panel | 1 | **YELLOW, PERMISSION_REQUIRED** | 8 Oct: same page; 4 congestion items with lat/lon + 1–2 breakdown items; changed between fetches | Point | None (map legend defines severity by 250/500/750 m queue) | **Yes**, lat/lon in a Google Maps link | Timestamp only (HH:MM DD-MM-YYYY), no end | Changed at least twice in 33 min; congestion batch timestamped 11:45, breakdowns 12:59 and 13:36 | Same CeG policy | Same | Same | Not read by REI (user's decision); only Tier 1 source with exact coordinates |
| BTP ASTraM (Congestion map, Incident Management, "Map Engine & API") | 1 | **RED, PERMISSION_REQUIRED** | 8 Oct: description page only (3.5 MB of inline images); congestion map = Power BI iframe; Incident Management page says "Content Updating Soon"; no registration/documentation page found | — | — | — | — | — | None published | No public interface | — | Nothing public to automate; the "map service providers" API would need an agreement with BTP |
| Karnataka State Police (ksp.karnataka.gov.in) | 1 | RED | 8 Oct: HTTP 200; robots.txt returns HTML (unparseable, nothing to honour); home links are circulars (noise, hit-and-run scheme, legal bulletins) and the dead `bangaloretrafficpolice.gov.in` | — | — | — | — | — | Not read | — | — | No traffic advisories or press releases found on 7 or 8 Oct |
| BBMP (bbmp.gov.in, updates.bbmpgov.in, site.bbmp.gov.in "Fix My Street", api.bbmpgov.in) | 1 | **RED (not verifiable)** | 8 Oct: ConnectTimeout on three hosts, DNS failure on the API host; 7 Oct identical from two network paths | ? | ? | ? | ? | ? | Not readable | Unknown | Unknown | Could not be verified on two days; re-test from another network |
| Greater Bengaluru Authority (gba.karnataka.gov.in) | 1 | **RED today** (policy would allow) | 8 Oct: 666-byte React shell (Last-Modified 3 Oct 2026); bundle's API base `api.bbmpgov.in/gba/v1` does not resolve; notices at `updates.bbmpgov.in/public` unreachable | — | — | — | — | — | "may be reproduced free of charge … source must be prominently acknowledged" | Would be, if content were reachable | Yes per policy | Nothing readable by a plain client; the most promising civic source *if* its hosts return |
| data.gov.in (incl. api.data.gov.in) | 1 | **RED (not verifiable)** | 8 Oct: HTTP 403 "Access Denied" on `/` and `/catalogs` (robots.txt itself 403); API host refuses the connection. Same on 7 Oct | — | — | — | — | — | Not readable | — | — | Blocked for automated clients from this environment |
| Karnataka GIS, KSRSAC (kgis.ksrsac.in; ArcGIS REST `/kgismaps/rest/services`) | 1 | **RED for REI (commercial use forbidden)** | 8 Oct: portal `/kgis/` HTTP 200; REST root JSON lists 49 folders; folders Base_Layer (empty), State_Basemap (3 basemap MapServers), Urban (Mangaluru only), CITYGIS (BDA plans, ESCOM, KHB…), BMRCL (`Metro_BH`); robots.txt 404; host root `/` 403 | Unknown (no road layer verified) | — | — | — | Unknown | "Under no circumstances data will be used for any commercial purposes by anyone"; disclaimer: "shall not be used for any legal purpose … representational maps" | Technically readable; licence forbids commercial use | **No** | Do not use for a commercial product; no road layer found anyway |
| Karnataka PWD (kpwd.karnataka.gov.in) | 1 | RED | 7 Oct: live; statutory notifications; newest circular PDF is a scanned image | — | — | — | — | — | — | — | — | Not road events (7 Oct finding, not re-fetched) |
| KRDCL (krdcl.in), BDA (bdakarnataka.in) | 1 | RED | 7 Oct: KRDCL last press item May 2019; BDA empty JS shell | — | — | — | — | — | — | — | — | Not usable (7 Oct finding, not re-fetched) |
| BMRCL / Namma Metro (english.bmrc.co.in) | 2 | RED today | 8 Oct: HTTP 200 but the English host serves Kannada; `/news/` renders "No Data Found"; copyright page is the CeG text in Kannada (prior authorisation required); robots.txt 404 | — | — | — | — | — | Kannada CeG policy: republication needs prior authorisation | No content to automate | Permission needed | No traffic-impacting notices published; metro projects are not events |
| The Hindu Bengaluru RSS | 4 | **BLUE** (connected) | 8 Oct: 200; 60 items / 5 days; description on 44, no body; robots allows the path | Named places in text | Sometimes in text | None | In text | ~12 items/day | "personal use … not for commercial purposes" (7 Oct) | Feed is public; terms personal | No | Discovery-only, as connected |
| Indian Express Bangalore RSS | 4 | **RED (terms)** | 8 Oct: 200; 200 items / 34 days; description and body empty on all 200 | Named places (titles only) | — | None | — | ~6 items/day | Prohibits "automated tools, bots, crawlers, scrapers" and AI summarisation (7 Oct) | **No** by terms | No | Do not automate; article pages hold the text (JSON-LD) |
| Times of India Bengaluru RSS | 4 | BLUE, PERMISSION_REQUIRED | 8 Oct: 200; 20-item rolling window (today 12:56 back to ~24 h), 7 with abstracts | Named places | Sometimes | None | In text | ~20/day | RSS "for personal, non-commercial use", link-back required (7 Oct) | Feed public; non-commercial | No | Discovery-only; link-back condition |
| Bangalore Mirror RSS | 4 | BLUE, PERMISSION_REQUIRED | 8 Oct: 200; 15 items (print batch 00:30 UTC), abstracts on all | Named places | None seen | None | None seen | 15/day | Times Internet group terms; BM-specific RSS terms not found | Feed public | No | Discovery-only, abstracts only |
| TV9 Kannada Bengaluru RSS | 4 | BLUE, PERMISSION_REQUIRED | 8 Oct: 200; 60 items / 50 h, full Kannada body on all 60; robots allows | Named places (Kannada) | None structured | None | In text (Kannada dates) | ~29/day | Terms forbid "unauthorized spidering, scraping, or harvesting of content" and commercial use without consent (8 Oct) | Feed public; automated harvesting restricted | No | Discovery-only; needs Kannada rules |
| The New Indian Express (`stories.rss?section=bengaluru`) | 4 | BLUE, PERMISSION_REQUIRED (unproven) | 8 Oct: 200 but **0 items** (channel only; 1 item on 7 Oct); site-wide `stories.rss` not re-fetched | — | — | — | — | Unproven | Not extractable (client-rendered page, 7 Oct) | Unknown | Unknown | Not usable until the section filter proves to carry items |
| Deccan Herald | 4 | **RED (terms; no feed)** | 8 Oct: section page has **no** `<link rel="alternate">`; site-wide `stories.rss` 35 items / 28 h with full bodies, 2 Bengaluru; robots `*` group allows (blocks named AI crawlers) | Named places | Sometimes | None | In text | — | "Automated extraction, redistribution, framing, scraping, or republication of content is not permitted" (7 Oct) | **No** by terms | No | No Bengaluru feed; terms forbid automation |
| Prajavani (Kannada; `stories.rss?section=bengaluru-city`) | 4 | **RED (terms)** | 8 Oct: 200; Quintype feed found, 5 items today with full Kannada bodies; `news_sitemap.xml` lists 1,000 URLs / ~32 h | Named places (Kannada) | In text | None | In text | 5 in the feed window | "Use of content for data scraping, training artificial intelligence models, or automated text extraction is strictly prohibited unless expressly licensed"; "up to five (5) article summaries per day … up to 20 words" | **No** by terms | No | Do not automate |
| Vijaya Karnataka (Kannada; `sitemap/rssfeed.xml`) | 4 | **RED (terms)** | 8 Oct: 200; site-wide feed of 34 items (17 Aug–8 Oct), Kannada abstracts; no Bengaluru feed found | Named places (Kannada) | — | None | In text | Unknown | Times Internet: "personal and non-commercial use only"; forbids "any data gathering or extraction tools" | **No** by terms | No | Do not automate |
| Udayavani (Kannada) | 4 | RED (no feed) | 8 Oct: home 200; no RSS link; robots points to monthly sitemaps (`kan/10-2026.xml`); terms page not found | — | — | — | — | — | Not verified | — | — | Nothing to connect |
| Citizen Matters (`/feed/`) | 4 | BLUE, PERMISSION_REQUIRED | 8 Oct: 200; WordPress site-wide feed, 10 items / 17 days (Bengaluru, Chennai, Delhi, Pune), descriptions only | Named places | — | None | In text | ~4/week | "print or download extracts … for non-commercial and / or personal use only" | Feed public; non-commercial | No | Low volume; discovery-only at best |

## 3. Sources, one section each

### 3.1 Bengaluru Traffic Police website: "Upcoming Events / Press Notes"

- **Source name:** Bengaluru Traffic Police website, home-page "UPCOMING EVENTS /
  PRESS NOTES" panel. **Official URL:** https://btp.karnataka.gov.in/en (Kannada
  default at `/`; widget text is English on both). **City:** Bengaluru.
  **Authority:** Bengaluru Traffic Police, Karnataka State Police; site built
  and hosted by the Centre for e-Governance (CeG), Government of Karnataka.
- **Source type:** HTML (server-rendered list; no RSS, no API, no PDFs, no item
  pages, no ids). `/sitemap/en` (8 Oct) lists only navigation pages: no
  advisory, notification, press-release or circular page exists on the site.
- **Event categories:** "Department Work" (white-topping, night works, tunnel
  soil testing, junction works), "Public Event" (early-morning entries at NICE
  Road toll plaza, Decathlon Sarjapur Road, Freedom Park: type not stated),
  "Private Event" (exhibition centres, malls, Palace Grounds).
- **Geometry availability:** none. A "near <address>" string on 15 of 39 items;
  "near None" on 24. **Distance:** none. **Coordinates:** none.
- **Start/end availability:** yes, structured: `Start : 10:30 Hrs 08-10-2026 and
  End : 08-10-2026` (end has no time). Start dates seen 02-07-2026 to
  17-11-2026, end dates to 02-09-2027.
- **Update frequency:** 39 unique items on every fetch on 8 Oct (13:57, 14:03,
  14:07, 14:18, 17:31); 40 on 7 Oct (the "Freedom Park 08-10-2026"
  entry appears on both days; one 7 Oct item ended). The list is maintained at
  least weekly (newest start date 08-10-2026); its refresh time is unknown.
- **Terms / licensing (verbatim, footer modal, fetched 8 Oct 13:57):**
  > Copyright policy (if the published information is available free of any charge)
  > 1)Information featured on this website can be re-published in any media form free of any charge only with prior permission from us(CeG) or concerned respective authority which is owning the website, through email.
  > 2)Information can be republished as it is available and not to be used in a distorted or misleading manner.
  > 3)Where the material is being published or suggested to others, the source must be prominently acknowledged
  > 4)13. However, the permission to reproduce this material does not extend to any material on this site, which is explicitly identified as being the copyright of a third party
  > Copyright policy (if there is a provision to reuse published information)
  > 1)The information published on the website comes under copyright policy and obtaining authorization for their republish is a pre-requisite.
  > 2)To get permission one can mail to ……..@.........

  > Hyperlinking Policy … 1)We do not object to you linking directly to the information that is hosted on our site and no prior permission is required for the same. 2)we do not permit our pages to be loaded into frames on other sites. Our Department's pages must load into a newly opened browser window of the user. (in case of hyperlink permission is necessary for the website) 1)to provide any link or its form on this website, it is compulsory to procure permission. 2)permission can be obtained from the Centre for e-governance by requesting to this email. pd.webportal@karnataka.gov.in

  Footer: "Content Owned and maintained by: Bengaluru Traffic Police, Karnataka
  State Police, Govt. of Karnataka. Designed, Developed & Hosted by: Centre for
  e-governance … Version: CeG/KRN 4.0". The permission e-mail in the copyright
  modal is a blank template ("……..@........."); the only address given is the
  hyperlinking one, `pd.webportal@karnataka.gov.in`.
- **robots.txt (8 Oct):** `User-agent: *` / `Disallow:` (everything allowed).
  Response header `Cache-Control: no-store, max-age=0, no-cache`.
- **Automation permission:** technically unrestricted (robots, no rate limit
  published, 215 KB per fetch); legally, re-publication needs prior written
  permission. **Commercial-use suitability:** not stated; permission needed.
- **Classification:** YELLOW, PERMISSION_REQUIRED. Tier 1.
- **Connector recommendation:** keep the existing HTML connector as built
  (poll at most every 6 h; the page is `no-store`, so each run is one fresh
  request). Do not schedule until permission is on file. Nothing more can be
  extracted: no item has a link, id, PDF or coordinates.
- **Sample events (real, 8 Oct 2026, https://btp.karnataka.gov.in/en):**
  - "Department Work : White Topping Work at New Diagonal Road, Jayanagar. near
    7th Main Road, Byrasandra, Bengaluru South City Corporation, Bengaluru,
    Bengaluru Urban, Karnataka, 560011, India | Start : 00:00 Hrs 07-10-2026 and
    End : 04-01-2027"
  - "Department Work : 5TH MAIN CHAMARAJPET. White Topping Work near Puttanna
    Chetty Road, Chamarajapete, Bengaluru Central City Corporation, Bengaluru,
    Bengaluru Urban, Karnataka, 560018, India | Start : 00:00 Hrs 27-07-2026 and
    End : 26-10-2026"
  - "Department Work : Soil Testing of Twin Tunnel Project near , Hebbal,
    Bengaluru North City Corporation, Bengaluru, Bengaluru Urban, Karnataka,
    560024, India | Start : 10:30 Hrs 20-08-2026 and End : 31-01-2027"
  - "Department Work : Shivananda Junction near None | Start : 00:00 Hrs
    05-10-2026 and End : 20-10-2026"
  - "Public Event : Freedom Park, Bengaluru near Kalidasa Road, Gandhinagar,
    Bengaluru Central City Corporation, Bengaluru, Bengaluru Urban, Karnataka,
    560009, India | Start : 10:30 Hrs 08-10-2026 and End : 08-10-2026"
  - "Public Event : Decathlon Sarjapur Road, Outer Ring Road Corridor, Bengaluru
    near None | Start : 06:00 Hrs 10-10-2026 and End : 10-10-2026"
  - "Public Event : NICE Road Toll Plaza, Behind PES University Campus,
    Hosakerehalli, Bengaluru near None | Start : 05:30 Hrs 11-10-2026 and End :
    11-10-2026"
  - "Department Work : The work shout be carried out Only 11:0PM to 5:00AM. near
    , Channasandra, Bengaluru East City Corporation, Bengaluru, Bengaluru Urban,
    Karnataka, 560066, India | Start : 00:00 Hrs 28-08-2026 and End : 28-12-2026"
  - "Department Work : None near None | Start : 00:00 Hrs 25-09-2026 and End :
    22-02-2027" (one of 13 such lines: the no-location, no-description case)

### 3.2 Bengaluru Traffic Police website: "Traffic Alerts" panel (not connected)

- **Source name / URL / city / authority:** as 3.1; the "TRAFFIC ALERTS" panel
  on the same page (card plus "View All" dialog; items repeated).
- **Source type:** HTML. Each item is `<kind> <reported near|occurred at>
  <place> | HH:MM Hrs DD-MM-YYYY`; congestion items carry a link
  `https://maps.google.com/?q=<lat>,<lon>&z=13`; breakdown items carry none.
- **Event categories:** "Severe Congestion reported near …", "Vehicle Breakdown
  occurred at …" (8 Oct); 7 Oct also showed "construction occurred at" (per
  the source page). Transient, operational.
- **Geometry:** point. **Distance:** none in the item (the Power BI map legend
  defines severity by queue length 250/500/750 m; not readable by a plain
  client). **Coordinates:** yes, decimal lat/lon to 15 places (ASTraM output).
  **Start/end:** a single timestamp; no end.
- **Update frequency (8 Oct, verified):** see §4. The congestion set is a batch
  with one timestamp (11:45 on 8 Oct; 11:30/11:45 on 7 Oct), still displayed
  two and a half hours later; breakdown items appeared and disappeared within
  the half hour. The ASTraM page's "every 15 minutes" refers to alerts to
  officers, not to this panel.
- **Terms, robots, automation, commercial:** as 3.1 (YELLOW, PERMISSION_REQUIRED).
- **Connector recommendation:** if the user decides REI should carry transient
  alerts, the same connector can read this panel (parse the Google Maps link
  for the point; keep the timestamp as "reported at"; expire on absence, since
  the source never states an end). Not recommended before that decision.
- **Sample events (real, 8 Oct 2026, 13:57 fetch):**
  - "Severe Congestion reported near Bangalore East, Varthur, Gandhi Circle |
    11:45 Hrs 08-10-2026" → 12.939121091628252, 77.74673450085938
  - "Severe Congestion reported near Chikka Banaswadi Road, Bangalore East,
    Subbayanapalya, Doctors Layout | 11:45 Hrs 08-10-2026" → 13.006030346289963,
    77.64172066083252
  - "Severe Congestion reported near Dr. CV Raman Road, Bangalore North,
    Sadashivanagar, Achaiah Chetty Layout | 11:45 Hrs 08-10-2026" →
    13.014686731111823, 77.58309829792725
  - "Severe Congestion reported near Service Road, Bangalore East, Munnenkolalu,
    MSR Layout | 11:45 Hrs 08-10-2026" → 12.951457485456505, 77.6999996983081
  - "Vehicle Breakdown occurred at Seshadri Road, Gandhi Nagar 1 | 12:59 Hrs
    08-10-2026" (13:57 fetch only; gone by 14:03)
  - "Vehicle Breakdown occurred at 7th Main Road, Block 3 | 13:36 Hrs
    08-10-2026" (13:57, 14:03, 14:07 fetches)
  - 7 Oct for comparison: "Severe Congestion reported near Sarjapur Road,
    Bangalore South, HSR Layout | 11:45 Hrs 07-10-2026" (12.924652, 77.648630).

### 3.3 BTP ASTraM (Actionable Intelligence for Sustainable Traffic Management)

- **Official URL:** https://btp.karnataka.gov.in/209/astram/en (8 Oct: 200,
  3.5 MB, almost all inline images); congestion map
  https://btp.karnataka.gov.in/188/congestion-map/en (8 Oct: a Power BI
  `app.powerbi.com/view?r=…` iframe, needs a browser); Incident Management
  https://btp.karnataka.gov.in/155/incident-management/en (8 Oct: "Content
  Updating Soon"); Traffic Management Centre https://btp.karnataka.gov.in/tmc/en
  (descriptive). **City/authority:** Bengaluru / BTP. **Source type:** none
  public (HTML description only).
- **What the page says (verbatim, 8 Oct):** "Module 1: Congestion Monitoring &
  Prediction. This initiative intends to provide real-time alerts on congestion
  to the jurisdictional traffic officials every 15 minutes." "Module-2: Incident
  Reporting & Map Engine & API. The purpose of this BOT service is to report any
  field incident from the authorized sources so that corresponding information
  is shared with the map services, which provides public with real-time
  information. … This information is made available for map service providers
  to consume and provide reliable real time information to road users."
  "Module-4 : Event Calendar with Simulation Tool …".
- **Findings:** no registration page, documentation, developer portal, feed or
  public endpoint exists on the site (sitemap read in full) or was found by web
  search (8 Oct); press coverage says ASTraM combines Google, Bing and TomTom
  data and was built with Arcadis, which is not a public interface. The citizen
  features are in the mobile app, which was not examined (rule). The only
  machine-readable ASTraM output is the home-page alerts panel (3.2).
- **Geometry / distance / coordinates / start-end / frequency:** not applicable
  (nothing public). **Terms:** none published for an API. **Automation:** no.
  **Commercial:** unknown.
- **Classification:** RED, PERMISSION_REQUIRED (an agreement with BTP as a "map
  service provider" would be the route). Tier 1.
- **Connector recommendation:** none. Open question for the user: whether JSAN
  wants to approach BTP about the map-provider API.
- **Sample events:** none (nothing public).

### 3.4 Karnataka State Police (ksp.karnataka.gov.in)

- **URL:** https://ksp.karnataka.gov.in/ (8 Oct: 200, 303 KB). **Tier 1.**
  **Source type:** HTML + PDFs.
- **Findings (8 Oct):** `robots.txt` returns an HTML page (status 200), so no
  robots rules could be read; home-page links are HR/legal circulars
  (`Circular-1_NoisePullution.pdf`, "Hit and Run Motor Accident Compensation
  Scheme, 2022", four "Legal Bulletin" PDFs, "LICENCE ISSUED 2013.pdf"), the
  circulars listing `/info-4/Circular/kn` (7 Oct: medals, commendations), a
  "Traffic" FAQ page and the dead `www.bangaloretrafficpolice.gov.in`. A web
  search restricted to the host returned no traffic advisory or press release
  page (8 Oct). No BTP advisory archive exists here.
- **Geometry / distance / coordinates / dates / frequency:** none for road
  events. **Terms:** not read (no road content to licence). **Automation:**
  nothing to automate. **Classification:** RED. **Connector:** none.
  **Sample events:** none.

### 3.5 BBMP: bbmp.gov.in, updates.bbmpgov.in, site.bbmp.gov.in (Fix My Street), api.bbmpgov.in

- **Tier 1** (the former municipal corporation; since 2025 the Greater
  Bengaluru Authority and five city corporations).
- **Access (8 Oct 13:59–14:05):** `https://bbmp.gov.in/` ConnectTimeout;
  `https://updates.bbmpgov.in/` ConnectTimeout;
  `https://site.bbmp.gov.in/departmentwebsites/BBMPIT/fms.html` (the "Fix My
  Street" page named by web search) ConnectTimeout; `https://api.bbmpgov.in/`
  DNS failure (`getaddrinfo failed`). **7 Oct:** timed out (httpx) and refused
  (second network path). Nothing about content, format, terms, geometry or
  frequency can be stated. The GBA bundle (3.6) references
  `https://updates.bbmpgov.in/public` and a file route
  `updates.bbmpgov.in/v1/api/file/…-openhousevenues.pdf`, which were **not**
  called (bundle-only routes).
- **Web search (8 Oct, not verified by fetch):** BBMP's pothole tools are the
  "Fix My Street" app (2017; relaunched December 2024), "Sahaaya 2.0 / Namma
  Bengaluru" grievance app, and a "pothole dashboard"; all are described as
  apps/dashboards, none as open data. Indian Express (9 Sep 2026, feed title
  only): "New platforms for grievance redressal, transparent roadworks in
  Bengaluru".
- **Classification:** RED (not verifiable). **Connector:** none until a host
  answers. **Sample events:** none.

### 3.6 Greater Bengaluru Authority (gba.karnataka.gov.in)

- **URL:** https://gba.karnataka.gov.in/ **Tier 1.** **Source type:** React
  single-page app; content comes from an API.
- **Access (8 Oct):** the host fails TLS validation on this machine
  (`CERTIFICATE_VERIFY_FAILED`, the known local CA problem; 7 Oct too). With
  verification off, `/` is a 666-byte shell ("You need to enable JavaScript to
  run this app", Last-Modified Sat 3 Oct 2026) and the public bundle
  `/static/js/main.2c80bd9f.js` (587 KB) names `api.bbmpgov.in/gba/v1` (DNS
  failure) and `updates.bbmpgov.in/public` (timeout). Nothing else was called.
- **Terms (verbatim, from the public bundle, 8 Oct):** "Material featured on
  this site may be reproduced free of charge in any format or media without
  requiring specific permission. This is subject to the material being
  reproduced accurately and not being used in a derogatory manner or in a
  misleading context. Where the material is being published or issued to
  others, the source must be prominently acknowledged. However, the permission
  to reproduce this material does not extend to any material on this site,
  which is explicitly identified as being the copyright of a third party.
  Authorisation to reproduce such material must be obtained from the copyright
  holders concerned."
- **Geometry / distance / coordinates / dates / frequency:** unknown (no
  content reachable). **Automation:** would be permitted by the policy;
  technically impossible today. **Commercial:** permitted by the policy
  ("free of charge in any format or media"), with acknowledgement.
- **Classification:** RED today; the best-licensed civic source if its backend
  returns. **Connector:** none now; re-test `updates.bbmpgov.in` and the GBA
  API host on another network, then evaluate. **Sample events:** none.

### 3.7 data.gov.in (Open Government Data platform, Karnataka datasets)

- **URLs:** https://data.gov.in/ → 301 → https://www.data.gov.in/ (8 Oct: HTTP
  403 "Access Denied", 371 B; `/robots.txt` 403; `/catalogs` 403);
  https://api.data.gov.in/ (8 Oct: connection refused). 7 Oct: 403 (Akamai)
  from two networks. **Tier 1.**
- Nothing about Karnataka transport, traffic, road, accident or GIS datasets,
  their licence (normally the Government Open Data License – India) or their
  update dates could be verified. **Classification:** RED (not verifiable).
  **Connector:** none. **Sample events:** none.

### 3.8 Karnataka GIS (KSRSAC; kgis.ksrsac.in)

- **URLs:** portal https://kgis.ksrsac.in/kgis/ (8 Oct: 200, ASP.NET page, 417
  KB; host root `/` is 403; `robots.txt` 404); ArcGIS REST
  https://kgis.ksrsac.in/kgismaps/rest/services?f=json (8 Oct: 200, ArcGIS
  Server 11.5). **Tier 1** (state GIS agency). **Source type:** ArcGIS REST
  (MapServer) + portal apps.
- **What was found (8 Oct):** the REST root lists 49 folders (Agriculture …
  Base_Layer, BMRCL, Boundaries, BWSSB, CITYGIS, DULT, State_Basemap, Urban,
  Utilities, WR …) and one root service (`SampleWorldCities`). Folder
  listings fetched: `Base_Layer` → empty; `State_Basemap` →
  `State_Basemap_Cached`, `State_Basemap_Dynamic`, `State_Basemap`
  (MapServers); `Urban` → Mangaluru e-khata and land parcels only; `CITYGIS` →
  `BDA_Plans`, `Escom`, `KHB`, `MRC_Property`, `RGRHCL`; `BMRCL` → `Metro_BH`.
  **No road-network layer was verified** (the basemap MapServers were not
  opened to list their layers: 3 more requests would tell, but the licence
  below makes it moot). Portal links include `bbmpgis`, `bgis` (Bengaluru GIS),
  `karnatakagis`, `kag2024` (Karnataka Atlas), `downloads.aspx`, not opened.
- **Terms (verbatim, portal footer modals, 8 Oct):** Copyright Policy:
  "1.Karnataka State Remote Sensing Applications Centre has built this
  Application as a free application for users. This Application is provided by
  Karnataka State Remote Sensing Applications Centre at no cost and is intended
  for use as is. **Under no circumstances data will be used for any commercial
  purposes by anyone.**" Disclaimer: "The geospatial data available in KSRSAC
  Website shall not be used for any legal purpose. They are just
  representational maps and information which are to be validated for its
  accuracy and correctness. Hence, the derived information / data from the
  KSRSAC Website needs to be revalidated with the respective agencies / KSRSAC."
  Terms and Conditions: "… the same should not be construed as a statement of
  law or used for any legal purposes."
- **Geometry:** unknown for roads. **Distance / coordinates / start-end:** not
  applicable (reference data, not events). **Update frequency:** not stated.
- **Automation permission:** technically open REST; legally restricted to
  non-commercial use. **Commercial-use suitability:** **no**.
- **Classification:** RED for REI (commercial). Tier 1. **Connector:** none.
  **Sample events:** none (not an event source).

### 3.9 Karnataka PWD, KRDCL, BDA, Bengaluru Smart City (7 Oct findings)

Not re-fetched on 8 Oct; recorded as found on 7 Oct. **KPWD**
(kpwd.karnataka.gov.in): live; notifications are statutory (road
classification, pipelines on PWD roads, roadside margins); newest circular PDF
(18-03-2026) is a scanned image (`pdftotext` extracted 2 characters). **KRDCL**
(krdcl.in, http only): last press item May 2019. **BDA** (bdakarnataka.in):
empty JavaScript shell whose bundle exposes only admin/authentication routes;
old domain has a certificate mismatch. **Bengaluru Smart City Ltd:** no
official site found (three domains fail DNS). All RED; no connector; no sample
events.

### 3.10 BMRCL / Namma Metro (english.bmrc.co.in; Kannada site)

- **URLs:** https://english.bmrc.co.in/ (8 Oct: 200, 52 KB, Next.js; **the
  English host served Kannada text** on every page read: nav "ಮುಖಪುಟ / ಮೆಟ್ರೋ
  ಬಗ್ಗೆ / ವಾರ್ತೆಗಳು …"); `/news/` (8 Oct: 200, table "ಮೆಟ್ರೋ ಸುದ್ದಿ … No Data
  Found"); `/copyright-policy/` and `/terms-conditions/` (8 Oct: 200);
  `robots.txt` 404 (nothing to honour). A separate Kannada host was not
  identified; the English host already serves Kannada. **Tier 2** (operator).
  **Source type:** HTML (client-side app with a backend; 7 Oct: content loaded
  from a raw-IP backend, not called).
- **Traffic-impacting content:** none published. No diversion, station
  construction or road-closure notice exists on the site; the only PDF linked
  from the home page is a fare "Media Brief" on a non-standard port
  (`english.bmrc.co.in:8282/…/Media Brief -English- Fin 08.02.2025 (1).pdf`,
  not fetched). Metro construction impacts reach the public through BTP
  advisories (on X) and the press, e.g. The Hindu 7 Oct "BMRCL, BMTC add new bus
  stops near two metro stations" (not a road event).
- **Terms (Kannada, verbatim, 8 Oct, `/copyright-policy/`):** "ಕೃತಿಸ್ವಾಮ್ಯ
  ನೀತಿ (ಪ್ರಕಟಿತ ಮಾಹಿತಿಯನ್ನು ಮರುಬಳಕೆ ಮಾಡಲು ಅವಕಾಶವಿದ್ದರೆ) ವೆಬ್‌ಸೈಟ್‌ನಲ್ಲಿ ಪ್ರಕಟವಾದ
  ಮಾಹಿತಿಯು ಹಕ್ಕುಸ್ವಾಮ್ಯ ನೀತಿಯ ಅಡಿಯಲ್ಲಿ ಬರುತ್ತದೆ ಮತ್ತು ಅವುಗಳ ಮರುಪ್ರಕಟಕ್ಕಾಗಿ
  ಅಧಿಕೃತತೆಯನ್ನು ಪಡೆಯುವುದು ಪೂರ್ವ ಅವಶ್ಯಕವಾಗಿದೆ. ಅನುಮತಿ ಪಡೆಯಲು ಒಬ್ಬರು ……………… ..
  @ ........." [gloss: the published information is under the copyright policy
  and obtaining authorisation for republication is a prerequisite; the
  permission e-mail is a blank template], i.e. the CeG template in Kannada,
  with "3. … ಮೂಲವನ್ನು ಪ್ರಮುಖವಾಗಿ ಅಂಗೀಕರಿಸಬೇಕು" [the source must be prominently
  acknowledged].
- **Geometry / distance / coordinates / dates / frequency:** none (no
  notices). **Automation:** nothing to automate. **Commercial:** permission
  needed. **Classification:** RED today, Tier 2. **Connector:** none. Do not
  count metro projects as events. **Sample events:** none.

### 3.11 The Hindu, Bengaluru (connected, discovery-only)

- **Feed URL (verified 8 Oct 14:02):**
  https://www.thehindu.com/news/cities/bangalore/feeder/default.rss → 200,
  `application/xml`, 47.9 KB, Last-Modified 08 Oct 2026 06:38 GMT. **Tier 4.**
- **Items / window:** 60 items, 3 Oct 14:59 → 8 Oct 06:51 IST (about 12 a
  day). **Body present:** one-line `description` on 44 of 60; no
  `content:encoded`. **Language:** English (0 Kannada characters).
- **robots.txt (8 Oct):** `*` group disallows `/cgi-bin/`, `/search/`,
  `/todays-paper/*article*`, `/news-service/*` and similar; the feed path and
  article paths are allowed. **Terms (7 Oct, quoted then):** "limited licence
  to access and make personal use … but not for commercial purposes".
- **Geometry:** named places in text; **distance:** sometimes ("2.56-km
  stretch", 5 Oct); **coordinates:** none; **start/end:** in text ("60 days
  starting Monday (October 5)").
- **Classification:** BLUE (connected on the generic RSS connector). Automation:
  the feed is public; the licence is personal, non-commercial. Commercial reuse:
  no.
- **Sample events (read 8 Oct):** "Heavy rain leaves Bengaluru roads, underpasses
  waterlogged" (6 Oct 19:35; description: "Traffic police officials said most
  instances of waterlogging were cleared overnight …"); "Chandapura sees
  hours-long traffic jam as weekend return rush peaks" (5 Oct 22:31); "White
  topping work on Race Course Road, traffic diversions for 60 days" (5 Oct
  20:22); "Sanjaynagar Main Road work near completion, footpath woes persist"
  (5 Oct 16:40, "scheduled to be completed by November-end, according to sources
  in the Greater Bengaluru Authority"); "BMRCL, BMTC add new bus stops near two
  metro stations" (7 Oct, not a road event).

### 3.12 The Indian Express, Bangalore

- **Feed URL (8 Oct 14:02):** https://indianexpress.com/section/cities/bangalore/feed/
  → 200, 208 KB, 200 items, 4 Sep 06:18 → 8 Oct 05:35 UTC. **Body:**
  `description` and `content:encoded` **empty on all 200** (titles, links,
  dates only). **Language:** English. **robots.txt:** `*` allows `/` (specific
  disallows unrelated). **Tier 4.**
- **Terms (7 Oct, quoted then):** prohibits "automated tools, bots, crawlers,
  scrapers" and "Use the content for AI training, summarization, and/or
  commercial purposes".
- **Geometry:** named places (article text; JSON-LD `articleBody` on article
  pages, verified 8 Oct on the Race Course Road article); **distance:**
  sometimes ("150-m wall", 1 Oct); **coordinates:** none; **start/end:** in
  text.
- **Classification:** RED for automation (the terms forbid it); titles only in
  the feed. Commercial reuse: no. **Connector:** none (do not connect; a
  reviewer may read articles by hand).
- **Sample events (read 8 Oct):** "Bengaluru's Race Course Road closed for 60
  days. Check alternate routes" (6 Oct 13:33 IST; article: "the Greater
  Bengaluru Authority began white-topping work on Race Course Road from Maurya
  Junction to Hare Krishna Road Junction on October 5. They said in a press
  release Sunday … 'The movement of all vehicles on Race Course Road, from
  Trilight Junction to Maurya Junction and from Shivananda Junction to Maurya
  Junction, will be restricted,' a traffic police officer said … expected to run
  until December"); "Two-wheelers banned on Bengaluru airport road; traffic curbs
  on 3 flyovers" (4 Sep) and "No 2-wheeler ban on Bengaluru airport, Electronics
  City flyovers for now" (9 Sep); "Bengaluru rain: 150-m wall collapses after
  drain blocked, triggers flooding" (1 Oct).

### 3.13 The Times of India, Bengaluru

- **Feed URL (8 Oct 14:02):** https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms
  → 200, 23 KB, 20 items (rolling), newest 8 Oct 12:56 IST; ISO dates;
  abstracts on 7 of 20; no body. **Language:** English. **robots.txt:** `*`
  allows `/`; disallows `/feeds/`, `/rssarticleshow`, `/topic/…` (the feed
  path `/rssfeeds/` and `/city/…/articleshow/` are allowed). **Tier 4.**
- **Terms (7 Oct, quoted then):** RSS "for personal, non-commercial use"; "a
  functional link … to the display of the full article" required.
- **Geometry:** named places; **distance:** sometimes ("less-than-one-kilometre
  stretch", 7 Oct); **coordinates:** none; **start/end:** in text.
- **Classification:** BLUE, PERMISSION_REQUIRED (link-back condition;
  non-commercial). **Connector:** generic RSS connector fits; not connected.
- **Sample events (read 8 Oct):** "Panel formed to oversee Bengaluru's Varthur
  road works" (7 Oct 22:48; article: "ordered immediate filling of potholes,
  removal of construction debris and silt, and repairs to damaged footpaths,
  drains and slabs along ITPL Main Road and at Kundalahalli Colony"); "Bengaluru
  traffic claims life: Man dies of heart attack on flyover next to hospital"
  (7 Oct 22:19; article: "As they approached Chandapura on NH-44, they took the
  flyover … The National Highways Authority of India (NHAI) has attributed a
  significant part of the recent congestion to the railway overbridge (ROB)
  being co[nstructed]"); "AI survey finds 14k potholes on Bengaluru North
  corporation roads" (7 Oct, a statistic, not an event).

### 3.14 Bangalore Mirror

- **Feed URL (8 Oct 14:02):** https://bangaloremirror.indiatimes.com/rssfeed.cms
  → 200, 15.6 KB, 15 items (print batch, all dated 00:30 GMT 7 and 8 Oct),
  abstracts on all 15, no body. **Language:** English. **robots.txt:**
  `User-agent: *` / `Allow: /`. **Tier 4.**
- **Terms:** Times Internet group (the Vijaya Karnataka page quoted in 3.19 is
  the same TIL text); no Bangalore Mirror–specific RSS terms were found (7 and
  8 Oct). **Geometry:** named places; distance/coordinates/dates: none seen.
- **Classification:** BLUE, PERMISSION_REQUIRED. **Connector:** generic RSS
  connector fits; abstracts only; article bodies are not in the HTML (7 Oct).
- **Sample events (read 8 Oct):** "Sarjapur's junctions at a crossroads of
  safety" (7 Oct; "Residents demand urgent upgrades at key intersections …");
  "Fall by the wayside" (7 Oct; tree falls "leading to severe consequences like
  road blockages", no location). Nothing current with a road measure.

### 3.15 TV9 Kannada, Bengaluru

- **Feed URL (8 Oct 14:02):** https://tv9kannada.com/karnataka/bengaluru/feed →
  200, 493 KB, 60 items, 6 Oct 12:05 → 8 Oct 13:58 IST (about 29 a day); full
  `content:encoded` body on all 60; 64 % of characters are Kannada.
  **robots.txt:** `User-agent: *` / `Allow: /`. **Tier 4.**
- **Terms (verbatim, 8 Oct, https://tv9kannada.com/terms-and-conditions):**
  users agree not to "use the Application and/or Service, without the Companys
  express written consent, for any commercial or unauthorized purpose" and not
  to "engage in unauthorized spidering, scraping, or harvesting of content or
  personal information, or use any other unauthorized automated means to compile
  information".
- **Geometry:** named places in Kannada ("ಚಂದಾಪುರ", "ರಾಷ್ಟ್ರೀಯ ಹೆದ್ದಾರಿ-48");
  **distance:** in text, Kannada ("ಕಿಲೋಮೀಟರ್‌ಗಟ್ಟಲೆ", kilometres-long);
  **coordinates:** none; **start/end:** in text (Kannada dates "ಅಕ್ಟೋಬರ್ 7").
- **What an English-rules detector would miss:** everything not transliterated.
  The 8 Oct road items use ಸಂಚಾರ (traffic), ಟ್ರಾಫಿಕ್ ಜಾಮ್ (traffic jam, loan
  word), ರಸ್ತೆ (road), ಅಂಡರ್‌ಪಾಸ್ (underpass, with a zero-width joiner),
  ಕಾಮಗಾರಿ (works), ಮಳೆ ನೀರು ನಿಂತಿರುವುದು (standing rainwater), ಫ್ಲೈಓವರ್
  (flyover), ಮೆರವಣಿಗೆ (procession), ಪ್ರತಿಭಟನೆ (protest), ಸೇತುವೆ (bridge),
  ಗುಂಡಿ (pothole). Only the English URL slug (e.g.
  `…/chandapura-traffic-jam-…`) and embedded @blrcitytraffic posts (English, seen
  7 Oct) would match English rules. Kannada agglutination means stems must be
  matched as prefixes (ರಸ್ತೆ/ರಸ್ತೆಯಲ್ಲಿ/ರಸ್ತೆಗಳು), and ZWJ/ZWNJ characters must be
  normalised before matching.
- **Classification:** BLUE, PERMISSION_REQUIRED. **Connector:** generic RSS
  connector reads it; detection needs a Kannada rule set (not built).
- **Sample events (read 8 Oct):** "ಚಂದಾಪುರ ರೈಲ್ವೆ ಬ್ರಿಡ್ಜ್ ಬಳಿ ರಸ್ತೆ ಅಸ್ತವ್ಯಸ್ತ …"
  (6 Oct 14:36; body: "ಚಂದಾಪುರ ಬಳಿಯ ರಾಷ್ಟ್ರೀಯ ಹೆದ್ದಾರಿ-48ರಲ್ಲಿ ಮಳೆ ನೀರು
  ನಿಂತಿರುವುದು ಮತ್ತು ಅಂಡರ್‌ಪಾಸ್ ಕಾಮಗಾರಿ ನಡೆಯುತ್ತಿರುವುದರಿಂದ ಭಾರಿ ಟ್ರಾಫಿಕ್ ಜಾಮ್
  ಸಂಭವಿಸಿದೆ" [standing rainwater and underpass works on NH-48 near Chandapura
  have caused a heavy traffic jam]); "ಕರ್ನಾಟಕ ಸಾರಿಗೆ ನೌಕರರಿಂದ ಮತ್ತೆ ಪ್ರತಿಭಟನೆ
  … ಅ. 22 ಡೆಡ್‌ಲೈನ್" (7 Oct; transport workers' protest with a 22 Oct deadline:
  a possible future strike, no road measure); "ಬೆಂಗಳೂರಿನಲ್ಲಿ ಟ್ರಾಫಿಕ್ ರೂಲ್ಸ್
  ಪಾಲನೆಗೆ ವಾಹನ ಸವಾರರು ಅಸಡ್ಡೆ: ಎಂಟೇ ತಿಂಗಳಲ್ಲಿ 24.54 ಲಕ್ಷ ಕೇಸ್" (7 Oct;
  statistics).

### 3.16 The New Indian Express

- **Feed URL (8 Oct 14:02):** https://www.newindianexpress.com/stories.rss?section=bengaluru
  → 200, **815 bytes: a channel with no items** (`sy:updatePeriod hourly`). On
  7 Oct the same URL returned 1 item with full text. The site-wide
  `stories.rss` (7 Oct: full text, same-day items) was not re-fetched.
  **robots.txt:** `*` allows `/`. **Tier 4.**
- **Terms:** not extractable (client-rendered page, 7 Oct); not re-tried.
- **Classification:** BLUE, PERMISSION_REQUIRED, unproven volume. **Connector:**
  the generic RSS connector would work if the filter carried items; a multi-day
  sample is needed first. **Sample events:** none today.

### 3.17 Deccan Herald

- **Checked (8 Oct 14:02):** section page
  https://www.deccanherald.com/india/karnataka/bengaluru → 200, 2.1 MB, **no
  `<link rel="alternate" type="application/rss+xml">` and no feed URL anywhere
  in the HTML**; site-wide https://www.deccanherald.com/stories.rss → 200,
  35 items, 7 Oct 04:27 → 8 Oct 08:09 UTC, full `content:encoded` bodies, **2
  Bengaluru items**. 7 Oct: `?section=` filters returned an empty channel.
  **robots.txt:** no `*` group restrictions beyond named bots (GPTBot,
  ClaudeBot, anthropic-ai, Yandex, SeekportBot disallowed); the research
  client is governed by the `*` group. **Tier 4.**
- **Terms (7 Oct, quoted then):** "Automated extraction, redistribution,
  framing, scraping, or republication of content is not permitted."
- **Classification:** RED (terms forbid automation; no Bengaluru feed).
  **Connector:** none.
- **Sample events (read 8 Oct from `stories.rss`):** "Mass protest erupts at
  Bengaluru's Freedom Park over SIR …" (8 Oct 08:09 UTC; "more than over 2,000
  protesters gathered for a State-level mass demonstration"); "High-end car
  crashes into Attibele petrol bunk in Bengaluru, catches fire" (8 Oct; no road
  closure stated). Two web-search leads were read and rejected as not current:
  "Bengaluru's Panathur Road to reopen today" is dated **17 Nov 2025**, and
  "Service road closure triggers major ORR traffic chaos" is dated **31 Jul
  2026**.

### 3.18 Prajavani (Kannada; The Printers Mysore, same publisher as Deccan Herald)

- **Checked (8 Oct):** home page (5.2 MB) has no feed link; `robots.txt` lists
  `sitemap.xml` and `news_sitemap.xml` and disallows only named AI/search bots;
  `news_sitemap.xml` → 200, 1,000 URLs with `news:publication_date` 7 Oct 06:25
  → 8 Oct 14:00 IST (a `district/bengaluru-city` section exists). Because the
  site runs the same Quintype platform as Deccan Herald, the documented
  Quintype feed `https://www.prajavani.net/stories.rss?section=bengaluru-city`
  was tested once → 200, **5 items today**, full Kannada `content:encoded` on
  all 5 (3 with descriptions), 72 % Kannada. **Tier 4.**
- **Terms (verbatim, 8 Oct, https://www.prajavani.net/terms):** "You may
  download or print extracts from the Website strictly for your personal,
  non-commercial use"; "You shall not reproduce, modify, publish, store,
  distribute, transmit, create derivative works from, or commercially exploit
  any TPML Content without our prior written consent."; "**Use of content for
  data scraping, training artificial intelligence models, or automated text
  extraction is strictly prohibited unless expressly licensed by TPML.**";
  "You may share links and publish up to five (5) article summaries per day …
  Summaries may include either up to 20 words quoted verbatim or 20-word
  non-verbatim abstracts."
- **Geometry:** named places in Kannada; distance in text ("2,493.5 ಕಿ.ಮೀ.");
  coordinates none; dates in text ("ಗುರುವಾರ (ಅ.8) ಬೆಳಿಗ್ಗೆ 10.30").
  **Kannada detection:** same gaps as TV9 (3.15).
- **Classification:** RED (terms forbid automated extraction). **Connector:**
  none.
- **Sample events (read 8 Oct):** "ಸ್ವಾತಂತ್ರ್ಯ ಉದ್ಯಾನದಲ್ಲಿ ಜನತಾ ನ್ಯಾಯಾಲಯ, ಬೃಹತ್
  ಪ್ರತಿಭಟನೆ ಇಂದು" (8 Oct 06:30; "ಗುರುವಾರ (ಅ.8) ಬೆಳಿಗ್ಗೆ 10.30ಕ್ಕೆ ಸ್ವಾತಂತ್ರ್ಯ
  ಉದ್ಯಾನದಲ್ಲಿ" [Thursday 8 Oct, 10:30 a.m., at Freedom Park]: the same event the
  BTP list dates "10:30 Hrs 08-10-2026"); "ಉತ್ತರ ಪಾಲಿಕೆ | ಪ್ರತಿ ಕಿಲೋ ಮೀಟರ್‌ಗೆ 6
  ಗುಂಡಿಗಳು" (8 Oct; 5.8 potholes per km on 2,493.5 km of North corporation
  roads: statistics).

### 3.19 Vijaya Karnataka (Kannada; Times Internet)

- **Checked (8 Oct):** home page declares `<link rel="alternate"
  type="application/rss+xml" href="https://vijaykarnataka.com/sitemap/rssfeed.xml">`
  (and a `langapi/sitemap/gstandrssfeed.xml`). `sitemap/rssfeed.xml` → 200,
  71 KB, 34 items, 17 Aug → 8 Oct 13:59 IST, Kannada abstracts (83 %
  Kannada), no bodies, site-wide (world, astrology, lifestyle); 1 Bengaluru
  road item. No Bengaluru-section feed was found. `robots.txt`: `*` allows `/`
  (disallows `*/xml/`, product pages). **Tier 4.**
- **Terms (verbatim, 8 Oct, https://vijaykarnataka.com/termsandcondition.cms):**
  "a personal, limited, non-exclusive, non-transferable, freely revocable
  license to use the Services for the personal and non-commercial use only";
  "TIL forbids you from any attempts to resell or put to commercial use any
  part of the Site; … any derivative use of the Site or its contents; … or any
  data gathering or extraction tools".
- **Classification:** RED (terms). **Connector:** none.
- **Sample event (read 8 Oct):** "AI survey to assess the condition of
  Bengaluru roads" (`news/bengaluru-city/ai-survey-to-assess-the-condition-of-bengaluru-roads/articleshow/134777726.cms`,
  7 Oct): statistics, not an event.

### 3.20 Udayavani (Kannada)

- **Checked (8 Oct):** https://www.udayavani.com/ → 301 → https://udayavani.com/
  (200, 694 KB); no RSS link in the HTML; `robots.txt` (`*` allows `/`,
  disallows `/search/`, `/tags/`, `/archive/`, `*.json`) names sitemaps
  `sitemap.xml`, `kannada.xml`, `english.xml`; `kannada.xml` → a sitemap index
  of monthly files (`kan/10-2026.xml` …), not a feed. No terms page link was
  found in the home HTML. **Tier 4.**
- **Classification:** RED (no feed; terms not verified). **Connector:** none.
  **Sample events:** none read.

### 3.21 Citizen Matters

- **Feed URL (8 Oct 14:09):** https://citizenmatters.in/feed/ (WordPress
  default; the home page declares only oEmbed/JSON alternates) → 200, 16 KB,
  10 items, 21 Sep → 8 Oct, descriptions only, site-wide (Bengaluru, Chennai,
  Delhi, Pune). `robots.txt`: disallows named AI and SEO bots only. **Tier 4.**
- **Terms (verbatim, 8 Oct, https://citizenmatters.in/terms-and-conditions/):**
  "You are permitted to print or download extracts from these pages for
  non-commercial and / or personal use only." A "#reprint-permissions" anchor
  exists on that page (its text was not isolated).
- **Classification:** BLUE, PERMISSION_REQUIRED; about four items a week, few
  on roads. **Connector:** generic RSS would work; not worth connecting now.
- **Sample event (read 8 Oct):** "Stop Hebbal Short Tunnel project: 20,000
  residents and activists sign petition" (24 Sep; a project, not a road event).

## 4. BTP cadence evidence and ASTraM findings

Five fetches of https://btp.karnataka.gov.in/en on 8 October 2026 (times from
the fetch log, IST; the page is served `Cache-Control: no-store`):

| Fetch | Time | Bytes | Congestion alerts (all stamped 11:45 08-10-2026) | Breakdown alerts | Events |
| --- | --- | --- | --- | --- | --- |
| 1 | 13:57:14 | 214,831 | 4 (Gandhi Circle Varthur; Chikka Banaswadi Road; Dr. CV Raman Road; Service Road Munnenkolalu) | "Seshadri Road, Gandhi Nagar 1 \| 12:59"; "7th Main Road, Block 3 \| 13:36" | 39 |
| 2 | 14:03:44 | 214,651 | same 4 | "7th Main Road, Block 3 \| 13:36" only (12:59 item gone) | 39, identical |
| 3 | 14:07:14 | 214,651 | same 4 | same as fetch 2 | 39, identical |
| 4 | 14:18:07 | 214,651 | same 4 | same as fetch 2 | 39, identical |
| 5 | 17:31:56 (fetched by the main session after the research agent was cut off) | 214,485 | same 4 | none (the 13:36 item gone) | 39 |

**Reading:** the "Traffic Alerts" panel is live-ish: a breakdown item was
removed between 13:57 and 14:03 (about an hour after its 12:59 stamp), the 13:36
item was gone by 17:31, while
the congestion batch kept its 11:45 stamp for the whole window (on 7 Oct the
batch stamped 11:30/11:45 was still shown at 20:00). The congestion items are
therefore a daily or occasional batch, not a 15-minute feed; breakdown items
have a lifetime of roughly an hour. The "Upcoming Events / Press Notes" list
did not change within the day; between 7 and 8 Oct it went from 40 to 39 items
(an ended item dropped). This is still a single-day sample; a multi-day
sample is needed before any refresh interval is relied on.

**ASTraM:** see 3.3. No public web interface for real-time updates, event
alerts, accident reporting, congestion alerts or traffic news exists beyond
the home-page panel; the "Incident Management" page is empty ("Content Updating
Soon"); the "Map Engine & API" has no registration or documentation page; the
congestion map is a Power BI report embedded by URL token. The ASTraM mobile
app was not examined.

## 5. Road network: OSM versus official Karnataka GIS

- **OpenStreetMap** remains the road network for Bengaluru: the place list
  built on 8 Oct (decision 0017) has 9,590 names, 8,994 with a position, under
  ODbL (attribution and share-alike of derived databases). Coverage of
  Bengaluru's arterial and residential roads is dense (not measured here).
- **Karnataka GIS (KSRSAC):** an ArcGIS Server 11.5 REST endpoint is publicly
  reachable (`/kgismaps/rest/services`) with state basemap MapServers and
  department folders, but (a) no road-centreline layer was verified in the
  folders checked, (b) no update date is published at the folder level, and
  (c) the portal's copyright policy states "Under no circumstances data will be
  used for any commercial purposes by anyone" and its disclaimer says the data
  "shall not be used for any legal purpose". KSRSAC's own `bbmpgis` / `bgis`
  portal apps were not opened. **Do not replace OSM**; do not use KGIS data in
  REI. If a road layer were ever needed from the state, it would need a written
  licence from KSRSAC.
- **data.gov.in** (where Karnataka road datasets under the Government Open Data
  License would be catalogued) is blocked to this client (403), so nothing
  there could be compared.

## 6. OCR needs

- **Among usable sources, none.** The BTP website publishes no PDFs for events
  or alerts (the only PDF on the site is the English "Coffee Table Book"); The
  Hindu and the other feeds are text. No Kannada or English scanned PDF stands
  between REI and a usable Bengaluru source today.
- **Raw-bytes checks (at most 2):**
  1. `https://ksp.karnataka.gov.in/storage/pdf-files/Circular-1_NoisePullution.pdf`
     (KSP, 8 Oct): 1,461,174 bytes, `%PDF-1.3`, **`/Font` present (12)** and
     `/Image` present (6): text layer exists (a circular, not a road event).
  2. Karnataka PWD circular of 18-03-2026 (7 Oct, `pdftotext`): 2 characters
     extracted, i.e. a scanned image with no text layer (not re-fetched).
- If BBMP/GBA notices (`updates.bbmpgov.in/public`, e.g. the bundle's
  "openhousevenues.pdf") become reachable, they are PDFs of unknown kind and
  should be byte-checked then. Kannada OCR is untested on this machine and no
  OCR library is installed (pip is broken).

## 7. Real events available now (read on 8 October 2026)

Tier 1 = BTP website; Tier 4 = news, with attribution as the article states
it. Categories use the brief's words. Items older than a week or already
ended (the 5–6 Oct waterlogging, the 1 Oct Sampigehalli wall collapse) are
listed last as recent, not current.

1. **Race Course Road closed between named junctions, 5 Oct – December 2026
   (60 days).** The Indian Express, 6 Oct 13:33 IST,
   https://indianexpress.com/article/cities/bangalore/bengaluru-traffic-restrictions-race-course-road-diversions-10908866/ :
   "the Greater Bengaluru Authority began white-topping work on Race Course
   Road from Maurya Junction to Hare Krishna Road Junction on October 5. They
   said in a press release Sunday …"; "All vehicles are prohibited from moving
   from Shivananda Junction to Maurya Junction … from Trilight Junction on Race
   Course Road towards Maurya Junction"; alternate routes via "L R D E Junction
   … Basaveshwara Junction", "Kumara Krupa Road to reach Shivananda Circle …
   S C Road", "over the Shivananda Flyover … S C Road via Nehru Circle". Also
   The Hindu, 5 Oct 20:22 (feed title "White topping work on Race Course Road,
   traffic diversions for 60 days"). Tier 4 ×2, attributed to Bengaluru
   Traffic Police press release and GBA. Possibly the same works as BTP item
   "Shivananda Junction, 05-10-2026 to 20-10-2026" (Tier 1; not established).
   Categories: closure, diversion, long-running, construction, utility.
2. **New Diagonal Road, Jayanagar white-topping, 07-10-2026 → 04-01-2027.**
   BTP list (quoted in 3.1), Tier 1. Categories: construction, long-running.
   Already in REI.
3. **5th Main Road, Chamarajpet white-topping, 27-07-2026 → 26-10-2026.** BTP
   list, Tier 1. Categories: construction, long-running. Already in REI.
4. **Twin Tunnel soil testing near Hebbal, 20-08-2026 → 31-01-2027.** BTP list,
   Tier 1. Categories: excavation, long-running.
5. **Shivananda Junction department work, 05-10-2026 → 20-10-2026.** BTP list,
   Tier 1. Categories: construction (type unstated), long-running.
6. **Channasandra night works (11 PM–5 AM), 28-08-2026 → 28-12-2026.** BTP list:
   "The work shout be carried out Only 11:0PM to 5:00AM. near , Channasandra …".
   Tier 1. Categories: construction, long-running, maintenance.
7. **Freedom Park gathering, 8 Oct 2026 from 10:30.** BTP list: "Public Event :
   Freedom Park, Bengaluru near Kalidasa Road, Gandhinagar … | Start : 10:30
   Hrs 08-10-2026 and End : 08-10-2026" (Tier 1) **and** Deccan Herald 8 Oct
   ("more than over 2,000 protesters gathered … at Freedom Park"), Prajavani 8
   Oct ("ಗುರುವಾರ (ಅ.8) ಬೆಳಿಗ್ಗೆ 10.30ಕ್ಕೆ ಸ್ವಾತಂತ್ರ್ಯ ಉದ್ಯಾನದಲ್ಲಿ"), The Times of
   India 8 Oct 11:26 ("'chappal protest' to follow"), The Indian Express live
   8 Oct. Tier 1 + Tier 4: a genuine two-source event, though no road measure
   is stated by any source. Categories: gathering, procession (possible).
8. **Decathlon Sarjapur Road, Outer Ring Road corridor, 10 Oct 06:00.** BTP
   "Public Event", Tier 1; type unstated (early-morning venue event, likely a
   run). Categories: gathering / marathon (unconfirmed).
9. **NICE Road Toll Plaza, Hosakerehalli, 11 Oct 05:30** and **"Nice Road", 25
   Oct 05:30.** BTP "Public Event", Tier 1; type unstated. Categories:
   gathering / marathon (unconfirmed).
10. **BIEC, Tumkur Road, 10–12 Oct 09:00; 23–26 Oct; 17–19 Nov.** BTP "Private
    Event", Tier 1. Categories: gathering (exhibition).
11. **Phoenix Mall of Asia, Bellary Road, 10 Oct 18:00; "Sprawling Outdoor
    Arena near Fraser Town / Hennur Main Outskirts", 10 Oct 14:00.** BTP
    "Private Event", Tier 1. Categories: gathering.
12. **The Soda Factory, Nagarabhavi, 17 Oct 16:00; Nexus Koramangala Mall,
    Hosur Road, 17 Oct 18:30.** BTP "Private Event", Tier 1. Gathering.
13. **Tripura Vasini, Palace Grounds, 23–25 Oct; Orion Mall Arena, Dr.
    Rajkumar Road, 24 Oct 18:30; Bhartiya Mall of Bengaluru, Thanisandra Main
    Road, 24 Oct 19:00; Palace Grounds (Bellary Road) 28–31 Oct and (Jayamahal
    Road entrance) 29–31 Oct.** BTP "Private Event", Tier 1. Gathering.
14. **Chandapura, NH-48/NH-44 (Hosur Road): standing water and underpass /
    railway-overbridge works causing hours-long jams, ongoing.** TV9 Kannada 6
    Oct 14:36 ("ಮಳೆ ನೀರು ನಿಂತಿರುವುದು ಮತ್ತು ಅಂಡರ್‌ಪಾಸ್ ಕಾಮಗಾರಿ … ಭಾರಿ ಟ್ರಾಫಿಕ್
    ಜಾಮ್"), The Hindu 5 Oct 22:31 ("Chandapura sees hours-long traffic jam"),
    The Times of India 7 Oct 22:19 ("NHAI has attributed a significant part of
    the recent congestion to the railway overbridge (ROB) being co[nstructed]";
    the death occurred "on the flyover" at Chandapura). Tier 4 ×3 (one
    Kannada). Categories: construction, underpass, waterlogging, congestion,
    long-running.
15. **Sanjaynagar Main Road white-topping, 2.56 km, Nagashettihalli to Ballari
    Road, to end November.** The Hindu 5 Oct 16:40 (feed: "scheduled to be
    completed by November-end, according to sources in the Greater Bengaluru
    Authority"; article read 7 Oct: "2.56-km stretch … 460-metre stretch is in
    progress"). Tier 4, attributed to GBA. Categories: construction,
    widening/white-topping, long-running; distance stated. Already in REI.
16. **Vehicle-class restrictions on the airport elevated corridor, BGS flyover,
    Peenya elevated corridor and the double-decker flyover, from 4 Sep 2026
    (phased).** The Indian Express 4 Sep and 9 Sep (titles in today's feed;
    text read 7 Oct). Tier 4, attributed to Joint CP (Traffic). Categories:
    long-running, flyover, restriction. Not re-confirmed as still in force.
17. **ITPL Main Road and Kundalahalli Colony: pothole filling, debris removal,
    footpath/drain repairs ordered (Varthur road works panel).** The Times of
    India 7 Oct 22:48. Tier 4, attributed to Bengaluru East City Corporation.
    Categories: maintenance; no closure stated.
18. **Attibele: car crashes into a petrol bunk and catches fire, night of 7–8
    Oct.** Deccan Herald 8 Oct. Tier 4, attributed to Attibele police.
    Categories: accident, emergency; road impact not stated.
19. **Four "Severe Congestion" points with coordinates, 8 Oct 11:45** (Gandhi
    Circle Varthur; Chikka Banaswadi Road; Dr. CV Raman Road, Sadashivanagar;
    Service Road, Munnenkolalu) and two vehicle breakdowns (Seshadri Road 12:59;
    7th Main Road Block 3 13:36). BTP alerts, Tier 1 (3.2). Categories:
    congestion, emergency (transient).
20. **Recent, ended: waterlogging of 5–6 Oct.** The Hindu 6 Oct ("slowing
    traffic on stretches including Laggere, Yeshwantpur and Hebbal … The
    Shivananda Circle and Hoodi underpasses were flooded … most instances of
    waterlogging were cleared overnight"). Tier 4. Categories: waterlogging,
    flooding, underpass.
21. **Recent, ended: Sampigehalli 150 m wall collapse and flooding, 1 Oct.**
    The Indian Express 1 Oct (title in feed; text read 7 Oct). Tier 4.
    Categories: flooding, emergency; distance stated.

Not counted: Mysuru Dasara diversions (outside the city); "Panathur Road to
reopen" (Nov 2025); ORR service-road closures (Jul 2026; the "45-day ORR
service road closure from 6 October" in web search is from October **2025**);
KSRTC/railway special trains; metro tenders; pothole statistics; the
transport-workers' 22 Oct strike deadline (not yet an event).

## 8. Open questions

1. **Permission from CeG/BTP** for re-publishing the website's lists is still
   not requested; the copyright modal's permission address is a blank template
   and the only working address is `pd.webportal@karnataka.gov.in`
   (hyperlinking). Who writes, and asking for what (events list, alerts, both)?
2. **Transient alerts:** should REI carry the "Traffic Alerts" points (exact
   coordinates, about hour-long lifetimes, congestion batch stamped once a
   day)? The user's decision.
3. **ASTraM map-provider API:** JSAN would have to approach BTP; no public
   route exists.
4. **BBMP/GBA hosts** (`bbmp.gov.in`, `updates.bbmpgov.in`, `site.bbmp.gov.in`,
   `api.bbmpgov.in`) have been unreachable on two days from two networks. Are
   they down, or is this environment's egress blocked? Test from another
   network (a phone hotspot would do). The GBA policy is the only permissive
   one found.
5. **data.gov.in** is 403 to this client on both days; the Karnataka
   catalogue (and the Government Open Data License) could not be checked.
6. **KGIS basemap layers:** whether `State_Basemap/State_Basemap` contains a
   road layer is unverified (3 requests would tell), but the non-commercial
   clause makes it unusable for REI regardless.
7. **Deccan Herald / Prajavani:** both publishers forbid automated extraction;
   should REI ask TPML for a licence (they offer "expressly licensed" use)?
8. **Kannada detection rules** (TV9, Prajavani): the term list in 3.15 is a
   start; ZWJ/ZWNJ normalisation and prefix matching are needed; false
   positives on ಮಳೆ (rain) and ಪ್ರತಿಭಟನೆ (protest, often political) are likely.
9. **New Indian Express** section filter carried 1 item on 7 Oct and 0 on 8
   Oct: unusable until proven otherwise.
10. **Refresh cadence** of both BTP panels comes from two single-day samples;
    a scheduled multi-day sample (one request an hour) would settle it.
11. Whether the Race Course Road, flyover-restriction and Chandapura advisories
    exist as Tier 1 records anywhere but X was not checked: REI does not read
    social media.
12. The BMRCL "English" host serves Kannada; whether an English site exists
    elsewhere was not pursued (nothing traffic-related is published either way).

## 9. Counts

- **Sources researched:** 22 (BTP website events list; BTP alerts panel
  counted with it; ASTraM; KSP; BBMP; GBA; data.gov.in; KGIS; KPWD; KRDCL;
  BDA; BMRCL; The Hindu; Indian Express; Times of India; Bangalore Mirror; TV9
  Kannada; New Indian Express; Deccan Herald; Prajavani; Vijaya Karnataka;
  Udayavani; Citizen Matters).
- **GREEN:** 0. **YELLOW:** 1 (BTP website, both panels). **BLUE:** 6 (The
  Hindu, Times of India, Bangalore Mirror, TV9 Kannada, New Indian Express,
  Citizen Matters). **RED:** 15 (ASTraM, KSP, BBMP, GBA, data.gov.in, KGIS,
  KPWD, KRDCL, BDA, BMRCL, Indian Express, Deccan Herald, Prajavani, Vijaya
  Karnataka, Udayavani).
- **PERMISSION_REQUIRED:** 7 (BTP website, ASTraM, Times of India, Bangalore
  Mirror, TV9 Kannada, New Indian Express, Citizen Matters).
- **Production candidates:** 1, conditional (BTP website, already connected and
  run by hand; production only after written permission). **Discovery
  sources:** 6 (one connected: The Hindu).
- **Real current/upcoming events read on 8 Oct:** 19 (items 1–19 in §7), of
  which Tier 1: 12 (plus the alerts); two-source: 2 (Race Course Road; Freedom
  Park, the latter Tier 1 + Tier 4); with exact coordinates: the alerts only;
  with a stated distance: 1 (Sanjaynagar, 2.56 km); with start and end dates:
  all 14 BTP list items and Race Course Road ("60 days" from 5 Oct).
