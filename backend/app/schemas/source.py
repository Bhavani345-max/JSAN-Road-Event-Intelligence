from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_name: str
    organization: str | None
    authority_type: str | None
    source_tier: int | None
    source_type: str
    source_url: str | None
    endpoint: str | None
    access_method: str | None
    # CONNECTED, DISCOVERED, VALIDATED, READY_FOR_INTEGRATION, TERMS_REVIEW_REQUIRED,
    # BLOCKED, NOT_USABLE, REQUIRES_ACCESS or MANUAL_ONLY.
    integration_status: str
    # AUTHORITATIVE_OFFICIAL, GOVERNMENT_OPEN_DATA, PARTNER, PUBLISHER, DISCOVERY,
    # COMMERCIAL; null for manual entry.
    source_class: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    cost_category: str | None = None
    rate_limit: str | None = None
    terms_status: str = "NOT_REVIEWED"
    licence: str | None = None
    attribution: str | None = None
    commercial_use: str = "UNKNOWN"
    provides_geometry: bool = False
    provides_segments: bool = False
    provides_direction: bool = False
    real_time: bool = False
    discovery_only: bool = False
    active: bool
    polling_frequency_minutes: int | None
    language: str | None
    events_supported: list[str]
    parser_type: str | None
    terms_reviewed: bool
    evidence_retention: str | None
    notes: str | None
    last_poll_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error: str | None
    # How much has been acquired from this source so far.
    artifact_count: int = 0
    event_count: int = 0


class IngestionResultOut(BaseModel):
    source_id: str
    # "ok", or "failed" with `error` set.
    status: str
    error: str | None = None
    fetched: int = 0
    new_artifacts: int = 0
    duplicates: int = 0
    # Held items the source has revised since (official feeds).
    revised: int = 0
    relevant: int = 0
    events_created: int = 0
    started_at: datetime
    finished_at: datetime | None = None


class IngestionRunOut(BaseModel):
    results: list[IngestionResultOut]
