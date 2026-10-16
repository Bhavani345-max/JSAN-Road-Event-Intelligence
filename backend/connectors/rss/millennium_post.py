"""Millennium Post — Delhi and Bengal section feeds (16 October 2026, decision 0033).

Verified live on 16 October 2026: the Delhi section feed (23 items) and the
Bengal section feed (29 items; Kolkata news sits there), each with the full
article body. robots.txt allows the feeds. Items of the Bengal feed about other
places are left out by Kolkata's scope rules.

Terms (https://www.millenniumpost.in/terms, read 16 October 2026): the page
linked as "Terms" holds only a privacy policy; nothing on personal or
commercial use, automated access, RSS, storage or AI. Connected like
Telangana Today and NewsMeter: permission to be asked of the publisher
(docs/data-sources/india-national-feeds-2026-10-16.md).
"""

from .models import news_rss_source

_NOTES = (
    "Each item with the full article body. The publisher's terms page holds only a "
    "privacy policy (read 16 October 2026): permission to be asked of Millennium Post."
)

MILLENNIUM_POST_DELHI = news_rss_source(
    source_id="millennium-post-delhi",
    source_name="Millennium Post (Delhi)",
    organization="Millennium Post",
    source_url="https://www.millenniumpost.in/delhi",
    endpoint="https://www.millenniumpost.in/category/delhi/google_feeds.xml",
    region="Delhi",
    city="delhi",
    notes=f"About 25 items covering about a day. {_NOTES}",
)

MILLENNIUM_POST_KOLKATA = news_rss_source(
    source_id="millennium-post-kolkata",
    source_name="Millennium Post (Kolkata)",
    organization="Millennium Post",
    source_url="https://www.millenniumpost.in/bengal",
    endpoint="https://www.millenniumpost.in/category/bengal/google_feeds.xml",
    region="West Bengal",
    city="kolkata",
    notes=(
        "The Bengal section feed, about 30 items covering about a day; Kolkata's scope "
        f"rules keep the Kolkata items. {_NOTES}"
    ),
)
