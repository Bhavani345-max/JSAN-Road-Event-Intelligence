"""Which events are current: the API's rule, the same as the console's isCurrent
(apps/web/features/events/filters.ts; its cases are in events.test.ts)."""

from datetime import datetime, timedelta, timezone

import pytest

from packages.event_schema import EventDetection, EventStatus, EventType, ReiEvent
from services.lifecycle import is_current

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
DAY = timedelta(days=1)


def event(*, status=EventStatus.VALIDATION_REQUIRED, start=None, end=None, event_type=None, ended=False):
    return ReiEvent(
        event_id="EVT-CUR000000001", source_id="test", title="Test event", status=status,
        start_time=start, end_time=end, event_type=event_type,
        detection=EventDetection(method="keyword_rules", matched_keywords=[], source_reports_ended=ended),
        created_at=NOW, updated_at=NOW,
    )  # fmt: skip


@pytest.mark.parametrize(
    "case, current",
    [
        (dict(start=NOW + DAY, end=NOW + 3 * DAY), True),  # upcoming
        (dict(start=NOW - DAY, end=NOW + DAY), True),  # ongoing
        (dict(start=NOW - DAY), True),  # until further notice
        (dict(end=NOW + DAY), True),
        (dict(start=NOW - 3 * DAY, end=NOW - DAY), False),  # ended
        (dict(start=NOW + DAY, status=EventStatus.REJECTED), False),
        (dict(start=NOW + DAY, status=EventStatus.CANCELLED), False),
        (dict(start=NOW + DAY, status=EventStatus.EXPIRED), False),
        (dict(start=NOW - DAY, ended=True), False),  # the source says it is over
    ],
)
def test_stated_times_decide(case, current):
    assert is_current(event(**case), reported_at=NOW - 60 * DAY, now=NOW) is current


@pytest.mark.parametrize(
    "age_days, event_type, current",
    [
        (6, None, True),
        (8, None, False),
        (8, EventType.ROAD_CONSTRUCTION, True),  # works reports stay 30 days
        (31, EventType.ROAD_CONSTRUCTION, False),
    ],
)
def test_an_undated_report_is_current_while_it_is_recent(age_days, event_type, current):
    e = event(event_type=event_type)
    assert is_current(e, reported_at=NOW - age_days * DAY, now=NOW) is current


def test_an_undated_event_with_no_report_time_is_current():
    assert is_current(event(), reported_at=None, now=NOW) is True


def test_an_official_record_with_no_stated_end_stays_current_whatever_its_age():
    """"Till Next Order": no end is invented from the record's age (brief of 8 Oct 2026, s.16)."""
    official = event()
    official.detection.method = "source_provided"
    assert is_current(official, reported_at=NOW - 90 * DAY, now=NOW) is True
    # Unless its source reports it ended, or a reviewer closed it.
    official.detection.source_reports_ended = True
    assert is_current(official, reported_at=NOW - 90 * DAY, now=NOW) is False
    closed = event(status=EventStatus.REJECTED)
    closed.detection.method = "source_provided"
    assert is_current(closed, reported_at=NOW, now=NOW) is False
