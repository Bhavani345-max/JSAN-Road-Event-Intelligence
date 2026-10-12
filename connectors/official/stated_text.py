"""What an official notice states in words: dates written as day/month/year,
and a distance. Only explicit wording is read, and the words are kept.

Indian authorities write dates as 05/10/2026 or 05-10-2026, sometimes in
Devanagari digits (०५/१०/२०२६). Nothing is estimated: a notice that gives no
date gets none.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, tzinfo

from packages.common.time import IST, end_of_day, start_of_day

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_DMY = r"(?P<{g}d>\d{{1,2}})[/.-](?P<{g}m>\d{{1,2}})[/.-](?P<{g}y>\d{{4}})"
_FLAGS = re.IGNORECASE
# "from 14/09/2026 to 25/09/2026", "between 14/09/2026 and 25/09/2026"
_FROM_TO = re.compile(
    rf"\b(?:from|between|w\.?e\.?f\.?)\s*{_DMY.format(g='a')}\s*(?:to|till|until|upto|up to|and|-|–)\s*{_DMY.format(g='b')}",
    _FLAGS,
)
# "until 31/05/2027", "till 31/05/2027", "upto 31/05/2027", "valid till 31/05/2027"
_TILL = re.compile(rf"\b(?:till|until|upto|up\s+to)\s*{_DMY.format(g='a')}", _FLAGS)
# "on 04/10/2026": one day.
_ON = re.compile(rf"\bon\s*{_DMY.format(g='a')}", _FLAGS)
# "from 01/07/2026", "w.e.f. 01/07/2026": a start with no end.
_FROM = re.compile(rf"\b(?:from|w\.?e\.?f\.?)\s*{_DMY.format(g='a')}", _FLAGS)

# "100 meter", "2.56 km", "(100 मीटर)": a distance in the source's words.
_DISTANCE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:-\s*)?(?:m|mtrs?|meters?|metres?|kms?|kilomet(?:er|re)s?|मीटर|मी\.|कि\.?मी\.?)\b",
    _FLAGS,
)


@dataclass(frozen=True)
class StatedDates:
    start: datetime | None
    end: datetime | None
    # The notice's words the dates were read from.
    text: str


def ascii_digits(text: str) -> str:
    return text.translate(_DEVANAGARI_DIGITS)


def parse_dmy(value: str | None) -> date | None:
    """05/10/2026 or 05-10-2026 as a date; None if it is not one."""
    if not value:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*", ascii_digits(value))
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _date_of(match: re.Match[str], group: str) -> date | None:
    try:
        return date(
            int(match.group(f"{group}y")), int(match.group(f"{group}m")), int(match.group(f"{group}d"))
        )
    except ValueError:
        return None


def stated_dates(*texts: str | None, zone: tzinfo = IST) -> StatedDates | None:
    """The period a notice states in day/month/year dates, whole days in `zone`.

    The first explicit statement found wins, in this order: a from-to range,
    an end alone ("until 31/05/2027"), one day ("on 04/10/2026"), a start
    alone ("from 01/07/2026"). None when the text states no date.
    """
    for text in texts:
        if not text:
            continue
        text = ascii_digits(text)
        match = _FROM_TO.search(text)
        if match:
            start, end = _date_of(match, "a"), _date_of(match, "b")
            if start and end and end >= start:
                return StatedDates(start_of_day(start, zone), end_of_day(end, zone), _words(match))
        match = _TILL.search(text)
        if match and (end := _date_of(match, "a")):
            return StatedDates(None, end_of_day(end, zone), _words(match))
        match = _ON.search(text)
        if match and (day := _date_of(match, "a")):
            return StatedDates(start_of_day(day, zone), end_of_day(day, zone), _words(match))
        match = _FROM.search(text)
        if match and (start := _date_of(match, "a")):
            return StatedDates(start_of_day(start, zone), None, _words(match))
    return None


_UNIT_METRES = (
    (("km", "kms", "kilometer", "kilometers", "kilometre", "kilometres", "कि.मी.", "कि.मी", "किमी"), 1000.0),
    (("m", "mtr", "mtrs", "meter", "meters", "metre", "metres", "मीटर", "मी."), 1.0),
)


def distance_in_metres(stated: str | None) -> float | None:
    """A stated distance ("100 meter", "2.56-km") in metres; None when it cannot be read.

    The source's words stay the record; this is the same number in one unit.
    """
    if not stated:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*-?\s*(\S+)", ascii_digits(stated))
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2).lower().rstrip(".") + ("." if match.group(2).endswith(".") else "")
    for units, factor in _UNIT_METRES:
        if unit in units or unit.rstrip(".") in units:
            return value * factor
    return None


def stated_distance(*texts: str | None) -> str | None:
    """The first distance a notice states, verbatim ("100 meter"); None if none."""
    for text in texts:
        if text and (match := _DISTANCE.search(text)):
            return _words(match)
    return None


def _words(match: re.Match[str]) -> str:
    return " ".join(match.group().split())
