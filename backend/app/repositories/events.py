import threading
import weakref
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import Engine, and_, event, func, or_, select
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
from packages.common.time import ensure_utc, utc_now
from packages.cities import default_city
from packages.event_schema import EventSeverity, EventStatus, ReiEvent
from services.lifecycle import approval_blockers
from services.lifecycle.current import (
    CLOSED_VIEWS,
    OPERATIONAL_STATUSES,
    REVIEW_STATUSES,
    EventListView,
    in_review_status,
    map_rule,
    matches_closed_view,
    matches_event_view,
    review_listing,
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
    off_map_reason = map_rule(
        located=event.geometry is not None,
        start=event.start_time,
        end=event.end_time,
        source_ended=bool(event.detection and event.detection.source_reports_ended),
        method=event.detection.method if event.detection else None,
        now=utc_now(),
    )
    return EventOut(
        **event.model_dump(),
        map_eligible=off_map_reason is None,
        off_map_reason=off_map_reason,
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
        cities: Sequence[str] | None = None,
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
        if cities is not None:
            # The cities' display names, as event creation records them: one
            # city, or a country entry and the cities within it (decision 0035).
            city_filter = Event.city.in_(list(cities))
            if default_city().name in cities:
                city_filter = or_(city_filter, Event.city.is_(None))
            filters.append(city_filter)
        if not include_merged:
            # An event merged into another is shown as part of it.
            filters.append(Event.merged_into.is_(None))

        # Most recently published first.
        order = (func.coalesce(SourceArtifact.published_at, Event.created_at).desc(), Event.event_id)
        terms = (q or "").lower().split()
        now = now or utc_now()
        if not terms and (view in CLOSED_VIEWS or (view in _CONSOLE_VIEWS and not include_hidden)):
            # `include_hidden` changes nothing for history and rejected.
            view_filters, keep = _view_rule(view, now)
            return self._list_light(filters + view_filters, order, limit, offset, keep=keep)

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
            and matches_event_view(
                to_rei_event(row),
                view,
                now=now,
                include_hidden=include_hidden,
                reported_at=(row.artifact.published_at if row.artifact else None) or row.created_at,
            )
        ]
        return matched[offset : offset + limit], len(matched)

    def _list_light(
        self, filters, order, limit: int, offset: int, *, keep
    ) -> "tuple[list[Event], int]":
        """A view without a text search: filtered by the database, one page loaded.

        The database applies the view's column rules (`_view_rule`); `keep`
        applies the rest to a row of `_light_columns`. Only the page's events
        are loaded in full, with their articles.
        """
        ids = [
            row.event_id
            for row in self.session.execute(
                select(*_light_columns()).outerjoin(Event.artifact).where(*filters).order_by(*order)
            )
            if keep(row)
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
        view_filters, keep = _view_rule(view, now)
        rows = self.session.execute(
            select(*_light_columns(), Event.city)
            .outerjoin(Event.artifact)
            .where(Event.merged_into.is_(None), *view_filters)
        )
        for row in rows:
            if not keep(row):
                continue
            found = counts.setdefault(row.city, {"status": Counter(), "type": Counter()})
            found["status"][row.status] += 1
            found["type"][row.event_type or "UNCLASSIFIED"] += 1
        return counts

    def tally(self, *, by: str, now: datetime | None = None) -> "dict[str | None, Counter]":
        """Every event counted from detection to the map, per source or per city.

        `by` is "source" (source id) or "city" (the city's name as events record
        it; None for legacy records). Keys: detected (not merged into another),
        merged, rejected, closed, pending_review, validated, recent (detected in
        the last 7 days); on_map_review: events awaiting review on the review
        queue's map; on_map_operations: validated events on the operations map
        (exactly what those two console views list; the two are never added
        up: an event awaiting review is not a confirmed road event). For
        events not on their view's map, the first rule that hides each,
        separately for the review queue (hidden_review_<rule>) and the
        operations view (hidden_operations_<rule>); rules: no_location,
        no_start, ended, source_ended, open_end_lapsed (decisions 0034, 0035).
        listed_review: what the review queue lists, on its map or not (it also
        lists located events with no stated start that are not known to be
        over, decision 0038).

        Counting reads every event, seconds with tens of thousands, and the
        console asks for both groupings at once and again after each decision.
        So one count of both serves every request until anything is committed
        to the database, or for at most `_TALLY_MAX_AGE` (the rules depend on
        the time, and the command-line tools write from other processes).
        Requests that arrive during a count wait for it. Given `now`, the
        events are counted afresh.
        """
        if now is not None:
            return _copied(self._count_all(ensure_utc(now))[by])
        shared = _shared_tally(self.session.get_bind().engine)
        with shared.lock:
            now = utc_now()
            if (
                shared.counts is None
                or shared.counted_at is None
                or shared.counted_version != shared.version
                or now - shared.counted_at >= _TALLY_MAX_AGE
            ):
                version = shared.version
                shared.counts = self._count_all(now)
                shared.counted_version, shared.counted_at = version, now
            return _copied(shared.counts[by])

    def _count_all(self, now: datetime) -> "dict[str, dict[str | None, Counter]]":
        """`tally` for both groupings in one pass: {"source": ..., "city": ...}."""
        recent_since = now - timedelta(days=7)
        rows = self.session.execute(
            select(*_light_columns(), Event.source_id, Event.city, Event.merged_into, Event.created_at)
            .outerjoin(Event.artifact)
        )
        by_source: dict[str | None, Counter] = {}
        by_city: dict[str | None, Counter] = {}
        for row in rows:
            found = (by_source.setdefault(row.source_id, Counter()), by_city.setdefault(row.city, Counter()))
            for name in _tally_names(row, now, recent_since):
                for counts in found:
                    counts[name] += 1
        return {"source": by_source, "city": by_city}

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


def _light_columns() -> tuple:
    """What the view rules read, without the event's or its article's full records.

    Of the detection record only the two facts the rules read, taken out by the
    database: parsing every whole record was most of the cost of a count.
    `reported_at` is when the source published the event, else when REI stored it.
    """
    return (
        Event.event_id,
        Event.status,
        Event.event_type,
        Event.detection["source_reports_ended"].as_boolean().label("source_reports_ended"),
        Event.detection["method"].as_string().label("detection_method"),
        Event.start_time,
        Event.end_time,
        Event.geometry.is_not(None).label("located"),
        func.coalesce(SourceArtifact.published_at, Event.created_at).label("reported_at"),
    )


def _row_facts(row) -> dict:
    """The facts `map_rule` reads, from a row of `_light_columns`."""
    return {
        "located": bool(row.located),
        "start": row.start_time,
        "end": row.end_time,
        "source_ended": bool(row.source_reports_ended),
        "method": row.detection_method,
    }


_REVIEW_VALUES = frozenset(status.value for status in REVIEW_STATUSES)
_OPERATIONAL_VALUES = frozenset(status.value for status in OPERATIONAL_STATUSES)


def _tally_names(row, now: datetime, recent_since: datetime) -> list[str]:
    """The `tally` keys one event counts under, from a row of `_light_columns`."""
    if row.merged_into:
        return ["merged"]
    names = ["detected"]
    if row.created_at is not None and ensure_utc(row.created_at) >= recent_since:
        names.append("recent")
    if row.status in _REVIEW_VALUES:
        group = "pending_review"
    elif row.status in _OPERATIONAL_VALUES:
        group = "validated"
    else:
        names.append("rejected" if row.status == EventStatus.REJECTED.value else "closed")
        return names
    names.append(group)
    if in_review_status(row.status, row.start_time) and _listed_for_review(row, now):
        names.append("listed_review")
    map_name = "review" if group == "pending_review" else "operations"
    rule = map_rule(**_row_facts(row), now=now)
    names.append(f"on_map_{map_name}" if rule is None else f"hidden_{map_name}_{rule}")
    return names


def _copied(counts: "dict[str | None, Counter]") -> "dict[str | None, Counter]":
    """A shared count, safe for the caller to change."""
    return {key: Counter(found) for key, found in counts.items()}


# How long one count may serve requests when nothing has been committed.
_TALLY_MAX_AGE = timedelta(seconds=60)


class _SharedTally:
    """The last count of one database's events, shared by its requests."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.version = 0  # raised by every commit to the database
        self.counted_version = -1
        self.counted_at: datetime | None = None
        self.counts: dict[str, dict[str | None, Counter]] | None = None


_SHARED_TALLIES: "weakref.WeakKeyDictionary[Engine, _SharedTally]" = weakref.WeakKeyDictionary()
_SHARED_TALLIES_LOCK = threading.Lock()


def _shared_tally(engine: Engine) -> _SharedTally:
    with _SHARED_TALLIES_LOCK:
        shared = _SHARED_TALLIES.get(engine)
        if shared is None:
            shared = _SHARED_TALLIES[engine] = _SharedTally()
        return shared


@event.listens_for(Engine, "commit")
def _count_again_after_commit(connection) -> None:
    """Any commit may change a count: the next `tally` counts again."""
    shared = _SHARED_TALLIES.get(connection.engine)
    if shared is not None:
        shared.version += 1


def _listed_for_review(row, now: datetime) -> bool:
    return review_listing(**_row_facts(row), event_type=row.event_type, reported_at=row.reported_at, now=now)


def _view_rule(view: EventListView, now: datetime):
    """A view's rule as database conditions, and the rest as a test of a row of
    `_light_columns` (the parts read from the detection record or the article).
    The same as `matches_event_view`."""
    if view in CLOSED_VIEWS:
        # The status here; the end and the source's report of it over in the test.
        status_filter = (
            Event.status == EventStatus.REJECTED.value
            if view is EventListView.REJECTED
            else Event.status != EventStatus.REJECTED.value
        )
        return [status_filter], lambda row: matches_closed_view(
            view, EventStatus(row.status), row.end_time, _row_facts(row)["source_ended"], now=now
        )
    located_not_ended = [Event.geometry.is_not(None), or_(Event.end_time.is_(None), Event.end_time >= now)]
    if view is EventListView.VALIDATION:
        # Awaiting review, or validated with no stated start (`in_review_status`).
        status_filter = or_(
            Event.status.in_([status.value for status in REVIEW_STATUSES]),
            and_(
                Event.status.in_([status.value for status in OPERATIONAL_STATUSES]),
                Event.start_time.is_(None),
            ),
        )
        return located_not_ended + [status_filter], lambda row: _listed_for_review(row, now)
    filters = located_not_ended + [
        Event.start_time.is_not(None),
        Event.status.in_([status.value for status in OPERATIONAL_STATUSES]),
    ]
    if view is EventListView.CURRENT:
        filters.append(Event.start_time <= now)
    elif view is EventListView.UPCOMING:
        filters.append(Event.start_time > now)
    return filters, lambda row: map_rule(**_row_facts(row), now=now) is None


def _closed_filters(view: EventListView) -> list:
    """The status part of `matches_closed_view`, as a database condition."""
    if view is EventListView.REJECTED:
        return [Event.status == EventStatus.REJECTED.value]
    return [Event.status != EventStatus.REJECTED.value]


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
