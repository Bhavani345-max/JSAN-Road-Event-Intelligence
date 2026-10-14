"""The road network the GIS resolver reads: OpenStreetMap roads and named points.

Separate from the place gazetteer (services/geo_resolution), which stays a
name dictionary of single points. Here every road is its full line with its
OSM node ids, so roads that meet share a node and junctions can be found.

Two implementations of one interface:

- `InMemoryRoadNetwork`, built from an Overpass response (tests, small areas);
- `PostGISRoadNetwork` (postgis.py), backed by the imported tables.

The resolver's algorithm is the same over either.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from services.geo_resolution.names import normalise_name

from .geometry import Position, distance_m, project

# OSM road classes imported (drivable public roads; service roads left out).
ROAD_CLASSES = (
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
    "living_street", "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link",
)  # fmt: skip
NAME_TAGS = ("name", "name:en", "alt_name", "old_name", "official_name", "short_name", "loc_name")
_LETTER_DIGIT = re.compile(r"([a-z])(\d)")


def name_key(text: str | None) -> str:
    """A name as REI compares it: normalised words, letters and digits apart ("NH65" = "NH-65")."""
    key = normalise_name(text or "")
    return " ".join(_LETTER_DIGIT.sub(r"\1 \2", key).split())


@dataclass(frozen=True)
class RoadWay:
    way_id: int
    name: str | None
    alt_names: tuple[str, ...]
    ref: str | None
    highway: str
    oneway: str | None
    lanes: str | None
    node_ids: tuple[int, ...]
    coords: tuple[Position, ...]
    tags: dict[str, str] = field(default_factory=dict, hash=False, compare=False)

    @property
    def keys(self) -> frozenset[str]:
        names = [self.name, *self.alt_names]
        refs = [part.strip() for part in (self.ref or "").split(";") if part.strip()]
        return frozenset(k for k in (name_key(n) for n in names + refs) if k)

    @property
    def is_structure(self) -> bool:
        return self.tags.get("bridge") not in (None, "no") or self.tags.get("tunnel") not in (None, "no")


@dataclass(frozen=True)
class NamedPoint:
    """A named OSM feature that marks a spot on the road network (a junction)."""

    osm_ref: str
    name: str
    kind: str
    position: Position
    node_id: int | None = None

    @property
    def key(self) -> str:
        return name_key(self.name)


def ways_from_overpass(document: dict[str, Any]) -> list[RoadWay]:
    """Road ways from an Overpass `out body geom` response."""
    ways = []
    for element in document.get("elements", []):
        tags = element.get("tags") or {}
        if element.get("type") != "way" or tags.get("highway") not in ROAD_CLASSES:
            continue
        geometry = element.get("geometry") or []
        nodes = element.get("nodes") or []
        if len(geometry) < 2 or len(geometry) != len(nodes):
            continue
        alt = []
        for tag in NAME_TAGS[1:]:
            alt += [v.strip() for v in tags.get(tag, "").split(";") if v.strip()]
        ways.append(
            RoadWay(
                way_id=int(element["id"]),
                name=tags.get("name"),
                alt_names=tuple(dict.fromkeys(a for a in alt if a != tags.get("name"))),
                ref=tags.get("ref"),
                highway=tags["highway"],
                oneway=tags.get("oneway"),
                lanes=tags.get("lanes"),
                node_ids=tuple(int(n) for n in nodes),
                coords=tuple((float(p["lon"]), float(p["lat"])) for p in geometry),
                tags={k: str(v) for k, v in tags.items()},
            )
        )
    return ways


# Named points that are not junctions even when named like one.
_NOT_A_JUNCTION = {"bus_stop", "platform", "stop_position"}


def points_from_overpass(document: dict[str, Any]) -> list[NamedPoint]:
    points = []
    for element in document.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name:en") or tags.get("name")
        if not name or tags.get("highway") in _NOT_A_JUNCTION or tags.get("public_transport"):
            continue
        if element.get("type") == "node":
            position = (float(element["lon"]), float(element["lat"]))
            node_id = int(element["id"])
        elif element.get("center"):
            position = (float(element["center"]["lon"]), float(element["center"]["lat"]))
            node_id = None
        else:
            continue
        kind = (
            "junction" if tags.get("junction") or tags.get("highway") in ("traffic_signals", "motorway_junction")
            else tags.get("highway") or "point"
        )  # fmt: skip
        points.append(NamedPoint(f"{element['type']}/{element['id']}", name, kind, position, node_id))
    return points


class RoadNetwork(Protocol):
    """What the resolver needs to read."""

    # "OpenStreetMap 2026-10-06T07:40:50Z": the data and its date, kept with every result.
    version: str
    city_id: str

    def ways_named(self, key: str) -> list[RoadWay]: ...

    def ways_through_node(self, node_id: int) -> list[RoadWay]: ...

    def ways_near(self, position: Position, metres: float) -> list[RoadWay]: ...

    def points_named(self, key: str) -> list[NamedPoint]: ...


class InMemoryRoadNetwork:
    def __init__(
        self, ways: list[RoadWay], points: list[NamedPoint], *, version: str, city_id: str
    ) -> None:
        self.version = version
        self.city_id = city_id
        self._ways = ways
        self._points = points
        self._by_key: dict[str, list[RoadWay]] = {}
        self._by_node: dict[int, list[RoadWay]] = {}
        for way in ways:
            for key in way.keys:
                self._by_key.setdefault(key, []).append(way)
            for node in set(way.node_ids):
                self._by_node.setdefault(node, []).append(way)

    @classmethod
    def from_overpass(cls, document: dict[str, Any], *, city_id: str) -> "InMemoryRoadNetwork":
        stamp = (document.get("osm3s") or {}).get("timestamp_osm_base") or "unknown date"
        return cls(
            ways_from_overpass(document),
            points_from_overpass(document),
            version=f"OpenStreetMap {stamp}",
            city_id=city_id,
        )

    def __len__(self) -> int:
        return len(self._ways)

    def ways_named(self, key: str) -> list[RoadWay]:
        return list(self._by_key.get(key, []))

    def ways_through_node(self, node_id: int) -> list[RoadWay]:
        return list(self._by_node.get(node_id, []))

    def ways_near(self, position: Position, metres: float) -> list[RoadWay]:
        return [w for w in self._ways if project(position, w.coords)[0] <= metres]

    def points_named(self, key: str) -> list[NamedPoint]:
        return [p for p in self._points if p.key == key]


def node_position(way: RoadWay, node_id: int) -> Position:
    return way.coords[way.node_ids.index(node_id)]


def shared_nodes(a: list[RoadWay], b: list[RoadWay]) -> dict[int, Position]:
    """Nodes that a way of `a` and a way of `b` both pass through: where the roads meet."""
    a_ids = {wid for w in a for wid in [w.way_id]}
    b_ids = {w.way_id for w in b}
    if a_ids & b_ids:
        a = [w for w in a if w.way_id not in b_ids]
    nodes_a = {n: w for w in a for n in w.node_ids}
    found: dict[int, Position] = {}
    for way in b:
        for n in way.node_ids:
            if n in nodes_a:
                found[n] = node_position(way, n)
    return found


def within(points: list[Position], bbox: tuple[float, float, float, float]) -> bool:
    south, west, north, east = bbox
    return all(south <= lat <= north and west <= lon <= east for lon, lat in points)


__all__ = [
    "InMemoryRoadNetwork",
    "NamedPoint",
    "ROAD_CLASSES",
    "RoadNetwork",
    "RoadWay",
    "distance_m",
    "name_key",
    "points_from_overpass",
    "shared_nodes",
    "ways_from_overpass",
]
