"""The Hans India — Hyderabad section RSS feed.

Verified live on 2 October 2026: 29 items covering under three hours. This is
the feed the Hyderabad section page itself declares. Every item is tagged
Hyderabad and carries a summary and the full article body.

Removed from REI on 14 October 2026 by the user's decision (decision 0026):
its terms allow personal, non-commercial use only, and its Cloudflare
protection refuses REI's production server. The source stays registered so
the articles stored before then keep their source.
"""

from .models import news_rss_source, removed_from_rei

THE_HANS_INDIA = removed_from_rei(
    news_rss_source(
        source_id="the-hans-india",
        source_name="The Hans India",
        organization="The Hans India",
        source_url="https://www.thehansindia.com/news/cities/hyderabad",
        endpoint="https://www.thehansindia.com/category/news/cities/hyderabad/google_feeds.xml",
        polling_frequency_minutes=15,
        notes=(
            "About 30 items covering under three hours, so it was polled every 15 minutes. "
            "Every item is tagged Hyderabad and carries a summary and the full article body."
        ),
    ),
    licence=(
        "Terms (https://www.thehansindia.com/pages/terms-conditions, read 14 October 2026): "
        "'HMHL grants you a limited license to access and make personal use of this site but "
        "not for commercial purposes.'"
    ),
    attribution=(
        "'We permit the use of materials on this website subject to due credit is given to HMHL.'"
    ),
    reason=(
        "Removed from REI on 14 October 2026 by the user's decision: its terms allow personal, "
        "non-commercial use only, and its Cloudflare protection refuses REI's production server "
        "(HTTP 403 from Railway since 12 October; an office connection gets 200)."
    ),
)
