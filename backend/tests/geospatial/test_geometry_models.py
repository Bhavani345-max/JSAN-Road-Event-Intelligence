from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from packages.geo_models import Geometry, LineString, Point, Polygon
from tests.support import load_located_events

geometry = TypeAdapter(Geometry)

# Rough bounding box of the Hyderabad metropolitan area.
WEST, SOUTH, EAST, NORTH = 78.2, 17.2, 78.7, 17.6


def test_valid_geometries_parse_to_their_type():
    assert isinstance(geometry.validate_python({"type": "Point", "coordinates": [78.47, 17.4]}), Point)
    assert isinstance(
        geometry.validate_python({"type": "LineString", "coordinates": [[78.4, 17.4], [78.5, 17.5]]}),
        LineString,
    )
    ring = [[78.4, 17.4], [78.5, 17.4], [78.5, 17.5], [78.4, 17.4]]
    assert isinstance(geometry.validate_python({"type": "Polygon", "coordinates": [ring]}), Polygon)


@pytest.mark.parametrize(
    "value",
    [
        {"type": "Point", "coordinates": [17.4, 178.47]},  # latitude out of range
        {"type": "Point", "coordinates": [278.47, 17.4]},  # longitude out of range
        {"type": "Point", "coordinates": [78.47]},
        {"type": "LineString", "coordinates": [[78.4, 17.4]]},  # a line needs two points
        {"type": "Polygon", "coordinates": [[[78.4, 17.4], [78.5, 17.4], [78.5, 17.5]]]},  # too short
        {"type": "Polygon", "coordinates": [[[78.4, 17.4], [78.5, 17.4], [78.5, 17.5], [78.4, 17.5]]]},  # open
        {"type": "MultiPoint", "coordinates": [[78.4, 17.4]]},  # unsupported type
        {"type": "Point"},
    ],
)
def test_invalid_geometries_are_rejected(value):
    with pytest.raises(ValidationError):
        geometry.validate_python(value)


def test_located_fixture_geometry_is_valid_and_inside_hyderabad():
    events = load_located_events(datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc))
    assert len(events) == 8
    assert {type(event.geometry) for event in events} == {Point, LineString, Polygon}

    for event in events:
        shape = event.geometry
        positions = (
            [shape.coordinates]
            if isinstance(shape, Point)
            else shape.coordinates
            if isinstance(shape, LineString)
            else [position for ring in shape.coordinates for position in ring]
        )
        for longitude, latitude in positions:
            assert WEST <= longitude <= EAST, event.event_id
            assert SOUTH <= latitude <= NORTH, event.event_id


def test_located_fixture_times_follow_the_given_day_in_india_time():
    # 20:00 UTC on 2 Oct is already 01:30 on 3 Oct in India.
    events = {e.event_id: e for e in load_located_events(datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc))}
    marathon = events["TEST-LOC-001"]  # two days later, 04:30–10:00 IST
    assert marathon.start_time.isoformat() == "2026-10-05T04:30:00+05:30"
    assert marathon.end_time.isoformat() == "2026-10-05T10:00:00+05:30"
    assert events["TEST-LOC-005"].end_time is None
