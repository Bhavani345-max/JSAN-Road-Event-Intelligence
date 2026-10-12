"""The Hindu — Bengaluru city RSS feed.

Verified live on 7 October 2026: 60 items covering about five days, one-line
descriptions on 41 of 60, no article body. The same structure as the
connected Hyderabad city feed; detection usually rests on the headline. The
feed is Bengaluru-led but carries Karnataka items (Mandya, Mysuru), which the
scope check keeps out.
"""

from .models import news_rss_source

THE_HINDU_BENGALURU = news_rss_source(
    source_id="the-hindu-bengaluru",
    source_name="The Hindu (Bengaluru)",
    organization="The Hindu",
    source_url="https://www.thehindu.com/news/cities/bangalore/",
    endpoint="https://www.thehindu.com/news/cities/bangalore/feeder/default.rss",
    region="Karnataka",
    city="bengaluru",
    notes=(
        "About 60 items covering roughly five days; one-line descriptions on most, no "
        "body. Bengaluru-led with other Karnataka districts mixed in."
    ),
)
