"""French feeds of 5 November 2026: the Département des Côtes d'Armor's traffic
orders for works on its roads (Data Fair) and Brest métropole's temporary
traffic orders (ArcGIS).

The fixtures are real items each feed returned on 5 November 2026 (a trimmed
sample, in the feed's own order), fetched with the connectors' own queries;
Brest's applicant and the firm allowed to park hold placeholders. Events are
built only from what each source states, at the source's own geometry; every
event still needs validation. No test reaches any service.
"""

import copy
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import brest_traffic_orders as brest
from connectors.official import cotes_darmor_works_orders as cd22
from packages.cities import get_city
from packages.event_schema import EventType, LocationClass
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.extraction import KeywordClassifier, build_event_from_source, classify_source_record
from services.ingestion import run_ingestion
from tests.support import FakeConnector

FIXTURES = Path(__file__).parents[1] / "fixtures"
PARIS = ZoneInfo("Europe/Paris")
FRANCE = get_city("france")
FEEDS = {
    cd22.SOURCE_ID: (cd22, cd22.cotes_darmor_source, cd22.CotesDarmorWorksOrdersConnector),
    brest.SOURCE_ID: (brest, brest.brest_source, brest.BrestTrafficOrdersConnector),
}
PLANTED = "A Person, a.person@example.org, 06 00 00 00 00 (test value)"


def fixture(source_id):
    body = json.loads((FIXTURES / f"{source_id.replace('-', '_')}_2026-11-05.json").read_text(encoding="utf-8"))
    return datetime.fromisoformat(body["fetched_at"]), body


def items(source_id):
    """What the connector's fetch hands to to_record: one line per dossier for Côtes d'Armor
    (ended or not), the areas grouped by order for Brest."""
    _, body = fixture(source_id)
    if source_id == cd22.SOURCE_ID:
        return cd22.orders(body["items"], date.min)
    return brest.orders(body["items"])


def records(source_id):
    now, _ = fixture(source_id)
    module = FEEDS[source_id][0]
    return now, [(item, record) for item in items(source_id) if (record := module.to_record(item, now))]


def by_id(source_id):
    return {record.external_id: (item, record) for item, record in records(source_id)[1]}


# --- the definitions ------------------------------------------------------------------


SOURCE_LIMITS = {
    column.name: column.type.length
    for column in Source.__table__.columns
    if isinstance(column.type, String) and column.type.length
}


@pytest.mark.parametrize("source_id", FEEDS)
def test_each_feed_is_a_connected_tier_one_open_data_source_run_by_hand(source_id):
    make = FEEDS[source_id][1]
    definition = make(scheduled=False)
    assert definition.source_id == source_id
    assert definition.integration_status is IntegrationStatus.CONNECTED
    assert definition.active is False and make(scheduled=True).active is True
    assert definition.source_tier == 1 and definition.discovery_only is False
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert definition.city == "france" and definition.country == "FR"
    assert definition.region.startswith("Bretagne") and definition.language == "fr"
    assert definition.polling_frequency_minutes == 720
    assert definition.provides_geometry is True
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert "Licence Ouverte" in definition.licence and "Licence Ouverte" in definition.attribution
    # Never recorded as settled: no legal review (decision 0009).
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.evidence_retention and "5 November 2026" in definition.notes
    values = definition.model_dump(mode="json")
    too_long = {
        name: len(str(values[name]))
        for name, limit in SOURCE_LIMITS.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert not too_long and len(definition.parser_type) <= 32 and len(source_id) <= 64


# --- both feeds -------------------------------------------------------------------------


@pytest.mark.parametrize("source_id", FEEDS)
def test_every_event_is_located_by_the_source_in_france_and_needs_validation(source_id):
    now, found = records(source_id)
    assert found
    for _, record in found:
        assert record.source_id == source_id
        assert record.structured.attribution and record.structured.covers_city is True
        for moment in (record.structured.start, record.structured.end):
            assert moment.tzinfo == PARIS
        assert (record.structured.start.hour, record.structured.start.minute) == (0, 0)
        assert (record.structured.end.hour, record.structured.end.minute) == (23, 59)
        event = build_event_from_source(record, classify_source_record(record, FRANCE), now=now)
        assert event is not None and event.city == FRANCE.name
        assert event.status.value == "VALIDATION_REQUIRED"
        assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
        assert event.severity is None


@pytest.mark.parametrize("source_id", FEEDS)
def test_external_ids_are_the_order_numbers_unique_and_stable(source_id):
    now, found = records(source_id)
    ids = [record.external_id for _, record in found]
    assert len(ids) == len(set(ids))
    module = FEEDS[source_id][0]
    later = now + timedelta(hours=6)
    assert [module.to_record(copy.deepcopy(item), later).external_id for item, _ in found] == ids


# --- Côtes d'Armor: reading -------------------------------------------------------------------


def test_cotes_darmor_ids_titles_and_whole_paris_days():
    _, found = records(cd22.SOURCE_ID)
    for item, record in found:
        p = item["properties"]
        assert record.external_id == p["NUMDOSSIER"]
        assert record.structured.start == datetime.fromisoformat(p["DATEDEBUT"][:10]).replace(tzinfo=PARIS)
        assert record.structured.end.date() == date.fromisoformat(p["DATEFIN"][:10])
        assert record.title.startswith(f"{p['CIRCULATION']}: {p['ROUTE']}, PR ")
        assert record.title.endswith(f"({p.get('COMMUNE') or 'Côtes-d' + chr(39) + 'Armor'})")
        if p.get("TRAVAUX"):
            assert record.summary.startswith(p["TRAVAUX"])
    _, plédéliac = by_id(cd22.SOURCE_ID)["2026T3115"]
    assert plédéliac.title == "Limitation de vitesse: D52, PR 14+2930 à PR 15+340 (Plédéliac)"
    one_day = by_id(cd22.SOURCE_ID)["2026T2950"][1].structured  # 5 November only
    assert one_day.start == datetime(2026, 11, 5, tzinfo=PARIS)
    assert one_day.end == datetime(2026, 11, 5, 23, 59, 59, tzinfo=PARIS)


def test_a_cotes_darmor_time_other_than_midnight_is_read_as_that_paris_moment():
    now, body = fixture(cd22.SOURCE_ID)
    item = copy.deepcopy(body["items"][0])
    item["properties"]["DATEFIN"] = "2027-07-31 17:30:00.0"
    assert cd22.to_record(item, now).structured.end == datetime(2027, 7, 31, 17, 30, tzinfo=PARIS)
    item["properties"]["DATEFIN"] = None
    assert cd22.to_record(item, now).structured.end is None  # not stated: left empty


def test_cotes_darmor_measures_give_the_event_type():
    _, found = records(cd22.SOURCE_ID)
    expected = {
        "INTERDICTION": EventType.PLANNED_ROAD_CLOSURE.value,
        "Circulation interdite": EventType.PLANNED_ROAD_CLOSURE.value,
        "Circulation alternée": EventType.LANE_RESTRICTION.value,
        "Circulation alternée et limitation de vitesse": EventType.LANE_RESTRICTION.value,
        "Limitation de vitesse": EventType.ROAD_WORKS.value,
        "Limitation catégorielle": EventType.ROAD_WORKS.value,
        "Limitation catégorielle et de vitesse": EventType.ROAD_WORKS.value,
    }
    seen = set()
    for item, record in found:
        measure = item["properties"]["CIRCULATION"]
        assert record.structured.event_type == expected[measure]
        assert record.structured.locations[0].closure == measure
        seen.add(measure)
    assert seen == set(expected)


def test_cotes_darmor_keeps_the_line_drawn_and_a_collection_as_its_lines():
    now, body = fixture(cd22.SOURCE_ID)
    for item in body["items"]:
        record = cd22.to_record(item, now)
        source = item.get("geometry")
        if source is None:
            assert record is None  # no line: unlocated, left out
        elif source["type"] == "GeometryCollection":
            lines = [part["coordinates"] for part in source["geometries"] if part["type"] == "LineString"]
            assert record.structured.geometry == {"type": "MultiLineString", "coordinates": lines}
        else:
            assert record.structured.geometry == source
    assert any(item.get("geometry") is None for item in body["items"])
    assert any((item.get("geometry") or {}).get("type") == "GeometryCollection" for item in body["items"])


def test_cotes_darmor_hours_stay_text_and_data_fair_bookkeeping_is_not_evidence():
    _, found = records(cd22.SOURCE_ID)
    for item, record in found:
        p = item["properties"]
        kept = record.raw["item"]["properties"]
        assert set(kept) == set(p) - cd22.BOOKKEEPING
        assert all(p[key] == value for key, value in kept.items())
        assert record.published_at == datetime.fromisoformat(p["_updatedAt"].replace("Z", "+00:00"))
        for hours in (p.get("JOURSETHORAIRES1"), p.get("JOURSETHORAIRES2")):
            if hours:
                assert " ".join(hours.split()) in record.structured.stated_period
                assert " ".join(hours.split()) in record.summary
    stated = by_id(cd22.SOURCE_ID)["2026T3115"][1].structured.stated_period
    assert stated.startswith("2026-11-03 – 2027-07-31")
    # Pushed again with a new line id and update time, the order is no revision.
    item, record = found[0]
    again = copy.deepcopy(item)
    again["properties"].update({"_id": "another", "_i": 1, "_rand": 2, "_updatedAt": "2026-11-06T03:00:10.469Z"})
    assert cd22.to_record(again, record.retrieved_at).content_hash == record.content_hash


def test_a_cotes_darmor_dossier_listed_twice_is_one_order_its_latest_line():
    _, body = fixture(cd22.SOURCE_ID)
    twice = [item for item in body["items"] if item["properties"]["NUMDOSSIER"] == "2026T0287"]
    assert len(twice) == 2
    kept = cd22.orders(body["items"], date(2026, 7, 1))
    numbers = [item["properties"]["NUMDOSSIER"] for item in kept]
    assert len(numbers) == len(set(numbers)) and "2026T0287" in numbers
    latest = max(twice, key=lambda item: item["properties"]["_updatedAt"])
    assert next(item for item in kept if item["properties"]["NUMDOSSIER"] == "2026T0287") is latest


# --- Côtes d'Armor: fetching ------------------------------------------------------------------


def cotes_darmor_connector(handler, now, scheduled=True):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return cd22.CotesDarmorWorksOrdersConnector(
        cd22.cotes_darmor_source(scheduled=scheduled), "test-agent", client=client, clock=lambda: now
    )


def test_cotes_darmor_stops_at_the_page_ending_with_an_ended_order_and_keeps_the_rest_running():
    now, body = fixture(cd22.SOURCE_ID)
    asked = []

    def handler(request):
        asked.append(request)
        page = {"type": "FeatureCollection", "total": body["total"], "features": body["items"]}
        return httpx.Response(200, json=page, headers={"Link": f"<{body['next_link']}>; rel=next"})

    connector = cotes_darmor_connector(handler, now)
    kept = connector.fetch()
    assert len(asked) == 1 and asked[0].headers["User-Agent"] == "test-agent"
    assert dict(asked[0].url.params) == {"size": "1000", "sort": "-DATEFIN", "format": "geojson"}
    today = now.astimezone(PARIS).date()
    running = {
        item["properties"]["NUMDOSSIER"]
        for item in body["items"]
        if item.get("geometry") and date.fromisoformat(item["properties"]["DATEFIN"][:10]) >= today
    }
    assert {record.external_id for record in kept} == running == connector.observed_ids
    assert len(running) == 20 and all(record.structured.end >= now for record in kept)
    upcoming = [record for record in kept if record.structured.start > now]
    assert upcoming and len(upcoming) < len(kept)


def test_cotes_darmor_follows_the_link_header_while_the_page_is_still_running():
    now, body = fixture(cd22.SOURCE_ID)
    today = now.astimezone(PARIS).date()
    first = [i for i in body["items"] if date.fromisoformat(i["properties"]["DATEFIN"][:10]) >= today]
    rest = body["items"][len(first) :]
    asked = []

    def handler(request):
        asked.append(str(request.url))
        if len(asked) == 1:
            page = {"type": "FeatureCollection", "features": first}
            return httpx.Response(200, json=page, headers={"Link": f"<{body['next_link']}>; rel=next"})
        return httpx.Response(200, json={"type": "FeatureCollection", "features": rest})

    kept = cotes_darmor_connector(handler, now).fetch()
    assert len(asked) == 2 and asked[1] == str(httpx.URL(body["next_link"]))
    assert len(kept) == 20


def test_cotes_darmor_ended_by_the_run_clock_are_dropped():
    now, body = fixture(cd22.SOURCE_ID)
    later = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)

    def handler(request):
        return httpx.Response(200, json={"type": "FeatureCollection", "features": body["items"]})

    kept = {record.external_id for record in cotes_darmor_connector(handler, later, scheduled=False).fetch()}
    assert not {"2026T3037", "2026T3073", "2026T3071", "2026T2950"} & kept  # ended 5 to 13 November
    assert {"2026T3115", "2026T2024"} <= kept


def test_cotes_darmor_refusals_and_endless_pages_are_connector_errors():
    now, body = fixture(cd22.SOURCE_ID)
    with pytest.raises(ConnectorError, match="rate limited"):
        cotes_darmor_connector(lambda request: httpx.Response(429), now).fetch()
    running = [i for i in body["items"] if i["properties"]["DATEFIN"][:10] >= "2026-11-05"]

    def endless(request):
        page = {"type": "FeatureCollection", "features": running}
        return httpx.Response(200, json=page, headers={"Link": f"<{body['next_link']}>; rel=next"})

    with pytest.raises(ConnectorError, match="pages"):
        cotes_darmor_connector(endless, now).fetch()


# --- Brest: reading ---------------------------------------------------------------------------


def test_brest_areas_are_grouped_by_order_in_their_own_order():
    _, body = fixture(brest.SOURCE_ID)
    orders = brest.orders(body["items"])
    assert len(orders) == len({item["properties"]["ARRETESRCID"] for item in body["items"]})
    four = next(order for order in orders if order["ARRETESRCID"] == "26-AT-0024")
    assert [area["properties"]["EMPRISENO"] for area in four["features"]] == [1, 2, 3, 4]


def test_brest_orders_that_restrict_no_traffic_or_are_not_published_are_left_out():
    now, _ = fixture(brest.SOURCE_ID)
    orders = {order["ARRETESRCID"]: order for order in items(brest.SOURCE_ID)}
    assert brest.to_record(orders["26-AT-0038"], now) is None  # parking ban only
    assert brest.to_record(orders["26-AT-0016"], now) is None  # INTERNET "false", no shape
    hidden = copy.deepcopy(orders["26-AT-0048"])
    hidden["features"][0]["properties"]["INTERNET"] = "false"
    assert brest.to_record(hidden, now) is None
    pedestrians = copy.deepcopy(orders["26-AT-0048"])
    pedestrians["features"][0]["properties"].update(
        {"MESURES": "BZH - Cheminement piétonnier interdit", "PARAMMESUR": None}
    )
    assert brest.to_record(pedestrians, now) is None
    kept = by_id(brest.SOURCE_ID)
    assert set(kept) == set(orders) - {"26-AT-0038", "26-AT-0016"}


def test_brest_event_types_come_from_the_measures_not_the_order_title():
    kept = {number: record for number, (_, record) in by_id(brest.SOURCE_ID).items()}
    closure, lane = EventType.PLANNED_ROAD_CLOSURE.value, EventType.LANE_RESTRICTION.value
    assert kept["26-AT-0040"].structured.event_type == closure  # interdiction totale
    assert kept["26-AT-0040"].title == "Circulation interdite (interdiction totale): 35 RUE JOHANN STRAUSS (Brest métropole)"
    assert kept["26-AT-0048"].structured.event_type == lane
    assert kept["26-AT-0048"].title.startswith("Circulation interdite (voie réduite): 85 CHE DE KERASTEL MONTAGNE")
    assert kept["26-AT-0036"].structured.event_type == lane
    assert kept["26-AT-0036"].title.startswith("Circulation alternée: ")
    # Titled "Route barrée", the order states a reduced lane; titled "Chaussée rétrécie", a full closure.
    assert "(Route barrée)" in kept["26-AT-0037"].summary and kept["26-AT-0037"].structured.event_type == lane
    assert "(Chaussée rétrécie)" in kept["26-AT-0030"].summary and kept["26-AT-0030"].structured.event_type == closure
    # A measure name the layer cut short is not read; the full names in PARAMMESUR are.
    cut = kept["26-AT-0015"]
    assert cut.structured.event_type == closure
    assert "Circulation interdi;" not in cut.summary and "Circulation alternée" in cut.summary


def test_brest_draws_the_works_areas_and_names_the_detour():
    _, body = fixture(brest.SOURCE_ID)
    shapes = {item["properties"]["IDEMPRISE"]: item for item in body["items"]}
    found = by_id(brest.SOURCE_ID)
    _, strauss = found["26-AT-0040"]
    works = next(s for s in shapes.values() if s["properties"]["ARRETESRCID"] == "26-AT-0040" and s["properties"]["EMPR_TYPE"] == "CIRCULATION")
    assert strauss.structured.geometry == works["geometry"]
    assert "Déviation : BD TANGUY PRIGENT" in strauss.summary
    _, porte = found["26-AT-0024"]  # two works areas (one closing, one closing and banning parking) and two detours
    works = [
        s["geometry"]
        for s in sorted(shapes.values(), key=lambda s: s["properties"]["EMPRISENO"])
        if s["properties"]["ARRETESRCID"] == "26-AT-0024" and s["properties"]["EMPR_TYPE"] != "DEVIATION"
    ]
    assert porte.structured.geometry == {"type": "MultiPolygon", "coordinates": [g["coordinates"] for g in works]}
    assert len(porte.structured.locations) == 2 and "Déviation : RUE BOUILLON" in porte.summary
    _, plymouth = found["26-AT-0015"]
    assert plymouth.structured.geometry["type"] == "MultiPolygon"


def test_brest_days_are_the_stated_days_in_paris_time():
    _, found = records(brest.SOURCE_ID)
    for order, record in found:
        first = order["features"][0]["properties"]
        assert record.structured.start.date() == datetime.fromtimestamp(first["ARRETEDEB"] / 1000, tz=timezone.utc).date()
        assert record.structured.end.date() == datetime.fromtimestamp(first["ARRETEFIN"] / 1000, tz=timezone.utc).date()
        stated = first["PARAMARR"].split("Date de début de l'arrêté : ")[1][:10]
        assert record.structured.start.strftime("%d/%m/%Y") == stated
    _, goez = by_id(brest.SOURCE_ID)["26-AT-0048"]
    assert goez.structured.end == datetime(2027, 2, 4, 23, 59, 59, tzinfo=PARIS)


def test_brest_evidence_has_no_applicant_no_firm_and_no_load_fields():
    now, body = fixture(brest.SOURCE_ID)
    planted = copy.deepcopy(body["items"])
    for item in planted:
        p = item["properties"]
        p["EMETTEUR"], p["EMETT_ID"] = PLANTED, 4242
        if p.get("PARAMMESUR"):
            p["PARAMMESUR"] = p["PARAMMESUR"].replace("[entreprise]", PLANTED)
    assert any(PLANTED in (item["properties"].get("PARAMMESUR") or "") for item in planted)
    found = [(o, r) for o in brest.orders(planted) if (r := brest.to_record(o, now))]
    assert found
    left_out = brest.PERSONAL | brest.BOOKKEEPING
    for order, record in found:
        text = json.dumps(record.raw, ensure_ascii=False)
        assert PLANTED not in text and PLANTED not in (record.summary or "") and "4242" not in text
        for area in order["features"]:
            assert not left_out & set(area["properties"])
            assert brest.COMPANY_KEY not in (area["properties"].get("PARAMMESUR") or "")
    # Everything else is kept as the layer gave it.
    source = {item["properties"]["IDEMPRISE"]: item for item in body["items"]}
    for order, _ in found:
        for area in order["features"]:
            stated = source[area["properties"]["IDEMPRISE"]]
            assert area["geometry"] == stated["geometry"]
            assert set(area["properties"]) == set(stated["properties"]) - left_out
            unchanged = {k: v for k, v in area["properties"].items() if k != "PARAMMESUR"}
            assert all(stated["properties"][k] == v for k, v in unchanged.items())


# --- Brest: fetching --------------------------------------------------------------------------


def brest_connector(handler, now):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return brest.BrestTrafficOrdersConnector(brest.brest_source(scheduled=True), "test-agent", client=client, clock=lambda: now)


def test_brest_asks_once_in_wgs84_and_keeps_only_orders_in_force_or_coming():
    now, body = fixture(brest.SOURCE_ID)
    asked = []

    def handler(request):
        asked.append(request)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": body["items"]})

    connector = brest_connector(handler, now)
    kept = connector.fetch()
    assert len(asked) == 1 and asked[0].url.path.endswith("/MapServer/1718004/query")
    assert dict(asked[0].url.params) == {"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson"}
    assert [record.external_id for record in kept] == ["26-AT-0048"]  # 26-AT-0038 bans parking only
    assert connector.observed_ids == set(by_id(brest.SOURCE_ID))
    earlier = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
    kept = {record.external_id for record in brest_connector(handler, earlier).fetch()}
    assert {"26-AT-0040", "26-AT-0036", "26-AT-0048", "26-AT-0037"} <= kept
    assert not {"26-AT-0024", "26-AT-0015", "26-AT-0030"} & kept  # ended in the summer


def test_a_cut_brest_list_is_a_connector_error():
    now, body = fixture(brest.SOURCE_ID)
    cut = {"type": "FeatureCollection", "features": body["items"], "exceededTransferLimit": True}
    with pytest.raises(ConnectorError, match="cut"):
        brest_connector(lambda request: httpx.Response(200, json=cut), now).fetch()
    error = {"error": {"code": 400, "message": "Invalid query"}}
    with pytest.raises(ConnectorError, match="error"):
        brest_connector(lambda request: httpx.Response(200, json=error), now).fetch()


# --- into the database --------------------------------------------------------------------------


def test_events_are_stored_once_and_every_value_fits_its_column(session):
    definitions = [make(scheduled=False) for _, make, _ in FEEDS.values()]
    SourceRepository(session).sync_registry(definitions)
    session.commit()
    created = {}
    for definition in definitions:
        _, found = records(definition.source_id)

        def ingest(found=found, definition=definition):
            result = run_ingestion(
                FakeConnector([record for _, record in found], source=definition),
                KeywordClassifier.for_city(FRANCE), SqlIngestionStore(session), None, FRANCE,
            )  # fmt: skip
            session.commit()
            return result

        created[definition.source_id] = (ingest().events_created, len(found))
        assert ingest().events_created == 0
    assert all(made == expected for made, expected in created.values()), created
    rows = session.scalars(select(Event).where(Event.source_id.in_(FEEDS))).unique().all()
    assert rows and {row.status for row in rows} == {"VALIDATION_REQUIRED"}
    assert all(row.geometry is not None for row in rows)
    too_long = []
    for model in (Event, SourceArtifact, EventVersion):
        limits = {
            column.name: column.type.length
            for column in model.__table__.columns
            if isinstance(column.type, String) and column.type.length
        }
        for row in session.scalars(select(model)).unique():
            for name, limit in limits.items():
                value = getattr(row, name)
                if value is not None and len(str(value)) > limit:
                    too_long.append((model.__tablename__, name, len(str(value)), limit))
    assert not too_long, too_long[:10]
