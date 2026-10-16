"""GDELT news search (DOC 2.0 API): a DISCOVERY source, one per city with a place list.

The GDELT Project (https://www.gdeltproject.org/) monitors news worldwide and
offers a free full-text search of the last three months of coverage:

    https://api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=ArtList&format=json
        &maxrecords=250&timespan=1d&sort=DateDesc

No key is needed. Each result is an article's address, headline, the time
GDELT saw it ("seendate", e.g. 20261016T074500Z), its site, language and the
country of the outlet. Verified live on 16 October 2026 (the Delhi search
returned "Delhi traffic advisory today: 21 roads around Connaught Place
restricted from 3 PM ..."). GDELT asks for at most one request every five
seconds and answers faster requests with HTTP 429 and "Please limit requests
to one every 5 seconds"; every GDELT source in the process therefore shares
one pace (`_PACE`), and a refusal ends the poll until the next one.

Query syntax (GDELT's documentation): quoted phrases, one level of
"(a OR b)" blocks, "-" to exclude, sourcecountry:<FIPS code> (India IN,
South Africa SF) and sourcelang:english. A city's searches are its
`discovery.gdelt_queries`, or its name with REI's road phrases.

GDELT's own data may be used freely, also commercially, with a citation
(gdeltproject.org/about.html#termsofuse). The articles it points to are the
publishers', under each publisher's terms (decision 0033,
connectors/restricted.py):

- a publisher whose terms forbid automated access, or that the user removed
  from REI, is left out before anything is stored or fetched;
- a publisher whose terms permit REI to read and keep its articles
  (READABLE_PUBLISHERS) has the article read from its page, and that article,
  with the publisher's text and publication time, is the evidence;
- from any other publisher only GDELT's result is kept: headline, address
  and the time GDELT saw it. Its page is never requested.

Results not naming the city, naming another city in the headline, or not in
Latin script are dropped, as for the other search sources. Every event found
is a lead for review.
"""

import logging
import re
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from connectors.base import ConnectorError
from connectors.html.article import download_page, parse_article_page
from connectors.restricted import readable_publisher, removed_publisher, restricted_publisher
from packages.cities import City
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

API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
TERMS_URL = "https://www.gdeltproject.org/about.html#termsofuse"
POLLING_FREQUENCY_MINUTES = 120
# Each poll searches the last day: a missed poll loses nothing, and results
# already held are recognised by their address and headline.
TIMESPAN = "1d"
MAX_RECORDS = 250
# GDELT's limit is one request every five seconds, for all of REI's GDELT sources.
MIN_SECONDS_BETWEEN_REQUESTS = 6.0
# Article pages read in one poll; further new results keep GDELT's headline.
MAX_ARTICLE_PAGES_PER_POLL = 40
MAX_RESPONSE_BYTES = 5 * 1024 * 1024

# GDELT names countries by FIPS 10-4 code, not ISO 3166 (Country Lookup).
FIPS_COUNTRY = {
    "IN": "IN", "ZA": "SF", "AU": "AS", "GB": "UK", "US": "US", "CA": "CA", "FR": "FR", "FI": "FI",
}  # fmt: skip
# The road phrases a city search asks for, at least one in the article.
ROAD_PHRASES: tuple[str, ...] = (
    '"traffic advisory"', '"traffic diversion"', '"traffic diversions"', '"road closed"',
    '"roads closed"', '"road closure"', '"traffic restrictions"', '"diversions"',
    '"waterlogging"', '"road blocked"',
)  # fmt: skip

# Cities whose news crowds a search; a headline naming one of them (and not
# the city searched for) is about that other city.
OTHER_CITIES: tuple[str, ...] = (
    "Delhi", "Bengaluru", "Bangalore", "Mumbai", "Chennai", "Pune", "Kolkata", "Noida",
    "Gurugram", "Gurgaon", "Ahmedabad", "Lucknow", "Patna", "Jaipur", "Kochi", "Hyderabad",
    "Chandigarh", "Bhopal", "Indore", "Nagpur", "Surat", "Thane", "Navi Mumbai",
)  # fmt: skip
# A headline with no Latin letters is in a script REI does not read.
_LATIN = re.compile(r"[A-Za-z]{3}")
# GDELT writes its headlines with spaces before punctuation: "Delhi : Security".
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,:;?!.%])")
_THOUSANDS = re.compile(r"(\d) , (\d{3})\b")


class _Pace:
    """Keeps GDELT requests at least `MIN_SECONDS_BETWEEN_REQUESTS` apart, process-wide."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self, seconds: float, sleep: Callable[[float], None], clock: Callable[[], float]) -> None:
        with self._lock:
            pause = self._last + seconds - clock()
            if pause > 0:
                sleep(pause)
            self._last = clock()


_PACE = _Pace()


def source_id_for(city: City) -> str:
    return f"gdelt-{city.id}"


def queries_for(city: City) -> tuple[str, ...]:
    """The city's GDELT searches: its own, or its name with the road phrases."""
    if city.discovery.gdelt_queries:
        return city.discovery.gdelt_queries
    country = FIPS_COUNTRY.get(city.country)
    filters = (f"sourcecountry:{country} " if country else "") + "sourcelang:english"
    return (f'"{city.name}" ({" OR ".join(ROAD_PHRASES)}) {filters}',)


def clean_title(title: str) -> str:
    """GDELT's headline as the publisher wrote it, as near as can be told."""
    text = html_to_text(title).strip()
    text = _THOUSANDS.sub(r"\1,\2", text)
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    return re.sub(r"\s{2,}", " ", text)


def parse_seendate(value: str | None) -> datetime | None:
    """GDELT's "20261016T074500Z" as a UTC time; None when it cannot be read."""
    try:
        return datetime.strptime(value or "", "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def gdelt_source(city: City, *, enabled: bool = True) -> SourceDefinition:
    """The search for one city; listed but never run unless `enabled`."""
    queries = queries_for(city)
    return SourceDefinition(
        source_id=source_id_for(city),
        source_name=f"GDELT news search ({city.name})",
        organization="The GDELT Project",
        authority_type="SEARCH_API",
        # Finds news articles: discovery-only, like the news feeds.
        source_tier=4,
        source_type=SourceType.API,
        source_class=SourceClass.DISCOVERY,
        discovery_only=True,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url="https://www.gdeltproject.org/",
        endpoint=API_URL,
        access_method="Public DOC 2.0 API (ArtList, JSON), no credentials",
        integration_status=IntegrationStatus.CONNECTED if enabled else IntegrationStatus.VALIDATED,
        active=enabled,
        polling_frequency_minutes=POLLING_FREQUENCY_MINUTES,
        language=city.language,
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="gdelt_doc",
        cost_category=CostCategory.FREE_WITH_LIMITS,
        rate_limit=(
            "One request every 5 seconds; faster requests get HTTP 429 (verified 16 October 2026)"
        ),
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "GDELT's data is available for unlimited and unrestricted use for any academic, "
            f"commercial, or governmental use, with a citation ({TERMS_URL}). The articles it "
            "links to are their publishers', under each publisher's terms."
        ),
        attribution="The GDELT Project (https://www.gdeltproject.org/)",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=False,
        real_time=False,
        terms_reviewed=False,
        evidence_retention=(
            "For each new result: GDELT's result (address, headline, seen time, site, language, "
            "country) and a SHA-256 hash. From a publisher whose terms permit it, the article "
            "read from its page (headline, summary, body, publication time) instead, with "
            "GDELT's result kept beside it."
        ),
        notes=(
            f"{len(queries)} search{'es' if len(queries) > 1 else ''} of the last day of news "
            f"for {city.name}, every {POLLING_FREQUENCY_MINUTES // 60} hours, at most one GDELT "
            "request every 6 seconds. Publishers whose terms forbid automated access are left "
            "out; articles are read only from publishers whose terms permit it, otherwise "
            "GDELT's headline is kept. Discovery only: results are leads for review, never "
            "confirmation."
            + (
                ""
                if enabled
                else " Switched off by default (decision 0033): on 16 October 2026 GDELT's API "
                "refused 33 of 44 requests. GDELT_SEARCH_ENABLED=true switches it on."
            )
        ),
    )


class GdeltConnector:
    """Searches GDELT for one city's road news and reads the articles found."""

    def __init__(
        self,
        source: SourceDefinition,
        city: City,
        user_agent: str,
        *,
        queries: tuple[str, ...] | None = None,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        pace: _Pace = _PACE,
        min_seconds_between_requests: float = MIN_SECONDS_BETWEEN_REQUESTS,
        max_article_pages: int = MAX_ARTICLE_PAGES_PER_POLL,
    ) -> None:
        self.source = source
        self.city = city
        self.queries = queries if queries is not None else queries_for(city)
        self._user_agent = user_agent
        self._client = client or httpx.Client(timeout=40, follow_redirects=True)
        self._sleep = sleep
        self._clock = clock
        self._pace = pace
        self._gap = min_seconds_between_requests
        self._max_pages = max_article_pages
        self._pages_read = 0
        self._in_scope = re.compile(
            "|".join(rf"\b{re.escape(term)}\b" for term in city.scope_terms), re.IGNORECASE
        )
        scope = {term.lower() for term in city.scope_terms}
        others = [name for name in (*OTHER_CITIES, *city.other_cities) if name.lower() not in scope]
        self._other_city = re.compile(
            r"\b(?:" + "|".join(re.escape(name) for name in others) + r")\b"
            r"(?!\s+(?:highway|road|rd|expressway|bypass|route|line|bridge|street))",
            re.IGNORECASE,
        )

    def fetch(self) -> list[RawSourceRecord]:
        """One record per distinct in-scope article across the city's searches."""
        self._pages_read = 0
        retrieved_at = utc_now()
        records: dict[str, RawSourceRecord] = {}
        for query in self.queries:
            for article in self._search(query):
                record = self._to_record(article, query, retrieved_at)
                if record is not None:
                    records.setdefault(record.external_id, record)
        return list(records.values())

    def complete(self, record: RawSourceRecord) -> RawSourceRecord:
        """Replace a new result by the article it points to (new results only).

        Only a publisher whose terms permit it is read (READABLE_PUBLISHERS);
        any other result stays GDELT's own: headline, address and seen time.
        """
        if self._pages_read >= self._max_pages or not readable_publisher(record.url):
            return record
        self._pages_read += 1
        try:
            _, page = download_page(record.url, self._user_agent, client=self._client)
            article = parse_article_page(self.source, record.url, page, retrieved_at=record.retrieved_at)
        except ConnectorError as error:
            logger.info("%s: kept GDELT's result only (%s)", self.source.source_id, error)
            return record
        return article.model_copy(
            update={
                # GDELT's seen time stands in when the page states none.
                "published_at": article.published_at or record.published_at,
                "raw": {**article.raw, "search_result": record.raw["search_result"]},
            }
        )

    def _search(self, query: str) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(MAX_RECORDS),
            "timespan": TIMESPAN,
            "sort": "DateDesc",
        }
        self._pace.wait(self._gap, self._sleep, self._clock)
        try:
            response = self._client.get(API_URL, params=params, headers={"User-Agent": self._user_agent})
        except httpx.HTTPError as error:
            raise ConnectorError(f"GDELT search failed: {error}") from error
        if response.status_code in (429, 503):
            raise ConnectorError(
                f"GDELT refused the request (HTTP {response.status_code}): "
                f"{response.text.strip()[:120]}; retried at the next poll"
            )
        if response.status_code != 200:
            raise ConnectorError(f"GDELT search failed: HTTP {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ConnectorError("GDELT response is larger than the allowed maximum")
        if not response.content.strip():
            return []
        try:
            document = response.json()
        except ValueError:
            # GDELT answers a query it cannot run with a plain-text message.
            raise ConnectorError(
                f"GDELT did not run the search: {response.text.strip()[:200]}"
            ) from None
        articles = document.get("articles") if isinstance(document, dict) else None
        return [article for article in articles or [] if isinstance(article, dict)]

    def _to_record(
        self, article: dict[str, Any], query: str, retrieved_at: datetime
    ) -> RawSourceRecord | None:
        link = (article.get("url") or "").strip()
        title = clean_title(article.get("title") or "")
        if not link.startswith("http") or not title or not _LATIN.search(title):
            return None
        # A publisher whose terms forbid automated access, or that the user
        # removed from REI, is not used at all.
        if restricted_publisher(link) or removed_publisher(link):
            return None
        if not self._in_scope.search(f"{title} {link}"):
            return None
        if self._other_city.search(title) and not self._in_scope.search(title):
            return None
        return RawSourceRecord(
            source_id=self.source.source_id,
            external_id=link,
            url=link,
            title=title,
            summary=None,
            content_text=None,
            categories=[],
            published_at=parse_seendate(article.get("seendate")),
            retrieved_at=retrieved_at,
            raw={
                "link": link,
                "title": article.get("title"),
                "published": article.get("seendate"),
                "categories": [],
                "summary_html": "",
                "content_html": "",
                "acquired_from": "GDELT DOC 2.0 search result",
                "search_result": {
                    "query": query,
                    "domain": article.get("domain"),
                    "language": article.get("language"),
                    "sourcecountry": article.get("sourcecountry"),
                    "seendate": article.get("seendate"),
                    "title": article.get("title"),
                },
            },
            content_hash=sha256_hex("\n".join([title, link])),
        )
