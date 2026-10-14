"""Publishers whose terms forbid automated access are never read (14 October 2026, decision 0024).

The Siasat Daily's terms allow personal, non-commercial use only and forbid
robots, scrapers and "other automated means to access, extract, or index the
Content without prior written permission". No request may reach siasat.com:
not its feeds, not its article pages (directly, by redirect or from a search
result), and its articles are never sent to an AI model.
"""

import json

import httpx
import pytest

from connectors.api.serper_news import SerperNewsConnector, serper_news_source
from connectors.base import ConnectorError
from connectors.html.article import download_page
from connectors.registry import REGISTERED_SOURCES, get_registered_source
from connectors.restricted import restricted_publisher
from packages.source_models import CommercialUse, IntegrationStatus, TermsStatus

SIASAT_ARTICLE = "https://www.siasat.com/hyderabad-traffic-diversions-at-khajaguda-1234567/"
OTHER_ARTICLE = "https://news.example.com/khajaguda-restrictions"


@pytest.mark.parametrize(
    "url, expected",
    [
        (SIASAT_ARTICLE, "siasat.com"),
        ("https://siasat.com/news/hyderabad/feed/", "siasat.com"),
        ("http://m.SIASAT.com./amp/story", "siasat.com"),
        ("https://notsiasat.com/a", None),
        ("https://siasat.com.example.org/a", None),
        (OTHER_ARTICLE, None),
        ("", None),
        (None, None),
    ],
)
def test_restricted_hosts_are_recognised_by_domain(url, expected):
    assert restricted_publisher(url) == expected


@pytest.mark.parametrize("source_id", ["siasat", "siasat-mumbai"])
def test_the_siasat_feeds_stay_registered_but_are_never_fetched(source_id):
    registered = get_registered_source(source_id)
    definition = registered.definition
    assert registered.create_connector is None
    assert definition.integration_status is IntegrationStatus.TERMS_REVIEW_REQUIRED
    assert definition.active is False
    assert definition.terms_status is TermsStatus.RESTRICTED
    assert definition.commercial_use is CommercialUse.NOT_PERMITTED
    # The terms were read, not formally reviewed by a lawyer.
    assert definition.terms_reviewed is False
    assert "without prior written permission" in definition.notes


def test_no_connected_source_reads_a_restricted_publisher():
    for registered in REGISTERED_SOURCES:
        if registered.create_connector is not None:
            for url in (registered.definition.endpoint, registered.definition.source_url):
                assert restricted_publisher(url) is None, registered.definition.source_id


def recording_client(routes: dict[str, httpx.Response]) -> tuple[httpx.Client, list[str]]:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return routes.get(str(request.url), httpx.Response(404))

    return httpx.Client(transport=httpx.MockTransport(handler)), requested


def test_a_restricted_page_is_refused_before_any_request():
    client, requested = recording_client({})
    with pytest.raises(ConnectorError, match="siasat.com does not permit automated access"):
        download_page(SIASAT_ARTICLE, "ua", client=client)
    assert requested == []


def test_a_redirect_to_a_restricted_publisher_is_not_followed():
    short = "https://short.example.com/x"
    client, requested = recording_client(
        {short: httpx.Response(301, headers={"Location": SIASAT_ARTICLE})}
    )
    with pytest.raises(ConnectorError, match="siasat.com"):
        download_page(short, "ua", client=client)
    assert requested == [short]


def test_ordinary_redirects_are_still_followed():
    moved = "https://old.example.com/story"
    client, requested = recording_client(
        {
            moved: httpx.Response(302, headers={"Location": OTHER_ARTICLE}),
            OTHER_ARTICLE: httpx.Response(200, text="<html>page</html>"),
        }
    )
    assert download_page(moved, "ua", client=client) == (OTHER_ARTICLE, "<html>page</html>")
    assert requested == [moved, OTHER_ARTICLE]


def test_search_results_linking_to_a_restricted_publisher_are_dropped():
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "google.serper.dev":
            title = f"Traffic diversions at Khajaguda junction in Hyderabad ({json.loads(request.content)['q']})"
            return httpx.Response(
                200,
                json={
                    "news": [
                        {"title": title, "link": SIASAT_ARTICLE, "snippet": "Hyderabad diversions"},
                        {"title": title, "link": OTHER_ARTICLE, "snippet": "Hyderabad diversions"},
                    ]
                },
            )
        requested.append(str(request.url))
        return httpx.Response(404)

    connector = SerperNewsConnector(
        serper_news_source(connected=True),
        "test-key",
        "ua",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    records = connector.fetch()
    assert [record.url for record in records] == [OTHER_ARTICLE]
    for record in records:
        connector.complete(record)
    assert SIASAT_ARTICLE not in requested
