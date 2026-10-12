"""Detection rules of 6 October 2026: wordings the earlier rules missed, and scope.

The headlines are ones Google News returned for Hyderabad road searches on
5 and 6 October 2026 that the rules of 5 October did not detect, or detected
although they were about another city.
"""

from datetime import datetime, timezone

import pytest

from packages.event_schema import EventType
from packages.source_models import RawSourceRecord
from services.extraction import KeywordClassifier
from services.geo_resolution import default_resolver

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)


def article(title, summary="", categories=(), body=None):
    return RawSourceRecord(
        source_id="google-news-serper",
        external_id=title,
        url="https://news.example.com/" + title[:20].lower().replace(" ", "-"),
        title=title,
        summary=summary or None,
        content_text=body,
        categories=list(categories),
        published_at=NOW,
        retrieved_at=NOW,
        raw={},
        content_hash="0" * 64,
    )


@pytest.fixture(scope="module")
def classifier():
    return KeywordClassifier.from_file()


@pytest.fixture(scope="module")
def placing_classifier():
    """The classifier as the API runs it: with the place resolver."""
    return KeywordClassifier.from_file(place_resolver=default_resolver())


@pytest.mark.parametrize(
    "title, summary, signal",
    [
        ("Hyderabad residents flag blocked roads to HYDRAA", "", "road blocked"),
        ("Hyderabad police block roads around Tank Bund", "", "road blocked"),
        (
            "Hyderabad: Why has one-way traffic system around KBR Park been made permanent",
            "",
            "one-way",
        ),
        ("Traffic alert: Hyderabad motorists told to avoid Begumpet", "", "traffic alert"),
        (
            "Hyderabad: Vehicles barred on Necklace Road for the marathon",
            "",
            "vehicles barred",
        ),
        ("Hyderabad flyover shut for repairs", "The Begumpet flyover will remain shut.", "flyover/bridge/tunnel closed"),
        ("Secunderabad road caves in after rain", "", "road cave-in"),
        (
            "Srinagar Colony road dug up again",
            "Hyderabad: The stretch was dug up for a pipeline.",
            "road dug up",
        ),
        (
            "Traffic restrictions to continue in Hyderabad on Ganesh immersion routes",
            "",
            "restrictions imposed",
        ),
        ("Hyderabad: Route diversion at Koti for the procession", "", "route diversion"),
        ("No entry for lorries in Hyderabad during Bathukamma", "", "no entry"),
    ],
)
def test_wordings_the_papers_use_for_road_measures_are_detected(
    classifier, title, summary, signal
):
    result = classifier.classify(article(title, summary))
    assert result.is_relevant, result
    assert signal in result.matched_keywords


@pytest.mark.parametrize(
    "title, summary",
    [
        # Named in a Hyderabad search, but about another city.
        ("Race Course Road Traffic Diversion in Bengaluru for 60 Days", "Unlike Hyderabad…"),
        ("Delhi Traffic Advisory: Diversions Near Jantar Mantar on October 2", "Hyderabad too"),
        ("Navi Mumbai Traffic Updates: Thane-Belapur Road To Shut On 4 Nights", "Hyderabad"),
        # Not road measures.
        ("Hyderabad Traffic Police book 380 drunk drivers in two-day special drive", ""),
        ("GHMC Elevated Corridor: Rs. 1,090 Crore Flyover Plan", "Hyderabad"),
        ("Bathukamma celebrations to be held across Telangana from October 10 to 18", "Hyderabad"),
    ],
)
def test_other_cities_and_non_measures_are_still_left_out(classifier, title, summary):
    assert not classifier.classify(article(title, summary)).is_relevant


def test_a_highway_named_after_another_city_is_not_that_city(classifier):
    result = classifier.classify(
        article("Traffic diversions on Mumbai Highway near Miyapur", "Hyderabad: …")
    )
    assert result.is_relevant and result.city == "Hyderabad"


def test_a_known_hyderabad_locality_in_the_headline_puts_an_article_in_scope(
    classifier, placing_classifier
):
    # "Hyderabad" is not written anywhere; Patancheru is a Hyderabad locality.
    record = article("Sangareddy-Patancheru: traffic diversions for road widening works")
    assert not classifier.classify(record).is_relevant
    result = placing_classifier.classify(record)
    assert result.is_relevant and result.city == "Hyderabad"


def test_a_locality_name_does_not_put_an_article_about_another_city_in_scope(
    placing_classifier,
):
    # Gandhi Nagar exists in Hyderabad and in many other cities.
    record = article("Traffic diversions at Gandhi Nagar", "Diversions in Bengaluru from Monday.")
    assert not placing_classifier.classify(record).is_relevant


def test_a_landmark_name_alone_does_not_put_an_article_in_scope(placing_classifier):
    # A hospital of this name may be anywhere; a place name is not a city.
    record = article("Traffic diversions near Apollo Hospital for 10 days")
    assert placing_classifier.classify(record).city is None


def test_advisory_phrases_do_not_decide_the_event_type(classifier):
    # "Alternate routes" accompany any measure; the works are the event named.
    result = classifier.classify(
        article("Traffic curbs for flyover works", "Hyderabad: commuters advised to take alternate routes.")
    )
    assert result.is_relevant
    assert result.event_type is EventType.ROAD_CONSTRUCTION
