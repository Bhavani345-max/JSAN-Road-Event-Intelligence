"""Which official feeds the scheduler polls (decision 0028).

Production polled no official feed from 13 to 15 October 2026 because
OFFICIAL_FEEDS_SCHEDULED is unset there, and setting it switches on all of them at
once. OFFICIAL_FEEDS_SCHEDULED_SOURCES switches them on one at a time.
"""

import logging

import pytest

from app.core.config import Settings
from app.services.bootstrap import sync_reference_data
from app.services.ingestion_service import IngestionService
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from tests.support import FakeConnector

TFL = "tfl-road-disruptions"
TORONTO = "toronto-road-restrictions"


def official(sources) -> dict:
    return {
        s.definition.source_id: s.definition
        for s in sources
        if s.definition.source_id in OFFICIAL_SOURCE_IDS
    }


def test_the_connected_official_feeds_can_be_named():
    # Seven, and nine for Canada and Australia since 15 October 2026 (decision 0029).
    assert len(OFFICIAL_SOURCE_IDS) == 16
    assert {TFL, TORONTO, "nyc-street-closures", "finland-digitraffic-road-events"} <= OFFICIAL_SOURCE_IDS
    # Removed for giving no location (decision 0029): not an official feed to schedule.
    assert not OFFICIAL_SOURCE_IDS & {
        "nyc-permitted-events", "mumbai-traffic-police-notifications", "bengaluru-traffic-police-website"
    }


def test_no_official_feed_is_scheduled_unless_asked():
    assert not any(d.active for d in official(registered_sources()).values())


def test_only_the_official_feeds_named_are_scheduled():
    feeds = official(registered_sources(official_feeds_scheduled_sources={TFL, TORONTO}))
    assert {source_id for source_id, d in feeds.items() if d.active} == {TFL, TORONTO}
    # A chosen feed is described as scheduled, the others as run by hand.
    assert "Polled every 15 minutes." in feeds[TFL].notes
    only_tfl = official(registered_sources(official_feeds_scheduled_sources={TFL}))
    assert "run by hand" in only_tfl[TORONTO].notes


def test_naming_a_news_restricted_or_removed_source_schedules_nothing():
    named = {"the-hans-india", "siasat", "telangana-today", "no-such-feed"}
    sources = {s.definition.source_id: s for s in registered_sources(official_feeds_scheduled_sources=named)}
    assert [s.definition for s in sources.values()] == [s.definition for s in registered_sources()]
    assert sources["the-hans-india"].create_connector is None
    assert sources["the-hans-india"].definition.active is False


def test_the_switch_for_every_feed_still_schedules_them_all():
    feeds = official(registered_sources(official_feeds_scheduled=True))
    assert all(d.active for d in feeds.values()) and len(feeds) == 16


def test_the_setting_is_a_comma_separated_list():
    settings = Settings(
        _env_file=None, official_feeds_scheduled_sources=f" {TFL}, ,{TORONTO} "
    )
    assert settings.official_feeds_scheduled_source_ids == {TFL, TORONTO}
    assert Settings(_env_file=None).official_feeds_scheduled_source_ids == frozenset()


@pytest.fixture
def scheduled_tfl(session_factory):
    """An ingestion service scheduling TfL only, every official feed faked, nothing fetched."""
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        official_feeds_scheduled_sources=TFL,
        event_matching_after_ingestion=False,
    )
    service = IngestionService(session_factory, settings)
    with session_factory() as session:
        sync_reference_data(session, service.sources)
    polled: list[str] = []

    def fake(source_id):
        definition = next(s.definition for s in service.sources if s.definition.source_id == source_id)

        def build():
            polled.append(source_id)
            return FakeConnector([], source=definition)

        return build

    # The removed source gets a connector here too: its inactive row must still stop it.
    service.connector_factories = {
        source_id: fake(source_id) for source_id in OFFICIAL_SOURCE_IDS | {"the-hans-india"}
    }
    return service, polled


def test_the_scheduler_polls_only_the_feed_switched_on(scheduled_tfl):
    service, polled = scheduled_tfl
    results = service.run_due()
    assert polled == [TFL]
    assert [r.status for r in results] == ["ok"]


def test_a_scheduled_feed_is_not_polled_again_before_its_interval(scheduled_tfl):
    service, polled = scheduled_tfl
    service.run_due()
    assert service.run_due() == []
    assert polled == [TFL]


def test_a_name_that_is_not_an_official_feed_is_reported(session_factory, caplog):
    settings = Settings(
        _env_file=None, database_url="sqlite://",
        official_feeds_scheduled_sources=f"{TFL},the-hans-india",
    )  # fmt: skip
    with caplog.at_level(logging.WARNING, logger="app.services.ingestion_service"):
        IngestionService(session_factory, settings)
    assert "the-hans-india not an official feed; ignored" in caplog.text
