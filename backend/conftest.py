"""Fixtures shared by the repository-level tests and the API tests."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_db_engine, create_session_factory
from app.models import Base
from app.repositories.sources import SourceRepository
from connectors.rss import RssConnector, RssFeedConfig
from packages.source_models import RawSourceRecord
from tests.support import FEEDS, RETRIEVED_AT, TEST_SOURCE


@pytest.fixture
def feed_bytes() -> bytes:
    return (FEEDS / "news_feed_sample.xml").read_bytes()


@pytest.fixture
def rss_connector() -> RssConnector:
    return RssConnector(RssFeedConfig(source=TEST_SOURCE))


@pytest.fixture
def records(rss_connector: RssConnector, feed_bytes: bytes) -> list[RawSourceRecord]:
    return rss_connector.parse(feed_bytes, retrieved_at=RETRIEVED_AT)


@pytest.fixture
def engine():
    """An empty in-memory database with the current schema."""
    engine = create_db_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture
def session(session_factory: sessionmaker[Session]):
    """A database session with the test source registered."""
    with session_factory() as session:
        SourceRepository(session).sync_registry([TEST_SOURCE])
        session.commit()
        yield session
