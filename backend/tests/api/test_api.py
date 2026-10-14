from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Event
from tests.support import TEST_SOURCE, FakeConnector


def ingest(client):
    response = client.post("/api/ingestion/run", params={"source_id": TEST_SOURCE.source_id})
    assert response.status_code == 200
    return response.json()["results"][0]


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_a_new_installation_has_no_events_at_all(client):
    """Nothing is seeded: until a source is ingested, there is nothing to show."""
    assert client.get("/api/events").json() == {"items": [], "total": 0}


def test_server_event_views_filter_before_count_and_pagination(client, session):
    ingest(client)
    # Undated reports are available for validation, not inferred to be active
    # from publication/retrieval or ingestion time.
    assert client.get("/api/events").json()["total"] == 0
    rows = list(session.scalars(select(Event).order_by(Event.event_id)))
    now = datetime.now(timezone.utc)
    rows[0].status = "APPROVED"
    rows[0].start_time = now - timedelta(hours=1)
    rows[0].end_time = now + timedelta(hours=1)
    rows[1].status = "APPROVED"
    rows[1].start_time = now + timedelta(days=1)
    rows[1].end_time = now + timedelta(days=2)
    rows[2].start_time = now + timedelta(days=1)
    rows[2].end_time = now + timedelta(days=2)
    session.commit()

    default = client.get("/api/events", params={"limit": 1, "offset": 0}).json()
    assert default["total"] == 2 and len(default["items"]) == 1
    assert client.get("/api/events", params={"view": "current"}).json()["total"] == 1
    assert client.get("/api/events", params={"view": "upcoming"}).json()["total"] == 1
    assert client.get("/api/events", params={"view": "validation"}).json()["total"] == 1
    assert client.get("/api/events", params={"view": "history"}).json()["total"] == 0
    page = client.get("/api/events", params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 2 and len(page["items"]) == 1

    rows[0].end_time = now - timedelta(seconds=1)
    session.commit()
    history = client.get("/api/events", params={"view": "history"}).json()
    assert history["total"] == 1
    assert history["items"][0]["status"] == "APPROVED"

    rows[2].status = "REJECTED"
    session.commit()
    rejected = client.get("/api/events", params={"view": "rejected"}).json()
    assert rejected["total"] == 1
    assert rejected["items"][0]["event_id"] == rows[2].event_id


def test_ingestion_creates_real_events_from_the_source(client):
    result = ingest(client)
    assert result | {"started_at": None, "finished_at": None} == {
        "source_id": "test-news",
        "status": "ok",
        "error": None,
        "fetched": 7,
        "new_artifacts": 6,
        "duplicates": 1,
        "revised": 0,
        "relevant": 3,
        "events_created": 3,
        "started_at": None,
        "finished_at": None,
    }

    body = client.get("/api/events?view=validation").json()
    assert body["total"] == 3
    # Most recently published first. The article with no publication date is
    # ordered by when it was found (now).
    assert [event["title"].split()[0] for event in body["items"]] == ["Road", "Traffic", "Heavy"]


def test_real_event_response_shape(client):
    ingest(client)
    events = client.get("/api/events?view=validation").json()["items"]
    event = next(e for e in events if e["title"].startswith("Traffic diversions at Lakeview"))

    assert event["event_id"].startswith("EVT-")
    assert event["status"] == "VALIDATION_REQUIRED"
    assert "is_demo" not in event
    assert event["source_id"] == "test-news"
    assert event["source"]["source_name"] == "Example Daily"
    assert event["source_reference"] == "https://news.example.com/traffic-diversions-lakeview-junction"
    assert event["event_type"] == "TRAFFIC_DIVERSION"
    assert event["city"] == "Hyderabad"
    assert event["affected_road"] == "Lakeview Junction; Station Road"
    assert event["detection"]["method"] == "keyword_rules"
    assert event["version"] == 1
    # Not provided by the article, so not present.
    for name in ("start_time", "end_time", "severity", "direction", "geometry", "confidence"):
        assert event[name] is None, name
    assert event["evidence"]["url"] == event["source_reference"]
    assert event["evidence"]["published_at"] == "2026-10-01T06:30:00Z"
    assert event["evidence"]["retrieved_at"] == "2026-10-02T08:00:00Z"
    assert len(event["evidence"]["content_hash"]) == 64


def test_repeated_ingestion_does_not_duplicate_events(client):
    ingest(client)
    second = ingest(client)
    assert second["new_artifacts"] == 0
    assert second["duplicates"] == 7
    assert second["events_created"] == 0
    assert client.get("/api/events?view=validation").json()["total"] == 3


def test_event_filters(client):
    ingest(client)
    assert client.get("/api/events", params={"view": "validation", "source_id": "test-news"}).json()["total"] == 3
    assert client.get("/api/events", params={"view": "validation", "source_id": "telangana-today"}).json()["total"] == 0
    assert client.get("/api/events", params={"view": "validation", "status": "VALIDATION_REQUIRED"}).json()["total"] == 3
    assert client.get("/api/events", params={"view": "validation", "status": "ACTIVE"}).json()["total"] == 0
    page = client.get("/api/events", params={"view": "validation", "limit": 2, "offset": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get("/api/events", params={"view": "validation", "status": "NOT_A_STATUS"}).status_code == 422


def test_event_detail_includes_version_history(client):
    ingest(client)
    event_id = client.get("/api/events?view=validation").json()["items"][0]["event_id"]
    detail = client.get(f"/api/events/{event_id}").json()
    assert detail["event_id"] == event_id
    assert [(v["version"], v["status"], v["changed_by"]) for v in detail["versions"]] == [
        (1, "VALIDATION_REQUIRED", "ingestion")
    ]
    assert client.get("/api/events/EVT-DOES-NOT-EXIST").status_code == 404


def test_reviewer_can_reject_or_send_to_qc(client):
    ingest(client)
    first, second = client.get("/api/events?view=validation").json()["items"][:2]

    rejected = client.post(
        f"/api/events/{first['event_id']}/status",
        json={"status": "REJECTED", "reason": "Not a road event"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["version"] == 2

    confirmed = client.post(f"/api/events/{second['event_id']}/status", json={"status": "QC_PENDING"})
    assert confirmed.json()["status"] == "QC_PENDING"

    history = client.get(f"/api/events/{first['event_id']}").json()["versions"]
    assert [(v["version"], v["status"]) for v in history] == [
        (1, "VALIDATION_REQUIRED"),
        (2, "REJECTED"),
    ]
    assert history[1]["change_reason"] == "Not a road event"
    assert client.post("/api/events/NOPE/status", json={"status": "REJECTED"}).status_code == 404


def test_unlocated_event_cannot_be_approved_or_published(client):
    ingest(client)
    event_id = client.get("/api/events?view=validation").json()["items"][0]["event_id"]
    url = f"/api/events/{event_id}/status"

    # No shortcut from validation straight to a live status.
    assert client.post(url, json={"status": "ACTIVE"}).status_code == 409
    assert client.post(url, json={"status": "APPROVED"}).status_code == 409

    # Even after QC, approval needs a resolved location and a start time.
    assert client.post(url, json={"status": "QC_PENDING"}).status_code == 200
    blocked = client.post(url, json={"status": "APPROVED"})
    assert blocked.status_code == 409
    assert "resolved location" in blocked.json()["detail"]
    assert client.get(f"/api/events/{event_id}").json()["status"] == "QC_PENDING"


def test_source_records_successful_poll_and_counts(client):
    ingest(client)
    source = client.get("/api/sources/test-news").json()
    assert source["last_poll_at"] is not None
    assert source["last_success_at"] == source["last_poll_at"]
    assert source["last_failure_at"] is None
    assert source["artifact_count"] == 6
    assert source["event_count"] == 3
    assert client.get("/api/sources/unknown").status_code == 404


def test_failed_fetch_is_reported_and_recorded_on_the_source(client, app):
    app.state.ingestion_service.connector_factories["test-news"] = lambda: FakeConnector(
        [], error="feed unreachable"
    )
    result = ingest(client)
    assert result["status"] == "failed"
    assert result["error"] == "feed unreachable"
    assert result["events_created"] == 0

    source = client.get("/api/sources/test-news").json()
    assert source["last_failure_at"] is not None
    assert source["last_success_at"] is None
    assert source["last_error"] == "feed unreachable"
    assert client.get("/api/events?view=validation").json()["total"] == 0


def test_ingestion_of_unknown_source_is_404(client):
    assert client.post("/api/ingestion/run", params={"source_id": "nope"}).status_code == 404
    # A researched source that is not connected has nothing to fetch.
    response = client.post("/api/ingestion/run", params={"source_id": "hyderabad-traffic-police"})
    assert response.status_code == 404
