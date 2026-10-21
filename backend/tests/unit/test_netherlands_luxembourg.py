"""NDW (Netherlands) and CITA (Luxembourg) DATEX II v3 feeds (21 October 2026), on
real samples saved that day. No test reaches either service.

The fixtures are trimmed copies of the feeds (the envelope kept, a few dozen
situations chosen by kind). In the NDW planned-feed sample, the comment lines
that named a contact person (name, phone number, e-mail address) were replaced
by one fictitious line ("A. Voorbeeld ... a.voorbeeld@example.org"), and one
person's name and one house number were taken out, so that no one's personal
details are kept in the repository; the connector must remove such lines.
"""

import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import cita, datex3_nl_lu as datex, ndw
from packages.cities import get_city, load_cities
from packages.event_schema import EventDirection, EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURES = Path(__file__).parents[1] / "fixtures"
CURRENT = (FIXTURES / "ndw_actueel_beeld_2026-10-21.xml").read_bytes()
PLANNED = (FIXTURES / "ndw_planningsfeed_2026-10-21.xml").read_bytes()
CITA = (FIXTURES / "cita_situationrecord36_2026-10-21.xml").read_bytes()
NOW = datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc)
UTC = timezone.utc


def client(body: bytes, status: int = 200) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, content=body)))


def current_connector(**options):
    # NDW serves its files gzipped, as application/xml without a content encoding.
    return ndw.NdwCurrentSituationsConnector(
        ndw.ndw_current_source(scheduled=False), "ua", client=client(gzip.compress(CURRENT)), clock=lambda: NOW, **options
    )


def planned_connector():
    return ndw.NdwPlannedWorksConnector(
        ndw.ndw_planned_source(scheduled=False), "ua", client=client(gzip.compress(PLANNED)), clock=lambda: NOW
    )


def cita_connector():
    return cita.CitaTrafficEventsConnector(cita.cita_source(scheduled=False), "ua", client=client(CITA), clock=lambda: NOW)


def by_id(records):
    return {record.external_id: record for record in records}


# --- definitions and country entries -------------------------------------------------------

DEFINITIONS = (
    (ndw.ndw_current_source, "nl-ndw-actueel-beeld", "netherlands", "NL"),
    (ndw.ndw_planned_source, "nl-ndw-planningsfeed-wegwerkzaamheden", "netherlands", "NL"),
    (cita.cita_source, "lu-cita-datex2-v36", "luxembourg", "LU"),
)


@pytest.mark.parametrize("make, source_id, city, country", DEFINITIONS)
def test_each_feed_is_a_connected_tier_one_open_data_source_run_by_hand(make, source_id, city, country):
    definition = make(scheduled=False)
    assert (definition.source_id, definition.city, definition.country) == (source_id, city, country)
    assert definition.source_tier == 1 and definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and make(scheduled=True).active is True
    # CC0: commercial reuse permitted, no attribution required (a courtesy credit is given).
    assert "CC0" in definition.licence and definition.attribution
    # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert definition.provides_geometry and not definition.discovery_only
    # PostgreSQL enforces the sources table's column limits (SQLite does not).
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = definition.model_dump(mode="json")
    assert not {name for name, limit in limits.items() if values.get(name) and len(str(values[name])) > limit}


def test_the_netherlands_and_luxembourg_are_country_entries_listing_their_feeds():
    cities = load_cities()
    netherlands, luxembourg = cities["netherlands"], cities["luxembourg"]
    assert (netherlands.level, netherlands.country, netherlands.timezone) == ("country", "NL", "Europe/Amsterdam")
    assert (luxembourg.level, luxembourg.country, luxembourg.timezone) == ("country", "LU", "Europe/Luxembourg")
    assert netherlands.official_sources == ("nl-ndw-actueel-beeld", "nl-ndw-planningsfeed-wegwerkzaamheden")
    assert luxembourg.official_sources == ("lu-cita-datex2-v36",)
    assert netherlands.covers(52.37, 4.90) and netherlands.covers(53.45, 6.84)  # Amsterdam, Delfzijl
    assert luxembourg.covers(49.61, 6.13) and not luxembourg.covers(50.85, 4.35)  # Luxembourg City, not Brussels


# --- contact details ---------------------------------------------------------------------


def test_lines_naming_a_contact_are_removed_and_project_codes_kept():
    text = "\n".join(
        [
            "Weg dicht in beide richtingen",
            "Contactinformatie: A. Voorbeeld, Voorbeeld BV",
            "Bel 06 12345678 bij vragen",
            "Of 010-1234567, of +31 20 123 4567",
            "mail a.voorbeeld@example.org",
            "Kabels / Leidingen PR02126000612 A0526000-0171 (634124) 26-1853, vanaf 2026-10-26",
        ]
    )
    cleaned = datex.without_contact_details(text)
    assert cleaned.splitlines() == [
        "Weg dicht in beide richtingen",
        datex.REMOVED,
        "Kabels / Leidingen PR02126000612 A0526000-0171 (634124) 26-1853, vanaf 2026-10-26",
    ]


def test_no_contact_detail_reaches_the_evidence_or_the_event():
    records = planned_connector().fetch()
    stored = json.dumps([record.raw for record in records], ensure_ascii=False)
    texts = " ".join(f"{record.title} {record.summary or ''}" for record in records)
    assert "a.voorbeeld@example.org" in PLANNED.decode("utf-8")  # the sample has the line
    for detail in ("Voorbeeld", "example.org", "06 12345678"):
        assert detail not in stored and detail not in texts
    assert datex.REMOVED in stored and datex.REMOVED not in texts


# --- NDW current picture -------------------------------------------------------------------


def test_the_current_picture_leaves_out_planned_works_now_in_force():
    connector = current_connector()
    records = by_id(connector.fetch())
    # Three NDW18 measures (made from NDW03 planned records) and two RWS01 *_WWA
    # situations name their planned-feed record: the planned-feed source lists them.
    assert connector.counts == {
        "situations": 26, "not_real": 0, "skipped": 5, "not_road_events": 4, "outside_window": 0,
    }  # fmt: skip
    assert not any(external_id.startswith("NDW18_") or external_id.endswith("_WWA") for external_id in records)
    assert connector.observed_ids == set(records)
    everything = current_connector(include_planned_measures=True)
    # Asked for, they are kept, except one measure whose stated end has passed.
    assert len(everything.fetch()) == len(records) + 4
    assert everything.counts["skipped"] == 0 and everything.counts["outside_window"] == 1


def test_traffic_flow_and_rush_hour_lanes_are_not_road_events():
    records = by_id(current_connector().fetch())
    assert "RWS10_OBS0000000385" not in records  # hardShoulderRunningInOperation: a lane opened
    assert "NLRWS_0005495719" not in records  # AbnormalTraffic (slow traffic)


def test_current_records_keep_the_sources_type_point_and_utc_times():
    records = by_id(current_connector().fetch())
    obstruction = records["NDW06_944faf60-fa19-4afa-9f35-96ec5e29c773"]
    # <loc:latitude>51.40341</loc:latitude><loc:longitude>5.815823</loc:longitude>
    assert obstruction.structured.geometry == {"type": "Point", "coordinates": [5.815823, 51.40341]}
    assert obstruction.structured.start == datetime(2026, 10, 21, 10, 24, 32, 204922, tzinfo=UTC)
    assert obstruction.structured.end is None  # the source states no end; none is invented
    assert obstruction.structured.event_type == EventType.ROAD_HAZARD.value
    assert records["NDW06_ce04f4de-be16-4099-b5f1-fa75f5d0c42b"].structured.event_type == EventType.ACCIDENT.value
    bridge = records["MOS01_NLSAP000130333200154_692482921"]
    assert bridge.structured.event_type == EventType.BRIDGE_TUNNEL_RESTRICTION.value
    assert bridge.title == "Bridge swing in operation (MOS01)"


def test_a_closure_whose_cause_is_not_stated_gets_no_type_invented():
    record = by_id(current_connector().fetch())["NLRWS_0005495730"]
    # A carriageway closed for a broken-down lorry ("Defecte vrachtwagen"), with no
    # works, event or incident record: neither "planned" nor "emergency" is claimed.
    assert record.structured.event_type is None
    assert record.title == "Carriageway closed (NLRWS)" and record.summary == "Defecte vrachtwagen"
    assert record.structured.category == "RoadOrCarriagewayOrLaneManagement / carriagewayClosures"


# --- NDW planned feed ----------------------------------------------------------------------


def test_one_record_per_planned_situation_in_the_run_window():
    connector = planned_connector()
    records = by_id(connector.fetch())
    assert connector.counts["situations"] == 23 and len(records) == 21
    # Ended on 19 October, and a parade more than a year ahead: observed, not kept.
    assert {"NDW03_622987", "AND01_D17D8F381B044CAB9500B25E5FB5C593"} <= connector.observed_ids - set(records)
    assert all(record.structured.start for record in records.values())
    # Only one situation states no end (works in progress on a Rijkswaterstaat road).
    assert [key for key, record in records.items() if record.structured.end is None] == ["RWS01_SM1172662_D2"]
    assert all(record.structured.geometry for record in records.values())


def test_a_situations_records_become_one_event_led_by_its_closure():
    record = by_id(planned_connector().fetch())["NDW03_631380"]
    assert record.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value
    assert record.title == "Carriageway closed – Denenweg (Gemeente Horst aan de Maas)"
    assert record.structured.category == (
        "RoadOrCarriagewayOrLaneManagement / carriagewayClosures; MaintenanceWorks / maintenanceWork; "
        "ReroutingManagement / useIntersectionOrJunction"
    )
    assert record.structured.start == datetime(2026, 10, 12, 5, 0, tzinfo=UTC)
    assert record.structured.end == datetime(2026, 11, 6, 15, 0, tzinfo=UTC)
    # "Weg dicht in beide richtingen": the source says both directions.
    assert record.structured.direction == EventDirection.BOTH_DIRECTIONS.value
    assert record.structured.affected_road == "Denenweg"
    # Works, the closure in each direction (AB, BA: the same line reversed), a diversion.
    assert [r["type"] for r in record.raw["item"]["records"]] == [
        "MaintenanceWorks", "RoadOrCarriagewayOrLaneManagement", "RoadOrCarriagewayOrLaneManagement",
        "ReroutingManagement",
    ]  # fmt: skip
    assert record.structured.geometry["type"] == "LineString"


def test_lines_are_read_latitude_first_and_a_line_drawn_both_ways_is_kept_once():
    record = by_id(planned_connector().fetch())["NDW03_625751"]
    lines = [line["posList"] for r in record.raw["item"]["records"] for line in r.get("lines", [])]
    assert len(lines) == 2 and lines[0].startswith("51.507371 4.860907")
    # The AB and BA records draw the same positions in reverse order: one line.
    assert record.structured.geometry["type"] == "LineString"
    assert record.structured.geometry["coordinates"][0] == [4.860907, 51.507371]
    for item in planned_connector().fetch():
        geometry = item.structured.geometry
        if geometry["type"] == "MultiLineString":
            shapes = [tuple(map(tuple, line)) for line in geometry["coordinates"]]
            assert len(set(shapes) | {shape[::-1] for shape in shapes}) == 2 * len(shapes)


def test_public_events_and_the_periods_the_source_states():
    records = by_id(planned_connector().fetch())
    marathon = records["NDW03_633898"]
    assert marathon.structured.event_type == EventType.PLANNED_ROAD_CLOSURE.value  # the closure leads
    assert "PublicEvent / marathon" in marathon.structured.category
    market = records["AND01_18CA6DD91E5A45A080C77F107CA89332"]
    assert market.structured.event_type == EventType.SPECIAL_EVENT.value
    assert market.title == "Public event (market) – Markt. (Gemeente Breda)"
    assert market.structured.stated_period.startswith(
        "104 periods stated (UTC): 2026-10-23 04:00–12:00; 2026-10-30 05:00–13:00;"
    )
    assert (market.structured.start, market.structured.end) == (
        datetime(2026, 10, 23, 4, 0, tzinfo=UTC), datetime(2028, 10, 13, 12, 0, tzinfo=UTC),
    )  # fmt: skip
    diversion = records["NDW03_622173"]
    assert diversion.structured.event_type == EventType.TRAFFIC_DIVERSION.value
    assert diversion.structured.geometry["type"] == "Point"


def test_a_revision_is_a_change_of_content_not_of_bookkeeping():
    record = by_id(planned_connector().fetch())["NDW03_631380"]
    item = record.raw["item"]
    touched = {**item, "version_time": "2026-10-21T12:00:00Z", "record_versions": {"x": "9"}}
    assert datex.revision_key({"item": touched}) == datex.revision_key(record.raw)
    edited = json.loads(json.dumps(item))
    edited["records"][0]["end"] = "2026-11-13T15:00:00Z"
    assert datex.revision_key({"item": edited}) != datex.revision_key(record.raw)


# --- CITA, Luxembourg ----------------------------------------------------------------------


def test_cita_events_keep_their_road_directions_and_stated_start():
    connector = cita_connector()
    records = by_id(connector.fetch())
    assert len(records) == 15 and connector.observed_ids == set(records)
    assert {record.structured.event_type for record in records.values()} == {
        EventType.ROAD_WORKS.value, EventType.ROAD_HAZARD.value,
    }  # fmt: skip
    # The publisher states no end: every event stays without one.
    assert all(record.structured.start and record.structured.end is None for record in records.values())
    works = records["232972"]
    assert works.title == "Road works – A1 (Autoroute de Tréves, vers Trier / Autoroute de Tréves, vers Gasperich) (CITA)"
    assert works.structured.geometry["type"] == "MultiLineString" and len(works.structured.geometry["coordinates"]) == 2
    assert works.structured.affected_road == "A1" and works.structured.stated_distance == "11.0 m; 10.0 m"
    assert works.summary == "2 Pisten ageengt"
    obstruction = records["237970"]
    # 2026-10-21T12:36:08+02:00 as written.
    assert obstruction.structured.start == datetime(2026, 10, 21, 10, 36, 8, tzinfo=UTC)
    assert obstruction.structured.geometry["coordinates"][0] == [5.959474, 49.529923]
    assert obstruction.structured.stated_distance_m == 100.0
    fault = records["237865"]
    assert fault.structured.event_type == EventType.ROAD_HAZARD.value
    assert fault.title.startswith("Equipment or system fault (not working) – A13 (Tunnel Markusberg")


# --- fetching ------------------------------------------------------------------------------


def test_a_refusal_or_unreadable_file_is_a_connector_error():
    refused = cita.CitaTrafficEventsConnector(cita.cita_source(scheduled=False), "ua", client=client(b"", 503))
    with pytest.raises(ConnectorError, match="refused"):
        refused.fetch()
    broken = cita.CitaTrafficEventsConnector(cita.cita_source(scheduled=False), "ua", client=client(CITA[:5000]))
    with pytest.raises(ConnectorError, match="DATEX II"):
        broken.fetch()


def test_the_run_window_is_the_shared_one():
    assert datex.in_run_window(NOW - timedelta(days=30), None, NOW)
    assert not datex.in_run_window(NOW - timedelta(days=30), NOW - timedelta(seconds=1), NOW)
    assert not datex.in_run_window(NOW + timedelta(days=366), None, NOW)


# --- through the pipeline ------------------------------------------------------------------


@pytest.mark.parametrize(
    "make_connector, city_id, name",
    [(current_connector, "netherlands", "Netherlands"), (planned_connector, "netherlands", "Netherlands"), (cita_connector, "luxembourg", "Luxembourg")],
)
def test_events_through_the_pipeline_fit_the_columns(session, make_connector, city_id, name):
    connector = make_connector()
    SourceRepository(session).sync_registry([connector.source])
    session.commit()
    city = get_city(city_id)
    result = run_ingestion(connector, KeywordClassifier.from_file(), SqlIngestionStore(session), None, city)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == connector.source.source_id)))
    assert result.events_created == len(events) == result.fetched > 0
    assert all(event.geometry and event.start_time and event.city == name for event in events)
    too_long = []
    for model in (Event, SourceArtifact):
        limits = {
            column.name: column.type.length
            for column in model.__table__.columns
            if isinstance(column.type, String) and column.type.length
        }
        for row in session.scalars(select(model).where(model.source_id == connector.source.source_id)):
            too_long += [
                (model.__tablename__, column, len(str(getattr(row, column))))
                for column, limit in limits.items()
                if getattr(row, column) is not None and len(str(getattr(row, column))) > limit
            ]
    assert not too_long
