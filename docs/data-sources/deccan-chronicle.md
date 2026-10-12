# Deccan Chronicle (RSS)

| | |
| --- | --- |
| Source id | `deccan-chronicle` |
| Feed | `https://www.deccanchronicle.com/category/southern-states/telangana/google_feeds.xml` (Telangana section) |
| Verified | 2 October 2026: reachable, 60 items covering about 18 hours |
| Format | RSS 2.0 |
| Polling | Every 30 minutes |
| Definition | `connectors/rss/deccan_chronicle.py` (configuration only; read by the generic RSS connector) |
| Authority type, tier | Not assigned |

## Why the Telangana feed and not a Hyderabad feed

No usable Hyderabad-only feed was found:

| Endpoint checked | Result |
| --- | --- |
| `/category/southern-states/telangana/google_feeds.xml` | Live, 60 items. Declared by the Telangana section page itself. **Used.** |
| `/category/hyderabad/google_feeds.xml` | Responds, but held 7 items, all from 13 July 2026. Stale; not used |
| `/google_feeds.xml` | Live, site-wide, 60 items spanning about 4 hours. Too broad and too short a window |
| `/feeds.xml` | Live, site-wide, 611 items over two days. Works, but 80% is outside Telangana |
| `/category/southern-states/telangana/hyderabad/google_feeds.xml` | Empty response |

The detection scope check selects the Hyderabad items from the Telangana feed
(9 of 60 mentioned Hyderabad on the day it was checked).

## How this feed differs

- **Headlines Are In Title Case.** Road names are recognised by capital
  letters, which carry no meaning when every word is capitalised, so road
  mentions are taken from the sentence-case summary only for such headlines
  (`services/extraction/road_mentions.py`). Road numbers such as "NH-65" are
  still picked up from headlines.
- **The city is only in the dateline.** Items are not tagged Hyderabad, and
  the headline and summary often do not name the city; the article body opens
  with "Hyderabad: …". The scope check reads that opening dateline (and
  nothing else in the body). Before this was added, the IIIT Junction article
  of 29 June 2026 was rejected as outside Hyderabad.
- Each item has a single category holding a comma-separated list
  ("Southern States,Telangana,Trending"). It is stored as received.
- The GUID is the article URL.
- Items include a summary and the full article HTML.

## Observed results

2 October 2026: 60 articles stored, **0** detected as traffic candidates.
All 60 headlines were read to confirm that none concerned a road closure,
diversion, procession route or waterlogging in Hyderabad during that window.
(The site-wide feed did carry a Delhi traffic advisory, which the scope check
correctly left out.)

## Known limits

- The feed holds under a day of items. Polling every 30 minutes keeps up, but
  an outage longer than about 18 hours would lose articles.
- A road named only in a Title Case headline is not captured as a road mention.
- A dateline says where an article was filed, not what it is about. A traffic
  article filed from Hyderabad about another district is accepted and left to
  the reviewer.

## Terms of use

Review Deccan Chronicle's terms before any commercial redistribution of its
content. REI stores what the feed provides as evidence and shows the
headline, the summary and a link back to the original.
