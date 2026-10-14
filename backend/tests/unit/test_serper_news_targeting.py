"""The Google News searches of 6 October 2026: targeting, windows and what is left out."""

import json

import httpx
import pytest

from connectors.api.serper_news import (
    CROWDING_CITIES,
    DEFAULT_QUERIES,
    DEFAULT_WINDOW,
    WINDOWS,
    SerperNewsConnector,
    serper_news_source,
)

SOURCE = serper_news_source(connected=True)

RESULTS = {
    "news": [
        {
            "title": "Hyderabad police block roads around Tank Bund",
            "link": "https://news.example.com/tank-bund",
            "snippet": "Roads around Tank Bund were blocked on Sunday.",
            "date": "1 week ago",
            "source": "Example Mail",
        },
        {
            # Names another city in its headline: dropped before any page is read.
            "title": "Race Course Road Traffic Diversion in Bengaluru for 60 Days",
            "link": "https://news.example.com/bengaluru",
            "snippet": "Unlike Hyderabad, Bengaluru…",
            "date": "22 hours ago",
        },
        {
            # A Hyderabad road named after another city is still Hyderabad.
            "title": "Diversions on Mumbai Highway near Miyapur",
            "link": "https://news.example.com/mumbai-highway",
            "snippet": "Hyderabad: Cyberabad police…",
            "date": "2 days ago",
        },
        {
            # A script REI does not read.
            "title": "कंदवा पंचकोसी मार्ग पर खराब सड़क पर भरा पानी",
            "link": "https://news.example.com/hindi",
            "snippet": "Hyderabad",
            "date": "2 days ago",
        },
    ]
}


@pytest.fixture
def requests():
    return []


def connector(requests, **kwargs):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=RESULTS)

    return SerperNewsConnector(
        SOURCE, "k", "ua", client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs
    )


def test_every_search_names_hyderabad_and_leaves_the_crowding_cities_out():
    assert len(DEFAULT_QUERIES) == 12
    for query in DEFAULT_QUERIES:
        assert any(
            name in query for name in ("Hyderabad", "Secunderabad", "Cyberabad", "GHMC")
        ), query
        assert "-Delhi" in query and "-Bengaluru" in query
    assert "Delhi" in CROWDING_CITIES and "Bengaluru" in CROWDING_CITIES


def test_polls_search_the_past_week_ten_results_at_a_time(requests):
    connector(requests).fetch()
    assert {request["tbs"] for request in requests} == {DEFAULT_WINDOW} == {"qdr:w"}
    assert {request["num"] for request in requests} == {10}
    assert {request["gl"] for request in requests} == {"in"}


def test_a_sweep_can_search_a_longer_window(requests):
    connector(requests, window=WINDOWS["month"], results_per_query=20).fetch()
    assert {request["tbs"] for request in requests} == {"qdr:m"}
    assert {request["num"] for request in requests} == {20}


def test_results_about_other_cities_and_in_other_scripts_are_left_out(requests):
    records = connector(requests).fetch()
    assert [record.title for record in records] == [
        "Hyderabad police block roads around Tank Bund",
        "Diversions on Mumbai Highway near Miyapur",
    ]


def test_the_source_says_what_a_day_of_polling_costs():
    notes = SOURCE.notes
    assert "12 Hyderabad road searches" in notes
    assert "every 8 hours" in notes and "36 a day" in notes
    assert SOURCE.polling_frequency_minutes == 480
