"""The Siasat Daily — Hyderabad section RSS feed.

Verified live on 2 October 2026: 40 items covering about 30 hours. Every item
is tagged Hyderabad and carries a summary and the full article body.

Not read since 14 October 2026: the publisher's terms forbid automated
access (connectors/restricted.py, decision 0024). The source stays registered
so the articles stored before then keep their source.
"""

from connectors.restricted import RESTRICTED_PUBLISHERS

from .models import news_rss_source, restricted_by_terms

SIASAT = restricted_by_terms(
    news_rss_source(
        source_id="siasat",
        source_name="The Siasat Daily",
        organization="The Siasat Daily",
        source_url="https://www.siasat.com/news/hyderabad/",
        endpoint="https://www.siasat.com/news/hyderabad/feed/",
        notes=(
            "About 40 items covering roughly 30 hours. Every item is tagged Hyderabad "
            "and carries a summary and the full article body."
        ),
    ),
    terms=RESTRICTED_PUBLISHERS["siasat.com"],
)
