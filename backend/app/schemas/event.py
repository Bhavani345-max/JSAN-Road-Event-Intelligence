from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from packages.event_schema import EventSeverity, EventStatus, EventType, ReiEvent


class SourceSummary(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    # What kind of body the source is, its REI tier and whether it is only a
    # way of finding reports (news, search). See packages/source_models.
    source_class: str | None = None
    source_tier: int | None = None
    discovery_only: bool = False


class ArticleImageOut(BaseModel):
    """The image published with the source article, and whether REI may show it (decision 0050).

    Read from the stored evidence; never fetched, stored or guessed. Fields the
    source does not state stay empty.
    """

    # AVAILABLE: REI may show it; WITHHELD: the article has one, not shown
    # (`reason` says why); NONE: the stored article has no image.
    status: str = "NONE"
    # Only when AVAILABLE: the address of the image on the publisher's site.
    url: str | None = None
    # The article the image was published with.
    source_url: str | None = None
    # Where in the stored evidence it was found: "article_markup".
    found_in: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    # The photo credit as the source states it.
    credit: str | None = None
    # The permission REI shows it under, quoted.
    licence: str | None = None
    # The credit line the permission requires.
    attribution: str | None = None
    reason: str | None = None


class EvidenceOut(BaseModel):
    """The stored source artifact an event was derived from."""

    artifact_id: str
    url: str | None
    title: str
    published_at: datetime | None
    retrieved_at: datetime
    content_hash: str
    image: ArticleImageOut = ArticleImageOut()


class ContributingEvidenceOut(BaseModel):
    """The evidence of an event merged into this one, with its source."""

    event_id: str
    source: SourceSummary
    artifact_id: str | None
    url: str | None
    title: str
    published_at: datetime | None
    retrieved_at: datetime | None
    # "automatic" or "reviewer".
    how: str | None = None
    image: ArticleImageOut = ArticleImageOut()


class MergeCandidateOut(BaseModel):
    """A pair of events that may be the same, awaiting (or after) review."""

    candidate_id: int
    # SAME or POSSIBLE.
    classification: str
    # PENDING, AUTO_MERGED, CONFIRMED, REJECTED, SUPERSEDED.
    status: str
    reasons: list[str]
    conflicts: list[dict]
    other_event_id: str
    other_title: str
    other_source: SourceSummary
    decided_by: str | None = None
    decision_reason: str | None = None


class EventOut(ReiEvent):
    """A canonical event as returned by the API."""

    source: SourceSummary
    evidence: EvidenceOut | None
    version: int
    # Set when this event was merged into another; it is then not listed alone.
    merged_into: str | None = None
    # The evidence of every event merged into this one.
    other_evidence: list[ContributingEvidenceOut] = []
    # Pending candidates: events that may be the same as this one.
    merge_candidates: list[MergeCandidateOut] = []
    # For an event in QC_PENDING: every QC requirement it does not yet meet,
    # in plain words. Empty when it can be approved (and for other statuses).
    approval_blockers: list[str] = []
    # Whether the console's maps may draw it: located, with a stated start, not
    # over (decision 0038). The review queue also lists events no map draws.
    map_eligible: bool = False
    # The first rule that keeps it off the maps: no_location, no_start, ended,
    # source_ended or open_end_lapsed; None when it may be drawn.
    off_map_reason: str | None = None


class EventVersionOut(BaseModel):
    version: int
    status: EventStatus
    change_reason: str | None
    changed_by: str
    created_at: datetime


class EventDetailOut(EventOut):
    versions: list[EventVersionOut]


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int


class CityEventCountOut(BaseModel):
    """How many events a console view lists for one configured city."""

    city_id: str
    city_name: str
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]


class CityCoverageOut(BaseModel):
    """One city's events from detection to the map (decisions 0034, 0035).

    detected: events not merged into another; merged: rows merged into another
    event (duplicates); pending_review / validated: awaiting a reviewer /
    approved and in force; on_map_review: events awaiting review that the
    review queue's map shows now; on_map_operations: validated events that the
    operations map shows now (the two are never added up); hidden_review /
    hidden_operations: events awaiting review / validated that their view's
    map does not show, by the first rule that hides each.
    """

    city_id: str
    city_name: str
    country: str
    detected: int = 0
    merged: int = 0
    rejected: int = 0
    closed: int = 0
    pending_review: int = 0
    validated: int = 0
    recent: int = 0
    on_map_review: int = 0
    # What the review queue lists, on its map or not: it also lists located
    # events with no stated start that are not known to be over (decision 0038).
    listed_review: int = 0
    on_map_operations: int = 0
    hidden_review: dict[str, int] = {}
    hidden_operations: dict[str, int] = {}


class EventCoverageOut(BaseModel):
    cities: list[CityCoverageOut]


class EventSummaryOut(BaseModel):
    """Per city, what a console view lists: for the overview of all cities."""

    view: str
    cities: list[CityEventCountOut]


class GisDecisionIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class GisChoiceIn(BaseModel):
    """A reviewer's choice among the GIS candidates of one result."""

    result_index: int = Field(ge=0)
    # None: the result's own candidate; otherwise one of its alternatives.
    alternative_index: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=5, max_length=500)


class JunctionOut(BaseModel):
    junction_id: int
    city: str
    canonical_name: str
    aliases: list[str]
    latitude: float | None
    longitude: float | None
    osm_node_id: int | None
    related_roads: list[str]
    source: str
    status: str
    confirmation_method: str | None
    reviewer: str | None
    confirmed_at: datetime | None
    decision_reason: str | None


class MergeDecisionIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class MergeGroupDecisionIn(BaseModel):
    """A reviewer's decision that all these candidates (of one event) are the same event."""

    candidate_ids: list[int] = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=5, max_length=500)


class StatusUpdateIn(BaseModel):
    status: EventStatus
    reason: str | None = Field(default=None, max_length=500)
    # Approve anyway, overriding the QC checks the event does not meet; needs a reason.
    force: bool = False
    # REI severity the reviewer assigns with this decision, if any. Never
    # required; never filled in by REI itself.
    severity: EventSeverity | None = None


class SeverityIn(BaseModel):
    """A reviewer's REI severity for an event (LOW, MEDIUM, HIGH or CRITICAL)."""

    severity: EventSeverity
    reason: str | None = Field(default=None, max_length=500)


class ExtendIn(BaseModel):
    """A reviewer's extension of an event. Dates are whole days in IST."""

    # The new last day; null for "until further notice".
    end_date: date | None = None
    # How the reviewer knows, e.g. "Still closed on 5 October, seen on site".
    reason: str = Field(min_length=5, max_length=500)


class LocationIn(BaseModel):
    """The spot a reviewer picked on the map for an event (WGS 84)."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    # What is at that spot, e.g. "IIIT Junction".
    place_name: str = Field(min_length=2, max_length=120)
    # How the reviewer knows the event is there.
    reason: str = Field(min_length=5, max_length=500)


class ManualEventIn(BaseModel):
    """A road event entered by a reviewer. Dates are whole days in IST."""

    title: str = Field(min_length=5, max_length=200)
    event_type: EventType | None = None
    description: str | None = Field(default=None, max_length=2000)
    # A junction, road, landmark or locality; located if it is a known name.
    place: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    # Where the reviewer saw it, if anywhere on the web.
    reference_url: str | None = Field(default=None, max_length=1000, pattern=r"^https?://\S+$")
    # How the reviewer knows of the event. Required: an entry is only as good as this.
    basis: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> "ManualEventIn":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date is before the start date.")
        return self


class PlaceOut(BaseModel):
    """A known Hyderabad place an event can be located by."""

    name: str
    # junction, flyover, landmark, road or area.
    kind: str
