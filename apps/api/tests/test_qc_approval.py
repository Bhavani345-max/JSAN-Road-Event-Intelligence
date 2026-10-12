"""QC approval through the API (7 October 2026).

An event in QC_PENDING says which QC requirements it does not yet meet; it
can be approved only when it meets them all. An approval is recorded with the
reviewer, the time, the reason and the event version it created.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.sources import SourceRepository
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.telangana_today import TELANGANA_TODAY
from tests.support import FakeConnector, iiit_junction_article

from .test_manual_and_extend import DLF_CLOSURE, undated_article

APPROVE_REASON = "Location checked on the map; dates as the article states"


@pytest.fixture
def client(engine, session):
    """The API holding the real DLF closure article and an undated report."""
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
        assert client.post("/api/ingestion/run").status_code == 200
        yield client


def event_titled(client, title):
    items = client.get("/api/events", params={"limit": 500}).json()["items"]
    return next(item for item in items if item["title"] == title)


def set_status(client, event, status, reason=None):
    return client.post(f"/api/events/{event['event_id']}/status", json={"status": status, "reason": reason})


def confirmed(client, title):
    """The event, confirmed as a road event (VALIDATION_REQUIRED -> QC_PENDING)."""
    event = event_titled(client, title)
    assert set_status(client, event, "QC_PENDING", "Reviewer confirmed").status_code == 200
    return event_titled(client, title)


def place_at_junction(client, event):
    response = client.post(
        f"/api/events/{event['event_id']}/location",
        json={
            "longitude": 78.35223, "latitude": 17.44556, "place_name": "IIIT Junction",
            "reason": "The flyover works are at this junction",
        },
    )  # fmt: skip
    assert response.status_code == 200


def test_only_an_event_in_qc_pending_lists_blockers(client):
    # Still in validation: approval is not the next step, so nothing is listed.
    assert event_titled(client, DLF_CLOSURE)["approval_blockers"] == []
    assert confirmed(client, DLF_CLOSURE)["approval_blockers"] != []


def test_an_approximate_location_blocks_approval_and_says_why(client):
    event = confirmed(client, DLF_CLOSURE)
    assert event["detection"]["location_class"] == "APPROXIMATE"
    assert len(event["approval_blockers"]) == 1
    assert "approximate" in event["approval_blockers"][0]

    response = set_status(client, event, "APPROVED", APPROVE_REASON)
    assert response.status_code == 409
    after = event_titled(client, DLF_CLOSURE)
    assert after["status"] == "QC_PENDING" and after["version"] == event["version"]
    assert after["detection"].get("qc_approval") is None


def test_an_undated_event_lists_every_missing_requirement(client):
    event = confirmed(client, undated_article().title)
    blockers = event["approval_blockers"]
    assert any("no start time" in b for b in blockers)
    assert any("approximate" in b for b in blockers)
    assert set_status(client, event, "APPROVED", APPROVE_REASON).status_code == 409


def test_once_every_requirement_is_met_the_approval_is_recorded(client):
    event = confirmed(client, DLF_CLOSURE)
    place_at_junction(client, event)
    ready = event_titled(client, DLF_CLOSURE)
    assert ready["approval_blockers"] == []

    response = set_status(client, ready, "APPROVED", APPROVE_REASON)
    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "APPROVED"
    assert approved["version"] == ready["version"] + 1
    assert approved["approval_blockers"] == []
    assert approved["detection"]["location_class"] == "QC_APPROVED"
    # How the location was obtained is kept.
    assert approved["detection"]["location"]["method"] == "reviewer_placed"
    approval = approved["detection"]["qc_approval"]
    assert approval["approved_by"] == "local-reviewer"
    assert approval["reason"] == APPROVE_REASON
    assert approval["version"] == approved["version"]
    assert approval["approved_at"]

    history = client.get(f"/api/events/{event['event_id']}").json()["versions"]
    last = history[-1]
    assert last["version"] == approved["version"]
    assert last["status"] == "APPROVED"
    assert last["changed_by"] == "local-reviewer"
    assert last["change_reason"] == APPROVE_REASON
    # Every earlier decision stays in the history.
    assert [v["status"] for v in history][-3:-1] == ["QC_PENDING", "QC_PENDING"]


def test_an_approved_event_cannot_be_approved_again(client):
    event = confirmed(client, DLF_CLOSURE)
    place_at_junction(client, event)
    assert set_status(client, event, "APPROVED", APPROVE_REASON).status_code == 200
    assert set_status(client, event, "APPROVED", APPROVE_REASON).status_code == 409
