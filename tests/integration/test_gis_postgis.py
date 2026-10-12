"""The PostGIS road-network store (6 October 2026).

Runs only when REI_GIS_TEST_DATABASE_URL names a PostGIS database used for
tests (never the real one), e.g.

    REI_GIS_TEST_DATABASE_URL=postgresql://rei:<pw>@localhost:5433/rei_gis_test

The synthetic network of tests/unit/test_gis_resolver.py is loaded under a test
city id and removed afterwards.
"""

import os

import pytest

from services.gis_resolution.network import name_key
from services.gis_resolution.resolver import GisRequest, OsmGisEngine
from tests.unit.test_gis_resolver import BBOX, NETWORK

URL = os.environ.get("REI_GIS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="REI_GIS_TEST_DATABASE_URL is not set")
CITY = "rei-test-city"


@pytest.fixture
def conn():
    from services.gis_resolution.postgis import connect, ensure_schema

    with connect(URL) as conn:
        ensure_schema(conn)
        yield conn
        with conn.transaction(), conn.cursor() as cur:
            for table in ("osm_junction_nodes", "osm_named_points", "osm_roads", "import_runs"):
                cur.execute(f"DELETE FROM gis.{table} WHERE city = %s", (CITY,))


def _load(conn):
    from services.gis_resolution.postgis import load

    names = ("Test Main Road", "Cross Road Avenue", "Twin Road", "Lakeside Flyover", "NH65")
    ways = [w for name in names for w in NETWORK.ways_named(name_key(name))]
    points = [p for name in ("Test Junction", "Lonely Junction") for p in NETWORK.points_named(name_key(name))]
    return load(conn, city=CITY, bbox=BBOX, ways=ways, points=points, osm_timestamp="2026-10-06T00:00:00Z",
                tiles=1, source="test")  # fmt: skip


def test_loading_twice_gives_the_same_network(conn):
    from services.gis_resolution.postgis import PostGISRoadNetwork

    first = _load(conn)
    second = _load(conn)
    assert {k: v for k, v in first.items() if k != "run_id"} == {k: v for k, v in second.items() if k != "run_id"}
    stats = PostGISRoadNetwork(conn, CITY).stats()
    assert stats["ways"] == 8 and stats["named_points"] == 2
    # Node 11 is where Test Main Road and Cross Road Avenue meet (four ways).
    with conn.cursor() as cur:
        cur.execute("SELECT ways FROM gis.osm_junction_nodes WHERE city = %s AND node_id = 11", (CITY,))
        assert cur.fetchone()[0] == 4


def test_the_resolver_gives_the_same_answer_from_postgis(conn):
    from services.gis_resolution.postgis import PostGISRoadNetwork

    _load(conn)
    stored = PostGISRoadNetwork(conn, CITY)
    title = "Diversions at the junction of Test Main Road and Cross Road Avenue; Lakeside Flyover closed"
    from_db = OsmGisEngine(stored, bbox=BBOX).resolve_request(GisRequest("EVT-T", CITY, title=title))
    in_memory = OsmGisEngine(NETWORK, bbox=BBOX).resolve_request(GisRequest("EVT-T", CITY, title=title))
    assert [(r.mention.text, r.confidence, r.chosen and r.chosen.osm_ids) for r in from_db] == [
        (r.mention.text, r.confidence, r.chosen and r.chosen.osm_ids) for r in in_memory
    ]
    assert stored.ways_near((78.405, 17.4001), 30)  # a spatial query finds the crossing ways
