"""REI severity: a reviewer's own judgment, assigned during review (8 October 2026).

Never read from text, never copied from the source's severity words, never
required, never assigned to existing events by anything but a reviewer.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.repositories.sources import SourceRepository
from connectors.official import tfl_source
from connectors.official.tfl import to_record as tfl_record
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from packages.event_schema import EventSeverity, ReiEvent
from tests.support import REVIEWER_EMAIL, FakeConnector, iiit_junction_article, sign_in
from tests.unit.test_official_sources import NOW as TFL_NOW
from tests.unit.test_official_sources import TFL, by_id

from .test_manual_and_extend import DLF_CLOSURE


@pytest.fixture(autouse=True)
def _no_minimum_length(monkeypatch):
    monkeypatch.setattr("packages.source_models.road_block.MIN_ROAD_BLOCK_LENGTH_M", 0)


@pytest.fixture
def client(engine, session):
    """The API holding a real Hyderabad article and a real TfL disruption (with TfL's severity)."""
    tfl = tfl_source(scheduled=False)
    SourceRepository(session).sync_registry([DECCAN_CHRONICLE, tfl])
    session.commit()
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=False,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        "deccan-chronicle": lambda: FakeConnector([iiit_junction_article()], source=DECCAN_CHRONICLE),
        "tfl-road-disruptions": lambda: FakeConnector(
            [tfl_record(by_id(TFL, "TIMS-235979"), TFL_NOW)], source=tfl
        ),
    }
    with TestClient(app) as client:
        sign_in(client)
        assert client.post("/api/ingestion/run", params={"source_id": "deccan-chronicle"}).status_code == 200
        assert client.post("/api/ingestion/run", params={"source_id": "tfl-road-disruptions"}).status_code == 200
        yield client


def events(client):
    return client.get("/api/events", params={"view": "validation", "include_hidden": "true", "limit": 500}).json()["items"]


def event_titled(client, title):
    return next(item for item in events(client) if item["title"].startswith(title))


def get(client, event_id):
    return client.get(f"/api/events/{event_id}").json()


# --- model ------------------------------------------------------------------


def test_the_four_values_and_null_are_the_only_severities():
    assert [s.value for s in EventSeverity] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    base = dict(event_id="EVT-SEV000000001", source_id="test", title="T", status="VALIDATION_REQUIRED",
                created_at=TFL_NOW, updated_at=TFL_NOW)  # fmt: skip
    assert ReiEvent(**base).severity is None
    for value in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        assert ReiEvent(**base, severity=value).severity is EventSeverity(value)
    with pytest.raises(ValidationError):
        ReiEvent(**base, severity="SEVERE")


# --- API --------------------------------------------------------------------


def test_new_events_have_no_rei_severity_however_the_source_rates_them(client):
    hyderabad = event_titled(client, DLF_CLOSURE)
    london = event_titled(client, "Vehicle collision")
    assert hyderabad["severity"] is None and hyderabad["detection"]["source_severity"] is None
    # TfL's own word is kept as it is; REI's severity stays empty.
    assert london["severity"] is None and london["detection"]["source_severity"] == "Serious"
    assert london["detection"]["severity_assessment"] is None


def test_a_reviewer_sets_rei_severity_and_it_is_recorded_and_persisted(client):
    london = event_titled(client, "Vehicle collision")
    response = client.post(
        f"/api/events/{london['event_id']}/severity",
        json={"severity": "HIGH", "reason": "Both carriageways affected at the peak"},
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved["severity"] == "HIGH" and saved["version"] == 2
    assessment = saved["detection"]["severity_assessment"]
    assert assessment["severity"] == "HIGH" and assessment["assessed_by"] == REVIEWER_EMAIL
    assert assessment["version"] == 2 and assessment["assessed_at"]
    assert assessment["reason"] == "Both carriageways affected at the peak"
    # Separate from, and leaving untouched, the source's own severity.
    assert saved["detection"]["source_severity"] == "Serious"

    again = get(client, london["event_id"])
    assert again["severity"] == "HIGH"
    assert again["detection"]["source_severity"] == "Serious"
    assert again["status"] == "VALIDATION_REQUIRED"  # severity alone changes no status
    assert again["versions"][-1]["change_reason"].startswith("REI severity set to HIGH by a reviewer.")
    assert again["versions"][-1]["changed_by"] == REVIEWER_EMAIL


def test_an_invalid_severity_is_rejected(client):
    event = event_titled(client, DLF_CLOSURE)
    assert client.post(f"/api/events/{event['event_id']}/severity", json={"severity": "SEVERE"}).status_code == 422
    assert client.post(f"/api/events/{event['event_id']}/severity", json={"severity": "high"}).status_code == 422
    assert client.post(f"/api/events/{event['event_id']}/status", json={"status": "QC_PENDING", "severity": "EXTREME"}).status_code == 422
    assert get(client, event["event_id"])["severity"] is None
    assert client.post("/api/events/NOPE/severity", json={"severity": "LOW"}).status_code == 404


def test_severity_can_be_given_with_a_review_decision_in_one_version(client):
    event = event_titled(client, DLF_CLOSURE)
    response = client.post(
        f"/api/events/{event['event_id']}/status",
        json={"status": "QC_PENDING", "reason": "Reviewer confirmed", "severity": "MEDIUM"},
    )
    assert response.status_code == 200
    saved = response.json()
    assert (saved["status"], saved["severity"], saved["version"]) == ("QC_PENDING", "MEDIUM", 2)
    history = get(client, event["event_id"])["versions"]
    assert [v["version"] for v in history] == [1, 2]
    assert history[-1]["change_reason"] == "Reviewer confirmed REI severity MEDIUM."
    # A later decision without a severity leaves the assessment as it was.
    back = client.post(f"/api/events/{event['event_id']}/status", json={"status": "VALIDATION_REQUIRED"})
    assert back.json()["severity"] == "MEDIUM"
    assert back.json()["detection"]["severity_assessment"]["version"] == 2


def test_a_rejected_event_cannot_be_given_a_severity(client):
    event = event_titled(client, DLF_CLOSURE)
    assert client.post(f"/api/events/{event['event_id']}/status", json={"status": "REJECTED"}).status_code == 200
    response = client.post(f"/api/events/{event['event_id']}/severity", json={"severity": "LOW"})
    assert response.status_code == 409 and "REJECTED" in response.json()["detail"]


def test_reprocessing_never_touches_a_reviewers_severity(client, session):
    from app.services.reprocess_service import reprocess_stored_evidence
    from services.extraction import KeywordClassifier
    from services.geo_resolution import default_resolver

    event = event_titled(client, DLF_CLOSURE)
    assert client.post(f"/api/events/{event['event_id']}/severity", json={"severity": "CRITICAL"}).status_code == 200
    reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    after = get(client, event["event_id"])
    assert after["severity"] == "CRITICAL"
    assert after["detection"]["severity_assessment"]["severity"] == "CRITICAL"


def test_the_severity_filter_uses_rei_severity_only(client):
    london = event_titled(client, "Vehicle collision")
    # TfL says "Serious"; nothing maps that to REI's HIGH.
    assert client.get("/api/events", params={"view": "validation", "include_hidden": "true", "severity": "HIGH"}).json()["total"] == 0
    client.post(f"/api/events/{london['event_id']}/severity", json={"severity": "HIGH"})
    found = client.get("/api/events", params={"view": "validation", "include_hidden": "true", "severity": "HIGH"}).json()
    assert [e["event_id"] for e in found["items"]] == [london["event_id"]]
