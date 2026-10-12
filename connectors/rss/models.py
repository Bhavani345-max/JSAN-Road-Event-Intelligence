from pydantic import BaseModel, ConfigDict

from packages.event_schema import EventType
from packages.source_models import (
    CostCategory,
    IntegrationStatus,
    SourceClass,
    SourceDefinition,
    SourceType,
)

DEFAULT_USER_AGENT = "JSAN-REI/1.0 (road event intelligence; RSS reader)"


class RssFeedConfig(BaseModel):
    """Everything needed to read one RSS/Atom feed."""

    model_config = ConfigDict(frozen=True)

    source: SourceDefinition
    timeout_seconds: float = 20.0
    user_agent: str = DEFAULT_USER_AGENT
    # Refuse responses larger than this; a feed is never legitimately this big.
    max_response_bytes: int = 10 * 1024 * 1024


def news_rss_source(
    *,
    source_id: str,
    source_name: str,
    organization: str,
    source_url: str,
    endpoint: str,
    notes: str,
    polling_frequency_minutes: int = 30,
    country: str = "IN",
    region: str | None = "Telangana",
    city: str | None = "hyderabad",
    language: str = "en",
) -> SourceDefinition:
    """A connected news feed. What every news RSS source has in common lives here.

    News publishers are neither an authority, an event organiser nor an approved
    partner, so under REI's tier definitions they are tier 4: discovery-only.
    Their reports are leads for human validation, never confirmed events.
    """
    return SourceDefinition(
        source_id=source_id,
        source_name=source_name,
        organization=organization,
        authority_type="NEWS_MEDIA",
        source_tier=4,
        source_type=SourceType.RSS,
        source_class=SourceClass.PUBLISHER,
        country=country,
        region=region,
        city=city,
        discovery_only=True,
        cost_category=CostCategory.FREE_PUBLIC,
        source_url=source_url,
        endpoint=endpoint,
        access_method="Public RSS feed, no credentials",
        integration_status=IntegrationStatus.CONNECTED,
        active=True,
        polling_frequency_minutes=polling_frequency_minutes,
        language=language,
        events_supported=tuple(event_type.value for event_type in EventType),
        parser_type="rss",
        # No publisher's terms have been formally reviewed for REI's purpose yet.
        terms_reviewed=False,
        evidence_retention=(
            "Each feed item is stored in full: title, link, publication and retrieval "
            "times, summary and body markup as received, and a SHA-256 content hash."
        ),
        notes=notes,
    )
