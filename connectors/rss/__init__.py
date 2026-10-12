from packages.source_models import SourceDefinition

from .base import RssConnector
from .models import DEFAULT_USER_AGENT, RssFeedConfig

__all__ = ["RssConnector", "RssFeedConfig", "create_rss_connector"]


def create_rss_connector(
    source: SourceDefinition, user_agent: str = DEFAULT_USER_AGENT
) -> RssConnector:
    """The one way an RSS source is read: the generic connector plus the source's definition."""
    return RssConnector(RssFeedConfig(source=source, user_agent=user_agent))
