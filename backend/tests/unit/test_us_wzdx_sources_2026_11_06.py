"""US WZDx feeds of 6 November 2026 (decision 0060): Washington State DOT connected,
the registry's other 13 new feeds recorded and not connected.

The fixture is 5 real work zones from WSDOT's feed of 6 November 2026 (a trimmed
sample, its feed_info kept). No test reaches any service.
"""

from datetime import datetime, timezone
from pathlib import Path

import httpx

from connectors.discovered_2026_11_06 import DISCOVERED_2026_11_06
from connectors.official.wzdx import FEEDS, connector_for, wzdx_source
from connectors.registry import OFFICIAL_SOURCE_IDS, registered_sources
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import IntegrationStatus

FIXTURES = Path(__file__).parents[1] / "fixtures"
WSDOT = {feed.key: feed for feed in FEEDS}["wsdot"]
# Shortly after the sample was fetched.
NOW = datetime(2026, 11, 6, 8, 30, tzinfo=timezone.utc)


def fetch(now: datetime = NOW):
    body = (FIXTURES / "wzdx_wsdot_sample_2026-11-06.geojson").read_text(encoding="utf-8")
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)))
    connector = connector_for(WSDOT)(wzdx_source(WSDOT, scheduled=True), "ua", client=client, clock=lambda: now)
    return connector.fetch(), connector


def test_washington_is_an_official_us_feed_with_its_own_time_zone():
    assert "wzdx-wsdot" in OFFICIAL_SOURCE_IDS
    united_states = get_city("united-states")
    assert "wzdx-wsdot" in united_states.official_sources
    assert united_states.source_time_zones["wzdx-wsdot"] == "America/Los_Angeles"
    definition = wzdx_source(WSDOT, scheduled=False)
    assert (definition.region, definition.endpoint) == ("Washington", "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed")
    assert definition.licence.startswith("CC0 1.0")


def test_washington_work_zones_keep_their_lines_dates_and_words():
    found, connector = fetch()
    # Five listed; the 2028 bridge painting starts more than a year ahead, so this run leaves it.
    assert len(connector.observed_ids) == 5
    assert {r.external_id for r in found} == {"40804-N", "40630-S", "14637-N", "9281-E"}
    assert all(r.structured.geometry["type"] == "LineString" and r.structured.start and r.structured.end for r in found)
    assert all(r.structured.event_type == EventType.ROAD_WORKS.value for r in found)  # impact "unknown"
    widening = next(r for r in found if r.external_id == "40804-N")
    assert widening.title == "Road works: 531 northbound (Washington)"
    assert widening.summary.startswith("SR 531/43rd Ave NE to 67th Ave. NE - Widening")
    assert widening.structured.start == datetime(2025, 5, 15, tzinfo=timezone.utc)
    assert widening.structured.end == datetime(2026, 12, 15, tzinfo=timezone.utc)
    assert widening.structured.direction == "NORTHBOUND"
    assert "start 2025-05-15T00:00:00+00:00 (verified)" in widening.structured.stated_period
    assert widening.raw["item"]["id"] == "40804-N"  # the feature itself is the evidence


def test_an_upcoming_washington_closure_is_kept_before_it_starts():
    found, _ = fetch()
    interchange = next(r for r in found if r.external_id == "9281-E")
    assert interchange.structured.start == datetime(2026, 11, 9, tzinfo=timezone.utc) > NOW
    assert interchange.structured.direction == "EASTBOUND"


def test_the_other_new_registry_feeds_are_recorded_but_never_fetched():
    registry = {s.definition.source_id: s for s in registered_sources()}
    assert len(DISCOVERED_2026_11_06) == 13
    for definition in DISCOVERED_2026_11_06:
        source = registry[definition.source_id]
        assert source.create_connector is None, definition.source_id
        assert definition.active is False, definition.source_id
        assert definition.integration_status is not IntegrationStatus.CONNECTED, definition.source_id
        assert definition.source_id not in OFFICIAL_SOURCE_IDS, definition.source_id
        assert definition.notes and "6 November 2026" in definition.notes, definition.source_id
        # Registry URLs with an access key are kept without it.
        assert not any(key in definition.endpoint for key in ("access_token", "app_key", "?")), definition.source_id


def test_each_reason_is_the_one_found():
    by_id = {d.source_id: d for d in DISCOVERED_2026_11_06}
    refused = {"us-ok-odot-wzdx", "us-ut-udot-wzdx", "us-ia-iowadot-wzdx", "us-wi-wisdot-wzdx"}
    assert all("HTTP 403" in by_id[s].notes and by_id[s].integration_status is IntegrationStatus.BLOCKED for s in refused)
    silent = {"us-id-itd-wzdx", "us-fl-fdot-wzdx", "us-nec-wzdx"}
    assert all(by_id[s].integration_status is IntegrationStatus.TERMS_REVIEW_REQUIRED for s in silent)
    assert all("awaiting" in by_id[s].notes for s in silent)
    assert "Disallow: /" in by_id["us-ms-mdot-wzdx"].notes
    assert by_id["us-hi-hidot-wzdx"].integration_status is IntegrationStatus.NOT_USABLE
    assert "ends exactly 7 days later" in by_id["us-hi-hidot-wzdx"].notes
