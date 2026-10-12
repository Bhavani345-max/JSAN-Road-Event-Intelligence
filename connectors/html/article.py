"""Reads one news article from its own page.

For articles that matter but are no longer in a publisher's feed, such as a
long-running closure announced before REI began polling. The article is read
from the structured data (schema.org NewsArticle, JSON-LD) that the publisher
embeds in the page for programs to read; the visible page is not scraped.

The result is a `RawSourceRecord` like any feed item, so the article goes
through the same evidence storage, detection and review as everything else.
"""

import json
import re
from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import ensure_utc, utc_now
from packages.source_models import RawSourceRecord, SourceDefinition

_JSON_LD = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_ARTICLE_TYPES = {"NewsArticle", "Article", "ReportageNewsArticle"}
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _find_article(page: str) -> dict[str, Any] | None:
    for block in _JSON_LD.findall(page):
        try:
            # Publishers put raw line breaks inside strings; allow them.
            data = json.loads(block, strict=False)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type")
            types = set(types) if isinstance(types, list) else {types}
            if types & _ARTICLE_TYPES and item.get("headline") and item.get("articleBody"):
                return item
    return None


def _published_at(value: Any) -> datetime | None:
    try:
        return ensure_utc(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def parse_article_page(
    source: SourceDefinition, url: str, page: str, *, retrieved_at: datetime
) -> RawSourceRecord:
    """The article described by a page's structured data.

    Raises ConnectorError when the page does not describe a news article.
    """
    article = _find_article(page)
    if article is None:
        raise ConnectorError(f"{url}: the page carries no readable news article data")

    title = html_to_text(article["headline"])
    summary = html_to_text(article.get("description"))
    body = html_to_text(article["articleBody"])
    published = article.get("datePublished")
    return RawSourceRecord(
        source_id=source.source_id,
        external_id=url,
        url=url,
        title=title,
        summary=summary or None,
        content_text=body or None,
        categories=[],
        published_at=_published_at(published),
        retrieved_at=retrieved_at,
        raw={
            "link": url,
            "title": article["headline"],
            "published": published,
            "categories": [],
            "summary_html": article.get("description") or "",
            "content_html": article["articleBody"],
            "acquired_from": "article page structured data (schema.org NewsArticle)",
        },
        content_hash=sha256_hex("\n".join([title, summary, body])),
    )


def download_page(
    url: str, user_agent: str, *, client: httpx.Client | None = None
) -> tuple[str, str]:
    """The page at `url`: its address after any redirect, and its markup."""
    try:
        response = (client or httpx).get(
            url, headers={"User-Agent": user_agent}, timeout=30, follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not fetch {url}: {error}") from error
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
    return str(response.url), response.text


class ArticlePageConnector:
    """A connector for exactly one article of a known source, read from its page."""

    def __init__(self, source: SourceDefinition, url: str, user_agent: str) -> None:
        self.source = source
        self.url = url
        self.user_agent = user_agent

    def fetch(self) -> list[RawSourceRecord]:
        # Stored under the publisher's own address for the article, after any redirect.
        url, page = download_page(self.url, self.user_agent)
        return [parse_article_page(self.source, url, page, retrieved_at=utc_now())]
