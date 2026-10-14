"""NewsMeter — Hyderabad section RSS feed.

Verified live on 2 October 2026: 60 items covering about ten days. This is the
feed the Hyderabad section page itself declares. Every item is tagged
Hyderabad and carries a summary and the full article body.
"""

from .models import news_rss_source

NEWSMETER = news_rss_source(
    source_id="newsmeter",
    source_name="NewsMeter",
    organization="NewsMeter",
    source_url="https://newsmeter.in/hyderabad",
    endpoint="https://newsmeter.in/category/hyderabad/google_feeds.xml",
    notes=(
        "About 60 items covering roughly ten days. Every item is tagged Hyderabad "
        "and carries a summary and the full article body."
    ),
)
