"""The Hans India — Hyderabad section RSS feed.

Verified live on 2 October 2026: 29 items covering under three hours. This is
the feed the Hyderabad section page itself declares. Every item is tagged
Hyderabad and carries a summary and the full article body.

Because the feed holds so little history, it is polled more often than the
others; articles published while REI is not running are lost.
"""

from .models import news_rss_source

THE_HANS_INDIA = news_rss_source(
    source_id="the-hans-india",
    source_name="The Hans India",
    organization="The Hans India",
    source_url="https://www.thehansindia.com/news/cities/hyderabad",
    endpoint="https://www.thehansindia.com/category/news/cities/hyderabad/google_feeds.xml",
    polling_frequency_minutes=15,
    notes=(
        "About 30 items covering under three hours, so it is polled every 15 minutes. "
        "Every item is tagged Hyderabad and carries a summary and the full article body."
    ),
)
