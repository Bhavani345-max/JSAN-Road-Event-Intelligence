"""Taipei, New Taipei and Taichung works feeds (21 October 2026), on trimmed real files.

The fixtures are records as received on 21 October 2026, trimmed to a few
of each kind; the values of the personal fields (names and phone numbers of
the people in charge) were replaced by placeholders (王小明, 0900000000)
before saving. No test reaches any of the three services.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String

from connectors.base import ConnectorError
from connectors.official import new_taipei_excavation as new_taipei
from connectors.official import taichung_traffic_plans as taichung
from connectors.official import taipei_works as taipei
from connectors.official import twd97
from connectors.official.taiwan_open_data import TAIPEI_TIME, organisation, roc_date
from packages.cities import cities_within, country_entry, get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass, TermsStatus
from services.ingestion.pipeline import classify

FIXTURES = Path(__file__).parents[1] / "fixtures"
TAIPEI_FILE = FIXTURES / "taipei_todaywork_2026-10-21.json"
NEW_TAIPEI_FILE = FIXTURES / "new_taipei_road_excavation_2026-10-21.csv"
TAICHUNG_FILE = FIXTURES / "taichung_traffic_plans_2026-10-21.json"
# 19:05 in Taipei.
NOW = datetime(2026, 10, 21, 11, 5, tzinfo=timezone.utc)

SOURCES = {
    # source id: (definition, connector, fixture, city)
    taipei.SOURCE_ID: (taipei.taipei_source, taipei.TaipeiTodayWorksConnector, TAIPEI_FILE, "taipei"),
    new_taipei.SOURCE_ID: (new_taipei.new_taipei_source, new_taipei.NewTaipeiRoadExcavationConnector, NEW_TAIPEI_FILE, "new-taipei"),
    taichung.SOURCE_ID: (taichung.taichung_source, taichung.TaichungTrafficPlansConnector, TAICHUNG_FILE, "taichung"),
}


def client(path: Path) -> httpx.Client:
    body = path.read_bytes()
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body)))


def connector_for(source_id: str):
    make, connector_class, path, _ = SOURCES[source_id]
    return connector_class(make(scheduled=True), "ua", client=client(path), clock=lambda: NOW)


def local(moment: datetime) -> str:
    return moment.astimezone(TAIPEI_TIME).strftime("%Y-%m-%d %H:%M:%S")


# --- shared reading -------------------------------------------------------------------


def test_roc_dates_and_organisations_are_read_as_written():
    assert roc_date("115/10/21").isoformat() == "2026-10-21"
    assert roc_date("99/08/17").isoformat() == "2010-08-17"
    assert roc_date("1151021").isoformat() == "2026-10-21"
    assert roc_date("115/02/30") is None and roc_date("") is None and roc_date("2026-10-21") is None
    for name in ("瑞祥營造有限公司", "新北市政府水利局河川工程科", "臺中市南區信義國小", "駿驊廣告社", "尚未發包"):
        assert organisation(name) == name
    for name in ("王小明", "彭秀枝", "楊春堂", "", None):
        assert organisation(name) is None


# --- Taipei ---------------------------------------------------------------------------


def taipei_features() -> dict[tuple[str, str], dict]:
    body = json.loads(TAIPEI_FILE.read_text(encoding="utf-8-sig"))
    return {(f["properties"]["Ac_no"], f["properties"]["sno"]): f for f in body["features"]}


def test_taipei_site_is_read_with_its_area_its_point_and_its_approved_days():
    feature = taipei_features()[("11200189-20", "1")]
    record = taipei.to_record(feature, NOW)
    properties = feature["properties"]
    assert record.external_id == "11200189-20-1"
    assert record.title.startswith("Road maintenance: 南海路/羅斯福路") and record.title.endswith("(萬華區, Taipei)")
    assert record.structured.event_type == EventType.ROAD_WORKS.value
    assert record.structured.category == "道路維護通報 / 道路維護"
    # The works area, converted from the TWD97 grid, is the event's geometry.
    assert record.structured.geometry["type"] == "MultiPolygon"
    first = properties["Positions"][0][0][0]
    assert record.structured.geometry["coordinates"][0][0][0] == list(twd97.to_lon_lat(*first))
    assert record.structured.locations[0].geometry == twd97.point(properties["X"], properties["Y"])
    # Approved 115/07/01 to 115/12/31 (ROC), in days: whole days in Taipei time.
    assert local(record.structured.start) == "2026-07-01 00:00:00"
    assert local(record.structured.end) == "2026-12-31 23:59:59"
    assert "115/07/01 – 115/12/31" in record.structured.stated_period
    assert properties["Co_Ti"] in record.structured.stated_period  # the hours stay words
    assert record.structured.attribution.startswith("臺北市政府工務局 2026 臺北市今日施工資訊")


def test_taipei_keeps_organisations_and_drops_the_site_staff_and_their_numbers():
    feature = taipei_features()[("114003796", "1")]
    record = taipei.to_record(feature, NOW)
    stored = record.raw["item"]["properties"]
    assert not taipei.PERSONAL_FIELDS & set(stored)
    assert "0900000000" not in json.dumps(record.raw, ensure_ascii=False)
    assert stored["App_Name"] and stored["Tc_Na"] and f"施工廠商：{stored['Tc_Na']}" in record.summary
    # The source says this site affects traffic and suggests a detour.
    assert record.structured.locations[0].closure == "影響通行（建議改道）"


def test_taipei_takes_road_works_not_pavement_only_works_or_the_feeds_test_entries():
    features = taipei_features()
    sidewalk_quiet = features[("11501492", "1")]["properties"]
    sidewalk_blocking = features[("11501605", "1")]["properties"]
    assert sidewalk_quiet["WItem"] == sidewalk_blocking["WItem"] == "人行道維護"
    assert (sidewalk_quiet["IsBlock"], sidewalk_blocking["IsBlock"]) == ("否", "是")
    assert taipei.to_record(features[("11501492", "1")], NOW) is None
    assert taipei.to_record(features[("11501605", "1")], NOW) is not None
    for key in (("99015156", "722"), ("99015156", "686")):
        assert features[key]["properties"]["Addr"] == "全市APP測試"
        assert taipei.to_record(features[key], NOW) is None


def test_taipei_run_keeps_the_sites_in_effect_inside_taipei():
    connector = connector_for(taipei.SOURCE_ID)
    records = connector.fetch()
    # 12 sites in the sample: one pavement-only and two test entries are not taken.
    assert len(connector.observed_ids) == 9 and len(records) == 7
    # 115002779-4 (to 115/10/07) and 115002387-2 (to 115/10/20) have ended.
    assert {"115002779-4", "115002387-2"} <= connector.observed_ids
    assert not {"115002779-4", "115002387-2"} & {r.external_id for r in records}
    assert all(r.structured.start and r.structured.end and r.structured.geometry for r in records)
    assert {classify(r, None, get_city("taipei")).label.value for r in records} == {"SOURCE_PROVIDED_EVENT"}


# --- New Taipei -----------------------------------------------------------------------


def new_taipei_rows() -> dict[str, dict]:
    return {row["caseid"]: row for row in new_taipei.read_rows(NEW_TAIPEI_FILE.read_text(encoding="utf-8"))}


def test_new_taipei_permit_is_read_with_its_point_and_permitted_days():
    row = new_taipei_rows()["349893"]
    record = new_taipei.to_record(row, NOW)
    assert record.external_id == "349893" and record.title.endswith("(New Taipei)")
    assert record.structured.event_type == EventType.ROAD_WORKS.value
    assert record.structured.geometry == twd97.point(row["twd97x"], row["twd97y"])
    assert record.structured.category == "道路挖掘 / 一般" and record.structured.status == "已核發許可證"
    assert (local(record.structured.start), local(record.structured.end)) == ("2026-07-20 00:00:00", "2027-01-15 23:59:59")
    assert row["workperiod"] in record.structured.stated_period


def test_new_taipei_hours_are_used_only_when_stated_for_one_continuous_stretch():
    rows = new_taipei_rows()
    # "連續性施工，115年07月01日09時起116年07月27日16時止，共392日" on the permit's own days.
    stated = new_taipei.to_record(rows["348951"], NOW)
    assert (local(stated.structured.start), local(stated.structured.end)) == ("2026-07-01 09:00:00", "2027-07-27 16:00:00")
    # Changed several times: the permit's days, whole, and the words kept.
    changed = new_taipei.to_record(rows["296348"], NOW)
    assert "；第1次變更" in rows["296348"]["workperiod"]
    assert (local(changed.structured.start), local(changed.structured.end)) == ("2022-12-12 00:00:00", "2027-01-13 23:59:59")


def test_new_taipei_drops_people_their_numbers_and_contact_remarks():
    rows = new_taipei_rows()
    for case in rows:
        stored = new_taipei.to_record(rows[case], NOW).raw["item"]
        assert not new_taipei.PERSONAL_FIELDS & set(stored)
        assert "0900000000" not in json.dumps(stored, ensure_ascii=False)
    # A private owner named as the supervising party is a person: not kept.
    assert rows["318413"]["supervise"] == "王小明"
    assert "supervise" not in new_taipei.to_record(rows["318413"], NOW).raw["item"]
    # Remarks with a contact person and phone number are not kept; others are.
    for case in ("343309", "343727"):
        assert "0900-000-000" in rows[case]["remark"]
        record = new_taipei.to_record(rows[case], NOW)
        assert "remark" not in record.raw["item"] and "0900-000-000" not in record.summary
    assert new_taipei.to_record(rows["309521"], NOW).raw["item"]["remark"] == rows["309521"]["remark"]


def test_new_taipei_run_keeps_the_permits_in_effect():
    connector = connector_for(new_taipei.SOURCE_ID)
    records = connector.fetch()
    assert len(connector.observed_ids) == 11 and len(records) == 9
    assert not {"318413", "311511"} & {r.external_id for r in records}  # ended in 2024
    assert {classify(r, None, get_city("new-taipei")).label.value for r in records} == {"SOURCE_PROVIDED_EVENT"}


def test_new_taipei_refuses_a_file_that_is_not_the_permits_csv():
    with pytest.raises(ConnectorError):
        new_taipei.read_rows("<html>Request Rejected</html>")


# --- Taichung -------------------------------------------------------------------------


def taichung_items() -> list[dict]:
    rows = json.loads(TAICHUNG_FILE.read_text(encoding="utf-8"))
    return taichung.group_plans(rows)


def by_plan(plan_id: str) -> list[dict]:
    return [item for item in taichung_items() if item["plan"].startswith(f"{plan_id}:")]


def test_taichung_daily_rows_of_one_site_are_one_period_with_the_stated_hours():
    (item,) = by_plan("1151014040036")  # 10-22, 10-23 and 10-24, each 9 to 16
    assert len(item["rows"]) == 3
    record = taichung.to_record(item, NOW)
    assert (local(record.structured.start), local(record.structured.end)) == ("2026-10-22 09:00:00", "2026-10-24 16:00:00")
    assert record.structured.stated_period == "施工日期：2026-10-22、2026-10-23、2026-10-24 施工時段：9時至16時"
    assert record.structured.geometry == {"type": "Point", "coordinates": [120.7096224, 24.1559431]}
    # The kind codes are not explained by the source: no event type is invented.
    assert record.structured.event_type is None and record.structured.category == "交通維持計畫 / 工程種類 4"


def test_taichung_days_with_a_gap_are_separate_periods_and_copies_count_once():
    gap = by_plan("1151016040016")  # 10-23, then 10-26 and 10-27
    assert sorted(len(item["rows"]) for item in gap) == [1, 2]
    assert len({item["plan"] for item in gap}) == 2
    (copy,) = by_plan("1150617010002")  # the same row twice
    assert len(copy["rows"]) == 1
    record = taichung.to_record(copy, NOW)
    # 0 to 24: the whole days.
    assert (local(record.structured.start), local(record.structured.end)) == ("2026-10-21 00:00:00", "2026-10-23 23:59:59")
    two_sites = by_plan("1130628020001")  # one plan, two sites on the same days
    assert len(two_sites) == 2 and len({item["plan"] for item in two_sites}) == 2


def test_taichung_points_make_the_site_line_or_area_and_rows_without_one_are_not_taken():
    shapes = {item["plan"].split(":")[0]: taichung.to_record(item, NOW).structured.geometry["type"] for item in taichung_items()}
    # The points close (the last is the first): an area, a sale's streets and a sewer works' blocks.
    assert shapes["1150522030001"] == "Polygon" and shapes["1140303060001"] == "Polygon"
    assert shapes["1110712020001"] == "LineString" and shapes["1150317010005"] == "LineString"
    assert shapes["1151012040072"] == "Point"
    assert "1151009040005" not in shapes  # no point at all


def test_taichung_drops_the_contact_person_their_phone_and_an_individuals_name():
    for item in taichung_items():
        for row in item["rows"]:
            assert not taichung.PERSONAL_FIELDS & set(row)
            assert row.get("Company") != "王小明"
    (item,) = by_plan("1150317010005")
    assert item["rows"][0]["Company"] == "瑞祥營造有限公司"
    assert "執行單位：瑞祥營造有限公司" in taichung.to_record(item, NOW).summary


def test_taichung_run_keeps_the_plans_in_effect():
    connector = connector_for(taichung.SOURCE_ID)
    records = connector.fetch()
    assert len(connector.observed_ids) == 13 and len(records) == 11
    # Ended at 16:00 today (it is 19:05 in Taipei).
    ended = {plan for plan in connector.observed_ids if plan.startswith(("1151012040068:", "1151001040049:"))}
    assert len(ended) == 2 and not ended & {r.external_id for r in records}
    assert {classify(r, None, get_city("taichung")).label.value for r in records} == {"SOURCE_PROVIDED_EVENT"}


# --- the three sources ----------------------------------------------------------------


@pytest.mark.parametrize("source_id", SOURCES)
def test_each_is_a_connected_tier_one_open_data_source_run_by_hand_unless_scheduled(source_id):
    from app.models import Source

    make, _, _, city_id = SOURCES[source_id]
    definition = make(scheduled=False)
    assert definition.source_id == source_id and definition.city == city_id and definition.country == "TW"
    assert definition.integration_status is IntegrationStatus.CONNECTED and definition.source_tier == 1
    assert definition.active is False and make(scheduled=True).active is True
    assert definition.source_class is SourceClass.GOVERNMENT_OPEN_DATA and definition.language == "zh"
    assert definition.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert definition.terms_status is TermsStatus.PERMITS_TESTING and definition.terms_reviewed is False
    assert "Open Government Data License, version 1.0" in definition.licence
    assert "政府資料開放授權條款" in definition.attribution and "https://data.gov.tw/license" in definition.attribution
    assert source_id in get_city(city_id).official_sources
    values = definition.model_dump(mode="json")
    for column in Source.__table__.columns:
        if isinstance(column.type, String) and column.type.length and values.get(column.name) is not None:
            assert len(str(values[column.name])) <= column.type.length, column.name


def test_taiwan_is_the_country_entry_of_its_three_cities():
    taiwan = get_city("taiwan")
    assert (taiwan.level, taiwan.country, taiwan.timezone) == ("country", "TW", "Asia/Taipei")
    assert {city.id for city in cities_within(taiwan)} >= {"taipei", "new-taipei", "taichung"}
    for city_id in ("taipei", "new-taipei", "taichung"):
        city = get_city(city_id)
        assert country_entry(city) == taiwan and city.timezone == "Asia/Taipei" and city.language == "zh"
    assert get_city("taipei").covers(25.0478, 121.517) and get_city("taichung").covers(24.1618, 120.6469)
    assert {"Taipei", "臺北"} <= set(get_city("taipei").scope_terms)


@pytest.mark.parametrize("source_id", SOURCES)
def test_records_become_events_through_the_pipeline(session, source_id):
    from sqlalchemy import select

    from app.models import Event, SourceArtifact
    from app.repositories.ingestion_store import SqlIngestionStore
    from app.repositories.sources import SourceRepository
    from services.extraction import KeywordClassifier
    from services.ingestion import run_ingestion

    make, _, _, city_id = SOURCES[source_id]
    source = make(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    result = run_ingestion(connector_for(source_id), KeywordClassifier.from_file(), SqlIngestionStore(session), None, get_city(city_id))
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source_id)))
    assert result.events_created == len(events) > 0
    assert all(e.geometry and e.start_time and e.end_time and e.city == get_city(city_id).name for e in events)
    stored = json.dumps(
        [a.raw_content for a in session.scalars(select(SourceArtifact).where(SourceArtifact.source_id == source_id))],
        ensure_ascii=False, default=str,
    )  # fmt: skip
    assert "0900000000" not in stored and "王小明" not in stored
    # PostgreSQL (production) refuses a value longer than its column; SQLite does not check.
    for model in (Event, SourceArtifact):
        limits = {c.name: c.type.length for c in model.__table__.columns if isinstance(c.type, String) and c.type.length}
        for row in session.scalars(select(model).where(model.source_id == source_id)).unique():
            for name, limit in limits.items():
                value = getattr(row, name)
                assert value is None or len(str(value)) <= limit, (model.__tablename__, name)
