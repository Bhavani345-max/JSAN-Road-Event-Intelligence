"""Google News RSS discovery connector (6 October 2026).

Tested on a saved feed only. The live source is BLOCKED: every feed says it
is for personal, non-commercial use in a feed reader, and any other use is
prohibited. These tests show the connector behaves if that ever changes, and
that the registry never presents it as usable or authoritative.
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from connectors.base import ConnectorError
from connectors.discovery.google_news_rss import (
    FEED_NOTICE,
    GoogleNewsRssConnector,
    google_news_rss_source,
)
from connectors.registry import registered_sources
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.cities import get_city
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.geo_resolution import default_resolver
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FEED = (Path(__file__).parents[1] / "fixtures" / "google_news_rss_sample.xml").read_bytes()
HYDERABAD = get_city("hyderabad")


def connector(handler, **kwargs) -> GoogleNewsRssConnector:
    source = google_news_rss_source(HYDERABAD, enabled=True)
    return GoogleNewsRssConnector(
        source,
        HYDERABAD,
        "ua",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda seconds: None,
        **kwargs,
    )


@pytest.fixture
def requests():
    return []


@pytest.fixture
def ok(requests):
    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=FEED)

    return handler


# --- registry -------------------------------------------------------------------


def test_the_source_is_blocked_by_its_terms_and_never_fetched_by_default():
    sources = {s.definition.source_id: s for s in registered_sources()}
    for city_id in ("hyderabad", "london"):
        registered = sources[f"google-news-rss-{city_id}"]
        definition = registered.definition
        assert registered.create_connector is None
        assert definition.integration_status is IntegrationStatus.BLOCKED
        assert definition.active is False
        assert definition.terms_status is TermsStatus.RESTRICTED
        assert definition.commercial_use is CommercialUse.NOT_PERMITTED
        assert FEED_NOTICE in definition.licence


def test_it_is_discovery_only_and_never_authoritative():
    definition = google_news_rss_source(HYDERABAD, enabled=True)
    assert definition.source_class is SourceClass.DISCOVERY
    assert definition.discovery_only and definition.source_tier == 4
    assert definition.provides_geometry is False


def test_there_is_one_source_per_configured_city_and_none_is_hard_coded():
    sources = {s.definition.source_id: s.definition for s in registered_sources()}
    london = sources["google-news-rss-london"]
    assert (london.city, london.country, london.language) == ("london", "GB", "en")


# --- the feed -------------------------------------------------------------------


def test_feed_addresses_follow_the_citys_country_and_language(ok, requests):
    london = get_city("london")
    gnews = GoogleNewsRssConnector(
        google_news_rss_source(london, enabled=True), london, "ua", queries=("London road closure",)
    )
    params = parse_qs(urlparse(gnews.feed_url("London road closure")).query)
    assert params == {
        "q": ["London road closure when:7d"],
        "hl": ["en-GB"],
        "gl": ["GB"],
        "ceid": ["GB:en"],
    }


def test_results_are_parsed_and_only_this_citys_are_kept(ok):
    records = connector(ok, queries=("Hyderabad traffic",)).fetch()
    assert [record.title for record in records] == [
        "Traffic curbs at Khajaguda Junction in Hyderabad for 60 days from September 26",
        "Hyderabad police block roads around Tank Bund",
    ]
    first = records[0]
    assert first.published_at == datetime(2026, 9, 23, 11, 30, tzinfo=timezone.utc)
    # The publisher's suffix is not part of the headline; it is kept apart.
    search = first.raw["search_result"]
    assert (search["publisher"], search["publisher_url"]) == ("The Hindu", "https://www.thehindu.com")
    assert search["query"] == "Hyderabad traffic"
    # Headline only: the article behind Google's link is not read.
    assert first.summary is None and first.content_text is None
    assert "headline only" in first.raw["acquired_from"]


def test_the_same_result_from_several_searches_is_one_record(ok, requests):
    records = connector(ok, queries=("one", "two", "three")).fetch()
    assert len(requests) == 3
    assert len(records) == 2


def test_requests_are_spaced_out(ok):
    pauses = []
    gnews = connector(ok, queries=("one", "two", "three"))
    gnews._sleep = pauses.append
    gnews.fetch()
    assert pauses == [gnews.pause_seconds] * 2 and gnews.pause_seconds >= 1


@pytest.mark.parametrize("status", [429, 503])
def test_a_refusal_stops_the_poll(status, requests):
    def handler(request):
        requests.append(request)
        return httpx.Response(status)

    with pytest.raises(ConnectorError, match=f"refused the request \\(HTTP {status}\\)"):
        connector(handler, queries=("one", "two")).fetch()
    assert len(requests) == 1  # the second search is not tried


def test_a_malformed_feed_is_an_error():
    with pytest.raises(ConnectorError, match="invalid feed"):
        connector(lambda request: httpx.Response(200, content=b"<html>not a feed")).fetch()


def test_a_timeout_is_an_error():
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(ConnectorError, match="timed out"):
        connector(handler).fetch()


# --- through the pipeline ------------------------------------------------------


def test_an_article_already_held_under_the_same_headline_is_not_stored_again(session, ok):
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from tests.support import khajaguda_article

    gnews = connector(ok, queries=("Hyderabad traffic",))
    SourceRepository(session).sync_registry([TELANGANA_TODAY, gnews.source])
    session.commit()
    feed_article = khajaguda_article().model_copy(
        update={
            "title": "Traffic curbs at Khajaguda Junction in Hyderabad for 60 days from September 26"
        }
    )
    classifier = KeywordClassifier.from_file()
    store = SqlIngestionStore(session)
    run_ingestion(FakeConnector([feed_article], source=TELANGANA_TODAY), classifier, store)
    session.commit()

    result = run_ingestion(gnews, classifier, store, default_resolver(), HYDERABAD)
    session.commit()
    assert (result.fetched, result.duplicates, result.new_artifacts) == (2, 1, 1)
    # A second poll adds nothing at all.
    again = run_ingestion(gnews, classifier, store, default_resolver(), HYDERABAD)
    assert (again.new_artifacts, again.events_created) == (0, 0)


def test_a_discovery_result_becomes_at_most_a_lead_for_review(session, ok):
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository

    gnews = connector(ok, queries=("Hyderabad traffic",))
    SourceRepository(session).sync_registry([gnews.source])
    session.commit()
    classifier = KeywordClassifier.for_city(HYDERABAD, default_resolver())
    result = run_ingestion(gnews, classifier, SqlIngestionStore(session), default_resolver(), HYDERABAD)
    session.commit()
    from sqlalchemy import select

    from app.models import Event

    events = session.scalars(select(Event)).unique().all()
    assert result.events_created == len(events) >= 1
    assert {event.status for event in events} == {"VALIDATION_REQUIRED"}
    assert all(event.confidence is None and event.severity is None for event in events)
