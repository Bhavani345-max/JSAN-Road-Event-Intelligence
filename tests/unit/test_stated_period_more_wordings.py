"""Explicit date wordings added on 6 October 2026: same-month ranges, "till", "on"."""

from datetime import datetime, timedelta, timezone

import pytest

from services.extraction.stated_period import find_stated_period

IST = timezone(timedelta(hours=5, minutes=30))
PUBLISHED = datetime(2026, 10, 4, 6, 0, tzinfo=timezone.utc)


def period(title="", summary=None, body=None, published_at=PUBLISHED):
    return find_stated_period(title=title, summary=summary, body=body, published_at=published_at)


def day(month, day_of_month, year=2026):
    return datetime(year, month, day_of_month, tzinfo=IST)


def end_of(month, day_of_month, year=2026):
    return datetime(year, month, day_of_month, 23, 59, 59, tzinfo=IST)


@pytest.mark.parametrize(
    "text, start, end",
    [
        ("Bathukamma celebrations across Telangana from October 10 to 18", day(10, 10), end_of(10, 18)),
        ("Traffic curbs between October 10 and 18 at Tank Bund", day(10, 10), end_of(10, 18)),
        ("Traffic curbs October 10-18 at Tank Bund", day(10, 10), end_of(10, 18)),
        ("Road closed Oct 30 to 2 for relaying", day(10, 30), end_of(11, 2)),
        # One day.
        ("Traffic restrictions in Hyderabad on October 2", day(10, 2), end_of(10, 2)),
    ],
)
def test_reads_ranges_within_a_month_and_single_days(text, start, end):
    found = period(title=text)
    assert (found.start, found.end) == (start, end)
    assert found.text in text


@pytest.mark.parametrize(
    "text, start, end",
    [
        ("Diversions at Isnapur Junction from September 26 for two months", day(9, 26), end_of(11, 25)),
        ("Closed for 6 weeks from October 1", day(10, 1), end_of(11, 11)),
        ("Curbs for a period of three months starting from October 10", day(10, 10), end_of(1, 9, 2027)),
        # The 31st of a month that has no 31st: the month's last day.
        ("Closed for one month from August 31", day(8, 31), end_of(9, 29)),
    ],
)
def test_reads_lengths_in_weeks_and_months_with_a_stated_start(text, start, end):
    found = period(title=text)
    assert (found.start, found.end) == (start, end)


def test_a_length_without_a_start_is_still_not_read():
    assert period(title="Closed for three months") is None


def test_an_end_alone_is_read_as_an_end_alone():
    found = period(title="Diversions at Khajaguda till October 18")
    assert (found.start, found.end, found.text) == (None, end_of(10, 18), "till October 18")


def test_a_complete_period_is_preferred_to_a_bare_end():
    found = period(title="Curbs till October 18", summary="In force from October 10 to October 18.")
    assert (found.start, found.end) == (day(10, 10), end_of(10, 18))


@pytest.mark.parametrize(
    "text",
    [
        "Restrictions on Sunday",
        "Curbs till further notice",
        "Diversions between 10 and 18 at the junction",
    ],
)
def test_reads_nothing_that_is_not_a_date(text):
    assert period(title=text) is None


@pytest.mark.parametrize(
    "text",
    [
        "Diversions from October 10 to 18 hours daily",  # hours, not a day
        "Closed from October 10 to 18 days",
    ],
)
def test_a_number_that_is_not_a_day_does_not_end_the_period(text):
    found = period(title=text)
    assert (found.start, found.end, found.text) == (day(10, 10), None, "from October 10")


def test_till_and_on_are_not_read_from_the_body():
    """In a body, "till October 18" too often belongs to something else."""
    assert period(title="Curbs", body="Bookings open till October 18.") is None
    assert period(title="Curbs", body="The minister spoke on October 2.") is None
