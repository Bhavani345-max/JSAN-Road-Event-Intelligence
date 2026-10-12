"""The AI reading service on a real (in-memory) database, with a fake model.

The fake answers like a model would, keyed by headline. Nothing reaches OpenRouter.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, SourceArtifact
from app.repositories.sources import SourceRepository
from app.services.ai_reading_service import AiReadingService
from app.services.reprocess_service import reprocess_stored_evidence
from connectors.rss.telangana_today import TELANGANA_TODAY
from services.ai_reading import ChatResult
from tests.support import FakeConnector, khajaguda_article
from tests.unit.test_ai_reading import TITLE, cycling_record, full_answer

KHAJAGUDA = khajaguda_article().title


class FakeModel:
    """Answers the triage and full prompts from tables keyed by headline."""

    def __init__(self, triage: dict, full: dict, remaining: int | None = None) -> None:
        self.triage, self.full, self.remaining = triage, full, remaining
        self.requests_sent = 0
        self.prompts: list[str] = []

    def free_requests_remaining(self):
        return self.remaining

    def chat_json(self, system: str, user: str, *, max_tokens: int) -> ChatResult:
        self.requests_sent += 1
        self.prompts.append(user)
        items = json.loads(user.split("Articles:\n", 1)[1])
        table = self.full if "Allowed place roles" in user else self.triage
        answers = [{**table[item["title"]], "id": item["id"]} for item in items if item["title"] in table]
        return ChatResult(content={"articles": answers}, model="fake/model")


def model() -> FakeModel:
    cycling_full = full_answer()["articles"][0]
    return FakeModel(
        triage={
            TITLE: {"road_event": True, "intent": "MARATHON", "why": "Tank Bund closed"},
            KHAJAGUDA: {"road_event": False, "why": "The model disagrees."},
        },
        full={TITLE: cycling_full},
    )


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
        openrouter_api_key="test-key",
        ai_model="fake/model",
    )
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        "telangana-today": lambda: FakeConnector(
            [khajaguda_article(), cycling_record()], source=TELANGANA_TODAY
        ),
    }
    app.state.ingestion_service.run_source("telangana-today")
    return app


def reader(app, tmp_path, fake: FakeModel, **settings) -> AiReadingService:
    merged = app.state.settings.model_copy(update=settings)
    return AiReadingService(
        app.state.session_factory,
        merged,
        app.state.ingestion_service,
        client_factory=lambda: fake,
        usage_path=tmp_path / "usage.json",
    )


def events_by_title(app) -> dict[str, Event]:
    with app.state.session_factory() as session:
        events = {event.title: event for event in session.scalars(select(Event)).unique()}
        for event in events.values():
            event.versions  # loaded while the session is open
        return events


def test_ai_reading_finds_the_event_the_keywords_missed_and_annotates_the_other(app, tmp_path):
    before = events_by_title(app)
    assert KHAJAGUDA in before and TITLE not in before

    fake = model()
    result = reader(app, tmp_path, fake).run()

    assert result.error is None
    assert (result.requests, result.triaged, result.fully_read, result.events_created) == (2, 2, 1, 1)
    events = events_by_title(app)

    cycling = events[TITLE]
    assert cycling.status == "VALIDATION_REQUIRED"
    assert cycling.event_type == "MARATHON"
    assert cycling.detection["method"] == "ai_reading"
    assert cycling.detection["location"]["place_name"] == "Tank Bund Road"
    assert cycling.versions[0].changed_by == "ai-reading"

    # The keywords' event is kept: the model's "no" is shown to the reviewer, not obeyed.
    khajaguda = events[KHAJAGUDA]
    assert khajaguda.status == "VALIDATION_REQUIRED"
    assert khajaguda.detection["method"] == "keyword_rules"
    assert khajaguda.detection["ai"]["is_road_event"] is False
    assert khajaguda.versions[-1].changed_by == "ai-reading"

    with app.state.session_factory() as session:
        artifact = session.scalar(select(SourceArtifact).where(SourceArtifact.title == TITLE))
        assert artifact.classification == "RELEVANT_TRAFFIC_ARTICLE"
        assert artifact.classification_details["ai"]["stage"] == "full"

    # Nothing is read twice.
    again = reader(app, tmp_path, model()).run()
    assert again.requests == 0 and again.stopped.startswith("Every article")


def test_reprocessing_keeps_what_the_ai_reading_found(app, tmp_path):
    reader(app, tmp_path, model()).run()
    service = app.state.ingestion_service
    with app.state.session_factory() as session:
        reprocess_stored_evidence(
            session, service.classifier, service.resolver, tools_for_source=service.tools_for_source
        )
    cycling = events_by_title(app)[TITLE]
    assert cycling.status == "VALIDATION_REQUIRED"
    assert cycling.detection["method"] == "ai_reading"


def test_the_api_returns_the_reading_with_each_place_role(app, tmp_path):
    reader(app, tmp_path, model()).run()
    with TestClient(app) as client:
        listed = client.get("/api/events").json()["items"]
        cycling = next(item for item in listed if item["title"] == TITLE)
        ai = cycling["detection"]["ai"]
        assert ai["intent"] == "MARATHON" and ai["impact"] == "CLOSURE"
        roles = {loc["name"]: loc["role"] for loc in cycling["detection"]["affected_locations"]}
        assert roles["Lower Tank Bund"] == "DIVERSION_ROUTE"


def test_an_event_a_reviewer_decided_is_never_changed(app, tmp_path):
    khajaguda = events_by_title(app)[KHAJAGUDA]
    with TestClient(app) as client:
        assert client.post(
            f"/api/events/{khajaguda.event_id}/status", json={"status": "QC_PENDING"}
        ).status_code == 200
    versions = len(events_by_title(app)[KHAJAGUDA].versions)

    reader(app, tmp_path, model()).run()

    after = events_by_title(app)[KHAJAGUDA]
    assert after.status == "QC_PENDING" and len(after.versions) == versions
    assert (after.detection or {}).get("ai") is None


def test_the_daily_limit_and_the_keys_free_requests_are_respected(app, tmp_path):
    fake = model()
    result = reader(app, tmp_path, fake, ai_daily_request_limit=1).run()
    assert fake.requests_sent == 1 and result.stopped == "The request budget for this run is used."
    assert reader(app, tmp_path, model(), ai_daily_request_limit=1).run().stopped.startswith("Today's AI request limit")

    low = model()
    low.remaining = 2
    assert reader(app, tmp_path / "other", low).run().requests == 0


def test_excluded_sources_are_never_sent(app, tmp_path):
    fake = model()
    result = reader(app, tmp_path, fake, ai_excluded_sources="telangana-today").run()
    assert fake.requests_sent == 0 and result.stopped.startswith("Every article")


def test_nothing_is_sent_without_a_key(app, tmp_path):
    fake = model()
    result = reader(app, tmp_path, fake, openrouter_api_key=None).run()
    assert fake.requests_sent == 0 and "No OpenRouter key" in result.stopped


class BrokenModel(FakeModel):
    """Answers, but never with usable JSON."""

    def chat_json(self, system, user, *, max_tokens):
        self.requests_sent += 1
        from services.ai_reading import AiError

        raise AiError("The model's answer is not JSON.", retryable=True)


def test_a_batch_that_keeps_failing_is_set_aside_after_three_tries(app, tmp_path):
    for attempt in range(3):
        broken = BrokenModel({}, {})
        result = reader(app, tmp_path, broken).run()
        assert result.error and broken.requests_sent == 1
    # Set aside: nothing more is sent for these articles today.
    broken = BrokenModel({}, {})
    assert reader(app, tmp_path, broken).run().stopped.startswith("Every article")
    assert broken.requests_sent == 0
