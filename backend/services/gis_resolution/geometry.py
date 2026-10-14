"""Small, exact geometry helpers for the GIS resolver, in plain Python.

Positions are (longitude, latitude) in WGS 84. Distances use a local flat
approximation, accurate to well under a metre at city scale. Nothing here
creates a position that is not on an input geometry: projections land on the
road's own line, and substrings are made of the road's own vertices plus the
projected ends.
"""

import math
from collections.abc import Sequence

Position = tuple[float, float]


def distance_m(a: Position, b: Position) -> float:
    lat = math.radians((a[1] + b[1]) / 2)
    dx = (a[0] - b[0]) * 111_320 * math.cos(lat)
    dy = (a[1] - b[1]) * 110_570
    return math.hypot(dx, dy)


def line_length_m(line: Sequence[Position]) -> float:
    return sum(distance_m(line[i], line[i + 1]) for i in range(len(line) - 1))


def project(point: Position, line: Sequence[Position]) -> tuple[float, float, Position]:
    """(distance from the line in metres, distance along it in metres, the point on it)."""
    best = (math.inf, 0.0, line[0])
    along = 0.0
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        lat = math.radians((a[1] + b[1]) / 2)
        kx, ky = 111_320 * math.cos(lat), 110_570
        ax, ay = a[0] * kx, a[1] * ky
        bx, by = b[0] * kx, b[1] * ky
        px, py = point[0] * kx, point[1] * ky
        dx, dy = bx - ax, by - ay
        seg = dx * dx + dy * dy
        t = 0.0 if seg == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg))
        on = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d = distance_m(point, on)
        if d < best[0]:
            best = (d, along + math.sqrt(seg) * t, on)
        along += math.sqrt(seg)
    return best


def substring(line: Sequence[Position], start_m: float, end_m: float) -> list[Position]:
    """The part of a line between two distances along it, in the line's own direction."""
    lo, hi = sorted((start_m, end_m))
    out: list[Position] = []
    along = 0.0
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        seg = distance_m(a, b)
        seg_start, seg_end = along, along + seg
        if seg_end >= lo and seg_start <= hi and seg > 0:
            t0 = max(0.0, (lo - seg_start) / seg)
            t1 = min(1.0, (hi - seg_start) / seg)
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            if not out:
                out.append(p0)
            if p1 != out[-1]:
                out.append(p1)
        along = seg_end
    return out


def chains(ways: Sequence[tuple[Sequence[int], Sequence[Position]]]) -> list[list[Position]]:
    """Join ways that share end nodes into continuous lines.

    Each way is (node ids, positions). Ways are joined end to end where an end
    node is shared by exactly two of them; a fork ends a chain. A dual
    carriageway therefore gives two chains, one per direction.
    """
    remaining = [(list(nodes), list(coords)) for nodes, coords in ways if len(nodes) >= 2]
    ends: dict[int, list[int]] = {}
    for index, (nodes, _) in enumerate(remaining):
        for end in (nodes[0], nodes[-1]):
            ends.setdefault(end, []).append(index)
    used: set[int] = set()
    result: list[list[Position]] = []
    for start in range(len(remaining)):
        if start in used:
            continue
        used.add(start)
        nodes, coords = remaining[start]
        nodes, coords = list(nodes), list(coords)
        for forward in (True, False):
            while True:
                end = nodes[-1] if forward else nodes[0]
                nexts = [i for i in ends.get(end, []) if i not in used]
                if len(ends.get(end, [])) != 2 or not nexts:
                    break
                i = nexts[0]
                used.add(i)
                n2, c2 = remaining[i]
                if forward:
                    if n2[0] != end:
                        n2, c2 = n2[::-1], c2[::-1]
                    nodes += n2[1:]
                    coords += c2[1:]
                else:
                    if n2[-1] != end:
                        n2, c2 = n2[::-1], c2[::-1]
                    nodes = n2[:-1] + nodes
                    coords = c2[:-1] + coords
        result.append(coords)
    return result


def clusters(items: list, position_of, within_m: float) -> list[list]:
    """Group items whose positions lie within `within_m` of another item in the group."""
    groups: list[list] = []
    for item in items:
        here = position_of(item)
        joined = [g for g in groups if any(distance_m(here, position_of(o)) <= within_m for o in g)]
        merged = [item]
        for g in joined:
            merged += g
            groups.remove(g)
        groups.append(merged)
    return groups


def centre(points: Sequence[Position]) -> Position:
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
