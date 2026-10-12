import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.support import SOURCE_FIXTURES, TEST_SOURCE, FakeConnector, parse_fixture


@pytest.fixture
def app(engine, session, records):
    """The API on an in-memory database, with a fake news source instead of the network."""
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_migrate=False,
        ingestion_scheduler_enabled=False,
        # These fixtures test ingestion per source. Matching (which merges the
        # identical fixture articles the sources share) is tested on its own
        # in test_merging_api.py.
        event_matching_after_ingestion=False,
    )
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        TEST_SOURCE.source_id: lambda: FakeConnector(records)
    }
    # The synthetic feeds name invented places, which no gazetteer knows.
    # Location is tested with real articles (test_location.py).
    app.state.ingestion_service.resolver = None
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def news_client(engine, session):
    """The API with all three real RSS sources, each fed a fixture in its publisher's format."""
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_migrate=False,
        ingestion_scheduler_enabled=False,
        # These fixtures test ingestion per source. Matching (which merges the
        # identical fixture articles the sources share) is tested on its own
        # in test_merging_api.py.
        event_matching_after_ingestion=False,
    )
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        source.source_id: (
            lambda source=source, filename=filename: FakeConnector(
                parse_fixture(source, filename), source=source
            )
        )
        for source, filename in SOURCE_FIXTURES
    }
    app.state.ingestion_service.resolver = None
    with TestClient(app) as client:
        yield client
