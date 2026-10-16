"""SAnews — the South African Government News Agency (GCIS) news feed.

Verified live on 16 October 2026: https://www.sanews.gov.za/south-africa-news-stories.xml,
10 items covering about a day, each with the full article text; dates only in
the wording and no coordinates. robots.txt allows the feed. Road closures are
few (a handful of articles a month in 2026, found by search).

User policy (https://www.sanews.gov.za/content/user-policy, read 16 October
2026): "Media are welcome to utilise all stories, pictures and other material
on this site ... at no cost, provided SAnews is credited." The grant is
addressed to media; a one-line confirmation from newsfiles@gcis.gov.za is
advisable before commercial use
(docs/data-sources/south-africa-sources-2026-10-16.md).
"""

from packages.source_models import CommercialUse, SourceDefinition, TermsStatus

from .models import news_rss_source

SANEWS = SourceDefinition.model_validate(
    news_rss_source(
        source_id="sanews",
        source_name="SAnews (South African Government News Agency)",
        organization="Government Communication and Information System (GCIS)",
        source_url="https://www.sanews.gov.za/",
        endpoint="https://www.sanews.gov.za/south-africa-news-stories.xml",
        polling_frequency_minutes=60,
        country="ZA",
        region="National",
        city="south-africa",
        notes=(
            "About 10 items covering a day, each with the full article text. Few road "
            "closures. Free to use with credit to SAnews (its user policy addresses media; "
            "confirmation advisable before commercial use)."
        ),
    ).model_dump()
    | {
        "terms_status": TermsStatus.PERMITS_TESTING,
        "commercial_use": CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        "licence": (
            "SAnews user policy (https://www.sanews.gov.za/content/user-policy, read 16 October "
            "2026): 'Media are welcome to utilise all stories, pictures and other material on "
            "this site ... at no cost, provided SAnews is credited.'"
        ),
        "attribution": "SAnews.gov.za",
    }
)
