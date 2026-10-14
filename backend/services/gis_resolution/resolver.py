"""The deterministic GIS resolver: article words -> road network candidates.

    event text
      -> mentions: roads, junctions, structures (flyovers, underpasses),
         places, stretches ("from A to B"), crossings ("junction of A and B")
      -> for each mention, candidates from the OSM road network, the
         reviewer-confirmed junction references and the place gazetteer
      -> a confidence by fixed rules, with every reason stated
      -> one result per mention; nothing is chosen when the evidence does not
         single one out

Rules (no machine learning, no scores):

- HIGH: a reviewer-confirmed junction reference or alias; an OSM feature
  named as the junction that sits on a road crossing; an explicitly named
  crossing of two roads that meet at one place; a named flyover/underpass
  that is one structure; a named road with both ends of the stretch found.
- MEDIUM: a junction reference not yet confirmed; a named road with no
  stretch (the article does not say which part); a name that matches places
  far apart (ambiguous).
- LOW: only a locality or a landmark (not a road) is named.
- UNRESOLVED: nothing in the network matches.

Only an unambiguous HIGH result may become GIS_RESOLVED, and then only as a
proposal for human QC. Every position comes from an OSM feature, a confirmed
reference, or a projection onto an OSM road line: none is made up.

This is not a navigation-grade map matcher.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from services.extraction.road_mentions import _NAMED_ROAD, _ROAD_NUMBER, _clean_name
from services.geo_resolution import PlaceResolver

from .geometry import Position, chains, clusters, distance_m, line_length_m, project, substring
from .network import NamedPoint, RoadNetwork, RoadWay, name_key, node_position, shared_nodes

ENGINE = "osm-deterministic-1"
# A point this close to a road line lies on it.
ON_ROAD_M = 80
# Features with one name closer than this are one place.
SAME_PLACE_M = 150
# A named structure (flyover, underpass) is one if its parts are this close.
ONE_STRUCTURE_M = 400
# Parts of a named road closer than this belong to one stretch of it.
ONE_ROAD_M = 700

_JUNCTION_WORDS = ("junction", "circle", "chowrasta", "rotary", "x road", "crossroads", "cross road")
_STRUCTURE_WORDS = ("flyover", "underpass", "bridge", "tunnel", "rob", "rub", "skywalk")
_ROAD_WORDS = ("road", "marg", "highway", "street", "lane", "expressway", "avenue", "bypass")
_STRETCH = re.compile(
    r"\b(?:from|between)\s+(?P<a>[A-Z][\w.’'&/-]*(?:\s+[A-Za-z0-9][\w.’'&/-]*){0,6}?)\s+"
    r"(?:to|till|until|and|up\s+to)\s+(?P<b>[A-Z][\w.’'&/-]*(?:\s+[A-Za-z0-9][\w.’'&/-]*){0,6}?)"
    r"(?=\s*(?:[,.;:)]|\s(?:for|on|in|from|due|as|with|is|are|will|has|have|stretch|road)\b|$))"
)
_CROSSING = re.compile(
    r"\b(?:intersection|junction|crossing)\s+of\s+(?P<a>[A-Z][\w.’'&-]*(?:\s+[A-Za-z0-9][\w.’'&-]*){0,5}?)\s+"
    r"and\s+(?P<b>[A-Z][\w.’'&-]*(?:\s+[A-Za-z0-9][\w.’'&-]*){0,5}?)(?=\s*(?:[,.;:)]|$|\s(?:will|is|on|for|from)\b))"
)


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNRESOLVED = "UNRESOLVED"


class MatchMethod(StrEnum):
    JUNCTION_REFERENCE = "JUNCTION_REFERENCE"
    ALIAS_MATCH = "ALIAS_MATCH"
    OSM_NAMED_JUNCTION = "OSM_NAMED_JUNCTION"
    ROAD_INTERSECTION = "ROAD_INTERSECTION"
    EXACT_ROAD_NAME = "EXACT_ROAD_NAME"
    ROAD_STRETCH = "ROAD_STRETCH"
    NEARBY_ROAD = "NEARBY_ROAD"
    LOCALITY_ONLY = "LOCALITY_ONLY"
    REVIEWER_CONFIRMED = "REVIEWER_CONFIRMED"


@dataclass(frozen=True)
class JunctionRef:
    """A reviewer-maintained junction name (see the junction_references table)."""

    ref_id: int
    name: str
    aliases: tuple[str, ...]
    # CONFIRMED, UNCONFIRMED or REJECTED.
    status: str
    position: Position | None
    osm_node_id: int | None = None
    related_roads: tuple[str, ...] = ()

    @property
    def keys(self) -> dict[str, bool]:
        """name key -> whether it is an alias."""
        found = {name_key(self.name): False}
        for alias in self.aliases:
            found.setdefault(name_key(alias), True)
        return found


@dataclass(frozen=True)
class Candidate:
    matched_name: str
    method: MatchMethod
    geometry: dict
    osm_ids: tuple[str, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class Mention:
    text: str
    found_in: str
    # junction, structure, road, place, stretch, crossing
    kind: str
    # Stretches and crossings: their two parts; a stretch may also name its road.
    parts: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocationResult:
    mention: Mention
    confidence: Confidence
    chosen: Candidate | None = None
    alternatives: tuple[Candidate, ...] = ()
    ambiguous: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def applicable(self) -> bool:
        """Defensible enough to be proposed as GIS_RESOLVED (still subject to QC)."""
        return self.confidence is Confidence.HIGH and not self.ambiguous and self.chosen is not None


@dataclass(frozen=True)
class GisRequest:
    event_id: str
    city_id: str
    title: str
    summary: str | None = None
    body: str | None = None
    # Names REI already extracted (road mentions, affected locations), with where.
    known: tuple[tuple[str, str], ...] = ()


def _kind(text: str) -> str:
    key = name_key(text)
    if key.endswith(_JUNCTION_WORDS) or key.endswith(("jn", "x roads")):
        return "junction"
    if key.endswith(_STRUCTURE_WORDS):
        return "structure"
    if key.endswith(_ROAD_WORDS) or re.fullmatch(r"(nh|sh) \d+\w?|orr|outer ring road", key):
        return "road"
    return "place"


def _variants(text: str) -> list[str]:
    """The name, then the name without leading words ("Gachibowli's IIIT Junction" -> "iiit junction")."""
    words = name_key(text).split()
    out = [" ".join(words[i:]) for i in range(len(words)) if len(words) - i >= 2 or i == 0]
    return list(dict.fromkeys(v for v in out if v))


def _point(position: Position) -> dict:
    return {"type": "Point", "coordinates": [position[0], position[1]]}


def _lines(lines: Sequence[Sequence[Position]]) -> dict:
    parts = [[list(p) for p in line] for line in lines if len(line) >= 2]
    if len(parts) == 1:
        return {"type": "LineString", "coordinates": parts[0]}
    return {"type": "MultiLineString", "coordinates": parts}


def _way_ids(ways: Sequence[RoadWay]) -> tuple[str, ...]:
    return tuple(f"way/{w.way_id}" for w in ways)


class OsmGisEngine:
    """Implements the GisResolutionEngine contract over an OSM road network."""

    def __init__(
        self,
        network: RoadNetwork,
        junctions: Sequence[JunctionRef] = (),
        places: PlaceResolver | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> None:
        self.network = network
        self.junctions = [j for j in junctions if j.status != "REJECTED"]
        self.places = places
        self.bbox = bbox

    # --- mentions ------------------------------------------------------------------

    def mentions(self, request: GisRequest) -> list[Mention]:
        found: dict[tuple[str, str], Mention] = {}

        def add(mention: Mention) -> None:
            found.setdefault((name_key(mention.text), mention.kind), mention)

        fields = (("title", request.title), ("summary", request.summary), ("body", request.body))
        for where, text in fields:
            if not text:
                continue
            for match in _STRETCH.finditer(text):
                add(Mention(f"{match['a']} to {match['b']}", where, "stretch", (match["a"], match["b"])))
            for match in _CROSSING.finditer(text):
                add(Mention(f"{match['a']} and {match['b']}", where, "crossing", (match["a"], match["b"])))
            # Named roads, junctions and structures, written with capitals
            # (headlines included: leading words are trimmed when matching).
            for match in _NAMED_ROAD.finditer(text):
                name = _clean_name(match.group(1))
                if name:
                    full = f"{name} {match.group(2)}"
                    add(Mention(full, where, _kind(full)))
            for match in _ROAD_NUMBER.finditer(text):
                add(Mention(f"{match.group(1)}-{match.group(2)}", where, "road"))
            # Reviewer-maintained junction names, however the text writes them.
            key_text = f" {name_key(text)} "
            for junction in self.junctions:
                for key in junction.keys:
                    if f" {key} " in key_text:
                        add(Mention(junction.name if key == name_key(junction.name) else key, where, "junction"))
            if self.places is not None:
                for place in self.places.find_in(text, where):
                    if place.kind in ("area", "ward", "landmark") and place.has_position:
                        add(Mention(place.name, where, "place"))
        # Names the detector already recorded, unless the text itself gave them
        # (so a location the resolver recorded is not resolved a second time).
        found_keys = {name_key(m.text) for m in found.values()}
        for text, where in request.known:
            if name_key(text) not in found_keys:
                add(Mention(text, where, _kind(text)))
        # A name inside a stretch or crossing (or a piece of one) is resolved as part of it, not twice.
        parts = [
            f" {name_key(part)} " for m in found.values() if m.kind in ("stretch", "crossing") for part in m.parts
        ]
        ordered = sorted(found.values(), key=lambda m: ("title", "summary", "body").index(m.found_in)
                         if m.found_in in ("title", "summary", "body") else 1)  # fmt: skip
        return [
            m for m in ordered
            if m.kind in ("stretch", "crossing") or not any(f" {name_key(m.text)} " in part for part in parts)
        ]  # fmt: skip

    # --- resolving ----------------------------------------------------------------------

    def resolve_request(self, request: GisRequest) -> list[LocationResult]:
        results = [self.resolve_mention(m) for m in self.mentions(request)]
        # A road a resolved stretch already covers is that stretch, not a second location.
        stretch_ways = {
            way for r in results if r.mention.kind == "stretch" and r.chosen for way in r.chosen.osm_ids
        }
        results = [
            r for r in results
            if not (r.mention.kind == "road" and stretch_ways and r.confidence is not Confidence.HIGH
                    and {way for c in ([r.chosen] if r.chosen else []) + list(r.alternatives) for way in c.osm_ids} <= stretch_ways
                    and (r.chosen or r.alternatives))
        ]  # fmt: skip
        # Several mentions of one place resolve once (e.g. "Khajaguda junction" and "Khajaguda Jn").
        seen: set[tuple] = set()
        unique = []
        for result in results:
            key = (result.chosen.osm_ids, result.chosen.method) if result.chosen else (result.mention.text,)
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return unique

    def resolve_mention(self, mention: Mention) -> LocationResult:
        if mention.kind == "stretch":
            return self._stretch(mention)
        if mention.kind == "crossing":
            return self._crossing(mention)
        for variant in _variants(mention.text):
            result = self._by_name(mention, variant)
            if result is not None:
                return self._inside_city(result)
        return LocationResult(
            mention, Confidence.UNRESOLVED,
            reasons=(f"no road, junction or reference named “{mention.text}” in {self.network.version}",),
        )  # fmt: skip

    def _inside_city(self, result: LocationResult) -> LocationResult:
        """A candidate outside the city's area is not this city's."""
        if self.bbox is None or result.chosen is None:
            return result
        from .network import within

        coords = result.chosen.geometry["coordinates"]
        flat = [coords] if result.chosen.geometry["type"] == "Point" else (
            coords if result.chosen.geometry["type"] == "LineString" else [p for part in coords for p in part]
        )  # fmt: skip
        if within([tuple(p) for p in flat], self.bbox):
            return result
        return LocationResult(result.mention, Confidence.UNRESOLVED, reasons=("the candidate lies outside the city's area",))

    def _by_name(self, mention: Mention, key: str) -> LocationResult | None:
        junction = self._junction_ref(mention, key)
        if junction is not None:
            return junction
        kind = _kind(key) if mention.kind not in ("place",) else "place"
        if kind == "junction":
            found = self._osm_junction(mention, key)
            if found is not None:
                return found
        ways = self.network.ways_named(key)
        if ways:
            if kind == "structure" or all(w.is_structure for w in ways):
                return self._structure(mention, key, ways)
            return self._road(mention, key, ways)
        if kind == "junction":
            return None
        if mention.kind == "place" and self.places is not None:
            place = self.places.lookup(mention.text, found_in=mention.found_in)
            if place is not None and place.has_position:
                return LocationResult(
                    mention, Confidence.LOW,
                    reasons=(f"“{place.name}” is a {place.kind}, not a road or junction: the event "
                             "stays at its approximate position",),
                )  # fmt: skip
        return None

    def _junction_ref(self, mention: Mention, key: str) -> LocationResult | None:
        for junction in self.junctions:
            if key not in junction.keys or junction.position is None:
                continue
            alias = junction.keys[key]
            method = MatchMethod.ALIAS_MATCH if alias else MatchMethod.JUNCTION_REFERENCE
            related = self._related_segments(junction)
            candidate = Candidate(
                junction.name, method, _point(junction.position),
                (f"junction-reference/{junction.ref_id}",)
                + ((f"node/{junction.osm_node_id}",) if junction.osm_node_id else ()),
                (f"junction reference #{junction.ref_id} “{junction.name}”"
                 + (f" (alias “{key}”)" if alias else ""),),
            )  # fmt: skip
            if junction.status == "CONFIRMED":
                return LocationResult(
                    mention, Confidence.HIGH, candidate, related,
                    reasons=("a reviewer confirmed this junction",),
                )  # fmt: skip
            return LocationResult(
                mention, Confidence.MEDIUM, candidate, related,
                reasons=("the junction reference has not been confirmed by a reviewer yet",),
            )  # fmt: skip
        return None

    def _related_segments(self, junction: JunctionRef) -> tuple[Candidate, ...]:
        """The named roads at a junction: their ways through, or beside, the junction."""
        if junction.position is None:
            return ()
        out = []
        for road in junction.related_roads:
            key = name_key(road)
            near = [
                w for w in self.network.ways_near(junction.position, 30) if key in w.keys
            ]
            if near:
                out.append(Candidate(
                    road, MatchMethod.NEARBY_ROAD, _lines([w.coords for w in near]), _way_ids(near),
                    (f"“{road}” passes through the junction",),
                ))  # fmt: skip
        return tuple(out)

    def _on_crossing(self, point: NamedPoint) -> bool:
        if point.node_id is not None:
            ways = self.network.ways_through_node(point.node_id)
            if len(ways) >= 2:
                return True
        near = self.network.ways_near(point.position, 20)
        return len({w.name for w in near if w.name}) >= 2

    def _osm_junction(self, mention: Mention, key: str) -> LocationResult | None:
        points = [p for p in self.network.points_named(key) if self._on_crossing(p)]
        if not points:
            return None
        groups = clusters(points, lambda p: p.position, SAME_PLACE_M)
        candidates = [
            Candidate(
                group[0].name, MatchMethod.OSM_NAMED_JUNCTION, _point(group[0].position),
                tuple(p.osm_ref for p in group),
                (f"OSM names {group[0].osm_ref} “{group[0].name}”, on a crossing of roads",),
            )  # fmt: skip
            for group in groups
        ]
        if len(candidates) == 1:
            return LocationResult(mention, Confidence.HIGH, candidates[0])
        return LocationResult(
            mention, Confidence.MEDIUM, None, tuple(candidates), ambiguous=True,
            reasons=(f"{len(candidates)} different places are named “{mention.text}”",),
        )  # fmt: skip

    def _structure(self, mention: Mention, key: str, ways: list[RoadWay]) -> LocationResult:
        groups = clusters(ways, lambda w: w.coords[len(w.coords) // 2], ONE_STRUCTURE_M)
        candidates = [
            Candidate(
                group[0].name or key, MatchMethod.EXACT_ROAD_NAME, _lines([w.coords for w in group]),
                _way_ids(group), (f"OSM road(s) named “{group[0].name}”",),
            )  # fmt: skip
            for group in groups
        ]
        if len(candidates) == 1:
            return LocationResult(mention, Confidence.HIGH, candidates[0])
        return LocationResult(
            mention, Confidence.MEDIUM, None, tuple(candidates), ambiguous=True,
            reasons=(f"{len(candidates)} separate structures are named “{mention.text}”",),
        )  # fmt: skip

    def _road(self, mention: Mention, key: str, ways: list[RoadWay]) -> LocationResult:
        groups = clusters(ways, lambda w: w.coords[len(w.coords) // 2], ONE_ROAD_M)
        candidates = [
            Candidate(
                group[0].name or key, MatchMethod.EXACT_ROAD_NAME, _lines(chains([(w.node_ids, w.coords) for w in group])),
                _way_ids(group),
                (f"OSM road “{group[0].name or key}”, "
                 f"{sum(line_length_m(w.coords) for w in group) / 1000:.1f} km of ways",),
            )  # fmt: skip
            for group in groups
        ]
        if len(candidates) == 1:
            return LocationResult(
                mention, Confidence.MEDIUM, candidates[0],
                reasons=("the road is named but not which part of it is affected",),
            )  # fmt: skip
        return LocationResult(
            mention, Confidence.MEDIUM, None, tuple(candidates), ambiguous=True,
            reasons=(f"{len(candidates)} separate roads are named “{mention.text}”",),
        )  # fmt: skip

    def _crossing(self, mention: Mention) -> LocationResult:
        a, b = mention.parts
        ways_a = next((self.network.ways_named(v) for v in _variants(a) if self.network.ways_named(v)), [])
        ways_b = next((self.network.ways_named(v) for v in _variants(b) if self.network.ways_named(v)), [])
        if not ways_a or not ways_b:
            missing = a if not ways_a else b
            return LocationResult(mention, Confidence.UNRESOLVED, reasons=(f"no OSM road named “{missing}”",))
        return self.intersection(mention, a, ways_a, b, ways_b)

    def intersection(self, mention: Mention, a: str, ways_a: list[RoadWay], b: str, ways_b: list[RoadWay]) -> LocationResult:
        nodes = shared_nodes(ways_a, ways_b)
        if not nodes:
            return LocationResult(mention, Confidence.UNRESOLVED, reasons=(f"“{a}” and “{b}” do not meet in OSM",))
        groups = clusters(list(nodes.items()), lambda item: item[1], 60)
        candidates = []
        for group in groups:
            # The OSM node nearest the middle of the crossing: a real node, not a computed point.
            middle = (sum(p[0] for _, p in group) / len(group), sum(p[1] for _, p in group) / len(group))
            node_id, position = min(group, key=lambda item: distance_m(item[1], middle))
            candidates.append(Candidate(
                f"{a} × {b}", MatchMethod.ROAD_INTERSECTION, _point(position),
                tuple(f"node/{n}" for n, _ in group), (f"“{a}” and “{b}” share OSM node {node_id}",),
            ))  # fmt: skip
        if len(candidates) == 1:
            return LocationResult(mention, Confidence.HIGH, candidates[0])
        return LocationResult(
            mention, Confidence.MEDIUM, None, tuple(candidates), ambiguous=True,
            reasons=(f"“{a}” and “{b}” meet at {len(candidates)} places",),
        )  # fmt: skip

    def _spot(self, text: str) -> tuple[Position, str, str] | None:
        """A precise position for a stretch end: (position, name, how found). Never a locality."""
        for variant in _variants(text):
            for junction in self.junctions:
                if variant in junction.keys and junction.status == "CONFIRMED" and junction.position:
                    return junction.position, junction.name, f"junction reference #{junction.ref_id}"
            points = [p for p in self.network.points_named(variant)]
            groups = clusters(points, lambda p: p.position, SAME_PLACE_M)
            if len(groups) == 1:
                return groups[0][0].position, groups[0][0].name, groups[0][0].osm_ref
        if self.places is not None:
            place = self.places.lookup(text, found_in="stretch")
            if place is not None and place.has_position and place.kind in ("junction", "landmark", "flyover"):
                return (place.longitude, place.latitude), place.name, f"OpenStreetMap {place.osm_ref}"
        return None

    def _stretch(self, mention: Mention) -> LocationResult:
        a_text, b_text = mention.parts
        a, b = self._spot(a_text), self._spot(b_text)
        missing = [t for t, s in ((a_text, a), (b_text, b)) if s is None]
        if missing:
            return LocationResult(
                mention, Confidence.UNRESOLVED,
                reasons=tuple(f"the stretch end “{t}” is not a known junction or landmark" for t in missing),
            )  # fmt: skip
        # The road both ends lie on (within ON_ROAD_M), by name.
        near_a = {k: w for w in self.network.ways_near(a[0], ON_ROAD_M) for k in w.keys}
        near_b = {k: w for w in self.network.ways_near(b[0], ON_ROAD_M) for k in w.keys}
        names = sorted(set(near_a) & set(near_b) - {""})
        if len(names) != 1:
            return LocationResult(
                mention, Confidence.UNRESOLVED if not names else Confidence.MEDIUM,
                reasons=((f"no single named road runs past both “{a[1]}” and “{b[1]}”",) if not names
                         else (f"several roads run past both ends: {', '.join(names)}",)),
                ambiguous=bool(names),
            )  # fmt: skip
        ways = self.network.ways_named(names[0])
        parts = []
        for line in chains([(w.node_ids, w.coords) for w in ways]):
            da, along_a, _ = project(a[0], line)
            db, along_b, _ = project(b[0], line)
            if da <= ON_ROAD_M and db <= ON_ROAD_M and abs(along_a - along_b) > 1:
                parts.append(substring(line, along_a, along_b))
        if not parts:
            return LocationResult(mention, Confidence.UNRESOLVED, reasons=("the ends do not lie on one continuous road line",))
        road = ways[0].name or names[0]
        candidate = Candidate(
            f"{road}: {a[1]} to {b[1]}", MatchMethod.ROAD_STRETCH, _lines(parts), _way_ids(ways),
            (f"start “{a[1]}” ({a[2]})", f"end “{b[1]}” ({b[2]})",
             f"{len(parts)} carriageway(s) of “{road}”, {max(line_length_m(p) for p in parts):.0f} m"),
        )  # fmt: skip
        return LocationResult(mention, Confidence.HIGH, candidate)


__all__ = [
    "Candidate",
    "Confidence",
    "ENGINE",
    "GisRequest",
    "JunctionRef",
    "LocationResult",
    "MatchMethod",
    "Mention",
    "OsmGisEngine",
]
