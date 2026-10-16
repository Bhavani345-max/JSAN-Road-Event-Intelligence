# India: city-local news outlets and official traffic/municipal sources (16 October 2026)

Research only. Nothing was connected, changed or scheduled. Cities: Delhi,
Kolkata, Chennai, Pune, Ahmedabad, plus sources not researched before for
Hyderabad, Mumbai and Bengaluru. National multi-city publishers (Times of
India, Hindustan Times, Indian Express, NDTV, India Today, ...) and the
excluded sources (Siasat, The Hindu, Deccan Chronicle, The Hans India,
Mid-day, Telangana Today, NewsMeter, Mumbai Traffic Police notifications,
Bengaluru Traffic Police website) were not researched.

**When and how.** 16 October 2026, 15:21-15:49 IST (09:51-10:19 UTC).
221 requests to 57 hosts, at most 10 per host, one at a time per host with at
least 2.5 s between requests to the same host, User-Agent
`JSAN-REI/1.0 (road event intelligence research)`. robots.txt was read before
any other path on every host. TLS was always verified (certifi; for servers
with incomplete chains the Windows trust store; for old government servers a
context that allows legacy renegotiation, certificates still verified). No
logins, CAPTCHAs, proxies or browser disguise. Discovery of candidate URLs
used web search (no fetching). Fetched files and scripts are in the session
scratchpad (`inlocal/data`, `inlocal/tools`).

**Verdict standard (REI).** RESTRICTED = personal/non-commercial use only, or
automated access / scraping / data mining / storage forbidden, or robots.txt
disallows the path. ASK_PERMISSION = no terms found, or terms silent, or a
government policy that allows re-use only after asking (no ban on automated
access). PERMITTED = re-use explicitly allowed (for example a government
copyright policy allowing reproduction with acknowledgement).

**Main findings.**

1. **No source in this round gives coordinates.** Every official list names
   places in words; most dates are in titles, file names or inside PDFs.
2. **Only one PERMITTED source: PIB** (copyright policy: reproduce free of
   charge, no prior approval, acknowledge the source). Its English city
   feeds could not be read within the request budget (the site redirects
   English requests to the Hindi edition).
3. **Best new official list: Ahmedabad City Police "Jahernama" page**
   (`cpahmedabad.gujarat.gov.in`): an HTML list of 1,742 notification PDFs,
   newest first, with 27 traffic or vehicle notifications from 2026
   (newest: Navratri heavy-vehicle ban, file dated 09/10/2026). Titles
   are Gujarati; the newest PDF is a scan (needs Gujarati OCR). Terms silent:
   ASK_PERMISSION.
4. **Chennai Metro Rail's road-diversion pages** (43 locations, diversion
   routes as HTML text) are the most structured diversion text found, but
   CMRL's terms forbid storing the content without written permission:
   RESTRICTED.
5. **Most city-local news outlets restrict commercial or automated use.**
   Terms re-read or read for the first time today put Hyderabad Mail,
   Telangana Tribune, Mumbai Live, Munsif, The Bengaluru Live, Afternoon
   Voice, DT Next, The Bridge Chronicle and The Telegraph in RESTRICTED. The
   feeds without terms (ASK_PERMISSION) are Punekar News, Pune Pulse,
   Mylapore Times, News Today, Kolkata24x7, Millennium Post, The South
   First, IndToday and Metro Rail News.
6. **Many official sites cannot be read by a plain HTTP client:** Delhi
   Traffic Police (robots.txt 403), Delhi Police and AIR News (timeouts),
   Tamil Nadu Police (invalid certificate), Ahmedabad Municipal Corporation
   (TLS failure), and JavaScript-only sites (Pune City Police, PMC, DMRC,
   NHAI, GBA/BBMP).

## Summary table

"Items" is what the fetched feed or list held today. "Dates where" says where a
road event's dates would be found. Robots = the `*` group for the path used.

| City | Source | Type | URL | HTTP | Items | Dates where | Coordinates? | Robots | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Delhi | Delhi Traffic Police advisories | Official (T1), HTML | https://traffic.delhipolice.gov.in/ | robots.txt **403** | — | — | — | robots.txt 403: host refuses this client; nothing else fetched | Unreachable |
| Delhi | Delhi Traffic Police (old host) | Official | https://delhitrafficpolice.nic.in/ | DNS failure | — | — | — | — | Unreachable |
| Delhi | Delhi Police | Official | https://delhipolice.gov.in/ | connect timeout ×2 | — | — | — | not obtainable | Unreachable |
| Delhi | Delhi PWD press releases / road works | Official, HTML | https://www.pwddelhi.gov.in/press-release | 200 | "No press releases match your search criteria" + 2 undated texts; road-works pages empty | — | No | robots.txt 404 (no rules) | No current data |
| Delhi | DMRC | Metro (T2), JS app | https://delhimetrorail.com/ | 200 (5.7 KB shell) | — | — | — | allows | Not readable |
| Delhi | AIR News (Prasar Bharati) | Govt broadcaster, RSS | https://newsonair.gov.in/feed/ | read timeout ×2 | — | — | — | allows | Unreachable |
| Delhi (and other cities) | PIB regional press releases | Official, RSS (listed) | https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3 | 302 to Hindi edition; budget used up | not verified | in release text | No | robots.txt is an HTML page (no rules) | **PERMITTED** (feed content not verified) |
| Delhi | Millennium Post, Delhi section | News, RSS | https://www.millenniumpost.in/category/delhi/google_feeds.xml | 200 | 23 in 20 h, full body | article text | No | allows | ASK_PERMISSION |
| Kolkata | Kolkata Traffic Police advisories | Official, HTML list of PDF links | https://kolkatatrafficpolice.gov.in/ | 200 | 35 advisory/diversion links, list undated; newest visible years 2025 | titles (some) and PDFs (text layer likely) | No | robots.txt 404 | ASK_PERMISSION |
| Kolkata | Kolkata Police | Official, WordPress RSS | https://kolkatapolice.gov.in/feed/ | 200 | **0 items** (empty channel) | — | — | robots.txt is HTML (no rules) | ASK_PERMISSION (policy: permission from NIC) |
| Kolkata | Metro Railway Kolkata press releases | Metro, HTML | https://mtp.indianrailways.gov.in/ | 200 | press titles in ticker; detail body not served; no road diversion notice | titles | No | robots.txt 404 | ASK_PERMISSION (permission by mail) |
| Kolkata | Kolkata Municipal Corporation | Official, JSP portal | https://www.kmcgov.in/KMCPortal/jsp/KMCPortalHome1.jsp | 200 | notices are old PDFs (2018-2023), no road-event list | — | No | robots.txt 404 | Not usable (terms not read) |
| Kolkata | Kolkata24x7, Kolkata city (Bengali) | News, RSS | https://kolkata24x7.in/category/kolkata/feed/ | 200 | 30 in 7 days, full body | article text (Bengali) | No | allows | ASK_PERMISSION |
| Kolkata | Millennium Post, Bengal section | News, RSS | https://www.millenniumpost.in/category/bengal/google_feeds.xml | 200 | 29 in 24 h, full body | article text | No | allows | ASK_PERMISSION |
| Kolkata | The Telegraph, My Kolkata | News, HTML (feed not located) | https://www.telegraphindia.com/my-kolkata | 200 (home) | — | article text | No | allows `*`; blocks ClaudeBot, GPTBot, CCBot and 15 more | **RESTRICTED** |
| Kolkata | Get Bengal | News | https://www.getbengal.com/ | robots 200 | — | — | — | **`Disallow: /`** | **RESTRICTED** (robots) |
| Chennai | Greater Chennai Traffic Police / TN Police | Official | https://www.tnpolice.gov.in/ | TLS: host-name mismatch, certificate outside validity | — | — | — | not obtainable | Unreachable |
| Chennai | Greater Chennai Corporation press releases (Tamil) | Official, HTML list of PDFs | https://chennaicorporation.gov.in/gcc/ | 200 | ~20 latest links, `news_YYYYMMDD_n.pdf` | file name; PDF text layer (Print-to-PDF, fonts, no images) | No | robots.txt 404 | ASK_PERMISSION (permission from department) |
| Chennai | CMRL road diversions | Metro, HTML pages | https://chennaimetrorail.org/road-diversion/ | 200 | 43 location pages, routes in text | **no dates** on pages; WordPress says index modified 24 Sep 2025 | No (named roads) | allows | **RESTRICTED** |
| Chennai | CMRL news | Metro, RSS | https://chennaimetrorail.org/feed/ | 200 | 10, newest 10 Oct 2026, oldest Jul 2024; no road items | — | No | allows | **RESTRICTED** |
| Chennai | DT Next, Chennai | News, RSS | https://www.dtnext.in/api/v1/collections/newschennai-news.rss | 200 | 40 in 3 days, full body | article text | No | allows (listed in robots.txt as a sitemap) | **RESTRICTED** |
| Chennai | Mylapore Times | Hyperlocal news, RSS | https://www.mylaporetimes.com/feed/ | 200 | 9 in 2 days, full body | article text | No | allows | ASK_PERMISSION |
| Chennai | News Today | News, RSS | https://newstodaynet.com/feed/ | 200 | 9 in 40 min, full body | article text | No | allows | ASK_PERMISSION |
| Pune | Pune City Police | Official, JS app | https://punepolice.gov.in/ | 200 (3.4 KB shell) | — | — | — | allows | Not readable |
| Pune | Pune Municipal Corporation | Official, Next.js | https://www.pmc.gov.in/news | 200 (client-rendered) | — | — | — | allows | Not readable |
| Pune | Pune Metro (Maha-Metro) press releases | Metro, HTML | https://www.punemetrorail.org/press-release | 200 | traffic-diversion titles only in the old part of the list | titles | No | allows | ASK_PERMISSION (nothing current) |
| Pune | Punekar News | News, RSS | https://www.punekarnews.in/feed/ | 200 | 10 in 3.3 h, full body | article text | No | robots.txt has no rules (content-signal preamble only) | ASK_PERMISSION |
| Pune | Pune Pulse | News, RSS | https://www.mypunepulse.com/feed/ | 200 | 15 in 18 h, summaries | article text | No | allows | ASK_PERMISSION |
| Pune | The Bridge Chronicle, Pune | News, RSS | https://www.thebridgechronicle.com/stories.rss?section=pune | 200 | 2, full body | article text | No | allows | **RESTRICTED** |
| Pune | Pune Mirror | News | https://punemirror.com/ | connection reset ×2 | — | — | — | not obtainable | Unreachable |
| Ahmedabad | Ahmedabad City Police notifications (Jahernama) | Official, HTML list of PDFs | https://cpahmedabad.gujarat.gov.in/cpahmedabad/CMS.aspx?content_id=23838 | 200 | 1,742 PDF links; 27 of the 2026 links concern traffic or vehicles; newest 09/10/2026 | titles (Gujarati numerals) and file names; PDFs scanned | No | robots.txt redirects to an HTML 404 page (no rules) | ASK_PERMISSION |
| Ahmedabad | Ahmedabad Municipal Corporation | Official | https://ahmedabadcity.gov.in/ | TLS fails (incomplete chain + legacy renegotiation) | — | — | — | not obtainable | Unreachable |
| Ahmedabad | ahmedabadcitypolice.org | Official (old) | https://ahmedabadcitypolice.org/ | connection reset ×2 | — | — | — | — | Unreachable |
| Ahmedabad | Gujarat Metro Rail (GMRC) | Metro, HTML + PDF | https://www.gujaratmetrorail.com/ | 200 | 1 press note (14.10.26, text-layer PDF); no traffic notice | PDF | No | allows | **RESTRICTED** |
| Ahmedabad | DeshGujarat | News, RSS | https://deshgujarat.com/feed/ | 302 to FeedBurner, 200 but **HTML, 0 items** | — | — | — | Ahmedabad category **disallowed**; `Crawl-delay: 300` | **RESTRICTED** (robots) |
| Ahmedabad | Ahmedabad Mirror | News | https://www.ahmedabadmirror.com/ | read timeout ×2 | — | — | — | allows | Unreachable |
| Ahmedabad | Gujarat Samachar | News (Gujarati) | https://www.gujaratsamachar.com/ | 200 | **no RSS link**; sitemaps incl. Ahmedabad category | — | — | allows | Not verified (terms not found) |
| Ahmedabad | Sandesh | News (Gujarati) | https://sandesh.com/ | 200 (16 KB JS shell) | no feed link | — | — | allows | Not verified |
| Hyderabad | The South First | News, RSS (south India) | https://thesouthfirst.com/feed/ | 200 | 10 in 5 h, full body | article text | No | allows | ASK_PERMISSION |
| Hyderabad | IndToday | News, RSS | https://indtoday.com/feed/ | 200 | 10 in 3 h, full body | article text | No | allows | ASK_PERMISSION |
| Hyderabad | Munsif News 24x7 | News, RSS | https://munsifdaily.com/feed/ | 200 | 20 in 4 h, summaries | article text | No | site feed allowed; section feeds (`/*/feed/`) disallowed | **RESTRICTED** |
| Hyderabad | Hyderabad Mail | News, RSS | https://hyderabadmail.com/feed/ | 200 | 10 in 5 h, full body in description | article text | No | allows | **RESTRICTED** |
| Hyderabad | Telangana Tribune | News, RSS | https://www.telanganatribune.com/feed/ | 200 | 10 in 23 h, summaries | article text | No | allows | **RESTRICTED** |
| Mumbai | Mumbai Live, civic | News, RSS | https://www.mumbailive.com/rss/en/civic.xml | 200 | 20 in 2 days, full text in description | article text | No | allows; `Crawl-delay: 10` | **RESTRICTED** |
| Mumbai | Afternoon Voice | News, RSS | https://www.afternoonvoice.com/feed | 200 | 10 in 4 days, full body | article text | No | allows `*`; blocks ClaudeBot, GPTBot, CCBot and 12 more | **RESTRICTED** |
| Bengaluru | The Bengaluru Live | News, RSS | https://thebengalurulive.com/feed/ | 200 | 50 in 3 days, summaries | article text | No | allows | **RESTRICTED** |
| Bengaluru | GBA / BBMP | Official, React app | https://gba.karnataka.gov.in/ , https://bbmp.gov.in/ | 200 (666-byte shells) | — | — | — | allows | Not readable |
| Multi-city | Metro Rail News | Trade news, RSS | https://metrorailnews.in/feed/ | 200 | 10 in 2 days, summaries; no road items | article text | No | allows | ASK_PERMISSION |
| Multi-city | NHAI | Official, JS app | https://nhai.gov.in/ | 200 (4.5 KB shell) | — | — | — | robots.txt 404 | Not readable |

## Current road-event items seen today

Fetched feeds and lists are small windows; most held no road event today.
Items found (verbatim where quoted; nothing inferred):

- **Ahmedabad City Police** list: "નવરાત્રી મહોત્સવ-૨૦૨૬ ભારે વાહન પ્રતિબંધ
  જાહેરનામું" (Navratri festival 2026 heavy-vehicle ban notification),
  `upload/CPAHMEDABADJahernamu1_09102026.pdf`; "ગણેશ વિસર્જન ટ્રાફિક
  જાહેરનામું-૨૦૨૬" (Ganesh immersion traffic notification 2026),
  `upload/CPAhmedabadPressnote02_23092026.pdf`. The first PDF is 4 scanned
  pages (0 fonts, 4 images; scanner "VersaLink B7125 MFP"): its roads and
  times were not read.
- **Pune Pulse** (article page, published 15 Oct 2026 11:37 UTC; it had
  already left the 15-item feed): "heavy and large vehicles have been
  prohibited from entering the stretch between Karla Phata and the foothill
  temple of Shri Ekvira Devi around the clock until October 20" (order of
  the district collector under s.115 MV Act).
- **Kolkata24x7** (11 Oct 2026, Bengali): "চতুর্থী অর্থাৎ ১৪ অক্টোবর থেকে
  প্রতিদিন বিকেল ৩টে নাগাদ অটোর চলাচল নিয়ন্ত্রণ করা হবে। এই নির্দেশ কার্যকর
  থাকবে একাদশী, অর্থাৎ ২২ অক্টোবর" (auto-rickshaw movement controlled daily
  from about 3 pm, 14 to 22 October).
- **CMRL** RK Salai page (undated): "VP Raman road (VM Street Jn. To
  Jumbulingam Street), VM Street, Judge Jumbulingam Street is made One Way for
  all Vehicle." and "Heavy Vehicles restriction from Ajantha junction to
  Indian Bank Junction via. ADMK Party Office."
- **Millennium Post, Delhi** (15 Oct 2026): "Heavy rain brings traffic to a
  crawl across Delhi", which reports waterlogging but no closure.
- **The Bengaluru Live** (15 Oct 2026): "Bengaluru Rain: Hemmigepura Logs 49
  mm, JP Nagar 40 mm; Tree Falls Reported as Crews Tackle Waterlogging";
  (14 Oct) "Bengaluru road circulation maps: GBA invites objections".
- **Kolkata Traffic Police** list: "Notification for Traffic Diversion at
  Picnic Garden Road under Tiljala ..." (`trafficadvisoryNotificationKMC.pdf`)
  and "Kolkata Police SDSL Half Marathon 2025 Route ..."; neither PDF's text
  was decoded here.
- **The Telegraph** (RESTRICTED) home page: "From Behala and Gariahat to
  Sector V, Kolkata commuters battle Puja tr[affic]" (URL slug
  `road-closures-and-auto-bus-restrictions-disrupt-commutes-from-behala-to-sector-v`).
- No road-event item was in today's windows of Punekar News, The Bridge
  Chronicle, Mylapore Times, News Today, DT Next (3 keyword false positives),
  Millennium Post Bengal, The South First, IndToday, Munsif, Hyderabad Mail,
  Telangana Tribune, Mumbai Live civic, Afternoon Voice or Metro Rail News.

## Per-source notes

### Official sources

**PIB (Press Information Bureau), regional offices**: PERMITTED.
`/ViewRss.aspx` lists RSS feeds as `RssMain.aspx?ModId=6&Lang=<l>&Regid=<r>`
(ModId 6 = releases), with regional office codes Delhi 3, Mumbai 1 (Pune
releases go here), Hyderabad 5, Chennai 6, Kolkata 19, Bengaluru 20,
Ahmedabad 22. Requests for English (`Lang=1`) were redirected to the Hindi
edition (`Lang=2&reg=48`), and the 10-request budget ran out before a feed
could be read, so item counts and dates are **not verified**. Copyright
policy (https://www.pib.gov.in/ContentPage.aspx?menuid=137&reg=48&lang=2;
English link `content/137_1_CopyrightPolicy.aspx` redirects to this Hindi
page): "इस वेबसाइट में प्रकाशित सामग्री को निशुल्क पुन: प्रस्तुत किया जा सकता
है और इसका उपयोग करने के लिए किसी पूर्वानुमोदन की कोई आवश्यकता नहीं है। ...
जहां कहीं भी यह सामग्री प्रकाशित की जा रही है अथवा दूसरों को जारी की जा रही
है, वहां उसके स्रोत को प्रमुख रूप से अभिस्वीकृत किया जाना चाहिए।" (Material
published on this website may be reproduced free of charge and no prior
approval is needed to use it ... wherever it is published or issued to
others, its source must be prominently acknowledged.) Terms of use (menuid
138) is a liability disclaimer. Road closures appear in PIB releases only
occasionally.

**Ahmedabad City Police, notifications ("જાહેરનામાં અને હુકમો")**: ASK_PERMISSION.
https://cpahmedabad.gujarat.gov.in/cpahmedabad/CMS.aspx?content_id=23838
(linked from the home page; found through a link on police.gujarat.gov.in).
A server-rendered HTML list (1.4 MB) of 1,742 PDF links, newest first. The
titles are in Gujarati and often state the period ("તા.૧૪/૧૦/૨૦૨૬ ના
૧૪/૦૦ થી"); file names carry the issue date (`..._09102026.pdf`). 140
links mention 2026 (mostly in the file name) and 27 of those mention traffic
or vehicles (Navratri heavy-vehicle ban, Ganesh immersion, Eid-e-Milad,
Tiranga Yatra, Rath Yatra diversion, bullet-train works, IPL, one-way order
of 21.4.2026, plus a few election and convoy orders). The
newest PDF checked is a scan, so Gujarati OCR is needed. robots.txt
redirects to `PageNotFound.html` (no rules). The only policy page is the
disclaimer (`CMS.aspx?content_id=143`, Gujarati): "આ વેબસાઇટનું સાહિત્ય
માત્ર માહિતીપ્રદ છે અને તે જાહેર જનતાના લાભ માટે છે." (The website's
material is for information only and for the benefit of the public.) It says
nothing about re-use. Footer: "© પોલીસ કમિશનરશ્રીની કચેરી, અમદાવાદ".

**Kolkata Traffic Police**: ASK_PERMISSION. https://kolkatatrafficpolice.gov.in/
(old server; needs legacy TLS renegotiation). The home page links 35
advisories and diversion plans as PDFs ("Traffic Advisory in connection with
closure of Sealdah Flyover.", "Notification for Traffic Diversion at Picnic
Garden Road ...", "Kolkata Police SDSL Half Marathon 2025 Route ..."). The
list itself has no dates. Many items are visibly old (FIFA U-17, the
Majherhat flyover collapse, "TATA STEEL MARATHON 2019", "04.08.2016"), and
two mention 2025. The Picnic
Garden PDF has 7 fonts and 2 images, so a text layer is likely; it was not
decoded. `traffic_restriction.html` is navigation only. robots.txt 404. The
site has no policy page, only "Copyright © Kolkata Traffic Police".

**Kolkata Police**: ASK_PERMISSION. https://kolkatapolice.gov.in/feed/ is
an empty WordPress channel (lastBuildDate 15 Oct 2026). Copyright policy
(https://kolkatapolice.gov.in/copyright-policy/): "Contents of this website
may not be reproduced partially or fully, without due permission from NIC.
If referred to as a part of another website, the source must be
appropriately acknowledged." The terms page has no re-use clause.

**Metro Railway Kolkata**: ASK_PERMISSION, no road notices.
Press-release titles on the home page are metro "traffic and power blocks"
and works ("BIG BOOST FOR CONSTRUCTION OF PINK LINE KMC ISSUES NOC FOR
CLOSURE OF WATER TRANSMISSION LINE ALONG BT ROAD"). The detail page
(`view_detail.jsp?lang=0&dcd=5705`) returned the page frame without the
release text. Disclaimer
(https://mtp.indianrailways.gov.in/view_section.jsp?lang=0&id=0,7,286):
"Material featured on this portal may be reproduced free of charge after
taking proper permission by sending a mail to us. ... Wherever the material
is being published or issued to others, the source must be prominently
acknowledged."

**Kolkata Municipal Corporation**: not usable. The portal home page links
notices (2018-2023 PDFs, a 2026 rebate notice, a 2026 sewer compensation
notification) and "Circular & MIC Resolution" on `kmc.wb.gov.in`. There is
no road-closure or works list. Its policy pages were not read.

**Greater Chennai Corporation**: ASK_PERMISSION. https://chennaicorporation.gov.in/gcc/
(the root shows a default Tomcat page). Its "What's new" lists Tamil press
releases `/news/news_YYYYMMDD_n.pdf` (three dated 15 Oct 2026; recent
titles concern northeast-monsoon relief and civic work). The newest PDF is "Microsoft: Print To PDF", with 3
fonts and no images, so it has a text layer (Tamil; not decoded). Policy
(https://chennaicorporation.gov.in/gcc/common/privacy-policy/): "Material
featured on this Portal maybe reproduced free of charge after taking proper
permission from the respective Organisation / Department. ... the source
must be prominently acknowledged." No road-closure list was found.

**Chennai Metro Rail (CMRL)**: RESTRICTED. https://chennaimetrorail.org/road-diversion/
links 43 pages (Otteri, RK Salai, Adyar Junction, Thoraipakkam, ...). Each
gives the diversion routes as text, with no start or end date; WordPress
reports the index page as modified 2025-09-24. https://chennaimetrorail.org/feed/
has 10 posts (newest 10 Oct 2026), none about roads. Terms
(https://chennaimetrorail.org/terms-conditions/): "The copyright of the
material contained in this Website belongs to and solely with CMRL. Your
access to this website does not license you to reproduce transmit store
anywhere or disseminate the contents of this website without CMRL's prior
written permission."

**Gujarat Metro Rail (GMRC)**: RESTRICTED. Terms
(https://www.gujaratmetrorail.com/terms-condition/): "You have no right to use
any search mechanisms other than that provided on the Website and will not use
any web-crawler or any data harvesting tools to harvest data of any sort from
the Website"; "You shall not create a link to a page of this website without
our prior permission." Disclaimer (https://www.gujaratmetrorail.com/disclaimer/):
"Material featured on this Portal/Website may be reproduced free of charge
after taking proper permission by sending a mail to us." Only one press note
(14.10.2026, Word-generated PDF) and no traffic notice were seen.

**Pune Metro (Maha-Metro)**: ASK_PERMISSION, nothing current. The
press-release list includes "Traffic Diversion at Shivaji Nagar", "Traffic
Diversion at Bund Garden Road for Pune Metro work" and "MAHA Metro Releases
Traffic Diversion Plan for PCMC", all in the old part of the list (below
items from 2020-2022). The policies page says only "Copyright 2016 - Pune
Metro Rail Project. All RIGHTS RESERVED."

**Delhi PWD**: no current data. `/press-release` says "No press releases
match your search criteria." and shows two undated texts (one on the
Haiderpur flyover crack). `/maintenance-work/road` and
`/construction-work/road` have no list in the HTML. The footer links only a
privacy policy.

**Not readable or unreachable (official)**:
- traffic.delhipolice.gov.in: robots.txt answered HTTP 403 with an HTML error
  page, so nothing else was requested. Web search shows the site has a
  "Traffic Advisory" section and PDF notifications under
  `/sites/default/files/uploads/`.
- delhitrafficpolice.nic.in: does not resolve.
- delhipolice.gov.in: two connect timeouts.
- newsonair.gov.in (AIR News): robots.txt allows everything, but `/feed/`
  timed out twice.
- tnpolice.gov.in (with and without `www`): certificate host-name mismatch
  (certifi) and "not within its validity period" (Windows store). Web search
  confirms that Greater Chennai Police has no separate website.
- ahmedabadcity.gov.in: certificate chain incomplete and legacy
  renegotiation required; no verified TLS mode connected.
- ahmedabadcitypolice.org and punemirror.com: connection reset twice.
- JavaScript-only shells with no content in the HTML: punepolice.gov.in
  (which also loads a script from a third-party domain), pmc.gov.in (Next.js;
  `/news` and `/b/website-policies` render client-side, so PMC's policy text
  was not readable), delhimetrorail.com, nhai.gov.in, gba.karnataka.gov.in
  and bbmp.gov.in. GBA and BBMP answered today (they timed out on 8 Oct),
  both serving the same 666-byte React shell. robots.txt on both:
  `User-agent: * / Disallow:`.

### News outlets: ASK_PERMISSION (no terms found, or terms silent)

- **Punekar News** (https://www.punekarnews.in/feed/): 10 items, 16 Oct
  03:54-07:13 UTC, full `content:encoded` (avg 1,888 chars), categories
  "Pune", "PCMC". robots.txt is only a Cloudflare content-signal preamble
  ("ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS
  OF RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790"),
  with no User-agent line and no signal values. The WordPress page list has
  no terms page (pages: About Us, Contact Us, Grievance Redressal, ...).
  Footer: "Copyright © All rights reserved".
- **Pune Pulse** (https://www.mypunepulse.com/feed/): 15 items, 15 Oct 15:36
  to 16 Oct 09:31 UTC, summaries only (avg 224 chars), categories include
  "Pune traffic" and "Pune infrastructure". Only a privacy policy exists
  (https://www.mypunepulse.com/accreditations/); no terms page found.
- **Mylapore Times** (https://www.mylaporetimes.com/feed/): 9 items, 14-16
  Oct, full body (avg 854 chars), hyperlocal Mylapore civic and events news.
  There is no terms page among the site's WordPress pages; footer
  "Copyright © 2026 MYLAPORE TIMES".
- **News Today** (https://newstodaynet.com/feed/): 9 items in 40 minutes,
  full body; mostly Tamil Nadu politics. Terms
  (https://newstodaynet.com/terms-and-conditions/) say only that the site may
  deny access "for any unauthorized access or use". The page also contains
  injected essay-writing advertisements, so the site's integrity is
  doubtful.
- **Kolkata24x7** (Bengali; https://kolkata24x7.in/category/kolkata/feed/):
  30 items, 8-15 Oct, full body (avg 2,861 chars). Terms
  (https://kolkata24x7.in/terms-conditions/): "Unauthorized reproduction,
  distribution, or modification is strictly prohibited without prior written
  consent. You may share links to our articles provided proper credit is
  given." Automated access and storage are not addressed. Storing full
  bodies may count as reproduction; links and extracted facts would not.
- **Millennium Post** (Delhi feed above; Bengal
  https://www.millenniumpost.in/category/bengal/google_feeds.xml, 29 items in
  24 h, full body). The site-wide `google_feeds.xml` is stale (60 items, all
  27 Jul 2026). No terms link in the HTML; `/terms-and-conditions` returns 404.
- **The South First** (https://thesouthfirst.com/feed/): 10 items in 5 h,
  full body (avg 5,783 chars), covering Telangana, Karnataka, Kerala and
  Andhra Pradesh. Section feeds do not exist (`/karnataka/feed/` redirects to
  an image; `/telangana/feed/` ends in 404). The disclaimer
  (https://thesouthfirst.com/disclaimer/) has no re-use clause: "© Copyright
  SouthFirst 2025 All rights reserved."
- **IndToday** (https://indtoday.com/feed/): 10 items in 3 h, full body;
  categories "Hyderabad News", "Telangana News" mixed with national news. No
  terms page among its WordPress pages (privacy policy, code of ethics,
  about, contact).
- **Metro Rail News** (https://metrorailnews.in/feed/): 10 items, 14-16 Oct,
  summaries; a national metro and railway trade site with no road events
  today. "Rules & Policies" is a page of metro laws, not site terms; no terms
  page found.

### News outlets: RESTRICTED

- **Hyderabad Mail** (feed works: 10 items, full body). Terms
  (https://hyderabadmail.com/terms-conditions/): "Hyderabad Mail grants you
  permission to only access and make personal use of the Site"; "you may
  print or download extracts from these pages for your personal /
  individual, non-commercial use only"; "these files may not be used to
  construct any kind of database"; it forbids "any data gathering or
  extraction tools". These terms were not assessed before today.
- **Telangana Tribune** (10 items, summaries). Terms
  (https://www.telanganatribune.com/terms-of-use/): "You may access and read
  the Content for personal, non-commercial use only. You may not reproduce,
  distribute, modify, or publicly display any Content without prior written
  permission."
- **Munsif News 24x7** (https://munsifdaily.com/terms-of-use/): "You agree
  not to reproduce, duplicate, copy, sell, resell or exploit any portion of
  the Service ... without express written permission by us." robots.txt
  disallows section feeds (`Disallow: /*/feed/`).
- **The Bengaluru Live** (https://thebengalurulive.com/terms-of-service/):
  "You may access and use the Websites for lawful personal and
  non-commercial purposes. ... You must not reproduce, republish,
  distribute, sell, license, systematically archive or create a substitute
  service from substantial portions of the Websites without prior written
  permission"; misuse "includes scraping or harvesting content or data at
  scale; using bots, crawlers or automated systems except as permitted by
  applicable law and our robots instructions".
- **Mumbai Live** (https://www.mumbailive.com/T&C; linked "TERMS &
  CONDITIONS" in the footer, which was not found on 8 Oct): "[You] are granted
  limited license only for purposes of viewing the material contained on
  this Website. Restrictions You are specifically restricted from all of the
  following: publishing any Website material in any other media; selling,
  sublicensing and/or otherwise commercializing any Website material; ...
  engaging in any data mining, data harvesting, data extracting or any other
  similar activity in relation to this Website". This contradicts its
  robots.txt comment ("Articles, sections and images are open to every
  search engine, social network, news aggregator and AI assistant."); the
  terms decide. Feeds: `/rss/en/latest.xml`, `/rss/en/civic.xml`, ...
- **Afternoon Voice** (https://www.afternoonvoice.com/disclaimer): "No one is
  authorized for making commercial use in any form
  (reproduction/transmitting/story) available in our database/content without
  prior written permission obtained from the editor-in-chief." robots.txt has
  an "# AI Bot Restrictions" block (GPTBot, ClaudeBot, anthropic-ai, CCBot,
  Google-Extended, ...: `Disallow: /`).
- **DT Next** (https://www.dtnext.in/terms-of-use; the page is written for
  its PressReader e-paper service): "DT Next owns intellectual property
  rights in (i) the content included within the Publications; the selection,
  coordination, and arrangement of the Service, the Website, the App and the
  Publications ... Publications may not be modified, reverse engineered,
  redistributed, sold, publicly displayed, licensed, rented, or otherwise
  provided to a third party or commercially exploited." Technically the best
  Chennai feed (40 items, full body).
- **The Bridge Chronicle** (Sakal Media;
  https://www.thebridgechronicle.com/terms-and-conditions): "You may not sell
  or modify the content of this website and/or mobile application or
  reproduce, display, publicly perform, distribute, or otherwise use the
  materials in any way for any public or commercial purpose without the
  respective organisation's or entity's written permission."
- **The Telegraph** (ABP; https://www.telegraphindia.com/terms-of-use): "ABP
  grants you permission to only access and make personal use of the Site";
  "you may print or download extracts from these pages for your personal /
  individual, non-commercial use only"; "ABP forbids you from ... any data
  gathering or extraction tools"; "You may not (whether directly or through
  the use of any software program) create a database in electronic or
  structured manual form by regularly or systematically downloading and
  storing all or any part of the pages from this site." robots.txt blocks 18
  named AI crawlers including ClaudeBot.
- **Get Bengal**: robots.txt `User-agent: * / Disallow: /`. Nothing else
  was fetched.
- **DeshGujarat**: robots.txt sets `Crawl-delay: 300` and
  `Disallow: /category/gujarat-2/`, which holds the Ahmedabad category
  (`/category/gujarat-2/ahmedabad/`), and `Disallow: /*?*`. `/feed/` redirects
  to `http://feeds.feedburner.com/DeshGujarat/news`, which returns an HTML
  page labelled `text/xml` (0 items). The about page is a privacy statement.

## Not verified

- PIB English regional RSS content (item counts, dates): budget exhausted by
  language redirects. A next check should request `Lang=2` (Hindi) or find
  how the site selects English without a session.
- Delhi Traffic Police advisory listing (robots.txt 403), AIR News feed
  (timeouts), Delhi Police (timeouts): not read today. A retry from another
  network or at another hour may differ.
- Telegraph My Kolkata feed URL: not located (the terms are restrictive
  anyway).
- Gujarat Samachar: no RSS link in the HTML; the sitemap index lists
  `news-sitemap.xml` and Ahmedabad category sitemaps (not fetched); terms
  not found in the server-rendered HTML. Sandesh: JavaScript shell, no
  feed or terms readable.
- Text of the Kolkata Traffic Police, GCC and GMRC PDFs: text layers are
  likely (fonts present, few or no images) but were not decoded (no PDF
  library on this machine). The Ahmedabad Police PDF checked is a scan.
- Metro Railway Kolkata press-release bodies: not served to this client.
- PMC policy text: rendered client-side, not readable.
- Ahmedabad Municipal Corporation, Tamil Nadu Police, Pune Mirror,
  Ahmedabad Mirror, ahmedabadcitypolice.org: unreachable with verified TLS or
  at all.
- Earlier Tier 1 Hyderabad sources (Hyderabad Traffic Police, Cyberabad,
  Rachakonda/Malkajgiri, GHMC) were not re-fetched; see
  [the Hyderabad research](../cities/hyderabad-source-research.md).
- Telugu, Kannada, Tamil, Bengali and Gujarati keyword coverage: today's
  searches for road events were English plus a small Bengali/Gujarati/Hindi
  list; items in other wording may have been missed.

## Access-rule slips during this research

- **DeshGujarat** (`Crawl-delay: 300`): `/feed/` was requested 3 s after
  robots.txt, before the fetcher honoured crawl-delay. The only later
  request (the about page) came 18 minutes after.
- **Mumbai Live** (`Crawl-delay: 10`): the home page was requested 3 s after
  robots.txt. Later requests kept at least 10 s apart.
- **ahmedabadcity.gov.in**: a retry bug in the fetcher made 9 TLS handshake
  attempts to robots.txt over 22 s (each at least 2.5 s apart; none
  completed an HTTP request) and used up the host's 10-request budget.
- The first two rounds checked robots.txt with Python's `urllib.robotparser`,
  which ignores `*` and `$` wildcards. Every fetched URL was re-checked
  afterwards with wildcard-aware matching: 0 fetches were disallowed.
- `/karnataka/feed/` on The South First redirected to a 1.3 MB PNG on
  `static.thesouthfirst.com`, which was followed (allowed by that host's
  robots.txt).
- Afternoon Voice `/disclaimer` was fetched. Its robots.txt rule
  `Disallow: */disclaimer/*` does not match the path without a trailing
  slash, but the intent may have been to cover it.
- WordPress `wp-json/wp/v2/pages` listings were used on five sites to look
  for terms pages (public, allowed by robots.txt).
