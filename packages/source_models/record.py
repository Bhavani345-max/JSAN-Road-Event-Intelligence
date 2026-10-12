from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SourceLocation(BaseModel):
    """A place a source states an event affects, with its geometry if the source gives one."""

    name: str
    kind: str | None = None
    # GeoJSON, as the source publishes it (validated when the event is built).
    geometry: dict[str, Any] | None = None
    direction: str | None = None
    closure: str | None = None
    reference: str | None = None
    # A place the source gives only indirectly (the file name of its PDF, a
    # division), used to place the event only when nothing else does, and
    # listed as an affected location only when it is a known place.
    fallback: bool = False


class SourceEvent(BaseModel):
    """What a structured source (an official feed) states about one event.

    Filled in by the connector from the source's own fields only; anything the
    source does not state stays None. When present, the event is built from
    these fields rather than detected from text.
    """

    event_type: str | None = None
    # The source's own category words, e.g. "Works / Utility works".
    category: str | None = None
    severity: str | None = None
    status: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    # The event's geometry as the source publishes it (GeoJSON).
    geometry: dict[str, Any] | None = None
    locations: list[SourceLocation] = []
    affected_road: str | None = None
    # An EventDirection value, only when the source states one direction for
    # the whole event; per-street directions stay on the locations.
    direction: str | None = None
    # The attribution the source's licence requires.
    attribution: str | None = None
    # The source itself reports the event cleared, cancelled or ended.
    reported_ended: bool = False
    # The source's own words that start/end were read from, when they were
    # read from text rather than taken from date fields ("until 31/05/2027").
    stated_period: str | None = None
    # A distance the source states, kept verbatim ("100 meter", "2.56 km").
    # Never measured or estimated by REI.
    stated_distance: str | None = None
    # The same distance in metres (the unit read from the words), for filters.
    stated_distance_m: float | None = None
    # The source publishes records for its own city only (a city traffic
    # police's notices), so a record that carries no geometry and names no
    # place is still the city's. Its location stays unresolved.
    covers_city: bool = False


class RawSourceRecord(BaseModel):
    """One item acquired from a source, before any interpretation.

    This is the evidence that is persisted as a source artifact. `raw` holds the
    item as the connector received it, so that extraction can later be re-run
    and audited against the original.
    """

    source_id: str
    # Stable identifier of the item within its source (feed GUID, URL, …).
    external_id: str
    url: str | None
    title: str
    summary: str | None
    # Plain text of the full item body, when the source provides one.
    content_text: str | None
    categories: list[str]
    published_at: datetime | None
    retrieved_at: datetime
    raw: dict[str, Any]
    # SHA-256 of the item's content; changes when the publisher edits it.
    content_hash: str
    # Set by connectors for structured sources (official feeds). Also kept in
    # `raw["source_event"]`, so stored evidence can be re-read later.
    structured: SourceEvent | None = None
