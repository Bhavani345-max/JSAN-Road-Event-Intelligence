"""How long the road blocks a structured source states are, and the length rule.

The brief of 8 October 2026 (section 8) is explicit: a real event is never
filtered out because the affected road is short; a source-provided distance
always wins, and 20 m is kept as 20 m. So the minimum is OFF: the constant
is 0. (Decision 0016 of 7 October set a 200 m minimum; decision 0018
withdraws it.) The measurement itself stays: the length of the closed
stretches a source draws is recorded on the event, for the reviewer, never
used to drop it.

The length is the source's own: the closed stretches it draws as lines. A
closure the source gives no line for (a point, an area) cannot be measured;
nothing is estimated.
"""

from packages.geo_models import line_length_m

from .record import SourceEvent

# 0 = no minimum. Any value above 0 would make road blocks drawn shorter than
# it not events; the brief of 8 October 2026 forbids that.
MIN_ROAD_BLOCK_LENGTH_M = 0

# Event types that are a public event; never subject to a minimum, even if one is set.
PUBLIC_EVENT_TYPES = frozenset(
    {"SPECIAL_EVENT", "PUBLIC_PROCESSION", "MARATHON", "SPORTING_EVENT", "VIP_MOVEMENT"}
)

# How sources say a stretch is closed to traffic: Toronto "ROAD_CLOSED", TfL "Closed".
_CLOSED = frozenset({"road_closed", "closed"})


def road_block_length_m(event: SourceEvent) -> float | None:
    """Total length of the closed stretches the source draws; None if it draws none."""
    lengths = [
        length
        for location in event.locations
        if (location.closure or "").strip().lower() in _CLOSED
        and (length := line_length_m(location.geometry)) is not None
    ]
    return sum(lengths) if lengths else None


def source_length_m(event: SourceEvent | None) -> float | None:
    """What the source's own geometry measures: its line, else its closed stretches."""
    if event is None:
        return None
    length = line_length_m(event.geometry)
    return length if length is not None else road_block_length_m(event)


def is_public_event(event: SourceEvent) -> bool:
    return event.event_type in PUBLIC_EVENT_TYPES


def too_short_road_block(event: SourceEvent | None) -> float | None:
    """The measured length when this is a road block under the minimum, else None.

    With the minimum at 0 this is always None: nothing is dropped for length.
    """
    if event is None or is_public_event(event) or MIN_ROAD_BLOCK_LENGTH_M <= 0:
        return None
    length = road_block_length_m(event)
    return length if length is not None and length < MIN_ROAD_BLOCK_LENGTH_M else None
