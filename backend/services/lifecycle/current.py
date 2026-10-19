"""Event time and list-view rules.

`is_current` retains the conservative recency rule used by merge candidate
selection. User-facing API views use `matches_event_view`: the console's
views show only located events with a stated start that have not ended
(`is_shown`), current/upcoming lists also need an operational
lifecycle status, and article age is never evidence of an ongoing event.
"""

from datetime import datetime, timedelta
from enum import StrEnum

from packages.common.time import ensure_utc
from packages.event_schema import EventStatus, EventType, ReiEvent

# How long an event whose source gave no times stays current.
RECENT_REPORT_DAYS = 7
# Road works run for months, so a report of them stays current longer.
RECENT_WORKS_REPORT_DAYS = 30
# An event read from an article that states a start but no end is shown for
# this many days after its start (the user's rule of 16 October 2026). An
# official record with no end is shown until its source reports it over.
OPEN_END_TEXT_DAYS = 30
# Detection methods that read an event from an article's text.
TEXT_METHODS = frozenset({"keyword_rules", "ai_reading"})

CLOSED_STATUSES = frozenset(
    {EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.SUPERSEDED, EventStatus.EXPIRED}
)


class EventListView(StrEnum):
    """Server-side event list views exposed by the API."""

    CURRENT_UPCOMING = "current_upcoming"
    CURRENT = "current"
    UPCOMING = "upcoming"
    VALIDATION = "validation"
    HISTORY = "history"
    REJECTED = "rejected"


REVIEW_STATUSES = frozenset(
    {
        EventStatus.DISCOVERED,
        EventStatus.EXTRACTED,
        EventStatus.GEO_RESOLVED,
        EventStatus.VALIDATION_REQUIRED,
        EventStatus.QC_PENDING,
    }
)
OPERATIONAL_STATUSES = frozenset(
    {
        EventStatus.APPROVED,
        EventStatus.SCHEDULED,
        EventStatus.ACTIVE,
        EventStatus.MONITORING,
        EventStatus.EXTENDED,
        EventStatus.MODIFIED,
        EventStatus.REOPENED,
    }
)
HISTORY_STATUSES = frozenset(
    {EventStatus.EXPIRED, EventStatus.CANCELLED, EventStatus.SUPERSEDED}
)


def event_time_state(event: ReiEvent, *, now: datetime) -> str | None:
    """Return current/upcoming/ended from stated event times, never article age."""
    now = ensure_utc(now)
    start = ensure_utc(event.start_time) if event.start_time else None
    end = ensure_utc(event.end_time) if event.end_time else None
    if start is None and end is None:
        return None
    if end is not None and end < now:
        return "ended"
    if start is not None and start > now:
        return "upcoming"
    return "current"


def open_end_lapsed(
    method: str | None, start: datetime | None, end: datetime | None, *, now: datetime
) -> bool:
    """Whether an event read from an article, with a stated start and no end,
    is past the days it is shown (`OPEN_END_TEXT_DAYS` after its start)."""
    return (
        end is None
        and start is not None
        and method in TEXT_METHODS
        and ensure_utc(now) - ensure_utc(start) > timedelta(days=OPEN_END_TEXT_DAYS)
    )


def is_shown(event: ReiEvent, *, now: datetime) -> bool:
    """Whether the console shows the event at all (the user's rules of 15 and
    16 October 2026).

    Only an event with a location and a stated start that has not ended. An
    event without a stated start is unconfirmed. One with a start and no end
    runs until further notice: an official record until its source reports it
    over; an event read from an article for `OPEN_END_TEXT_DAYS` after its
    start. One past its end, or that its source reports over, is expired.
    Neither is shown, in the operational views or the review queue. Nothing is
    deleted or changed: the history view and the stored evidence keep them.
    """
    detection = event.detection
    return (
        event.geometry is not None
        and event.start_time is not None
        and (event.end_time is None or ensure_utc(event.end_time) >= ensure_utc(now))
        and not (detection is not None and detection.source_reports_ended)
        and not open_end_lapsed(
            detection.method if detection is not None else None,
            event.start_time,
            event.end_time,
            now=now,
        )
    )


CLOSED_VIEWS = frozenset({EventListView.HISTORY, EventListView.REJECTED})


def matches_closed_view(
    view: EventListView,
    status: EventStatus,
    end: datetime | None,
    source_ended: bool,
    *,
    now: datetime,
) -> bool:
    """The rejected and history views' rule, from the three things it reads.

    Rejected: every rejected event. History: every other event that is over:
    expired, cancelled or superseded, past its stated end, or reported over
    by its source. Both keep every record they describe (no `is_shown`).
    """
    if view is EventListView.REJECTED:
        return status is EventStatus.REJECTED
    ended = end is not None and ensure_utc(end) < ensure_utc(now)
    return status is not EventStatus.REJECTED and (
        status in HISTORY_STATUSES or source_ended or ended
    )


def matches_event_view(
    event: ReiEvent, view: EventListView, *, now: datetime, include_hidden: bool = False
) -> bool:
    """Apply lifecycle and stated-time eligibility for a server-side list view.

    The console's views (current, upcoming and the validation queue) list
    only events `is_shown` accepts, unless `include_hidden` asks for the
    others too (audit and tools). History and rejected keep every record
    they describe.
    """
    status = event.status
    state = event_time_state(event, now=now)
    source_ended = bool(event.detection and event.detection.source_reports_ended)

    if view in CLOSED_VIEWS:
        return matches_closed_view(view, status, event.end_time, source_ended, now=now)
    if not include_hidden and not is_shown(event, now=now):
        return False
    if view is EventListView.VALIDATION:
        return status in REVIEW_STATUSES or (status in OPERATIONAL_STATUSES and state is None)
    if status not in OPERATIONAL_STATUSES or source_ended or state not in {"current", "upcoming"}:
        return False
    if view is EventListView.CURRENT:
        return state == "current"
    if view is EventListView.UPCOMING:
        return state == "upcoming"
    return view is EventListView.CURRENT_UPCOMING


def is_current(event: ReiEvent, *, reported_at: datetime | None, now: datetime) -> bool:
    """`reported_at`: when the source published the report (else when it was retrieved)."""
    if event.status in CLOSED_STATUSES:
        return False
    if event.detection is not None and event.detection.source_reports_ended:
        return False
    now = ensure_utc(now)
    if event.start_time is not None or event.end_time is not None:
        # A stated start with no end runs until further notice.
        return event.end_time is None or ensure_utc(event.end_time) >= now
    if event.detection is not None and event.detection.method == "source_provided":
        # An official record that states no end ("Till Next Order") is in
        # force until its source reports it ended or a reviewer closes it;
        # no expiry is invented from its age (brief of 8 October 2026, s.16).
        return True
    if reported_at is None:
        return True
    days = RECENT_WORKS_REPORT_DAYS if event.event_type is EventType.ROAD_CONSTRUCTION else RECENT_REPORT_DAYS
    return now - ensure_utc(reported_at) <= timedelta(days=days)
