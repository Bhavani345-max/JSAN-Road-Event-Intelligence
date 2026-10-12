"""The deterministic GIS resolver on small test networks (6 October 2026).

The synthetic network below is test data only (it is never loaded by the
application). The real-data checks on Khajaguda Junction and the DLF road /
Old Bombay Road crossing are in test_gis_resolver_real.py.
"""

import pytest

from services.geo_resolution import default_resolver
from services.gis_resolution.geometry import chains, distance_m, line_length_m, project, substring
from services.gis_resolution.network import (
    InMemoryRoadNetwork,
    NamedPoint,
    RoadWay,
    name_key,
    ways_from_overpass,
)
from services.gis_resolution.resolver import (
    Confidence,
    GisRequest,
    JunctionRef,
    MatchMethod,
    Mention,
    OsmGisEngine,
)

# A small grid near 17.40 N, 78.40 E. 0.001 degree ≈ 106 m east-west, 111 m north-south.
A = (78.400, 17.400)
B = (78.405, 17.400)
C = (78.410, 17.400)
D = (78.405, 17.395)
E = (78.405, 17.405)
FAR = (78.470, 17.460)  # ~9 km away
FAR2 = (78.475, 17.460)


def way(way_id, name, nodes, coords, **tags) -> RoadWay:
    return RoadWay(
        way_id=way_id, name=name, alt_names=tuple(tags.pop("alt", ())), ref=tags.pop("ref", None),
        highway=tags.pop("highway", "secondary"), oneway=tags.pop("oneway", None), lanes=None,
        node_ids=tuple(nodes), coords=tuple(coords), tags={"name": name, **tags},
    )  # fmt: skip


NETWORK = InMemoryRoadNetwork(
    [
        way(1, "Test Main Road", [10, 11], [A, B]),
        way(2, "Test Main Road", [11, 12], [B, C]),
        way(3, "Cross Road Avenue", [13, 11], [D, B]),
        way(4, "Cross Road Avenue", [11, 14], [B, E]),
        # The same name, far away: a different road.
        way(5, "Twin Road", [20, 21], [A, D]),
        way(6, "Twin Road", [22, 23], [FAR, FAR2]),
        way(7, "Lakeside Flyover", [30, 31], [E, (78.407, 17.407)], bridge="yes"),
        way(8, "National Highway", [40, 41], [D, C], ref="NH65"),
    ],
    [
        NamedPoint("node/11", "Test Junction", "junction", B, node_id=11),
        NamedPoint("node/99", "Lonely Junction", "junction", (78.43, 17.43), node_id=99),
    ],
    version="OpenStreetMap test-network",
    city_id="hyderabad",
)
BBOX = (17.18, 78.15, 17.68, 78.75)


def engine(junctions=(), places=None) -> OsmGisEngine:
    return OsmGisEngine(NETWORK, junctions, places=places, bbox=BBOX)


def resolve(text, *, kind=None, junctions=(), places=None):
    eng = engine(junctions, places)
    if kind:
        return eng.resolve_mention(Mention(text, "title", kind))
    return eng.resolve_request(GisRequest("EVT-T", "hyderabad", title=text))


# --- geometry -----------------------------------------------------------------------


def test_projection_and_substring_stay_on_the_line():
    line = [A, B, C]
    d, along, on = project((78.4075, 17.4003), line)
    assert d == pytest.approx(33, abs=2) and on[1] == pytest.approx(17.400)
    part = substring(line, 100, along)
    assert part[0][1] == pytest.approx(17.400) and part[-1] == on
    assert line_length_m(part) == pytest.approx(along - 100, rel=1e-6)


def test_ways_sharing_ends_form_one_chain_and_a_fork_ends_it():
    lines = chains([(w.node_ids, w.coords) for w in NETWORK.ways_named("test main road")])
    assert lines == [[A, B, C]]


def test_names_compare_however_they_are_written():
    assert name_key("NH-65") == name_key("NH65") == "nh 65"
    assert name_key("Khajaguda Jn") == "khajaguda junction"


# --- matches -------------------------------------------------------------------------


def test_exact_junction_named_in_osm_on_a_crossing_is_high():
    result = resolve("Test Junction", kind="junction")
    assert result.confidence is Confidence.HIGH and result.applicable
    assert result.chosen.method is MatchMethod.OSM_NAMED_JUNCTION
    assert result.chosen.geometry == {"type": "Point", "coordinates": list(B)}


def test_a_named_junction_not_on_a_crossing_is_not_used():
    result = resolve("Lonely Junction", kind="junction")
    assert result.confidence is Confidence.UNRESOLVED


def test_road_intersection_by_wording():
    [result] = resolve("Diversions at the junction of Test Main Road and Cross Road Avenue, says police")
    assert result.mention.kind == "crossing"
    assert result.chosen.method is MatchMethod.ROAD_INTERSECTION and result.applicable
    assert result.chosen.geometry["coordinates"] == list(B)
    assert "node/11" in result.chosen.osm_ids


def test_roads_that_do_not_meet_give_no_intersection():
    [result] = resolve("Curbs at the junction of Lakeside Flyover and Twin Road.")
    assert result.confidence is Confidence.UNRESOLVED


def test_a_confirmed_junction_reference_is_high_and_lists_its_roads():
    ref = JunctionRef(1, "Unnamed Junction", ("UJ",), "CONFIRMED", B, 11, ("Test Main Road",))
    result = resolve("Unnamed Junction", kind="junction", junctions=[ref])
    assert result.confidence is Confidence.HIGH and result.applicable
    assert result.chosen.method is MatchMethod.JUNCTION_REFERENCE
    assert result.chosen.osm_ids == ("junction-reference/1", "node/11")
    assert [alt.matched_name for alt in result.alternatives] == ["Test Main Road"]


def test_an_alias_of_a_confirmed_junction_matches_as_an_alias():
    ref = JunctionRef(1, "Unnamed Junction", ("UJ Cross",), "CONFIRMED", B, 11)
    [result] = resolve("Diversions at UJ Cross from today", junctions=[ref])
    assert result.chosen.method is MatchMethod.ALIAS_MATCH and result.applicable


def test_an_unconfirmed_junction_reference_is_only_a_candidate():
    ref = JunctionRef(1, "Unnamed Junction", (), "UNCONFIRMED", B, 11)
    result = resolve("Unnamed Junction", kind="junction", junctions=[ref])
    assert result.confidence is Confidence.MEDIUM and not result.applicable
    assert "not been confirmed" in result.reasons[0]


def test_a_rejected_junction_reference_is_ignored():
    ref = JunctionRef(1, "Unnamed Junction", (), "REJECTED", B, 11)
    assert resolve("Unnamed Junction", kind="junction", junctions=[ref]).confidence is Confidence.UNRESOLVED


def test_a_road_named_without_a_stretch_is_not_applied():
    result = resolve("Test Main Road", kind="road")
    assert result.confidence is Confidence.MEDIUM and not result.applicable
    assert result.chosen.method is MatchMethod.EXACT_ROAD_NAME
    assert result.chosen.geometry["type"] == "LineString"
    assert "not which part" in result.reasons[0]


def test_one_name_for_roads_far_apart_is_ambiguous_with_every_candidate():
    result = resolve("Twin Road", kind="road")
    assert result.ambiguous and result.chosen is None and len(result.alternatives) == 2
    assert not result.applicable


def test_a_named_flyover_is_one_structure():
    result = resolve("Lakeside Flyover", kind="structure")
    assert result.confidence is Confidence.HIGH and result.chosen.geometry["type"] == "LineString"


def test_a_road_number_matches_its_ref():
    result = resolve("NH-65", kind="road")
    assert result.chosen is not None and result.chosen.osm_ids == ("way/8",)


def test_a_missing_road_is_unresolved_and_nothing_is_made_up():
    result = resolve("Nowhere Road", kind="road")
    assert result.confidence is Confidence.UNRESOLVED and result.chosen is None and not result.alternatives


def test_a_stretch_between_two_known_spots_is_the_part_of_the_road_between_them():
    ref_a = JunctionRef(1, "West Gate Junction", (), "CONFIRMED", A, 10)
    ref_c = JunctionRef(2, "East Gate Junction", (), "CONFIRMED", C, 12)
    [result] = resolve("Test Main Road closed from West Gate Junction to East Gate Junction for works",
                       junctions=[ref_a, ref_c])  # fmt: skip
    assert result.mention.kind == "stretch"
    assert result.chosen.method is MatchMethod.ROAD_STRETCH and result.applicable
    assert result.chosen.geometry["coordinates"][0] == list(A)
    assert result.chosen.geometry["coordinates"][-1] == list(C)


def test_a_stretch_with_an_unknown_end_is_unresolved():
    ref_a = JunctionRef(1, "West Gate Junction", (), "CONFIRMED", A, 10)
    [result] = resolve("Road closed from West Gate Junction to Gate No.9 for works", junctions=[ref_a])
    assert result.confidence is Confidence.UNRESOLVED
    assert "Gate No.9" in result.reasons[0]


def test_each_place_an_event_names_is_resolved_on_its_own():
    ref = JunctionRef(1, "Unnamed Junction", (), "CONFIRMED", B, 11)
    results = resolve("Works at Test Junction, Lakeside Flyover and Nowhere Junction", junctions=[ref])
    by_mention = {r.mention.text: r.confidence for r in results}
    assert by_mention["Test Junction"] is Confidence.HIGH
    assert by_mention["Lakeside Flyover"] is Confidence.HIGH
    assert by_mention["Nowhere Junction"] is Confidence.UNRESOLVED


def test_a_locality_alone_is_low_and_never_resolved():
    [result] = [r for r in resolve("Heavy rain in Tolichowki", places=default_resolver())
                if r.mention.text == "Tolichowki"]  # fmt: skip
    assert result.confidence is Confidence.LOW and not result.applicable


def test_a_candidate_outside_the_city_is_not_the_citys():
    outside = InMemoryRoadNetwork(
        [way(1, "Far Away Road", [1, 2], [(80.0, 20.0), (80.01, 20.0)]),
         way(2, "Far Away Lane", [3, 2], [(80.0, 20.01), (80.01, 20.0)])],
        [NamedPoint("node/2", "Far Junction", "junction", (80.01, 20.0), node_id=2)],
        version="test", city_id="hyderabad",
    )  # fmt: skip
    result = OsmGisEngine(outside, bbox=BBOX).resolve_mention(Mention("Far Junction", "title", "junction"))
    assert result.confidence is Confidence.UNRESOLVED and "outside the city" in result.reasons[0]


def test_resolving_twice_gives_the_same_answer():
    first = resolve("Diversions at the junction of Test Main Road and Cross Road Avenue.")
    assert first == resolve("Diversions at the junction of Test Main Road and Cross Road Avenue.")


def test_overpass_ways_keep_their_names_one_way_lanes_and_nodes():
    document = {"elements": [{
        "type": "way", "id": 5, "nodes": [1, 2],
        "geometry": [{"lat": 17.4, "lon": 78.4}, {"lat": 17.41, "lon": 78.4}],
        "tags": {"highway": "primary", "name": "DLF road", "alt_name": "DLF Gachibowli Road",
                 "oneway": "yes", "lanes": "2", "ref": "SH1"},
    }, {"type": "way", "id": 6, "nodes": [1], "geometry": [{"lat": 17.4, "lon": 78.4}],
        "tags": {"highway": "primary"}}, {"type": "way", "id": 7, "nodes": [1, 2],
        "geometry": [{"lat": 1, "lon": 1}, {"lat": 2, "lon": 2}], "tags": {"highway": "footway"}}]}  # fmt: skip
    [road] = ways_from_overpass(document)
    assert (road.name, road.alt_names, road.oneway, road.lanes, road.ref) == (
        "DLF road", ("DLF Gachibowli Road",), "yes", "2", "SH1",
    )
    assert road.keys == {"dlf road", "dlf gachibowli road", "sh 1"}
    assert distance_m(road.coords[0], road.coords[1]) == pytest.approx(1105.7, rel=1e-3)
