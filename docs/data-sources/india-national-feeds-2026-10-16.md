# National and multi-city Indian news feeds: research, 16 October 2026

Scope: national or multi-city publishers with city sections for Delhi (NCR),
Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, Pune and Ahmedabad. Research
only; nothing was connected.

Not re-researched (already decided): siasat.com, thehindu.com,
deccanchronicle.com, thehansindia.com, mid-day.com, telanganatoday.com,
newsmeter.in.

**Method.** All fetches were server-side (no JavaScript) on 16 October 2026,
09:50 to 10:08 UTC, with the User-Agent
`JSAN-REI/1.0 (road event intelligence research)`. A small fetcher enforced
the rules: robots.txt first on every host; every later path checked against
the `*` group (longest match, wildcards); at most 10 requests per host;
requests to one host one at a time with at least 2.5 s between them; no
browser user agent, logins, paywalls or proxies. Different hosts were fetched
in parallel. 163 requests in total. Feed URLs came from each publisher's own
RSS page, section page `<link rel="alternate">`, or the site's own redirect
table (New Indian Express). Web search was tried once for terms URLs and gave
nothing usable. Terms pages were read from the server HTML. Quotes are
verbatim; "[...]" marks a cut.

**Verdict standard.**
- RESTRICTED: the terms limit use to personal or non-commercial use; or forbid
  automated access, scraping, crawling, data mining, or storing in a retrieval
  system; or limit RSS to personal feed readers; or robots.txt disallows the
  feed.
- ASK_PERMISSION: no terms page found, or the terms say nothing on these
  points.
- PERMITTED: the terms explicitly allow this kind of use.

No publisher was PERMITTED.

## Summary table

"Items" gives the count and the newest item date (UTC). "Has summary": `desc`
is the RSS `description`, `body` is `content:encoded`; "full text" means the
body averages 1,700 characters or more. "Robots" is the `*` group's answer for
the feed path.

| Publisher | City | Feed URL | HTTP | Items (newest) | Has summary | Robots | Terms verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Times of India | Delhi | https://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms | 200 | 20 (16 Oct 08:24) | desc 8/20, avg 398 ch; no body | Allowed | RESTRICTED |
| Times of India | Mumbai | https://timesofindia.indiatimes.com/rssfeeds/-2128838597.cms | 200 | 20 (16 Oct 07:07) | desc 8/20, avg 433 ch | Allowed | RESTRICTED |
| Times of India | Kolkata | https://timesofindia.indiatimes.com/rssfeeds/-2128830821.cms | 200 | 20 (16 Oct 01:48) | desc 3/20, avg 300 ch | Allowed | RESTRICTED |
| Times of India | Chennai | https://timesofindia.indiatimes.com/rssfeeds/2950623.cms | 200 | 20 (16 Oct 09:04) | desc 6/20, avg 210 ch | Allowed | RESTRICTED |
| Times of India | Bengaluru | https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms | 200 | 20 (16 Oct 03:25) | desc 2/20, avg 465 ch | Allowed | RESTRICTED |
| Times of India | Hyderabad | https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms | 200 | 20 (16 Oct 06:48) | desc 2/20, avg 438 ch | Allowed | RESTRICTED |
| Times of India | Pune | https://timesofindia.indiatimes.com/rssfeeds/-2128821991.cms | 200 | 20 (15 Oct 19:09) | desc 1/20 | Allowed | RESTRICTED |
| Times of India | Ahmedabad | https://timesofindia.indiatimes.com/rssfeeds/-2128821153.cms | 200 | 20 (15 Oct 18:43) | desc 1/20, 78 ch | Allowed | RESTRICTED |
| Hindustan Times | Delhi | https://www.hindustantimes.com/feeds/rss/cities/delhi-news/rssfeed.xml | 200 | 36 (16 Oct 06:43) | desc 36/36, avg 164 ch; no body | Allowed | RESTRICTED |
| Hindustan Times | Mumbai | https://www.hindustantimes.com/feeds/rss/cities/mumbai-news/rssfeed.xml | 200 | 49 (16 Oct 06:33) | desc all, avg 188 ch | Allowed | RESTRICTED |
| Hindustan Times | Kolkata | https://www.hindustantimes.com/feeds/rss/cities/kolkata-news/rssfeed.xml | 200 | 5 (16 Oct 05:10) | desc all, avg 104 ch | Allowed | RESTRICTED |
| Hindustan Times | Bengaluru | https://www.hindustantimes.com/feeds/rss/cities/bengaluru-news/rssfeed.xml | 200 | 2 (16 Oct 03:49) | desc all, avg 121 ch | Allowed | RESTRICTED |
| Hindustan Times | Pune | https://www.hindustantimes.com/feeds/rss/cities/pune-news/rssfeed.xml | 200 | 28 (16 Oct 02:19) | desc all, avg 159 ch | Allowed | RESTRICTED |
| Hindustan Times | Hyderabad | https://www.hindustantimes.com/feeds/rss/cities/hyderabad-news/rssfeed.xml | 200 | **0** (empty channel, title "null") | — | Allowed | RESTRICTED |
| Indian Express | Delhi | https://indianexpress.com/section/cities/delhi/feed/ | 200 | 200 (16 Oct 08:24) | **none** (empty `description`, empty `content:encoded`) | Allowed | RESTRICTED |
| Indian Express | Mumbai | https://indianexpress.com/section/cities/mumbai/feed/ | 200 | 200 (16 Oct 08:53) | none | Allowed | RESTRICTED |
| Indian Express | Kolkata | https://indianexpress.com/section/cities/kolkata/feed/ | 200 | 200 (16 Oct 07:01) | none | Allowed | RESTRICTED |
| Indian Express | Chennai | https://indianexpress.com/section/cities/chennai/feed/ | 200 | 200 (11 Oct 00:05; reaches back to 2024) | none | Allowed | RESTRICTED |
| Indian Express | Bengaluru | https://indianexpress.com/section/cities/bangalore/feed/ | 200 | 200 (16 Oct 05:33) | none | Allowed | RESTRICTED |
| Indian Express | Pune | https://indianexpress.com/section/cities/pune/feed/ | 200 | 200 (16 Oct 07:12) | none | Allowed | RESTRICTED |
| Indian Express | Ahmedabad | https://indianexpress.com/section/cities/ahmedabad/feed/ | 200 | 200 (16 Oct 09:35) | none | Allowed | RESTRICTED |
| New Indian Express | Chennai | https://www.newindianexpress.com/api/v1/collections/chennai-cities.rss | 200 | 40 (16 Oct 02:58) | full text, avg 2,416 ch | Allowed | ASK_PERMISSION |
| New Indian Express | Bengaluru | https://www.newindianexpress.com/api/v1/collections/bengaluru-cities.rss | 200 | 40 (16 Oct 02:14) | full text, avg 2,246 ch | Allowed | ASK_PERMISSION |
| New Indian Express | Hyderabad | https://www.newindianexpress.com/api/v1/collections/hyderabad-cities.rss | 200 | 40 (15 Oct 04:04) | full text, avg 2,424 ch | Allowed | ASK_PERMISSION |
| New Indian Express | Delhi | https://www.newindianexpress.com/stories.rss?section=delhi | 200 | 1 (16 Oct 08:38) | full text, 3,572 ch | Allowed | ASK_PERMISSION |
| New Indian Express | Chennai / Bengaluru / Hyderabad | `stories.rss?section=chennai` / `=bengaluru` / `=hyderabad` | 200 | **0** | — | Allowed | ASK_PERMISSION |
| Deccan Herald | (site-wide; no city feed) | https://www.deccanherald.com/stories.rss | 200 | 49 (16 Oct 09:45) | full text, avg 3,471 ch | Allowed | RESTRICTED |
| Free Press Journal | Mumbai | https://www.freepressjournal.in/api/v1/collections/mumbai.rss | 200 | 40 (16 Oct 08:51) | full text, avg 2,957 ch | Allowed (`/*/feed` disallowed) | RESTRICTED |
| Free Press Journal | Pune | https://www.freepressjournal.in/api/v1/collections/pune.rss | 200 | 40 (16 Oct 09:50) | full text, avg 2,430 ch | Allowed | RESTRICTED |
| Free Press Journal | Mumbai / Pune / Delhi | `stories.rss?section=mumbai` / `=pune` / `=delhi` | 200 | about 104 (filter ignored: site-wide feed) | full text | Allowed | RESTRICTED |
| ABP Live | Delhi NCR | https://news.abplive.com/states/delhi-ncr/feed | 200 | 10 (16 Oct 08:27) | desc = full text, avg 3,076 ch | Allowed | RESTRICTED |
| ABP Live | Cities (mixed, mostly Delhi) | https://news.abplive.com/cities/feed | 200 | 10 (16 Oct 08:27) | desc = full text, avg 3,979 ch | Allowed | RESTRICTED |
| Times Now | Delhi | https://www.timesnownews.com/feeds/gns-en-delhi.xml | 200 | 50 (16 Oct 10:00) | desc avg 169 ch + body avg 2,754 ch | Allowed | RESTRICTED |
| Times Now | Mumbai | https://www.timesnownews.com/feeds/gns-en-mumbai.xml | 200 | 50 (16 Oct 03:43) | desc + body avg 2,362 ch | Allowed | RESTRICTED |
| Times Now | Kolkata | https://www.timesnownews.com/feeds/gns-en-kolkata.xml | 200 | 50 (14 Oct 17:54) | desc + body avg 2,610 ch | Allowed | RESTRICTED |
| Times Now | Bengaluru | https://www.timesnownews.com/feeds/gns-en-bengaluru.xml | 200 | 50 (16 Oct 09:59) | desc + body avg 2,193 ch | Allowed | RESTRICTED |
| Times Now | Hyderabad | https://www.timesnownews.com/feeds/gns-en-hyderabad.xml | 200 | 50 (13 Oct 07:32) | desc + body avg 1,971 ch | Allowed | RESTRICTED |
| Times Now | Chennai | https://www.timesnownews.com/feeds/gns-en-chennai.xml | 200 | 50 (14 Oct 05:39) | desc + body avg 2,223 ch | Allowed | RESTRICTED |
| Times Now | Pune / Ahmedabad | `.../feeds/gns-en-pune.xml`, `.../gns-en-ahmedabad.xml` | not fetched (budget) | — | — | Allowed | RESTRICTED |
| Millennium Post | Delhi | https://www.millenniumpost.in/category/delhi/google_feeds.xml | 200 | 23 (16 Oct 05:21) | full text, avg 1,853 ch | Allowed | ASK_PERMISSION |
| Millennium Post | Kolkata (Bengal section) | https://www.millenniumpost.in/category/bengal/google_feeds.xml | 200 | 29 (15 Oct 19:20) | full text, avg 1,740 ch; desc 10/29 | Allowed | ASK_PERMISSION |
| The South First | Hyderabad / Bengaluru / Chennai (site-wide; no city feed) | https://thesouthfirst.com/feed/ | 200 | 10 (16 Oct 08:56) | desc avg 340 ch + full text avg 5,716 ch | Allowed | ASK_PERMISSION |
| The Federal | (site-wide; no metro feed) | https://thefederal.com/google_feeds.xml | 200 | 60 (16 Oct 10:03) | desc 59/60, avg 174 ch | Allowed | RESTRICTED |
| Bangalore Mirror | Bengaluru | https://bangaloremirror.indiatimes.com/rssfeed.cms | 200 | 15 (16 Oct 00:30, print batch) | desc all, avg 413 ch | Allowed | RESTRICTED |
| NDTV (FeedBurner) | Cities (mixed) | https://feeds.feedburner.com/ndtvnews-cities-news | 200 | 20 (16 Oct 03:00) | desc avg 156 ch | ndtv.com robots.txt **403** | Not reachable (terms unreadable) |
| News18 | — | no city feed (RSS page lists 19 topic feeds only) | — | — | — | Allowed | RESTRICTED |
| India Today | — | no city feed (RSS page lists 16 section feeds only) | — | — | — | Allowed | RESTRICTED |
| Moneycontrol | — | no city feed (RSS list page answers 410) | 410 | — | — | Allowed | RESTRICTED |
| Lokmat Times | — | no feed found | — | — | — | Allowed | RESTRICTED |
| ThePrint | — | `/feed/` redirects to the home page; no city sections | 301 | — | — | Allowed | RESTRICTED |
| Mumbai Mirror | — | no feed (`/rss`, `/feed` 404; no feed link) | 404 | — | — | Allowed | Terms unreadable (bccl.in robots.txt 403) |
| Ahmedabad Mirror | — | no feed (`/rss`, `/feed` 404; no feed link) | 404 | — | — | Allowed (empty `Disallow`) | ASK_PERMISSION (nothing to connect) |
| DNA India, Zee News, Telegraph India, The Week | — | — | robots.txt **403** "Access Denied" | — | — | Unreadable | Not reachable |
| The Statesman | — | — | robots.txt 200; home page **403** | — | — | Allowed | Not reachable |
| Pune Mirror | — | — | connection reset (punemirror.com and www) | — | — | Unreadable | Not reachable |

## Per-publisher notes

Unless stated otherwise, terms pages were read on 16 October 2026.

### The Times of India (Times Internet Ltd)

- **Robots** (`timesofindia.indiatimes.com/robots.txt`): `*` allows `/`. It
  disallows `/feeds/`, `*rssarticleshow*` and `/topic/...`, but not
  `/rssfeeds/` or `/city/.../articleshow/`. Of the AI crawlers, only
  `meta-externalagent` is blocked.
- **Feeds:** seven city feed IDs come from rss.cms. Ahmedabad is not listed
  there; its ID (`-2128821153`) came from memory, and the feed answered with
  the title "Ahmedabad News, Latest Ahmedabad News Headlines & Live Updates -
  Times of India".
- **Terms** (RSS page, https://timesofindia.indiatimes.com/rss.cms):
  - "TOI grants you permission to only access and make personal use of its
    RSS feeds and you agree not to, directly or indirectly, download, modify,
    alter, change, amend, vary, transform, revise, translate, copy, publish,
    distribute or otherwise disseminate these RSS feeds, or any portion of
    these [...] except with the express consent of Times Internet Ltd (TIL)."
  - "TIL forbids you from any attempts at displaying, hosting, aggregating,
    reselling or putting to commercial use either directly or indirectly TIL's
    RSS feeds or any part of the same."
  - "You must not retain any copies of these pages saved to disk or to any
    other storage medium except for the purposes of using the same for your
    individual/personal use".
- **Article page:** not fetched today (the 10-request budget went on the RSS
  page and the 8 feeds). On 8 October, article text was readable server-side.
- **Road events in feeds today:** "CJP protest today: Delhi Police issues
  traffic advisory, Central Park shut for 2 days; check diversions, affected
  routes" (Delhi, 16 Oct 02:14 UTC). "India vs WI T20: Check parking
  restrictions, traffic curbs around Chinnaswamy stadium" (Bengaluru, 16 Oct
  03:25).
- **Verdict: RESTRICTED** (RSS for personal use only; commercial use and
  aggregation forbidden; storage forbidden).

### Hindustan Times (HT Digital Streams)

- **Robots:** `*` allows `/`. It disallows `/intfeeds/` but not `/feeds/rss/`.
  No AI crawler is blocked; Google-Extended is grouped with `*`. The file
  starts with a byte-order mark.
- **City feeds** (from https://www.hindustantimes.com/rss): Delhi, Mumbai,
  Kolkata, Bengaluru and Pune, plus Noida and Gurugram. There is none for
  Chennai, Hyderabad or Ahmedabad; the Hyderabad URL used on 8 October is
  still an empty channel.
- **Terms** (https://www.hindustantimes.com/termsofuse):
  - "These terms apply to Hindustan Times , LiveMint , Live Hindustan , and
    their mobile apps, emails/newsletters, APIs, widgets, RSS feeds, and any
    online service we operate".
  - "You may view and share content for personal, non-commercial use."
  - Under the heading "7A) Automated access; bots, crawlers & AI/ML":
    "Except for public search engines creating searchable indices in line
    with robots.txt, you must not use robots, spiders, crawlers, scrapers, or
    similar tools to access, copy, cache, archive, or index the Services."
  - "You must not use our content or metadata to train, fine-tune, evaluate,
    benchmark, or improve AI/ML systems without a written license."
  - "Automated scraping/crawling/bulk downloading is prohibited."
  - "You may not reproduce, republish, or distribute our material for
    commercial gain without explicit written permission."
  - "Separate terms may apply to the use of our APIs, data feeds, widgets, and
    embeds."
- **Article page:**
  https://www.hindustantimes.com/cities/delhi-news/ndmc-closes-central-park-for-administrative-reasons-delhi-101792088854415.html
  answered 200. The text is in the HTML: JSON-LD `articleBody` of 3,194
  characters.
- **Road events:** "NDMC closes Central Park for 'administrative' reasons"
  (Delhi, 15 Oct). "Mumbai: Reconstructed Sion railway bridge to open for
  traffic soon" (15 Oct). "NH-48 traffic restored over 30 hours after calling
  off protest at Kognoli toll plaza" (Pune, 15 Oct).
- **Verdict: RESTRICTED.**

### The Indian Express (IE Online Media Services)

- **Robots:** `*` allows `/section/cities/*/feed/` and `/article/`. The file
  blocks many AI crawlers: ClaudeBot, Claude-Web, anthropic-ai, PerplexityBot,
  meta-externalagent, Bytespider, Applebot-Extended, cohere-ai, Diffbot,
  Omgili, img2dataset, Timpibot and others.
- **Feeds:** every one has an empty `description` and an empty
  `content:encoded` (`<![CDATA[]]>`), so items are titles only, as on 8
  October. The Chennai feed is stale: the newest item is 11 October, and the
  feed reaches back to 2024.
- **Terms** (https://indianexpress.com/terms-and-conditions/; the
  `/terms-of-use/` URL gave 404 on 8 October):
  - "That if you access any of our other digital products not limited to RDF
    Site Summary (RSS) fees, APIs and Software, you agree to abide by all the
    Terms & Conditions contained herein."
  - "[...] a personal, limited, non-exclusive, non-transferable, freely
    revocable license to use the Services for the personal and non-commercial
    use only."
  - "You may not (whether directly or through the use of any software
    program) create a database in electronic and/or structured manual form by
    regularly or systematically downloading and storing all or any part of the
    pages from the Sites or e-papers."
  - "[...] nor included in any public or private electronic retrieval system
    or services without our prior written permission and upon payment of
    requisite fees".
  - "Use automated tools, bots, crawlers, scrapers, or similar technologies
    including and not limited to data mining, robot, spider, or other
    automated means, to access, extract, download, store or index any portion
    of the Content."
  - "Use the content for AI training, summarization, and/or commercial
    purposes."
  - "[...] access, we may require a per-crawl fee and/or licensing
    agreement."
- **Article page:** not fetched today (budget). On 8 October the JSON-LD
  `articleBody` was present.
- **Road events:** "CJP Tiranga march today: Traffic curbs likely in
  Connaught Place from 3 pm" (Delhi, 16 Oct 05:35). "Road closures,
  diversions, one-way grids: Kolkata's Durga Puja traffic curbs" (5 Oct).
  "Mumbai-Bengaluru highway hit by Karnataka protest: Travellers told to avoid
  NH-48" (Pune, 14 Oct).
- **Verdict: RESTRICTED.**

### The New Indian Express (Express Network Pvt Ltd, ENPL)

- **Robots:** the whole file is `User-agent: *` / `Allow: /`.
- **Feeds:** the Quintype `stories.rss?section=<city>` filter is still empty
  for Chennai, Bengaluru and Hyderabad. It gave 1 item for Delhi. The site's
  own redirect table, embedded in its pages, maps `/:param1/:param2/rssfeed`
  to `/api/v1/collections/:param2-:param1.rss`, so `/cities/chennai/rssfeed`
  becomes `/api/v1/collections/chennai-cities.rss`. Those collection feeds
  work, with 40 items each and full article text.
- **City sections:** chennai, bengaluru, hyderabad, delhi, mumbai, kolkata,
  kochi and thiruvananthapuram. The Delhi, Mumbai and Kolkata collection
  feeds were not tested (budget).
- **Terms** (https://www.newindianexpress.com/terms-of-use): the page is
  titled "Terms Of Use", but its server-rendered text is a privacy notice. It
  begins: "ENPL respects the privacy of its users and is committed to
  protecting it in all respects." It also says: "Our web servers
  automatically collect limited information about your computer's connection
  to the Internet, including your IP address". It ends: "Copyright -
  newindianexpress.com 2026. All rights reserved." Nothing in the page, or in
  its embedded JSON, covers personal or commercial use, automated access,
  RSS, storage or AI.
- **Caution:** the 14 October summary
  (`source-research-2026-10-14.md`) lists the New Indian Express among
  publishers that restrict automated or commercial use, but records no quote
  or URL. Today's terms page does not support that. Get written permission
  from ENPL before connecting.
- **Article page:** not fetched (budget). The collection feeds carry full
  text in `content:encoded`.
- **Road events:** "PM Modi visit: Traffic to be diverted in Chennai today"
  (11 Oct). "GBA chief pushes officials to commence Jalahalli Cross underpass
  work at the earliest" (Bengaluru, 10 Oct). "Bengaluru: Bannerghatta Road
  junctions to be developed for smooth traffic movement" (14 Oct).
  "Commuters stage protest over flyover delay in Hyderabad" (12 Oct).
- **Verdict: ASK_PERMISSION** (the terms say nothing on these points).

### Deccan Herald (The Printers Mysore, TPML)

- **Robots:** `*` allows. The file blocks GPTBot, ChatGPT-User, OAI-SearchBot,
  ClaudeBot, anthropic-ai, Google-Extended, CCBot, PerplexityBot,
  Perplexity-User, Bytespider, Amazonbot, Yandex and SeekportBot.
- **Feeds:** only the site-wide `stories.rss`, with full text. There is no
  city feed (8 October finding).
- **Terms** (https://www.deccanherald.com/terms):
  - "These platforms may be accessed through various means, including desktop
    browsers, mobile devices, applications, and RSS feeds."
  - "You may download or print extracts from the Website strictly for your
    personal, non-commercial use [...]".
  - "You shall not reproduce, modify, publish, store, distribute, transmit,
    create derivative works from, or commercially exploit any TPML Content
    without our prior written consent."
  - "Use of content for data scraping, training artificial intelligence
    models, or automated text extraction is strictly prohibited unless
    expressly licensed by TPML."
  - "Automated extraction, redistribution, framing, scraping, or
    republication of content is not permitted."
- **Article page:** answered 200 with a JSON-LD `articleBody` of 2,491
  characters ("'Hope better sense will prevail': Supreme Court refuses urgent
  hearing on Central Park closure").
- **Verdict: RESTRICTED.**

### Free Press Journal

- **Robots:** `*` disallows `/*/feed`, so section `/feed` URLs were not
  fetched. `stories.rss` and `/api/v1/collections/*.rss` are allowed. No AI
  crawler is blocked.
- **Feeds:** `stories.rss?section=` ignores the filter and returns the
  site-wide feed. The Quintype collection feeds `mumbai.rss` and `pune.rss`
  work, with 40 items each and full text. Delhi was not tested.
- **Terms** (https://www.freepressjournal.in/disclaimer; `/legal` is a news
  section, not terms):
  - "All the contents of Free Press Journal website(s) are provided to enhance
    public access to general information, news and current affairs for
    personal information or use."
  - "Neither this website nor any part of it may be downloaded, reproduced,
    stored, distributed, adapted, translated or transmitted in any form or by
    any means or medium, whether now known or hereinafter invented, without
    prior permission of Free Press Journal."
- **Article page:** answered 200 with a JSON-LD `articleBody` of 3,808
  characters ("Bombay HC Extends Year-Round Ban On Bursting Firecrackers On
  Public Roads").
- **Road events:** "Mumbai Police Grant CJP Permission To Hold 'Lehrao
  Tiranga' Rally At Azad Maidan Today" (15 Oct). "Pune: Collector Jitendra
  Dudi Sets October 30 Deadline For HCMTR, Inner Ring Road Land Measurement"
  (16 Oct).
- **Verdict: RESTRICTED.**

### ABP Live (ABP Network)

- **Robots:** `*` allows `/.../feed`. No AI crawler is blocked.
- **Feeds:** `states/delhi-ncr/feed` and `cities/feed` (mostly Delhi), 10
  items each. The full text is in `description`. No feed was found for the
  other metros.
- **Terms** (https://news.abplive.com/disclaimer; no separate terms page is
  linked):
  - "Except where specifically authorised, the Subscriber may not modify,
    copy, reproduce, republish, upload, post, transmit or distribute in any
    way any material from the ABP NEWS Sites including code and software."
  - "Subscriber may download copyrighted material for Subscriber's personal
    use only."
  - "Except as otherwise expressly permitted under copyright law, no copying,
    redistribution, retransmission, publication or commercial exploitation of
    downloaded material will be permitted without the express permission of
    the Company and the copyright owner."
  - Nothing on automated access or AI.
- **Article page:** answered 200 with a JSON-LD `articleBody` of 2,297
  characters.
- **Road events:** "Delhi Police Warn Of Traffic Disruptions Ahead Of CJP's
  Tiranga March, List Key Roads" (16 Oct 01:52). "Delhi Traffic Advisory: 23
  Roads, Junctions Likely To Be Affected Amid CEC Gyanesh Kumar Protests"
  (13 Oct).
- **Verdict: RESTRICTED** (personal use only).

### Times Now (Times Network, THPL)

- **Robots:** `*` allows `/feeds/` and articles, and disallows `/story/*`. It
  blocks meta-externalagent, Applebot, Amazonbot, Bytespider and others.
- **Feeds:** https://www.timesnownews.com/info/rssfeed lists feeds for all 8
  metros (`gns-en-<city>.xml`). Six were fetched; each has 50 items with a
  description and a body.
- **Terms** (https://www.timesnownews.com/info/terms-conditions):
  - "THPL grants you permission to only access and make personal use of the
    Site [...]".
  - "Automated data collection, web scraping, AI Bot crawling, any form of AI
    tool usage or any other automated activity is strictly prohibited."
  - "Use robots, spiders, scripts, service, software or any manual or
    automatic device, tool, or process designed to data mine or scrape the
    Content [...]".
  - "[...] nor included in any public or private electronic retrieval system
    or service without prior written permission."
  - "[...] training, fine tuning, or grounding the machine learning or AI
    system or as part of retrieval-augmented generation".
- **Article page:** not fetched (budget). The feeds carry full text.
- **Road events:** "Delhi Traffic Alert! Ramlila, Durga Puja Celebrations To
  Affect East Delhi Roads Till October 20" (13 Oct). "Chennai OMR Road Caves
  In, Car Topples Into Massive Sinkhole Amid Metro Work" (8 Oct).
- **Verdict: RESTRICTED.**

### Millennium Post (Millennium Post Media)

- **Robots:** `*` allows `/category/*/google_feeds.xml`. No AI crawler is
  blocked.
- **Feeds:** the Delhi section page advertises
  `/category/delhi/google_feeds.xml`. Kolkata news sits in the Bengal section
  (`/category/bengal/google_feeds.xml`). Both carry full text in
  `content:encoded`. The site-wide `google_feeds.xml` has 60 items.
- **Terms** (https://www.millenniumpost.in/terms, linked as "Terms" in the
  footer): the page is titled "Contact Us" and holds only a privacy policy.
  For example: "By using MP's website or its services, you consent to
  collection, storage, and use of the personal information you provide". The
  footer says "© Copyrights 2022. All rights reserved." Nothing covers
  personal or commercial use, automated access, RSS, storage or AI.
- **Article page:**
  https://www.millenniumpost.in/delhi/heavy-rain-brings-traffic-to-a-crawl-across-delhi-679956
  answered 200 with a JSON-LD `articleBody` of 1,977 characters. It names
  places: "From India Gate and ITO to Mandi House".
- **Road events:** "Heavy rain brings traffic to a crawl across Delhi" (15
  Oct; waterlogging). "State takes corrective steps after bikes skid on
  painted roads" (Kolkata, 15 Oct).
- **Verdict: ASK_PERMISSION** (the terms say nothing on these points).

### The South First (Dakshin Digital Media Pvt Ltd)

- **Robots:** `*` allows. It disallows only wp-admin, attachments and search.
  No AI crawler is blocked.
- **Feeds:** the site-wide `/feed/` (WordPress) has 10 items covering about 5
  hours, with full text. The site has state sections (telangana, karnataka,
  tamilnadu, andhrapradesh, kerala) but no city sections. Two state feed
  attempts failed: `/telangana/feed/` and `/tamilnadu/feed/` redirect to
  `/?p=4818`, which gives 404, and `/karnataka/feed/` redirects to an image.
  `/category/<state>/feed/` was not tested (budget).
- **Terms:** no terms-of-use page is linked. The footer has privacy, editorial,
  corrections and disclaimer pages. https://thesouthfirst.com/disclaimer/
  covers only accuracy, opinions, external links and corrections, plus
  "© Copyright SouthFirst 2025 All rights reserved."
  https://thesouthfirst.com/privacy-policy/ covers personal data only.
- **Article page:** not fetched (the budget went on the failed state-feed
  redirects). The feed carries full text.
- **Road events today:** none. The only road item: "'CM's aide told us not to
  bid': Rajagopal Reddy's bombshell claims over Rs 3,300-crore Telangana road
  project" (16 Oct).
- **Verdict: ASK_PERMISSION.** Low value: 10 items, mostly politics, none city
  by city.

### News18 (Network18)

- **Robots:** now readable (200; it answered 403 on 7 and 8 October). `*`
  allows `/rss/` and articles. The file blocks GPTBot, ChatGPT-User,
  OAI-SearchBot, CCBot, Google-Extended, ClaudeBot, Claude-Web, Bytespider,
  cohere-ai, Diffbot, Scrapy and others.
- **Feeds:** https://www.news18.com/rss/ lists 19 topic feeds
  (`/commonfeeds/v1/eng/rss/<topic>.xml`) and none per city. City pages
  (`/cities/mumbai-news/` etc.) carry no feed link.
- **Terms** (https://www.news18.com/disclaimer/, "Disclaimer & Terms of
  Use"):
  - "(iii) scrape, crawl, mine or extract data from the site, including
    personal data, without express written permission of News18.com, and
    (iv) rent, lease, sublicense, distribute, transfer, copy, reproduce,
    publicly display, publish, adapt, store or time-share News18.com, any
    part thereof or material thereon [...] unless separately and specifically
    authorized in writing by News18.com prior to such use".
- **Article page:** answered 200 with a JSON-LD `articleBody` of 5,233
  characters.
- **Verdict: RESTRICTED.**

### India Today (Living Media India)

- **Robots:** `*` allows `/rss/` and `/cities/`. It disallows `/pti-feed/*`.
  No AI crawler is fully blocked.
- **Feeds:** https://www.indiatoday.in/rss lists 16 section feeds (Home,
  Nation, States and others) and none per city. City sections exist
  (`/cities/delhi/`, `/cities/mumbai/`, `/cities/hyderabad/`,
  `/cities/ahmedabad/` and others).
- **Terms** (https://specials.indiatoday.com/common/termsandconditions.phtml,
  linked from the RSS page):
  - "Use the Service only for your personal, non-commercial purposes;"
  - "Not to use any automated systems or means to access, acquire, copy or
    monitor any part of the Service."
  - "Not to use any automated systems or means, except for those provided by
    us, for the selection or downloading of the Content;"
- **Article page:** answered 200 with a JSON-LD `articleBody` of 5,716
  characters.
- **Verdict: RESTRICTED.**

### ThePrint

- **Robots:** `*` allows. CCBot is blocked.
- **Feeds:** `/feed/` redirects 301 to the home page; the only feed
  advertised is `/web-stories/feed/`. There are no city sections.
- **Terms** (https://theprint.in/terms-of-use/):
  - "The Company grants You permission to access and make use of the ThePrint
    Platform only for non-commercial personal purposes."
  - "You may not (whether directly or through the use of any software
    program) create a database in electronic or structured manual form by
    downloading and/ or storing all or any part of the pages from ThePrint
    Platform."
  - "[...] nor included in any public or private electronic retrieval system
    or service without prior written permission from the Company."
- **Article page:** answered 200. There is no JSON-LD body, but the text is
  in 23 `<p>` paragraphs.
- **Verdict: RESTRICTED.**

### Moneycontrol (Network18)

- **Robots:** `*` allows `/city/`. It blocks CCBot, GPTBot, ChatGPT-User and
  Google-Extended.
- **Feeds:** a city news section exists (`/city/<city>/...`), but the RSS
  list page `/india/newsarticle/rssfeeds/rssfeeds.php` answers 410. No city
  feed was found.
- **Terms** (https://www.moneycontrol.com/cdata/termsofuse.php):
  - "(iii) use any automated systems including bots, scrapers, spiders,
    crawlers, miners or similar technologies to access, monitor, download,
    copy or extract data or any part of the Site or its content [...] without
    prior express written permission of Moneycontrol.com".
  - "Reproduction of news articles, photos, videos or any other content in
    whole or in part in any form or medium without express written permission
    of moneycontrol.com is prohibited."
- **Article page:** the first URL redirected once, to `/city/delhi/...`, which
  answered 200 with a JSON-LD `articleBody` of 3,573 characters ("Delhi wakes
  up to heavy rain, waterlogging in many areas").
- **Verdict: RESTRICTED.**

### Lokmat Times (English; Lokmat Media)

- **Robots:** `Allow: /`.
- **Feeds:** none found. Neither the home page nor `/mumbai/` has a feed
  link.
- **Terms** (https://www.lokmattimes.com/terms-of-use/):
  - "[...] a personal, limited, non-exclusive, non-transferable, freely
    revocable license to use the Services for the personal and non-commercial
    use only."
  - "use or launch any "robots", "spiders", "offline readers" etc. or any
    other automated system, that accesses the Site or the Services in a
    manner that sends numerous automated requests to the Site´s servers in a
    given period of time".
  - "Use the Site, Services or Company Content for any commercial purpose or
    the benefit of any third party".
- **Article page:** answered 200 with a JSON-LD `articleBody` of 2,145
  characters.
- **Verdict: RESTRICTED.**

### The Federal (New Generation Media)

- **Robots:** `*` allows. No AI crawler is blocked.
- **Feeds:** only the site-wide `google_feeds.xml`. The sections are regional
  ("states"), not metro city sections.
- **Terms** (https://thefederal.com/terms):
  - "You may view and/or print pages from https://thefederal.com for your own
    personal use subject to restrictions set in these terms and conditions."
  - Followed by a list of things the user must not do: "Republish material
    from", "Reproduce, duplicate or copy material from", "Redistribute
    content".
- **Article page:** answered 200 with a JSON-LD `articleBody` of 4,999
  characters.
- **Verdict: RESTRICTED.**

### Bangalore Mirror (Times group)

- **Robots:** `Allow: /`.
- **Feed:** `rssfeed.cms` has 15 items, a print batch dated 00:30 UTC.
- **Terms:** the article footer links to
  https://www.indiatimes.com/termsandcondition (Times Internet). Its
  robots.txt was fetched first; the page is allowed.
  - "End-Users are permitted to make personal, non-commercial use of such
    content only, and are prohibited from aggregating, scraping, recreating
    or redistributing the content".
  - "Use any robot, spider, scraper, or other automated or manual means to
    access the Website or copy any Content or information on the Website."
- **Article page:** answered 200, but the text is mostly not in the HTML
  (2 paragraphs, 399 characters; no JSON-LD body).
- **Road events:** "This jam has cost us dearly" (14 Oct, Bengaluru traffic
  cover story; no closure).
- **Verdict: RESTRICTED.**

### Mumbai Mirror

- `mumbaimirror.indiatimes.com/robots.txt` redirects 301 to
  `www.mumbaimirror.com`. That cross-host redirect was not followed; its
  robots.txt was fetched separately and allows everything except
  `/dashboard/` and `/api/`.
- **Feeds:** the Next.js site has no feed link; `/rss` and `/feed` give 404.
- **Terms:** the footer links to https://bccl.in/terms-of-use/, but
  `bccl.in/robots.txt` answers 403, so the page was not fetched.
- **Article page:** answered 200 with a JSON-LD `articleBody` of 3,694
  characters.
- **Verdict:** nothing to connect (no feed), and the terms are unreadable.

### Ahmedabad Mirror (Shayona Times Pvt Ltd)

- **Robots:** `User-agent: *` / `Disallow:` (empty), so everything is
  allowed. The home page timed out twice and loaded on the third try.
- **Feeds:** none. There is no feed link; `/rss` and `/feed` give 404.
- **Terms** (https://www.ahmedabadmirror.com/pg/terms-conditions): a generic
  template naming "Shayona Times Private Limited". It covers age, links,
  termination, liability and governing law, and says nothing on personal or
  commercial use, automated access, RSS, storage or AI.
- **Article page:** answered 200. There is no JSON-LD body, but the text is
  in 17 `<p>` paragraphs (4,855 characters).
- **Verdict: ASK_PERMISSION**, but there is nothing to connect without a
  feed.

### NDTV

- `www.ndtv.com/robots.txt` answers 403 "Access Denied" (Akamai), as on 7
  and 8 October. No other ndtv.com path was requested.
- **Feed:** the FeedBurner cities feed
  (https://feeds.feedburner.com/ndtvnews-cities-news) answers 200 with 20
  mixed-city items. FeedBurner's robots.txt returned an HTML page, not a
  robots file. Today's items include "Mumbai Cops Give CJP Permission For
  'Lehra Do Tiranga' Rally At Azad Maidan Today" and "After Viral Skid
  Videos, Kolkata Scrubs Colour Paint From Flyover Road".
- **Terms:** unreadable.
- **Verdict:** not reachable. Article links point to ndtv.com, which refuses
  REI's user agent.

### Not reachable

- **DNA India, Zee News, Telegraph India, The Week:** robots.txt answered 403
  "Access Denied" (Akamai) to REI's user agent. Nothing further was
  requested.
- **The Statesman:** robots.txt answered 200 (WordPress; only `/wp-admin/`
  and `/test` disallowed), but the home page answered 403.
- **Pune Mirror:** both `https://www.punemirror.com/robots.txt` and
  `https://punemirror.com/robots.txt` were reset by the server.

### Out of scope: no metro city sections (robots.txt only)

Scroll, Republic, Business Standard, Outlook, The Quint, Firstpost,
Mathrubhumi English and Onmanorama. For each, only robots.txt was read; for
Republic, the home page too (it has no city links). Scroll had no city feed on
8 October. Two robots findings:

- The Quint's robots.txt disallows `/story/`.
- Onmanorama's robots.txt disallows `/rss/` and `/*.feed.xml$` for `*`, and
  blocks GPTBot.

No terms were read for these publishers.

## Not verified

- **Feeds not fetched (10-request budget):**
  - Indian Express Hyderabad (fetched 8 October: 200 items, empty bodies).
  - Times Now Pune and Ahmedabad (listed on their RSS page).
  - New Indian Express Delhi, Mumbai and Kolkata collection feeds
    (`/api/v1/collections/<city>-cities.rss` is the expected pattern).
  - Free Press Journal Delhi collection.
  - The South First `/category/<state>/feed/`.
- **Article pages not fetched (budget):** Times of India, Indian Express, New
  Indian Express, Times Now, The South First. The last three carry full text
  in their feeds.
- **New Indian Express terms:** only the server-rendered `/terms-of-use` was
  read. Any terms shown by JavaScript, or in another page, were not seen. The
  14 October note that it restricts automated use has no quote behind it.
- **Times of India general terms:** the TOI footer's "Terms of Use and
  Grievance Redressal Policy" was not fetched. The RSS terms and the Times
  Internet terms (indiatimes.com) were.
- **Mumbai Mirror terms** (bccl.in) and **NDTV terms:** unreadable (robots.txt
  403).
- **India Today and News18:** no city feeds were found on their RSS pages;
  undocumented per-city feed URLs were not guessed.
- **Freshness over time:** every count is one snapshot taken on 16 October.
  Item rates, and whether the New Indian Express and Millennium Post feeds
  stay current, need a multi-day sample.

## Request record

- 163 requests to 41 hosts. The most to any host was 10 (Times of India,
  Hindustan Times, Indian Express, New Indian Express, Free Press Journal,
  Times Now, The South First).
- Gaps between requests to one host were at least 2.5 s (log timestamps have
  1-second resolution).
- No robots-disallowed path was requested.
- Redirects were followed on the same host only, and each step was counted.
  Four South First requests went on redirects of state feed URLs. Two
  cross-host redirects were not followed (mumbaimirror.indiatimes.com to
  www.mumbaimirror.com; thesouthfirst.com to an image on
  static.thesouthfirst.com).
- Two Ahmedabad Mirror home-page requests timed out and are counted.
