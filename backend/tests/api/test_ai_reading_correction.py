"""Setting aside AI readings made with the wrong rules (decision 0033).

Reproduces 16 October 2026 on an in-memory database: an AI pass with another
city's rules rejects an event; the correction sets the reading aside and
re-derives the event with its own city's rules, keeping every version; the
undo puts back exactly what was there.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, SourceArtifact
from app.repositories.sources import SourceRepository
from app.services.ai_reading_correction import (
    rederive_events,
    reject_again,
    restore_readings,
    supersede_readings,
)
from app.services.reprocess_service import AI_CHANGED_BY, rederive_artifact
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.cities import get_city
from tests.support import FakeConnector, khajaguda_article

REASON = "read with Hyderabad's rules by an API running older code"
AT = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
WRONG_READING = {"stage": "triage", "is_road_event": False, "model": "fake/model", "read_at": "2026-10-16T10:25:00Z"}


@pytest.fixture
def app(engine, session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY])
    session.commit()
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_migrate=False,
        ingestion_scheduler_enabled=False,
        event_matching_after_ingestion=False,
    )
    app = create_app(settings, engine=engine)
    service = app.state.ingestion_service
    service.connector_factories = {
        "telangana-today": lambda: FakeConnector([khajaguda_article()], source=TELANGANA_TODAY)
    }
    service.run_source("telangana-today")
    return app


def _wrongly_reject(app):
    """What the older API did: re-derive with another city's rules, as an AI reading."""
    service = app.state.ingestion_service
    with app.state.session_factory() as session:
        artifact = session.scalar(select(SourceArtifact))
        row = session.scalar(select(Event))
        mumbai = get_city("mumbai")
        outcome, _ = rederive_artifact(
            session, artifact, row,
            classifier=service.classifiers["mumbai"], resolver=service.resolvers["mumbai"], city=mumbai,
            reason="AI reading (fake/model)", changed_by=AI_CHANGED_BY,
        )  # fmt: skip
        artifact.classification_details = {**artifact.classification_details, "ai": WRONG_READING}
        session.commit()
        assert outcome == "rejected"
        return artifact.artifact_id, row.event_id


def _state(app, artifact_id, event_id):
    with app.state.session_factory() as session:
        artifact = session.get(SourceArtifact, artifact_id)
        row = session.get(Event, event_id)
        versions = [(v.version, v.status, v.changed_by) for v in row.versions]
        return artifact.classification, dict(artifact.classification_details), row.status, versions


def test_the_reading_is_set_aside_and_the_event_restored_with_its_own_citys_rules(app):
    artifact_id, event_id = _wrongly_reject(app)
    before = _state(app, artifact_id, event_id)
    assert before[0] == "NOT_RELEVANT" and before[2] == "REJECTED"

    with app.state.session_factory() as session:
        readings = supersede_readings(session, [artifact_id], reason=REASON, at=AT)
        session.flush()
        events = rederive_events(session, app.state.ingestion_service, [event_id], reason=f"keyword rules ({REASON})")
        session.commit()
    assert readings.changed == [artifact_id] and events.changed == [event_id]

    classification, details, status, versions = _state(app, artifact_id, event_id)
    assert status == "VALIDATION_REQUIRED" and classification == "RELEVANT_TRAFFIC_ARTICLE"
    assert details["in_scope_city"] == "Hyderabad"
    # Every version kept: created, wrongly rejected, restored.
    assert versions == [(1, "VALIDATION_REQUIRED", "ingestion"), (2, "REJECTED", AI_CHANGED_BY),
                        (3, "VALIDATION_REQUIRED", "reprocessing")]  # fmt: skip
    # The wrong reading is kept, with why, when and the classification it came with.
    assert "ai" not in details
    (entry,) = details["ai_superseded"]
    assert entry["reading"] == WRONG_READING and entry["reason"] == REASON
    assert entry["superseded_at"] == AT.isoformat() and entry["classification_at_the_time"] == "NOT_RELEVANT"


def test_the_correction_can_be_undone_exactly(app):
    artifact_id, event_id = _wrongly_reject(app)
    before = _state(app, artifact_id, event_id)
    with app.state.session_factory() as session:
        supersede_readings(session, [artifact_id], reason=REASON, at=AT)
        session.flush()
        rederive_events(session, app.state.ingestion_service, [event_id], reason="keyword rules")
        session.commit()

    with app.state.session_factory() as session:
        assert reject_again(session, [event_id], reason=f"Correction undone: {REASON}").changed == [event_id]
        assert restore_readings(session, [artifact_id], reason=REASON).changed == [artifact_id]
        session.commit()

    classification, details, status, versions = _state(app, artifact_id, event_id)
    # The article is exactly as it was before the correction.
    assert (classification, details) == before[:2]
    # The event is rejected again, by a further version; nothing was removed.
    assert status == "REJECTED" and [v[0] for v in versions] == [1, 2, 3, 4]


def test_an_event_not_rejected_by_an_ai_reading_is_left_alone(app):
    with app.state.session_factory() as session:
        row = session.scalar(select(Event))
        result = rederive_events(session, app.state.ingestion_service, [row.event_id], reason="keyword rules")
        session.commit()
        assert result.changed == [] and "not an AI reading's rejection" in result.skipped[row.event_id]
        assert [v.version for v in row.versions] == [1]


def test_an_article_without_a_reading_is_skipped_not_changed(app):
    with app.state.session_factory() as session:
        artifact = session.scalar(select(SourceArtifact))
        before = dict(artifact.classification_details)
        result = supersede_readings(session, [artifact.artifact_id], reason=REASON, at=AT)
        assert result.changed == [] and result.skipped == {artifact.artifact_id: "no AI reading"}
        assert artifact.classification_details == before
