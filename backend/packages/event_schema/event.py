from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from packages.geo_models import Geometry

from .enums import EventDirection, EventSeverity, EventStatus, EventType, LocationClass

# EventLocation.method values.
NAMED_PLACE = "named_place"
REVIEWER_PLACED = "reviewer_placed"
SOURCE_PROVIDED = "source_provided"
GIS_RESOLVED = "gis_resolved"

_CLASS_BY_METHOD = {
    NAMED_PLACE: LocationClass.APPROXIMATE,
    REVIEWER_PLACED: LocationClass.HUMAN_CORRECTED,
    SOURCE_PROVIDED: LocationClass.SOURCE_PROVIDED,
    GIS_RESOLVED: LocationClass.GIS_RESOLVED,
}


class EventLocation(BaseModel):
    """How an event's geometry was obtained. Kept for reviewers.

    The geometry is the position of a place the source names, taken from a
    map; it is not a surveyed extent of the closure or works.
    """

    # "named_place": a place named in the source, looked up in the gazetteer.
    # "reviewer_placed": a point a reviewer put on the map, with the name they gave it.
    # "source_provided": geometry the source itself publishes.
    # "gis_resolved": matched to the road network (future GIS Resolution Engine).
    method: str
    place_name: str
    # junction, flyover, landmark, road or area.
    place_kind: str
    # "place" (a junction, flyover or landmark), "road" or "area".
    precision: str
    # The words as the source wrote them, and where: title, summary or body.
    mention: str
    found_in: str
    # The map feature the position comes from, e.g. "OpenStreetMap node/123".
    reference: str
    # When the event is placed at a spot (a junction, flyover or landmark) the
    # source names inside the locality its headline names: that locality.
    within: str | None = None


class GisCandidate(BaseModel):
    """A road-network candidate for a location, with how and why it was found."""

    matched_name: str
    # JUNCTION_REFERENCE, ALIAS_MATCH, OSM_NAMED_JUNCTION, ROAD_INTERSECTION,
    # EXACT_ROAD_NAME, ROAD_STRETCH, NEARBY_ROAD, REVIEWER_CONFIRMED
    method: str
    geometry: dict[str, Any]
    # OSM features ("way/123", "node/456") or "junction-reference/7".
    osm_ids: list[str] = []
    reasons: list[str] = []


class GisLocationResult(BaseModel):
    """What the GIS resolver found for one place an event names."""

    mention: str
    found_in: str
    # junction, structure, road, place, stretch, crossing
    kind: str
    # HIGH, MEDIUM, LOW or UNRESOLVED (fixed rules; see docs/gis-resolution-engine.md)
    confidence: str
    ambiguous: bool = False
    chosen: GisCandidate | None = None
    alternatives: list[GisCandidate] = []
    reasons: list[str] = []
    # Whether this result became the event's (proposed) location.
    applied: bool = False


class GisResolution(BaseModel):
    """The latest GIS resolution of an event, and its review."""

    engine: str
    # The road data and its date, e.g. "OpenStreetMap 2026-10-06T07:40:50Z".
    network: str
    resolved_at: datetime
    results: list[GisLocationResult] = []
    # Whether a result was applied as the event's location (GIS_RESOLVED).
    applied: bool = False
    # Why nothing was applied, when nothing was.
    not_applied_reason: str | None = None
    # PENDING (a proposal awaiting review), APPROVED, REJECTED, SUPERSEDED (a
    # reviewer placed the event themselves), NOT_APPLIED (candidates only).
    review_status: str = "NOT_APPLIED"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None
    # The location before GIS resolution, restored if a reviewer rejects it.
    previous: dict[str, Any] | None = None


class AffectedLocation(BaseModel):
    """One place an event affects. An event may affect several: junctions,
    streets, segments, directions. Each says how it was located, or that it
    was not; a name that could not be placed is kept as a name."""

    name: str
    # junction, flyover, landmark, road, area, ward, street, segment, spot …
    kind: str | None = None
    resolution: LocationClass
    # Its own geometry, when known; never made up.
    geometry: Geometry | None = None
    # As the source states it: "Westbound", "Both directions", "ONE_DIRECTION".
    direction: str | None = None
    # As the source states it: "Closed", "Open" (lane-level restriction).
    closure: str | None = None
    # The words as the source wrote them, and where: title, summary, body, source.
    mention: str | None = None
    found_in: str | None = None
    # Where the geometry comes from: an OpenStreetMap feature, the source's record.
    reference: str | None = None
    # What the GIS resolver found for it, when it has run.
    gis: GisLocationResult | None = None
    # What the place is to the event, as an AI reading of the article states it:
    # CLOSED, AFFECTED, STRETCH_FROM, STRETCH_TO, VENUE, NEAR, DIVERSION_ROUTE,
    # ALTERNATE_ROUTE. None when no AI reading gave one.
    role: str | None = None


class AiPlace(BaseModel):
    """A place an AI reading says the article names, checked against the article.

    Only names found word for word in the article text are kept: the model
    cannot add a place the article does not name.
    """

    # The name exactly as the article writes it.
    name: str
    # CLOSED, AFFECTED, STRETCH_FROM, STRETCH_TO, VENUE, NEAR, DIVERSION_ROUTE, ALTERNATE_ROUTE
    role: str
    # Where the name stands in the article: title, summary or body.
    found_in: str | None = None
    # The article's words that show the place's role, when they were found in the article.
    quote: str | None = None


class AiReading(BaseModel):
    """What a language model read from an article, after checking against the article.

    The model's free-text answers (why, cause, summary) are its own words and
    are shown as such. Everything that could put an event on the map or give
    it dates (places, the period, the evidence) is kept only when the article
    contains it word for word; what failed that check is listed in `discarded`.
    """

    # The model that answered (an OpenRouter model id), and the prompt version.
    model: str
    prompt_version: str
    read_at: datetime
    # "triage" (headline and summary only) or "full" (the whole article).
    stage: str
    is_road_event: bool
    # Why it is or is not a road event, in the model's words.
    why: str | None = None
    # One of EventType's values, or None when the model gave none it may use.
    intent: EventType | None = None
    # What happens on the road: CLOSURE, DIVERSION, LANE_RESTRICTION … (see the config).
    impact: str | None = None
    # Why the road is affected, in the model's words ("Ganesh immersion procession").
    cause: str | None = None
    # One plain sentence on what happens where and when, in the model's words.
    summary: str | None = None
    # The city the model says the event is in, as it wrote it.
    city: str | None = None
    # Whether the event is in the city the source covers (decided by REI, not the model).
    in_scope: bool | None = None
    places: list[AiPlace] = []
    # The article's words stating when, if found in the article, and the dates read from them.
    period_text: str | None = None
    # "rules" when REI's own date rules read the words, "ai" when only the model did.
    period_read_by: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    # Who announced the measure, as the article writes it.
    authority: str | None = None
    # The article's sentence that states the road measure.
    evidence: str | None = None
    # What the model answered that the article does not contain, so was not used.
    discarded: list[str] = []


class SourceRevisionNote(BaseModel):
    """A revision the source made to the record an event was built from."""

    # The version of the source record: the original is 1.
    revision: int
    revised_at: datetime
    # What changed, in plain words ("end … → …").
    changes: list[str]


class FieldSource(BaseModel):
    """Which event (and so which source) a canonical event's field came from."""

    event_id: str
    source_id: str


class Contribution(BaseModel):
    """An event merged into a canonical event: its source and evidence stay linked."""

    event_id: str
    source_id: str
    artifact_id: str | None = None
    title: str
    url: str | None = None
    published_at: datetime | None = None
    merged_at: datetime
    merged_by: str
    # "automatic" (clearly the same event) or "reviewer" (a confirmed candidate).
    how: str
    reason: str | None = None
    # Fields the canonical event took from it because it had none.
    fields: list[str] = []


class MergeConflict(BaseModel):
    """Sources disagree on a field. Every value is kept; none is chosen automatically."""

    field: str
    # [{"event_id": …, "source_id": …, "value": …}, …]
    values: list[dict[str, Any]]


class Observation(BaseModel):
    """Whether an official source still lists the record (refresh by refresh).

    Absence from a feed is not proof that an event has ended: it is only
    counted, and after a threshold flagged for a reviewer.
    """

    last_seen_at: datetime | None = None
    missing_since: datetime | None = None
    missed_refreshes: int = 0
    review_required: bool = False


class PeriodRevision(BaseModel):
    """A reviewer's change to when an event ends. The latest one; all are in the history."""

    # The end the event had before, e.g. the one its article stated.
    previous_end: datetime | None
    # Why the reviewer says it runs longer, in their words.
    reason: str
    revised_by: str
    revised_at: datetime


class LocationRevision(BaseModel):
    """A reviewer's correction of where an event is. The latest one; all are in the history."""

    # The place the event was located by before, if it was located at all.
    previous_place_name: str | None
    # How the reviewer knows where it is, in their words.
    reason: str
    revised_by: str
    revised_at: datetime


class QcApproval(BaseModel):
    """A reviewer's QC approval of an event. The latest one; all decisions are in the history."""

    approved_by: str
    approved_at: datetime
    # The reviewer's reason, as given with the decision.
    reason: str | None = None
    # The event version the approval created (its entry in the version history).
    version: int
    # Approved anyway: a reviewer overrode QC checks the event did not meet,
    # listed in `overridden` in the words the console showed them.
    forced: bool = False
    overridden: list[str] = []


class SeverityAssessment(BaseModel):
    """A reviewer's REI severity for an event: REI's own judgment of how much
    the event disrupts traffic. Assigned by a person during review, never
    read from text and never copied from the source's own severity words
    (which stay in `source_severity`). The latest one; every change is in the
    version history."""

    severity: EventSeverity
    assessed_by: str
    assessed_at: datetime
    # The reviewer's reason, if given.
    reason: str | None = None
    # The event version the assessment created.
    version: int


class EventDetection(BaseModel):
    """Why a source item was turned into an event. Kept for reviewers."""

    # "ai_reading" for an article a language model read as a road event,
    # "keyword_rules" for a detected article, "manual_entry" for a reviewer's
    # entry, "source_provided" for an event an official source states itself.
    method: str
    # The keyword score; None where no keywords were scored (source-provided events).
    score: float | None = None
    matched_keywords: list[str]
    # Road names found verbatim in the source text. These are unverified
    # mentions, not resolved roads.
    road_mentions: list[str] = []
    # Known Hyderabad places the source names, most telling first.
    places: list[str] = []
    # None when the source names no place the event can be located by.
    location: EventLocation | None = None
    # The source's own words that start_time/end_time were read from.
    stated_period: str | None = None
    # A distance the source states, in its own words ("100 meter"). Never
    # measured by REI; a reviewer reads it against the map.
    stated_distance: str | None = None
    # The same distance in metres, read from the stated unit.
    stated_distance_m: float | None = None
    # Length in metres of the source's OWN geometry (its line, or the stretches
    # it draws as closed), measured on that geometry. Nothing is estimated;
    # a source that draws no line has none. Never used to drop an event.
    source_geometry_length_m: float | None = None
    # Authorities the source says announced the measure (a second-hand report).
    attributed_to: list[str] = []
    # For a manually entered event: how the reviewer knows of it, in their words.
    basis: str | None = None
    # Set when a reviewer has extended the event beyond the end first recorded.
    period_revision: PeriodRevision | None = None
    # Set when a reviewer has put the event at a spot of their own choosing.
    location_revision: LocationRevision | None = None
    # How the event's location was obtained (filled in from `location` when unset).
    location_class: LocationClass | None = None
    # Every place the event affects, located or not.
    affected_locations: list[AffectedLocation] = []
    # What an official source states, in its own words: its category and
    # sub-category, its severity and status, and the attribution its licence
    # requires. REI's own severity is not derived from these.
    source_category: str | None = None
    source_severity: str | None = None
    source_status: str | None = None
    attribution: str | None = None
    # REI's own severity, as a reviewer assessed it (the value itself is the
    # event's `severity`; this records who, when and why).
    severity_assessment: SeverityAssessment | None = None
    # The latest source revision applied to the event.
    source_revision: SourceRevisionNote | None = None
    # A source revision that arrived after a reviewer decided the event, not
    # applied: for a reviewer to act on.
    pending_source_revision: SourceRevisionNote | None = None
    # The source itself reports the event cleared, cancelled or ended.
    source_reports_ended: bool = False
    # Official sources: whether the latest refreshes still listed the record.
    observation: Observation | None = None
    # Cross-source merging: the events merged into this one, which event each
    # field came from, and fields the sources disagree on.
    contributions: list[Contribution] = []
    provenance: dict[str, FieldSource] = {}
    merge_conflicts: list[MergeConflict] = []
    merge_review_required: bool = False
    # The latest run of the GIS Resolution Engine on this event.
    gis: GisResolution | None = None
    # Set when a reviewer approved the event in QC.
    qc_approval: QcApproval | None = None
    # A language model's reading of the article, checked against the article.
    ai: AiReading | None = None

    @model_validator(mode="after")
    def _fill_location_class(self) -> "EventDetection":
        if self.location_class is None:
            self.location_class = (
                _CLASS_BY_METHOD.get(self.location.method, LocationClass.APPROXIMATE)
                if self.location
                else LocationClass.UNRESOLVED
            )
        return self


class ReiEvent(BaseModel):
    """The canonical REI road event.

    Every source is converted into this shape. A field is None when the source
    did not state it: nothing here is ever guessed.
    """

    event_id: str
    source_id: str
    # Where the event came from within the source, e.g. the article URL.
    source_reference: str | None = None
    title: str
    event_type: EventType | None = None
    description: str | None = None
    city: str | None = None
    affected_road: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: EventStatus
    severity: EventSeverity | None = None
    direction: EventDirection | None = None
    # None when the event could not be located; see detection.location for
    # where a geometry came from.
    geometry: Geometry | None = None
    # 0–1. None until a confidence assessment exists.
    confidence: float | None = Field(default=None, ge=0, le=1)
    detection: EventDetection | None = None
    created_at: datetime
    updated_at: datetime
