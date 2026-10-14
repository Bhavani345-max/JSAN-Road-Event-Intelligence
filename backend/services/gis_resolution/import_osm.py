"""Import a city's OpenStreetMap road network, as of one pinned snapshot, into PostGIS:

    python -m services.gis_resolution.import_osm --city hyderabad --snapshot 2026-10-06T00:00:00Z --download-only
    python -m services.gis_resolution.import_osm --city hyderabad --snapshot 2026-10-06T00:00:00Z --validate
    python -m services.gis_resolution.import_osm --city hyderabad --snapshot 2026-10-06T00:00:00Z            # download, validate, load

One snapshot. Every query carries Overpass's `[date:"…"]` setting, so every
tile describes OSM exactly as it was at that moment, however long the
download takes. Queries go to overpass-api.de only (`PINNED_SERVER`): public
mirrors run their own, sometimes months-old, databases, and tiles from
different snapshots disagree where they meet. Each answer is verified: no
Overpass remark (a timeout or partial answer), and every element's own OSM
timestamp at or before the snapshot. A tile that fails is marked failed and
retried in a later pass; no other server is used.

Tiles. The city's area (packages/cities, `bbox`) is fetched in a 6 x 6 grid.
A tile the server cannot answer whole is fetched in quarters (and quarters of
quarters), each piece saved, then joined by OSM way id. Overpass returns each
way whole, so a way crossing a tile edge is in both tiles, identical; the
load keeps it once.

Files, all named with the snapshot, under backend/.data/osm/<city>/snapshot-<stamp>/:
roads_<row>_<col>@<stamp>.json.gz, pieces/…, named_points@<stamp>.json.gz and
a validation report. Each file carries its metadata under "rei". User names,
user ids and changeset ids that Overpass sends with element metadata are
dropped; versions and timestamps are kept.

Roads: drivable public road classes (motorway … residential, living streets
and links). Named points: OSM features named as junctions, excluding bus stops.

Data © OpenStreetMap contributors, Open Database Licence (ODbL) 1.0.
"""

import argparse
import gzip
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

from packages.cities import get_city

from .network import ROAD_CLASSES, points_from_overpass, ways_from_overpass

PINNED_SERVER = "https://overpass-api.de/api/interpreter"
SERVER_NAME = "overpass-api.de"
USER_AGENT = "JSAN-REI/1.0 (road event intelligence PoC; GIS import)"
# backend/services/gis_resolution/import_osm.py -> backend/.data/osm
CACHE_ROOT = Path(__file__).resolve().parents[2] / ".data" / "osm"
GRID = 6
# A tile the server cannot answer whole is fetched in quarters, at most this many times over.
MAX_SPLIT = 2
# Element metadata REI does not keep (personal data it has no use for).
_DROPPED_META = ("user", "uid", "changeset")

_ROADS = """[out:json][timeout:180][date:"{snapshot}"];
way["highway"~"^({classes})$"]({bbox});
out meta geom;"""
_POINTS = """[out:json][timeout:180][date:"{snapshot}"];
(
  node["junction"]["name"]({bbox});
  way["junction"]["name"]({bbox});
  node["highway"~"^(traffic_signals|motorway_junction|mini_roundabout)$"]["name"]({bbox});
  node["name"~"(Junction|Jn|X Road|X Roads|Cross Road|Cross Roads|Crossroads|Circle|Chowrasta|Rotary)$",i]({bbox});
);
out center meta;"""


class FetchFailed(RuntimeError):
    """The pinned server did not give a complete, verified answer."""


def network_version(snapshot: str) -> str:
    return f"OSM snapshot: {snapshot}"


def stamp(snapshot: str) -> str:
    """The snapshot as it appears in file names: 2026-10-06T000000Z."""
    return snapshot.replace(":", "")


def parse_snapshot(text: str) -> str:
    moment = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if moment > datetime.now(UTC):
        raise ValueError("the snapshot cannot be in the future")
    return text


def tiles(bbox: tuple[float, float, float, float], grid: int = GRID):
    south, west, north, east = bbox
    dlat, dlon = (north - south) / grid, (east - west) / grid
    for row in range(grid):
        for col in range(grid):
            yield row, col, (south + row * dlat, west + col * dlon, south + (row + 1) * dlat, west + (col + 1) * dlon)


def _bbox_text(b) -> str:
    return ",".join(f"{v:.6f}" for v in b)


def query_bbox(b) -> tuple[float, ...]:
    """The bounding box exactly as sent to Overpass (six decimals)."""
    return tuple(float(v) for v in _bbox_text(b).split(","))


def verify(document: dict, snapshot: str) -> None:
    """Raise FetchFailed unless the answer is complete and entirely of the snapshot."""
    if "elements" not in document or "osm3s" not in document:
        raise FetchFailed("not an Overpass answer")
    if document.get("remark"):
        raise FetchFailed(f"Overpass remark (partial or timed-out answer): {document['remark'][:100]}")
    for element in document["elements"]:
        when = element.get("timestamp")
        if not when or "version" not in element:
            raise FetchFailed(f"{element.get('type')} {element.get('id')} has no version/timestamp: snapshot unverified")
        if when > snapshot:
            raise FetchFailed(f"{element['type']} {element['id']} is from {when}, after the snapshot {snapshot}")


def fetch(query: str, snapshot: str, *, attempts: int = 3, client=httpx) -> dict:
    """POST a pinned query to overpass-api.de; retry the same server; verify the answer."""
    reason = "no attempt"
    for attempt in range(attempts):
        try:
            response = client.post(PINNED_SERVER, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=300)
            if response.status_code == 200:
                document = response.json()
                verify(document, snapshot)
                for element in document["elements"]:
                    for key in _DROPPED_META:
                        element.pop(key, None)
                return document
            reason = f"HTTP {response.status_code}"
        except FetchFailed as error:
            reason = str(error)
        except (httpx.HTTPError, ValueError) as error:
            reason = str(error)[:120] or type(error).__name__
        wait = 15 * (attempt + 1)
        print(f"    {SERVER_NAME}: {reason}; retry in {wait} s", flush=True)
        time.sleep(wait)
    raise FetchFailed(reason)


def _read(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return json.load(file)


def _write(path: Path, document: dict) -> None:
    """Write atomically: a stopped download never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    with gzip.open(temporary, "wt", encoding="utf-8") as file:
        json.dump(document, file)
    temporary.replace(path)


def _join(parts: list[dict], label: str) -> list[dict]:
    """Join pieces by OSM id. Copies of one way must be identical (one snapshot), else it is an error."""
    joined: dict[tuple, dict] = {}
    for part in parts:
        for element in part["elements"]:
            key = (element["type"], element["id"])
            if key in joined and joined[key] != element:
                raise FetchFailed(f"{label}: two different copies of {key[0]} {key[1]}")
            joined.setdefault(key, element)
    return sorted(joined.values(), key=lambda e: (e["type"], e["id"]))


class Downloader:
    def __init__(self, city, snapshot: str, root: Path, *, client=httpx, pause: float = 5) -> None:
        self.city, self.snapshot, self.root = city, snapshot, root
        self.client, self.pause = client, pause

    def tile_path(self, row: int, col: int) -> Path:
        return self.root / f"roads_{row}_{col}@{stamp(self.snapshot)}.json.gz"

    def piece_path(self, row: int, col: int, piece: str) -> Path:
        return self.root / "pieces" / f"roads_{row}_{col}_{piece}@{stamp(self.snapshot)}.json.gz"

    def points_path(self) -> Path:
        return self.root / f"named_points@{stamp(self.snapshot)}.json.gz"

    def _meta(self, **extra) -> dict:
        return {
            "snapshot": self.snapshot, "network_version": network_version(self.snapshot),
            "server": SERVER_NAME, "verified": True, "city": self.city.id,
            "downloaded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), **extra,
        }  # fmt: skip

    def _area(self, row: int, col: int, bbox, piece: str, depth: int) -> tuple[dict, list[str]]:
        """Roads of one area: a saved piece, the server's answer, or its quarters joined."""
        if piece:
            path = self.piece_path(row, col, piece)
            if path.exists():
                return _read(path), [piece]
        query = _ROADS.format(snapshot=self.snapshot, classes="|".join(ROAD_CLASSES), bbox=_bbox_text(bbox))
        try:
            document = fetch(query, self.snapshot, attempts=3 if depth < MAX_SPLIT else 6, client=self.client)
            time.sleep(self.pause)
            if piece:
                document["rei"] = self._meta(tile=[row, col], piece=piece, bbox=_bbox_text(bbox))
                _write(self.piece_path(row, col, piece), document)
            return document, [piece] if piece else []
        except FetchFailed:
            if depth >= MAX_SPLIT:
                raise
        print(f"    splitting {piece or 'tile'} {_bbox_text(bbox)} into quarters", flush=True)
        parts, pieces = [], []
        for qrow, qcol, quarter in tiles(bbox, grid=2):
            name = f"{piece}.q{qrow}{qcol}" if piece else f"q{qrow}{qcol}"
            part, names = self._area(row, col, quarter, name, depth + 1)
            parts.append(part)
            pieces += names
        return {"osm3s": parts[0]["osm3s"], "elements": _join(parts, f"tile {row},{col}")}, pieces

    def tile(self, row: int, col: int, bbox) -> dict:
        path = self.tile_path(row, col)
        if path.exists():
            return _read(path)
        document, pieces = self._area(row, col, bbox, "", 0)
        document["rei"] = self._meta(tile=[row, col], bbox=_bbox_text(bbox), pieces=pieces)
        _write(path, document)
        return document

    def points(self) -> dict:
        path = self.points_path()
        if path.exists():
            return _read(path)
        bbox = tuple(self.city.bbox)
        document = fetch(_POINTS.format(snapshot=self.snapshot, bbox=_bbox_text(bbox)), self.snapshot,
                         attempts=6, client=self.client)  # fmt: skip
        document["rei"] = self._meta(bbox=_bbox_text(bbox))
        _write(path, document)
        return document

    def run(self, *, passes: int = 30, wait_between_passes: float = 60) -> bool:
        """Download every missing tile; failed tiles are retried in later passes. True when complete."""
        layout = list(tiles(tuple(self.city.bbox)))
        for number in range(1, passes + 1):
            failed: list = []
            for row, col, bbox in layout:
                if self.tile_path(row, col).exists():
                    continue
                try:
                    document = self.tile(row, col, bbox)
                    print(f"  tile {row},{col}: {len(document['elements'])} road ways", flush=True)
                except FetchFailed as error:
                    failed.append((row, col))
                    print(f"  tile {row},{col}: FAILED ({error}); will retry", flush=True)
            if not self.points_path().exists():
                try:
                    print(f"  named points: {len(self.points()['elements'])}", flush=True)
                except FetchFailed as error:
                    failed.append("named points")
                    print(f"  named points: FAILED ({error}); will retry", flush=True)
            if not failed:
                return True
            print(f"pass {number}: {len(failed)} not yet downloaded: {failed}", flush=True)
            time.sleep(wait_between_passes)
        return False


def validate(city, snapshot: str, root: Path, grid: int = GRID) -> dict:
    """Check the saved snapshot before anything is loaded. Returns the findings and counts."""
    problems: list[str] = []
    layout = {(r, c): b for r, c, b in tiles(tuple(city.bbox), grid)}
    downloader = Downloader(city, snapshot, root)
    docs: dict[tuple, dict] = {}
    for key in layout:
        path = downloader.tile_path(*key)
        if not path.exists():
            problems.append(f"tile {key} missing")
            continue
        docs[key] = _read(path)
    # Nothing of another snapshot, and no half-written file, in the folder.
    foreign = [p.name for p in root.rglob("*") if p.is_file() and p.suffix == ".gz" and f"@{stamp(snapshot)}" not in p.name]
    partial = [p.name for p in root.rglob("*.partial")]
    if foreign:
        problems.append(f"files of another snapshot present: {foreign[:5]}")
    if partial:
        problems.append(f"half-written files present: {partial[:5]}")

    def check_doc(label: str, document: dict) -> None:
        meta = document.get("rei") or {}
        if meta.get("snapshot") != snapshot or meta.get("server") != SERVER_NAME or not meta.get("verified"):
            problems.append(f"{label}: metadata says snapshot {meta.get('snapshot')} from {meta.get('server')}")
        try:
            verify(document, snapshot)
        except FetchFailed as error:
            problems.append(f"{label}: {error}")

    for key, document in docs.items():
        check_doc(f"tile {key}", document)

    # Quarter pieces join back into exactly their tile, and cover it.
    split_tiles = {}
    for key, document in docs.items():
        pieces = (document.get("rei") or {}).get("pieces") or []
        if not pieces:
            continue
        parts = []
        for piece in pieces:
            path = downloader.piece_path(*key, piece)
            if not path.exists():
                problems.append(f"tile {key}: piece {piece} missing")
                continue
            part = _read(path)
            check_doc(f"tile {key} piece {piece}", part)
            parts.append(part)
        try:
            if _join(parts, f"tile {key}") != document["elements"]:
                problems.append(f"tile {key}: pieces do not join into the saved tile")
        except FetchFailed as error:
            problems.append(str(error))
        boxes = [tuple(map(float, part["rei"]["bbox"].split(","))) for part in parts]
        area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
        tile_box = query_bbox(layout[key])
        tile_area = (tile_box[2] - tile_box[0]) * (tile_box[3] - tile_box[1])
        inside = all(tile_box[0] <= b[0] and tile_box[1] <= b[1] and b[2] <= tile_box[2] and b[3] <= tile_box[3] for b in boxes)
        if not inside or not math.isclose(area, tile_area, rel_tol=1e-4):
            problems.append(f"tile {key}: pieces cover {area / tile_area:.6f} of the tile (inside: {inside})")
        split_tiles[key] = len(pieces)

    # Copies of a way in several tiles must be identical, so the copy kept does not matter.
    copies: dict[int, dict[tuple, dict]] = defaultdict(dict)
    for key, document in docs.items():
        ids = [e["id"] for e in document["elements"]]
        if len(ids) != len(set(ids)):
            problems.append(f"tile {key}: a way id appears twice in the tile")
        for element in document["elements"]:
            copies[element["id"]][key] = element
    differing = [w for w, by_tile in copies.items() if len({json.dumps(e, sort_keys=True) for e in by_tile.values()}) > 1]
    if differing:
        problems.append(f"{len(differing)} ways differ between tiles, e.g. {differing[:5]}")

    # Cross-tile completeness: a way with a vertex inside a tile's query box is in that tile.
    boxes = {key: query_bbox(b) for key, b in layout.items() if key in docs}
    incomplete = []
    for wid, by_tile in copies.items():
        element = next(iter(by_tile.values()))
        entered = {key for key, (s, w, n, e) in boxes.items()
                   for p in element.get("geometry") or [] if s <= p["lat"] <= n and w <= p["lon"] <= e}  # fmt: skip
        if not entered <= set(by_tile):
            incomplete.append((wid, sorted(entered - set(by_tile))))
    if incomplete:
        problems.append(f"{len(incomplete)} ways missing from a tile they enter, e.g. {incomplete[:3]}")

    # Geometry: a line of at least two valid points, one per node, in the region.
    south, west, north, east = city.bbox
    bad_geometry = []
    for wid, by_tile in copies.items():
        element = next(iter(by_tile.values()))
        geometry = element.get("geometry") or []
        if (element.get("type") != "way" or len(geometry) < 2 or len(geometry) != len(element.get("nodes") or [])
                or any(p is None or not (math.isfinite(p["lat"]) and math.isfinite(p["lon"]))
                       or not (south - 0.5 < p["lat"] < north + 0.5 and west - 0.5 < p["lon"] < east + 0.5)
                       for p in geometry)):  # fmt: skip
            bad_geometry.append(wid)
    if bad_geometry:
        problems.append(f"{len(bad_geometry)} ways with invalid geometry, e.g. {bad_geometry[:5]}")

    points = None
    if downloader.points_path().exists():
        point_doc = _read(downloader.points_path())
        check_doc("named points", point_doc)
        points = len(points_from_overpass(point_doc))
    else:
        problems.append("named points missing")

    unique = {wid: next(iter(by_tile.values())) for wid, by_tile in copies.items()}
    parsed = ways_from_overpass({"elements": list(unique.values())})
    return {
        "snapshot": snapshot,
        "network_version": network_version(snapshot),
        "server": SERVER_NAME,
        "tiles_present": len(docs),
        "tiles_expected": len(layout),
        "split_tiles": {f"{k[0]},{k[1]}": n for k, n in sorted(split_tiles.items())},
        "unique_ways": len(unique),
        "road_ways_parsed": len(parsed),
        "segments": sum(len(e["nodes"]) - 1 for e in unique.values()),
        "named_ways": sum(1 for w in parsed if w.name),
        "cross_tile_ways": sum(1 for by_tile in copies.values() if len(by_tile) > 1),
        "way_copies_in_tiles": sum(len(by_tile) for by_tile in copies.values()),
        "latest_element_edit": max((e["timestamp"] for e in unique.values()), default=None),
        "named_points": points,
        "problems": problems,
        "consistent": not problems,
    }


def load_snapshot(city, snapshot: str, root: Path, database_url: str) -> dict:
    """Load a validated snapshot into PostGIS (one transaction). Ways are read in tile order, each kept once."""
    from .postgis import connect, ensure_schema, load

    downloader = Downloader(city, snapshot, root)
    ways = []
    for row, col, _ in tiles(tuple(city.bbox)):
        ways += ways_from_overpass(_read(downloader.tile_path(row, col)))
    points = points_from_overpass(_read(downloader.points_path()))
    with connect(database_url) as conn:
        ensure_schema(conn)
        return load(
            conn, city=city.id, bbox=tuple(city.bbox), ways=ways, points=points, osm_timestamp=snapshot,
            tiles=GRID * GRID, source=f"{network_version(snapshot)}; Overpass API ({SERVER_NAME}), {GRID}x{GRID} tiles",
        )  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Import a city's OSM road network, as of one snapshot, into PostGIS")
    parser.add_argument("--city", default="hyderabad")
    parser.add_argument("--snapshot", required=True, help="the OSM moment, e.g. 2026-10-06T00:00:00Z")
    parser.add_argument("--download-only", action="store_true", help="download and validate; do not load")
    parser.add_argument("--validate", action="store_true", help="validate the saved snapshot only")
    parser.add_argument("--from-cache", action="store_true", help="validate and load the saved snapshot; no download")
    parser.add_argument("--cache-dir", help="default: backend/.data/osm/<city>/snapshot-<stamp>")
    parser.add_argument("--database-url", default=os.environ.get("GIS_DATABASE_URL"))
    args = parser.parse_args(argv)

    snapshot = parse_snapshot(args.snapshot)
    city = get_city(args.city)
    root = Path(args.cache_dir) if args.cache_dir else CACHE_ROOT / city.id / f"snapshot-{stamp(snapshot)}"
    loading = not (args.download_only or args.validate)
    if loading and not args.database_url:
        sys.exit("Set GIS_DATABASE_URL (see .env.example) or pass --database-url")

    if not (args.validate or args.from_cache):
        print(f"{city.name}: downloading {network_version(snapshot)} from {SERVER_NAME} into {root}", flush=True)
        if not Downloader(city, snapshot, root).run():
            sys.exit("Download incomplete after all passes; run again to resume.")
    report = validate(city, snapshot, root)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"validation@{stamp(snapshot)}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["consistent"]:
        sys.exit("Validation failed: nothing loaded.")
    if loading:
        result = load_snapshot(city, snapshot, root, args.database_url)
        print(f"Loaded {result}. Data © OpenStreetMap contributors, ODbL.")


if __name__ == "__main__":
    main()
