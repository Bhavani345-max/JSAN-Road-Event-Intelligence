"""Every source REI can poll, in every country, is tried again early when the
internet is lost (decision 0041).

The scheduler retries a poll that could not reach its site after 15 minutes
instead of the source's full interval, but only when the connector's error says
so (`could_not_reach`). Here the network is cut for every registered connector:
each must fail that way, whatever kind of source it is (RSS news, an official
feed, a search).
"""

import httpx
import pytest

from connectors.base import ConnectorError, could_not_reach
from connectors.discovery import gdelt
from connectors.registry import registered_sources

POLLABLE = [
    source
    for source in registered_sources(
        serper_api_key="test-key",
        official_feeds_scheduled=True,
        tfl_app_key="test-key",
        gdelt_enabled=True,
    )
    if source.create_connector is not None
]


def _offline(self, request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 11001] getaddrinfo failed", request=request)


@pytest.fixture
def no_internet(monkeypatch):
    # Every httpx request of a connector ends in this transport.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _offline)
    # GDELT's searches wait their turn (6 s apart); nothing is sent here.
    monkeypatch.setattr(gdelt._Guard, "wait", lambda self, seconds, sleep, clock: None)


def test_every_kind_of_source_is_checked():
    ids = {source.definition.source_id for source in POLLABLE}
    assert len(ids) > 70
    # RSS news, official feeds of several countries, the city searches.
    assert {
        "telangana-today", "nl-ndw-planningsfeed-wegwerkzaamheden", "tfl-road-disruptions"
    } <= ids
    assert any(source_id.startswith("google-news-serper") for source_id in ids)


@pytest.mark.parametrize("source", POLLABLE, ids=lambda source: source.definition.source_id)
def test_a_source_that_cannot_reach_its_site_is_retried_early(source, no_internet):
    connector = source.create_connector("REI-test")
    with pytest.raises(ConnectorError) as failure:
        connector.fetch()
    assert could_not_reach(failure.value), str(failure.value)
