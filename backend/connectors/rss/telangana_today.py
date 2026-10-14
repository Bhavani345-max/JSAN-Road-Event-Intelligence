"""Telangana Today — Hyderabad section RSS feed.

The publisher's own "Hyderabad" section feed is used rather than the site-wide
feed, so items are already scoped to the PoC city.
"""

from .models import news_rss_source

TELANGANA_TODAY = news_rss_source(
    source_id="telangana-today",
    source_name="Telangana Today",
    organization="Telangana Today",
    source_url="https://telanganatoday.com/hyderabad",
    endpoint="https://telanganatoday.com/hyderabad/feed",
    notes=(
        "About 500 items covering roughly two weeks. Every item is tagged Hyderabad "
        "and carries a summary and the full article body."
    ),
)
