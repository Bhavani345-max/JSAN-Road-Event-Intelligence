"""Gazetteer of 6 October 2026: more kinds of place, spellings, and the spot within a locality."""

from datetime import datetime, timezone

import pytest

from packages.source_models import RawSourceRecord
from services.extraction import KeywordClassifier, build_event_from_article
from services.geo_resolution import PlaceMatch, default_resolver, spot_within
from services.geo_resolution.build_gazetteer import build_places
from services.geo_resolution.names import spelling_variants

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def resolver():
    return default_resolver()


@pytest.mark.parametrize(
    "written, osm_name",
    [
        ("Dilsukhnagar", "Dilsukh Nagar"),
        ("Lakdikapul", "Lakdi-ka-pul"),
        ("Basheerbagh", "Basheer Bagh"),
        ("Tank Bund", "Tank Bund Road"),
        ("Secunderabad railway station", "Secunderabad Junction"),
        ("Jubilee Hills Check Post", "Jubilee Check Post Jn"),
        ("RGIA", "Rajiv Gandhi International Airport"),
        ("Quthbullapur", "Quthbullapur"),
    ],
)
def test_names_as_the_papers_write_them_find_their_openstreetmap_feature(
    resolver, written, osm_name
):
    match = resolver.lookup(written, found_in="title")
    assert match is not None and match.name == osm_name
    assert match.has_position and match.osm_ref


@pytest.mark.parametrize(
    "key, variants",
    [
        ("dilsukh nagar", ["dilsukhnagar"]),
        ("lakdi ka pul", ["lakdikapul"]),
        ("dilsukhnagar", ["dilsukh nagar"]),
        ("khajaguda junction", []),  # "junction" is never joined to the word before
        ("koti", []),  # too short to split
    ],
)
def test_spelling_variants(key, variants):
    assert spelling_variants(key) == variants


def test_a_ward_stands_in_for_a_locality_that_has_no_place_node():
    def relation(osm_id, name, lat, lon):
        return {
            "type": "relation",
            "id": osm_id,
            "center": {"lat": lat, "lon": lon},
            "tags": {"name": name, "boundary": "administrative", "admin_level": "10"},
        }

    places, _ = build_places([relation(1, "Ward 131 Quthbullapur", 17.52, 78.45)])
    assert [(p["name"], p["kind"], p["precision"]) for p in places] == [
        ("Quthbullapur", "ward", "area")
    ]


def test_a_locality_node_is_preferred_to_its_ward():
    node = {
        "type": "node", "id": 2, "lat": 17.50, "lon": 78.40,
        "tags": {"name": "Kukatpally", "place": "suburb"},
    }  # fmt: skip
    ward = {
        "type": "relation", "id": 3, "center": {"lat": 17.51, "lon": 78.41},
        "tags": {"name": "Ward 120 Kukatpally", "boundary": "administrative", "admin_level": "10"},
    }  # fmt: skip
    places, _ = build_places([node, ward])
    assert [(p["kind"], p["osm"]) for p in places] == [("area", "node/2")]


# --- the spot within the locality ----------------------------------------------


def place(name, kind, lat, lon, found_in="title"):
    return PlaceMatch(
        name=name, kind=kind, precision="place" if kind in ("junction", "flyover", "landmark") else "area",
        latitude=lat, longitude=lon, osm_ref="node/1", mention=name, found_in=found_in,
    )  # fmt: skip


def test_a_spot_the_article_names_inside_the_locality_is_taken():
    gachibowli = place("Gachibowli", "area", 17.4436, 78.3520)
    nearby_junction = place("Gachibowli Junction", "junction", 17.4400, 78.3480, "summary")
    assert spot_within(gachibowli, [gachibowli, nearby_junction]) == nearby_junction


def test_a_spot_elsewhere_in_the_city_is_not_taken():
    gachibowli = place("Gachibowli", "area", 17.4436, 78.3520)
    far_junction = place("Khajaguda Junction", "junction", 17.4227, 78.3817, "summary")
    assert spot_within(gachibowli, [gachibowli, far_junction]) is None


def test_an_event_is_put_at_the_junction_its_summary_names_within_the_headlines_locality():
    record = RawSourceRecord(
        source_id="test-news",
        external_id="khajaguda",
        url="https://news.example.com/khajaguda",
        title="Traffic diversions in Raidurg for 60 days from September 26",
        summary="Hyderabad: Cyberabad police have diverted traffic at Khajaguda junction.",
        content_text=None,
        categories=[],
        published_at=NOW,
        retrieved_at=NOW,
        raw={},
        content_hash="0" * 64,
    )
    classifier = KeywordClassifier.from_file()
    event = build_event_from_article(
        record, classifier.classify(record), now=NOW, resolver=default_resolver()
    )
    location = event.detection.location
    # "Khajaguda Jn" is the junction's name on OpenStreetMap.
    assert (location.place_name, location.place_kind, location.found_in) == (
        "Khajaguda Jn",
        "junction",
        "summary",
    )
    assert location.within == "Raidurg"
    longitude, latitude = event.geometry.coordinates
    assert 78.37 < longitude < 78.39 and 17.41 < latitude < 17.43


def test_a_junction_in_the_body_alone_does_not_move_the_event():
    """A junction named only in the body may be a diversion route, not the event."""
    record = RawSourceRecord(
        source_id="test-news",
        external_id="raidurg",
        url="https://news.example.com/raidurg",
        title="Traffic diversions in Raidurg for 60 days from September 26",
        summary="Hyderabad: Cyberabad police have diverted traffic.",
        content_text="Vehicles may instead go via Khajaguda junction.",
        categories=[],
        published_at=NOW,
        retrieved_at=NOW,
        raw={},
        content_hash="0" * 64,
    )
    classifier = KeywordClassifier.from_file()
    event = build_event_from_article(
        record, classifier.classify(record), now=NOW, resolver=default_resolver()
    )
    assert event.detection.location.place_name == "Raidurg"
    assert event.detection.location.within is None
    assert "Khajaguda Jn" in event.detection.places
