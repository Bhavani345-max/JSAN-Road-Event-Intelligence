"""What a reviewer can do beyond accepting or rejecting: extend an event, and add one by hand."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, SourceArtifact
from app.repositories.sources import SourceRepository
from app.services.reprocess_service import reprocess_stored_evidence
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.telangana_today import TELANGANA_TODAY
from services.extraction import KeywordClassifier
from services.geo_resolution import default_resolver
from tests.support import REVIEWER_EMAIL, FakeConnector, iiit_junction_article, khajaguda_article, sign_in

DLF_CLOSURE = "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works"
MANUAL = {
    "title": "DLF Road closed between Gate No.1 and Gachibowli Traffic PS",
    "event_type": "PLANNED_ROAD_CLOSURE",
    "description": "Barricades in place; traffic diverted via Gachibowli Junction.",
    "place": "dlf road",
    "start_date": "2026-07-01",
    "end_date": "2026-12-31",
    "reference_url": "https://x.com/CYBTRAFFIC/status/1",
    "basis": "Seen on site on 5 October 2026",
}


def undated_article():
    """A real kind of report: a named place and a road signal, but no dates."""
    title = "Waterlogging at Tolichowki slows traffic in Hyderabad"
    return khajaguda_article().model_copy(
        update={
            "external_id": "https://news.example.com/tolichowki",
            "url": "https://news.example.com/tolichowki",
            "title": title,
            "summary": None,
            "content_text": None,
            "raw": {"title": title, "summary_html": "", "content_html": "", "categories": ["Hyderabad"]},
        }
    )


@pytest.fixture
def client(engine, session):
    """The API as it runs for real, holding the DLF closure and an undated report."""
    SourceRepository(session).sync_registry([TELANGANA_TODAY, DECCAN_CHRONICLE])
    session.commit()
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        "telangana-today": lambda: FakeConnector([undated_article()], source=TELANGANA_TODAY),
        "deccan-chronicle": lambda: FakeConnector([iiit_junction_article()], source=DECCAN_CHRONICLE),
    }
    with TestClient(app) as client:
        sign_in(client)
        assert client.post("/api/ingestion/run").status_code == 200
        yield client


def event_titled(client, title):
    items = client.get("/api/events", params={"view": "validation", "limit": 500}).json()["items"]
    return next(item for item in items if item["title"] == title)


def extend(client, event, **body):
    return client.post(f"/api/events/{event['event_id']}/extend", json=body)


# --- extending an event ----------------------------------------------------------


def test_a_reviewer_can_extend_a_closure_past_the_end_its_article_stated(client):
    closure = event_titled(client, DLF_CLOSURE)
    assert closure["end_time"].startswith("2026-09-28T18:29:59")  # 28 September, IST

    response = extend(
        client, closure, end_date="2026-12-31", reason="Still closed on 5 October, seen on site"
    )
    assert response.status_code == 200
    extended = response.json()
    assert extended["end_time"].startswith("2026-12-31T18:29:59")  # the whole of 31 December, IST
    assert extended["start_time"] == closure["start_time"]
    assert extended["version"] == closure["version"] + 1
    assert extended["status"] == "VALIDATION_REQUIRED"  # extending is not approving

    # What the article said stays on record next to what the reviewer changed.
    detection = extended["detection"]
    assert detection["stated_period"] == "for a period of 90 days starting from July 1, 2026"
    revision = detection["period_revision"]
    assert revision["previous_end"].startswith("2026-09-28T18:29:59")
    assert revision["reason"] == "Still closed on 5 October, seen on site"
    assert revision["revised_by"] == REVIEWER_EMAIL

    history = client.get(f"/api/events/{closure['event_id']}").json()["versions"]
    assert history[-1]["changed_by"] == REVIEWER_EMAIL
    assert history[-1]["change_reason"] == (
        "Extended until 2026-12-31. Still closed on 5 October, seen on site"
    )


def test_an_event_can_be_extended_until_further_notice_once(client):
    closure = event_titled(client, DLF_CLOSURE)
    response = extend(client, closure, end_date=None, reason="No reopening date announced")
    assert response.status_code == 200 and response.json()["end_time"] is None
    assert "further notice" in client.get(f"/api/events/{closure['event_id']}").json()[
        "versions"
    ][-1]["change_reason"]

    again = extend(client, closure, end_date=None, reason="No reopening date announced")
    assert again.status_code == 409 and "already" in again.json()["detail"]


@pytest.mark.parametrize(
    "end_date, problem",
    [
        ("2026-09-28", "later than the current one (2026-09-28)"),
        ("2026-08-01", "later than the current one"),
        ("2026-06-01", "before the event starts"),
    ],
)
def test_an_extension_must_actually_extend(client, end_date, problem):
    closure = event_titled(client, DLF_CLOSURE)
    response = extend(client, closure, end_date=end_date, reason="Still closed, seen on site")
    assert response.status_code == 409 and problem in response.json()["detail"]
    assert event_titled(client, DLF_CLOSURE)["version"] == closure["version"]


def test_an_extension_needs_a_reason_and_an_existing_open_event(client):
    closure = event_titled(client, DLF_CLOSURE)
    assert extend(client, closure, end_date="2026-12-31").status_code == 422
    assert extend(client, closure, end_date="2026-12-31", reason="ok").status_code == 422
    missing = client.post(
        "/api/events/EVT-NOPE/extend", json={"end_date": "2026-12-31", "reason": "Still closed"}
    )
    assert missing.status_code == 404

    client.post(f"/api/events/{closure['event_id']}/status", json={"status": "REJECTED"})
    rejected = extend(client, closure, end_date="2026-12-31", reason="Still closed, seen on site")
    assert rejected.status_code == 409 and "REJECTED" in rejected.json()["detail"]


def test_an_undated_report_can_be_given_an_end_but_not_an_open_one(client):
    report = event_titled(client, undated_article().title)
    assert report["start_time"] is None and report["end_time"] is None

    open_ended = extend(client, report, end_date=None, reason="Water still standing today")
    assert open_ended.status_code == 409 and "no start date" in open_ended.json()["detail"]

    dated = extend(client, report, end_date="2026-10-20", reason="Water still standing today")
    assert dated.status_code == 200
    assert dated.json()["end_time"].startswith("2026-10-20T18:29:59")
    assert dated.json()["detection"]["period_revision"]["previous_end"] is None


def test_reprocessing_leaves_an_extended_event_as_the_reviewer_left_it(client, session):
    closure = event_titled(client, DLF_CLOSURE)
    extend(client, closure, end_date="2026-12-31", reason="Still closed, seen on site")

    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert (result.updated, result.rejected) == (0, 0)
    assert event_titled(client, DLF_CLOSURE)["end_time"].startswith("2026-12-31")


# --- adding an event by hand ---------------------------------------------------------


def test_a_reviewer_can_add_an_event_no_source_reported(client, session):
    response = client.post("/api/events", json=MANUAL)
    assert response.status_code == 201
    event = response.json()

    assert event["title"] == MANUAL["title"]
    assert event["event_type"] == "PLANNED_ROAD_CLOSURE"
    assert event["description"] == MANUAL["description"]
    assert event["affected_road"] == "dlf road"  # as the reviewer wrote it
    assert event["source_reference"] == MANUAL["reference_url"]
    assert event["start_time"].startswith("2026-06-30T18:30:00")  # 1 July, 00:00 IST
    assert event["end_time"].startswith("2026-12-31T18:29:59")
    # Entered by a person, but still a lead until it has been through review.
    assert event["status"] == "VALIDATION_REQUIRED"
    assert event["severity"] is None and event["confidence"] is None
    assert event["source"] == {
        "source_id": "manual-entry", "source_name": "Manual entry", "source_type": "MANUAL",
        # A manual entry is no kind of source and has no tier.
        "source_class": None, "source_tier": None, "discovery_only": False,
    }  # fmt: skip

    detection = event["detection"]
    assert detection["method"] == "manual_entry" and detection["matched_keywords"] == []
    assert detection["basis"] == "Seen on site on 5 October 2026"
    # Located like any event: by a known place name, at its OpenStreetMap position.
    assert detection["location"]["place_name"] == "DLF road"
    assert detection["location"]["found_in"] == "entry"
    assert detection["location"]["reference"].startswith("OpenStreetMap way/")
    longitude, latitude = event["geometry"]["coordinates"]
    assert 78.35 < longitude < 78.37 and 17.44 < latitude < 17.46

    # The entry itself is kept as evidence, exactly as typed.
    stored = session.get(SourceArtifact, event["evidence"]["artifact_id"])
    assert stored.classification == "MANUAL_ENTRY"
    assert stored.raw_content["basis"] == MANUAL["basis"]
    assert stored.raw_content["entered_by"] == REVIEWER_EMAIL
    assert stored.raw_content["place"] == "dlf road"

    history = client.get(f"/api/events/{event['event_id']}").json()["versions"]
    assert [(v["version"], v["changed_by"]) for v in history] == [(1, REVIEWER_EMAIL)]
    assert history[0]["change_reason"] == "Entered manually. Basis: Seen on site on 5 October 2026"


def test_a_manual_event_is_listed_filtered_and_searched_like_any_other(client):
    event = client.post("/api/events", json=MANUAL).json()
    listed = client.get("/api/events", params={"view": "validation", "source_id": "manual-entry"}).json()
    assert [item["event_id"] for item in listed["items"]] == [event["event_id"]]
    found = client.get("/api/events", params={"view": "validation", "q": "barricades gate"}).json()
    assert [item["event_id"] for item in found["items"]] == [event["event_id"]]
    # And it can be reviewed and extended like any other.
    assert client.post(
        f"/api/events/{event['event_id']}/status", json={"status": "QC_PENDING"}
    ).status_code == 200
    assert extend(client, event, end_date="2027-03-31", reason="Works extended").status_code == 200


def test_only_the_title_and_the_basis_are_needed(client):
    response = client.post(
        "/api/events",
        json={"title": "Road cave-in near the market", "basis": "Reported by a JSAN colleague"},
    )
    assert response.status_code == 201
    event = response.json()
    for name in ("event_type", "description", "affected_road", "start_time", "end_time", "geometry"):
        assert event[name] is None, name
    assert event["detection"]["location"] is None


def test_a_place_that_is_unknown_or_not_one_spot_does_not_locate_the_event(client):
    for place in ("Lakeview Junction", "Indira Nagar"):  # invented; several in the city
        event = client.post("/api/events", json={**MANUAL, "place": place}).json()
        assert event["geometry"] is None and event["detection"]["location"] is None
        assert event["affected_road"] == place


def test_a_place_can_be_given_in_a_phrase(client):
    event = client.post(
        "/api/events", json={**MANUAL, "place": "service road at khajaguda junction"}
    ).json()
    assert event["detection"]["location"]["place_name"] == "Khajaguda Jn"
    assert event["affected_road"] == "service road at khajaguda junction"


@pytest.mark.parametrize(
    "change",
    [
        {"basis": None},
        {"basis": "ok"},
        {"title": "Hi"},
        {"end_date": "2026-06-01"},  # before the start
        {"event_type": "PARADE"},
        {"reference_url": "see WhatsApp"},
    ],
)
def test_an_incomplete_or_inconsistent_entry_is_refused(client, change):
    body = {key: value for key, value in {**MANUAL, **change}.items() if value is not None}
    assert client.post("/api/events", json=body).status_code == 422
    assert client.get("/api/events", params={"view": "validation", "source_id": "manual-entry"}).json()["total"] == 0


def test_reprocessing_never_touches_a_manual_entry(client, session):
    event = client.post("/api/events", json=MANUAL).json()
    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert (result.created, result.updated, result.rejected) == (0, 0, 0)

    row = session.get(Event, event["event_id"])
    session.refresh(row)
    assert row.status == "VALIDATION_REQUIRED" and row.version == 1
    stored = session.scalars(
        select(SourceArtifact).where(SourceArtifact.source_id == "manual-entry")
    ).one()
    assert stored.classification == "MANUAL_ENTRY"


def test_manual_entry_is_a_source_that_is_never_polled(client):
    source = client.get("/api/sources/manual-entry").json()
    assert source["integration_status"] == "MANUAL_ONLY" and source["active"] is False
    assert source["source_tier"] is None
    client.post("/api/events", json=MANUAL)
    run = client.post("/api/ingestion/run").json()["results"]
    assert "manual-entry" not in {result["source_id"] for result in run}
    assert client.post("/api/ingestion/run", params={"source_id": "manual-entry"}).status_code == 404
    assert client.get("/api/sources/manual-entry").json()["event_count"] == 1


# --- place suggestions ------------------------------------------------------------------


def test_places_are_suggested_as_the_reviewer_types(client):
    names = [place["name"] for place in client.get("/api/places", params={"q": "khajag"}).json()]
    assert "Khajaguda Jn" in names and "Khajaguda" in names
    assert len(names) <= 8
    # A name that starts with what was typed comes before one that merely contains it.
    dlf = client.get("/api/places", params={"q": "dlf"}).json()
    assert dlf[0] == {"name": "DLF road", "kind": "road"}


def test_only_places_with_a_position_are_suggested(client):
    names = [p["name"] for p in client.get("/api/places", params={"q": "indira nagar"}).json()]
    assert "Indira Nagar" not in names  # several in the city: it would locate nothing
    assert client.get("/api/places", params={"q": "zzzz"}).json() == []
    assert client.get("/api/places", params={"q": "k"}).status_code == 422


# --- correcting where an event is -----------------------------------------------------

IIIT_JUNCTION = {
    "longitude": 78.35190,
    "latitude": 17.44550,
    "place_name": "IIIT Junction",
    "reason": "Pillars are going up at the junction itself, seen on site",
}


def relocate(client, event, **change):
    return client.post(f"/api/events/{event['event_id']}/location", json={**IIIT_JUNCTION, **change})


def test_a_reviewer_can_put_an_event_at_the_exact_spot(client):
    closure = event_titled(client, DLF_CLOSURE)
    before = closure["detection"]["location"]
    assert before["method"] == "named_place"  # where the article's wording put it

    response = relocate(client, closure)
    assert response.status_code == 200
    moved = response.json()
    assert moved["geometry"] == {"type": "Point", "coordinates": [78.3519, 17.4455]}
    assert moved["version"] == closure["version"] + 1
    assert moved["status"] == closure["status"]  # relocating is not approving

    location = moved["detection"]["location"]
    assert location["method"] == "reviewer_placed"
    assert location["place_name"] == "IIIT Junction" and location["precision"] == "place"
    assert location["reference"] == f"placed on the map by {REVIEWER_EMAIL}"
    revision = moved["detection"]["location_revision"]
    assert revision["previous_place_name"] == before["place_name"]
    assert revision["reason"] == IIIT_JUNCTION["reason"]
    assert revision["revised_by"] == REVIEWER_EMAIL
    # Everything else the article gave is untouched.
    assert moved["detection"]["stated_period"] == closure["detection"]["stated_period"]
    assert moved["start_time"] == closure["start_time"]

    history = client.get(f"/api/events/{closure['event_id']}").json()["versions"]
    assert history[-1]["changed_by"] == REVIEWER_EMAIL
    assert history[-1]["change_reason"].startswith(
        "Located at IIIT Junction (17.44550, 78.35190) by a reviewer. Pillars"
    )


def test_an_event_that_was_not_located_can_be_placed(client):
    event = client.post(
        "/api/events", json={"title": "Road cave-in near the market", "basis": "Seen on site"}
    ).json()
    assert event["geometry"] is None
    placed = relocate(client, event).json()
    assert placed["geometry"]["type"] == "Point"
    assert placed["detection"]["location_revision"]["previous_place_name"] is None


@pytest.mark.parametrize(
    "change, status",
    [
        ({"latitude": 28.61, "longitude": 77.21}, 409),  # Delhi
        ({"latitude": 95}, 422),
        ({"place_name": ""}, 422),
        ({"reason": "ok"}, 422),
    ],
)
def test_a_spot_must_be_in_hyderabad_and_explained(client, change, status):
    closure = event_titled(client, DLF_CLOSURE)
    response = relocate(client, closure, **change)
    assert response.status_code == status
    if status == 409:
        assert "outside Greater Hyderabad" in response.json()["detail"]
    assert event_titled(client, DLF_CLOSURE)["version"] == closure["version"]


def test_relocating_needs_an_existing_open_event(client):
    assert client.post("/api/events/EVT-NOPE/location", json=IIIT_JUNCTION).status_code == 404
    closure = event_titled(client, DLF_CLOSURE)
    client.post(f"/api/events/{closure['event_id']}/status", json={"status": "REJECTED"})
    assert relocate(client, closure).status_code == 409


def test_reprocessing_keeps_the_spot_a_reviewer_chose(client, session):
    closure = event_titled(client, DLF_CLOSURE)
    relocate(client, closure)
    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert result.updated == 0
    assert event_titled(client, DLF_CLOSURE)["detection"]["location"]["method"] == "reviewer_placed"


def test_an_extension_is_a_whole_day_in_the_events_own_city(session):
    """A London event extended to 31 December ends at 23:59:59 London time, not India's."""
    from datetime import date, datetime, timedelta, timezone

    from app.repositories.events import EventRepository
    from app.repositories.sources import SourceRepository
    from app.services.review_service import extend_event
    from connectors.official import tfl_source
    from packages.event_schema import EventDetection, EventStatus, ReiEvent

    SourceRepository(session).sync_registry([tfl_source(scheduled=False)])
    start = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    EventRepository(session).add(
        ReiEvent(
            event_id="EVT-LONDON", source_id="tfl-road-disruptions", title="Works", city="London",
            start_time=start, end_time=start + timedelta(days=7),
            status=EventStatus.VALIDATION_REQUIRED, created_at=start, updated_at=start,
            detection=EventDetection(method="source_provided", matched_keywords=[]),
        ),  # fmt: skip
        artifact_id=None, change_reason="Created", changed_by="ingestion",
    )  # fmt: skip
    session.commit()
    row = extend_event(session, "EVT-LONDON", date(2026, 12, 31), "Seen still closed on site")
    # London is on GMT in December: the last second of the day is 23:59:59 UTC.
    assert row.end_time == datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
