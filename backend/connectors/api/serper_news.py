"""Google News search results, through the Serper API (https://serper.dev).

A discovery source: it finds Hyderabad road and traffic articles that the
connected feeds do not carry, from whichever publisher wrote them. A search
result is only a headline, a snippet and a link, so each new result's article
is then read from its own page (connectors/html/article.py) and it is the
article, with the publisher's own text and publication time, that is stored
as evidence. When a page carries no readable article, the search result is
stored as it is.

Verified live on 5 and 6 October 2026: POST /news returns up to 10 results
per query for one Serper credit, each with title, link, snippet, source and a
relative date ("3 days ago"). A plain "Hyderabad traffic ..." search returns
mostly Delhi, Bengaluru and Pune articles; leaving those cities out of the
search (-Delhi -Bengaluru ...) and asking for the past month instead of the
past week turned the same search into ten Hyderabad road articles out of ten.
The searches therefore exclude the cities that crowd them out, and a result
whose headline names another city, or that does not mention Hyderabad at all,
is left out before anything is stored.

The API key comes from the SERPER_API_KEY environment variable, never from code.

Since 19 October 2026 (decision 0037) the same search runs for each Indian city
with a place list and searches of its own (Delhi, Mumbai, Bengaluru, Chennai,
Kolkata, Pune, Ahmedabad), as `google-news-serper-<city>`. By the user's
decision of that day they read the article pages as Hyderabad's search does:
Google's headline and snippet rarely state a date, and an event without a
stated start is not shown. A publisher whose terms forbid automated access, or
that the user removed, is left out of every search, result and page alike.
(`read_any_publisher=False` would read only READABLE_PUBLISHERS, as the GDELT
search does.)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import httpx

from connectors.base import ConnectorError
from connectors.html.article import download_page, parse_article_page
from connectors.restricted import readable_publisher, removed_publisher, restricted_publisher
from packages.cities import DEFAULT_CITY_ID, City, get_city, load_cities
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import ensure_utc, utc_now
from packages.event_schema import EventType
from packages.source_models import (
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceType,
    TermsStatus,
)

logger = logging.getLogger(__name__)

SOURCE_ID = "google-news-serper"
ENDPOINT = "https://google.serper.dev/news"

# A search that times out or meets a temporary server error is tried this
# many more times before it is skipped, so one slow reply does not throw away
# the other searches of the poll (and the credits they used).
TRANSIENT_RETRIES = 1


class _TemporarySearchError(ConnectorError):
    """A timeout, network failure, rate limit (429) or server error (5xx)."""

# Cities whose road news crowds Hyderabad's out of a plain search. They are
# left out of every search, and a result whose headline names one is dropped.
CROWDING_CITIES: tuple[str, ...] = (
    "Delhi", "Bengaluru", "Bangalore", "Mumbai", "Chennai", "Pune", "Kolkata", "Noida",
    "Gurugram", "Gurgaon", "Ahmedabad", "Lucknow", "Patna", "Jaipur", "Kochi", "Mysuru",
    "Coimbatore", "Bhopal", "Indore", "Nagpur", "Vijayawada", "Visakhapatnam", "Thane",
)  # fmt: skip

# The city the original source searches for. The searches are the city's own
# (packages/cities/data/<city>.json, "discovery.queries"), each naming the
# city or an authority of it and one kind of road measure, with the crowding
# cities excluded. One Serper credit each, every poll.
CITY_ID = DEFAULT_CITY_ID


def _own_names(city: City) -> set[str]:
    return {term.lower() for term in (city.name, *city.scope_terms)}


def other_cities_for(city: City) -> tuple[str, ...]:
    """The cities whose news crowds this city's out, never its own names.

    Hyderabad's are the crowding cities; another city's also include Hyderabad
    and the neighbours its file names (Delhi: Noida, Gurugram, ...).
    """
    own = _own_names(city)
    extra = () if city.id == DEFAULT_CITY_ID else ("Hyderabad", "Secunderabad", *city.other_cities)
    names = dict.fromkeys(name for name in (*CROWDING_CITIES, *extra) if name.lower() not in own)
    return tuple(names)


def queries_for(city_id: str = CITY_ID) -> tuple[str, ...]:
    """A city's searches. Hyderabad's leave out the cities that crowd it out;
    another city's leave out none: on 19 October 2026 leaving out the other
    large cities cut Mumbai's and Ahmedabad's results to a few (their news names
    Pune, Delhi or Mumbai too), and results about another city are dropped
    before anything is stored anyway."""
    city = get_city(city_id)
    if city.id != DEFAULT_CITY_ID:
        return city.discovery.queries
    exclude = " ".join(f"-{name}" for name in CROWDING_CITIES[:8])
    return tuple(f"{query} {exclude}" for query in city.discovery.queries)


def searched_cities() -> tuple[City, ...]:
    """The cities searched besides Hyderabad (decision 0037): each Indian city
    with a place list (to locate what it finds) and searches of its own."""
    return tuple(
        city
        for city in load_cities().values()
        if city.id != DEFAULT_CITY_ID
        and city.level == "city"
        and city.country == "IN"
        and city.gazetteer
        and city.discovery.queries
    )


def source_id_for(city_id: str) -> str:
    return SOURCE_ID if city_id == DEFAULT_CITY_ID else f"{SOURCE_ID}-{city_id}"


DEFAULT_QUERIES: tuple[str, ...] = queries_for()
# Google's "past week" (qdr:w), "past month" (qdr:m) and "past year" (qdr:y).
DEFAULT_WINDOW = "qdr:w"
WINDOWS = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}
# Results per search: up to 100 for two credits (10 cost one), so five times
# the results per credit (21 October 2026, the user asked to remove the caps).
DEFAULT_RESULTS_PER_QUERY = 100
CREDITS_PER_SEARCH = 2 if DEFAULT_RESULTS_PER_QUERY > 10 else 1
# A result must mention one of these to be about the PoC's city at all.
DEFAULT_SCOPE_TERMS: tuple[str, ...] = ("Hyderabad", "Secunderabad", "Cyberabad", "Rachakonda")
POLLING_FREQUENCY_MINUTES = 480
# The other cities' searches run once a day: a past-week search catches what
# was announced since, and each city's 8-9 searches cost one credit each.
CITY_POLLING_FREQUENCY_MINUTES = 1440
# Article pages read in one poll; further new results keep their search snippet.
# None: every new result's page is read (reading a page costs no credit).
MAX_ARTICLE_PAGES_PER_POLL: int | None = None
# A headline with no Latin letters is in a script REI does not read.
_LATIN = re.compile(r"[A-Za-z]{3}")


def serper_news_source(*, connected: bool, city_id: str = CITY_ID) -> SourceDefinition:
    """The source as it stands with (`connected`) or without an API key: the
    original Hyderabad search, or another city's (decision 0037)."""
    if city_id != CITY_ID:
        return _city_source(get_city(city_id), connected=connected)
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Google News search",
        organization="Google News results via Serper.dev",
        authority_type="SEARCH_API",
        # Finds news articles: discovery-only, like the news feeds.
        source_tier=4,
        source_type=SourceType.API,
        source_class=SourceClass.DISCOVERY,
        discovery_only=True,
        country="IN",
        region="Telangana",
        city="hyderabad",
        cost_category=CostCategory.FREE_WITH_LIMITS,
        rate_limit=(
            "2,500 free credits once per account, then paid packs (USD 50 per 50,000); "
            "1 credit per search of up to 10 results, 2 for 11-100 (serper.dev pricing, "
            "checked 6 October 2026)"
        ),
        terms_status=TermsStatus.REVIEW_REQUIRED,
        source_url="https://serper.dev/",
        endpoint=ENDPOINT,
        access_method="Commercial search API; API key in SERPER_API_KEY",
        integration_status=(
            IntegrationStatus.CONNECTED if connected else IntegrationStatus.REQUIRES_ACCESS
        ),
        active=connected,
        polling_frequency_minutes=POLLING_FREQUENCY_MINUTES,
        language="en",
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="serper_news",
        terms_reviewed=False,
        evidence_retention=(
            "For each new search result: the article read from the publisher's page "
            "(headline, summary, body, publication time) together with the search "
            "result that led to it, and a SHA-256 content hash."
        ),
        notes=(
            f"{len(DEFAULT_QUERIES)} Hyderabad road searches of the past week, every "
            f"{POLLING_FREQUENCY_MINUTES // 60} hours, up to {DEFAULT_RESULTS_PER_QUERY} results each "
            f"({len(DEFAULT_QUERIES) * CREDITS_PER_SEARCH} Serper credits a poll, "
            f"{len(DEFAULT_QUERIES) * CREDITS_PER_SEARCH * 24 * 60 // POLLING_FREQUENCY_MINUTES} a day). "
            "A deeper sweep of the past month or year is run by hand with "
            "backend/cli/search_sweep.py. Results come from any publisher Google lists; their "
            "reliability is not assessed, so every event is a lead for review. "
            + ("" if connected else "Not connected: SERPER_API_KEY is not set.")
        ).strip(),
    )


def _city_source(city: City, *, connected: bool) -> SourceDefinition:
    queries = queries_for(city.id)
    per_day = len(queries) * CREDITS_PER_SEARCH * 24 * 60 // CITY_POLLING_FREQUENCY_MINUTES
    return SourceDefinition(
        source_id=source_id_for(city.id),
        source_name=f"Google News search ({city.name})",
        organization="Google News results via Serper.dev",
        authority_type="SEARCH_API",
        source_tier=4,
        source_type=SourceType.API,
        source_class=SourceClass.DISCOVERY,
        discovery_only=True,
        country=city.country,
        region=city.region,
        city=city.id,
        cost_category=CostCategory.FREE_WITH_LIMITS,
        rate_limit=(
            "Shares the SERPER_API_KEY credits: 1 credit per search of up to 10 results, "
            "2 for 11-100 (serper.dev pricing, checked 6 October 2026)"
        ),
        terms_status=TermsStatus.REVIEW_REQUIRED,
        source_url="https://serper.dev/",
        endpoint=ENDPOINT,
        access_method="Commercial search API; API key in SERPER_API_KEY",
        integration_status=(
            IntegrationStatus.CONNECTED if connected else IntegrationStatus.REQUIRES_ACCESS
        ),
        active=connected,
        polling_frequency_minutes=CITY_POLLING_FREQUENCY_MINUTES,
        language="en",
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="serper_news",
        terms_reviewed=False,
        evidence_retention=(
            "For each new search result: the article read from the publisher's page "
            "(headline, summary, body, publication time) together with the search result "
            "that led to it, and a SHA-256 content hash; Google's result alone when the "
            "page carries no readable article."
        ),
        notes=(
            f"{len(queries)} {city.name} road searches of the past week, once a day "
            f"({per_day} Serper credits a day). Results from publishers whose terms forbid "
            "automated access, or that the user removed, are left out. Article pages are "
            "read as for Hyderabad (the user's decision of 19 October 2026). Results come "
            "from any publisher Google lists; every event is a lead for review. "
            + ("" if connected else "Not connected: SERPER_API_KEY is not set.")
        ).strip(),
    )


_AGO = re.compile(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", re.IGNORECASE)
_UNIT = {
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
}
_DATE_FORMATS = ("%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y")


def parse_result_date(text: str | None, *, now: datetime) -> datetime | None:
    """When Google says a result was published: "3 days ago" or "Oct 3, 2026".

    A relative date is only as exact as its unit. None when it cannot be read.
    """
    text = (text or "").strip()
    match = _AGO.fullmatch(text)
    if match:
        return now - int(match.group(1)) * _UNIT[match.group(2).lower()]
    for date_format in _DATE_FORMATS:
        try:
            return ensure_utc(datetime.strptime(text, date_format))
        except ValueError:
            continue
    return None


class SerperNewsConnector:
    """Searches Google News for one city's road events and reads the articles found."""

    def __init__(
        self,
        source: SourceDefinition,
        api_key: str,
        user_agent: str,
        *,
        queries: tuple[str, ...] = DEFAULT_QUERIES,
        scope_terms: tuple[str, ...] = DEFAULT_SCOPE_TERMS,
        other_cities: tuple[str, ...] = CROWDING_CITIES,
        country: str = "in",
        read_any_publisher: bool = True,
        whole_words: bool = False,
        window: str = DEFAULT_WINDOW,
        results_per_query: int = DEFAULT_RESULTS_PER_QUERY,
        client: httpx.Client | None = None,
    ) -> None:
        self.source = source
        self.queries = queries
        self.window = window
        self.results_per_query = results_per_query
        self._country = country
        # Whether any page not refused is read (every city's search, decision
        # 0037), or only those of publishers whose terms permit it.
        self._read_any_publisher = read_any_publisher
        # Another city's names include short ones ("MCD", "BMC"), matched as
        # whole words only.
        terms = "|".join(re.escape(term) for term in scope_terms)
        self._in_scope = re.compile(rf"\b(?:{terms})\b" if whole_words else terms, re.IGNORECASE)
        # A headline about another city; "Mumbai Highway" is a road in Hyderabad.
        self._other_city = re.compile(
            r"\b(?:"
            + "|".join(re.escape(city) for city in other_cities)
            + r")\b(?!\s+(?:highway|road|rd|expressway|bypass|route|line))",
            re.IGNORECASE,
        )
        self._api_key = api_key
        self._user_agent = user_agent
        self._client = client or httpx.Client(timeout=30, follow_redirects=True)
        self._pages_read = 0

    @classmethod
    def for_city(
        cls, source: SourceDefinition, city: City, api_key: str, user_agent: str, **options: Any
    ) -> "SerperNewsConnector":
        """Another city's search (decision 0037): its own searches, names and
        neighbours; article pages read as Hyderabad's are (the user's decision
        of 19 October 2026), unless `read_any_publisher=False` is given."""
        return cls(
            source,
            api_key,
            user_agent,
            **{
                "queries": queries_for(city.id),
                "scope_terms": tuple(dict.fromkeys((city.name, *city.scope_terms))),
                "other_cities": other_cities_for(city),
                "country": city.country.lower(),
                "read_any_publisher": True,
                "whole_words": True,
                **options,
            },
        )

    def fetch(self) -> list[RawSourceRecord]:
        """One record per distinct in-scope article link across all searches.

        A search that still fails temporarily after a retry is skipped and the
        others are kept; the poll fails only if every search failed. Any other
        failure (a refused key, a bad request) fails the poll at once.
        """
        self._pages_read = 0
        retrieved_at = utc_now()
        records: dict[str, RawSourceRecord] = {}
        skipped: list[str] = []
        for query in self.queries:
            try:
                results = self._search_with_retry(query)
            except _TemporarySearchError as error:
                logger.warning("%s: skipped the search %r (%s)", self.source.source_id, query, error)
                skipped.append(query)
                continue
            for result in results:
                record = self._to_record(result, query, retrieved_at)
                if record is not None:
                    records.setdefault(record.external_id, record)
        if self.queries and len(skipped) == len(self.queries):
            raise ConnectorError(f"Serper news search failed: all {len(skipped)} searches failed")
        if skipped:
            logger.warning(
                "%s: %d of %d searches skipped after a retry",
                self.source.source_id,
                len(skipped),
                len(self.queries),
            )
        return list(records.values())

    def _search_with_retry(self, query: str) -> list[dict[str, Any]]:
        for attempt in range(TRANSIENT_RETRIES + 1):
            try:
                return self._search(query)
            except _TemporarySearchError:
                if attempt == TRANSIENT_RETRIES:
                    raise
        raise AssertionError("unreachable")

    def complete(self, record: RawSourceRecord) -> RawSourceRecord:
        """Replace a new search result by the article it points to.

        Called by the ingestion pipeline for results not stored before. The
        record keeps its identifier (the link Google gave) and the search
        result it came from; the text and publication time become the article's.
        """
        if not record.url or (
            MAX_ARTICLE_PAGES_PER_POLL is not None and self._pages_read >= MAX_ARTICLE_PAGES_PER_POLL
        ):
            return record
        if not self._read_any_publisher and not readable_publisher(record.url):
            return record
        self._pages_read += 1
        try:
            _, page = download_page(record.url, self._user_agent, client=self._client)
            article = parse_article_page(
                self.source, record.url, page, retrieved_at=record.retrieved_at
            )
        except ConnectorError as error:
            logger.info("%s: kept the search result only (%s)", self.source.source_id, error)
            return record
        return article.model_copy(
            update={
                # Google's date stands in when the page states none.
                "published_at": article.published_at or record.published_at,
                "raw": {
                    **article.raw,
                    "search_result": record.raw["search_result"],
                    # Whose publication time it is: a day may be counted from the
                    # article's own, never from the search result's (decision 0038).
                    "published_at_from": "article" if article.published_at else "search_result",
                },
            }
        )

    def _search(self, query: str) -> list[dict[str, Any]]:
        try:
            response = self._client.post(
                ENDPOINT,
                headers={"X-API-KEY": self._api_key, "User-Agent": self._user_agent},
                # The city's country's results, in English, from the chosen window.
                json={
                    "q": query,
                    "gl": self._country,
                    "hl": "en",
                    "tbs": self.window,
                    "num": self.results_per_query,
                },
            )
            response.raise_for_status()
            return response.json().get("news") or []
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            if status == 429 or status >= 500:
                raise _TemporarySearchError(f"Serper news search failed: HTTP {status}") from error
            reason = "the API key was refused" if status in (401, 403) else f"HTTP {status}"
            raise ConnectorError(f"Serper news search failed: {reason}") from error
        except httpx.TransportError as error:
            # Timeouts and network failures.
            raise _TemporarySearchError(f"Serper news search failed: {error}") from error
        except (httpx.HTTPError, ValueError) as error:
            raise ConnectorError(f"Serper news search failed: {error}") from error

    def _to_record(
        self, result: dict[str, Any], query: str, retrieved_at: datetime
    ) -> RawSourceRecord | None:
        title = html_to_text(result.get("title"))
        link = (result.get("link") or "").strip()
        if not title or not link.startswith("http"):
            return None
        snippet = html_to_text(result.get("snippet"))
        # Search noise from other cities is not evidence of anything here, nor
        # is an article in a script REI does not read.
        if not self._in_scope.search(f"{title} {snippet} {link}") or not _LATIN.search(title):
            return None
        if self._other_city.search(title) and not self._in_scope.search(title):
            return None
        # A publisher whose terms forbid automated access is not used at all:
        # neither its page nor the search result that links to it (decision
        # 0024); nor one the user removed from REI (decision 0026).
        if restricted_publisher(link) or removed_publisher(link):
            return None
        return RawSourceRecord(
            source_id=self.source.source_id,
            external_id=link,
            url=link,
            title=title,
            summary=snippet or None,
            content_text=None,
            categories=[],
            published_at=parse_result_date(result.get("date"), now=retrieved_at),
            retrieved_at=retrieved_at,
            raw={
                "link": link,
                "title": result.get("title"),
                "published": result.get("date"),
                "categories": [],
                "summary_html": result.get("snippet") or "",
                "content_html": "",
                "acquired_from": "Google News search result via Serper",
                "search_result": {
                    "query": query,
                    "publisher": result.get("source"),
                    "date": result.get("date"),
                    "title": result.get("title"),
                    "snippet": result.get("snippet"),
                },
            },
            content_hash=sha256_hex("\n".join([title, snippet])),
        )
