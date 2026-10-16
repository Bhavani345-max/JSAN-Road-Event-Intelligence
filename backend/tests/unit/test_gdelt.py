"""GDELT news search connector (16 October 2026).

The fixture is a real DOC 2.0 response saved on 16 October 2026 (a search for
Delhi). No test calls GDELT.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from connectors.base import ConnectorError
from connectors.discovery.gdelt import (
    API_URL,
    GdeltConnector,
    _Pace,
    clean_title,
    gdelt_source,
    parse_seendate,
    queries_for,
)
from connectors.registry import registered_sources
from packages.cities import get_city, load_cities
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass

DOCUMENT = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "gdelt_doc_delhi_2026-10-16.json").read_text(encoding="utf-8")
)
DELHI = get_city("delhi")
ARTICLE_URL = (
    "http://www.indiagazette.com/news/279377723/delhi-security-forces-deployed-in-and-around-"
    "connaught-place-ahead-of-lehra-do-tiranga-protest"
)
# LiveMint: HT Digital Streams' terms forbid scrapers (connectors/restricted.py).
RESTRICTED_URL = (
    "https://www.livemint.com/news/india/delhi-traffic-advisory-today-20-roads-around-connaught-"
    "place-restricted-from-3-pm-for-cjps-tiranga-march-11792115666103.html"
)
ARTICLE_PAGE = """<html><head><script type="application/ld+json">
{"@type": "NewsArticle",
 "headline": "Delhi traffic advisory today: 21 roads around Connaught Place restricted from 3 PM",
 "description": "Delhi Traffic Police restrict traffic around Connaught Place on October 16.",
 "datePublished": "2026-10-16T09:40:00+05:30",
 "articleBody": "New Delhi: The Delhi Traffic Police said traffic will be restricted on 21 roads."}
</script></head><body></body></html>"""


def connector(handler, *, city=DELHI, sleep=None, clock=None, pace=None) -> GdeltConnector:
    return GdeltConnector(
        gdelt_source(city),
        city,
        "ua",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleep or (lambda seconds: None),
        clock=clock or (lambda: 0.0),
        pace=pace or _Pace(),
    )


def answer(document=DOCUMENT, status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(API_URL):
            if isinstance(document, str):
                return httpx.Response(status, text=document)
            return httpx.Response(status, json=document)
        return httpx.Response(200, text=ARTICLE_PAGE)

    return handler


def test_a_city_search_names_the_city_asks_for_road_phrases_and_its_country_press():
    (query,) = queries_for(DELHI)
    assert query.startswith('"Delhi" (')
    assert '"traffic advisory" OR "traffic diversion"' in query
    assert query.endswith("sourcecountry:IN sourcelang:english")
    # South Africa searches its whole press; GDELT's code for it is SF, not ZA.
    (za,) = queries_for(get_city("south-africa"))
    assert "sourcecountry:SF" in za and '"roadworks"' in za


def test_the_search_asks_gdelt_for_a_day_of_articles_as_json():
    seen = []

    def handler(request):
        seen.append(request.url)
        return httpx.Response(200, json={})

    connector(handler).fetch()
    (url,) = seen
    assert url.params["mode"] == "ArtList" and url.params["format"] == "json"
    assert url.params["timespan"] == "1d" and url.params["maxrecords"] == "250"
    assert url.params["query"] == queries_for(DELHI)[0]


def test_results_become_records_with_the_publishers_headline_as_written():
    records = {record.url: record for record in connector(answer()).fetch()}
    result = records[ARTICLE_URL]
    assert result.title == (
        "Delhi: Security forces deployed in and around Connaught Place ahead of Lehra Do "
        "Tiranga protest"
    )
    assert result.published_at == datetime(2026, 10, 16, 7, 30, tzinfo=timezone.utc)
    assert result.raw["search_result"]["domain"] == "indiagazette.com"
    assert result.source_id == "gdelt-delhi" and result.content_text is None


def test_publishers_whose_terms_forbid_scraping_are_left_out_of_a_real_response():
    urls = {record.url for record in connector(answer()).fetch()}
    assert RESTRICTED_URL not in urls
    assert not any("indiatimes.com" in url or "livemint.com" in url for url in urls)


def test_results_that_do_not_name_the_city_are_left_out():
    titles = [record.title for record in connector(answer()).fetch()]
    assert titles and all("Delhi" in title or "NDMC" in title for title in titles)
    assert not any(title.startswith("NYT Fact") for title in titles)


def test_restricted_publishers_and_other_cities_are_left_out_before_anything_is_stored():
    document = {
        "articles": [
            {"url": "https://www.thehindu.com/news/cities/Delhi/roads-closed.ece",
             "title": "Delhi : roads closed for march", "seendate": "20261016T074500Z"},
            {"url": "https://www.thehansindia.com/news/cities/delhi-diversions",
             "title": "Delhi diversions for march", "seendate": "20261016T074500Z"},
            {"url": "https://news.example.com/mumbai-diversions",
             "title": "Mumbai traffic diversions as Delhi team visits", "seendate": "20261016T074500Z"},
            {"url": "https://news.example.com/mumbai-only",
             "title": "Mumbai traffic diversions for the procession", "seendate": "20261016T074500Z"},
        ]
    }  # fmt: skip
    urls = {record.url for record in connector(answer(document)).fetch()}
    # The headline names Delhi too, so it stays; one naming only Mumbai does not.
    assert urls == {"https://news.example.com/mumbai-diversions"}


def test_a_refusal_or_a_message_instead_of_results_fails_the_poll():
    message = "Please limit requests to one every 5 seconds or contact us for larger queries."
    with pytest.raises(ConnectorError, match="refused the request \\(HTTP 429\\)"):
        connector(answer(message, status=429)).fetch()
    with pytest.raises(ConnectorError, match="did not run the search"):
        connector(answer("The specified phrase is too short.")).fetch()


def test_no_results_is_an_empty_poll():
    assert connector(answer({})).fetch() == []
    assert connector(answer("")).fetch() == []


def test_requests_are_kept_six_seconds_apart_across_searches():
    now = [100.0]
    pauses = []

    def sleep(seconds):
        pauses.append(seconds)
        now[0] += seconds

    pace = _Pace()
    two = GdeltConnector(
        gdelt_source(DELHI), DELHI, "ua", queries=("a", "b"),
        client=httpx.Client(transport=httpx.MockTransport(answer({}))),
        sleep=sleep, clock=lambda: now[0], pace=pace,
    )  # fmt: skip
    two.fetch()
    # The first request goes at once; the second waits out the gap.
    assert pauses == [pytest.approx(6.0)]


SANEWS_URL = "https://www.sanews.gov.za/south-africa/roads-closed-cape-town-cycle-tour"
SANEWS_DOCUMENT = {
    "articles": [
        {"url": SANEWS_URL, "title": "Roads closed in Cape Town for the Cycle Tour",
         "seendate": "20261016T074500Z", "domain": "sanews.gov.za"},
    ]
}  # fmt: skip


def test_an_article_is_read_from_its_page_only_where_the_publishers_terms_permit_it():
    za = get_city("south-africa")
    gdelt = connector(answer(SANEWS_DOCUMENT), city=za)
    (record,) = gdelt.fetch()
    article = gdelt.complete(record)
    assert article.title.startswith("Delhi traffic advisory today: 21 roads")  # the page's own
    assert "restricted on 21 roads" in article.content_text
    assert article.published_at == datetime(2026, 10, 16, 4, 10, tzinfo=timezone.utc)
    assert article.raw["search_result"]["domain"] == "sanews.gov.za"


def test_any_other_publishers_page_is_never_requested():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return answer()(request)

    gdelt = connector(handler)
    records = gdelt.fetch()
    assert all(gdelt.complete(record) is record for record in records)
    # Only the search itself was sent; GDELT's headline, address and time are kept.
    assert len(requested) == 1 and requested[0].startswith(API_URL)


def test_a_page_without_an_article_keeps_gdelts_result():
    def handler(request):
        if str(request.url).startswith(API_URL):
            return httpx.Response(200, json=SANEWS_DOCUMENT)
        return httpx.Response(200, text="<html><body>No structured data</body></html>")

    gdelt = connector(handler, city=get_city("south-africa"))
    (record,) = gdelt.fetch()
    assert gdelt.complete(record) is record


def test_gdelt_titles_and_times_are_read_as_written():
    assert clean_title("Delhi Deploys 27 , 000 Personnel , Section 163 in Force") == (
        "Delhi Deploys 27,000 Personnel, Section 163 in Force"
    )
    assert clean_title("  Delhi : Security  forces ?") == "Delhi: Security forces?"
    assert parse_seendate("20261016T074500Z") == datetime(2026, 10, 16, 7, 45, tzinfo=timezone.utc)
    assert parse_seendate("yesterday") is None


def test_every_city_with_a_place_list_has_one_search_source_and_only_those():
    sources = {
        s.definition.source_id: s
        for s in registered_sources(gdelt_enabled=True)
        if s.definition.source_id.startswith("gdelt-")
    }
    with_places = {f"gdelt-{city.id}" for city in load_cities().values() if city.gazetteer}
    assert set(sources) == with_places and "gdelt-south-africa" in sources
    for registered in sources.values():
        definition = registered.definition
        assert definition.integration_status is IntegrationStatus.CONNECTED and definition.active
        assert definition.source_class is SourceClass.DISCOVERY and definition.discovery_only
        assert definition.source_tier == 4 and not definition.terms_reviewed
        assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
        assert registered.create_connector is not None


def test_gdelt_is_off_by_default_listed_but_never_run():
    # Decision 0033: GDELT's API refused 33 of 44 requests on 16 October 2026.
    from app.core.config import Settings

    assert Settings(_env_file=None).gdelt_search_enabled is False
    off = [s for s in registered_sources() if s.definition.source_id.startswith("gdelt-")]
    assert off and all(s.create_connector is None and not s.definition.active for s in off)
    assert all(s.definition.integration_status is IntegrationStatus.DISABLED for s in off)


# --- through the pipeline ------------------------------------------------------


def test_syndicated_copies_in_one_poll_are_stored_once(session):
    # The Delhi response of 16 October 2026 lists three stories twice, on two
    # sites each (ANI and India Gazette, IANS and Prokerala): one copy is kept.
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion

    gdelt = connector(answer())
    SourceRepository(session).sync_registry([gdelt.source])
    session.commit()
    result = run_ingestion(gdelt, KeywordClassifier.from_file(), SqlIngestionStore(session))
    session.commit()
    assert (result.fetched, result.new_artifacts, result.duplicates) == (10, 7, 3)


def test_a_publishers_own_feed_keeps_two_items_with_one_headline(session):
    # Two items of one feed may share a headline ("Traffic advisory") and be
    # different reports: only search sources compare headlines.
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from connectors.rss.telangana_today import TELANGANA_TODAY
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion
    from tests.support import FakeConnector, khajaguda_article

    first = khajaguda_article()
    second = first.model_copy(update={"external_id": "p=2", "url": "https://telanganatoday.com/second"})
    SourceRepository(session).sync_registry([TELANGANA_TODAY])
    session.commit()
    result = run_ingestion(
        FakeConnector([first, second], source=TELANGANA_TODAY),
        KeywordClassifier.from_file(),
        SqlIngestionStore(session),
    )
    assert (result.new_artifacts, result.duplicates) == (2, 0)


# --- refusals, cooldown, cache (decision 0034) -------------------------------------


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _counting(responses):
    """A transport answering GDELT searches from `responses` in turn, counting them."""
    sent = []

    def handler(request):
        sent.append(str(request.url))
        status, body, headers = responses[min(len(sent) - 1, len(responses) - 1)]
        return httpx.Response(status, text=body, headers=headers)

    return handler, sent


def _connector(handler, guard, clock, city=DELHI):
    return GdeltConnector(
        gdelt_source(city), city, "ua",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda seconds: None, clock=clock, pace=guard, min_seconds_between_requests=0,
    )  # fmt: skip


REFUSAL = (429, "Please limit requests to one every 5 seconds.", {})
EMPTY = (200, "{}", {"Cache-Control": "public, max-age=900"})


def test_a_refusal_stops_every_gdelt_request_for_a_bounded_growing_time():
    from connectors.discovery.gdelt import COOLDOWN_BASE_SECONDS, COOLDOWN_MAX_SECONDS

    guard, clock = _Pace(), Clock()
    handler, sent = _counting([REFUSAL])
    with pytest.raises(ConnectorError, match=r"refused the request \(HTTP 429\).*no request before"):
        _connector(handler, guard, clock).fetch()
    assert len(sent) == 1
    # During the cooldown no request is sent at all, for any city.
    for city in (DELHI, get_city("mumbai"), get_city("south-africa")):
        with pytest.raises(ConnectorError, match="cooling down after a refusal: no request sent"):
            _connector(handler, guard, clock, city).fetch()
    assert len(sent) == 1
    # After it, one request; refused again, the cooldown doubles ...
    clock.now += COOLDOWN_BASE_SECONDS + 1
    with pytest.raises(ConnectorError, match="refused"):
        _connector(handler, guard, clock).fetch()
    assert len(sent) == 2 and guard.cooldown_until - clock.now == 2 * COOLDOWN_BASE_SECONDS
    # ... up to a day at most.
    for _ in range(12):
        clock.now = guard.cooldown_until + 1
        with pytest.raises(ConnectorError):
            _connector(handler, guard, clock).fetch()
    assert guard.cooldown_until - clock.now == COOLDOWN_MAX_SECONDS


def test_an_answer_resets_the_cooldown():
    guard, clock = _Pace(), Clock()
    handler, _sent = _counting([REFUSAL, EMPTY])
    with pytest.raises(ConnectorError):
        _connector(handler, guard, clock).fetch()
    clock.now = guard.cooldown_until + 1
    assert _connector(handler, guard, clock).fetch() == []
    assert guard.refusals == 0 and guard.cooling_down(clock) == 0


def test_gdelts_limit_message_with_status_200_counts_as_a_refusal():
    guard, clock = _Pace(), Clock()
    handler, _sent = _counting([(200, "Please limit requests to one every 5 seconds or contact us.", {})])
    with pytest.raises(ConnectorError, match="refused"):
        _connector(handler, guard, clock).fetch()
    assert guard.cooling_down(clock) > 0


def test_the_same_search_within_its_freshness_is_answered_from_the_cache():
    guard, clock = _Pace(), Clock()
    handler, sent = _counting([EMPTY])
    _connector(handler, guard, clock).fetch()
    _connector(handler, guard, clock).fetch()
    assert len(sent) == 1
    clock.now += 901  # GDELT's max-age=900 has passed
    _connector(handler, guard, clock).fetch()
    assert len(sent) == 2


def test_with_gdelt_disabled_the_api_has_no_gdelt_connector_and_polls_none(engine, session):
    from app.core.config import Settings
    from app.main import create_app
    from app.repositories.sources import SourceRepository

    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=False,
    )  # fmt: skip
    app = create_app(settings, engine=engine)
    service = app.state.ingestion_service
    assert not any(source_id.startswith("gdelt-") for source_id in service.connector_factories)
    SourceRepository(session).sync_registry(s.definition for s in service.sources)
    session.commit()
    rows = [s for s in SourceRepository(session).list() if s.source_id.startswith("gdelt-")]
    assert rows and all(r.integration_status == "DISABLED" and not r.active for r in rows)
    # Nothing else is polled in this test: only GDELT's rows are looked at.
    service.connector_factories = {}
    assert service.run_due() == []
