"""Deccan Chronicle — Telangana section RSS feed.

Verified live on 2 October 2026: 60 items covering about 18 hours.

Deccan Chronicle has no usable Hyderabad-only feed (the /category/hyderabad/
feed held seven stale items from July 2026). This is the feed its Telangana
section page declares; the detection scope check selects the Hyderabad items.

Notes on this feed:
- Headlines Are Written In Title Case.
- Each item has one <category> holding a comma-separated list
  ("Southern States,Telangana,Trending").
- The city is given only in the dateline that opens the article body.
- The GUID is the article URL.
"""

from .models import news_rss_source

DECCAN_CHRONICLE = news_rss_source(
    source_id="deccan-chronicle",
    source_name="Deccan Chronicle",
    organization="Deccan Chronicle",
    source_url="https://www.deccanchronicle.com/southern-states/telangana",
    endpoint="https://www.deccanchronicle.com/category/southern-states/telangana/google_feeds.xml",
    notes=(
        "About 60 items covering under a day. Telangana-wide; the city appears only "
        "in the article dateline, which the scope check reads. Title Case headlines."
    ),
)
