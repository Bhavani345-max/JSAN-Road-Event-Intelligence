"""Sources keep working through brief failures, and no test-phase limit holds data back
(21 October 2026, decision 0039).

- A dropped connection, a timeout or a 500/502/504 is tried once more before a
  run fails; a refusal (429, 503) is not: the source asked REI to wait.
- TfL's occasional GeoJSON answer instead of its list is asked again once.
- Official feeds keep every record (no 30-record limit) and planned closures
  up to a year ahead (not only a week).
- Google News search asks for 100 results a search and reads every new page;
  place look-ups have no daily limit unless one is configured.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.core.config import Settings
from connectors.base import ConnectorError
from connectors.official import common
from connectors.official.common import UPCOMING_WINDOW, fetch_json, fetch_text, select_for_run
from connectors.official.tfl import TflRoadDisruptionsConnector, tfl_source

NOW = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)


def flaky(*answers):
    """A transport giving each answer in turn: a Response, or an exception to raise."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        answer = answers[min(len(calls), len(answers) - 1)]
        calls.append(str(request.url))
        if isinstance(answer, Exception):
            raise answer
        return answer

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


@pytest.mark.parametrize(
    "first",
    [
        httpx.ConnectError("Connection reset by peer"),
        httpx.ReadTimeout("The read operation timed out"),
        httpx.RemoteProtocolError("Server disconnected without sending a response."),
        httpx.Response(500),
        httpx.Response(502),
        httpx.Response(504),
    ],
)
def test_a_brief_failure_is_tried_once_more(first):
    client, calls = flaky(first, httpx.Response(200, json=[{"id": 1}]))
    assert fetch_json("https://feed.example.org/x", "ua", client=client) == [{"id": 1}]
    assert len(calls) == 2
    client, calls = flaky(first, httpx.Response(200, text="<html>ok</html>"))
    assert fetch_text("https://feed.example.org/y", "ua", client=client) == "<html>ok</html>"
    assert len(calls) == 2


@pytest.mark.parametrize("status", [429, 503])
def test_a_refusal_is_not_asked_again(status):
    client, calls = flaky(httpx.Response(status), httpx.Response(200, json=[]))
    with pytest.raises(ConnectorError, match="rate limited"):
        fetch_json("https://feed.example.org/x", "ua", client=client)
    assert len(calls) == 1


def test_a_failure_that_lasts_fails_the_run_after_one_more_try():
    client, calls = flaky(httpx.ConnectError("refused"), httpx.ConnectError("refused"))
    with pytest.raises(ConnectorError, match="Could not fetch"):
        fetch_json("https://feed.example.org/x", "ua", client=client)
    assert len(calls) == 2
    client, calls = flaky(httpx.Response(504), httpx.Response(504))
    with pytest.raises(ConnectorError, match="HTTP 504"):
        fetch_json("https://feed.example.org/x", "ua", client=client)
    assert len(calls) == 2


def test_the_retry_waits_a_moment_first(monkeypatch):
    waited = []
    monkeypatch.setattr(common, "_sleep", waited.append)
    client, _ = flaky(httpx.Response(502), httpx.Response(200, json=[]))
    fetch_json("https://feed.example.org/x", "ua", client=client)
    assert waited == [common.RETRY_DELAY_SECONDS]


GEOJSON = {"type": "FeatureCollection", "crs": {}, "features": []}


def test_tfls_odd_geojson_answer_is_asked_again_once():
    from tests.unit.test_official_sources import TFL

    client, calls = flaky(httpx.Response(200, json=GEOJSON), httpx.Response(200, json=TFL))
    connector = TflRoadDisruptionsConnector(tfl_source(scheduled=False), "ua", client=client, clock=lambda: NOW)
    assert connector.fetch()
    assert len(calls) == 2
    client, calls = flaky(httpx.Response(200, json=GEOJSON))
    connector = TflRoadDisruptionsConnector(tfl_source(scheduled=False), "ua", client=client, clock=lambda: NOW)
    with pytest.raises(ConnectorError, match=r"not a list \(keys: crs, features, type\)"):
        connector.fetch()
    assert len(calls) == 2


def test_official_feeds_keep_every_record_and_closures_planned_up_to_a_year_ahead(monkeypatch):
    for name in ("OFFICIAL_FEED_MAX_RECORDS", "PLACE_LOOKUP_DAILY_CREDITS"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.official_feed_max_records == 0  # every record
    assert settings.place_lookup_daily_credits == 0  # no daily limit
    assert UPCOMING_WINDOW == timedelta(days=365)
    items = [(f"r{n}", NOW + timedelta(days=days), None, n) for n, days in enumerate((0, 10, 200, 364, 366))]
    kept = select_for_run(items, now=NOW, start=lambda i: i[1], end=lambda i: i[2], order=lambda i: i[3], limit=None)
    assert sorted(i[0] for i in kept) == ["r0", "r1", "r2", "r3"]


def test_google_news_search_asks_for_100_results_and_reads_every_new_page():
    from connectors.api import serper_news

    assert serper_news.DEFAULT_RESULTS_PER_QUERY == 100 and serper_news.CREDITS_PER_SEARCH == 2
    assert serper_news.MAX_ARTICLE_PAGES_PER_POLL is None


def test_place_lookups_have_no_daily_limit_unless_one_is_set(tmp_path):
    from services.geo_resolution.google_maps import GoogleMapsLookup

    unlimited = GoogleMapsLookup("k", tmp_path / "cache.json", daily_credits=0, allow_network=False)
    assert all(unlimited._spend(3) for _ in range(100))
    limited = GoogleMapsLookup("k", tmp_path / "cache2.json", daily_credits=5, allow_network=False)
    assert limited._spend(3) and not limited._spend(3)
