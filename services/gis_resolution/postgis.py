"""The OSM road network in PostGIS: schema, import and reading.

Kept in its own database (GIS_DATABASE_URL, e.g. `rei_gis`) and schema
(`gis`), apart from the application's events and from the place gazetteer.

Tables:

- `gis.osm_roads`: one row per OSM way of the imported road classes: its id,
  names, ref, class, one-way, lanes, all OSM tags, node ids and line geometry;
  GiST index on the geometry, GIN on names and node ids.
- `gis.osm_named_points`: named OSM features that mark junctions.
- `gis.osm_junction_nodes`: nodes where two or more road ways meet (derived).
- `gis.import_runs`: every import, with the OSM data date.

`ensure_schema` is idempotent; `load` replaces a city's rows in one
transaction, so an import can be repeated at any time.
"""

import json
from collections.abc import Iterable
from datetime import UTC, datetime

import psycopg

from .geometry import Position
from .network import NamedPoint, RoadWay, name_key

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS gis;
CREATE TABLE IF NOT EXISTS gis.import_runs (
    run_id serial PRIMARY KEY,
    city text NOT NULL,
    source text NOT NULL,
    osm_timestamp text,
    bbox double precision[] NOT NULL,
    tiles integer,
    ways integer,
    points integer,
    junction_nodes integer,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL,
    notes text
);
CREATE TABLE IF NOT EXISTS gis.osm_roads (
    way_id bigint PRIMARY KEY,
    city text NOT NULL,
    name text,
    alt_names text[] NOT NULL DEFAULT '{}',
    ref text,
    highway text NOT NULL,
    oneway text,
    lanes text,
    tags jsonb NOT NULL,
    node_ids bigint[] NOT NULL,
    name_keys text[] NOT NULL,
    geom geometry(LineString, 4326) NOT NULL,
    run_id integer REFERENCES gis.import_runs(run_id)
);
CREATE INDEX IF NOT EXISTS osm_roads_geom_idx ON gis.osm_roads USING gist (geom);
CREATE INDEX IF NOT EXISTS osm_roads_name_keys_idx ON gis.osm_roads USING gin (name_keys);
CREATE INDEX IF NOT EXISTS osm_roads_node_ids_idx ON gis.osm_roads USING gin (node_ids);
CREATE INDEX IF NOT EXISTS osm_roads_city_idx ON gis.osm_roads (city);
CREATE TABLE IF NOT EXISTS gis.osm_named_points (
    osm_ref text PRIMARY KEY,
    city text NOT NULL,
    name text NOT NULL,
    name_keys text[] NOT NULL,
    kind text NOT NULL,
    node_id bigint,
    geom geometry(Point, 4326) NOT NULL,
    run_id integer REFERENCES gis.import_runs(run_id)
);
CREATE INDEX IF NOT EXISTS osm_named_points_keys_idx ON gis.osm_named_points USING gin (name_keys);
CREATE TABLE IF NOT EXISTS gis.osm_junction_nodes (
    node_id bigint PRIMARY KEY,
    city text NOT NULL,
    ways integer NOT NULL,
    road_names text[] NOT NULL,
    geom geometry(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS osm_junction_nodes_geom_idx ON gis.osm_junction_nodes USING gist (geom);
"""


def connect(url: str) -> psycopg.Connection:
    """A connection from a SQLAlchemy-style URL (postgresql+psycopg://…) or a plain one."""
    return psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"))


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()


def _wkt_line(coords: Iterable[Position]) -> str:
    return "LINESTRING(" + ", ".join(f"{lon} {lat}" for lon, lat in coords) + ")"


def load(
    conn: psycopg.Connection,
    *,
    city: str,
    bbox: tuple[float, float, float, float],
    ways: Iterable[RoadWay],
    points: Iterable[NamedPoint],
    osm_timestamp: str | None,
    tiles: int,
    source: str,
) -> dict[str, int]:
    """Replace the city's road network with these ways and points, in one transaction."""
    started = datetime.now(UTC)
    unique_ways = {way.way_id: way for way in ways}
    unique_points = {point.osm_ref: point for point in points}
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "INSERT INTO gis.import_runs (city, source, osm_timestamp, bbox, tiles, started_at, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'RUNNING') RETURNING run_id",
            (city, source, osm_timestamp, list(bbox), tiles, started),
        )
        run_id = cur.fetchone()[0]
        cur.execute("DELETE FROM gis.osm_junction_nodes WHERE city = %s", (city,))
        cur.execute("DELETE FROM gis.osm_named_points WHERE city = %s", (city,))
        cur.execute("DELETE FROM gis.osm_roads WHERE city = %s", (city,))
        cur.executemany(
            "INSERT INTO gis.osm_roads (way_id, city, name, alt_names, ref, highway, oneway, lanes, "
            "tags, node_ids, name_keys, geom, run_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, ST_GeomFromText(%s, 4326), %s) ON CONFLICT (way_id) DO NOTHING",
            [
                (
                    w.way_id, city, w.name, list(w.alt_names), w.ref, w.highway, w.oneway, w.lanes,
                    json.dumps(w.tags), list(w.node_ids), sorted(w.keys), _wkt_line(w.coords), run_id,
                )  # fmt: skip
                for w in unique_ways.values()
            ],
        )
        cur.executemany(
            "INSERT INTO gis.osm_named_points (osm_ref, city, name, name_keys, kind, node_id, geom, run_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s) "
            "ON CONFLICT (osm_ref) DO NOTHING",
            [
                (p.osm_ref, city, p.name, [p.key], p.kind, p.node_id, p.position[0], p.position[1], run_id)
                for p in unique_points.values()
            ],
        )
        # Where ways meet: a node shared by two or more of the city's road ways.
        cur.execute(
            """
            INSERT INTO gis.osm_junction_nodes (node_id, city, ways, road_names, geom)
            SELECT n.node_id, %s, count(DISTINCT n.way_id),
                   array_remove(array_agg(DISTINCT n.name), NULL),
                   (array_agg(ST_PointN(n.geom, n.ord::int)))[1]
            FROM (
                SELECT r.way_id, r.name, r.geom, u.node_id, u.ord
                FROM gis.osm_roads r, unnest(r.node_ids) WITH ORDINALITY AS u(node_id, ord)
                WHERE r.city = %s
            ) n
            GROUP BY n.node_id
            HAVING count(DISTINCT n.way_id) >= 2
            """,
            (city, city),
        )
        cur.execute("SELECT count(*) FROM gis.osm_junction_nodes WHERE city = %s", (city,))
        junctions = cur.fetchone()[0]
        cur.execute(
            "UPDATE gis.import_runs SET ways = %s, points = %s, junction_nodes = %s, "
            "finished_at = %s, status = 'COMPLETE' WHERE run_id = %s",
            (len(unique_ways), len(unique_points), junctions, datetime.now(UTC), run_id),
        )
    return {"ways": len(unique_ways), "points": len(unique_points), "junction_nodes": junctions, "run_id": run_id}


class PostGISRoadNetwork:
    """The imported network of one city, read for the resolver."""

    def __init__(self, conn: psycopg.Connection, city_id: str) -> None:
        self._conn = conn
        self.city_id = city_id
        with conn.cursor() as cur:
            cur.execute(
                "SELECT osm_timestamp FROM gis.import_runs WHERE city = %s AND status = 'COMPLETE' "
                "ORDER BY run_id DESC LIMIT 1",
                (city_id,),
            )
            row = cur.fetchone()
        if row is None:
            raise LookupError(f"No road network has been imported for {city_id}")
        self.version = f"OpenStreetMap {row[0] or 'unknown date'}"

    _COLUMNS = "way_id, name, alt_names, ref, highway, oneway, lanes, tags, node_ids, ST_AsGeoJSON(geom)"

    def _ways(self, where: str, params: tuple) -> list[RoadWay]:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT {self._COLUMNS} FROM gis.osm_roads WHERE city = %s AND {where}", (self.city_id, *params))
            rows = cur.fetchall()
        return [
            RoadWay(
                way_id=r[0], name=r[1], alt_names=tuple(r[2] or ()), ref=r[3], highway=r[4],
                oneway=r[5], lanes=r[6], node_ids=tuple(r[8]),
                coords=tuple(tuple(c) for c in json.loads(r[9])["coordinates"]),
                tags=r[7] or {},
            )  # fmt: skip
            for r in rows
        ]

    def ways_named(self, key: str) -> list[RoadWay]:
        return self._ways("name_keys @> ARRAY[%s]::text[]", (key,))

    def ways_through_node(self, node_id: int) -> list[RoadWay]:
        return self._ways("node_ids @> ARRAY[%s]::bigint[]", (node_id,))

    def ways_near(self, position: Position, metres: float) -> list[RoadWay]:
        lon, lat = position
        return self._ways(
            "geom && ST_Expand(ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s) "
            "AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)",
            (lon, lat, metres / 90_000, lon, lat, metres),
        )

    def points_named(self, key: str) -> list[NamedPoint]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT osm_ref, name, kind, ST_X(geom), ST_Y(geom), node_id FROM gis.osm_named_points "
                "WHERE city = %s AND name_keys @> ARRAY[%s]::text[]",
                (self.city_id, key),
            )
            return [NamedPoint(r[0], r[1], r[2], (r[3], r[4]), r[5]) for r in cur.fetchall()]

    def stats(self) -> dict[str, int]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT (SELECT count(*) FROM gis.osm_roads WHERE city = %s), "
                "(SELECT count(*) FROM gis.osm_roads WHERE city = %s AND name IS NOT NULL), "
                "(SELECT count(*) FROM gis.osm_named_points WHERE city = %s), "
                "(SELECT count(*) FROM gis.osm_junction_nodes WHERE city = %s)",
                (self.city_id,) * 4,
            )
            ways, named, points, junctions = cur.fetchone()
        return {"ways": ways, "named_ways": named, "named_points": points, "junction_nodes": junctions}


__all__ = ["PostGISRoadNetwork", "connect", "ensure_schema", "load", "name_key"]
