"""Conservative matching of events that may describe the same real-world event.

Two events are compared on what each states: type, named places and roads,
position, stated period, direction, when they were reported, headline
wording, and who reported them. The answer is one of:

- SAME: clearly the same event. Today that means the same article reported
  twice (an identical headline or link), or two reports that state the same
  type, the same full period and a shared place.
- POSSIBLE: they share a place, a road or a position and are close in time,
  but that is not enough to be sure. A reviewer decides.
- DIFFERENT: no evidence they are the same, or evidence they are not
  (different types, periods that do not overlap, different junctions,
  positions far apart, two records of one official source).

Where both state a value and the values differ (start, end, direction,
position, type, status), it is a conflict: kept, never resolved here.

A SAME match may be merged automatically only if nothing conflicts, neither
event has been touched by a reviewer, and both come from sources of the same
standing (never an official source and a news report). Everything else is a
candidate for review.

No machine learning and no fuzzy scores: every reason is a stated fact a
reviewer can check.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from packages.common.time import ensure_utc

# Reports this far apart in time, with no stated periods, are not compared.
REPORT_WINDOW = timedelta(days=14)
# Stated periods may differ by this much at either end and still overlap.
PERIOD_SLACK = timedelta(days=1)
# Positions closer than this are the same spot; further than FAR, different places.
SAME_SPOT_KM = 0.3
NEARBY_KM = 1.0
FAR_KM = 2.0
# Headline word overlap (Jaccard) that, with a shared place, makes a possible match.
SIMILAR_HEADLINES = 0.15

_STOPWORDS = frozenset(
    """a an the of to in on at for and or as by with from is are be been being has have
    had was were will would may can why what how who which this that these those it its
    their after before over under into near amid about new now today says said hyderabad
    secunderabad cyberabad london toronto city traffic road roads""".split()
)
_WORD = re.compile(r"[a-z0-9]+")
_DATELINE = re.compile(r"^\s*[a-z][a-z .'-]{1,30}:\s*", re.IGNORECASE)


class MatchClass(StrEnum):
    SAME = "SAME"
    POSSIBLE = "POSSIBLE"
    DIFFERENT = "DIFFERENT"


@dataclass(frozen=True)
class EventFacts:
    """What matching knows about one event. Built from the stored event."""

    event_id: str
    source_id: str
    # REI tier of the source: 1 official … 4 discovery; None when not assigned.
    source_tier: int | None
    official: bool
    title: str
    url: str | None
    event_type: str | None
    start: datetime | None
    end: datetime | None
    direction: str | None
    # A representative position (longitude, latitude), if located.
    position: tuple[float, float] | None
    # Whether the position is only a named place's (approximate).
    approximate: bool
    # Kind of the place the event is located by (junction, area, …).
    place_kind: str | None
    place_name: str | None
    # Normalised names of every place and road the event states.
    places: frozenset[str] = frozenset()
    roads: frozenset[str] = frozenset()
    reported_at: datetime | None = None
    # A reviewer has acted on it (any decision, extension, correction).
    reviewed: bool = False
    source_status: str | None = None
    city: str | None = None


@dataclass(frozen=True)
class Match:
    classification: MatchClass
    reasons: tuple[str, ...] = ()
    # [{"field": …, "a": …, "b": …}]
    conflicts: tuple[dict, ...] = ()
    auto_merge: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


def normalise(text: str | None) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def headline_key(title: str) -> str:
    """A headline without its dateline ("Hyderabad: …") and punctuation."""
    return normalise(_DATELINE.sub("", title or ""))


def headline_words(title: str) -> frozenset[str]:
    words = set()
    for word in _WORD.findall(headline_key(title)):
        if word in _STOPWORDS or len(word) < 2:
            continue
        # Plurals: "flyovers" and "flyover" are one word here.
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        words.add(word)
    return frozenset(words)


def headline_similarity(a: str, b: str) -> float:
    wa, wb = headline_words(a), headline_words(b)
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lon1, lat1), (lon2, lat2) = a, b
    lat = math.radians((lat1 + lat2) / 2)
    dx = (lon1 - lon2) * 111.32 * math.cos(lat)
    dy = (lat1 - lat2) * 110.57
    return math.hypot(dx, dy)


def _utc(value: datetime | None) -> datetime | None:
    return ensure_utc(value) if value else None


def _periods_overlap(a: EventFacts, b: EventFacts) -> bool | None:
    """Whether stated periods overlap; None when either states no period.

    An open end (no stated end) runs on; an open start ran from before.
    """
    if not (a.start or a.end) or not (b.start or b.end):
        return None
    starts = [time for time in (_utc(a.start), _utc(b.start)) if time]
    ends = [time for time in (_utc(a.end), _utc(b.end)) if time]
    if not starts or not ends:
        return True
    return max(starts) <= min(ends) + PERIOD_SLACK


def _reported_close(a: EventFacts, b: EventFacts) -> bool:
    if a.reported_at is None or b.reported_at is None:
        return True
    return abs(_utc(a.reported_at) - _utc(b.reported_at)) <= REPORT_WINDOW


def compare(a: EventFacts, b: EventFacts) -> Match:
    """Whether two events describe the same real-world event (see the module notes)."""
    if a.event_id == b.event_id:
        return Match(MatchClass.DIFFERENT, ("the same event",))
    if a.city and b.city and a.city != b.city:
        return Match(MatchClass.DIFFERENT, ("different cities",))
    if a.source_id == b.source_id and a.official and b.official:
        # An authority's separate records are separate events.
        return Match(MatchClass.DIFFERENT, ("separate records of one official source",))

    same_article = headline_key(a.title) == headline_key(b.title) and bool(headline_key(a.title))
    if a.url and b.url and a.url == b.url:
        same_article = True

    overlap = _periods_overlap(a, b)
    if overlap is False:
        return Match(MatchClass.DIFFERENT, ("stated periods do not overlap",))
    if overlap is None and not _reported_close(a, b):
        return Match(MatchClass.DIFFERENT, ("reported more than two weeks apart",))

    reasons: list[str] = []
    conflicts: list[dict] = []

    def conflict(name: str, va, vb) -> None:
        conflicts.append({"field": name, "a": va, "b": vb})

    if a.event_type and b.event_type and a.event_type != b.event_type:
        if not same_article:
            return Match(MatchClass.DIFFERENT, (f"different types ({a.event_type}, {b.event_type})",))
        conflict("event_type", a.event_type, b.event_type)

    distance = distance_km(a.position, b.position) if a.position and b.position else None
    shared_places = sorted(a.places & b.places)
    shared_roads = sorted(a.roads & b.roads)
    # Two named-place positions on the same named road or place can be far
    # apart and still be one event (a highway's works): only precise
    # positions far apart prove different events.
    approximate_but_linked = (a.approximate or b.approximate) and bool(shared_places or shared_roads)
    if distance is not None and distance > FAR_KM and not same_article and not approximate_but_linked:
        return Match(MatchClass.DIFFERENT, (f"positions {distance:.1f} km apart",))
    if (
        a.place_kind == "junction"
        and b.place_kind == "junction"
        and a.place_name
        and b.place_name
        and normalise(a.place_name) != normalise(b.place_name)
        and not same_article
    ):
        return Match(MatchClass.DIFFERENT, (f"different junctions ({a.place_name}, {b.place_name})",))

    # Values both state that differ: kept as conflicts.
    for name, va, vb in (("start_time", a.start, b.start), ("end_time", a.end, b.end)):
        if va and vb and abs(_utc(va) - _utc(vb)) > timedelta(hours=1):
            conflict(name, _utc(va).isoformat(), _utc(vb).isoformat())
    if a.direction and b.direction and a.direction != b.direction:
        conflict("direction", a.direction, b.direction)
    if a.source_status and b.source_status and a.official and b.official and a.source_status != b.source_status:
        conflict("source_status", a.source_status, b.source_status)
    if distance is not None and distance > SAME_SPOT_KM and not (a.approximate and b.approximate):
        conflict("geometry", list(a.position), list(b.position))
    elif distance is not None and distance > FAR_KM:
        conflict("geometry", list(a.position), list(b.position))

    similarity = headline_similarity(a.title, b.title)
    same_period = bool(
        a.start and b.start and a.end and b.end
        and abs(_utc(a.start) - _utc(b.start)) <= timedelta(hours=1)
        and abs(_utc(a.end) - _utc(b.end)) <= timedelta(hours=1)
    )  # fmt: skip
    same_start = bool(a.start and b.start and abs(_utc(a.start) - _utc(b.start)) <= timedelta(hours=1))

    if same_article:
        reasons.append("the same article (identical headline or link)")
    if shared_places:
        reasons.append("both name " + ", ".join(shared_places))
    if shared_roads:
        reasons.append("both name the road " + ", ".join(shared_roads))
    if distance is not None and distance <= NEARBY_KM:
        reasons.append(f"positions {distance * 1000:.0f} m apart")
    if same_period:
        reasons.append("the same stated period")
    elif same_start:
        reasons.append("the same stated start")
    if a.event_type and a.event_type == b.event_type:
        reasons.append(f"the same type ({a.event_type})")
    if similarity >= SIMILAR_HEADLINES and not same_article:
        reasons.append(f"similar headlines ({similarity:.0%} of words shared)")

    located_together = bool(shared_places or shared_roads) or (
        distance is not None and distance <= SAME_SPOT_KM
    )
    if distance is not None and distance > FAR_KM and not same_article:
        reasons.append(f"named-place positions {distance:.1f} km apart")
    if same_article:
        classification = MatchClass.SAME
    elif located_together and same_period and a.event_type and a.event_type == b.event_type:
        classification = MatchClass.SAME
    elif located_together and (
        similarity >= SIMILAR_HEADLINES
        or same_start
        or (a.event_type is not None and a.event_type == b.event_type)
    ):
        classification = MatchClass.POSSIBLE
    else:
        return Match(MatchClass.DIFFERENT, tuple(reasons) or ("nothing in common",))

    notes: list[str] = []
    if a.official != b.official:
        notes.append("an official source and a news report: never merged without review")
    if a.reviewed or b.reviewed:
        notes.append("a reviewer has acted on one of them: merged only by a reviewer")
    if conflicts:
        notes.append("the sources disagree: merged only by a reviewer")
    auto = (
        classification is MatchClass.SAME
        and not conflicts
        and not a.reviewed
        and not b.reviewed
        and a.official == b.official
    )
    return Match(classification, tuple(reasons), tuple(conflicts), auto, tuple(notes))
