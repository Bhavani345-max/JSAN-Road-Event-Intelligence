from datetime import datetime

from packages.cities import City
from packages.common.hashing import sha256_hex
from packages.common.time import IST
from packages.common.text import truncate
from packages.event_schema import (
    AffectedLocation,
    EventDetection,
    EventLocation,
    EventStatus,
    LocationClass,
    ReiEvent,
)
from packages.geo_models import Point
from packages.source_models import RawSourceRecord
from services.geo_resolution import PlaceMatch, PlaceResolver, spot_within
from services.geo_resolution.placement import Mention, Placed, Placement, Placer

from .attribution import find_attributions
from .keyword_classifier import ClassificationResult
from .road_mentions import find_road_mentions
from .stated_period import find_stated_period

DETECTION_METHOD = "keyword_rules"
LOCATION_METHOD = "named_place"
MAX_DESCRIPTION_LENGTH = 600
MAX_PLACES = 8

# A place in the headline or summary is what the article is about. One that
# appears only in the body may be a passing mention, so it does not locate the event.
_LOCATING_FIELDS = ("title", "summary")


def event_id_for(source_id: str, external_id: str) -> str:
    """Deterministic id, so re-processing an item can never create a second event."""
    return "EVT-" + sha256_hex(f"{source_id}|{external_id}")[:12].upper()


def _location(place: PlaceMatch, within: PlaceMatch | None = None) -> EventLocation:
    return EventLocation(
        method=LOCATION_METHOD,
        place_name=place.name,
        place_kind=place.kind,
        precision=place.precision,
        mention=place.mention,
        found_in=place.found_in,
        reference=f"OpenStreetMap {place.osm_ref}",
        within=within.name if within else None,
    )


def _affected(place: PlaceMatch) -> AffectedLocation:
    """A place the headline or summary names, at its named-place position if it has one."""
    return AffectedLocation(
        name=place.name,
        kind=place.kind,
        resolution=LocationClass.APPROXIMATE if place.has_position else LocationClass.UNRESOLVED,
        geometry=(
            Point(type="Point", coordinates=(place.longitude, place.latitude))
            if place.has_position
            else None
        ),
        mention=place.mention,
        found_in=place.found_in,
        reference=f"OpenStreetMap {place.osm_ref}" if place.osm_ref else None,
    )


def location_from_placed(placement: Placement) -> EventLocation | None:
    """How the event was located: the place the placer chose, with its source."""
    best = placement.best
    if best is None:
        return None
    return EventLocation(
        method=LOCATION_METHOD,
        place_name=best.name,
        place_kind=best.kind,
        precision=best.precision,
        mention=best.mention.name,
        found_in=best.mention.found_in or "title",
        reference=best.reference,
        within=placement.within,
    )


def affected_from_placement(placement: Placement) -> list[AffectedLocation]:
    """Every place the source names for the event: each placed one at its named
    place's position, each one that could not be placed by its name only."""
    affected = [
        AffectedLocation(
            name=placed.name,
            kind=placed.kind,
            resolution=LocationClass.APPROXIMATE,
            geometry=Point(type="Point", coordinates=(placed.longitude, placed.latitude)),
            mention=placed.mention.name,
            found_in=placed.mention.found_in,
            reference=placed.reference,
            role=placed.mention.role,
        )
        for placed in sorted(placement.placed, key=lambda placed: placed.order)
    ]
    affected += [
        AffectedLocation(
            name=mention.name,
            resolution=LocationClass.UNRESOLVED,
            mention=mention.name,
            found_in=mention.found_in,
            role=mention.role,
        )
        for mention in placement.unplaced
    ]
    return affected


def point_of(placed: Placed | None) -> Point | None:
    if placed is None:
        return None
    return Point(type="Point", coordinates=(placed.longitude, placed.latitude))


def _field_of(name: str, record: RawSourceRecord) -> str | None:
    for field, text in (("title", record.title), ("summary", record.summary)):
        if text and name.lower() in text.lower():
            return field
    return None


def article_mentions(placer: Placer, record: RawSourceRecord) -> list[Mention]:
    """The names an article's headline and summary state: places as whole names, then roads.

    Places named only in the body may be diversion routes, so they do not locate the event.
    """
    mentions = placer.whole_mentions(record.title, "title") + placer.whole_mentions(record.summary, "summary")
    seen = {mention.name.lower() for mention in mentions}
    for road in find_road_mentions(record.title, record.summary):
        if road.lower() not in seen and not any(road.lower() in name for name in seen):
            seen.add(road.lower())
            mentions.append(Mention(name=road, role=None, found_in=_field_of(road, record)))
    return mentions


# For events built from an official source's text (source_event.py), which
# locate a named place the same way an article does.
location_from_place = _location
affected_from_place = _affected


def locate(places: list[PlaceMatch]) -> tuple[PlaceMatch | None, PlaceMatch | None]:
    """The place an event is positioned at, and the locality it lies within.

    The headline's place comes first, then the summary's. When that place is a
    locality or a road, and the headline or summary also names a spot inside
    it (a junction, flyover or landmark within WITHIN_KM), the event is put at
    that spot: it is the most exact place the article itself names. A spot in
    the body alone is not used, as it may be a diversion route rather than the
    event.
    """
    named_up_front = [place for place in places if place.found_in in _LOCATING_FIELDS]
    located_by = next((place for place in named_up_front if place.has_position), None)
    if located_by is None or located_by.is_spot:
        return located_by, None
    spot = spot_within(located_by, named_up_front)
    return (spot, located_by) if spot else (located_by, None)


def publication_day_known(record: RawSourceRecord) -> bool:
    """Whether the record's publication time is the publisher's own, so that a
    day can be counted from it ("begins today", decision 0038).

    A result found through a search (Google News via Serper, GDELT) carries the
    search engine's time ("3 days ago", the time it was seen) unless its
    article page stated one (`published_at_from` "article").
    """
    if record.published_at is None:
        return False
    raw = record.raw or {}
    if "search_result" in raw:
        return raw.get("published_at_from") == "article"
    return True


def build_event_from_article(
    record: RawSourceRecord,
    classification: ClassificationResult,
    *,
    now: datetime,
    resolver: PlaceResolver | None = None,
    city: City | None = None,
    placer: Placer | None = None,
) -> ReiEvent:
    """Create the canonical event for an article detected as traffic-related.

    Only what the article itself provides is filled in:

    - times, when it states a period in so many words ("for 60 days from
      September 26"); the words are kept in `detection.stated_period`;
    - a location, when its headline or summary names a known Hyderabad place;
      the position is that place's on OpenStreetMap, and `detection.location`
      records which place and where it was named.

    Severity, direction and confidence stay empty, and the event always starts
    as VALIDATION_REQUIRED: a keyword match is a lead for a human reviewer, not
    a confirmed road event.
    """
    road_mentions = find_road_mentions(record.title, record.summary)
    places = (
        resolver.find_places(title=record.title, summary=record.summary, body=record.content_text)
        if resolver
        else []
    )
    placement = None
    if resolver is not None:
        placer = placer or Placer.for_city(resolver, city)
        placement = placer.place(
            article_mentions(placer, record),
            title=record.title,
            summary=record.summary,
            body=record.content_text,
        )
    period = find_stated_period(
        title=record.title,
        summary=record.summary,
        body=record.content_text,
        published_at=record.published_at,
        zone=city.tz if city else IST,
        publication_day_known=publication_day_known(record),
    )
    return ReiEvent(
        event_id=event_id_for(record.source_id, record.external_id),
        source_id=record.source_id,
        source_reference=record.url,
        title=record.title,
        event_type=classification.event_type,
        description=truncate(record.summary, MAX_DESCRIPTION_LENGTH) if record.summary else None,
        city=classification.city,
        affected_road="; ".join(road_mentions) or None,
        start_time=period.start if period else None,
        end_time=period.end if period else None,
        status=EventStatus.VALIDATION_REQUIRED,
        geometry=point_of(placement.best) if placement else None,
        detection=EventDetection(
            method=DETECTION_METHOD,
            score=classification.score,
            matched_keywords=classification.matched_keywords,
            road_mentions=road_mentions,
            places=[place.name for place in places[:MAX_PLACES]],
            location=location_from_placed(placement) if placement else None,
            # Every place named up front: an event may affect several (works at
            # three junctions). Places named only in the body may be diversion
            # routes, so they are kept in `places` but not listed as affected.
            affected_locations=affected_from_placement(placement) if placement else [],
            stated_period=period.text if period else None,
            attributed_to=find_attributions(record.title, record.summary, record.content_text),
        ),
        created_at=now,
        updated_at=now,
    )


def names_a_place(event: ReiEvent) -> bool:
    """Whether the article behind the event names any road or Hyderabad place."""
    detection = event.detection
    return bool(detection and (detection.places or detection.road_mentions))
