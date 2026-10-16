from collections import Counter
from datetime import datetime

from sqlalchemy import func, or_, select
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
from packages.cities import default_city
from packages.event_schema import EventSeverity, EventStatus, ReiEvent
from services.lifecycle import approval_blockers
from services.lifecycle.current import (
    OPERATIONAL_STATUSES,
    REVIEW_STATUSES,
    EventListView,
    matches_event_view,
    open_end_lapsed,
)

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
        include_hidden: bool = False,
        view: EventListView = EventListView.CURRENT_UPCOMING,
        q: str | None = None,
        limit: int = 200,
        offset: int = 0,
        now: datetime | None = None,
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
            city_filter = Event.city == city
            if city == default_city().name:
                city_filter = or_(city_filter, Event.city.is_(None))
            filters.append(city_filter)
        if not include_merged:
            # An event merged into another is shown as part of it.
            filters.append(Event.merged_into.is_(None))

        # Most recently published first.
        order = (func.coalesce(SourceArtifact.published_at, Event.created_at).desc(), Event.event_id)
        terms = (q or "").lower().split()
        now = now or utc_now()
        if not terms and not include_hidden and view in _CONSOLE_VIEWS:
            return self._list_shown(filters + _shown_filters(view, now), order, limit, offset, now)

        query = (
            select(Event)
            .outerjoin(Event.artifact)
            .options(contains_eager(Event.artifact))
            .where(*filters)
            .order_by(*order)
        )
        # Apply view and text eligibility before pagination. At current REI
        # volumes this keeps totals and pages correct without dialect-specific
        # JSON timestamp/status expressions.
        matched = [
            row
            for row in self.session.scalars(query).unique()
            if (not terms or _matches(row, terms))
            and matches_event_view(to_rei_event(row), view, now=now, include_hidden=include_hidden)
        ]
        return matched[offset : offset + limit], len(matched)

    def _list_shown(
        self, filters, order, limit: int, offset: int, now: datetime
    ) -> "tuple[list[Event], int]":
        """A console view without a text search: filtered by the database, one page loaded.

        The database applies the view's column rules (`_shown_filters`); the
        rules inside the detection record (`_hidden_by_detection`) are read
        here. Only the page's events are loaded in full.
        """
        ids = [
            event_id
            for event_id, detection, start, end in self.session.execute(
                select(Event.event_id, Event.detection, Event.start_time, Event.end_time)
                .outerjoin(Event.artifact)
                .where(*filters)
                .order_by(*order)
            )
            if not _hidden_by_detection(detection, start, end, now)
        ]
        page = ids[offset : offset + limit]
        if not page:
            return [], len(ids)
        rows = {
            row.event_id: row
            for row in self.session.scalars(
                select(Event)
                .outerjoin(Event.artifact)
                .options(contains_eager(Event.artifact))
                .where(Event.event_id.in_(page))
            ).unique()
        }
        return [rows[event_id] for event_id in page], len(ids)

    def count_shown_by_city(
        self, view: EventListView, *, now: datetime | None = None
    ) -> "dict[str | None, dict[str, Counter]]":
        """What a console view lists, counted per city (by status and by type).

        The same rules as `list` for that view, without loading the events.
        """
        if view not in _CONSOLE_VIEWS:
            raise ValueError(f"{view} is not a console view")
        counts: dict[str | None, dict[str, Counter]] = {}
        now = now or utc_now()
        rows = self.session.execute(
            select(
                Event.city,
                Event.status,
                Event.event_type,
                Event.detection,
                Event.start_time,
                Event.end_time,
            ).where(Event.merged_into.is_(None), *_shown_filters(view, now))
        )
        for city, status, event_type, detection, start, end in rows:
            if _hidden_by_detection(detection, start, end, now):
                continue
            found = counts.setdefault(city, {"status": Counter(), "type": Counter()})
            found["status"][status] += 1
            found["type"][event_type or "UNCLASSIFIED"] += 1
        return counts

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


_CONSOLE_VIEWS = frozenset(
    {
        EventListView.CURRENT_UPCOMING,
        EventListView.CURRENT,
        EventListView.UPCOMING,
        EventListView.VALIDATION,
    }
)


def _hidden_by_detection(detection: dict | None, start, end, now: datetime) -> bool:
    """The part of `is_shown` read from the detection record: the source reports
    the event over, or an open-ended event read from an article has lapsed."""
    detection = detection or {}
    return bool(detection.get("source_reports_ended")) or open_end_lapsed(
        detection.get("method"), start, end, now=now
    )


def _shown_filters(view: EventListView, now: datetime) -> list:
    """`matches_event_view` for a console view, as database conditions (all but
    `_hidden_by_detection`, which reads the detection record)."""
    filters = [
        Event.geometry.is_not(None),
        Event.start_time.is_not(None),
        or_(Event.end_time.is_(None), Event.end_time >= now),
    ]
    if view is EventListView.VALIDATION:
        return filters + [Event.status.in_([status.value for status in REVIEW_STATUSES])]
    filters.append(Event.status.in_([status.value for status in OPERATIONAL_STATUSES]))
    if view is EventListView.CURRENT:
        filters.append(Event.start_time <= now)
    elif view is EventListView.UPCOMING:
        filters.append(Event.start_time > now)
    return filters


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
