"""Countries and the cities within them (decisions 0035, 0036).

Canada is a country entry and Toronto a city within it; the United States a
country entry and New York City a city within it; India a country entry with
no source of its own and its eight cities within it. Choosing a country covers
its own events and its cities' events; choosing a city covers that city's
only. Nothing is copied: events keep the city they were recorded with.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Event
from packages.cities import area_of, cities_within, country_entry, get_city, load_cities
from packages.common.time import utc_now

NOW = datetime.now(timezone.utc)
POINT = {"type": "Point", "coordinates": [-79.38, 43.65]}
# event id: (city as events record it, source, status)
EVENTS = {
    "EVT-CA-NATIONAL": ("Canada", "drivebc-events", "VALIDATION_REQUIRED"),
    "EVT-CA-TORONTO": ("Toronto", "toronto-road-restrictions", "VALIDATION_REQUIRED"),
    "EVT-CA-TORONTO-OK": ("Toronto", "toronto-road-restrictions", "APPROVED"),
    "EVT-US-NATIONAL": ("United States", "wzdx-deldot", "VALIDATION_REQUIRED"),
    "EVT-US-NYC": ("New York City", "nyc-street-closures", "VALIDATION_REQUIRED"),
    "EVT-IN-DELHI": ("Delhi", "gdelt-delhi", "VALIDATION_REQUIRED"),
    "EVT-IN-HYDERABAD": ("Hyderabad", "telangana-today", "VALIDATION_REQUIRED"),
    # Recorded before cities existed: Hyderabad's (as the list treats them).
    "EVT-IN-LEGACY": (None, "telangana-today", "VALIDATION_REQUIRED"),
    "EVT-GB-LONDON": ("London", "tfl-road-disruptions", "VALIDATION_REQUIRED"),
}
INDIAN_CITIES = {"hyderabad", "ahmedabad", "bengaluru", "chennai", "delhi", "kolkata", "mumbai", "pune"}


# --- the configuration -------------------------------------------------------------


def test_toronto_is_a_city_within_canada_and_new_york_within_the_united_states():
    canada, toronto = get_city("canada"), get_city("toronto")
    assert (canada.level, toronto.level) == ("country", "city")
    assert toronto.country == canada.country == "CA"
    assert country_entry(toronto) == canada and country_entry(canada) is None
    assert cities_within(canada) == (toronto,)
    assert area_of(canada) == (canada, toronto) and area_of(toronto) == (toronto,)

    united_states, new_york = get_city("united-states"), get_city("new-york")
    assert (united_states.level, new_york.level) == ("country", "city")
    assert country_entry(new_york) == united_states
    assert area_of(united_states) == (united_states, new_york) and area_of(new_york) == (new_york,)


def test_india_covers_its_cities_with_no_source_of_its_own():
    india, delhi = get_city("india"), get_city("delhi")
    assert (india.level, india.country, india.official_sources) == ("country", "IN", ())
    assert country_entry(delhi) == india and area_of(delhi) == (delhi,)
    assert {city.id for city in cities_within(india)} == INDIAN_CITIES
    assert area_of(india)[0] == india
    for city_id, country_id in (("london", "united-kingdom"), ("hamburg", "germany"), ("brussels", "belgium")):
        assert country_entry(get_city(city_id)) == get_city(country_id)


def test_every_city_lies_within_exactly_one_country_entry():
    cities = load_cities().values()
    countries = [city.country for city in cities if city.level == "country"]
    assert len(countries) == len(set(countries))
    within = [city.id for entry in cities for city in cities_within(entry)]
    assert len(within) == len(set(within))
    assert set(within) == {city.id for city in cities if city.level == "city"}
    # Each country entry's map opens inside its area, as a city's does.
    for entry in cities:
        if entry.level == "country":
            longitude, latitude = entry.map.center
            assert entry.covers(latitude, longitude)


def test_a_city_without_a_country_entry_is_refused(tmp_path, monkeypatch):
    import json

    import packages.cities as cities_module

    for name in ("hyderabad", "london"):
        (tmp_path / f"{name}.json").write_text(
            (cities_module.DATA_DIR / f"{name}.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
    india = json.loads((cities_module.DATA_DIR / "india.json").read_text(encoding="utf-8"))
    (tmp_path / "india.json").write_text(json.dumps(india), encoding="utf-8")
    monkeypatch.setattr(cities_module, "DATA_DIR", tmp_path)
    cities_module.load_cities.cache_clear()
    try:
        with pytest.raises(ValueError, match="london: no country entry for GB"):
            cities_module.load_cities()
    finally:
        monkeypatch.undo()
        cities_module.load_cities.cache_clear()
    assert "london" in cities_module.load_cities()


def test_the_cities_api_states_the_hierarchy(client):
    cities = {city["id"]: city for city in client.get("/api/cities").json()}
    assert (cities["canada"]["level"], cities["canada"]["parent_id"]) == ("country", None)
    assert (cities["toronto"]["level"], cities["toronto"]["parent_id"]) == ("city", "canada")
    assert cities["new-york"]["parent_id"] == "united-states"
    assert (cities["india"]["level"], cities["india"]["parent_id"]) == ("country", None)
    assert cities["delhi"]["parent_id"] == cities["hyderabad"]["parent_id"] == "india"
    assert cities["london"]["parent_id"] == "united-kingdom"
    assert all(city["parent_id"] for city in cities.values() if city["level"] == "city")


# --- events ------------------------------------------------------------------------


@pytest.fixture
def events(client, session):
    for index, (event_id, (city, source_id, status)) in enumerate(EVENTS.items()):
        session.add(
            Event(
                event_id=event_id,
                source_id=source_id,
                title=f"Road closed in {city} ({event_id})",
                city=city,
                status=status,
                start_time=NOW - timedelta(hours=1),
                end_time=NOW + timedelta(days=1),
                geometry=POINT,
                detection={"method": "source_provided", "matched_keywords": []},
                version=1,
                created_at=utc_now() - timedelta(minutes=index),
                updated_at=utc_now(),
            )
        )
    session.commit()
    return client


def listed(client, view: str, city: str | None = None, q: str | None = None) -> set[str]:
    params = {"view": view, **({"city": city} if city else {}), **({"q": q} if q else {})}
    response = client.get("/api/events", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["items"])
    return {item["event_id"] for item in body["items"]}


def test_choosing_canada_lists_canadas_and_torontos_events(events):
    assert listed(events, "validation", "canada") == {"EVT-CA-NATIONAL", "EVT-CA-TORONTO"}
    assert listed(events, "current_upcoming", "canada") == {"EVT-CA-TORONTO-OK"}


def test_choosing_toronto_lists_torontos_events_only(events):
    assert listed(events, "validation", "toronto") == {"EVT-CA-TORONTO"}
    assert listed(events, "current_upcoming", "toronto") == {"EVT-CA-TORONTO-OK"}


def test_the_united_states_and_new_york_city(events):
    assert listed(events, "validation", "united-states") == {"EVT-US-NATIONAL", "EVT-US-NYC"}
    assert listed(events, "validation", "new-york") == {"EVT-US-NYC"}


def test_choosing_india_lists_the_events_of_every_indian_city(events):
    assert listed(events, "validation", "india") == {"EVT-IN-DELHI", "EVT-IN-HYDERABAD", "EVT-IN-LEGACY"}
    assert listed(events, "validation", "delhi") == {"EVT-IN-DELHI"}
    assert listed(events, "validation", "hyderabad") == {"EVT-IN-HYDERABAD", "EVT-IN-LEGACY"}
    assert listed(events, "validation", "india", q="road closed") == {
        "EVT-IN-DELHI", "EVT-IN-HYDERABAD", "EVT-IN-LEGACY"
    }  # fmt: skip
    assert listed(events, "validation", "united-kingdom") == listed(events, "validation", "london") == {"EVT-GB-LONDON"}
    assert listed(events, "validation", "germany") == set()


def test_search_follows_the_same_hierarchy(events):
    assert listed(events, "validation", "canada", q="road closed") == {"EVT-CA-NATIONAL", "EVT-CA-TORONTO"}
    assert listed(events, "validation", "toronto", q="road closed") == {"EVT-CA-TORONTO"}


def test_all_cities_lists_each_event_once(events):
    assert listed(events, "validation") == {
        event_id for event_id, (_, _, status) in EVENTS.items() if status != "APPROVED"
    }


def test_an_unknown_city_is_still_refused(events):
    assert events.get("/api/events", params={"city": "atlantis"}).status_code == 422


def test_counts_per_entry_are_its_own_and_add_up_to_all_cities_without_double_counting(events):
    """The summary and the coverage keep one row per entry (Canada: its national
    events; Toronto: its own). The console adds a country's cities to it."""
    summary = {row["city_id"]: row["total"] for row in events.get("/api/events/summary", params={"view": "validation"}).json()["cities"]}
    assert (summary["canada"], summary["toronto"]) == (1, 1)
    assert (summary["united-states"], summary["new-york"]) == (1, 1)
    assert (summary["india"], summary["delhi"], summary["hyderabad"]) == (0, 1, 2)
    assert sum(summary.values()) == len(listed(events, "validation"))

    coverage = {row["city_id"]: row for row in events.get("/api/events/coverage").json()["cities"]}
    assert (coverage["canada"]["on_map_review"], coverage["toronto"]["on_map_review"]) == (1, 1)
    assert coverage["toronto"]["on_map_operations"] == 1
    assert sum(row["detected"] for row in coverage.values()) == len(EVENTS)


def test_merge_candidates_follow_the_same_hierarchy(events, session):
    from app.models import EventMergeCandidate
    from services.merging import MatchClass

    session.add(
        EventMergeCandidate(
            event_a="EVT-CA-TORONTO", event_b="EVT-CA-NATIONAL", classification=MatchClass.SAME.value,
            status="PENDING", reasons=[], conflicts=[], created_at=utc_now(),
        )
    )  # fmt: skip
    session.commit()
    def found(city: str) -> int:
        return len(events.get("/api/merge-candidates", params={"city": city}).json())

    assert (found("canada"), found("toronto"), found("united-states")) == (1, 1, 0)
