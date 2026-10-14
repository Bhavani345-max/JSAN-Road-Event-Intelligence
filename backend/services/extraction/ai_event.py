"""Builds an event from an AI reading of an article (services/ai_reading).

The reading has already been checked against the article: its places are
names the article writes word for word, its period comes with the article's
own words. Here those names are placed exactly as the keyword path places
them, by looking them up in the city's OpenStreetMap place list, and the
position is recorded as APPROXIMATE (the named place, not the closure's
extent). The model never supplies a coordinate.
"""

from datetime import datetime

from packages.cities import City
from packages.common.text import truncate
from packages.common.time import IST
from packages.event_schema import (
    AffectedLocation,
    AiReading,
    EventDetection,
    EventStatus,
    LocationClass,
    ReiEvent,
)
from packages.source_models import RawSourceRecord
from services.geo_resolution import PlaceMatch, PlaceResolver
from services.geo_resolution.placement import Mention, Placer

from .attribution import find_attributions
from .event_factory import (
    MAX_DESCRIPTION_LENGTH,
    MAX_PLACES,
    affected_from_placement,
    event_id_for,
    location_from_placed,
    point_of,
)
from .keyword_classifier import ClassificationResult
from .road_mentions import find_road_mentions
from .stated_period import find_stated_period

AI_METHOD = "ai_reading"
# Where traffic is sent instead: never where the event is.
ROUTE_ROLES = ("DIVERSION_ROUTE", "ALTERNATE_ROUTE")
DEFAULT_ROLE_PRIORITY = ("CLOSED", "AFFECTED", "STRETCH_FROM", "VENUE", "STRETCH_TO", "NEAR")


def resolve_place(resolver: PlaceResolver | None, name: str, found_in: str) -> PlaceMatch | None:
    """The city's place of this name: the exact name, else the longest known name inside it."""
    if resolver is None:
        return None
    exact = resolver.lookup(name, found_in=found_in)
    if exact is not None:
        return exact
    inside = resolver.find_in(name, found_in, require_capital=False)
    inside = [match for match in inside if match.has_position] or inside
    return max(inside, key=lambda match: len(match.name), default=None)


def is_ai_road_event(reading: AiReading | None) -> bool:
    """Whether a full, checked reading says the article is a road event in the city."""
    return bool(
        reading is not None
        and reading.stage == "full"
        and reading.is_road_event
        and reading.in_scope
    )


def build_event_from_ai(
    record: RawSourceRecord,
    classification: ClassificationResult,
    reading: AiReading,
    *,
    now: datetime,
    resolver: PlaceResolver | None,
    city: City | None,
    role_priority: tuple[str, ...] = DEFAULT_ROLE_PRIORITY,
    placer: Placer | None = None,
) -> ReiEvent | None:
    """The event the reading describes, or None when it names no place of the event.

    Places: the reading's names with their roles, placed by the placer
    (services/geo_resolution/placement.py): OpenStreetMap first, Google Maps
    when OSM cannot place a name; never at a diversion or alternative route.
    Dates: the period the reading checked against the article, which says
    which date belongs to the road measure; REI's own rules on the whole
    article only when the reading gives none. Type: the reading's intent.
    The keyword result is kept alongside for comparison.
    """
    event_places = [place for place in reading.places if place.role not in ROUTE_ROLES]
    if not event_places:
        return None

    placement = None
    if resolver is not None:
        placer = placer or Placer.for_city(resolver, city)
        placement = placer.place(
            [Mention(name=place.name, role=place.role, found_in=place.found_in) for place in reading.places],
            title=record.title,
            summary=record.summary,
            body=record.content_text,
        )
    affected = (
        affected_from_placement(placement)
        if placement
        else [
            AffectedLocation(
                name=place.name,
                resolution=LocationClass.UNRESOLVED,
                mention=place.name,
                found_in=place.found_in,
                role=place.role,
            )
            for place in reading.places
        ]
    )

    if reading.period_text:
        start, end, period_text = reading.start_time, reading.end_time, reading.period_text
    else:
        rules_period = find_stated_period(
            title=record.title,
            summary=record.summary,
            body=record.content_text,
            published_at=record.published_at,
            zone=city.tz if city else IST,
        )
        start, end, period_text = (
            (rules_period.start, rules_period.end, rules_period.text) if rules_period else (None, None, None)
        )

    road_names = [place.name for place in event_places]
    regex_roads = find_road_mentions(record.title, record.summary)
    attributed = find_attributions(record.title, record.summary, record.content_text)
    if reading.authority and reading.authority not in attributed:
        attributed.append(reading.authority)

    return ReiEvent(
        event_id=event_id_for(record.source_id, record.external_id),
        source_id=record.source_id,
        source_reference=record.url,
        title=record.title,
        event_type=reading.intent or classification.event_type,
        description=truncate(record.summary, MAX_DESCRIPTION_LENGTH) if record.summary else None,
        city=city.name if city else classification.city,
        affected_road="; ".join(road_names) or None,
        start_time=start,
        end_time=end,
        status=EventStatus.VALIDATION_REQUIRED,
        geometry=point_of(placement.best) if placement else None,
        detection=EventDetection(
            method=AI_METHOD,
            score=classification.score,
            matched_keywords=classification.matched_keywords,
            road_mentions=list(dict.fromkeys([*road_names, *regex_roads])),
            places=list(
                dict.fromkeys(
                    location.name
                    for location in affected
                    if location.resolution is LocationClass.APPROXIMATE
                )
            )[:MAX_PLACES],
            location=location_from_placed(placement) if placement else None,
            affected_locations=affected,
            stated_period=period_text,
            attributed_to=attributed,
            ai=reading,
        ),
        created_at=now,
        updated_at=now,
    )
