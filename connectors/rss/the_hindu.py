"""The Hindu — Hyderabad city RSS feed.

Verified live on 2 October 2026: 60 items covering about two days.

Notes on this feed:
- Despite being the Hyderabad city feed, most items are tagged "Telangana" and
  cover the whole state; the detection scope check keeps other districts out.
- Most items have no summary, so detection usually rests on the headline alone.
- There is no article body in the feed.
"""

from .models import news_rss_source

THE_HINDU = news_rss_source(
    source_id="the-hindu",
    source_name="The Hindu",
    organization="The Hindu",
    source_url="https://www.thehindu.com/news/cities/Hyderabad/",
    endpoint="https://www.thehindu.com/news/cities/Hyderabad/feeder/default.rss",
    notes=(
        "About 60 items covering roughly two days. Most items are statewide and "
        "tagged Telangana; most have no summary and none has a body, so detection "
        "usually rests on the headline alone."
    ),
)
