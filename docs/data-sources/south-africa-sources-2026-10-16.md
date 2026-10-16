# Source research, 16 October 2026: South Africa (second pass)

South Africa shows no events in REI. This pass re-checks the Western Cape
road closures layer under the rule change of 16 October 2026 (an event with a
source start date but no end date may now be shown) and looks for sources the
first pass ([south-africa-source-research-2026-10-15.md](south-africa-source-research-2026-10-15.md))
missed, including South African news feeds.

Every endpoint below was fetched live on 16 October 2026 between 09:49 and
10:17 UTC (11:49-12:17 South African time) with the User-Agent
`JSAN-REI/1.0 (road event intelligence research)`. robots.txt was requested
first on every host. Requests were sequential with a 2-second pause, at most
10 per host (the most on one host was 9), and redirects were not followed
automatically. There were no logins, keys, CAPTCHAs, proxies or browser
disguise. Nothing was connected and no code was changed.

Verdicts use REI's standard: **RESTRICTED** (personal or non-commercial only,
or forbids automated access, scraping, data mining or storage, or robots.txt
disallows); **ASK_PERMISSION** (no terms found, or the terms are silent);
**PERMITTED** (explicitly allowed, such as Creative Commons or an open data
licence). This is a reading of published terms, not legal advice.

## Result in short

- **Western Cape road closures layer: technically ready, still blocked by its licence.**
  Under the new rule all 47 closures qualify: every one has a start date, none
  has an end date, and every one has a line and coordinates. The licence is
  unchanged: non-commercial reuse only without permission; commercial reuse
  "may be granted subject to a written request to service@westerncape.gov.za".
- **Only one source is PERMITTED: SAnews (the government news agency, GCIS).**
  It has a working RSS feed with full article text and a published grant: "Media are welcome to utilise all stories … at no cost, provided SAnews is credited."
  It is text only (no coordinates), and road closures are occasional: none
  were in today's 10 items.
- **New ASK_PERMISSION finds:** the Arrive Alive "News from Arrive Alive" feed
  (live Durban/KZN traffic alerts with named intersections, five items, all
  from today) and its sister site trafficinformation.co.za (same owner).
  Neither publishes any terms beyond "All rights reserved".
- Every large South African news publisher checked (IOL with Cape Argus and
  Cape Times, TimesLIVE, EWN with 702 and CapeTalk, Jacaranda FM) limits use to
  personal or non-commercial purposes. News24's terms could not be read (a
  Cloudflare challenge). The Citizen (with the Caxton local papers such as
  Roodepoort Record), Daily Maverick and SABC could not be read at all.
- The metros publish text only. Cape Town, Johannesburg and Nelson Mandela Bay
  limit reuse to non-commercial use. Tshwane, eThekwini and Ekurhuleni have no
  reuse terms, but their feeds carry no road events today.

## Summary table

HTTP = status of the main data URL. Items = items in the feed or list today.
"Dates?" = a date for the event in the data (not only a publication date).
"Coordinates?" = machine-readable positions.

| Source | Type | URL | HTTP | Items | Dates? | Coordinates? | robots.txt | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Western Cape DOI public road closures | ArcGIS FeatureServer (JSON/GeoJSON) | `gis.westerncape.gov.za/server4/rest/services/RoadClosures/Public_Road_Closures/FeatureServer` | 200 | 47 (31 + 12 + 4) | Start on all 47; end on 0 | Yes (lines, plus start/end lon/lat) | 404 (no rules) | RESTRICTED (non-commercial only; written-permission route) |
| Western Cape DOI news | RSS | `westerncape.gov.za/infrastructure/taxonomy/term/175/feed` | 200 | 10 (29 Sep-15 Oct) | Publication only; summary is metadata | No | Allowed | RESTRICTED (same WCG terms) |
| City of Cape Town media releases, tag "road closures" | Site's internal JSON list + HTML articles | `capetown.gov.za/umbraco/surface/RefinerFilterMediaSearchSurface/GetChildrenWithRefinerKeywordsMedia` | 200 | 79 (newest 12 Oct) | Release date; closure dates only in the text | No (named roads) | Allow all | RESTRICTED |
| City of Johannesburg / JMPD media statements | PDFs | `joburg.org.za/media_/Documents/2026-Media-Statements/` | not listed | n/a | In the PDF text | No | 404 (no rules) | RESTRICTED |
| Johannesburg Roads Agency | RSS (WordPress) | `jra.org.za/feed/` | 200 | 10 (newest 17 Dec 2025) | Publication only | No | 404 (no rules) | Not assessed: feed stale |
| City of Tshwane | RSS (WordPress) | `tshwane.gov.za/?feed=rss2` | 200 | 10 (9-16 Oct) | Publication only | No | 404 (no rules) | ASK_PERMISSION (no terms found) |
| eThekwini (Durban) news | HTML list | `durban.gov.za/news` | 200 | 5 a page | Publication only | No | Allow all | ASK_PERMISSION (no reuse terms) |
| City of Ekurhuleni | RSS (WordPress) | `ekurhuleni.gov.za/feed/` | 200 | 10 (9-16 Oct) | Publication only | No | Allow all | ASK_PERMISSION (terms silent on reuse) |
| Nelson Mandela Bay news | HTML list | `nelsonmandelabay.gov.za/news` | 200 | about 10 a page | Publication only | No | none (redirect to 404 page) | RESTRICTED |
| Gauteng Roads and Transport statements (on gov.za) | HTML | `gov.za/gauteng/gauteng-roads-and-transport` (from search) | not fetched | n/a | In the text | No | Allowed | RESTRICTED (gov.za terms) |
| KZN Department of Transport | n/a | `kzntransport.gov.za` | timeout | n/a | n/a | n/a | unreachable | UNREACHABLE |
| SANRAL media centre (traffic advisories) | HTML list | `nra.co.za/media-centre` | 200 | newest press item 23 Apr 2026 | In the text (e.g. "from 30 January to 30 April 2026") | No (km and interchanges named) | Allow all | ASK_PERMISSION (terms page text not readable); stale |
| SANRAL i-TRAFFIC API | REST API | `i-traffic.co.za` | not re-tested | n/a | n/a | n/a | (15 Oct) API allowed | RESTRICTED (key and written consent; unchanged) |
| N3 Toll Concession | RSS (WordPress) | `n3tc.co.za/feed/` | 200 | 21 (30 Jan-22 Sep) | In the text | No | Allow all | RESTRICTED |
| TRAC N4 | RSS (WordPress) | `tracn4.co.za/feed/` | 200 | 10 (5 Dec 2025-21 Sep) | In the text | No | Allowed | ASK_PERMISSION (no terms found) |
| Bakwena N1N4 | RSS (WordPress) | `bakwena.co.za/feed/` | 200 | 10 (27 Aug 2025-20 Jul) | In the text | No | Allowed | RESTRICTED |
| Arrive Alive, "News from Arrive Alive" | RSS | `arrivealive.co.za/rss/rsswritearrivealive.aspx` | 200 | 5 (all 16 Oct) | Publication time; events are live | No (named intersections) | Allow all | ASK_PERMISSION |
| Arrive Alive, "Road Safety in the Media" | RSS | `arrivealive.co.za/rss/rsswriteroadsafetymedia.aspx` | 200 | 5 (2 Apr-30 Jun) | Publication only | No | Allow all | ASK_PERMISSION |
| trafficinformation.co.za | RSS (WordPress) | `trafficinformation.co.za/feed/` | 200 | 10 (6-16 Oct) | Publication only | No | Allowed for `*`; GPTBot, Google-Extended blocked | ASK_PERMISSION |
| KZN COGTA (disaster advisories) | RSS (WordPress) | `kzncogta.gov.za/feed/` | 200 | 10 (1-30 Sep) | In the text | No | Allow all | ASK_PERMISSION (no terms found) |
| SAnews (GCIS) | RSS | `sanews.gov.za/south-africa-news-stories.xml` | 200 | 10 (15 Oct 11:29-16 Oct 08:23 UTC) | Publication; dates in the text | No | Allowed | **PERMITTED** (media use, credit SAnews; see caveat) |
| IOL (includes Cape Argus, Cape Times) | RSS | `iol.co.za/rss/` | 200 | 30 (about 2 hours) | Publication | No | Allowed for `*`; ClaudeBot, GPTBot and others blocked | RESTRICTED |
| Cape Argus (own domain) | RSS | `capeargus.co.za/rss/` | 200 | 1 (12 May 2026) | Publication | No | Allowed for `*`; AI bots blocked | RESTRICTED (stale; IOL terms) |
| TimesLIVE | RSS | `timeslive.co.za/arc/outboundfeeds/rss/category/news/` | 200 | 99 (13-16 Oct) | Publication | No | Allowed for `*`; AI bots blocked | RESTRICTED |
| News24 | RSS | `feeds.capi24.com/v1/Search/articles/news24/SouthAfrica/rss` | 200 | 20 (about 16 hours) | Publication (non-standard date format, no time zone) | No | feeds host: 404 (no rules); news24.com: `*` allowed, AI assistants blocked | ASK_PERMISSION (terms behind Cloudflare challenge) |
| EWN (also 702, CapeTalk news) | none advertised | `ewn.co.za` | 200 (home) | n/a | n/a | n/a | Allowed for `*`; GPTBot, ClaudeBot, CCBot and others blocked | RESTRICTED |
| 702 / CapeTalk / 947 | none | redirect to `primediaplus.com/station/...` | 301 | n/a | n/a | n/a | 404 on primediaplus.com | No news feed (news is on EWN) |
| Jacaranda FM traffic | HTML (audio, X embed) | `jacarandafm.com/news/latestlocaltrafficnewsjacarandafm/` | 200 | n/a | No | No | Allowed | RESTRICTED |
| GroundUp | RSS | `groundup.org.za/sitenews/rss/` | 200 | 15 (13-16 Oct) | Publication | No | Allowed | ASK_PERMISSION (explicit permission needed since 1 April 2026) |
| The Witness (Caxton) | RSS (WordPress) | `witness.co.za/feed/` | 200 | 10 (about 23 minutes) | Publication | No | Allowed for `*`; CCBot blocked | ASK_PERMISSION (site terms not found) |
| The Citizen, Caxton local papers (e.g. Roodepoort Record) | n/a | `citizen.co.za` | 403 on robots.txt (Cloudflare challenge) | n/a | n/a | n/a | unreadable | UNREACHABLE |
| Daily Maverick | n/a | `dailymaverick.co.za` | 403 on robots.txt (Cloudflare challenge) | n/a | n/a | n/a | unreadable | UNREACHABLE |
| SABC News | n/a | `sabcnews.com` | robots.txt redirect loop (https to http to https) | n/a | n/a | n/a | unreadable | UNREACHABLE |

## Western Cape road closures, re-assessed

**Data (unchanged since 15 October).** One query of layers 0, 2 and 3 without
geometry (`.../FeatureServer/query?layerDefs={"0":"1=1","2":"1=1","3":"1=1"}&returnGeometry=false&f=json`):

- 47 closures, 47 unique `closureid`, all `status` = Approved.
- Reasons: Flood Damage 44, Flooding 2, Hazard 1. Districts: Cape Winelands 15,
  Garden Route 12, Central Karoo 9, West Coast 6, Overberg 1, none 4.
- `starttime` on all 47 (25 August to 9 October 2026); `endtime` on none; no
  start in the future. Last edit 9 October 2026 10:51 UTC.
- Location: polyline geometry on every record (shown on 15 October), plus
  `startx`/`starty` on all 47, provincial road number on all 47, `street` on 7,
  free-text `description` on 41.

**Under the new rule:** before 16 October none of the 47 could be shown
(both dates were required). Now all 47 qualify: each has a source start date,
no end date, a confirmed (Approved) status, and coordinates. REI would treat
each as in force until its `closureid` disappears from the layer.

**Licence (unchanged).** The portal search (`gis.westerncape.gov.za/portal/sharing/rest/search?q=road closures`)
lists 15 items, including the FeatureServer, the MapServer, the detours view,
two web maps and two web experiences. Every one has an empty `licenseInfo`. The
WCG terms of use ([westerncape.gov.za/terms-of-use](https://www.westerncape.gov.za/terms-of-use)):

> "Non-commercial: You may reproduce written copyright material (except that belonging to third parties) on the WCG digital channels for non-commercial purposes in any format or media without obtaining permission. … The source must be acknowledged including the URL and copyright status of the material."
>
> "Commercial: Permission to reproduce content for commercial purposes may be granted subject to a written request to service@westerncape.gov.za"

The same page says: "There is no copyright in: Official texts of a
legislative, administrative or legal nature … News of the day, which is a mere
item of press information." Whether a road closures map layer falls under
that is a legal question for the user. It is not a reason to connect without
permission.

**Verdict:** RESTRICTED under REI's standard (free reuse is non-commercial
only). There is a clear permission route. The draft request in
[permissions-and-activation-2026-10-15.md](permissions-and-activation-2026-10-15.md),
section 3.1, still applies. Its question 3 (end dates) matters less now.

**Western Cape DOI news feed** (found this time): `https://www.westerncape.gov.za/infrastructure/taxonomy/term/175/feed`,
valid RSS, 10 items from 29 September to 15 October 2026. The description holds
only the title, author, date and tags, not the article text. Current road
items: "Good progress on Meiringspoort emergency flood-damage repairs" (15 Oct)
and "Good progress on Seven Passes flood-damage repairs" (13 Oct). Same WCG
terms: RESTRICTED. robots.txt allows the path.

## Per-source notes

### Official and authority sources

**City of Cape Town.** robots.txt: `User-agent: *` / `Allow: /`. The media
page (`/media-and-news/`, 1.4 MB) has no RSS link. Its script calls an
internal JSON list, which with the "road closures" tag returns 79 releases
(fields `name`, `url`, `formattedDate`, `truncatedBody`). Newest: "N1 FW De
Klerk Pedestrian Bridge Repairs Ongoing" (12 October 2026) and "Temporary road
closure: N1 from CBD Lower Church Street pedestrian bridge" (11 October 2026).
The 11 October article names the N1 inbound and outbound between the CBD and
the Lower Church Street pedestrian bridge in Woodstock. It gives a release date
but no end date. This JSON list is the site's own internal endpoint, not a
published API. Terms ([capetown.gov.za/general/terms-of-use/](https://www.capetown.gov.za/general/terms-of-use/)):

> "Any redistribution or reproduction of part or all of the contents in any form is prohibited, other than the following: You may print or download to a local hard disk extracts for your personal and non-commercial use only … You may not, except with our express written permission, distribute or commercially exploit the content." Enquiries: cct.webmaster@capetown.gov.za.

Verdict: RESTRICTED.

**City of Johannesburg and JMPD.** robots.txt is 404 (no rules). Media
statements are PDFs under `/media_/Documents/2026-Media-Statements/` (search
found, for example, `ROAD-CLOSURES-AND-TRAFFIC-MANAGEMENT-FOR-THE-JUNE.pdf` and
a Safe Cycling Ride closure in Orange Farm on 22 March 2026). There is no feed;
`/media_/Pages/default.aspx` gives 404. Terms ([joburg.org.za/Pages/Terms-and-Conditions.aspx](https://joburg.org.za/Pages/Terms-and-Conditions.aspx)):

> "… a non-exclusive, non-transferable, limited and revocable right to access, display, use, download and otherwise copy the current and future content of the website for your personal, non-commercial and informational purposes only. … The website and content may not be reproduced, duplicated, copied, resold or otherwise exploited for any commercial purpose without the express, prior written consent of the City."

Verdict: RESTRICTED.

**Johannesburg Roads Agency.** `https://www.jra.org.za/feed/` is valid RSS
with 10 items. The newest is "2025 Signed Audited AFS" (17 December 2025); the
newest road item is from October 2024. The feed is stale, so the terms were not
checked.

**City of Tshwane.** robots.txt is 404. The WordPress feed
`https://www.tshwane.gov.za/?feed=rss2` is valid, with 10 items (9-16
October). They are water and electricity interruptions, news and quotations;
no road events today. The home page links no terms or disclaimer. Verdict:
ASK_PERMISSION. (The e-GIS server `e-gis001.tshwane.gov.za` disallows
everything; see the 15 October research.)

**eThekwini (Durban).** robots.txt: `User-agent: *` / `Disallow:` (empty, so
everything is allowed). `/news` is an HTML list, 5 a page, newest 16 October;
no road items and no feed. The "Terms & Conditions" link leads to the privacy
policy. The [eDisclaimer](https://www.durban.gov.za/page/edisclaimer) covers
e-mail only. The footer says "© Copyright 2025 EThekwini Municipality | All
Rights Reserved". Verdict: ASK_PERMISSION.

**City of Ekurhuleni.** robots.txt (Yoast): everything allowed. `/feed/` and
`/category/press-releases/service-delivery-interruptions/feed/` are valid,
with 10 items each: power, water and quotations, no road events. Terms
([ekurhuleni.gov.za/terms-and-conditions-agreement/](https://www.ekurhuleni.gov.za/terms-and-conditions-agreement/))
say only: "The Site and its original content, features and functionality are
owned by City of Ekurhuleni and are protected by international copyright …".
Nothing on reuse or automated access. Verdict: ASK_PERMISSION.

**Nelson Mandela Bay.** There is no robots.txt (it redirects to a 404 help
page). `/news` is an HTML list. A road item: "Burman Road reopens …"
(14 September 2026). Terms ([nelsonmandelabay.gov.za/page/terms-and-conditions/](https://www.nelsonmandelabay.gov.za/page/terms-and-conditions/)):

> "Users may view, copy, download to a local drive, print and distribute the content of this website or any part thereof for non-commercial, information or reference purposes only. Users who wish to reproduce, duplicate, copy, resell or otherwise use any content from this site for any commercial purpose may only do so if prior written permission has been obtained from the webmaster at webmaster@mandelametro.gov.za"

Verdict: RESTRICTED.

**Gauteng Department of Roads and Transport.** Search finds its statements on
gov.za (for example, R28 and D603 closures), not on a feed. gov.za terms
([gov.za/terms-and-conditions-use](https://www.gov.za/terms-and-conditions-use)):

> "Users may view, copy, download to a local drive, print and distribute the content of this website, or any part thereof only for non-commercial informational or reference purposes. Users who wish to use content from this site for commercial purposes may only do so with the prior written permission obtained from the web manager … electronic@gcis.gov.za"

Verdict: RESTRICTED. The department's own website was not checked.

**KZN Department of Transport.** `https://www.kzntransport.gov.za/robots.txt`:
connection timed out twice (15 s each). Recorded as unreachable. See the access
notes.

**Western Cape Mobility.** It is part of the same `westerncape.gov.za` site
and terms (RESTRICTED). Its pages were not checked separately.

**SANRAL website (nra.co.za).** robots.txt: `User-agent: *` / `Allow: /`. The
media centre is HTML (Press 1,294, Blogs 774) with no feed. The newest press
item is "N3 Key Ridge to Hammarsdale interchange upgrade: N3 southbound
carriageway shift to contraflow" (23 April 2026), so nothing has been posted
for almost six months. Advisories carry dates and named places (search
example: R21 Olifantsfontein, fast lanes closed "from 30 January to 30 April
2026"). The [terms page](https://www.nra.co.za/terms-conditions) is built by a
script; the static HTML holds only the heading, so the terms were not read.
Verdict: ASK_PERMISSION (and stale). **i-TRAFFIC** is unchanged from 15
October (key plus SANRAL's written consent). It was not re-tested.

**N3 Toll Concession.** robots.txt allows everything. `https://www.n3tc.co.za/feed/`
is valid, with 21 items from 30 January to 22 September 2026 and summaries.
Current road items: "Travel Advisory | Busy traffic conditions expected as
Heritage Day long weekend and school holidays commence" (22 September) and
"Traffic Update | The N3 Toll Route remains open despite severe weather
conditions" (12 August). Terms ([n3tc.co.za/disclaimer-and-tcs/](https://www.n3tc.co.za/disclaimer-and-tcs/)):

> "Any text, images, graphics, sound files, animation files, video files, etc. and their arrangement on this Website are subject to copyright and other intellectual property protection. These objects may not be copied for commercial use or distribution, nor may these objects be modified or reposted to other sites."

Verdict: RESTRICTED.

**TRAC N4.** robots.txt allows the feed. `https://tracn4.co.za/feed/` is
valid, with 10 items from 5 December 2025 to 21 September 2026. Road-related
item: "TRACN4 Rally returns to Dullstroom …" (rally on 30 and 31 October 2026;
no closures stated). The site has no traffic page, and its "Cookie Policy" and
"Privacy Policy" links point to `#`. No terms were found. Verdict:
ASK_PERMISSION (low road-event yield).

**Bakwena N1N4.** robots.txt allows the feed. `https://www.bakwena.co.za/feed/`
is valid, with 10 items from 27 August 2025 to 20 July 2026 (project updates,
for example "Bakwena achieves another key milestone on the N4 dualling
project", 20 July). Terms ([bakwena.co.za/terms-and-conditions/](https://www.bakwena.co.za/terms-and-conditions/)):

> "Bakwena hereby grants to the user a personal, non-exclusive right to use and display all content … The user shall not copy any of the content or software on the site nor shall the user reproduce, redistribute, retransmit, publish or otherwise transfer or exploit any information … without first obtaining Bakwena's consent."

Verdict: RESTRICTED.

**Arrive Alive.** robots.txt: `User-Agent: *` / `Allow: /`, with only static
asset folders disallowed. The feeds are listed on `/rsssubscribe.aspx`; the
mixed-case URLs redirect to lowercase.

- `https://www.arrivealive.co.za/rss/rsswritearrivealive.aspx` ("News from
  Arrive Alive"): valid RSS, **5 items, all from 16 October 2026** (07:58 to
  12:00 SAST), with summaries. Current road events: "An active SADTU march is
  currently approaching the intersection of Dr Pixley kaSeme Street and Brook
  Street" ("Motorists using Dr Pixley kaSeme Street should expect traffic
  delays") and "Road crash at the intersection of Clark Avenue and Moore Road,
  Durban". With only 5 items, the feed would need polling about every 30
  minutes.
- `https://www.arrivealive.co.za/rss/rsswriteroadsafetymedia.aspx`: 5 items,
  2 April to 30 June 2026 (for example "Major protest action brings the N2 to
  a standstill in the Eastern Cape", 27 May).
- Terms: the [disclaimer](https://www.arrivealive.co.za/disclaimer) covers
  liability and e-mail only, then "All rights reserved." It says nothing on
  reuse or automated access. Many items repeat other organisations' alerts
  (Durban Metro Police, N3TC, emergency services), so Arrive Alive may not hold
  the rights to all of them.

Verdict: ASK_PERMISSION. The site is "a private initiative" of Johan Jonck,
who also maintains trafficinformation.co.za, so one request could cover both.

**trafficinformation.co.za.** robots.txt allows `/feed/` for `*`; it blocks
AdsBot, Google-Extended, GPTBot and CCBot. `https://www.trafficinformation.co.za/feed/`
is valid, with 10 items from 6 to 16 October, mostly crime notices. One road
event: "Stockville Protests: The road remains closed due to ongoing protests"
(12 October; the item also mentions an M1 West collision at Clairwood
Hospital). No terms page was found; the footer says it is "maintained by Johan
Jonck". Verdict: ASK_PERMISSION.

**KZN COGTA (disaster management).** robots.txt allows everything.
`https://www.kzncogta.gov.za/feed/` is valid, with 10 items from 1 to 30
September. One weather item ("Disaster teams remain on high alert as rain
continues across the province"). Search found a 10 August 2026 advisory that
the R617 between Underberg and Kokstad was closed by snow. The site has only a
privacy-policy link and "Copyright © 2025 The Department of Cooperative
Governance and Traditional Affairs". Verdict: ASK_PERMISSION (low yield).

**SAnews (South African Government News Agency, GCIS).** robots.txt is the
Drupal default; the feed paths are allowed. The feeds are linked in the footer:
`/south-africa-news-stories.xml` and `/features.xml` (the home page also
declares `/rss-old.xml`, not fetched). `https://www.sanews.gov.za/south-africa-news-stories.xml`
is valid RSS with 10 items from 15 October 11:29 to 16 October 08:23 UTC, each
with full article text (1,000 to 10,000 characters). No road items today.
Search shows 2026 road-closure articles such as "Road closures: State of the
Nation Address", "Road closures ahead of the Cape Town Cycle Tour", "SANRAL
warns of road closures in Durban at uMngeni Interchange", "Temporary lane
closures on the R21" and "JMPD warns of major traffic on 30 June". These come
from search results; they were not fetched. User policy ([sanews.gov.za/content/user-policy](https://www.sanews.gov.za/content/user-policy)):

> "All media are welcome to utilise SA Government News Agency's content and credit such use to SAnews.gov.za."
>
> "Media are welcome to utilise all stories, pictures and other material on this site, as well as from our Facebook and X accounts, at no cost, provided SAnews is credited."

Verdict: PERMITTED, with a caveat. The grant is addressed to "media". REI is
a commercial road-event service, not a news outlet, and GCIS's other site
(gov.za) requires written permission for commercial use. A one-line
confirmation from newsfiles@gcis.gov.za would remove the doubt. There are no
prohibitions on automated access or storage.

### News feeds

**IOL (Independent Media; carries Cape Argus and Cape Times).** robots.txt
allows `/rss/` for `*`. It blocks Amazonbot, anthropic-ai, ChatGPT-User,
ClaudeBot, Claude-Web, GPTBot, cohere-ai, Bytespider, Diffbot and others.
`https://iol.co.za/rss/` (redirected from `/rss`) is valid, with 30 items
covering about 2 hours and summaries. Current road events: "Nelson Mandela
Marathon: What Cape Town runners and motorists need to know" ("takes place on
Sunday, 18 October 2026 … planned road closures and MyCiTi transport
information"). No second one. `capeargus.co.za/rss/` has a single item from 12
May 2026. Terms ([iol.co.za/iol-terms-and-conditions/](https://iol.co.za/iol-terms-and-conditions/)):

> "27. The website owner offers a service whereby headlines featured on the website may be displayed on a website using RSS Feeds under an implied license. This service is available at no cost for non-commercial use. 28. Licences for commercial use of this service will be negotiated by the website owner on application."
>
> "51. The use of search technology in an unlawful manner or for the collecting or harvesting of data for commercial gain is prohibited."

Verdict: RESTRICTED (a commercial RSS licence can be negotiated).

**TimesLIVE (Arena Holdings).** robots.txt allows `*` and blocks GPTBot,
ClaudeBot, anthropic-ai, Google-Extended, CCBot and others. The feeds are
listed at [timeslive.co.za/information/rss-feeds/](https://www.timeslive.co.za/information/rss-feeds/).
`https://www.timeslive.co.za/arc/outboundfeeds/rss/category/news/` is valid,
with 99 items from 13 to 16 October and summaries. No road events today. Terms
([timeslive.co.za/information/terms-and-conditions/](https://www.timeslive.co.za/information/terms-and-conditions/)):

> "5.2 … You may not, without Arena's prior written consent: 5.2.1 reproduce, publish, perform, broadcast, adapt, sell, lease, offer, make available, transfer, or otherwise use any content for commercial purposes; … 5.2.3 incorporate the content, in whole or in part, into any other work or content for any purpose"

Verdict: RESTRICTED.

**News24 (Media24).** The home page links `feeds.24.com/articles/news24/topstories/rss`.
The tested feed `https://feeds.capi24.com/v1/Search/articles/news24/SouthAfrica/rss`
is valid, with 20 items from 15 October 17:54 to 16 October 09:30 and summaries.
Dates are written like "Friday Oct 16 2026 09:30:45", with no time zone. No
road events today. robots.txt for `www.news24.com` allows `*` and blocks
Claude-User, ChatGPT-User, GPTBot, CCBot and others. The terms are at
`https://www.24.com/terms-and-conditions/`, but that host answered both
robots.txt and the terms page with a Cloudflare challenge (403), so they could
not be read. Verdict: ASK_PERMISSION (terms unreadable).

**EWN (Primedia Broadcasting; also the news for 702 and CapeTalk).** robots.txt
("Updated April 2026") allows `*` and disallows GPTBot, ClaudeBot,
Google-Extended, CCBot, Meta-ExternalAgent and Applebot-Extended. The home
page advertises no RSS feed, and no feed URL was guessed. Terms ([ewn.co.za/ewn-terms-and-conditions](https://www.ewn.co.za/ewn-terms-and-conditions)):

> "Primedia Broadcasting authorises you to view, copy, download to a local drive, print and distribute the content of this web site, or parts thereof, provided that: Such content is used for information purposes only; Such content is used for non-commercial purposes … You are expressly prohibited from incorporating any of the material from this web site in any other work, publication or web site of your own or belonging to another."

Verdict: RESTRICTED. `702.co.za`, `capetalk.co.za` and `947.co.za` now
redirect to `primediaplus.com/station/...`, Primedia's advertising sales site
(a script-only page); it has no news or traffic feed.

**Jacaranda FM (Kagiso Media).** robots.txt disallows only `/search/*`. The
traffic page has audio updates and an embedded X timeline (`@jaca_traffic`),
no list and no feed. Terms ([jacarandafm.com/terms-of-use/](https://www.jacarandafm.com/terms-of-use/)):

> "2.2 Any person accessing this website may save for downloading one copy for their personal computers and solely for their private and non-commercial use, but may not copy, disseminate, distribute, advertise, publish, adapt, modify or in any way reproduce the contents of this website for commercial purposes, unless the permission of the Company is obtained in writing."

Verdict: RESTRICTED.

**GroundUp.** `www.groundup.org.za` redirects to `groundup.org.za`. robots.txt
disallows only admin and preview paths. `https://groundup.org.za/sitenews/rss/`
is valid, with 15 items from 13 to 16 October; no road events. Licence ([groundup.org.za/licence-change/](https://groundup.org.za/licence-change/)):

> "From 1 April 2026, GroundUp will publish most of our articles under a new licence, which we are calling the GroundUp Republication Licence. … under the new licence terms our articles will only be available for republication with our explicitly granted permission."
>
> "Generally we will grant such permission to any legitimate news publication that — if it is primarily aimed at a South African audience — is a member of the South African Press Council."

Older articles stay under Creative Commons. Verdict: ASK_PERMISSION (new
articles need explicit permission; REI is unlikely to qualify as a "news
publication").

**The Witness (now a Caxton title).** robots.txt allows `/feed/` for `*` and
blocks CCBot and several SEO crawlers. `https://witness.co.za/feed/` is valid,
with 10 items covering about 23 minutes, so it would need very frequent
polling. No road events in today's items. Search shows daily "Live traffic
updates: PMB, Midlands and KZN" articles up to at least 28 July 2026, mostly
quoting i-traffic KZN (SANRAL, RESTRICTED). The only terms found
([witness.co.za/ts-cs/](https://witness.co.za/ts-cs/)) are for competitions;
Caxton's group terms would be on citizen.co.za, which is unreadable. Verdict:
ASK_PERMISSION.

**The Citizen and Caxton local papers (Roodepoort Record and others under
`citizen.co.za/...`).** `https://www.citizen.co.za/robots.txt` answered 403
with a Cloudflare challenge ("Just a moment…", `Cf-Mitigated: challenge`).
Nothing else was requested. Unreachable for REI.

**Daily Maverick.** The same Cloudflare challenge on robots.txt. Nothing else
was requested. Unreachable for REI.

**SABC News.** `https://www.sabcnews.com/robots.txt` redirected to
`http://www.sabcnews.com/robots.txt`, which redirected back to
`https://www.sabcnews.com:443/robots.txt`: a loop. robots.txt could not be
read, so nothing else was requested. Unreachable for REI.

## What REI can connect today

1. **SAnews South Africa feed (PERMITTED, with a caveat).** It is the only
   source that passes REI's standard. It would run on the generic RSS
   connector, polled about hourly (10 items cover about a day). It is text
   only: locations from named places (OpenStreetMap) and dates from explicit
   wording, under the existing rules. Expect a few road items a month, not a
   steady stream. Before commercial launch, ask newsfiles@gcis.gov.za to confirm
   that the media-use grant covers REI.
2. **Nothing with coordinates can be connected without permission.** The
   Western Cape layer is the only machine-readable, located source, and the
   new rule makes all 47 of its closures showable. The single most useful
   step for South Africa is sending the drafted request to
   service@westerncape.gov.za (cc PDO@westerncape.gov.za).
3. **Worth asking next:** Johan Jonck for Arrive Alive and
   trafficinformation.co.za (live KZN/Durban alerts, one owner), then IOL's
   commercial RSS licence (Cape Town and national coverage, including event
   closures such as the Nelson Mandela Marathon on 18 October). SANRAL
   i-TRAFFIC remains the only path to national-road events.

## Not verified

- Whether the Western Cape `starttime` is the real closure start or the time
  the record was entered; whether reopened roads get an `endtime` or are
  deleted.
- Whether the "no copyright in official texts of an administrative nature"
  clause in the WCG terms covers the closures layer (a legal question).
- Whether SAnews's grant to "media" extends to a commercial service such as
  REI; how often SAnews carries road closures (from search results, not
  counted).
- Site-wide terms of News24/Media24 (Cloudflare), Caxton (The Citizen,
  The Witness, Roodepoort Record), Daily Maverick and SABC; Cape Times
  separately from IOL.
- Whether EWN has an unadvertised RSS feed (not guessed).
- SANRAL website terms (the page builds its text with a script); Tshwane terms
  (none linked); JRA terms (not checked, as the feed is stale).
- Gauteng Department of Roads and Transport's own site, Western Cape Mobility
  pages, MyCiTi service notices (City of Cape Town terms would apply),
  event organisers (for example the Sanlam Cape Town Marathon and Nelson
  Mandela Marathon sites), and KZN Department of Transport (unreachable).
- The City of Cape Town Open Data Portal and other ArcGIS portals were not
  re-searched; on 15 October they had no closures layer.
- Whether Arrive Alive holds the rights to the third-party alerts it reposts.
- i-TRAFFIC was not re-tested.

## Access-rule notes

- 125 requests to 39 hosts; the most to one host was 9 (`www.arrivealive.co.za`,
  three of them redirects to lowercase URLs). Each redirect was a separate,
  counted request.
- **KZN Department of Transport:** after robots.txt timed out twice, the same
  command also tried the home page twice (both connection timeouts, nothing
  received). Under the rule it should have stopped after the robots.txt
  timeouts.
- **www.24.com:** robots.txt returned a Cloudflare challenge (403), and the
  same command then requested the terms page once (also a challenge, nothing
  read). It should have stopped after the robots.txt answer.
- **City of Cape Town:** the "road closures" list came from the JSON endpoint
  that the City's own media page calls (robots.txt allows everything). It is
  not a published API.
- No AI-crawler user agent was used. REI's agent name is not listed in any
  robots.txt seen; several publishers block ClaudeBot, GPTBot and similar AI
  agents, which matters if article text would be sent to a model.
- Raw responses are in the session scratchpad (`za/data/`), not in the
  repository.
