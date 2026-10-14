import json
from datetime import datetime, timezone

import pytest

from packages.event_schema import EventType
from packages.source_models import RawSourceRecord
from services.extraction import ArticleRelevance, KeywordClassifier
from services.extraction.keyword_classifier import DEFAULT_CONFIG_PATH

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def article(title: str, summary: str = "", categories: tuple[str, ...] = ("Hyderabad",)):
    return RawSourceRecord(
        source_id="test-news",
        external_id=title,
        url=None,
        title=title,
        summary=summary or None,
        content_text=None,
        categories=list(categories),
        published_at=None,
        retrieved_at=NOW,
        raw={},
        content_hash="0" * 64,
    )


@pytest.fixture(scope="module")
def classifier() -> KeywordClassifier:
    return KeywordClassifier.from_file()


@pytest.mark.parametrize(
    "title, summary",
    [
        ("Traffic diversions at Lakeview Junction for 30 days", ""),
        ("Traffic restrictions in place for the festival", ""),
        ("Road closure near Orchard Flyover this weekend", ""),
        ("Motorists stranded as roads around the lake remain closed", ""),
        ("Heavy rain leaves colonies waterlogged", ""),
        ("Rain batters city", "Gusty winds disrupt traffic across the city."),
        ("Festival crowds swell", "Traffic gridlocked for hours near the venue."),
        ("Marathon on Sunday", "Traffic will be regulated along the route."),
    ],
)
def test_traffic_articles_are_relevant(classifier, title, summary):
    result = classifier.classify(article(title, summary))
    assert result.label is ArticleRelevance.RELEVANT_TRAFFIC_ARTICLE
    assert result.is_relevant
    assert result.matched_keywords
    assert result.city == "Hyderabad"


@pytest.mark.parametrize(
    "title, summary",
    [
        ("City cricket team lifts state trophy", "The home side won by six wickets."),
        # "trafficking" is not "traffic".
        ("Police bust human trafficking racket", "Three detained for trafficking."),
        ("Airport sees record air traffic in September", ""),
        # A single general mention of traffic is not enough.
        ("Road safety awareness programme held at school", "Students learnt traffic rules."),
        # Supporting words alone never qualify, however many there are.
        ("Offices to remain closed for the immersion procession", "A rally and a marathon too."),
        # The same general idea twice still counts once.
        ("Study on traffic congestion", "The study will look at traffic in the corridor."),
    ],
)
def test_other_articles_are_not_relevant(classifier, title, summary):
    result = classifier.classify(article(title, summary))
    assert result.label is ArticleRelevance.NOT_RELEVANT
    assert not result.is_relevant


def test_traffic_article_outside_the_city_scope_is_not_relevant(classifier):
    result = classifier.classify(
        article("Traffic diversions announced in Warangal", categories=("Warangal", "Telangana"))
    )
    assert result.score >= classifier.threshold
    assert result.city is None
    assert result.label is ArticleRelevance.NOT_RELEVANT


def test_scope_can_come_from_the_text_instead_of_the_category(classifier):
    result = classifier.classify(
        article("Traffic diversions in Secunderabad from Monday", categories=("News",))
    )
    assert result.is_relevant


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Traffic diversions at Lakeview Junction", EventType.TRAFFIC_DIVERSION),
        ("Colonies waterlogged after heavy rain", EventType.FLOODING),
        ("Traffic restrictions for the procession", EventType.PUBLIC_PROCESSION),
        ("Road widening work to slow traffic", EventType.ROAD_CONSTRUCTION),
        # A closure could be planned or an emergency: the type is left open.
        ("Road closure near Orchard Flyover", None),
        # Waterlogging is what the event is; the diversion is the measure taken.
        ("Traffic diversions as roads waterlogged", EventType.FLOODING),
        # Two equally strong, different suggestions: left open.
        ("Traffic diversion on Tank Bund as procession and convoy pass", None),
    ],
)
def test_event_type_is_suggested_only_when_clear(classifier, title, expected):
    assert classifier.classify(article(title)).event_type is expected


def test_longer_keyword_is_not_recounted_as_its_parts(classifier):
    result = classifier.classify(article("Traffic diversion announced"))
    assert result.matched_keywords == ["traffic diversion"]
    assert result.score == 3


def test_keywords_are_configurable(tmp_path):
    config = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["version"] = "custom"
    config["keywords"] = [{"term": "landslide", "weight": 3}]
    path = tmp_path / "keywords.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    custom = KeywordClassifier.from_file(path)
    assert custom.classify(article("Landslide blocks the ghat section")).is_relevant
    assert not custom.classify(article("Traffic diversions at Lakeview Junction")).is_relevant
    assert custom.classify(article("Landslide")).classifier_version == "custom"
