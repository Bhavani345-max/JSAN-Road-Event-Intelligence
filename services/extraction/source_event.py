"""Events that a structured source states itself (official feeds and listings).

An official feed such as Transport for London's road disruptions says what
the event is, where (with its own geometry), when, and how severe, in fields.
Nothing needs to be detected from text, so the event is built from those
fields, as the connector put them in `RawSourceRecord.structured`.

An official listing without geometry (the Mumbai Traffic Police's
notifications, the Bengaluru Traffic Police's events list) states the event in
words: the type, the dates, and the roads or places by name. Such an event is
located the way an article is (decision 0006): by a place it names, at that
place's position on OpenStreetMap, recorded as APPROXIMATE and never presented
as the event's exact location. A notice that names no known place is kept with
its location unresolved, for a reviewer to place.

The rules are the same as for any other event:

- only what the source states is filled in; its own words are kept;
- the source's geometry is preserved as it is, recorded as SOURCE_PROVIDED,
  and never replaced by a place looked up by name;
- REI's severity and confidence stay empty: the source's severity is kept in
  its own words, not translated;
- an event whose position lies outside the city's area is not that city's
  and is not created (the evidence is still stored);
- a road block the source draws shorter than 200 m is not an event, unless
  it is for a public event (packages/source_models/road_block.py);
- every event starts as VALIDATION_REQUIRED, however official the source.
"""

import logging
from datetime import datetime

from pydantic import TypeAdapter, ValidationError

from packages.cities import City
from packages.common.text import truncate
from packages.common.time import IST
from packages.event_schema import (
    SOURCE_PROVIDED,
    AffectedLocation,
    EventDetection,
    EventDirection,
    EventLocation,
    EventStatus,
    EventType,
    LocationClass,
    ReiEvent,
)
from packages.geo_models import Geometry, Point, positions_of
from packages.source_models import RawSourceRecord, source_length_m, too_short_road_block
from services.geo_resolution import PlaceMatch, PlaceResolver

from .event_factory import (
    MAX_DESCRIPTION_LENGTH,
    MAX_PLACES,
    affected_from_place,
    event_id_for,
    locate,
    location_from_place,
)
from .keyword_classifier import ArticleRelevance, ClassificationResult
from .road_mentions import find_road_mentions
from .stated_period import find_stated_period

logger = logging.getLogger(__name__)

DETECTION_METHOD = "source_provided"
CLASSIFIER_VERSION = "source-provided"
_GEOMETRY = TypeAdapter(Geometry)
# A place in the title or summary is what the notice is about (as for articles).
_LOCATING_FIELDS = ("title", "summary")


def _geometry(value: dict | None) -> Geometry | None:
    """The source's GeoJSON as a validated geometry; None if it is not valid GeoJSON."""
    if not value:
        return None
    try:
        return _GEOMETRY.validate_python(value)
    except ValidationError:
        logger.info("A source geometry is not valid GeoJSON and was left out: %s", str(value)[:120])
        return None


def _inside(geometry: Geometry, city: City) -> bool:
    return all(city.covers(latitude, longitude) for longitude, latitude in positions_of(geometry))


def _event_type(value: str | None) -> EventType | None:
    try:
        return EventType(value) if value else None
    except ValueError:
        return None


def classify_source_record(record: RawSourceRecord, city: City | None) -> ClassificationResult:
    """The 'classification' of a structured record: in or out of the city's area.

    A record is in scope when the geometry it states lies inside the city's
    area. One without any geometry is in scope only if its locations name
    places (they are kept unresolved), or if its source publishes for the
    city alone (`covers_city`), as a city's traffic police does.
    """
    structured = record.structured
    assert structured is not None
    geometry = _geometry(structured.geometry)
    in_area = city is not None and (
        (geometry is not None and _inside(geometry, city))
        or (
            geometry is None
            and (any(not place.fallback for place in structured.locations) or structured.covers_city)
        )
    )
    label = ArticleRelevance.SOURCE_PROVIDED_EVENT if in_area else ArticleRelevance.NOT_RELEVANT
    if in_area and too_short_road_block(structured) is not None:
        label = ArticleRelevance.BELOW_MINIMUM_LENGTH
    return ClassificationResult(
        label=label,
        score=0.0,
        matched_keywords=[],
        event_type=_event_type(structured.event_type),
        city=city.name if (city and in_area) else None,
        classifier_version=CLASSIFIER_VERSION,
    )


def _place_by_name(resolver: PlaceResolver | None, name: str) -> PlaceMatch | None:
    """The gazetteer place a source's location name points to, if it is one spot."""
    if resolver is None:
        return None
    exact = resolver.lookup(name, found_in="source")
    if exact is not None and exact.has_position:
        return exact
    # An address is read from its most exact part: "7th Main Road, Byrasandra,
    # Jayanagar" is placed at 7th Main Road if that is one known spot, else at
    # Byrasandra, and so on.
    for part in name.split(","):
        match = resolver.lookup(part, found_in="source") if part.strip() else None
        if match is not None and match.has_position:
            return match
    # Otherwise the first known place written anywhere in the text.
    return next(
        (
            match
            for match in resolver.find_in(name, "source", require_capital=False)
            if match.has_position
        ),
        None,
    )


def build_event_from_source(
    record: RawSourceRecord,
    classification: ClassificationResult,
    *,
    now: datetime,
    resolver: PlaceResolver | None = None,
    city: City | None = None,
) -> ReiEvent | None:
    """The canonical event a structured record states, or None outside the city's area.

    With the source's own geometry, the event is exactly where the source
    draws it. Without any, and with a place resolver, the event is put at the
    position of a known place the source names in its title, summary or
    location names (APPROXIMATE), as an article would be; otherwise its
    location is unresolved.
    """
    structured = record.structured
    if structured is None or not classification.is_relevant:
        return None
    geometry = _geometry(structured.geometry)

    # Places named in the text: only for a source that draws nothing itself.
    named: list[PlaceMatch] = []
    text_located: PlaceMatch | None = None
    text_within: PlaceMatch | None = None
    road_mentions: list[str] = []
    period = None
    if geometry is None:
        if resolver is not None:
            named = resolver.find_places(
                title=record.title, summary=record.summary, body=record.content_text
            )
            text_located, text_within = locate(named)
        road_mentions = find_road_mentions(record.title, record.summary)
        if structured.start is None and structured.end is None and not structured.stated_period:
            period = find_stated_period(
                title=record.title,
                summary=record.summary,
                body=record.content_text,
                published_at=record.published_at,
                zone=city.tz if city else IST,
            )

    # Where the event is put, in order: the source's own location fields (an
    # address, a road it names), then a place named in its title or summary,
    # then a place the source gives only indirectly (a PDF's file name).
    locations: list[AffectedLocation] = []
    source_located: PlaceMatch | None = None
    fallback_located: PlaceMatch | None = None
    for place in structured.locations:
        place_geometry = _geometry(place.geometry)
        match = _place_by_name(resolver, place.name) if place_geometry is None else None
        if match is not None:
            locations.append(
                AffectedLocation(
                    name=place.name,
                    kind=place.kind or match.kind,
                    resolution=LocationClass.APPROXIMATE,
                    geometry=Point(type="Point", coordinates=(match.longitude, match.latitude)),
                    direction=place.direction,
                    closure=place.closure,
                    mention=place.name,
                    found_in="source",
                    reference=f"OpenStreetMap {match.osm_ref}",
                )
            )
            if place.fallback:
                fallback_located = fallback_located or match
            else:
                source_located = source_located or match
            continue
        if place.fallback:
            # Not a known place: a hint that led nowhere, not an affected location.
            continue
        locations.append(
            AffectedLocation(
                name=place.name,
                kind=place.kind,
                resolution=(
                    LocationClass.SOURCE_PROVIDED if place_geometry else LocationClass.UNRESOLVED
                ),
                geometry=place_geometry,
                direction=place.direction,
                closure=place.closure,
                mention=place.name,
                found_in="source",
                reference=place.reference,
            )
        )
    listed = {location.name.lower() for location in locations}
    for place in named[:MAX_PLACES]:
        if place.found_in in _LOCATING_FIELDS and place.name.lower() not in listed:
            locations.append(affected_from_place(place))
            listed.add(place.name.lower())
    if source_located is not None:
        located_by, within = source_located, None
    elif text_located is not None:
        located_by, within = text_located, text_within
    else:
        located_by, within = fallback_located, None

    if geometry is not None:
        location: EventLocation | None = EventLocation(
            method=SOURCE_PROVIDED,
            place_name=structured.affected_road or record.title,
            place_kind=geometry.type.lower(),
            precision="source",
            mention=structured.affected_road or record.title,
            found_in="source",
            reference=f"{record.source_id} record {record.external_id}",
        )
        event_geometry: Geometry | None = geometry
        location_class = LocationClass.SOURCE_PROVIDED
    elif located_by is not None:
        location = location_from_place(located_by, within)
        event_geometry = Point(
            type="Point", coordinates=(located_by.longitude, located_by.latitude)
        )
        location_class = LocationClass.APPROXIMATE
    else:
        location = None
        event_geometry = None
        location_class = LocationClass.UNRESOLVED

    start = structured.start if structured.start else (period.start if period else None)
    end = structured.end if structured.end else (period.end if period else None)
    return ReiEvent(
        event_id=event_id_for(record.source_id, record.external_id),
        source_id=record.source_id,
        source_reference=record.url,
        title=record.title,
        event_type=_event_type(structured.event_type),
        description=truncate(record.summary, MAX_DESCRIPTION_LENGTH) if record.summary else None,
        city=classification.city,
        affected_road=structured.affected_road or ("; ".join(road_mentions) or None),
        start_time=start,
        end_time=end,
        direction=EventDirection(structured.direction) if structured.direction else None,
        status=EventStatus.VALIDATION_REQUIRED,
        geometry=event_geometry,
        detection=EventDetection(
            method=DETECTION_METHOD,
            score=None,
            matched_keywords=[],
            road_mentions=road_mentions,
            places=[place.name for place in structured.locations if not place.fallback]
            + [place.name for place in named[:MAX_PLACES] if place.name not in {p.name for p in structured.locations}],
            location=location,
            location_class=location_class,
            affected_locations=locations,
            stated_period=structured.stated_period or (period.text if period else None),
            stated_distance=structured.stated_distance,
            stated_distance_m=structured.stated_distance_m,
            source_geometry_length_m=(
                round(length, 1) if (length := source_length_m(structured)) is not None else None
            ),
            source_category=structured.category,
            source_severity=structured.severity,
            source_status=structured.status,
            source_reports_ended=structured.reported_ended,
            attribution=structured.attribution,
        ),
        created_at=now,
        updated_at=now,
    )
