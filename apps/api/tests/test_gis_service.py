"""Applying GIS results to events: precedence, review, and re-runs (6 October 2026).

Uses the small synthetic test network of tests/unit/test_gis_resolver.py
(test data only, never loaded by the application).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models import Event, JunctionReference
from app.repositories.events import EventRepository
from app.repositories.sources import SourceRepository
from app.services import gis_service
from app.services.review_service import set_event_location, update_event_status
from connectors.official import tfl_source
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.cities import get_city
from packages.event_schema import (
    AffectedLocation,
    EventDetection,
    EventLocation,
    EventStatus,
    LocationClass,
    ReiEvent,
)
from packages.geo_models import Point
from services.gis_resolution.resolver import JunctionRef, OsmGisEngine
from services.lifecycle import InvalidTransition
from tests.unit.test_gis_resolver import B, BBOX, NETWORK

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
HYDERABAD = get_city("hyderabad")
LOCALITY = (78.401, 17.401)


def add(session, event_id, title, *, method="named_place", city="Hyderabad", source=TELANGANA_TODAY,
        roads=(), status=EventStatus.VALIDATION_REQUIRED, position=LOCALITY) -> Event:  # fmt: skip
    location = EventLocation(
        method=method, place_name="Some Locality", place_kind="area", precision="area",
        mention="Some Locality", found_in="title", reference="OpenStreetMap node/1",
    )  # fmt: skip
    event = ReiEvent(
        event_id=event_id, source_id=source.source_id, title=title, city=city, start_time=NOW,
        status=status, geometry=Point(type="Point", coordinates=position),
        detection=EventDetection(
            method="keyword_rules", score=3.0, matched_keywords=[], road_mentions=list(roads),
            location=location,
            affected_locations=[AffectedLocation(name="Some Locality", kind="area",
                                                 resolution=LocationClass.APPROXIMATE, found_in="title")],
        ),  # fmt: skip
        created_at=NOW, updated_at=NOW,
    )
    row = EventRepository(session).add(event, artifact_id=None, change_reason="Created", changed_by="ingestion")
    session.commit()
    return row


@pytest.fixture
def db(session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY, tfl_source(scheduled=False)])
    session.commit()
    return session


def engine(junctions=()) -> OsmGisEngine:
    return OsmGisEngine(NETWORK, junctions, places=None, bbox=BBOX)


def resolve(session, row, junctions=()):
    report = gis_service.resolve_event(session, row, engine(junctions), now=NOW)
    session.commit()
    session.refresh(row)
    return report


CROSSING_TITLE = "Diversions at the junction of Test Main Road and Cross Road Avenue."


def test_a_defensible_result_becomes_a_gis_proposal_and_keeps_the_old_location(db):
    row = add(db, "EVT-1", CROSSING_TITLE)
    report = resolve(db, row)
    assert report["applied"] and report["changed"]
    assert row.geometry == {"type": "Point", "coordinates": list(B)}
    detection = row.detection
    assert detection["location_class"] == "GIS_RESOLVED"
    assert detection["location"]["method"] == "gis_resolved"
    gis = detection["gis"]
    assert gis["review_status"] == "PENDING" and gis["network"] == "OpenStreetMap test-network"
    assert gis["previous"]["geometry"] == {"type": "Point", "coordinates": list(LOCALITY)}
    assert gis["previous"]["location_class"] == "APPROXIMATE"
    [result] = [r for r in gis["results"] if r["applied"]]
    assert result["chosen"]["method"] == "ROAD_INTERSECTION" and result["confidence"] == "HIGH"
    assert row.versions[-1].changed_by == "gis-resolver"


def test_running_the_resolver_again_changes_nothing(db):
    row = add(db, "EVT-1", CROSSING_TITLE)
    resolve(db, row)
    version = row.version
    report = resolve(db, row)
    assert not report["changed"] and row.version == version


def test_a_gis_proposal_must_be_approved_before_the_event_can_be(db):
    row = add(db, "EVT-1", CROSSING_TITLE, status=EventStatus.QC_PENDING)
    resolve(db, row)
    with pytest.raises(InvalidTransition, match="GIS proposal"):
        update_event_status(db, "EVT-1", EventStatus.APPROVED, "ok")
    gis_service.approve(db, "EVT-1", reviewer="local-reviewer", reason="Checked on the map")
    update_event_status(db, "EVT-1", EventStatus.APPROVED, "ok")
    assert db.get(Event, "EVT-1").status == "APPROVED"


def test_a_rejected_proposal_restores_the_old_location_and_is_not_proposed_again(db):
    row = add(db, "EVT-1", CROSSING_TITLE)
    resolve(db, row)
    gis_service.reject(db, "EVT-1", reviewer="local-reviewer", reason="Not this junction")
    db.refresh(row)
    assert row.geometry == {"type": "Point", "coordinates": list(LOCALITY)}
    assert row.detection["location_class"] == "APPROXIMATE"
    assert row.detection["gis"]["review_status"] == "REJECTED"
    report = resolve(db, row)
    assert not report["applied"]
    assert row.detection["location_class"] == "APPROXIMATE"


def test_source_provided_geometry_is_never_replaced(db):
    row = add(db, "EVT-1", CROSSING_TITLE, method="source_provided", source=tfl_source(scheduled=False))
    before = dict(row.geometry)
    report = resolve(db, row)
    assert not report["applied"]
    assert row.geometry == before and row.detection["location_class"] == "SOURCE_PROVIDED"
    assert "higher-precedence" in row.detection["gis"]["not_applied_reason"]


def test_a_reviewers_correction_is_never_replaced_and_supersedes_a_proposal(db):
    row = add(db, "EVT-1", CROSSING_TITLE)
    resolve(db, row)
    set_event_location(db, None, "EVT-1", longitude=78.402, latitude=17.402, place_name="Gate", reason="Seen on site")
    db.refresh(row)
    assert row.detection["location_class"] == "HUMAN_CORRECTED"
    assert row.detection["gis"]["review_status"] == "SUPERSEDED"
    report = resolve(db, row)
    assert not report["applied"]
    assert row.geometry["coordinates"] == [78.402, 17.402]


def test_an_approximate_location_is_not_promoted_without_a_defensible_result(db):
    row = add(db, "EVT-1", "Traffic jam reported on Test Main Road")  # a road, no stretch
    report = resolve(db, row)
    assert not report["applied"]
    assert row.detection["location_class"] == "APPROXIMATE"
    assert row.geometry["coordinates"] == list(LOCALITY)
    assert row.detection["gis"]["review_status"] == "NOT_APPLIED"
    [road] = [r for r in row.detection["gis"]["results"] if r["kind"] == "road"]
    assert road["confidence"] == "MEDIUM" and road["chosen"]["geometry"]["type"] == "LineString"


def test_each_location_keeps_its_own_result(db):
    row = add(db, "EVT-1", "Works at Test Junction and Lakeside Flyover; Nowhere Junction too")
    resolve(db, row)
    locations = {loc["name"]: loc for loc in row.detection["affected_locations"]}
    assert locations["Test Junction"]["resolution"] == "GIS_RESOLVED"
    assert locations["Lakeside Flyover"]["resolution"] == "GIS_RESOLVED"
    assert locations["Lakeside Flyover"]["geometry"]["type"] == "LineString"
    assert locations["Nowhere Junction"]["resolution"] == "UNRESOLVED"
    assert locations["Some Locality"]["resolution"] == "APPROXIMATE"
    # One event geometry: the first location of the headline, not a merged shape.
    assert row.geometry == {"type": "Point", "coordinates": list(B)}


def test_a_reviewer_can_choose_one_of_ambiguous_candidates(db):
    row = add(db, "EVT-1", "Potholes on Twin Road")
    resolve(db, row)
    index = next(i for i, r in enumerate(row.detection["gis"]["results"]) if r["ambiguous"])
    gis_service.choose(db, "EVT-1", result_index=index, alternative_index=0, reviewer="local-reviewer", reason="The one by the lake")
    db.refresh(row)
    assert row.detection["location_class"] == "GIS_RESOLVED"
    assert row.detection["gis"]["review_status"] == "APPROVED"
    assert "REVIEWER_CONFIRMED" in row.detection["location"]["reference"]


def test_an_unconfirmed_junction_needs_a_reviewer_then_resolves(db):
    row = add(db, "EVT-1", "Curbs near Unnamed Junction for flyover works")
    ref = gis_service.propose_junction(
        db, city_id="hyderabad", name="Unnamed Junction", source="test", position=B, osm_node_id=11,
        related_roads=["Test Main Road"],
    )  # fmt: skip
    refs = gis_service.junction_refs(db, "hyderabad")
    assert refs[0].status == "UNCONFIRMED"
    assert not resolve(db, row, refs)["applied"]
    gis_service.decide_junction(db, ref.junction_id, confirm=True, reviewer="local-reviewer", reason="Checked", method="test")
    refs = gis_service.junction_refs(db, "hyderabad")
    assert resolve(db, row, refs)["applied"]
    stored = db.scalars(select(JunctionReference)).one()
    assert (stored.status, stored.reviewer) == ("CONFIRMED", "local-reviewer")


def test_a_junction_without_a_position_cannot_be_confirmed(db):
    ref = gis_service.propose_junction(db, city_id="hyderabad", name="Nameless Junction", source="test")
    with pytest.raises(gis_service.GisActionRefused, match="position"):
        gis_service.decide_junction(db, ref.junction_id, confirm=True, reviewer="r", reason="x", method="t")


def test_an_event_of_a_city_without_a_road_network_is_left_alone(db):
    row = add(db, "EVT-L", CROSSING_TITLE, city="London", method="source_provided", source=tfl_source(scheduled=False))
    assert gis_service.get_network_city(row) is None
    assert row.detection.get("gis") is None

