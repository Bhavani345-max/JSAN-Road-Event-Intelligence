"""Set aside AI readings made with the wrong rules, and re-derive the events they changed.

On 16 October 2026 a local API running older code read articles of sources it
did not know with Hyderabad's rules (decision 0033): its AI readings of them
were made for the wrong city, and it rejected the events of five of them.

Nothing here deletes anything:

- `supersede_readings` moves an article's reading from `classification_details["ai"]`
  to the list `classification_details["ai_superseded"]`, with the reason, the
  time, and the article's classification as it stood, so `restore_readings`
  can put back exactly what was there;
- `rederive_events` re-derives each event with its own city's rules, as
  reprocessing does: a new version, every earlier one kept. An event a person
  has touched is never changed. `reject_again` undoes it with a further version.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Event, SourceArtifact
from app.services.reprocess_service import (
    AI_CHANGED_BY,
    CHANGED_BY,
    SUPERSEDED_KEY,
    rederive_artifact,
)
from packages.common.time import utc_now
from packages.event_schema import EventStatus

# The keyword fields of classification_details, kept with a superseded reading.
_KEYWORD_FIELDS = ("method", "classifier_version", "score", "matched_keywords", "in_scope_city", "relevant_by")


@dataclass
class CorrectionResult:
    changed: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)


def supersede_readings(
    session: Session, artifact_ids: list[str], *, reason: str, at: datetime
) -> CorrectionResult:
    """Move each article's AI reading aside, with why and when; nothing is deleted."""
    result = CorrectionResult()
    for artifact_id in artifact_ids:
        artifact = session.get(SourceArtifact, artifact_id)
        details = dict((artifact.classification_details or {}) if artifact else {})
        if artifact is None:
            result.skipped[artifact_id] = "no such article"
            continue
        if not details.get("ai"):
            result.skipped[artifact_id] = "no AI reading"
            continue
        entry = {
            "reading": details.pop("ai"),
            "reason": reason,
            "superseded_at": at.isoformat(),
            "classification_at_the_time": artifact.classification,
            "keyword_details_at_the_time": {k: details[k] for k in _KEYWORD_FIELDS if k in details},
        }
        details[SUPERSEDED_KEY] = [*details.get(SUPERSEDED_KEY, []), entry]
        artifact.classification_details = details
        result.changed.append(artifact_id)
    return result


def restore_readings(session: Session, artifact_ids: list[str], *, reason: str) -> CorrectionResult:
    """Undo `supersede_readings` for these articles: the last reading set aside with
    `reason` goes back, with the classification it was set aside with."""
    result = CorrectionResult()
    for artifact_id in artifact_ids:
        artifact = session.get(SourceArtifact, artifact_id)
        details = dict((artifact.classification_details or {}) if artifact else {})
        entries = list(details.get(SUPERSEDED_KEY) or [])
        index = next((i for i in range(len(entries) - 1, -1, -1) if entries[i]["reason"] == reason), None)
        if artifact is None or index is None:
            result.skipped[artifact_id] = "nothing set aside with this reason"
            continue
        if details.get("ai"):
            result.skipped[artifact_id] = "a newer reading is in place"
            continue
        entry = entries.pop(index)
        for key in _KEYWORD_FIELDS:
            details.pop(key, None)
        details.update(entry["keyword_details_at_the_time"])
        details["ai"] = entry["reading"]
        if entries:
            details[SUPERSEDED_KEY] = entries
        else:
            details.pop(SUPERSEDED_KEY, None)
        artifact.classification = entry["classification_at_the_time"]
        artifact.classification_details = details
        result.changed.append(artifact_id)
    return result


def rederive_events(session: Session, service, event_ids: list[str], *, reason: str) -> CorrectionResult:
    """Re-derive events an AI reading rejected, each with its own source's city rules.

    Only an event whose latest version is an AI reading's rejection is
    re-derived; the outcome is recorded per event ("restored" when it comes back).
    """
    result = CorrectionResult()
    for event_id in event_ids:
        row = session.get(Event, event_id)
        if row is None or row.source_artifact_id is None:
            result.skipped[event_id] = "no such event, or no stored article"
            continue
        last = row.versions[-1]
        if row.status != EventStatus.REJECTED.value or last.changed_by != AI_CHANGED_BY:
            result.skipped[event_id] = f"not an AI reading's rejection ({row.status}, {last.changed_by})"
            continue
        artifact = session.get(SourceArtifact, row.source_artifact_id)
        classifier, resolver, city = service.tools_for_source(artifact.source_id)
        outcome, _ = rederive_artifact(
            session,
            artifact,
            row,
            classifier=classifier,
            resolver=resolver,
            city=city,
            rebuild=service.rebuild_for_source(artifact.source_id),
            reason=reason,
            changed_by=CHANGED_BY,
            placer=service.placer_for_source(artifact.source_id),
        )
        (result.changed if outcome == "restored" else []).append(event_id)
        if outcome != "restored":
            result.skipped[event_id] = f"re-derivation gave {outcome!r}"
    return result


def reject_again(session: Session, event_ids: list[str], *, reason: str) -> CorrectionResult:
    """Undo `rederive_events`: a further version rejects each restored event again."""
    result = CorrectionResult()
    from app.repositories.events import EventRepository

    events = EventRepository(session)
    for event_id in event_ids:
        row = session.get(Event, event_id)
        last = row.versions[-1] if row is not None else None
        if last is None or last.changed_by != CHANGED_BY or row.status == EventStatus.REJECTED.value:
            result.skipped[event_id] = "not a restored event"
            continue
        row.status = EventStatus.REJECTED.value
        row.version += 1
        row.updated_at = utc_now()
        events.record_version(row, change_reason=reason, changed_by=CHANGED_BY)
        result.changed.append(event_id)
    return result
