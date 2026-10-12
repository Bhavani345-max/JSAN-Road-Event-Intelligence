"""Re-derives events from the evidence already stored.

When the detection rules change, the stored articles are read again with the
new rules, so that old and new articles are treated alike. Nothing is fetched
and no evidence is altered. Every change to an event is recorded as a new
version; an event the rules no longer support is rejected, not deleted.

Only events no person has touched are changed: a reviewer's decision, an
extension and a manual entry are never overridden. An event that reprocessing
itself rejected is brought back if later rules detect it again.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, SourceArtifact
from app.repositories.events import EventRepository, column_values, to_rei_event
from app.services.retention_service import is_stub
from packages.common.text import html_to_text
from packages.common.time import ensure_utc, utc_now
from packages.event_schema import AiReading, EventStatus, ReiEvent
from packages.source_models import RawSourceRecord, SourceEvent, road_block, too_short_road_block
from services.extraction import ArticleRelevance, ClassificationResult, KeywordClassifier
from services.extraction.ai_event import is_ai_road_event
from services.geo_resolution import PlaceResolver
from services.ingestion import event_for_record
from services.ingestion.pipeline import classify

CHANGED_BY = "reprocessing"
# Changes made after a language model read the article (app/services/ai_reading_service.py).
AI_CHANGED_BY = "ai-reading"
# Who makes changes without a person deciding them.
_AUTOMATIC = {"ingestion", CHANGED_BY, "source-update", "gis-resolver", AI_CHANGED_BY}
# Automatic re-derivations whose rejection a later one may undo.
_REDERIVERS = {CHANGED_BY, AI_CHANGED_BY}
# Notes on an event about source revisions; not derived from the article.
_KEPT_DETECTION_KEYS = (
    "source_revision",
    "pending_source_revision",
    "observation",
    "severity_assessment",
)
# Evidence that is a person's entry, not an article to classify.
_MANUAL_ENTRY = "MANUAL_ENTRY"

# What reprocessing may rewrite on an event: everything derived from the article.
_DERIVED_FIELDS = (
    "event_type",
    "city",
    "affected_road",
    "start_time",
    "end_time",
    "geometry",
    "detection",
)


@dataclass
class ReprocessResult:
    artifacts: int = 0
    created: int = 0
    updated: int = 0
    rejected: int = 0
    restored: int = 0
    unchanged: int = 0


def record_from_artifact(
    artifact: SourceArtifact, rebuild: Callable[[dict], SourceEvent | None] | None = None
) -> RawSourceRecord:
    """The source item exactly as it was stored as evidence, in its latest version.

    `rebuild`, when a connector offers one, redoes the connector's structured
    reading of the stored item from the item itself (a notice's table row),
    so a stored official record is read with the current rules like any
    article. The stored evidence is not altered.
    """
    latest = artifact.latest
    raw = latest.raw_content or {}
    structured = SourceEvent.model_validate(raw["source_event"]) if raw.get("source_event") else None
    if rebuild is not None and (raw.get("source_event") or raw.get("row") or raw.get("line")):
        structured = rebuild(raw)
    return RawSourceRecord(
        source_id=artifact.source_id,
        external_id=artifact.external_id,
        url=latest.url,
        title=latest.title,
        summary=html_to_text(raw.get("summary_html")) or None,
        content_text=html_to_text(raw.get("content_html")) or None,
        categories=[category for category in raw.get("categories") or [] if category],
        published_at=latest.published_at,
        retrieved_at=latest.retrieved_at,
        raw=raw,
        content_hash=latest.content_hash,
        structured=structured,
    )


def _derived(event: ReiEvent) -> dict:
    """The derived fields in one comparable form, whatever time zone they are held in."""
    values = event.model_dump(mode="json")
    derived = {name: values[name] for name in _DERIVED_FIELDS}
    if derived["detection"]:
        derived["detection"] = {
            key: value
            for key, value in derived["detection"].items()
            if key not in _KEPT_DETECTION_KEYS
        }
    for name in ("start_time", "end_time"):
        value = getattr(event, name)
        derived[name] = ensure_utc(value).isoformat() if value else None
    return derived


def _keep_notes(row: Event, values: dict) -> dict:
    """Derived values with the event's source-revision notes carried over."""
    kept = {key: (row.detection or {}).get(key) for key in _KEPT_DETECTION_KEYS}
    if values.get("detection") is not None:
        values["detection"] = {
            **values["detection"],
            **{key: value for key, value in kept.items() if value is not None},
        }
    return values


def ai_reading_of(artifact: SourceArtifact) -> AiReading | None:
    """The AI reading stored with the article, if it has been read."""
    stored = (artifact.classification_details or {}).get("ai")
    if not stored:
        return None
    try:
        return AiReading.model_validate(stored)
    except ValueError:
        return None


def _record_classification(artifact: SourceArtifact, classification: ClassificationResult) -> None:
    """Store the keyword result; an AI reading stored with the article is kept.

    An article the keywords pass over but a checked AI reading calls a road
    event in the city counts as relevant, so its text is not removed as an
    unrelated article's would be (retention_service).
    """
    previous = artifact.classification_details or {}
    label = classification.label.value
    details = {
        "method": classification.method,
        "classifier_version": classification.classifier_version,
        "score": classification.score,
        "matched_keywords": classification.matched_keywords,
        "in_scope_city": classification.city,
    }
    if previous.get("ai"):
        details["ai"] = previous["ai"]
        if label == ArticleRelevance.NOT_RELEVANT.value and is_ai_road_event(ai_reading_of(artifact)):
            label = ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE.value
            details["relevant_by"] = "ai_reading"
    artifact.classification = label
    artifact.classification_details = details


def rederive_artifact(
    session: Session,
    artifact: SourceArtifact,
    row: Event | None,
    *,
    classifier: KeywordClassifier,
    resolver: PlaceResolver | None,
    city=None,
    rebuild: Callable | None = None,
    reason: str,
    changed_by: str = CHANGED_BY,
    role_priority: tuple[str, ...] | None = None,
    placer=None,
) -> tuple[str, str | None]:
    """Re-derive one stored item's event. Returns the outcome and the event id.

    Outcomes: created, updated, rejected, restored, unchanged, and "none" when
    the item has no event and gives rise to none. Only events no
    person has touched are changed; one a re-derivation rejected may come back.
    """
    events = EventRepository(session)
    record = record_from_artifact(artifact, rebuild)
    classification = classify(record, classifier, city)
    _record_classification(artifact, classification)
    now = utc_now()
    derived = event_for_record(
        record,
        classification,
        resolver,
        now=now,
        city=city,
        ai=ai_reading_of(artifact),
        role_priority=role_priority,
        placer=placer,
    )

    if row is None:
        if derived is None:
            # No event, and none to derive: not counted.
            return "none", None
        events.add(
            derived,
            artifact_id=artifact.artifact_id,
            change_reason=f"Created from stored evidence with {reason}",
            changed_by=changed_by,
        )
        return "created", derived.event_id

    rejected_here = (
        row.status == EventStatus.REJECTED.value and row.versions[-1].changed_by in _REDERIVERS
    )
    touched_by_a_person = any(v.changed_by not in _AUTOMATIC for v in row.versions)
    # A GIS-resolved location is left alone: re-run the resolver after a rule change.
    if ((row.detection or {}).get("gis") or {}).get("applied"):
        return "unchanged", row.event_id
    if touched_by_a_person or (
        row.status != EventStatus.VALIDATION_REQUIRED.value and not rejected_here
    ):
        return "unchanged", row.event_id

    if rejected_here:
        if derived is None:
            return "unchanged", row.event_id
        row.status = EventStatus.VALIDATION_REQUIRED.value
        values = _keep_notes(row, column_values(derived))
        for name in _DERIVED_FIELDS:
            setattr(row, name, values[name])
        change = f"Detected again as a road event with {reason}"
        outcome = "restored"
    elif derived is None:
        row.status = EventStatus.REJECTED.value
        short = too_short_road_block(record.structured)
        change = (
            f"Road block {short:.0f} m long, under the {road_block.MIN_ROAD_BLOCK_LENGTH_M} m minimum"
            if short is not None
            else f"No longer detected as a road event with {reason}"
        )
        outcome = "rejected"
    elif _derived(to_rei_event(row)) != _derived(derived):
        values = _keep_notes(row, column_values(derived))
        for name in _DERIVED_FIELDS:
            setattr(row, name, values[name])
        change = f"Re-derived from stored evidence with {reason}"
        outcome = "updated"
    else:
        return "unchanged", row.event_id

    row.version += 1
    row.updated_at = now
    events.record_version(row, change_reason=change, changed_by=changed_by)
    return outcome, row.event_id


def reprocess_stored_evidence(
    session: Session,
    classifier: KeywordClassifier,
    resolver: PlaceResolver,
    *,
    tools_for_source: Callable | None = None,
    rebuild_for_source: Callable[[str], Callable | None] | None = None,
    placer_for_source: Callable | None = None,
) -> ReprocessResult:
    """Re-derive events. `tools_for_source(source_id)` gives the (classifier,
    resolver, city) for a source's city; without it the given pair is used
    for every artifact. `rebuild_for_source(source_id)` gives the connector's
    way of re-reading a stored item's structured fields, or None.

    An article's stored AI reading is used as it was read: reprocessing never
    asks the model again (app/services/ai_reading_service.py does)."""
    result = ReprocessResult()
    reason = f"detection rules {classifier.version}"

    by_artifact = {
        event.source_artifact_id: event for event in session.scalars(select(Event)).unique()
    }
    articles = select(SourceArtifact).where(SourceArtifact.classification != _MANUAL_ENTRY)
    for artifact in session.scalars(articles):
        # An old article that was not a road event keeps only a stub: its
        # headline alone is not re-classified (see retention_service).
        if is_stub(artifact):
            continue
        result.artifacts += 1
        rebuild = rebuild_for_source(artifact.source_id) if rebuild_for_source else None
        city = None
        this_classifier, this_resolver = classifier, resolver
        if tools_for_source is not None:
            this_classifier, this_resolver, city = tools_for_source(artifact.source_id)
        outcome, _ = rederive_artifact(
            session,
            artifact,
            by_artifact.get(artifact.artifact_id),
            classifier=this_classifier,
            resolver=this_resolver,
            city=city,
            rebuild=rebuild,
            reason=reason,
            placer=placer_for_source(artifact.source_id) if placer_for_source else None,
        )
        if outcome != "none":
            setattr(result, outcome, getattr(result, outcome) + 1)

    session.commit()
    return result
