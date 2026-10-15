"""Cross-source merging through the database and the API (6 October 2026).

Merging links events, never deletes or rewrites them: every source's evidence
stays reachable, its history stays whole, and which source gave which field
is recorded. Uncertain matches wait for a reviewer; conflicts are kept.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, EventMergeCandidate
from app.repositories.events import EventRepository
from app.repositories.sources import SourceRepository
from app.services import merge_service
from connectors.official import tfl_source
from connectors.rss.siasat import SIASAT
from connectors.rss.telangana_today import TELANGANA_TODAY
from connectors.rss.the_hindu import THE_HINDU
from packages.event_schema import (
    AffectedLocation,
    EventDetection,
    EventLocation,
    EventStatus,
    LocationClass,
    ReiEvent,
)
from packages.geo_models import Point
from tests.support import SOURCE_FIXTURES, FakeConnector, parse_fixture, sign_in

T0 = datetime(2026, 9, 26, tzinfo=timezone.utc)
KHAJAGUDA = (78.3817, 17.4227)


def add(session, event_id, source, title, *, place="Khajaguda Jn", kind="junction",
        position=KHAJAGUDA, method="named_place", event_type="TRAFFIC_DIVERSION",
        start=None, end=None, city="Hyderabad", created=T0) -> Event:  # fmt: skip
    location = (
        EventLocation(
            method=method, place_name=place, place_kind=kind, precision="place", mention=place,
            found_in="title", reference="OpenStreetMap node/1" if method == "named_place" else "source",
        )  # fmt: skip
        if position
        else None
    )
    resolution = LocationClass.SOURCE_PROVIDED if method == "source_provided" else LocationClass.APPROXIMATE
    event = ReiEvent(
        event_id=event_id, source_id=source.source_id, title=title, event_type=event_type,
        city=city, start_time=start, end_time=end, status=EventStatus.VALIDATION_REQUIRED,
        geometry=Point(type="Point", coordinates=position) if position else None,
        detection=EventDetection(
            method="source_provided" if method == "source_provided" else "keyword_rules",
            score=3.0, matched_keywords=[], location=location,
            affected_locations=[AffectedLocation(name=place, kind=kind, resolution=resolution)],
        ),
        created_at=created, updated_at=created,
    )  # fmt: skip
    row = EventRepository(session).add(event, artifact_id=None, change_reason="Created", changed_by="ingestion")
    session.commit()
    return row


@pytest.fixture
def db(session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY, THE_HINDU, SIASAT, tfl_source(scheduled=False)])
    session.commit()
    return session


def candidates(session):
    return session.scalars(select(EventMergeCandidate).order_by(EventMergeCandidate.id)).all()


def by_id(session, event_id) -> Event:
    session.expire_all()
    return session.get(Event, event_id)


# --- automatic merges --------------------------------------------------------------------


def test_the_same_event_from_two_sources_is_merged_with_both_kept(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Traffic diversions at Khajaguda junction for 60 days")
    add(db, "EVT-B", THE_HINDU, "Hyderabad: Traffic diversions at Khajaguda junction for 60 days",
        created=T0 + timedelta(hours=2))  # fmt: skip
    run = merge_service.find_candidates(db)
    db.commit()
    assert (run.candidates, run.auto_merged) == (1, 1)
    a, b = by_id(db, "EVT-A"), by_id(db, "EVT-B")
    # Same standing: the first reported is canonical; the other is linked, not deleted.
    assert a.merged_into is None and b.merged_into == "EVT-A"
    [contribution] = a.detection["contributions"]
    assert (contribution["event_id"], contribution["source_id"], contribution["how"]) == (
        "EVT-B", "the-hindu", "automatic",
    )
    assert candidates(db)[0].status == "AUTO_MERGED"


def test_the_same_event_from_three_sources_becomes_one_event_with_three_sources(db):
    title = "Traffic diversions at Khajaguda junction for 60 days"
    add(db, "EVT-A", TELANGANA_TODAY, title)
    add(db, "EVT-B", THE_HINDU, title, created=T0 + timedelta(hours=1))
    add(db, "EVT-C", SIASAT, title, created=T0 + timedelta(hours=2))
    run = merge_service.find_candidates(db)
    db.commit()
    assert run.auto_merged == 2
    canonical = by_id(db, "EVT-A")
    assert sorted(c["source_id"] for c in canonical.detection["contributions"]) == ["siasat", "the-hindu"]
    assert {by_id(db, "EVT-B").merged_into, by_id(db, "EVT-C").merged_into} == {"EVT-A"}


def test_a_canonical_event_takes_missing_fields_and_records_where_they_came_from(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Traffic diversions at Khajaguda junction for 60 days")
    add(db, "EVT-B", THE_HINDU, "Traffic diversions at Khajaguda junction for 60 days",
        start=T0, end=T0 + timedelta(days=59), created=T0 + timedelta(hours=1))  # fmt: skip
    merge_service.find_candidates(db)
    db.commit()
    canonical = by_id(db, "EVT-A")
    assert canonical.start_time == T0
    provenance = canonical.detection["provenance"]
    assert provenance["start_time"] == {"event_id": "EVT-B", "source_id": "the-hindu"}
    assert provenance["geometry"] == {"event_id": "EVT-A", "source_id": "telangana-today"}
    assert canonical.detection["contributions"][0]["fields"] == ["start_time", "end_time"]


def test_history_is_preserved_on_both_events(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Traffic diversions at Khajaguda junction for 60 days")
    add(db, "EVT-B", THE_HINDU, "Traffic diversions at Khajaguda junction for 60 days", created=T0 + timedelta(hours=1))
    merge_service.find_candidates(db)
    db.commit()
    canonical, member = by_id(db, "EVT-A"), by_id(db, "EVT-B")
    assert [v.version for v in canonical.versions] == [1, 2]
    assert [v.version for v in member.versions] == [1, 2]
    assert member.versions[0].change_reason == "Created"
    assert member.versions[1].change_reason.startswith("Merged into EVT-A")
    assert canonical.versions[1].changed_by == "auto-merge"


# --- candidates: kept apart until a reviewer decides --------------------------------------------


def possible_pair(db):
    add(db, "EVT-A", TELANGANA_TODAY, "KBR flyover plan changed due to success of one way traffic",
        place="KBR Park", kind="landmark", position=(78.4201, 17.4202), event_type=None)  # fmt: skip
    add(db, "EVT-B", SIASAT, "GHMC revises KBR Park flyover plans, mulls permanent one-way",
        place="KBR Park", kind="landmark", position=(78.4201, 17.4202), event_type=None,
        created=T0 + timedelta(days=1))  # fmt: skip
    run = merge_service.find_candidates(db)
    db.commit()
    return run


def test_an_uncertain_match_becomes_a_candidate_and_both_stay_separate(db):
    run = possible_pair(db)
    assert (run.candidates, run.auto_merged) == (1, 0)
    [candidate] = candidates(db)
    assert (candidate.classification, candidate.status) == ("POSSIBLE", "PENDING")
    assert by_id(db, "EVT-A").merged_into is None and by_id(db, "EVT-B").merged_into is None


def test_a_confirmed_merge_links_the_events_with_the_reviewers_reason(db):
    possible_pair(db)
    candidate = candidates(db)[0]
    canonical = merge_service.confirm(db, candidate.id, reviewer="local-reviewer", reason="Same GHMC decision")
    assert canonical.event_id == "EVT-A"
    assert by_id(db, "EVT-B").merged_into == "EVT-A"
    contribution = by_id(db, "EVT-A").detection["contributions"][0]
    assert (contribution["how"], contribution["merged_by"], contribution["reason"]) == (
        "reviewer", "local-reviewer", "Same GHMC decision",
    )
    assert candidates(db)[0].status == "CONFIRMED"
    with pytest.raises(merge_service.CandidateDecided):
        merge_service.confirm(db, candidate.id, reviewer="local-reviewer", reason="again")


def test_a_rejected_merge_keeps_them_apart_and_is_not_proposed_again(db):
    possible_pair(db)
    candidate = candidates(db)[0]
    merge_service.reject(db, candidate.id, reviewer="local-reviewer", reason="Different articles' subjects")
    assert candidates(db)[0].status == "REJECTED"
    again = merge_service.find_candidates(db)
    db.commit()
    assert again.candidates == 0
    assert by_id(db, "EVT-A").merged_into is None and by_id(db, "EVT-B").merged_into is None


def test_conflicting_dates_are_kept_side_by_side_and_flagged(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Traffic diversions at Khajaguda junction for 60 days",
        start=T0, end=T0 + timedelta(days=59))  # fmt: skip
    add(db, "EVT-B", THE_HINDU, "Traffic diversions at Khajaguda junction for 60 days",
        start=T0, end=T0 + timedelta(days=89), created=T0 + timedelta(hours=1))  # fmt: skip
    run = merge_service.find_candidates(db)
    db.commit()
    assert run.auto_merged == 0  # disagreeing sources are not merged automatically
    candidate = candidates(db)[0]
    assert [c["field"] for c in candidate.conflicts] == ["end_time"]
    canonical = merge_service.confirm(db, candidate.id, reviewer="local-reviewer", reason="Same works")
    canonical = by_id(db, canonical.event_id)
    # The canonical event keeps its own end; both values are recorded; review is flagged.
    assert canonical.end_time == T0 + timedelta(days=59)
    [conflict] = canonical.detection["merge_conflicts"]
    assert conflict["field"] == "end_time"
    assert [v["source_id"] for v in conflict["values"]] == ["telangana-today", "the-hindu"]
    assert canonical.detection["merge_review_required"] is True


def test_conflicting_geometry_is_kept_and_flagged(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Works on NH-65", place="NH-65", kind="road",
        position=(78.30, 17.52), event_type="ROAD_CONSTRUCTION")  # fmt: skip
    add(db, "EVT-B", THE_HINDU, "Works on NH-65 near Isnapur", place="NH-65", kind="road",
        position=(78.25, 17.54), event_type="ROAD_CONSTRUCTION", created=T0 + timedelta(hours=1))  # fmt: skip
    merge_service.find_candidates(db)
    db.commit()
    candidate = candidates(db)[0]
    canonical = merge_service.confirm(db, candidate.id, reviewer="local-reviewer", reason="Same NH-65 works")
    canonical = by_id(db, canonical.event_id)
    assert canonical.geometry["coordinates"] == [78.30, 17.52]
    assert [c["field"] for c in canonical.detection["merge_conflicts"]] == ["geometry"]


def test_an_official_event_stays_canonical_and_keeps_its_geometry_against_news(db):
    london = dict(city="London", place="Waterloo Road", kind="street")
    add(db, "EVT-NEWS", THE_HINDU, "Waterloo Road works", position=(-0.1110, 51.5010),
        event_type="ROAD_WORKS", **london)  # fmt: skip
    add(db, "EVT-TFL", tfl_source(scheduled=False), "Waterloo Road works", position=(-0.1100, 51.5000),
        method="source_provided", event_type="ROAD_WORKS", created=T0 + timedelta(hours=3), **london)  # fmt: skip
    run = merge_service.find_candidates(db)
    db.commit()
    assert run.auto_merged == 0  # official + news: never automatic
    candidate = candidates(db)[0]
    canonical = merge_service.confirm(db, candidate.id, reviewer="local-reviewer", reason="Same works")
    assert canonical.event_id == "EVT-TFL"  # the official source, though reported later
    canonical = by_id(db, "EVT-TFL")
    assert canonical.geometry["coordinates"] == [-0.11, 51.5]
    assert canonical.detection["location_class"] == "SOURCE_PROVIDED"
    assert canonical.detection["provenance"]["geometry"]["source_id"] == "tfl-road-disruptions"


def test_events_at_different_junctions_get_no_candidate(db):
    add(db, "EVT-A", TELANGANA_TODAY, "Traffic diversions at Khajaguda junction")
    add(db, "EVT-B", THE_HINDU, "Traffic diversions at Biodiversity junction", place="Biodiversity Junction",
        position=(78.3890, 17.4280))  # fmt: skip
    assert merge_service.find_candidates(db).candidates == 0


# --- the API ---------------------------------------------------------------------------


@pytest.fixture
def merging_client(engine, session):
    """Every RSS source fed its publisher-format fixture, with matching after ingestion on."""
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=True,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        source.source_id: (
            lambda source=source, filename=filename: FakeConnector(parse_fixture(source, filename), source=source)
        )
        for source, filename in SOURCE_FIXTURES
    }
    app.state.ingestion_service.resolver = None
    with TestClient(app) as client:
        yield sign_in(client)


def test_the_same_articles_from_four_sources_are_listed_once_with_every_source(merging_client):
    """The fixture feeds carry the same articles under four publishers: duplicate ingestion."""
    merging_client.post("/api/ingestion/run")
    every = merging_client.get("/api/events", params={"view": "validation", "include_hidden": "true", "include_merged": "true"}).json()
    listed = merging_client.get("/api/events?view=validation&include_hidden=true").json()
    assert every["total"] == 9
    assert listed["total"] < every["total"]
    # Nothing was deleted: listed events plus their merged evidence account for all 9.
    assert sum(1 + len(e["other_evidence"]) for e in listed["items"]) == 9
    merged = [e for e in listed["items"] if e["other_evidence"]]
    assert merged
    for event in merged:
        sources = {event["source"]["source_id"]} | {o["source"]["source_id"] for o in event["other_evidence"]}
        assert len(sources) == 1 + len(event["other_evidence"])
        for other in event["other_evidence"]:
            # Each source's own evidence is still reachable, merged or not.
            member = merging_client.get(f"/api/events/{other['event_id']}").json()
            assert member["merged_into"] == event["event_id"]
            assert member["evidence"]["url"] == other["url"]
    # Polling again changes nothing.
    merging_client.post("/api/ingestion/run")
    assert merging_client.get("/api/events?view=validation&include_hidden=true").json()["total"] == listed["total"]


def test_candidates_can_be_listed_confirmed_and_rejected_through_the_api(merging_client, session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY, SIASAT])
    session.commit()
    possible_pair(session)
    pending = merging_client.get("/api/merge-candidates", params={"status": "PENDING"}).json()
    assert len(pending) == 1 and pending[0]["classification"] == "POSSIBLE"
    event = merging_client.get("/api/events/EVT-A").json()
    assert [c["other_event_id"] for c in event["merge_candidates"]] == ["EVT-B"]
    assert merging_client.post(f"/api/merge-candidates/{pending[0]['candidate_id']}/confirm", json={"reason": "x"}).status_code == 422
    rejected = merging_client.post(
        f"/api/merge-candidates/{pending[0]['candidate_id']}/reject", json={"reason": "Different subjects"}
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"
    assert merging_client.get("/api/events/EVT-A").json()["merge_candidates"] == []
    again = merging_client.post(f"/api/merge-candidates/{pending[0]['candidate_id']}/confirm", json={"reason": "Changed my mind"})
    assert again.status_code == 409
