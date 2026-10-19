"""Event time and list-view rules.

`is_current` retains the conservative recency rule used by merge candidate
selection. User-facing API views use `matches_event_view`. Four levels, each
narrower than the one before (decision 0038):

- Stored: every event detected, whatever its dates, with its evidence. No
  rule here deletes or changes one.
- Listed for review (`listed_for_review`): located, awaiting review, and not
  known to be over. A stated start is not needed: an event that states only an
  end is listed until that end, an official record its source still lists is
  listed, and a report stating no period at all is listed for a short time
  after it was published (RECENT_REPORT_DAYS; road works longer).
- On the map (`is_shown`, `map_rule`): located, with a stated start, and not
  over. No start is ever derived from an end alone.
- Current and upcoming (operations): additionally an operational status,
  which only a reviewer gives; article age is never evidence of an ongoing
  event, and no status is set by these rules.
"""

from datetime import datetime, timedelta
from enum import StrEnum

from packages.common.time import ensure_utc
from packages.event_schema import EventStatus, EventType, ReiEvent

# How long an event whose source gave no times stays current, and stays in the
# review queue after it was reported (decision 0038): long enough for a reviewer
# to check it; after that a report that states no period is no evidence that
# the measure still holds.
RECENT_REPORT_DAYS = 7
# Road works run for months, so a report of them stays current longer.
RECENT_WORKS_REPORT_DAYS = 30
# The detection method of a record an official source published with its fields.
SOURCE_PROVIDED = "source_provided"
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


def map_rule(
    *,
    located: bool,
    start: datetime | None,
    end: datetime | None,
    source_ended: bool,
    method: str | None,
    now: datetime,
) -> str | None:
    """The first rule that keeps an event off the console's maps, or None when
    they may draw it (the user's rules of 15 and 16 October 2026).

    "no_location"; "no_start": no stated start, so no period to show it for
    (none is derived from an end alone); "ended": past its stated end;
    "source_ended": its source reports it over; "open_end_lapsed": read from an
    article with a start and no end, over `OPEN_END_TEXT_DAYS` after its start
    (an official record with no end runs until its source reports it over).
    """
    if not located:
        return "no_location"
    if start is None:
        return "no_start"
    if end is not None and ensure_utc(end) < ensure_utc(now):
        return "ended"
    if source_ended:
        return "source_ended"
    if open_end_lapsed(method, start, end, now=now):
        return "open_end_lapsed"
    return None


def _facts(event: ReiEvent) -> dict:
    detection = event.detection
    return {
        "located": event.geometry is not None,
        "start": event.start_time,
        "end": event.end_time,
        "source_ended": bool(detection and detection.source_reports_ended),
        "method": detection.method if detection is not None else None,
    }


def is_shown(event: ReiEvent, *, now: datetime) -> bool:
    """Whether the console's maps may draw the event: located, with a stated
    start, and not over (`map_rule`). Whether a map draws it also depends on
    the view (awaiting review or validated). Nothing is deleted or changed for
    an event that is not drawn: the review list, the history view and the
    stored evidence keep it."""
    return map_rule(**_facts(event), now=now) is None


def review_listing(
    *,
    located: bool,
    start: datetime | None,
    end: datetime | None,
    source_ended: bool,
    method: str | None,
    event_type: str | None,
    reported_at: datetime | None,
    now: datetime,
) -> bool:
    """Whether the review queue lists an event, from the facts it reads
    (decision 0038). The status is checked by the view.

    A located event that is not known to be over: with a stated start, while
    the map may draw it; with only a stated end ("until 20 October"), until
    that end, its start staying unknown; an official record with no dates,
    while its source does not report it over; any other report with no dates,
    for RECENT_REPORT_DAYS after it was reported (RECENT_WORKS_REPORT_DAYS for
    road works), then it is treated as probably over and only stored.
    """
    if not located:
        return False
    if start is not None:
        return map_rule(
            located=located, start=start, end=end, source_ended=source_ended, method=method, now=now
        ) is None
    if source_ended:
        return False
    if end is not None:
        return ensure_utc(end) >= ensure_utc(now)
    if method == SOURCE_PROVIDED:
        return True
    if reported_at is None:
        return False
    days = RECENT_WORKS_REPORT_DAYS if event_type == EventType.ROAD_CONSTRUCTION.value else RECENT_REPORT_DAYS
    return ensure_utc(now) - ensure_utc(reported_at) <= timedelta(days=days)


def listed_for_review(event: ReiEvent, *, reported_at: datetime | None = None, now: datetime) -> bool:
    """`review_listing` for an event; `reported_at` is when its source
    published it (else when REI stored it, the event's `created_at`)."""
    event_type = event.event_type.value if event.event_type else None
    return review_listing(
        **_facts(event), event_type=event_type, reported_at=reported_at or event.created_at, now=now
    )


def in_review_status(status: EventStatus | str, start: datetime | None) -> bool:
    """Whether the review queue takes an event of this status: one awaiting
    review, or a validated one with no stated start (approved anyway), which
    neither map can draw and so a reviewer still has to see."""
    status = EventStatus(status)
    return status in REVIEW_STATUSES or (status in OPERATIONAL_STATUSES and start is None)


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
    event: ReiEvent,
    view: EventListView,
    *,
    now: datetime,
    include_hidden: bool = False,
    reported_at: datetime | None = None,
) -> bool:
    """Apply lifecycle and stated-time eligibility for a server-side list view.

    The review queue lists what `listed_for_review` accepts (`reported_at`:
    when the source published the event); current and upcoming only events a
    map may draw (`is_shown`). `include_hidden` asks for the others too (audit
    and tools). History and rejected keep every record they describe.
    """
    status = event.status
    state = event_time_state(event, now=now)
    source_ended = bool(event.detection and event.detection.source_reports_ended)

    if view in CLOSED_VIEWS:
        return matches_closed_view(view, status, event.end_time, source_ended, now=now)
    if view is EventListView.VALIDATION:
        return in_review_status(status, event.start_time) and (
            include_hidden or listed_for_review(event, reported_at=reported_at, now=now)
        )
    if not include_hidden and not is_shown(event, now=now):
        return False
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
