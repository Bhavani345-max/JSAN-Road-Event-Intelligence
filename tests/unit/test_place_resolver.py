"""Places are found only where the text names them, and located from OpenStreetMap."""

import json

import pytest

from services.geo_resolution import PlaceResolver, default_resolver
from services.geo_resolution.build_gazetteer import build_places
from services.geo_resolution.names import normalise_name
from services.geo_resolution.resolver import DEFAULT_GAZETTEER_PATH


@pytest.fixture(scope="module")
def resolver() -> PlaceResolver:
    return default_resolver()


def names(matches):
    return [match.name for match in matches]


def test_gazetteer_file_is_real_openstreetmap_data():
    document = json.loads(DEFAULT_GAZETTEER_PATH.read_text(encoding="utf-8"))
    assert "OpenStreetMap" in document["source"] and "ODbL" in document["licence"]
    south, west, north, east = document["bbox_south_west_north_east"]
    assert len(document["places"]) > 3000
    located = [place for place in document["places"] if place["precision"] != "none"]
    assert len(located) > 3000
    for place in located:
        assert place["osm"].split("/")[0] in {"node", "way", "relation"}
        assert south <= place["lat"] <= north and west <= place["lon"] <= east
    # A name that is not one spot is known, but has no position at all.
    for place in document["places"]:
        if place["precision"] == "none":
            assert not {"lat", "lon", "osm"} & place.keys()


@pytest.mark.parametrize(
    "written, same_as",
    [
        ("Khajaguda Jn", "khajaguda junction"),
        ("RTC X Roads", "rtc x road"),
        ("RTC Cross Road", "rtc x road"),
        ("Gachibowli Traffic PS", "gachibowli traffic police station"),
        ("Gachibowli's", "gachibowli"),
    ],
)
def test_names_are_matched_across_spellings(written, same_as):
    assert normalise_name(written) == same_as


def test_finds_the_places_a_text_names(resolver):
    matches = resolver.find_in("Traffic diversions at Khajaguda junction near Tolichowki", "title")
    assert [(m.mention, m.kind) for m in matches] == [
        ("Khajaguda junction", "junction"),
        ("Tolichowki", "area"),
    ]
    assert all(match.osm_ref and match.found_in == "title" for match in matches)


def test_the_longest_name_wins(resolver):
    # "Khajaguda Lake" is the lake, not the locality of Khajaguda.
    assert names(resolver.find_in("Vehicles can use the Khajaguda Lake route", "body")) == [
        "Khajaguda Lake"
    ]


def test_a_word_counts_as_a_name_only_when_written_as_one(resolver):
    assert resolver.find_in("residents of tolichowki and the charminar area", "body") == []


def test_the_city_itself_is_not_a_location(resolver):
    assert resolver.find_in("Heavy rain across Hyderabad and Secunderabad", "title") == []


def test_headline_places_come_before_summary_and_body_places(resolver):
    matches = resolver.find_places(
        title="Waterlogging at Tolichowki",
        summary="Traffic was slow near Hussain Sagar.",
        body="Vehicles were diverted at Khajaguda junction.",
    )
    assert [(m.name, m.found_in) for m in matches] == [
        ("Tolichowki", "title"),
        ("Hussain Sagar", "summary"),
        ("Khajaguda Jn", "body"),
    ]


def test_nothing_is_located_when_no_known_place_is_named(resolver):
    assert resolver.find_places(title="Traffic diversions at Lakeview Junction", summary=None) == []


# --- building the gazetteer ---------------------------------------------------


def node(osm_id, name, lat, lon, **tags):
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": {"name": name, **tags}}


def test_a_name_shared_by_distant_places_is_known_but_locates_nothing(resolver):
    # There are several Indira Nagars in Hyderabad.
    (match,) = resolver.find_in("Water supply cut in Indira Nagar", "title")
    assert (match.name, match.precision, match.has_position) == ("Indira Nagar", "none", False)


def test_a_name_shared_by_distant_places_has_no_position():
    places, skipped = build_places(
        [
            node(1, "Indira Nagar", 17.30, 78.40, place="neighbourhood"),
            node(2, "Indira Nagar", 17.50, 78.50, place="neighbourhood"),
            node(3, "Tolichowki", 17.40, 78.41, place="suburb"),
        ]
    )
    assert [(place["key"], place["precision"]) for place in places] == [
        ("indira nagar", "none"),
        ("tolichowki", "area"),
    ]
    assert "lat" not in places[0] and skipped["area not one spot"] == 1


def test_a_long_road_has_no_position_and_a_short_one_has():
    def way(osm_id, name, lat, lon):
        return {
            "type": "way",
            "id": osm_id,
            "center": {"lat": lat, "lon": lon},
            "tags": {"name": name, "highway": "primary"},
        }

    places, _ = build_places(
        [
            way(1, "Long Road", 17.30, 78.40),
            way(2, "Long Road", 17.40, 78.40),
            way(3, "Short Road", 17.400, 78.400),
            way(4, "Short Road", 17.401, 78.401),
        ]
    )
    assert [(place["key"], place["precision"]) for place in places] == [
        ("long road", "none"),
        ("short road", "road"),
    ]
    # The position is a real feature of that name, not an average.
    assert (places[1]["lat"], places[1]["lon"]) in {(17.4, 78.4), (17.401, 78.401)}


def test_generic_and_city_wide_names_are_left_out():
    places, _ = build_places(
        [
            node(1, "Hyderabad", 17.38, 78.48, place="suburb"),
            node(2, "Park", 17.40, 78.40, leisure="park"),
            node(3, "Koti", 17.38, 78.48, place="suburb"),
        ]
    )
    assert places == []
