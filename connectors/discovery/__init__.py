"""Discovery sources: find reports; are never evidence that an event is real."""

from .google_news_rss import (
    GoogleNewsRssConnector,
    create_google_news_rss_connector,
    google_news_rss_source,
)

__all__ = ["GoogleNewsRssConnector", "create_google_news_rss_connector", "google_news_rss_source"]
