"""The Google News search source: search results lead to articles, which are the evidence."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.models import Event, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.api.serper_news import (
    DEFAULT_QUERIES,
    SerperNewsConnector,
    parse_result_date,
    serper_news_source,
)
from connectors.base import ConnectorError
from connectors.registry import registered_sources
from connectors.rss.telangana_today import TELANGANA_TODAY
from services.extraction import KeywordClassifier
from services.geo_resolution import default_resolver
from services.ingestion import run_ingestion
from tests.support import FakeConnector, khajaguda_article

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
SOURCE = serper_news_source(connected=True)
ARTICLE_URL = "https://news.example.com/khajaguda-restrictions"
OTHER_CITY_URL = "https://news.example.com/pune-diversions"
NO_DATA_URL = "https://blog.example.com/tolichowki"

ARTICLE_PAGE = """<html><head><script type="application/ld+json">
{"@type": "NewsArticle",
 "headline": "Khajaguda junction 60-day restrictions may push traffic onto internal roads",
 "description": "Cyberabad Traffic Police impose traffic diversions near Khajaguda Junction for 60 days from September 26.",
 "datePublished": "2026-09-29T09:15:00+05:30",
 "articleBody": "Hyderabad: The Cyberabad Traffic Police announced traffic diversions at Khajaguda Junction."}
</script></head></html>"""


def search_results(query):
    return {
        "news": [
            {
                "title": "Khajaguda junction 60-day restrictions may push traffic onto internal roads",
                "link": ARTICLE_URL,
                "snippet": "Cyberabad Traffic Police impose 60-day traffic diversions near Khajaguda…",
                "date": "6 days ago",
                "source": "Example Daily",
            },
            {
                "title": "Pune traffic diversions for the festival",
                "link": OTHER_CITY_URL,
                "snippet": "Traffic diversions announced in Pune.",
                "date": "2 days ago",
                "source": "Other Daily",
            },
            {
                "title": "Waterlogging at Tolichowki slows Hyderabad traffic",
                "link": NO_DATA_URL,
                "snippet": "Roads in Tolichowki were waterlogged after overnight rain in Hyderabad.",
                "date": "3 hours ago",
                "source": "A Blog",
            },
            {"title": "", "link": "https://news.example.com/untitled"},
        ]
    }


@pytest.fixture
def calls():
    return {"searches": [], "pages": [], "api_keys": set()}


@pytest.fixture
def connector(calls):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "google.serper.dev":
            calls["searches"].append(json.loads(request.content)["q"])
            calls["api_keys"].add(request.headers["X-API-KEY"])
            return httpx.Response(200, json=search_results(calls["searches"][-1]))
        calls["pages"].append(str(request.url))
        if str(request.url) == NO_DATA_URL:
            return httpx.Response(200, text="<html><body>No structured data.</body></html>")
        return httpx.Response(200, text=ARTICLE_PAGE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SerperNewsConnector(SOURCE, "test-key", "ua", client=client)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("3 days ago", NOW - timedelta(days=3)),
        ("1 hour ago", NOW - timedelta(hours=1)),
        ("2 weeks ago", NOW - timedelta(weeks=2)),
        ("Oct 3, 2026", datetime(2026, 10, 3, tzinfo=timezone.utc)),
        ("3 Oct 2026", datetime(2026, 10, 3, tzinfo=timezone.utc)),
        ("recently", None),
        (None, None),
    ],
)
def test_result_dates_are_read_as_google_gives_them(text, expected):
    assert parse_result_date(text, now=NOW) == expected


def test_each_search_is_run_once_and_links_are_not_repeated(connector, calls):
    records = connector.fetch()
    assert calls["searches"] == list(DEFAULT_QUERIES)
    assert calls["api_keys"] == {"test-key"}
    # Two usable results, however many searches returned them. The untitled
    # one is dropped, and so is the one that does not mention the city.
    assert [record.url for record in records] == [ARTICLE_URL, NO_DATA_URL]
    assert calls["pages"] == []  # no article is read until a result is known to be new

    record = records[0]
    assert record.source_id == "google-news-serper" and record.external_id == ARTICLE_URL
    assert record.raw["search_result"]["publisher"] == "Example Daily"
    assert record.raw["search_result"]["query"] == DEFAULT_QUERIES[0]


def test_a_new_result_is_replaced_by_the_article_it_points_to(connector):
    result = connector.fetch()[0]
    article = connector.complete(result)

    assert article.external_id == result.external_id == ARTICLE_URL
    assert article.content_text.startswith("Hyderabad: The Cyberabad Traffic Police")
    assert article.summary.endswith("for 60 days from September 26.")
    # The publisher's own publication time, not Google's "6 days ago".
    assert article.published_at == datetime(2026, 9, 29, 3, 45, tzinfo=timezone.utc)
    assert article.raw["search_result"]["publisher"] == "Example Daily"
    assert "structured data" in article.raw["acquired_from"]


def test_a_result_whose_page_has_no_article_data_is_kept_as_a_search_result(connector):
    result = connector.fetch()[1]
    kept = connector.complete(result)
    assert kept == result
    assert kept.content_text is None and "search result" in kept.raw["acquired_from"]


def test_a_refused_key_fails_the_run_without_exposing_the_key():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    connector = SerperNewsConnector(SOURCE, "secret-key", "ua", client=client)
    with pytest.raises(ConnectorError) as error:
        connector.fetch()
    assert "key was refused" in str(error.value) and "secret-key" not in str(error.value)


def test_the_source_is_connected_only_when_a_key_is_configured():
    without = {s.definition.source_id: s for s in registered_sources()}["google-news-serper"]
    assert without.create_connector is None
    assert without.definition.integration_status == "REQUIRES_ACCESS"
    assert without.definition.active is False

    with_key = {s.definition.source_id: s for s in registered_sources("k")}["google-news-serper"]
    assert with_key.definition.integration_status == "CONNECTED" and with_key.definition.active
    assert with_key.definition.source_tier == 4
    assert isinstance(with_key.create_connector("ua"), SerperNewsConnector)


# --- through the pipeline -----------------------------------------------------


@pytest.fixture
def search_session(session):
    SourceRepository(session).sync_registry([SOURCE, TELANGANA_TODAY])
    session.commit()
    return session


def ingest(session, connector):
    result = run_ingestion(
        connector, KeywordClassifier.from_file(), SqlIngestionStore(session), default_resolver()
    )
    session.commit()
    return result


def test_search_results_become_located_events(
    search_session, connector, calls
):
    result = ingest(search_session, connector)
    assert (result.fetched, result.new_artifacts, result.events_created) == (2, 2, 2)
    assert sorted(calls["pages"]) == sorted([ARTICLE_URL, NO_DATA_URL])

    events = {event.title: event for event in search_session.scalars(select(Event)).unique()}
    khajaguda = events[
        "Khajaguda junction 60-day restrictions may push traffic onto internal roads"
    ]
    assert khajaguda.source_id == "google-news-serper"
    assert khajaguda.geometry["type"] == "Point"
    assert khajaguda.detection["stated_period"] == "for 60 days from September 26"
    assert khajaguda.status == "VALIDATION_REQUIRED"
    assert khajaguda.artifact.published_at.isoformat().startswith("2026-09-29T03:45")
    # The blog post had no article data: located from its headline, dated only by Google.
    blog = events["Waterlogging at Tolichowki slows Hyderabad traffic"]
    assert blog.detection["location"]["place_name"] == "Tolichowki"
    assert blog.start_time is None


def test_a_later_poll_reads_no_page_again(search_session, connector, calls):
    ingest(search_session, connector)
    calls["pages"].clear()
    again = ingest(search_session, connector)
    assert (again.new_artifacts, again.duplicates) == (0, 2)
    assert calls["pages"] == []


def test_an_article_already_held_from_its_publishers_feed_is_not_stored_again(
    search_session, calls
):
    feed_article = khajaguda_article()
    ingest(search_session, FakeConnector([feed_article], source=TELANGANA_TODAY))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "google.serper.dev":
            return httpx.Response(
                200,
                json={
                    "news": [
                        {
                            "title": feed_article.title,
                            "link": feed_article.url,
                            "snippet": "Hyderabad: Cyberabad police announced diversions.",
                            "date": "1 day ago",
                        }
                    ]
                },
            )
        calls["pages"].append(str(request.url))
        return httpx.Response(200, text=ARTICLE_PAGE)

    connector = SerperNewsConnector(
        SOURCE, "k", "ua", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = ingest(search_session, connector)
    assert (result.new_artifacts, result.duplicates, result.events_created) == (0, 1, 0)
    assert calls["pages"] == []
    stored = search_session.scalars(
        select(SourceArtifact).where(SourceArtifact.url == feed_article.url)
    ).all()
    assert [artifact.source_id for artifact in stored] == ["telangana-today"]


def test_every_article_is_read_before_anything_is_written(search_session, connector, calls):
    """A write locks the database; pages must not be fetched while it is held."""
    order: list[str] = []
    original_complete = connector.complete
    connector.complete = lambda record: order.append("read") or original_complete(record)

    class RecordingStore(SqlIngestionStore):
        def save_artifact(self, record, classification):
            order.append("write")
            return super().save_artifact(record, classification)

    run_ingestion(
        connector, KeywordClassifier.from_file(), RecordingStore(search_session), default_resolver()
    )
    assert order == ["read", "read", "write", "write"]


# --- temporary failures (7 October 2026: one search timed out and the whole poll was lost) ---


def flaky_connector(fail):
    """A connector whose searches fail while `fail(query, attempt)` says so."""
    attempts: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["q"]
        attempts[query] = attempts.get(query, 0) + 1
        outcome = fail(query, attempts[query])
        if outcome == "timeout":
            raise httpx.ReadTimeout("The read operation timed out", request=request)
        if isinstance(outcome, int):
            return httpx.Response(outcome)
        return httpx.Response(200, json=search_results(query))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SerperNewsConnector(SOURCE, "test-key", "ua", client=client), attempts


def test_a_search_that_times_out_once_is_retried_and_nothing_is_lost():
    first = DEFAULT_QUERIES[0]
    connector, attempts = flaky_connector(
        lambda q, n: "timeout" if q == first and n == 1 else None
    )
    records = connector.fetch()
    assert attempts[first] == 2
    assert [record.url for record in records] == [ARTICLE_URL, NO_DATA_URL]


@pytest.mark.parametrize("failure", ["timeout", 500, 503, 429])
def test_a_search_that_keeps_failing_is_skipped_and_the_others_are_kept(failure):
    last = DEFAULT_QUERIES[-1]
    connector, attempts = flaky_connector(lambda q, n: failure if q == last else None)
    records = connector.fetch()
    assert attempts[last] == 2  # tried, retried once, then skipped
    assert all(attempts[q] == 1 for q in DEFAULT_QUERIES[:-1])
    assert [record.url for record in records] == [ARTICLE_URL, NO_DATA_URL]


def test_the_poll_fails_when_every_search_fails():
    connector, _ = flaky_connector(lambda q, n: "timeout")
    with pytest.raises(ConnectorError, match="all .* searches failed"):
        connector.fetch()


@pytest.mark.parametrize("status", [400, 401, 403])
def test_a_refused_key_or_bad_request_still_fails_at_once_without_retrying(status):
    connector, attempts = flaky_connector(lambda q, n: status)
    with pytest.raises(ConnectorError):
        connector.fetch()
    assert sum(attempts.values()) == 1
