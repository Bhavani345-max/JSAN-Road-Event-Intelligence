# The Hindu (RSS)

| | |
| --- | --- |
| Source id | `the-hindu` |
| Feed | `https://www.thehindu.com/news/cities/Hyderabad/feeder/default.rss` (Hyderabad city feed) |
| Verified | 2 October 2026: reachable, 60 items covering about two days |
| Format | RSS 2.0 |
| Polling | Every 30 minutes |
| Definition | `connectors/rss/the_hindu.py` (configuration only; read by the generic RSS connector) |
| Authority type, tier | Not assigned |

## How this feed differs

- **Mostly statewide items.** Although it is the Hyderabad city feed, on the
  day it was checked 42 of 60 items were tagged "Telangana" and 11
  "Hyderabad". The detection scope check (publisher tag or a mention of
  Hyderabad, Secunderabad or Cyberabad) keeps other districts out.
- **Usually no summary.** 41 of 60 items had an empty description, so detection
  normally rests on the headline alone and the event has no description.
- **No article body** in the feed.
- GUIDs are of the form `article-71536756` and are not URLs; the link is
  stored separately.

## Observed results

2 October 2026: 60 articles stored, **0** detected as traffic candidates.
All 60 headlines were read to confirm that none concerned a road closure,
diversion, procession route or waterlogging in Hyderabad during that window.

## Known limits

- With headline-only detection, an article whose headline does not use the
  configured keywords is missed.
- A Hyderabad article tagged only "Telangana" whose headline names a locality
  (for example "Khajaguda") rather than the city is treated as out of scope.
- The feed holds about two days of items; polling every 30 minutes does not
  miss any, but history before the first poll is not available.

## Terms of use

Review The Hindu's terms before any commercial redistribution of its content.
REI stores what the feed provides as evidence and shows the headline with a
link back to the original.
