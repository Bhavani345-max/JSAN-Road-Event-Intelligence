"""Every RSS source runs on the same generic connector, differing only in configuration."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

import connectors.rss as rss_package
from connectors.base import ConnectorError
from connectors.registry import REGISTERED_SOURCES, get_registered_source
from connectors.rss import RssConnector
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.the_hindu import THE_HINDU
from packages.event_schema import EventStatus, EventType
from packages.source_models import IntegrationStatus, SourceType
from services.extraction import KeywordClassifier, build_event_from_article
from tests.support import RETRIEVED_AT, SOURCE_FIXTURES, parse_fixture

# Connected sources read by the RSS parser (official feeds have connectors of their own).
RSS_SOURCES = [
    source
    for source in REGISTERED_SOURCES
    if source.create_connector and source.definition.parser_type == "rss"
]
NEW_SOURCES = [THE_HINDU, DECCAN_CHRONICLE]

source_ids = lambda value: getattr(value, "source_id", None) or getattr(  # noqa: E731
    getattr(value, "definition", None), "source_id", None
)


@pytest.fixture(scope="module")
def classifier() -> KeywordClassifier:
    return KeywordClassifier.from_file()


# --- Source registration -----------------------------------------------------


def test_the_connected_rss_sources_are_registered_with_distinct_identities():
    ids = [source.definition.source_id for source in RSS_SOURCES]
    assert ids == [
        "telangana-today",
        "newsmeter",
        # South Africa, 16 October 2026 (decision 0033): free to use with credit.
        "sanews",
    ]
    # Disconnected by their publishers' terms: the two Siasat feeds on 14 October
    # 2026 (decision 0024); The Hindu (both cities) and Deccan Chronicle on 15
    # October 2026 (decision 0032); Mid-day on 16 October 2026 (decision 0033). The
    # Hans India was removed (decision 0026).
    assert len({source.definition.endpoint for source in RSS_SOURCES}) == len(ids)
    assert len({source.definition.source_name for source in RSS_SOURCES}) == len(ids)


@pytest.mark.parametrize(
    "source_id, domain",
    [("the-hindu", "thehindu.com"), ("the-hindu-bengaluru", "thehindu.com"),
     ("deccan-chronicle", "deccanchronicle.com"), ("mid-day-mumbai", "mid-day.com")],
)  # fmt: skip
def test_feeds_whose_terms_forbid_collection_are_registered_without_a_connector(source_id, domain):
    from connectors.restricted import RESTRICTED_PUBLISHERS, restricted_publisher
    from packages.source_models import CommercialUse, TermsStatus

    registered = get_registered_source(source_id)
    source = registered.definition
    assert registered.create_connector is None
    assert source.active is False
    assert source.integration_status is IntegrationStatus.TERMS_REVIEW_REQUIRED
    assert source.terms_status is TermsStatus.RESTRICTED
    assert source.commercial_use is CommercialUse.NOT_PERMITTED
    assert "Disconnected on 15 October 2026" in source.notes or (
        source_id == "mid-day-mumbai" and "Disconnected on 16 October 2026" in source.notes
    )
    assert RESTRICTED_PUBLISHERS[domain] in source.notes
    # No page of the publisher is read by any other path either.
    assert restricted_publisher(source.endpoint) == domain
    assert restricted_publisher(source.source_url) == domain


def test_the_hindu_parser_is_kept_for_reconnecting():
    assert THE_HINDU.source_name == "The Hindu"
    assert THE_HINDU.source_type is SourceType.RSS
    assert THE_HINDU.endpoint == "https://www.thehindu.com/news/cities/Hyderabad/feeder/default.rss"
    assert THE_HINDU.polling_frequency_minutes == 30


def test_deccan_chronicle_parser_is_kept_for_reconnecting():
    assert DECCAN_CHRONICLE.source_name == "Deccan Chronicle"
    assert DECCAN_CHRONICLE.source_type is SourceType.RSS
    assert DECCAN_CHRONICLE.endpoint == (
        "https://www.deccanchronicle.com/category/southern-states/telangana/google_feeds.xml"
    )
    assert DECCAN_CHRONICLE.polling_frequency_minutes == 30


@pytest.mark.parametrize("registered", RSS_SOURCES, ids=source_ids)
def test_news_feeds_are_discovery_only_and_their_terms_are_not_claimed_reviewed(registered):
    definition = registered.definition
    assert definition.authority_type == "NEWS_MEDIA"
    assert definition.source_tier == 4
    assert definition.terms_reviewed is False
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is True
    assert definition.parser_type == "rss"
    assert definition.endpoint.startswith("https://")
    assert definition.evidence_retention


@pytest.mark.parametrize("registered", RSS_SOURCES, ids=source_ids)
def test_every_rss_source_uses_the_generic_connector(registered):
    connector = registered.create_connector("REI-test-agent/1.0")
    # The generic class itself, not a per-publisher subclass.
    assert type(connector) is RssConnector
    assert connector.source == registered.definition
    assert connector.config.user_agent == "REI-test-agent/1.0"


def test_source_modules_contain_no_parsing_code():
    """A source is configuration only: it must not fetch or parse anything itself."""
    package_dir = Path(rss_package.__file__).parent
    for module in (
        "telangana_today",
        "the_hindu",
        "deccan_chronicle",
        "siasat",
        "newsmeter",
        "the_hans_india",
    ):
        code = (package_dir / f"{module}.py").read_text(encoding="utf-8")
        for forbidden in ("feedparser", "httpx", "def ", "class "):
            assert forbidden not in code, f"{module}.py contains {forbidden!r}"


# --- RSS parsing in each publisher's format ----------------------------------


def test_the_hindu_style_feed_is_parsed():
    records = parse_fixture(THE_HINDU, "the_hindu_style_feed.xml")
    # 6 items; the one with neither link nor GUID is skipped.
    assert len(records) == 5
    assert {record.source_id for record in records} == {"the-hindu"}

    first = records[0]
    assert first.title == "Traffic restrictions around Lakeview Stadium for Sunday’s marathon"
    assert first.external_id == "article-1001"
    assert first.url.endswith("/article1001.ece")
    assert first.categories == ["Hyderabad"]
    # 12:00 +0530 is 06:30 UTC.
    assert first.published_at == datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    assert first.retrieved_at == RETRIEVED_AT
    assert len(first.content_hash) == 64


def test_the_hindu_style_missing_fields():
    records = parse_fixture(THE_HINDU, "the_hindu_style_feed.xml")
    # Empty <description> and no article body are the norm for this feed.
    assert records[0].summary is None
    assert all(record.content_text is None for record in records)
    assert records[1].summary.startswith("Commuters were stranded on Station Road")


def test_deccan_chronicle_style_feed_is_parsed():
    records = parse_fixture(DECCAN_CHRONICLE, "deccan_chronicle_style_feed.xml")
    # 6 items; the one without a title is skipped.
    assert len(records) == 5
    assert {record.source_id for record in records} == {"deccan-chronicle"}

    first = records[0]
    assert first.title == "Traffic Diversions At Lakeview Junction In Hyderabad From Monday"
    # The GUID is the article URL.
    assert first.external_id == first.url
    assert first.url.endswith("traffic-diversions-at-lakeview-junction-2001")
    assert first.categories == ["Southern States,Telangana,Trending"]
    assert first.published_at == datetime(2026, 10, 1, 7, 0, tzinfo=timezone.utc)
    assert first.summary.startswith("Vehicles heading to Station Road")
    assert first.content_text.endswith("asked motorists to plan their journeys.")
    assert "<figure>" in first.raw["content_html"]
    assert first.raw["author"] == "DC Correspondent"


def test_deccan_chronicle_style_missing_fields():
    records = parse_fixture(DECCAN_CHRONICLE, "deccan_chronicle_style_feed.xml")
    no_body = next(record for record in records if "Warangal" in record.title)
    assert no_body.content_text is None
    assert no_body.raw["author"] is None


@pytest.mark.parametrize("source", NEW_SOURCES, ids=source_ids)
def test_empty_feed_yields_no_records(source):
    body = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'
    assert rss_package.create_rss_connector(source, "ua").parse(
        body, retrieved_at=RETRIEVED_AT
    ) == []


@pytest.mark.parametrize("source", NEW_SOURCES, ids=source_ids)
@pytest.mark.parametrize("body", [b"", b"<html><body>Service unavailable</body></html>", b"{}"])
def test_invalid_feed_is_rejected(source, body):
    connector = rss_package.create_rss_connector(source, "ua")
    with pytest.raises(ConnectorError, match=f"{source.source_id}: invalid feed"):
        connector.parse(body, retrieved_at=RETRIEVED_AT)


# --- Detection and event creation: same rules, same canonical event ----------


def events_from(source, filename, classifier):
    events = []
    for record in parse_fixture(source, filename):
        classification = classifier.classify(record)
        if classification.is_relevant:
            events.append(build_event_from_article(record, classification, now=RETRIEVED_AT))
    return events


def test_the_hindu_style_articles_become_events(classifier):
    events = events_from(THE_HINDU, "the_hindu_style_feed.xml", classifier)
    assert [event.title.split()[0] for event in events] == ["Traffic", "Heavy"]

    restrictions, flooding = events
    assert restrictions.source_id == "the-hindu"
    # "restrictions" is the measure; the headline says the event is a marathon.
    assert restrictions.event_type is EventType.MARATHON
    assert restrictions.description is None  # the feed gave no summary
    assert restrictions.affected_road is None
    # Tagged "Telangana", but the headline places it in Secunderabad.
    assert flooding.city == "Hyderabad"
    assert flooding.event_type is EventType.FLOODING
    assert flooding.affected_road == "Station Road"


def test_deccan_chronicle_style_articles_become_events(classifier):
    events = events_from(DECCAN_CHRONICLE, "deccan_chronicle_style_feed.xml", classifier)
    assert [event.title.split()[0] for event in events] == ["Traffic", "Hyderabad:"]

    diversion, closure = events
    assert diversion.source_id == "deccan-chronicle"
    assert diversion.event_type is EventType.TRAFFIC_DIVERSION
    assert diversion.source_reference.endswith("traffic-diversions-at-lakeview-junction-2001")
    # Roads come from the sentence-case summary; the Title Case headline is not
    # mined for names, because there every word is capitalised.
    assert diversion.affected_road == "Station Road; Lakeview Junction"
    assert closure.affected_road is None


@pytest.mark.parametrize("source, filename", SOURCE_FIXTURES, ids=source_ids)
def test_every_source_produces_the_same_canonical_event(source, filename, classifier):
    events = events_from(source, filename, classifier)
    assert events
    for event in events:
        assert event.source_id == source.source_id
        assert event.status is EventStatus.VALIDATION_REQUIRED
        assert event.event_id.startswith("EVT-")
        assert event.detection.method == "keyword_rules"
        for unknown in ("start_time", "end_time", "severity", "direction", "geometry", "confidence"):
            assert getattr(event, unknown) is None, unknown


@pytest.mark.parametrize("source, filename", SOURCE_FIXTURES, ids=source_ids)
def test_out_of_scope_and_unrelated_articles_create_no_event(source, filename, classifier):
    titles = [event.title for event in events_from(source, filename, classifier)]
    assert not any("Warangal" in title for title in titles)
    assert not any("rafficking" in title for title in titles)


@pytest.mark.parametrize("source_id", [
    "new-indian-express-hyderabad", "new-indian-express-bengaluru", "new-indian-express-chennai",
    "new-indian-express-delhi", "new-indian-express-mumbai", "new-indian-express-kolkata",
    "millennium-post-delhi", "millennium-post-kolkata",
])  # fmt: skip
def test_feeds_whose_terms_do_not_permit_reis_use_wait_for_permission_unread(source_id):
    # Decision 0033: verified working on 16 October 2026, but nothing in the
    # publishers' terms permits commercial use; never fetched until permission.
    from packages.source_models import CommercialUse, IntegrationStatus

    registered = get_registered_source(source_id)
    source = registered.definition
    assert registered.create_connector is None
    assert source.integration_status is IntegrationStatus.TERMS_REVIEW_REQUIRED and not source.active
    assert source.commercial_use is CommercialUse.UNKNOWN and not source.terms_reviewed
    assert "written permission" in source.access_method
