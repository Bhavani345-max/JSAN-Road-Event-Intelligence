"""Mid-Day — Mumbai section RSS feed.

Verified live on 7 October 2026: 30 items covering about 20 hours, every one
Mumbai-only, with the full article body (`content:encoded`). The feed's
`pubDate` carries no time zone. robots.txt allows the path. Terms: "No part
of any content ... may be reproduced ... other than for your personal use";
not reviewed for REI's purpose (docs/cities/mumbai-source-research.md).
"""

from .models import news_rss_source

MID_DAY_MUMBAI = news_rss_source(
    source_id="mid-day-mumbai",
    source_name="Mid-Day (Mumbai)",
    organization="Mid-Day Infomedia",
    source_url="https://www.mid-day.com/mumbai",
    endpoint="https://www.mid-day.com/Resources/midday/rss/mumbai.xml",
    region="Maharashtra",
    city="mumbai",
    notes=(
        "About 30 items covering roughly 20 hours, all Mumbai, each with the full "
        "article body. Publication times carry no time zone."
    ),
)
