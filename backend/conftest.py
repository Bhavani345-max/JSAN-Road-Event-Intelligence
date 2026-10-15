"""Fixtures shared by the repository-level tests and the API tests."""

import os

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


# Optional: run the tests on PostgreSQL, production's database, which enforces
# what SQLite lets through (column lengths, types). A throwaway database only:
# every test empties it.
TEST_POSTGRES_URL = os.environ.get("REI_TEST_POSTGRES_URL")


@pytest.fixture
def engine():
    """An empty database with the current schema: in memory, or the throwaway
    PostgreSQL database named by REI_TEST_POSTGRES_URL."""
    if TEST_POSTGRES_URL:
        engine = create_db_engine(TEST_POSTGRES_URL)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()
        return
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
