from pydantic import BaseModel, ConfigDict

from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    SourceClass,
    SourceDefinition,
    SourceType,
    TermsStatus,
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


def restricted_by_terms(
    definition: SourceDefinition,
    *,
    terms: str,
    licence: str = "Personal, non-commercial use only; automated access needs written permission",
    since: str = "14 October 2026",
) -> SourceDefinition:
    """`definition`, disconnected because the publisher's terms forbid REI's use.

    The source stays registered, so its stored evidence keeps its source and the
    console shows why it is not read, but it is never fetched (decisions 0024,
    0032). Rebuilt through validation, so the definition's own checks still apply.
    """
    return SourceDefinition.model_validate(
        definition.model_dump()
        | {
            "integration_status": IntegrationStatus.TERMS_REVIEW_REQUIRED,
            "active": False,
            # Read, not formally reviewed by a lawyer: terms_reviewed stays False.
            "terms_status": TermsStatus.RESTRICTED,
            "commercial_use": CommercialUse.NOT_PERMITTED,
            "licence": licence,
            "access_method": "Not accessed: the publisher's terms forbid automated access",
            "notes": f"{definition.notes} Disconnected on {since}: {terms}",
        }
    )


def awaiting_permission(definition: SourceDefinition, *, terms: str) -> SourceDefinition:
    """`definition`, verified working but not connected: the publisher's terms do not
    permit REI's (commercial) use, so it waits for written permission (decision 0033).

    Registered without a connector, so it is never fetched; connecting it once
    permission is granted is moving it to CONNECTED_SOURCES.
    """
    return SourceDefinition.model_validate(
        definition.model_dump()
        | {
            "integration_status": IntegrationStatus.TERMS_REVIEW_REQUIRED,
            "active": False,
            "terms_status": TermsStatus.REVIEW_REQUIRED,
            "commercial_use": CommercialUse.UNKNOWN,
            "access_method": "Not accessed: awaiting the publisher's written permission",
            "notes": f"{definition.notes} Not connected (16 October 2026): {terms}",
        }
    )


def removed_from_rei(
    definition: SourceDefinition, *, licence: str, attribution: str, reason: str
) -> SourceDefinition:
    """`definition`, removed from REI by the user's decision (decision 0026).

    Registered without a connector like a source restricted by its terms, so it
    is never fetched while its stored evidence keeps its source. Its terms were
    read but not formally reviewed, so they are not marked restricted.
    """
    return SourceDefinition.model_validate(
        definition.model_dump()
        | {
            "integration_status": IntegrationStatus.NOT_USABLE,
            "active": False,
            "terms_status": TermsStatus.REVIEW_REQUIRED,
            "commercial_use": CommercialUse.NOT_PERMITTED,
            "licence": licence,
            "attribution": attribution,
            "access_method": "Not accessed: removed from REI",
            "notes": f"{definition.notes} {reason}",
        }
    )
