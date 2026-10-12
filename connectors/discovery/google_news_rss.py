"""Google News RSS search feeds: a DISCOVERY source, one per configured city.

Google News publishes an RSS feed for any search:

    https://news.google.com/rss/search?q=<query>+when:7d&hl=en-GB&gl=GB&ceid=GB:en

No key is needed. Each item carries a headline, Google's own redirect link,
the publisher's name and site, and a publication time. That is all: the
link leads to a page that only runs script, so the publisher's article
cannot be read from it by documented means (verified 6 October 2026), and
no undocumented route is used to get round that. What is stored as evidence
is therefore the search result itself: headline, publisher, publisher site,
publication time, the search that found it and Google's link. Detection
works on the headline alone, which is where the papers put the measure and
the place.

Every feed carries Google's own notice (checked 6 October 2026): "This XML
feed is made available solely for the purpose of rendering Google News
results within a personal feed reader for personal, non-commercial use. Any
other use of the feed is expressly prohibited." news.google.com's robots.txt
also disallows automated access to paths outside a short allow-list that
does not include /rss. REI's use is neither personal nor a feed reader, so
the source is registered as BLOCKED by its terms and is never fetched. The
connector is kept, tested on a saved feed, for the day Google or a lawyer
says otherwise: GOOGLE_NEWS_RSS_ENABLED switches it on, and when on it polls
gently (one request per search, a pause between requests, every six hours;
a refusal, 429 or 503, stops the poll until the next one).

A result is left out before anything is stored when its headline names
another city and not this one, when it does not mention the city at all, or
when it is not in Latin script. The same article found by several searches
is one record; an article already held from its publisher's own feed, or
from another search source, is not stored again (the pipeline compares
publisher addresses and headlines).
"""

import logging
import re
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import feedparser
import httpx

from connectors.base import ConnectorError
from connectors.rss.base import _published_at
from packages.cities import City, get_city
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import utc_now
from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceType,
    TermsStatus,
)

logger = logging.getLogger(__name__)

FEED_URL = "https://news.google.com/rss/search"
# Google's notice in every feed's <copyright> element, as read on 6 October 2026.
FEED_NOTICE = (
    "This XML feed is made available solely for the purpose of rendering Google News "
    "results within a personal feed reader for personal, non-commercial use. Any other "
    "use of the feed is expressly prohibited."
)
POLLING_FREQUENCY_MINUTES = 360
DEFAULT_WINDOW_DAYS = 7
# Seconds between two requests to Google in one poll.
DEFAULT_PAUSE_SECONDS = 2.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
# A headline with no Latin letters is in a script REI does not read.
_LATIN = re.compile(r"[A-Za-z]{3}")

# Cities whose road news crowds a plain search; a headline naming one of them
# (and not the city searched for) is about that other city.
OTHER_CITIES: tuple[str, ...] = (
    "Delhi", "Bengaluru", "Bangalore", "Mumbai", "Chennai", "Pune", "Kolkata", "Noida",
    "Gurugram", "Gurgaon", "Ahmedabad", "Lucknow", "Patna", "Jaipur", "Kochi", "Hyderabad",
    "London", "Birmingham", "Manchester", "Leeds", "Glasgow", "Edinburgh", "Liverpool",
    "New York", "Sydney", "Toronto", "Singapore", "Dublin", "Paris",
)  # fmt: skip


def source_id_for(city: City) -> str:
    return f"google-news-rss-{city.id}"


def google_news_rss_source(city: City, *, enabled: bool) -> SourceDefinition:
    """The source for one city: BLOCKED by its terms unless explicitly `enabled`."""
    return SourceDefinition(
        source_id=source_id_for(city),
        source_name=f"Google News RSS ({city.name})",
        organization="Google News",
        authority_type="SEARCH_FEED",
        source_tier=4,
        source_type=SourceType.RSS,
        source_class=SourceClass.DISCOVERY,
        discovery_only=True,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://news.google.com/",
        endpoint=FEED_URL,
        access_method="Public RSS feed of Google News search results, no credentials",
        integration_status=(
            IntegrationStatus.CONNECTED if enabled else IntegrationStatus.BLOCKED
        ),
        active=enabled,
        polling_frequency_minutes=POLLING_FREQUENCY_MINUTES,
        language=city.language,
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="google_news_rss",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit=(
            "None published. news.google.com/robots.txt disallows automated access outside "
            "an allow-list that does not include /rss (checked 6 October 2026)."
        ),
        terms_status=TermsStatus.RESTRICTED,
        licence=f"Google's notice in each feed: {FEED_NOTICE}",
        attribution=None,
        commercial_use=CommercialUse.NOT_PERMITTED,
        provides_geometry=False,
        real_time=False,
        evidence_retention=(
            "For each result: the headline, publisher name and site, publication time, "
            "Google's link, the search that found it and a SHA-256 hash of headline and "
            "publisher. The article itself is not read."
        ),
        notes=(
            f"{len(city.discovery.queries)} searches of the past {DEFAULT_WINDOW_DAYS} days for "
            f"{city.name}, every {POLLING_FREQUENCY_MINUTES // 60} hours, with a pause between "
            "requests. Finds headlines only: the publisher's article cannot be read from "
            "Google's link. Discovery only: results are leads for review, never confirmation. "
            + (
                ""
                if enabled
                else "Not connected: each feed says it is for personal, non-commercial use in a "
                "feed reader only, and that any other use is prohibited."
            )
        ).strip(),
    )


class GoogleNewsRssConnector:
    """Reads Google News search feeds for one city's searches."""

    def __init__(
        self,
        source: SourceDefinition,
        city: City,
        user_agent: str,
        *,
        queries: tuple[str, ...] | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        pause_seconds: float = DEFAULT_PAUSE_SECONDS,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.city = city
        self.queries = queries if queries is not None else city.discovery.queries
        self.window_days = window_days
        self.pause_seconds = pause_seconds
        self._user_agent = user_agent
        self._client = client or httpx.Client(timeout=30, follow_redirects=True)
        self._sleep = sleep
        self._in_scope = re.compile(
            "|".join(re.escape(term) for term in city.scope_terms), re.IGNORECASE
        )
        others = [name for name in (*OTHER_CITIES, *city.other_cities) if name not in city.scope_terms]
        self._other_city = re.compile(
            r"\b(?:" + "|".join(re.escape(name) for name in others) + r")\b"
            r"(?!\s+(?:highway|road|rd|expressway|bypass|route|line|bridge|street))",
            re.IGNORECASE,
        )

    def feed_url(self, query: str) -> str:
        lang, country = self.city.language, self.city.country
        params = {
            "q": f"{query} when:{self.window_days}d",
            "hl": f"{lang}-{country}",
            "gl": country,
            "ceid": f"{country}:{lang}",
        }
        return f"{FEED_URL}?{urlencode(params)}"

    def fetch(self) -> list[RawSourceRecord]:
        """One record per distinct in-scope result across all searches."""
        retrieved_at = utc_now()
        records: dict[str, RawSourceRecord] = {}
        for index, query in enumerate(self.queries):
            if index:
                self._sleep(self.pause_seconds)
            for entry in self._search(query):
                record = self._to_record(entry, query, retrieved_at)
                if record is not None:
                    records.setdefault(record.external_id, record)
        return list(records.values())

    def _search(self, query: str) -> list[Any]:
        url = self.feed_url(query)
        try:
            response = self._client.get(url, headers={"User-Agent": self._user_agent})
        except httpx.HTTPError as error:
            raise ConnectorError(f"Google News RSS search failed: {error}") from error
        if response.status_code in (429, 503):
            raise ConnectorError(
                f"Google News RSS refused the request (HTTP {response.status_code}); "
                "the poll stops here and is retried at the next scheduled poll"
            )
        if response.status_code != 200:
            raise ConnectorError(f"Google News RSS search failed: HTTP {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ConnectorError("Google News RSS response is larger than the allowed maximum")
        parsed = feedparser.parse(response.content, sanitize_html=False)
        if not parsed.get("version"):
            reason = parsed.get("bozo_exception", "not an RSS document")
            raise ConnectorError(f"Google News RSS returned an invalid feed ({reason})")
        return list(parsed.entries)

    def _to_record(self, entry: Any, query: str, retrieved_at: datetime) -> RawSourceRecord | None:
        source = entry.get("source") or {}
        publisher = html_to_text(source.get("title")) or None
        publisher_url = source.get("href") or None
        title = html_to_text(entry.get("title"))
        # Google writes "Headline - Publisher".
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3].rstrip()
        link = (entry.get("link") or "").strip()
        guid = (entry.get("id") or link).strip()
        if not title or not guid or not _LATIN.search(title):
            return None
        if not self._in_scope.search(f"{title} {publisher or ''} {publisher_url or ''}"):
            return None
        if self._other_city.search(title) and not self._in_scope.search(title):
            return None
        return RawSourceRecord(
            source_id=self.source.source_id,
            external_id=guid,
            url=link or None,
            title=title,
            summary=None,
            content_text=None,
            categories=[],
            published_at=_published_at(entry),
            retrieved_at=retrieved_at,
            raw={
                "link": link,
                "title": entry.get("title"),
                "published": entry.get("published"),
                "categories": [],
                "summary_html": "",
                "content_html": "",
                "acquired_from": "Google News RSS search result (headline only)",
                "search_result": {
                    "query": query,
                    "feed_url": self.feed_url(query),
                    "publisher": publisher,
                    "publisher_url": publisher_url,
                    "google_link": link,
                },
            },
            content_hash=sha256_hex("\n".join([title, publisher or ""])),
        )


def create_google_news_rss_connector(
    city_id: str, user_agent: str, *, enabled: bool = True
) -> GoogleNewsRssConnector:
    city = get_city(city_id)
    return GoogleNewsRssConnector(google_news_rss_source(city, enabled=enabled), city, user_agent)
