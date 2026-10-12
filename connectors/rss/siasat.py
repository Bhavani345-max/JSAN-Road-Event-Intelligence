"""The Siasat Daily — Hyderabad section RSS feed.

Verified live on 2 October 2026: 40 items covering about 30 hours. Every item
is tagged Hyderabad and carries a summary and the full article body.
"""

from .models import news_rss_source

SIASAT = news_rss_source(
    source_id="siasat",
    source_name="The Siasat Daily",
    organization="The Siasat Daily",
    source_url="https://www.siasat.com/news/hyderabad/",
    endpoint="https://www.siasat.com/news/hyderabad/feed/",
    notes=(
        "About 40 items covering roughly 30 hours. Every item is tagged Hyderabad "
        "and carries a summary and the full article body."
    ),
)
