"""City configuration (6 October 2026): nothing about a city is hard-coded in the pipeline."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from packages.cities import DEFAULT_CITY_ID, City, MapView, default_city, get_city, load_cities
from packages.source_models import RawSourceRecord
from services.extraction import KeywordClassifier, build_event_from_article
from services.extraction.stated_period import find_stated_period
from services.geo_resolution import resolver_for

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def test_hyderabad_is_the_default_city_and_london_is_configured():
    cities = load_cities()
    assert DEFAULT_CITY_ID == "hyderabad" and list(cities)[0] == "hyderabad"
    assert default_city().name == "Hyderabad"
    assert set(cities) >= {"hyderabad", "london"}


def test_hyderabad_configuration_matches_what_the_pipeline_used_before():
    hyderabad = get_city("hyderabad")
    assert (hyderabad.country, hyderabad.region, hyderabad.timezone) == (
        "IN",
        "Telangana",
        "Asia/Kolkata",
    )
    assert hyderabad.bbox == (17.18, 78.15, 17.68, 78.75)
    assert "Hyderabad" in hyderabad.scope_terms and "Secunderabad" in hyderabad.scope_terms
    assert hyderabad.gazetteer == "hyderabad_places.json"
    assert len(hyderabad.discovery.queries) == 12
    assert hyderabad.covers(17.4065, 78.4747) and not hyderabad.covers(51.5, -0.1)


def test_london_configuration():
    london = get_city("london")
    assert (london.country, london.timezone, london.language) == ("GB", "Europe/London", "en")
    assert london.tz == ZoneInfo("Europe/London")
    assert "London" in london.scope_terms
    assert "Hyderabad" in london.other_cities
    assert london.official_sources == ("tfl-road-disruptions",)
    assert london.covers(51.5072, -0.1276)


def test_an_unknown_city_is_an_error():
    with pytest.raises(KeyError):
        get_city("atlantis")


def _city(**overrides) -> City:
    values = dict(
        id="testville", name="Testville", country="XX", timezone="UTC",
        bbox=(10.0, 20.0, 11.0, 21.0), map=MapView(center=(20.5, 10.5), zoom=10),
        scope_terms=("Testville",),
    )  # fmt: skip
    values.update(overrides)
    return City(**values)


def test_a_city_boundary_must_be_well_formed():
    with pytest.raises(ValidationError, match="south, west, north, east"):
        _city(bbox=(11.0, 20.0, 10.0, 21.0))
    with pytest.raises(ValidationError, match="outside the bbox"):
        _city(map=MapView(center=(0.0, 0.0), zoom=10))
    with pytest.raises(ValidationError, match="unknown timezone"):
        _city(timezone="Mars/Olympus")


def article(title, summary=None, body=None):
    return RawSourceRecord(
        source_id="test", external_id=title, url=None, title=title, summary=summary,
        content_text=body, categories=[], published_at=NOW, retrieved_at=NOW, raw={},
        content_hash="0" * 64,
    )  # fmt: skip


def test_the_classifier_takes_its_scope_from_the_city():
    london = KeywordClassifier.for_city(get_city("london"))
    hyderabad = KeywordClassifier.for_city(get_city("hyderabad"))
    record = article("London road closure: A40 Westway shut for 55 hours this weekend")
    assert london.classify(record).city == "London"
    assert london.classify(record).is_relevant
    assert hyderabad.classify(record).city is None
    # And the other way round.
    record = article("Traffic diversions in Hyderabad for the procession")
    assert hyderabad.classify(record).is_relevant
    assert not london.classify(record).is_relevant


def test_a_citys_own_name_is_never_one_of_its_other_cities():
    london = KeywordClassifier.for_city(get_city("london"))
    assert london.classify(article("London traffic diversions at Hyde Park Corner")).is_relevant


def test_stated_dates_are_whole_days_in_the_citys_zone():
    london_tz = ZoneInfo("Europe/London")
    found = find_stated_period(
        title="Road closed from October 10 to October 12", published_at=NOW, zone=london_tz
    )
    assert found.start == datetime(2026, 10, 10, tzinfo=london_tz)
    assert found.end == datetime(2026, 10, 12, 23, 59, 59, tzinfo=london_tz)
    # Without a city, as before: India Standard Time.
    default = find_stated_period(title="Road closed from October 10 to October 12", published_at=NOW)
    assert default.start.utcoffset() == timedelta(hours=5, minutes=30)


def test_an_event_for_a_london_article_is_dated_in_london_time():
    london = get_city("london")
    classifier = KeywordClassifier.for_city(london)
    record = article("London: Tower Bridge closed from October 10 to October 12 for repairs")
    event = build_event_from_article(
        record, classifier.classify(record), now=NOW, resolver=resolver_for(london), city=london
    )
    assert event.city == "London"
    assert event.start_time.utcoffset() == ZoneInfo("Europe/London").utcoffset(event.start_time)


def test_a_city_without_a_gazetteer_locates_nothing_but_knows_its_area():
    resolver = resolver_for(_city(gazetteer="no-such-file.json"))
    assert len(resolver) == 0
    assert resolver.find_places(title="Diversions at Khajaguda junction") == []
    assert resolver.covers(10.5, 20.5) and not resolver.covers(17.4, 78.4)
