"""Applying a source's revision of a record to the event built from it.

Official sources revise their records: a new end time, a changed severity, a
cancelled closure. The revision is stored as evidence (append-only, see
`SourceArtifactRevision`), and the event follows the source, within limits:

- An event still in review (VALIDATION_REQUIRED, QC_PENDING) takes the
  source's new values. What a reviewer did is kept: an extended end, a
  corrected location, the basis of a manual entry.
- An event that has been approved, or rejected, cancelled or expired, is not
  changed: a reviewer's decision is not overridden by an automatic update. The
  revision is recorded on the event (`detection.pending_source_revision`) for a
  reviewer to act on.
- Every applied or pending revision is a new event version, with what changed
  in plain words.
- Rows a source lists for one event (merge_service.LISTED_IN_SEVERAL_ROWS)
  stay merged only while their periods agree. A revision that changes a row's
  period lists it, and the rows of its source merged with it, on their own
  again; the next run merges again the rows that still share a period.
"""

from datetime import datetime

from sqlalchemy import select

from app.models import Event
from app.repositories.events import EventRepository, column_values, to_rei_event
from packages.common.time import ensure_utc
from packages.event_schema import EventStatus, ReiEvent
from services.lifecycle.transitions import REQUIRES_LOCATION_AND_TIME

CHANGED_BY = "source-update"
# Refreshes in a row without an official record before its event is flagged
# for review. Absence alone ends an event only for a source that lists only
# what is in force (NDW's current picture, decision 0049).
ABSENCE_REVIEW_AFTER = 3

# What a source revision may change on an event in review.
SOURCE_FIELDS = (
    "title",
    "description",
    "event_type",
    "affected_road",
    "start_time",
    "end_time",
    "direction",
    "geometry",
)
# What a reviewer put on the event, which a revision never replaces.
REVIEWER_DETECTION_KEYS = ("period_revision", "location_revision", "basis")
# What merging and observation added, which a revision keeps.
KEPT_DETECTION_KEYS = (
    "contributions", "provenance", "merge_conflicts", "merge_review_required", "observation",
)  # fmt: skip
# Notes about revisions, which are not part of what is derived from the source.
REVISION_NOTE_KEYS = ("source_revision", "pending_source_revision")

_CLOSED = {EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.SUPERSEDED, EventStatus.EXPIRED}


def _time(value: datetime | None) -> str:
    return ensure_utc(value).strftime("%Y-%m-%d %H:%M UTC") if value else "none"


def describe_changes(before: ReiEvent, after: ReiEvent) -> list[str]:
    """What a revision changes, in plain words; empty when nothing an event shows changed."""
    changes: list[str] = []

    def compare(label: str, old, new) -> None:
        if old != new:
            changes.append(f"{label} {old if old is not None else 'none'} → {new if new is not None else 'none'}")

    old_start = ensure_utc(before.start_time) if before.start_time else None
    new_start = ensure_utc(after.start_time) if after.start_time else None
    if old_start != new_start:
        changes.append(f"start {_time(before.start_time)} → {_time(after.start_time)}")
    old_end = ensure_utc(before.end_time) if before.end_time else None
    new_end = ensure_utc(after.end_time) if after.end_time else None
    if old_end != new_end:
        changes.append(f"end {_time(before.end_time)} → {_time(after.end_time)}")
    compare("type", before.event_type, after.event_type)
    if (before.detection and before.detection.source_reports_ended) != (
        after.detection and after.detection.source_reports_ended
    ):
        changes.append(
            "the source now reports it ended"
            if after.detection and after.detection.source_reports_ended
            else "the source no longer reports it ended"
        )
    compare("direction", before.direction, after.direction)
    old_detection = before.detection
    new_detection = after.detection
    if old_detection and new_detection:
        compare("source severity", old_detection.source_severity, new_detection.source_severity)
        compare("source status", old_detection.source_status, new_detection.source_status)
        compare("source category", old_detection.source_category, new_detection.source_category)
    if (before.geometry and before.geometry.model_dump(mode="json")) != (
        after.geometry and after.geometry.model_dump(mode="json")
    ):
        changes.append("geometry changed")
    if before.title != after.title:
        changes.append("title changed")
    if (before.description or "") != (after.description or ""):
        changes.append("description changed")
    return changes


def _period(start: datetime | None, end: datetime | None) -> tuple[str | None, str | None]:
    return (_time(start) if start else None, _time(end) if end else None)


def _separate_if_period_changed(
    events: EventRepository, row: Event, before: ReiEvent, *, now: datetime
) -> str:
    """List a row whose period the source changed apart from rows of its source merged with it.

    Returns a note for the row's version ("" when nothing was separated).
    """
    if _period(row.start_time, row.end_time) == _period(before.start_time, before.end_time):
        return ""
    session = events.session
    notes = []
    if row.merged_into:
        canonical = session.get(Event, row.merged_into)
        if canonical is not None and canonical.source_id == row.source_id:
            notes.append(
                f"It no longer has the period of {canonical.event_id}: listed on its own again."
            )
            row.merged_into = None
    members = session.scalars(
        select(Event).where(Event.merged_into == row.event_id, Event.source_id == row.source_id)
    ).all()
    for member in members:
        member.merged_into = None
        member.version += 1
        member.updated_at = now
        events.record_version(
            member,
            change_reason=(
                f"The source revised the period of {row.event_id}, which this row was merged into: "
                "listed on its own again."
            ),
            changed_by=CHANGED_BY,
        )
    if members:
        notes.append(
            f"{len(members)} rows of the source merged into it no longer share its period and are "
            "listed on their own again."
        )
    return "".join(" " + note for note in notes)


def apply_source_revision(
    events: EventRepository, row: Event, derived: ReiEvent, *, revision: int, now: datetime
) -> list[str]:
    """Apply (or, for a decided event, record) a source's revision. Returns what changed."""
    before = to_rei_event(row)
    changes = describe_changes(before, derived)
    if not changes:
        return []
    note = {"revision": revision, "revised_at": now.isoformat(), "changes": changes}
    detection = dict(row.detection or {})
    status = EventStatus(row.status)

    if status in REQUIRES_LOCATION_AND_TIME or status in _CLOSED:
        detection["pending_source_revision"] = note
        reason = (
            f"The source revised its record (revision {revision}) after the event was "
            f"{status.value.lower()}; not applied, for a reviewer to decide: " + "; ".join(changes)
        )
    else:
        values = column_values(derived)
        keep_end = detection.get("period_revision") is not None
        keep_location = detection.get("location_revision") is not None
        # A field another source contributed through a merge is that source's.
        others = {
            name
            for name, origin in (detection.get("provenance") or {}).items()
            if origin and origin.get("event_id") != row.event_id
        }
        for name in SOURCE_FIELDS:
            if (name == "end_time" and keep_end) or (name == "geometry" and keep_location):
                continue
            if name in others:
                continue
            setattr(row, name, values[name])
        merged = dict(values["detection"] or {})
        for key in REVIEWER_DETECTION_KEYS + KEPT_DETECTION_KEYS:
            if detection.get(key) is not None:
                merged[key] = detection[key]
        if keep_location:
            for key in ("location", "location_class"):
                merged[key] = detection.get(key)
        merged["source_revision"] = note
        detection = merged
        reason = f"The source revised its record (revision {revision}): " + "; ".join(changes)
        reason += _separate_if_period_changed(events, row, before, now=now)

    row.detection = detection
    row.version += 1
    row.updated_at = now
    events.record_version(row, change_reason=reason, changed_by=CHANGED_BY)
    return changes
