"""Location classes and multiple affected locations (6 October 2026).

An approximate location (the position of a place an article names) is
recorded and shown as approximate, and cannot be approved as the event's
location. Source-provided geometry, reviewer corrections and QC approval are
told apart. An event may affect several places; those that cannot be placed
stay unresolved names.
"""

from datetime import datetime, timezone

import pytest

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
from services.extraction import KeywordClassifier, build_event_from_article
from services.geo_resolution import default_resolver
from services.gis_resolution import NullGisEngine, ResolvedLocation, apply_resolution
from services.lifecycle import InvalidTransition, check_transition

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)


def article(title, summary=None):
    return RawSourceRecord(
        source_id="test", external_id=title, url=None, title=title, summary=summary,
        content_text=None, categories=["Hyderabad"], published_at=NOW, retrieved_at=NOW,
        raw={}, content_hash="0" * 64,
    )  # fmt: skip


def news_event(title, summary=None):
    record = article(title, summary)
    return build_event_from_article(
        record, KeywordClassifier.from_file().classify(record), now=NOW, resolver=default_resolver()
    )


def detection(**overrides):
    values = dict(method="keyword_rules", score=3.0, matched_keywords=[])
    values.update(overrides)
    return EventDetection(**values)


def location(method):
    return EventLocation(
        method=method, place_name="X", place_kind="area", precision="area", mention="X",
        found_in="title", reference="OpenStreetMap node/1",
    )  # fmt: skip


@pytest.mark.parametrize(
    "method, expected",
    [
        ("named_place", LocationClass.APPROXIMATE),
        ("reviewer_placed", LocationClass.HUMAN_CORRECTED),
        ("source_provided", LocationClass.SOURCE_PROVIDED),
        ("gis_resolved", LocationClass.GIS_RESOLVED),
    ],
)
def test_the_location_class_follows_how_the_location_was_obtained(method, expected):
    assert detection(location=location(method)).location_class is expected


def test_no_location_is_unresolved_and_a_stored_class_is_kept():
    assert detection().location_class is LocationClass.UNRESOLVED
    approved = detection(location=location("named_place"), location_class="QC_APPROVED")
    assert approved.location_class is LocationClass.QC_APPROVED


def test_a_news_event_located_by_a_named_place_is_approximate():
    event = news_event("Traffic diversions at Khajaguda junction for 60 days from September 26")
    assert event.geometry is not None
    assert event.detection.location_class is LocationClass.APPROXIMATE


def test_works_at_several_junctions_list_every_junction_named():
    event = news_event(
        "Hyderabad: Traffic curbs for flyover works at Khajaguda junction and Tolichowki",
        "Works also at Gachibowli Lakeview Colony, a place no map knows.",
    )
    names = [(loc.name, loc.resolution, loc.found_in) for loc in event.detection.affected_locations]
    assert ("Khajaguda Jn", LocationClass.APPROXIMATE, "title") in names
    assert ("Tolichowki", LocationClass.APPROXIMATE, "title") in names
    # Every listed location has a position only if it is a known place.
    for loc in event.detection.affected_locations:
        assert (loc.geometry is None) == (loc.resolution is LocationClass.UNRESOLVED)


def test_a_name_that_cannot_be_placed_is_kept_unresolved():
    event = news_event("Srinagar Colony Road Dug Up Just 6 Days After Relaying, Hyderabad")
    # The headline's whole name: "Srinagar Colony Road".
    [srinagar] = [loc for loc in event.detection.affected_locations if loc.name.startswith("Srinagar Colony")]
    assert srinagar.resolution is LocationClass.UNRESOLVED and srinagar.geometry is None
    assert event.geometry is None
    assert event.detection.location_class is LocationClass.UNRESOLVED


def qc_event(location_class: str | None, method: str | None = "named_place") -> ReiEvent:
    return ReiEvent(
        event_id="EVT-1", source_id="test", title="t", status=EventStatus.QC_PENDING,
        geometry=Point(type="Point", coordinates=(78.4, 17.4)), start_time=NOW,
        detection=detection(
            location=location(method) if method else None, location_class=location_class
        ),
        created_at=NOW, updated_at=NOW,
    )  # fmt: skip


def test_an_approximate_location_cannot_be_approved():
    with pytest.raises(InvalidTransition, match="approximate"):
        check_transition(qc_event(None, "named_place"), EventStatus.APPROVED)


@pytest.mark.parametrize("method", ["reviewer_placed", "source_provided"])
def test_a_corrected_or_source_provided_location_can_be_approved(method):
    check_transition(qc_event(None, method), EventStatus.APPROVED)


def test_the_null_gis_engine_resolves_nothing():
    event = news_event("Traffic diversions at Khajaguda junction for 60 days from September 26")
    results = NullGisEngine().resolve(event, "hyderabad")
    assert {r.resolution for r in results} == {LocationClass.UNRESOLVED}
    assert apply_resolution(event.detection.affected_locations, results) == (
        event.detection.affected_locations
    )


def test_a_gis_result_never_replaces_source_provided_or_corrected_geometry():
    source_line = Point(type="Point", coordinates=(-0.1, 51.5))
    locations = [
        AffectedLocation(name="A13", resolution=LocationClass.SOURCE_PROVIDED, geometry=source_line),
        AffectedLocation(name="Spot", resolution=LocationClass.HUMAN_CORRECTED, geometry=source_line),
        AffectedLocation(name="Junction", resolution=LocationClass.UNRESOLVED),
    ]
    resolved = Point(type="Point", coordinates=(-0.2, 51.4))
    results = [
        ResolvedLocation(name=loc.name, resolution=LocationClass.GIS_RESOLVED, geometry=resolved)
        for loc in locations
    ]
    applied = apply_resolution(locations, results)
    assert applied[0] == locations[0] and applied[1] == locations[1]
    assert applied[2].resolution is LocationClass.GIS_RESOLVED and applied[2].geometry == resolved


def test_gis_resolved_needs_a_geometry_and_one_answer_per_location():
    locations = [AffectedLocation(name="J", resolution=LocationClass.UNRESOLVED)]
    with pytest.raises(ValueError, match="needs a geometry"):
        apply_resolution(locations, [ResolvedLocation(name="J", resolution=LocationClass.GIS_RESOLVED)])
    with pytest.raises(ValueError, match="once for every"):
        apply_resolution(locations, [])
