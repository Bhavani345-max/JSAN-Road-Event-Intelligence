"""Whether an event is still of interest: upcoming, ongoing or recently reported.

The same rule as the console's (apps/web/features/events/filters.ts,
isCurrent). Ended, rejected, cancelled and superseded events are not current,
nor is one its source reports ended. An official record with no stated end
stays current (its source lists it in force). A news report that states no
times is current while recent: this is a default view, not a test of whether
the event is real; the console can show history.
"""

from datetime import datetime, timedelta

from packages.common.time import ensure_utc
from packages.event_schema import EventStatus, EventType, ReiEvent

# How long an event whose source gave no times stays current.
RECENT_REPORT_DAYS = 7
# Road works run for months, so a report of them stays current longer.
RECENT_WORKS_REPORT_DAYS = 30

CLOSED_STATUSES = frozenset(
    {EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.SUPERSEDED, EventStatus.EXPIRED}
)


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
