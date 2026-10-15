"""Publishers whose terms forbid REI's automated access (decision 0024).

REI never requests a page from these hosts, never stores a search result that
links to them, and never sends their articles to an AI model. Their feeds are
registered without a connector (connectors/registry.py). Evidence stored
before the restriction was found is kept, unchanged.
"""

from urllib.parse import urlsplit

# Registrable domain -> the terms that restrict it, in their own words.
RESTRICTED_PUBLISHERS: dict[str, str] = {
    "siasat.com": (
        "The Siasat Daily terms (https://www.siasat.com/terms-conditions/, read 14 October "
        "2026) give a licence 'solely for your personal, non-commercial use' (s.4.1), exclude "
        "any right to 'use any data mining, robots, scrapers, crawlers, or similar "
        "data-gathering and extraction tools' (s.4.2), and prohibit using 'any robot, spider, "
        "scraper, or other automated means to access, extract, or index the Content without "
        "prior written permission'."
    ),
    # Decision 0032: read 15 October 2026; disconnected until the publisher agrees.
    "thehindu.com": (
        "The Hindu's terms of use (https://www.thehindu.com/termsofuse/, THG Publishing, read "
        "15 October 2026) say users may not 'use robots, spiders, scripts, service, software or "
        "any manual or automatic device, tool, or process designed to data mine or scrape the "
        "Content, data or information from the Services, or otherwise use, access, or collect "
        "the Content, data or information from the Services using automated means', nor use the "
        "Content to train a machine learning or AI system."
    ),
    "deccanchronicle.com": (
        "Deccan Chronicle's terms (https://www.deccanchronicle.com/terms-and-condition, read 15 "
        "October 2026) grant a 'limited license only for purposes of viewing the material', and "
        "restrict 'publishing any Website material in any other media', 'selling, sublicensing "
        "and/or otherwise commercializing any Website material' and 'engaging in any data "
        "mining, data harvesting, data extracting or any other similar activity'."
    ),
}


def restricted_publisher(url: str | None) -> str | None:
    """The restricted publisher domain `url` is on, or None when it may be read."""
    if not url:
        return None
    host = (urlsplit(url.strip()).hostname or "").lower().rstrip(".")
    for domain in RESTRICTED_PUBLISHERS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None
