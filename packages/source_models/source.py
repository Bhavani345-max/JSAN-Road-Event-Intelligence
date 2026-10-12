from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(StrEnum):
    """How a source publishes. One connector family exists per type."""

    RSS = "RSS"
    API = "API"
    HTML = "HTML"
    PDF = "PDF"
    CSV = "CSV"
    EMAIL = "EMAIL"
    PARTNER_FEED = "PARTNER_FEED"
    # Published only for people to read (social posts, messaging channels).
    MANUAL = "MANUAL"


class SourceClass(StrEnum):
    """What kind of body stands behind a source, which is what its authority rests on.

    Independent of `SourceType` (the format) and of the tier (REI's trust
    level): a police force may publish PDFs, a newspaper an API.
    """

    # Traffic police, road authority, transport authority, municipal
    # authority, traffic management centre, official disruption API.
    AUTHORITATIVE_OFFICIAL = "AUTHORITATIVE_OFFICIAL"
    # Government open-data portals and GIS services.
    GOVERNMENT_OPEN_DATA = "GOVERNMENT_OPEN_DATA"
    # Approved partner or operator feeds.
    PARTNER = "PARTNER"
    # Newspapers, news websites and their feeds. A newspaper reporting what
    # the police announced is still a newspaper.
    PUBLISHER = "PUBLISHER"
    # Search and aggregation (Google News). Finds articles; is not a source of events.
    DISCOVERY = "DISCOVERY"
    # Paid traffic data providers (HERE, TomTom, …). Future and optional.
    COMMERCIAL = "COMMERCIAL"


class IntegrationStatus(StrEnum):
    """Where a source stands. Only CONNECTED sources are ever fetched."""

    CONNECTED = "CONNECTED"
    # Researched and reachable, but not integrated.
    DISCOVERED = "DISCOVERED"
    # Researched and real data fetched from its documented endpoint without
    # credentials, so it is known to work; not integrated.
    VALIDATED = "VALIDATED"
    # Validated, terms permit the intended use, a connector could be written.
    READY_FOR_INTEGRATION = "READY_FOR_INTEGRATION"
    # Reachable, but its terms must be reviewed before it is connected.
    TERMS_REVIEW_REQUIRED = "TERMS_REVIEW_REQUIRED"
    # Something other than terms or credentials stops integration (robots
    # rules, a broken endpoint, a format that cannot be read).
    BLOCKED = "BLOCKED"
    # Researched; cannot serve REI's purpose.
    NOT_USABLE = "NOT_USABLE"
    # Usable only with credentials, a contract or a partnership.
    REQUIRES_ACCESS = "REQUIRES_ACCESS"
    # Official, but published for people only: no machine-readable access.
    MANUAL_ONLY = "MANUAL_ONLY"


class CostCategory(StrEnum):
    FREE_PUBLIC = "FREE_PUBLIC"
    FREE_WITH_LIMITS = "FREE_WITH_LIMITS"
    REGISTRATION_REQUIRED = "REGISTRATION_REQUIRED"
    PAID = "PAID"
    PARTNER_ONLY = "PARTNER_ONLY"
    UNKNOWN = "UNKNOWN"


class TermsStatus(StrEnum):
    """Whether the source's terms of use have been read for REI's purpose."""

    NOT_REVIEWED = "NOT_REVIEWED"
    # Read; a decision needs someone with authority to make it.
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    # Read; development and testing use is permitted.
    PERMITS_TESTING = "PERMITS_TESTING"
    # Read; commercial use is permitted (with any attribution recorded).
    PERMITS_COMMERCIAL = "PERMITS_COMMERCIAL"
    # Read; REI's intended use is not permitted.
    RESTRICTED = "RESTRICTED"


class CommercialUse(StrEnum):
    UNKNOWN = "UNKNOWN"
    PERMITTED = "PERMITTED"
    PERMITTED_WITH_ATTRIBUTION = "PERMITTED_WITH_ATTRIBUTION"
    NOT_PERMITTED = "NOT_PERMITTED"
    CONTRACT_REQUIRED = "CONTRACT_REQUIRED"


class SourceDefinition(BaseModel):
    """A source as declared in the source registry (see connectors/registry.py).

    Fields are left unset when they have not been established; nothing here
    is guessed.
    """

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_name: str
    # Who owns and publishes the source.
    organization: str | None = None
    # Kind of organisation: GOVERNMENT, POLICE, NEWS_MEDIA, COMMERCIAL, …
    authority_type: str | None = None
    # REI source tier: 1 government / police / road authority; 2 official event
    # organiser or transport operator; 3 approved commercial or partner source;
    # 4 discovery-only.
    source_tier: int | None = Field(default=None, ge=1, le=4)
    source_type: SourceType
    # What kind of body stands behind the source. None only for manual entry.
    source_class: SourceClass | None = None
    # Where the source's data is about. ISO 3166-1 alpha-2 country; a region
    # (state, county); a city id from the city configuration (packages/cities).
    # Unset where the source is not about one place.
    country: str | None = Field(default=None, min_length=2, max_length=2)
    region: str | None = None
    city: str | None = None
    # The source's public home (website or section page).
    source_url: str | None = None
    # The machine-readable address that is actually fetched, if there is one.
    endpoint: str | None = None
    # How the content can be obtained, in plain words.
    access_method: str | None = None
    integration_status: IntegrationStatus = IntegrationStatus.DISCOVERED
    # Whether the source is polled. Only a CONNECTED source can be active.
    active: bool = False
    polling_frequency_minutes: int | None = None
    language: str | None = None
    # REI event types this source can give rise to.
    events_supported: tuple[str, ...] = ()
    # Which parser reads the source, e.g. "rss".
    parser_type: str | None = None
    # What the data costs to obtain. Unset where there is no machine access.
    cost_category: CostCategory | None = None
    # The documented limit, in the source's own terms ("50 requests a minute").
    rate_limit: str | None = None
    # Whether the source's terms of use have been formally reviewed for REI's purpose.
    terms_reviewed: bool = False
    terms_status: TermsStatus = TermsStatus.NOT_REVIEWED
    # The licence the data is published under, and where it says so.
    licence: str | None = None
    # Attribution the licence or terms require, in their words.
    attribution: str | None = None
    commercial_use: CommercialUse = CommercialUse.UNKNOWN
    # What the source's records carry, when they carry it.
    provides_geometry: bool = False
    provides_segments: bool = False
    provides_direction: bool = False
    real_time: bool = False
    # A source that finds reports but is never itself evidence that an event
    # is real: news feeds, search. Always tier 4.
    discovery_only: bool = False
    # What is kept as evidence for each item.
    evidence_retention: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _only_connected_sources_are_active(self) -> "SourceDefinition":
        if self.active and self.integration_status is not IntegrationStatus.CONNECTED:
            raise ValueError(f"{self.source_id}: only a CONNECTED source can be active")
        return self

    @model_validator(mode="after")
    def _discovery_sources_are_tier_four(self) -> "SourceDefinition":
        if self.discovery_only and self.source_tier not in (None, 4):
            raise ValueError(f"{self.source_id}: a discovery-only source cannot be above tier 4")
        if self.source_class in (SourceClass.DISCOVERY, SourceClass.PUBLISHER) and (
            not self.discovery_only or self.source_tier not in (None, 4)
        ):
            raise ValueError(
                f"{self.source_id}: publishers and search are discovery-only, tier 4"
            )
        if self.terms_reviewed and self.terms_status is TermsStatus.NOT_REVIEWED:
            raise ValueError(f"{self.source_id}: terms_reviewed needs a terms_status")
        return self
