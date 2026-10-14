"""The Siasat Daily — Mumbai tag RSS feed.

Verified live on 7 October 2026: 40 items covering about six weeks (about
one a day), full text, mostly PTI copy. The tag feed is newer than the
section feed (`news/mumbai/feed/`, newest 29 September), so the tag feed is
used. Same publisher and terms as the Hyderabad feed.

Not read since 14 October 2026: the publisher's terms forbid automated
access (connectors/restricted.py, decision 0024). The source stays registered
so the articles stored before then keep their source.
"""

from connectors.restricted import RESTRICTED_PUBLISHERS

from .models import news_rss_source, restricted_by_terms

SIASAT_MUMBAI = restricted_by_terms(
    news_rss_source(
        source_id="siasat-mumbai",
        source_name="The Siasat Daily (Mumbai)",
        organization="The Siasat Daily",
        source_url="https://www.siasat.com/tag/mumbai/",
        endpoint="https://www.siasat.com/tag/mumbai/feed/",
        region="Maharashtra",
        city="mumbai",
        notes=(
            "About 40 items covering roughly six weeks, about one a day, full text, "
            "mostly PTI copy. A second source for Mumbai stories."
        ),
    ),
    terms=RESTRICTED_PUBLISHERS["siasat.com"],
)
