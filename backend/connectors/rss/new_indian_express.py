"""The New Indian Express — city section feeds (16 October 2026, decision 0033).

The site's own redirect table maps /cities/<city>/rssfeed to
/api/v1/collections/<city>-cities.rss. Verified live on 16 October 2026: 40
items a city, the article body in the item's second content element (the
first is empty), no summary. The older stories.rss?section=<city> feeds are
empty. robots.txt allows everything.

Terms (https://www.newindianexpress.com/terms-of-use, read 16 October 2026):
the page titled "Terms Of Use" holds only a privacy notice; nothing on
personal or commercial use, automated access, RSS, storage or AI. The
research of 14 October listed the publisher among those restricting automated
use without quoting it; today's page does not support that. Connected like
Telangana Today and NewsMeter: permission to be asked of the publisher
(Express Network Pvt Ltd) (docs/data-sources/india-national-feeds-2026-10-16.md).
"""

from .models import news_rss_source

_NOTES = (
    "About 40 items covering several days, each with the full article body. The "
    "publisher's terms page holds only a privacy notice (read 16 October 2026): "
    "permission to be asked of Express Network Pvt Ltd."
)


def _city_feed(city_id: str, city_name: str, region: str, path: str):
    return news_rss_source(
        source_id=f"new-indian-express-{city_id}",
        source_name=f"The New Indian Express ({city_name})",
        organization="Express Network Pvt Ltd",
        source_url=f"https://www.newindianexpress.com/cities/{path}",
        endpoint=f"https://www.newindianexpress.com/api/v1/collections/{path}-cities.rss",
        region=region,
        city=city_id,
        notes=_NOTES,
    )


NEW_INDIAN_EXPRESS_FEEDS = (
    _city_feed("hyderabad", "Hyderabad", "Telangana", "hyderabad"),
    _city_feed("bengaluru", "Bengaluru", "Karnataka", "bengaluru"),
    _city_feed("chennai", "Chennai", "Tamil Nadu", "chennai"),
    _city_feed("delhi", "Delhi", "Delhi", "delhi"),
    _city_feed("mumbai", "Mumbai", "Maharashtra", "mumbai"),
    _city_feed("kolkata", "Kolkata", "West Bengal", "kolkata"),
)
