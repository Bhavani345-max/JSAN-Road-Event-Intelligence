"""Google News search for India's other cities (decision 0037).

Each Indian city with a place list and searches of its own gets its own search
source on the same Serper key. Results about another city, and results from
publishers whose terms forbid automated access or that the user removed, are
left out. Article pages are read as Hyderabad's are (the user's decision of
19 October 2026); the stricter mode reads only publishers that permit it.
"""

import json

import httpx
import pytest

from connectors.api.serper_news import (
    CITY_POLLING_FREQUENCY_MINUTES,
    DEFAULT_QUERIES,
    SerperNewsConnector,
    queries_for,
    searched_cities,
    serper_news_source,
    source_id_for,
)
from connectors.registry import registered_sources
from packages.cities import get_city
from packages.source_models import IntegrationStatus

OTHER_CITIES = {"ahmedabad", "bengaluru", "chennai", "delhi", "kolkata", "mumbai", "pune"}
DELHI = get_city("delhi")


def test_every_other_indian_city_with_a_place_list_is_searched():
    assert {city.id for city in searched_cities()} == OTHER_CITIES


def test_each_city_search_is_registered_on_the_key_and_listed_without_it():
    with_key = {s.definition.source_id: s for s in registered_sources("k")}
    without = {s.definition.source_id: s for s in registered_sources()}
    for city_id in OTHER_CITIES:
        source_id = source_id_for(city_id)
        assert source_id == f"google-news-serper-{city_id}"
        connected = with_key[source_id]
        assert connected.definition.integration_status is IntegrationStatus.CONNECTED
        assert connected.definition.active and connected.definition.city == city_id
        assert connected.definition.polling_frequency_minutes == CITY_POLLING_FREQUENCY_MINUTES
        assert isinstance(connected.create_connector("ua"), SerperNewsConnector)
        listed = without[source_id]
        assert listed.definition.integration_status is IntegrationStatus.REQUIRES_ACCESS
        assert not listed.definition.active and listed.create_connector is None
    # Hyderabad's search is unchanged.
    assert with_key["google-news-serper"].definition.city == "hyderabad"
    assert source_id_for("hyderabad") == "google-news-serper"


def test_hyderabads_searches_are_unchanged_and_other_cities_use_their_own():
    assert queries_for("hyderabad") == DEFAULT_QUERIES
    assert all(query.endswith("-Pune -Kolkata -Noida") for query in DEFAULT_QUERIES)
    assert queries_for("delhi") == DELHI.discovery.queries


DELHI_PAGE_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1"
UNREVIEWED_URL = "https://news.example.com/delhi-curbs"
RESULTS = [
    # About Delhi, from a publisher whose terms were not reviewed: kept as Google's result.
    {"title": "Delhi Traffic Police issues advisory for Connaught Place", "link": UNREVIEWED_URL,
     "snippet": "Diversions near Connaught Place on Sunday.", "date": "1 day ago", "source": "Example"},
    # About Delhi, from PIB, whose terms permit reading: its page is read.
    {"title": "Traffic arrangements in New Delhi for the parade", "link": DELHI_PAGE_URL,
     "snippet": "Delhi Traffic Police arrangements.", "date": "2 days ago", "source": "PIB"},
    # Another city's headline: left out.
    {"title": "Hyderabad traffic diversions for the festival", "link": "https://news.example.com/hyd",
     "snippet": "Not Delhi news, though Delhi is named here.", "date": "1 day ago", "source": "Example"},
    # A short name inside another word is not the city ("MCD" in "McDonald's").
    {"title": "McDonald's opens a drive-through", "link": "https://news.example.com/mcdonalds-drive",
     "snippet": "Road traffic expected.", "date": "1 day ago", "source": "Example"},
    # Publishers whose terms forbid automated access, or that the user removed: left out.
    {"title": "Delhi roads closed for the rally", "link": "https://timesofindia.indiatimes.com/city/delhi/x",
     "snippet": "Delhi Traffic Police.", "date": "1 day ago", "source": "TOI"},
    {"title": "Delhi diversions announced", "link": "https://www.thehansindia.com/news/delhi-x",
     "snippet": "Delhi.", "date": "1 day ago", "source": "Hans"},
]  # fmt: skip


def delhi_search(**options):
    calls = {"searches": [], "pages": [], "gl": set()}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "google.serper.dev":
            body = json.loads(request.content)
            calls["searches"].append(body["q"])
            calls["gl"].add(body["gl"])
            return httpx.Response(200, json={"news": RESULTS})
        calls["pages"].append(str(request.url))
        return httpx.Response(200, text="<html><body>No structured data.</body></html>")

    source = serper_news_source(connected=True, city_id="delhi")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SerperNewsConnector.for_city(source, DELHI, "test-key", "ua", client=client, **options), calls


@pytest.fixture
def delhi():
    return delhi_search()


def test_a_city_search_keeps_only_results_about_the_city_from_usable_publishers(delhi):
    connector, calls = delhi
    records = connector.fetch()
    assert calls["searches"] == list(DELHI.discovery.queries)
    assert calls["gl"] == {"in"}
    assert [record.url for record in records] == [UNREVIEWED_URL, DELHI_PAGE_URL]
    assert {record.source_id for record in records} == {"google-news-serper-delhi"}


def test_a_city_search_reads_the_article_pages_as_hyderabads_does(delhi):
    connector, calls = delhi
    for record in connector.fetch():
        connector.complete(record)
    assert calls["pages"] == [UNREVIEWED_URL, DELHI_PAGE_URL]


def test_the_strict_mode_reads_a_page_only_where_its_publisher_permits_it():
    connector, calls = delhi_search(read_any_publisher=False)
    unreviewed, permitted = connector.fetch()
    kept = connector.complete(unreviewed)
    assert kept == unreviewed and calls["pages"] == []  # Google's result, the page never opened
    connector.complete(permitted)
    assert calls["pages"] == [DELHI_PAGE_URL]


def test_hyderabads_search_leaves_out_a_publisher_the_user_removed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"news": [
            {"title": "Hyderabad traffic diversions", "link": "https://www.thehansindia.com/hyderabad/x",
             "snippet": "Hyderabad.", "date": "1 day ago", "source": "The Hans India"},
        ]})  # fmt: skip

    connector = SerperNewsConnector(
        serper_news_source(connected=True), "k", "ua", queries=("q",),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )  # fmt: skip
    assert connector.fetch() == []
