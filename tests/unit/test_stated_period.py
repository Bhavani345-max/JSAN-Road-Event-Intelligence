"""The period an article states is read from explicit wording only."""

from datetime import datetime, timedelta, timezone

import pytest

from services.extraction.stated_period import find_stated_period

IST = timezone(timedelta(hours=5, minutes=30))
PUBLISHED = datetime(2026, 9, 24, 6, 25, tzinfo=timezone.utc)


def period(title="", summary=None, body=None, published_at=PUBLISHED):
    return find_stated_period(title=title, summary=summary, body=body, published_at=published_at)


def day(month, day_of_month, year=2026):
    return datetime(year, month, day_of_month, tzinfo=IST)


def end_of(month, day_of_month, year=2026):
    return datetime(year, month, day_of_month, 23, 59, 59, tzinfo=IST)


@pytest.mark.parametrize(
    "text, start, end",
    [
        ("Diversions for 60 days from September 26", day(9, 26), end_of(11, 24)),
        ("Closed for a period of 90 days starting from July 1, 2026", day(7, 1), end_of(9, 28)),
        ("Diversions from September 26 for 60 days", day(9, 26), end_of(11, 24)),
        ("60-day traffic diversions at the junction from Sept. 26", day(9, 26), end_of(11, 24)),
        ("Road closed from October 1 to October 15", day(10, 1), end_of(10, 15)),
        ("Curbs between 3 October and 5 October 2026", day(10, 3), end_of(10, 5)),
        ("Closed for 1 day from October 2", day(10, 2), end_of(10, 2)),
    ],
)
def test_reads_a_start_and_an_end(text, start, end):
    found = period(title=text)
    assert (found.start, found.end) == (start, end)
    assert found.text in text
    assert found.found_in == "title"


def test_a_start_without_a_length_has_no_end():
    found = period(title="NH-65 traffic diversion from September 26")
    assert (found.start, found.end) == (day(9, 26), None)
    assert found.text == "from September 26"


@pytest.mark.parametrize(
    "text",
    [
        "Traffic diversions at the junction",
        "Diversions for 60 days",  # a length but no start
        "Closed for three months",  # not written as a number of days
        "Restrictions from Monday",  # a weekday is not a date
        "Works to finish by May 2027",
    ],
)
def test_reads_nothing_that_is_not_stated_explicitly(text):
    assert period(title=text) is None


def test_an_implausible_length_is_dropped_but_the_stated_start_is_kept():
    found = period(title="Diversions for 5000 days from September 26")
    assert (found.start, found.end, found.text) == (day(9, 26), None, "from September 26")


def test_a_bare_start_in_the_body_is_not_trusted():
    """In a body, "from <date>" too often belongs to something else."""
    assert period(title="Curbs", body="The scheme ran from September 26 last year.") is None
    # A complete period is taken from the body.
    found = period(title="Curbs", body="The road is closed for 10 days from September 26.")
    assert (found.start, found.end, found.found_in) == (day(9, 26), end_of(10, 5), "body")


def test_the_year_is_the_one_nearest_publication():
    december = datetime(2026, 12, 28, tzinfo=timezone.utc)
    found = period(title="Closed from January 2 to January 5", published_at=december)
    assert (found.start, found.end) == (day(1, 2, 2027), end_of(1, 5, 2027))


def test_nothing_is_read_without_a_publication_date():
    assert period(title="Diversions for 60 days from September 26", published_at=None) is None


def test_a_date_far_from_publication_is_treated_as_a_misreading():
    assert period(title="Closed from March 1, 2020 to March 5, 2020") is None
