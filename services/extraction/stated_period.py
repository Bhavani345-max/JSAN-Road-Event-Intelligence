"""Reads the period an article states for a road measure.

Only explicit wording is read: "for 60 days from September 26", "from July 1
to July 15", "from October 10 to 18", "October 10-18", "till October 18",
"on October 2", "for two months from September 26", "from September 26". The
dates are calendar arithmetic on
what the article says; nothing is estimated. The words they were read from
are kept with the event so a reviewer can check them.

Dates are whole days in the city's time zone (India Standard Time unless a
city is given): an article that gives no time of day is not given one. The year, when the article leaves it out, is the one
that puts the date nearest to the article's publication.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

from packages.common.time import IST, end_of_day, start_of_day

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?"
    r"|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"

# A period longer than this, or starting this far from publication, is taken
# to be a misreading rather than a road measure.
MAX_DAYS = 730
MAX_DAYS_FROM_PUBLICATION = 200


def _date(group: str) -> str:
    """Pattern for "September 26", "Sept. 26, 2026" or "26 September 2026"."""
    return (
        rf"(?:(?P<{group}m>{_MONTH})\s+(?P<{group}d>{_DAY})"
        rf"|(?P<{group}d2>{_DAY})\s+(?P<{group}m2>{_MONTH}))"
        rf"(?:,?\s+(?P<{group}y>\d{{4}}))?"
    )


_DAYS = r"(?P<n>\d{1,3})"
# "two months", "6 weeks": a length in weeks or months, with a stated start.
_WORD_NUMBERS = {
    "one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}  # fmt: skip
_LENGTH = (
    r"(?P<len>\d{1,2}|" + "|".join(_WORD_NUMBERS) + r")[- ](?P<unit>weeks?|months?)"
)
_FLAGS = re.IGNORECASE
# "for 60 days from September 26", "for a period of 90 days starting from July 1, 2026"
_FOR_DAYS_FROM = re.compile(
    rf"\bfor\s+(?:a\s+period\s+of\s+|the\s+next\s+)?{_DAYS}\s+days?,?\s+"
    rf"(?:(?:starting|beginning|commencing)\s+)?from\s+{_date('a')}",
    _FLAGS,
)
# "from September 26 for 60 days"
_FROM_FOR_DAYS = re.compile(
    rf"\bfrom\s+{_date('a')}\s+for\s+(?:a\s+period\s+of\s+)?{_DAYS}\s+days?\b", _FLAGS
)
# "for two months from September 26", "from September 26 for six weeks"
_FOR_LENGTH_FROM = re.compile(
    rf"\bfor\s+(?:a\s+period\s+of\s+|the\s+next\s+)?{_LENGTH},?\s+"
    rf"(?:(?:starting|beginning|commencing)\s+)?from\s+{_date('a')}",
    _FLAGS,
)
_FROM_FOR_LENGTH = re.compile(
    rf"\bfrom\s+{_date('a')}\s+for\s+(?:a\s+period\s+of\s+)?{_LENGTH}\b", _FLAGS
)
# "60-day traffic diversions … from Sept. 26" (within one sentence)
_N_DAY_FROM = re.compile(rf"\b{_DAYS}-day\b[^.!?]{{0,80}}?\bfrom\s+{_date('a')}", _FLAGS)
# "from July 1 to July 15", "between July 1 and July 15"
_FROM_TO = re.compile(
    rf"\b(?:from|between)\s+{_date('a')}\s+(?:to|till|until|and|through)\s+{_date('b')}", _FLAGS
)
# "from October 10 to 18", "between October 10 and 18": the second day in the
# first date's month. Not followed by a unit, so "from October 10 to 18 hours"
# and "to 18 days" are left alone.
_BARE_DAY = (
    r"(?P<bd>\d{1,2})(?:st|nd|rd|th)?"
    r"(?!\s*(?:[:.]\d|am\b|pm\b|hours?\b|hrs\b|days?\b|weeks?\b|months?\b|years?\b|%|,?\s*\d{4}))"
)
_FROM_TO_SAME_MONTH = re.compile(
    rf"\b(?:from|between)\s+{_date('a')}\s+(?:to|till|until|and|through)\s+{_BARE_DAY}\b", _FLAGS
)
# "October 10-18", "Oct 10 to 18, 2026"
_MONTH_DAY_RANGE = re.compile(
    rf"\b(?P<am>{_MONTH})\s+(?P<ad>{_DAY})\s*(?:-|\u2013|\u2014|to)\s*{_BARE_DAY}\b(?:,?\s+(?P<ay>\d{{4}}))?",
    _FLAGS,
)
# "till October 18", "until 18 October 2026", "up to October 18": an end with no start.
_TILL = re.compile(rf"\b(?:till|until|upto|up\s+to)\s+{_date('a')}", _FLAGS)
# "on October 2": one day.
_ON = re.compile(rf"\bon\s+{_date('a')}", _FLAGS)
# "from September 26"
_FROM = re.compile(rf"\bfrom\s+{_date('a')}", _FLAGS)


@dataclass(frozen=True)
class StatedPeriod:
    # None when the article gives an end ("till October 18") but no start.
    start: datetime | None
    # None when the article gives a start but no length or end.
    end: datetime | None
    # The article's words the period was read from.
    text: str
    found_in: str


def _group(match: re.Match[str], name: str) -> str | None:
    return match.group(name) if name in match.groupdict() else None


def _resolve_date(match: re.Match[str], group: str, published: date) -> date | None:
    month_text = _group(match, f"{group}m") or _group(match, f"{group}m2")
    day_text = _group(match, f"{group}d") or _group(match, f"{group}d2")
    if not (month_text and day_text):
        return None
    month = _MONTHS[month_text[:3].lower()]
    day = int(re.sub(r"\D", "", day_text))
    year_text = _group(match, f"{group}y")
    years = [int(year_text)] if year_text else [published.year - 1, published.year, published.year + 1]
    candidates = []
    for year in years:
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs((candidate - published).days))


def _add_months(start: date, months: int) -> date:
    """The same day `months` later, or the last day of that month if it has no such day."""
    years, month = divmod(start.month - 1 + months, 12)
    year = start.year + years
    for day in range(start.day, 0, -1):
        try:
            return date(year, month + 1, day)
        except ValueError:
            continue
    raise ValueError(start)


def _same_month_end(start: date, day: int) -> date | None:
    """"From October 10 to 18": the 18th of October; "from October 30 to 2": 2 November."""
    for month_offset in (0, 1):
        years, month = divmod(start.month - 1 + month_offset, 12)
        try:
            end = date(start.year + years, month + 1, day)
        except ValueError:
            continue
        if end >= start:
            return end
    return None


def _period(
    match: re.Match[str],
    found_in: str,
    published: date,
    *,
    reads: str = "start",
    zone: tzinfo = IST,
) -> StatedPeriod | None:
    """The period a match states.

    `reads` says what the date in group "a" is: the "start" (with an end from
    a length, a second date or a bare day in the same month, if given), the
    "end" alone, or "one_day" for a single stated day.
    """
    stated = _resolve_date(match, "a", published)
    if stated is None or abs((stated - published).days) > MAX_DAYS_FROM_PUBLICATION:
        return None
    text = " ".join(match.group().split())
    if reads == "end":
        return StatedPeriod(start=None, end=end_of_day(stated, zone), text=text, found_in=found_in)
    if reads == "one_day":
        return StatedPeriod(
            start=start_of_day(stated, zone),
            end=end_of_day(stated, zone),
            text=text,
            found_in=found_in,
        )
    start = stated
    groups = match.groupdict()
    end: date | None = None
    if groups.get("n"):
        days = int(groups["n"])
        if not 1 <= days <= MAX_DAYS:
            return None
        # "For 60 days from September 26": the 26th is the first of the 60.
        end = start + timedelta(days=days - 1)
    elif groups.get("len"):
        count = _WORD_NUMBERS.get(groups["len"].lower()) or int(groups["len"])
        if groups["unit"].lower().startswith("week"):
            end = start + timedelta(weeks=count) - timedelta(days=1)
        else:
            # "For two months from September 26": 26 September to 25 November.
            end = _add_months(start, count) - timedelta(days=1)
        if not 1 <= (end - start).days + 1 <= MAX_DAYS:
            return None
    elif "bm" in groups:
        end = _resolve_date(match, "b", start)
        if end is None or not start <= end <= start + timedelta(days=MAX_DAYS):
            return None
    elif groups.get("bd"):
        end = _same_month_end(start, int(groups["bd"]))
        if end is None:
            return None
    return StatedPeriod(
        start=start_of_day(start, zone),
        end=end_of_day(end, zone) if end else None,
        text=text,
        found_in=found_in,
    )


def find_stated_period(
    *,
    title: str | None,
    summary: str | None = None,
    body: str | None = None,
    published_at: datetime | None,
    zone: tzinfo = IST,
) -> StatedPeriod | None:
    """The period the article states, or None when it states none explicitly.

    Wording that gives both a start and an end is preferred wherever it
    appears. A bare "from <date>", "till <date>" or "on <date>" counts only in
    the headline or summary: in a body it too often belongs to something other
    than the road measure.
    """
    if published_at is None:
        return None
    published = published_at.astimezone(zone).date()
    fields = [("title", title), ("summary", summary), ("body", body)]

    complete = (
        _FOR_DAYS_FROM,
        _FROM_FOR_DAYS,
        _FOR_LENGTH_FROM,
        _FROM_FOR_LENGTH,
        _N_DAY_FROM,
        _FROM_TO,
        _FROM_TO_SAME_MONTH,
        _MONTH_DAY_RANGE,
    )
    searches = [
        (tuple((pattern, "start") for pattern in complete), fields),
        (((_FROM, "start"), (_TILL, "end"), (_ON, "one_day")), fields[:2]),
    ]
    for patterns, where in searches:
        for found_in, text in where:
            for pattern, reads in patterns:
                for match in pattern.finditer(text or ""):
                    period = _period(match, found_in, published, reads=reads, zone=zone)
                    if period:
                        return period
    return None
