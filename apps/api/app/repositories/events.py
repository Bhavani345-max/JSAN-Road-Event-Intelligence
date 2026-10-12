from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager

from app.models import Event, EventMergeCandidate, EventVersion, Source, SourceArtifact
from app.schemas.event import (
    ContributingEvidenceOut,
    EventOut,
    EvidenceOut,
    MergeCandidateOut,
    SourceSummary,
)
from packages.common.text import html_to_text
from packages.common.time import utc_now
from packages.event_schema import EventSeverity, EventStatus, ReiEvent
from services.lifecycle import approval_blockers

# Columns that are copied one-to-one between the canonical event and its row.
_CANONICAL_FIELDS = tuple(ReiEvent.model_fields)


def to_rei_event(row: Event) -> ReiEvent:
    return ReiEvent.model_validate({name: getattr(row, name) for name in _CANONICAL_FIELDS})


def source_summary(source: Source) -> SourceSummary:
    return SourceSummary(
        source_id=source.source_id,
        source_name=source.source_name,
        source_type=source.source_type,
        source_class=source.source_class,
        source_tier=source.source_tier,
        discovery_only=bool(source.discovery_only),
    )


def to_event_out(
    row: Event,
    *,
    members: list[Event] | None = None,
    candidates: list[EventMergeCandidate] | None = None,
    others: dict[str, Event] | None = None,
) -> EventOut:
    """The API form of an event, with the evidence of events merged into it
    (`members`) and its pending merge candidates (`others` holds their other events)."""
    artifact = row.artifact
    event = to_rei_event(row)
    how = {
        c.get("event_id"): c.get("how") for c in (row.detection or {}).get("contributions") or []
    }
    return EventOut(
        **event.model_dump(),
        merged_into=row.merged_into,
        approval_blockers=(
            approval_blockers(event) if event.status is EventStatus.QC_PENDING else []
        ),
        other_evidence=[
            ContributingEvidenceOut(
                event_id=member.event_id,
                source=source_summary(member.source),
                artifact_id=member.source_artifact_id,
                url=(member.artifact.url if member.artifact else None) or member.source_reference,
                title=member.artifact.title if member.artifact else member.title,
                published_at=member.artifact.published_at if member.artifact else None,
                retrieved_at=member.artifact.retrieved_at if member.artifact else None,
                how=how.get(member.event_id),
            )
            for member in members or []
        ],
        merge_candidates=[
            MergeCandidateOut(
                candidate_id=c.id,
                classification=c.classification,
                status=c.status,
                reasons=c.reasons or [],
                conflicts=c.conflicts or [],
                other_event_id=other.event_id,
                other_title=other.title,
                other_source=source_summary(other.source),
            )
            for c in candidates or []
            if (other := (others or {}).get(c.event_b if c.event_a == row.event_id else c.event_a))
            is not None
        ],
        source=source_summary(row.source),
        evidence=(
            EvidenceOut(
                artifact_id=artifact.artifact_id,
                url=artifact.url,
                title=artifact.title,
                published_at=artifact.published_at,
                retrieved_at=artifact.retrieved_at,
                content_hash=artifact.content_hash,
            )
            if artifact
            else None
        ),
        version=row.version,
    )


def column_values(event: ReiEvent) -> dict:
    """The canonical event as column values (enums and geometry as plain JSON)."""
    values = event.model_dump(mode="json")
    # Timestamps stay as datetimes for the database driver.
    for name in ("start_time", "end_time", "created_at", "updated_at"):
        values[name] = getattr(event, name)
    return values


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        status: EventStatus | None = None,
        severity: EventSeverity | None = None,
        source_id: str | None = None,
        city: str | None = None,
        include_merged: bool = False,
        q: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[Event], int]:
        filters = []
        if status is not None:
            filters.append(Event.status == status.value)
        if severity is not None:
            # REI's own severity only; the source's severity words are not searched.
            filters.append(Event.severity == severity.value)
        if source_id is not None:
            filters.append(Event.source_id == source_id)
        if city is not None:
            # The city's display name, as event creation records it.
            filters.append(Event.city == city)
        if not include_merged:
            # An event merged into another is shown as part of it.
            filters.append(Event.merged_into.is_(None))

        # Most recently published first.
        query = (
            select(Event)
            .outerjoin(Event.artifact)
            .options(contains_eager(Event.artifact))
            .where(*filters)
            .order_by(
                func.coalesce(SourceArtifact.published_at, Event.created_at).desc(),
                Event.event_id,
            )
        )
        terms = (q or "").lower().split()
        if terms:
            # Text search runs in Python over the event and its stored evidence.
            # That is adequate for the PoC's event volume; a full-text index
            # replaces it when volumes grow.
            matches = [
                row for row in self.session.scalars(query).unique() if _matches(row, terms)
            ]
            return matches[offset : offset + limit], len(matches)

        total = self.session.scalar(select(func.count()).select_from(Event).where(*filters)) or 0
        rows = self.session.scalars(query.limit(limit).offset(offset)).unique()
        return list(rows), total

    def get(self, event_id: str) -> Event | None:
        return self.session.get(Event, event_id)

    def add(
        self, event: ReiEvent, *, artifact_id: str | None, change_reason: str, changed_by: str
    ) -> Event:
        row = Event(**column_values(event), source_artifact_id=artifact_id, version=1)
        self.session.add(row)
        self.record_version(row, change_reason=change_reason, changed_by=changed_by)
        return row

    def record_version(self, row: Event, *, change_reason: str | None, changed_by: str) -> None:
        """Snapshot the event's current state as its current version."""
        row.versions.append(
            EventVersion(
                version=row.version,
                status=row.status,
                snapshot=to_rei_event(row).model_dump(mode="json"),
                change_reason=change_reason,
                changed_by=changed_by,
                created_at=utc_now(),
            )
        )



def searchable_text(row: Event) -> str:
    """Everything a reviewer may search an event by, lower-cased.

    Covers the event itself, its source, and the evidence it was derived from:
    the article's title, summary and full text.
    """
    source: Source = row.source
    parts = [row.title, row.description, row.affected_road, row.city, row.event_type]
    parts += [source.source_name, source.organization]
    if row.artifact is not None:
        raw = row.artifact.raw_content or {}
        parts += [
            row.artifact.title,
            html_to_text(raw.get("summary_html")),
            html_to_text(raw.get("content_html")),
        ]
    if row.detection:
        parts += row.detection.get("road_mentions") or []
    return " ".join(part for part in parts if part).lower()


def _matches(row: Event, terms: list[str]) -> bool:
    text = searchable_text(row)
    return all(term in text for term in terms)


def to_event_outs(session: Session, rows: list[Event]) -> list[EventOut]:
    """API forms of several events, loading merged evidence and candidates in bulk."""
    ids = [row.event_id for row in rows]
    members: dict[str, list[Event]] = {}
    if ids:
        for member in session.scalars(select(Event).where(Event.merged_into.in_(ids))).unique():
            members.setdefault(member.merged_into, []).append(member)
    from app.services.merge_service import pending_candidates_by_event

    candidates = {i: c for i, c in pending_candidates_by_event(session).items() if i in set(ids)}
    other_ids = {
        other
        for event_id, found in candidates.items()
        for c in found
        for other in (c.event_a, c.event_b)
        if other != event_id
    }
    others = (
        {e.event_id: e for e in session.scalars(select(Event).where(Event.event_id.in_(other_ids))).unique()}
        if other_ids
        else {}
    )
    return [
        to_event_out(
            row,
            members=members.get(row.event_id),
            candidates=candidates.get(row.event_id),
            others=others,
        )
        for row in rows
    ]
