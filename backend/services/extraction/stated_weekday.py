"""Checks a model's dates against the weekday the article names.

A language model counting days from the publication date sometimes lands on
the wrong weekday: "diversions on Monday" in an article published on Monday
2 November came back as Tuesday 3 November, "on Friday night" in Saturday's
paper as Sunday. The weekday is the article's own word, so it wins over the
model's arithmetic:

- The weekday is read from the period's words ("on Friday night", "from
  Monday to Thursday", "until Thursday evening"). When those words are only
  clock times ("between 1 pm and 7 pm"), from the sentence they stand in or
  the one before it ("restrictions on Monday ... between 1 pm and 7 pm"), and
  then from the headline, but only when that text names a single weekday.
- Words that also state a calendar date ("on Sunday, October 11"), or "today",
  "tonight", "tomorrow" or "yesterday", are left alone: those words govern.
- A date already on the named weekday is never moved. A wrong one is moved to
  the named weekday nearest the publication day: the publication day itself
  when it is that weekday; "next" and "last" are honoured; otherwise the
  occurrence just before or just after the publication day, whichever is
  nearer the model's date (the model reads the tense; it miscounts the days).
  A one-day period moves as a whole.
- When the publication day is not the publisher's own (a search engine's
  "3 days ago"), no day can be counted from it: the wrong dates are removed.

Every change is described in a note kept with the reading.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_DAY_NAMES = tuple(day.capitalize() for day in WEEKDAYS)
_MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_FLAGS = re.IGNORECASE
# "until Thursday", "till Sunday", "through Tuesday": the weekday ends the period.
_END_WORDS = r"until|till|til|through|thru|upto|up\s+to|ending|ends"
_QUALIFIERS = r"this\s+coming|this|next|last|coming|previous|past"
_MENTION = re.compile(
    rf"\b(?:(?P<end>{_END_WORDS}|to)\s+)?(?:(?P<qual>{_QUALIFIERS})\s+)?"
    rf"(?P<day>{'|'.join(WEEKDAYS)})\b",
    _FLAGS,
)
_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
# "October 11", "11 October", "11th of Oct", "11/10/2026", "2026-10-11".
_CALENDAR = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\b"
    rf"|{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b"
    r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\d{1,2}-\d{1,2}-\d{2,4}\b"
    r"|\d{1,2}\.\d{1,2}\.\d{2,4}\b|\d{4}-\d{2}-\d{2}\b)",
    _FLAGS,
)
_OTHER_DAY_WORDS = re.compile(r"\b(?:today|tonight|tomorrow|yesterday)\b", _FLAGS)
_CLOCK_TIME = re.compile(
    r"\b\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.?|p\.m\.?)(?![a-z])"
    r"|\b\d{1,2}:\d{2}\b|\bnoon\b|\bmidnight\b",
    _FLAGS,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_START, _END = "start", "end"


@dataclass(frozen=True)
class WeekdayCheck:
    """The dates after the check, and what was changed (None when nothing was)."""

    start: datetime | None
    end: datetime | None
    note: str | None = None
    # True when the dates were removed rather than moved.
    removed: bool = False


@dataclass(frozen=True)
class _Mention:
    weekday: int
    role: str
    qualifier: str | None
    words: str
    # Where the weekday was read: "words" (the period's own), "nearby" or "headline".
    found: str = "words"


def check_stated_weekdays(
    *,
    words: str,
    start: datetime | None,
    end: datetime | None,
    published_at: datetime | None,
    zone: tzinfo,
    publication_day_known: bool,
    context: Sequence[str | None] = (),
) -> WeekdayCheck:
    """The model's `start`/`end` for the period `words`, checked against the weekday they name.

    `context` is the article's headline, summary and body, in that order: the
    weekday is looked for there only when `words` are clock times alone.
    """
    unchanged = WeekdayCheck(start=start, end=end)
    if start is None and end is None:
        return unchanged
    mentions = _mentions_in_words(words)
    if mentions is None:
        return unchanged
    if not mentions:
        mention = _mention_around(words, start, end, zone, context)
        if mention is None:
            return unchanged
        mentions = [mention]

    days = {
        _START: start.astimezone(zone).date() if start else None,
        _END: end.astimezone(zone).date() if end else None,
    }
    wrong = [
        mention
        for mention in mentions
        if days[mention.role] is not None and days[mention.role].weekday() != mention.weekday
    ]
    if not wrong:
        return unchanged
    first = wrong[0]
    weekday = _DAY_NAMES[first.weekday]
    where = {
        "words": "",
        "nearby": f" (the article names {weekday} beside these words)",
        "headline": f" (the headline names {weekday})",
    }[first.found]
    said = f"The model dated “{words}” {_day(days[first.role])}, which is not a {weekday}{where}"
    if published_at is None or not publication_day_known:
        return WeekdayCheck(
            start=None,
            end=None,
            note=f"{said}; the publication day is not known, so these dates are not kept",
            removed=True,
        )

    published = published_at.astimezone(zone).date()
    new_days = dict(days)
    for mention in wrong:
        new_days[mention.role] = _named_day(mention, published, days[mention.role])
    roles = {mention.role for mention in mentions}
    one_day = days[_START] is not None and days[_START] == days[_END]
    if one_day and roles == {_START}:
        new_days[_END] = new_days[_START]
    elif one_day and roles == {_END}:
        new_days[_START] = new_days[_END]

    new_start = _moved(start, new_days[_START], zone)
    new_end = _moved(end, new_days[_END], zone)
    if new_start and new_end and new_end < new_start:
        return WeekdayCheck(
            start=None,
            end=None,
            note=f"{said}; on that weekday the period would end before it starts, "
            "so these dates are not kept",
            removed=True,
        )
    moved_to = new_days[first.role]
    return WeekdayCheck(
        start=new_start,
        end=new_end,
        note=f"{said}; {_day(moved_to)} is used instead, "
        f"counted from the publication day {_day(published)}",
    )


def _mentions_in_words(words: str) -> list[_Mention] | None:
    """The weekdays the period's words name, with the date each one sets; None when
    the words must be left alone (a calendar date, another day word, or too many days)."""
    if _CALENDAR.search(words) or _OTHER_DAY_WORDS.search(words):
        return None
    found = list(_MENTION.finditer(words))
    if len(found) > 2:
        return None
    mentions: list[_Mention] = []
    for index, match in enumerate(found):
        end_word = match.group("end")
        # "to" ends a period only after a first weekday ("from Monday to Thursday").
        ends = bool(end_word) and (end_word.lower() != "to" or index > 0)
        if index == 1 and not ends and mentions and mentions[0].role == _START:
            ends = True  # "on Saturday and Sunday"
        role = _END if ends else _START
        if any(mention.role == role for mention in mentions):
            return None
        mentions.append(
            _Mention(
                weekday=WEEKDAYS.index(match.group("day").lower()),
                role=role,
                qualifier=_qualifier(match),
                words=" ".join(match.group().split()),
            )
        )
    return mentions


def _mention_around(
    words: str,
    start: datetime | None,
    end: datetime | None,
    zone: tzinfo,
    context: Sequence[str | None],
) -> _Mention | None:
    """The one weekday the text around clock-time words names, for a one-day period."""
    if not _CLOCK_TIME.search(words):
        return None
    if start is None:
        return None
    if end is not None and end.astimezone(zone).date() != start.astimezone(zone).date():
        return None
    texts = [text for text in context if text]
    nearby = _sentences_around(words, texts)
    headline = context[0] if context else None
    for found, text in (("nearby", nearby), ("headline", headline)):
        if not text:
            continue
        if _CALENDAR.search(text) or _OTHER_DAY_WORDS.search(text):
            return None
        matches = list(_MENTION.finditer(text))
        named = {match.group("day").lower() for match in matches}
        if len(named) > 1:
            return None
        if named:
            match = matches[0]
            return _Mention(
                weekday=WEEKDAYS.index(match.group("day").lower()),
                role=_START,
                qualifier=_qualifier(match),
                words=" ".join(match.group().split()),
                found=found,
            )
    return None


def _sentences_around(words: str, texts: Sequence[str]) -> str | None:
    """The sentence holding `words` and the one before it, from the first text that has them."""
    parts = re.findall(r"\w+", words)
    if not parts:
        return None
    pattern = re.compile(r"\W+".join(re.escape(part) for part in parts), _FLAGS)
    for text in texts:
        match = pattern.search(text)
        if match is None:
            continue
        sentences: list[tuple[int, int]] = []
        position = 0
        for gap in _SENTENCE_BREAK.finditer(text):
            sentences.append((position, gap.start()))
            position = gap.end()
        sentences.append((position, len(text)))
        index = next(i for i, (_, stop) in enumerate(sentences) if match.start() <= stop)
        begin = sentences[max(index - 1, 0)][0]
        return text[begin : sentences[index][1]]
    return None


def _qualifier(match: re.Match[str]) -> str | None:
    """'next', 'last', 'this coming' ... before the weekday, in lower case."""
    qualifier = match.group("qual")
    return " ".join(qualifier.lower().split()) if qualifier else None


def _named_day(mention: _Mention, published: date, model_day: date) -> date:
    """The `mention`'s weekday nearest the publication day, as described above."""
    back = (published.weekday() - mention.weekday) % 7
    ahead = (mention.weekday - published.weekday()) % 7
    if mention.qualifier in ("next", "coming", "this coming"):
        return published + timedelta(days=ahead or 7)
    if mention.qualifier in ("last", "previous", "past"):
        return published - timedelta(days=back or 7)
    if back == 0:
        return published
    before, after = published - timedelta(days=back), published + timedelta(days=ahead)
    return min((before, after), key=lambda day: abs((day - model_day).days))


def _moved(value: datetime | None, day: date | None, zone: tzinfo) -> datetime | None:
    """`value` on `day`, at the same time of day in the city's zone."""
    if value is None or day is None:
        return value
    local = value.astimezone(zone)
    if local.date() == day:
        return value
    return datetime.combine(day, local.time(), tzinfo=zone)


def _day(day: date) -> str:
    return f"{_DAY_NAMES[day.weekday()]} {day.day} {_MONTH_NAMES[day.month - 1]} {day.year}"
