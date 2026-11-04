"""TomTom live incidents for the map (decision 0054): passed through, never stored.

No network: TomTom is driven through httpx.MockTransport with answers in the
shape of its Incident Details v5 and Copyright caption APIs (4 November 2026).
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import Event, SourceArtifact
from app.services.tomtom_live import (
    LiveFailed,
    LiveRefused,
    LiveUnavailable,
    TomTomLive,
    area_km2,
    parse_bbox,
)

WARSAW = "20.95,52.18,21.10,52.27"  # about 100 km²
KEY = "test-key-not-real"
INCIDENTS = {
    "incidents": [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[21.0, 52.2], [21.01, 52.21]]},
            "properties": {
                "id": "a1", "iconCategory": 8, "magnitudeOfDelay": 4,
                "events": [{"description": "Closed", "code": 401, "iconCategory": 8}],
                "startTime": "2026-11-03T12:44:15Z", "endTime": None,
                "from": "Literacka", "to": "Literacka", "roadNumbers": [],
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [21.02, 52.22]},
            "properties": {
                "id": "a2", "iconCategory": 9, "magnitudeOfDelay": 1,
                "events": [{"description": "Roadworks", "code": 701, "iconCategory": 9}],
                "startTime": "2026-11-01T06:00:00Z", "endTime": "2026-11-30T16:00:00Z",
                "from": "Marszałkowska", "to": "Świętokrzyska", "roadNumbers": ["7"],
            },
        },
        # A jam: not a road event, never shown even if TomTom sends one.
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[21.0, 52.2], [21.0, 52.25]]},
            "properties": {"id": "a3", "iconCategory": 6, "magnitudeOfDelay": 2, "events": [{"description": "Queuing traffic"}]},
        },
    ]
}


def tomtom(seen: list[httpx.Request], *, status: int = 200, cache_control: str = "no-store"):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/caption.json"):
            return httpx.Response(200, json={"formatVersion": "0.0.1", "copyrightsCaption": "© TomTom"})
        if status != 200:
            return httpx.Response(status, json={"detailedError": {"message": "nope"}})
        return httpx.Response(200, json=INCIDENTS, headers={"Cache-Control": cache_control})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_only_road_events_are_asked_for_and_passed_through_as_geojson():
    seen: list[httpx.Request] = []
    answer = TomTomLive(KEY, 100, client=tomtom(seen)).incidents(WARSAW)
    request = seen[0]
    assert request.url.params["categoryFilter"] == "1,3,7,8,9,11,14"
    assert request.url.params["timeValidityFilter"] == "present,future"
    assert request.url.params["key"] == KEY
    features = answer.collection["features"]
    assert [f["properties"]["label"] for f in features] == ["Road closed", "Road works"]
    assert features[1]["properties"]["from"] == "Marszałkowska" and features[1]["properties"]["roads"] == ["7"]
    assert answer.collection["attribution"] == "© TomTom"
    assert answer.cache_control == "no-store"


def test_an_area_too_large_or_malformed_is_refused_without_asking_tomtom():
    seen: list[httpx.Request] = []
    live = TomTomLive(KEY, 100, client=tomtom(seen))
    with pytest.raises(LiveRefused) as too_big:
        live.incidents("14.0,49.0,24.2,54.9")  # all of Poland
    assert too_big.value.status == 400 and "Zoom in" in str(too_big.value)
    with pytest.raises(LiveRefused):
        live.incidents("not,a,box")
    assert seen == []
    assert 90 < area_km2(parse_bbox(WARSAW)) < 120


def test_without_a_key_the_layer_is_unavailable():
    live = TomTomLive(None, 100)
    assert live.status()["configured"] is False
    with pytest.raises(LiveUnavailable):
        live.incidents(WARSAW)


def test_the_daily_allowance_is_kept():
    live = TomTomLive(KEY, 4, client=tomtom([]))
    live.incidents(WARSAW)
    live.incidents(WARSAW)  # two TomTom requests each: incidents and caption
    with pytest.raises(LiveRefused) as used_up:
        live.incidents(WARSAW)
    assert used_up.value.status == 429
    assert live.status()["requests_today"] == 4


def test_a_refused_key_is_a_failure_that_does_not_show_the_key():
    with pytest.raises(LiveFailed) as refused:
        TomTomLive(KEY, 100, client=tomtom([], status=403)).incidents(WARSAW)
    assert "refused the key" in str(refused.value) and KEY not in str(refused.value)


def test_the_route_needs_a_session_passes_tomtoms_cache_header_and_stores_nothing(app, client):
    app.state.tomtom_live = TomTomLive(KEY, 100, client=tomtom([], cache_control="max-age=30"))
    with app.state.session_factory() as session:
        before = (session.scalar(select(func.count()).select_from(Event)),
                  session.scalar(select(func.count()).select_from(SourceArtifact)))

    response = client.get("/api/live/tomtom-incidents", params={"bbox": WARSAW})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "max-age=30"
    assert len(response.json()["features"]) == 2
    assert client.get("/api/live/tomtom-incidents/status").json()["configured"] is True
    assert client.get("/api/live/tomtom-incidents", params={"bbox": "14,49,24,55"}).status_code == 400

    with app.state.session_factory() as session:
        after = (session.scalar(select(func.count()).select_from(Event)),
                 session.scalar(select(func.count()).select_from(SourceArtifact)))
    assert after == before

    with TestClient(app) as anonymous:
        assert anonymous.get("/api/live/tomtom-incidents", params={"bbox": WARSAW}).status_code == 401


def test_without_a_key_the_route_says_so(app, client):
    app.state.tomtom_live = TomTomLive(None, 100)
    response = client.get("/api/live/tomtom-incidents", params={"bbox": WARSAW})
    assert response.status_code == 503 and "not configured" in response.json()["detail"]
