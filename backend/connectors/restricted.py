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
    # Decision 0033: read 16 October 2026 (docs/data-sources/india-national-feeds-2026-10-16.md).
    "indiatimes.com": (
        "Times Internet's terms (https://www.indiatimes.com/termsandcondition, read 16 October "
        "2026) permit 'personal, non-commercial use of such content only' and prohibit "
        "'aggregating, scraping, recreating or redistributing the content' and using 'any robot, "
        "spider, scraper, or other automated or manual means to access the Website'; the Times of "
        "India RSS page (https://timesofindia.indiatimes.com/rss.cms) forbids 'aggregating, "
        "reselling or putting to commercial use' its RSS feeds."
    ),
    **{
        domain: (
            "HT Digital Streams' terms (https://www.hindustantimes.com/termsofuse, read 16 October "
            "2026; they cover Hindustan Times, LiveMint and Live Hindustan): 'You may view and share "
            "content for personal, non-commercial use' and 'you must not use robots, spiders, "
            "crawlers, scrapers, or similar tools to access, copy, cache, archive, or index the "
            "Services'; 'Automated scraping/crawling/bulk downloading is prohibited.'"
        )
        for domain in ("hindustantimes.com", "livemint.com", "livehindustan.com")
    },
    "indianexpress.com": (
        "The Indian Express terms (https://indianexpress.com/terms-and-conditions/, read 16 October "
        "2026) give a licence 'for the personal and non-commercial use only' and forbid to 'Use "
        "automated tools, bots, crawlers, scrapers, or similar technologies ... to access, "
        "extract, download, store or index any portion of the Content'."
    ),
    "deccanherald.com": (
        "Deccan Herald's terms (https://www.deccanherald.com/terms, read 16 October 2026): "
        "'Automated extraction, redistribution, framing, scraping, or republication of content is "
        "not permitted.'"
    ),
    "freepressjournal.in": (
        "The Free Press Journal disclaimer (https://www.freepressjournal.in/disclaimer, read 16 "
        "October 2026): 'Neither this website nor any part of it may be downloaded, reproduced, "
        "stored, distributed ... without prior permission of Free Press Journal.'"
    ),
    "timesnownews.com": (
        "Times Now's terms (https://www.timesnownews.com/info/terms-conditions, read 16 October "
        "2026): 'Automated data collection, web scraping, AI Bot crawling, any form of AI tool "
        "usage or any other automated activity is strictly prohibited.'"
    ),
    "news18.com": (
        "News18's terms (https://www.news18.com/disclaimer/, read 16 October 2026) forbid to "
        "'scrape, crawl, mine or extract data from the site ... without express written "
        "permission of News18.com'."
    ),
    "indiatoday.in": (
        "India Today's terms (https://specials.indiatoday.com/common/termsandconditions.phtml, read "
        "16 October 2026): 'Use the Service only for your personal, non-commercial purposes' and "
        "'Not to use any automated systems or means to access, acquire, copy or monitor any part "
        "of the Service.'"
    ),
    "moneycontrol.com": (
        "Moneycontrol's terms (https://www.moneycontrol.com/cdata/termsofuse.php, read 16 October "
        "2026) forbid to 'use any automated systems including bots, scrapers, spiders, crawlers, "
        "miners or similar technologies to access, monitor, download, copy or extract data ... "
        "without prior express written permission'."
    ),
    "theprint.in": (
        "ThePrint's terms (https://theprint.in/terms-of-use/, read 16 October 2026) permit use "
        "'only for non-commercial personal purposes' and forbid to 'create a database in "
        "electronic or structured manual form by downloading and/ or storing all or any part of "
        "the pages'."
    ),
    "mid-day.com": (
        "Mid-day's terms (https://www.mid-day.com/terms-and-conditions, read 15 October 2026) "
        "grant 'only a limited, nonexclusive license for use solely by you for your own personal "
        "use and not for republication, distribution ... or other use' and say 'No part of any "
        "content ... may be reproduced in any form or incorporated into any information "
        "retrieval system ... other than for your personal use'. Disconnected 16 October 2026 "
        "by the user's decision."
    ),
    "lokmattimes.com": (
        "Lokmat Times' terms (https://www.lokmattimes.com/terms-of-use/, read 16 October 2026) "
        "give a licence 'for the personal and non-commercial use only' and forbid 'any other "
        "automated system, that accesses the Site' and use 'for any commercial purpose'."
    ),
}


# Publishers the user removed from REI (decision 0026). Their terms do not
# forbid automated access, so they are not above; the GDELT search
# (decision 0033) leaves their articles out all the same.
REMOVED_PUBLISHERS: dict[str, str] = {
    "thehansindia.com": "Removed from REI on 14 October 2026 by the user's decision (decision 0026).",
}


# Publishers whose terms permit REI to read and keep their articles (decision
# 0033). The GDELT search reads an article's page only from these; from any
# other publisher it keeps GDELT's own result (headline, address, time).
READABLE_PUBLISHERS: dict[str, str] = {
    "sanews.gov.za": (
        "SAnews user policy (https://www.sanews.gov.za/content/user-policy, read 16 October "
        "2026): 'Media are welcome to utilise all stories ... at no cost, provided SAnews is "
        "credited.'"
    ),
    "pib.gov.in": (
        "PIB copyright policy (https://www.pib.gov.in/ContentPage.aspx?menuid=137&reg=48&lang=2, "
        "read 16 October 2026, in Hindi): material published on the website may be reproduced "
        "free of charge without prior approval; wherever it is published, its source must be "
        "prominently acknowledged."
    ),
}


def _publisher_in(url: str | None, domains) -> str | None:
    if not url:
        return None
    host = (urlsplit(url.strip()).hostname or "").lower().rstrip(".")
    for domain in domains:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def restricted_publisher(url: str | None) -> str | None:
    """The restricted publisher domain `url` is on, or None when it may be read."""
    return _publisher_in(url, RESTRICTED_PUBLISHERS)


def removed_publisher(url: str | None) -> str | None:
    """The domain of a publisher the user removed that `url` is on, or None."""
    return _publisher_in(url, REMOVED_PUBLISHERS)


def readable_publisher(url: str | None) -> str | None:
    """The domain of a publisher whose terms permit reading its articles, or None."""
    return _publisher_in(url, READABLE_PUBLISHERS)
