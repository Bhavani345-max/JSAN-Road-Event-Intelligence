"""The snapshot-pinned Overpass download and its validation (6 October 2026). No network."""

import json
import re
from dataclasses import dataclass

import pytest

from services.gis_resolution import import_osm
from services.gis_resolution.import_osm import Downloader, FetchFailed, fetch, validate, verify

SNAPSHOT = "2026-10-06T00:00:00Z"


@dataclass
class FakeCity:
    id: str = "testcity"
    name: str = "Test City"
    bbox: tuple = (17.0, 78.0, 17.6, 78.6)


def way(way_id, points, name=None, when="2026-09-01T10:00:00Z"):
    return {
        "type": "way", "id": way_id, "nodes": [way_id * 100 + i for i in range(len(points))],
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in points],
        "tags": {"highway": "secondary", **({"name": name} if name else {})},
        "version": 3, "timestamp": when, "user": "someone", "uid": 7, "changeset": 9,
    }  # fmt: skip


# Way 1 crosses the edge between tiles (0,0) and (0,1); way 2 lies inside tile (2,3).
WAYS = [
    way(1, [(17.05, 78.05), (17.05, 78.15)], "Edge Road"),
    way(2, [(17.25, 78.35), (17.26, 78.36)]),
]


class FakeResponse:
    def __init__(self, status, document=None):
        self.status_code, self._document = status, document

    def json(self):
        return json.loads(json.dumps(self._document))


class FakeServer:
    """Answers like Overpass: ways with a vertex in the box, whole. Can refuse large boxes."""

    def __init__(self, max_span=None, busy_first=0, ways=WAYS):
        self.max_span, self.busy, self.ways, self.urls, self.queries = max_span, busy_first, ways, [], []

    def post(self, url, data, headers, timeout):
        self.urls.append(url)
        query = data["data"]
        self.queries.append(query)
        if self.busy:
            self.busy -= 1
            return FakeResponse(504)
        if "out center meta" in query:  # the named points
            found = [{"type": "node", "id": 5, "lat": 17.1, "lon": 78.1, "tags": {"name": "Test Junction"},
                      "version": 1, "timestamp": "2026-01-01T00:00:00Z"}]  # fmt: skip
        else:
            s, w, n, e = map(float, re.search(r"\(([\d.,]+)\);\s*out", query).group(1).split(","))
            if self.max_span and (n - s) > self.max_span:
                return FakeResponse(504)
            found = [x for x in self.ways if any(s <= p["lat"] <= n and w <= p["lon"] <= e for p in x["geometry"])]
        return FakeResponse(200, {"osm3s": {"timestamp_osm_base": "2026-10-06T14:00:00Z"}, "elements": found})


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(import_osm.time, "sleep", lambda s: None)


def download(tmp_path, server):
    downloader = Downloader(FakeCity(), SNAPSHOT, tmp_path, client=server, pause=0)
    assert downloader.run(passes=3, wait_between_passes=0)
    return downloader


def test_every_query_is_pinned_to_the_snapshot_and_sent_to_overpass_api_de_only(tmp_path):
    server = FakeServer()
    download(tmp_path, server)
    assert set(server.urls) == {"https://overpass-api.de/api/interpreter"}
    assert all(f'[date:"{SNAPSHOT}"]' in q and ("out meta" in q or "out center meta" in q) for q in server.queries)
    assert len(server.queries) == 37  # 36 tiles and the named points


def test_files_and_metadata_carry_the_snapshot_and_personal_metadata_is_dropped(tmp_path):
    downloader = download(tmp_path, FakeServer())
    path = downloader.tile_path(0, 0)
    assert path.name == "roads_0_0@2026-10-06T000000Z.json.gz"
    document = import_osm._read(path)
    assert document["rei"]["snapshot"] == SNAPSHOT
    assert document["rei"]["network_version"] == "OSM snapshot: 2026-10-06T00:00:00Z"
    assert document["rei"]["server"] == "overpass-api.de"
    [element] = document["elements"]
    assert "user" not in element and "uid" not in element and element["version"] == 3


def test_a_complete_download_validates_with_each_way_counted_once(tmp_path):
    download(tmp_path, FakeServer())
    report = validate(FakeCity(), SNAPSHOT, tmp_path)
    assert report["problems"] == [] and report["consistent"]
    assert (report["tiles_present"], report["unique_ways"], report["cross_tile_ways"]) == (36, 2, 1)
    assert report["way_copies_in_tiles"] == 3 and report["segments"] == 2 and report["named_ways"] == 1


def test_a_tile_too_big_for_the_server_is_fetched_in_quarters_that_rejoin(tmp_path):
    server = FakeServer(max_span=0.06)  # tiles are 0.1 degree high; quarters 0.05
    download(tmp_path, server)
    report = validate(FakeCity(), SNAPSHOT, tmp_path)
    assert report["consistent"], report["problems"]
    assert len(report["split_tiles"]) == 36 and set(report["split_tiles"].values()) == {4}
    assert report["unique_ways"] == 2 and report["cross_tile_ways"] == 1


def test_a_failed_tile_is_retried_on_the_same_server_not_replaced(tmp_path):
    server = FakeServer(busy_first=4)
    download(tmp_path, server)
    assert set(server.urls) == {"https://overpass-api.de/api/interpreter"}
    assert validate(FakeCity(), SNAPSHOT, tmp_path)["consistent"]


def test_answers_that_are_partial_or_newer_than_the_snapshot_are_refused():
    base = {"osm3s": {}, "elements": [way(1, [(17.0, 78.0), (17.1, 78.1)])]}
    verify(base, SNAPSHOT)
    with pytest.raises(FetchFailed, match="remark"):
        verify({**base, "remark": "runtime error: Query timed out"}, SNAPSHOT)
    with pytest.raises(FetchFailed, match="after the snapshot"):
        verify({**base, "elements": [way(1, [(17.0, 78.0), (17.1, 78.1)], when="2026-10-06T08:00:00Z")]}, SNAPSHOT)
    unverified = way(1, [(17.0, 78.0), (17.1, 78.1)])
    del unverified["timestamp"]
    with pytest.raises(FetchFailed, match="unverified"):
        verify({**base, "elements": [unverified]}, SNAPSHOT)


def test_a_refused_answer_is_a_failure_after_retries():
    class Partial(FakeServer):
        def post(self, url, data, headers, timeout):
            return FakeResponse(200, {"osm3s": {}, "remark": "runtime error: timed out", "elements": []})

    with pytest.raises(FetchFailed, match="remark"):
        fetch("query", SNAPSHOT, attempts=2, client=Partial())


def test_validation_finds_missing_tiles_mixed_snapshots_and_differing_copies(tmp_path):
    downloader = download(tmp_path, FakeServer())
    # A tile of another snapshot dropped in the folder, a tile missing, a copy changed.
    (tmp_path / "roads_0_0@2026-05-06T000000Z.json.gz").write_bytes(downloader.tile_path(0, 0).read_bytes())
    downloader.tile_path(5, 5).unlink()
    document = import_osm._read(downloader.tile_path(0, 1))
    document["elements"][0]["geometry"][0]["lat"] = 17.051
    import_osm._write(downloader.tile_path(0, 1), document)
    problems = " | ".join(validate(FakeCity(), SNAPSHOT, tmp_path)["problems"])
    assert "another snapshot" in problems and "(5, 5) missing" in problems and "differ between tiles" in problems


def test_the_snapshot_cannot_be_in_the_future():
    with pytest.raises(ValueError):
        import_osm.parse_snapshot("2999-01-01T00:00:00Z")
