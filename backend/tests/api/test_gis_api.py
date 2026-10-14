"""The GIS review endpoints (6 October 2026). Test network: tests/unit/test_gis_resolver.py."""

import pytest

from app.models import Event
from app.services import gis_service
from connectors.official import tfl_source
from connectors.rss.telangana_today import TELANGANA_TODAY
from app.repositories.sources import SourceRepository
from tests.unit.test_gis_resolver import B
from tests.api.test_gis_service import CROSSING_TITLE, LOCALITY, add, resolve


@pytest.fixture
def proposed(client, session):
    SourceRepository(session).sync_registry([TELANGANA_TODAY, tfl_source(scheduled=False)])
    session.commit()
    row = add(session, "EVT-G", CROSSING_TITLE)
    resolve(session, row)
    return row


def test_the_event_carries_its_gis_proposal(client, proposed):
    body = client.get("/api/events/EVT-G").json()
    gis = body["detection"]["gis"]
    assert gis["review_status"] == "PENDING" and gis["applied"]
    assert body["geometry"]["coordinates"] == list(B)


def test_approve_through_the_api(client, proposed, session):
    response = client.post("/api/events/EVT-G/gis/approve", json={"reason": "Checked on the map"})
    assert response.status_code == 200
    assert response.json()["detection"]["gis"]["review_status"] == "APPROVED"


def test_reject_through_the_api_restores_the_location(client, proposed, session):
    response = client.post("/api/events/EVT-G/gis/reject", json={"reason": "Wrong junction"})
    assert response.status_code == 200
    body = response.json()
    assert body["detection"]["gis"]["review_status"] == "REJECTED"
    assert body["geometry"]["coordinates"] == list(LOCALITY)


def test_unknown_events_and_junctions_are_404(client, proposed):
    assert client.post("/api/events/EVT-NONE/gis/approve", json={"reason": "Checked by a reviewer"}).status_code == 404
    assert client.post("/api/junctions/999/confirm", json={"reason": "Checked by a reviewer"}).status_code == 404


def test_a_junction_without_a_position_is_refused_with_409(client, session):
    ref = gis_service.propose_junction(session, city_id="hyderabad", name="Nameless Junction", source="test")
    session.commit()
    response = client.post(f"/api/junctions/{ref.junction_id}/confirm", json={"reason": "Checked by a reviewer"})
    assert response.status_code == 409
    listed = client.get("/api/junctions?city=hyderabad").json()
    assert [(j["canonical_name"], j["status"]) for j in listed] == [("Nameless Junction", "UNCONFIRMED")]


def test_resolve_needs_the_road_network_database(client, proposed):
    # The test app has no GIS_DATABASE_URL: the endpoint says so instead of guessing.
    assert client.post("/api/events/EVT-G/gis/resolve").status_code == 503


def test_resolve_refuses_a_city_without_a_road_network(client, session):
    SourceRepository(session).sync_registry([tfl_source(scheduled=False)])
    session.commit()
    add(session, "EVT-L", CROSSING_TITLE, city="London", method="source_provided", source=tfl_source(scheduled=False))
    assert client.post("/api/events/EVT-L/gis/resolve").status_code == 409
    assert session.get(Event, "EVT-L").detection.get("gis") is None
