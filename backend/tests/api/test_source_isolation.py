"""One source's failure never stops the others (decision 0034)."""

from app.core.config import Settings
from app.main import create_app
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.registry import RegisteredSource
from packages.source_models import SourceDefinition
from tests.support import TEST_SOURCE, FakeConnector, khajaguda_article


def _source(source_id: str) -> SourceDefinition:
    return SourceDefinition.model_validate(
        TEST_SOURCE.model_dump() | {"source_id": source_id, "source_name": source_id}
    )


class BrokenParser:
    """A connector whose parser has a bug: not a ConnectorError."""

    def __init__(self, source):
        self.source = source

    def fetch(self):
        raise KeyError("geometry")


class Refused:
    def __init__(self, source):
        self.source = source

    def fetch(self):
        raise ConnectorError("HTTP 503")


def _service(engine, session, factories):
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=False,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    service = app.state.ingestion_service
    definitions = [_source(source_id) for source_id in factories]
    service.sources = (*service.sources, *(RegisteredSource(d) for d in definitions))
    SourceRepository(session).sync_registry(definitions)
    session.commit()
    service.connector_factories = {
        source_id: (lambda make=make, d=d: make(d)) for (source_id, make), d in zip(factories.items(), definitions)
    }
    service.resolver = None
    return service


def test_a_bug_in_one_source_is_recorded_and_the_next_source_still_runs(engine, session):
    service = _service(engine, session, {
        "a-broken": BrokenParser,
        "b-refused": Refused,
        "c-working": lambda d: FakeConnector([khajaguda_article().model_copy(update={"source_id": d.source_id})], source=d),
    })  # fmt: skip
    results = {r.source_id: r for r in service.run_due()}

    assert results["a-broken"].status == "failed"
    assert "Unexpected error while reading the source: KeyError" in results["a-broken"].error
    assert results["b-refused"].status == "failed" and results["b-refused"].error == "HTTP 503"
    assert results["c-working"].status == "ok" and results["c-working"].new_artifacts == 1

    sources = SourceRepository(session)
    session.expire_all()
    broken = sources.get("a-broken")
    # Recorded on the source, so the dashboard shows it failing and it waits for
    # its next interval instead of blocking every round.
    assert broken.last_failure_at is not None and broken.last_poll_at is not None
    assert "KeyError" in broken.last_error and broken.last_success_at is None
    assert sources.get("c-working").last_success_at is not None


def test_a_failed_source_is_not_polled_again_before_its_interval(engine, session):
    service = _service(engine, session, {"a-broken": BrokenParser})
    assert [r.source_id for r in service.run_due()] == ["a-broken"]
    assert service.run_due() == []
