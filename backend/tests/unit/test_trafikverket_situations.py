"""Trafikverket road traffic situations, Sweden (decision 0053).

The fixture is a real excerpt of the answer of 4 November 2026 (seven
situations, Trafikverket's own JSON, without the SWEREF 99 TM copies the query
leaves out). No network: the API is driven through httpx.MockTransport.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from connectors.base import ConnectorError
from connectors.official import trafikverket as tv
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.event_schema import EventType
from packages.source_models import IntegrationStatus

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "trafikverket_situations_2026-11-04.json"
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
KEY = "test-key-not-real"


def answer() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def situations() -> list[dict]:
    return answer()["RESPONSE"]["RESULT"][0]["Situation"]


def records() -> dict[str, object]:
    items = tv.situation_items(situations())
    return {item["id"][-8:]: tv.to_record(item, NOW) for item in items}


def connector(handler) -> tv.TrafikverketSituationsConnector:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return tv.TrafikverketSituationsConnector(
        tv.trafikverket_source(scheduled=False), "test-agent", api_key=KEY, client=client, clock=lambda: NOW
    )


def test_one_event_per_situation_from_trafikverkets_own_datex_terms():
    works = records()["ef2dd011"]
    assert works.structured.event_type == EventType.ROAD_WORKS.value
    assert works.title == "Road works – Väg 50 vid Åsbro, i båda riktningar. (Trafikverket)"
    assert works.categories == [
        "MaintenanceWorks / roadworks",
        "RoadOrCarriagewayOrLaneManagement / laneClosures",
        "SpeedManagement / speedRestrictionInOperation",
    ]
    assert works.structured.geometry["type"] == "MultiLineString"
    # Swedish words are kept as written, never translated.
    assert works.summary == "Tillfälliga cirkulationsplatser."
    assert works.structured.severity == "Liten påverkan"
    parts = works.raw["item"]["records"]
    assert {part["message_code"] for part in parts} >= {"Vägarbete", "Körfältsavstängningar"}


def test_a_municipal_closure_during_works_is_planned_and_credits_the_municipality():
    closure = records()["4dd667a2"]
    assert closure.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert closure.title.startswith("Road closed – Bussens Väg i Stockholms stad")
    assert closure.title.endswith("(Stockholms Stad)")


def test_ferry_notices_are_not_road_events():
    assert records()["c5b04b61ce19"[-8:]] is None


def test_until_further_notice_has_no_end():
    frost = records()["b4a6fe0a"]
    assert frost.structured.event_type == EventType.ROAD_HAZARD.value
    assert frost.structured.start == datetime.fromisoformat("2026-08-21T06:00:00+02:00")
    assert frost.structured.end is None
    assert frost.raw["item"]["records"][0]["until_further_notice"] is True


def test_suspended_parts_are_left_out():
    by_id = {item["id"][-8:]: item for item in tv.situation_items(situations())}
    partly = next(s for s in situations() if s["Id"].endswith("227b0094"))
    assert sum(1 for d in partly["Deviation"] if d.get("Suspended")) == 2
    assert len(by_id["227b0094"]["records"]) == 3
    every_part_suspended = {**partly, "Deviation": [d for d in partly["Deviation"] if d.get("Suspended")]}
    assert tv.situation_items([every_part_suspended]) == []


def test_a_road_already_in_a_fuller_location_is_not_repeated():
    assert records()["3ee2d81e"].title == (
        "Road works – Väg 667 från Näset till Trafikplats Enånger (211) båda riktningarna i "
        "Gävleborgs län (X) (Trafikverket)"
    )
    # "E45" is in "E 45 mellan Svenstavik och Brunflo": one road.
    assert " / E45" not in records()["227b0094"].title


def test_contact_lines_are_removed():
    text = "Vägarbete pågår.\nKontaktperson: Anna, tel. 070-123 45 67\nInfo: projekt@example.se"
    assert tv.without_contact_details(text) == "Vägarbete pågår.\n[contact details removed by REI]"
    # Dates and hours are not phone numbers.
    assert tv.without_contact_details("Mellan 2026-11-04 07:00 och 16:00") == "Mellan 2026-11-04 07:00 och 16:00"


def test_the_query_asks_for_parts_in_force_and_sends_the_key_only_in_the_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode("utf-8")
        seen["url"] = str(request.url)
        return httpx.Response(200, json=answer())

    fetched = connector(handler).fetch()
    assert f'authenticationkey="{KEY}"' in seen["body"]
    assert KEY not in seen["url"]
    assert '<NE name="Deviation.Suspended" value="true" />' in seen["body"]
    assert "<EXCLUDE>Deviation.Geometry.Line.SWEREF99TM</EXCLUDE>" in seen["body"]
    # Six of seven situations are road events; all are in force or upcoming on 4 November.
    assert len(fetched) == 6
    assert all(record.structured.geometry and record.structured.start for record in fetched)


def test_a_refused_key_is_an_error_that_does_not_show_the_key():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401, json={"RESPONSE": {"RESULT": [{"ERROR": {"SOURCE": "Security", "MESSAGE": "Invalid authentication"}}]}}
        )

    with pytest.raises(ConnectorError) as error:
        connector(handler).fetch()
    assert "refused the key" in str(error.value) and "Invalid authentication" in str(error.value)
    assert KEY not in str(error.value)


def test_without_a_key_the_source_is_listed_as_needing_access_and_never_fetched():
    without = {s.definition.source_id: s for s in registered_sources()}[tv.SOURCE_ID]
    assert without.definition.integration_status is IntegrationStatus.REQUIRES_ACCESS
    assert not without.definition.active and without.create_connector is None
    assert tv.SOURCE_ID in OFFICIAL_SOURCE_IDS

    with_key = {
        s.definition.source_id: s
        for s in registered_sources(official_feeds_scheduled_sources=[tv.SOURCE_ID], trafikverket_api_key=KEY)
    }[tv.SOURCE_ID]
    assert with_key.definition.integration_status is IntegrationStatus.CONNECTED
    assert with_key.definition.active
    assert isinstance(with_key.create_connector("agent"), tv.TrafikverketSituationsConnector)
