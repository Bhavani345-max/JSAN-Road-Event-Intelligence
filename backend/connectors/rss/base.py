import calendar
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from connectors.base import ConnectorError, refusal_detail
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import utc_now
from packages.source_models import RawSourceRecord, SourceDefinition

from .models import RssFeedConfig

logger = logging.getLogger(__name__)


class RssConnector:
    """Reads any RSS or Atom feed into `RawSourceRecord`s.

    Adding another news feed needs only a new `RssFeedConfig` (see
    telangana_today.py); nothing here is specific to one publisher.
    """

    def __init__(self, config: RssFeedConfig) -> None:
        if not config.source.endpoint:
            raise ValueError(f"RSS source {config.source.source_id} has no feed endpoint")
        self.config = config
        self.source: SourceDefinition = config.source

    def fetch(self) -> list[RawSourceRecord]:
        return self.parse(self._download(), retrieved_at=utc_now())

    def _download(self) -> bytes:
        url = self.source.endpoint
        assert url is not None
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": self.config.user_agent},
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            refused = error.response
            raise ConnectorError(
                f"Could not fetch {url}: HTTP {refused.status_code} {refused.reason_phrase}"
                + refusal_detail(refused)
            ) from error
        except httpx.HTTPError as error:
            raise ConnectorError(f"Could not fetch {url}: {error}") from error
        if len(response.content) > self.config.max_response_bytes:
            raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
        return response.content

    def parse(self, body: bytes, *, retrieved_at: datetime) -> list[RawSourceRecord]:
        """Parse a feed document. Unusable items are skipped, not fatal."""
        # Keep the publisher's markup as received: it is stored as evidence and
        # is only ever shown as plain text.
        parsed = feedparser.parse(body, sanitize_html=False)
        if not parsed.get("version"):
            reason = parsed.get("bozo_exception", "not an RSS or Atom document")
            raise ConnectorError(f"{self.source.source_id}: invalid feed ({reason})")

        records: list[RawSourceRecord] = []
        for entry in parsed.entries:
            record = self._to_record(entry, retrieved_at)
            if record is None:
                logger.warning(
                    "%s: skipped a feed item without a title or identifier",
                    self.source.source_id,
                )
                continue
            records.append(record)
        return records

    def _to_record(self, entry: Any, retrieved_at: datetime) -> RawSourceRecord | None:
        title = html_to_text(entry.get("title"))
        link = (entry.get("link") or "").strip() or None
        external_id = (entry.get("id") or "").strip() or link
        if not title or not external_id:
            return None

        summary_html = entry.get("summary") or ""
        contents = entry.get("content") or []
        # The first content element that has any; some feeds (The New Indian
        # Express) put an empty one first and the article in the next.
        content_html = next(
            (c.get("value", "") for c in contents if (c.get("value") or "").strip()), ""
        )
        categories = [tag.get("term", "").strip() for tag in entry.get("tags") or []]

        return RawSourceRecord(
            source_id=self.source.source_id,
            external_id=external_id,
            url=link,
            title=title,
            summary=html_to_text(summary_html) or None,
            content_text=html_to_text(content_html) or None,
            categories=[category for category in categories if category],
            published_at=_published_at(entry),
            retrieved_at=retrieved_at,
            raw={
                "guid": entry.get("id"),
                "link": link,
                "title": entry.get("title"),
                "published": entry.get("published") or dict.get(entry, "updated"),
                "author": entry.get("author"),
                "categories": categories,
                "summary_html": summary_html,
                "content_html": content_html,
            },
            content_hash=sha256_hex("\n".join([title, summary_html, content_html])),
        )


def _published_at(entry: Any) -> datetime | None:
    """Publication time in UTC, or None when missing or unparseable."""
    # dict.get: feedparser's own lookup aliases "updated" to "published" and warns.
    parsed = entry.get("published_parsed") or dict.get(entry, "updated_parsed")
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    except (OverflowError, ValueError):
        return None
