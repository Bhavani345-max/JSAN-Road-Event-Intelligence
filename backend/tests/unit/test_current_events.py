"""Which events are current: the API's rule, the same as the console's isCurrent
(frontend/features/events/filters.ts; its cases are in events.test.ts)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from packages.event_schema import EventDetection, EventStatus, EventType, ReiEvent
from packages.geo_models import Point
from services.lifecycle import is_current
from services.lifecycle.current import EventListView, event_time_state, is_shown, matches_event_view

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
HYDERABAD = Point(type="Point", coordinates=(78.4867, 17.385))
DAY = timedelta(days=1)


def event(
    *, status=EventStatus.VALIDATION_REQUIRED, start=None, end=None, event_type=None, ended=False,
    geometry=HYDERABAD, method="keyword_rules",
):
    return ReiEvent(
        event_id="EVT-CUR000000001", source_id="test", title="Test event", status=status,
        start_time=start, end_time=end, event_type=event_type, geometry=geometry,
        detection=EventDetection(method=method, matched_keywords=[], source_reports_ended=ended),
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


def test_server_views_require_reviewed_operational_status_and_stated_timing():
    ongoing = event(status=EventStatus.APPROVED, start=NOW - DAY, end=NOW + DAY)
    upcoming = event(status=EventStatus.SCHEDULED, start=NOW + DAY, end=NOW + 3 * DAY)
    pending = event(start=NOW + DAY, end=NOW + 3 * DAY)
    untimed_approved = event(status=EventStatus.APPROVED)

    assert matches_event_view(ongoing, EventListView.CURRENT_UPCOMING, now=NOW)
    assert matches_event_view(ongoing, EventListView.CURRENT, now=NOW)
    assert not matches_event_view(ongoing, EventListView.UPCOMING, now=NOW)
    assert matches_event_view(upcoming, EventListView.UPCOMING, now=NOW)
    assert matches_event_view(pending, EventListView.VALIDATION, now=NOW)
    assert not matches_event_view(pending, EventListView.CURRENT_UPCOMING, now=NOW)
    # Without a stated start no map can draw it, so it is never current or
    # upcoming; approved anyway, it goes back to the review queue for a
    # reviewer to see (decision 0038), its status unchanged.
    assert not is_shown(untimed_approved, now=NOW)
    assert matches_event_view(untimed_approved, EventListView.VALIDATION, now=NOW)
    assert not matches_event_view(untimed_approved, EventListView.CURRENT_UPCOMING, now=NOW)
    assert untimed_approved.status is EventStatus.APPROVED


def test_server_views_keep_ended_records_accessible_without_changing_status():
    ended = event(status=EventStatus.APPROVED, start=NOW - 3 * DAY, end=NOW - DAY)
    rejected = event(status=EventStatus.REJECTED, start=NOW + DAY)

    assert event_time_state(ended, now=NOW) == "ended"
    assert not matches_event_view(ended, EventListView.CURRENT_UPCOMING, now=NOW)
    assert matches_event_view(ended, EventListView.HISTORY, now=NOW)
    assert matches_event_view(rejected, EventListView.REJECTED, now=NOW)
    assert not matches_event_view(rejected, EventListView.CURRENT_UPCOMING, now=NOW)
    # Classification is read-only; no lifecycle transition is performed here.
    assert ended.status is EventStatus.APPROVED


def test_time_view_boundaries_are_utc_and_end_time_equal_to_now_is_current():
    from datetime import timedelta

    local_now = NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    event_at_boundary = event(
        status=EventStatus.ACTIVE,
        start=local_now - timedelta(hours=1),
        end=local_now,
    )
    event_ended = event(
        status=EventStatus.ACTIVE,
        start=local_now - timedelta(hours=1),
        end=local_now - timedelta(microseconds=1),
    )

    assert event_time_state(event_at_boundary, now=NOW) == "current"
    assert event_time_state(event_ended, now=NOW) == "ended"


@pytest.mark.parametrize("zone_name", ["Asia/Kolkata", "Europe/London", "America/Toronto"])
def test_timezone_local_boundary_is_compared_as_the_same_utc_instant(zone_name):
    from datetime import timedelta

    local_now = NOW.astimezone(ZoneInfo(zone_name))
    event_at_boundary = event(
        status=EventStatus.ACTIVE,
        start=local_now - timedelta(minutes=1),
        end=local_now,
    )

    assert event_time_state(event_at_boundary, now=NOW) == "current"


# --- What the console shows at all (the user's rules of 15 October 2026) -----------

CONSOLE_VIEWS = (EventListView.CURRENT_UPCOMING, EventListView.VALIDATION)


@pytest.mark.parametrize(
    "case, why, listed_for_review",
    [
        # Listed for review since decision 0038; still on no map.
        (dict(end=NOW + DAY), "no stated start", True),
        (dict(), "no stated period, reported now", True),
        # Hidden from the review queue too.
        (dict(start=NOW - 3 * DAY, end=NOW - DAY), "ended: expired", False),
        (dict(start=NOW - DAY, end=NOW + DAY, ended=True), "the source reports it over", False),
        (dict(start=NOW - DAY, end=NOW + DAY, geometry=None), "no location", False),
    ],
)
@pytest.mark.parametrize("status", [EventStatus.VALIDATION_REQUIRED, EventStatus.QC_PENDING, EventStatus.APPROVED])
def test_maps_draw_no_unconfirmed_expired_or_unlocated_event(case, why, listed_for_review, status):
    hidden = event(status=status, **case)
    assert not is_shown(hidden, now=NOW), why
    assert not matches_event_view(hidden, EventListView.CURRENT_UPCOMING, now=NOW), why
    assert matches_event_view(hidden, EventListView.VALIDATION, now=NOW) is listed_for_review, why


@pytest.mark.parametrize(
    "status, view",
    [
        (EventStatus.VALIDATION_REQUIRED, EventListView.VALIDATION),
        (EventStatus.QC_PENDING, EventListView.VALIDATION),
        (EventStatus.APPROVED, EventListView.CURRENT_UPCOMING),
    ],
)
def test_a_located_event_with_its_stated_period_is_shown(status, view):
    shown = event(status=status, start=NOW - DAY, end=NOW + DAY)
    assert is_shown(shown, now=NOW)
    assert matches_event_view(shown, view, now=NOW)


def test_hidden_events_are_kept_and_listed_on_request():
    ended = event(status=EventStatus.APPROVED, start=NOW - 3 * DAY, end=NOW - DAY)
    undated = event()
    assert matches_event_view(ended, EventListView.HISTORY, now=NOW)
    assert matches_event_view(undated, EventListView.VALIDATION, now=NOW, include_hidden=True)
    # Hiding changes nothing about the event itself.
    assert ended.status is EventStatus.APPROVED and undated.start_time is None


def test_an_event_ending_now_is_still_shown():
    assert is_shown(event(start=NOW - DAY, end=NOW), now=NOW)
    assert not is_shown(event(start=NOW - DAY, end=NOW - timedelta(seconds=1)), now=NOW)


# --- A stated start and no end (the user's rule of 16 October 2026) ----------------


@pytest.mark.parametrize("status, view", [
    (EventStatus.VALIDATION_REQUIRED, EventListView.VALIDATION),
    (EventStatus.APPROVED, EventListView.CURRENT_UPCOMING),
    (EventStatus.APPROVED, EventListView.CURRENT),
])  # fmt: skip
def test_a_located_event_with_a_start_and_no_end_is_shown(status, view):
    open_ended = event(status=status, start=NOW - DAY)
    assert is_shown(open_ended, now=NOW)
    assert matches_event_view(open_ended, view, now=NOW)


def test_an_open_ended_event_that_starts_later_is_upcoming():
    later = event(status=EventStatus.SCHEDULED, start=NOW + DAY)
    assert matches_event_view(later, EventListView.UPCOMING, now=NOW)
    assert not matches_event_view(later, EventListView.CURRENT, now=NOW)


@pytest.mark.parametrize("method", ["keyword_rules", "ai_reading"])
def test_an_open_ended_event_read_from_an_article_is_shown_30_days_after_its_start(method):
    assert is_shown(event(start=NOW - 30 * DAY, method=method), now=NOW)
    lapsed = event(start=NOW - 30 * DAY - timedelta(seconds=1), method=method)
    assert not is_shown(lapsed, now=NOW)
    for view in CONSOLE_VIEWS:
        assert not matches_event_view(lapsed, view, now=NOW)
    # Hidden, not changed: listed when hidden events are asked for.
    assert matches_event_view(lapsed, EventListView.VALIDATION, now=NOW, include_hidden=True)


def test_an_open_ended_official_record_is_shown_until_its_source_reports_it_over():
    assert is_shown(event(start=NOW - 400 * DAY, method="source_provided"), now=NOW)
    over = event(start=NOW - 400 * DAY, method="source_provided", ended=True)
    assert not is_shown(over, now=NOW)


def test_a_stated_end_is_not_cut_short_by_the_open_end_window():
    assert is_shown(event(start=NOW - 90 * DAY, end=NOW + DAY), now=NOW)
