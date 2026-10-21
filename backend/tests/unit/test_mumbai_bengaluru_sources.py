"""Mumbai and Bengaluru official sources (8 October 2026).

The fixtures are the two pages exactly as fetched on 8 October 2026: the
Mumbai Traffic Police Public Notice List and the Bengaluru Traffic Police
home page. Neither publishes coordinates, so their events are located by a
named place (APPROXIMATE) or left unresolved; nothing is estimated.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from connectors.base import ConnectorError
from connectors.official import (
    BengaluruTrafficPoliceConnector,
    MumbaiTrafficPoliceConnector,
    bengaluru_source,
    mumbai_source,
)
from connectors.official.bengaluru_traffic_police import parse_items, place_part
from connectors.official.bengaluru_traffic_police import rebuild_structured as btp_rebuild
from connectors.official.mumbai_traffic_police import rebuild_structured as mumbai_rebuild
from connectors.official.bengaluru_traffic_police import to_record as btp_record
from connectors.official.mumbai_traffic_police import (
    event_type_for,
    file_name_place,
    is_parking_only,
    parse_listing,
)
from connectors.official.stated_text import distance_in_metres, stated_dates, stated_distance
from connectors.registry import registered_sources
from packages.cities import get_city
from packages.event_schema import EventStatus, EventType, LocationClass
from packages.source_models import (
    CommercialUse,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceEvent,
    SourceLocation,
    TermsStatus,
)
from services.extraction import build_event_from_source, classify_source_record
from services.geo_resolution import resolver_for

FIXTURES = Path(__file__).parents[1] / "fixtures"
MUMBAI_PAGE = (FIXTURES / "mumbai_public_notices_2026-10-08.html").read_text(encoding="utf-8")
BTP_PAGE = (FIXTURES / "btp_homepage_2026-10-08.html").read_text(encoding="utf-8")
NOW = datetime(2026, 10, 8, 8, 0, tzinfo=timezone.utc)
IST = timezone(timedelta(hours=5, minutes=30))
MUMBAI = get_city("mumbai")
BENGALURU = get_city("bengaluru")


def event_of(record, city, resolver=None):
    return build_event_from_source(
        record, classify_source_record(record, city), now=NOW, resolver=resolver, city=city
    )


def mumbai_records():
    return parse_listing(MUMBAI_PAGE, NOW)


def mumbai_record(number: str) -> RawSourceRecord:
    return next(record for record in mumbai_records() if f"(Notification {number})" in record.title)


def btp_records():
    return [record for line in parse_items(BTP_PAGE) if (record := btp_record(line, NOW))]


# --- cities and registry ------------------------------------------------------


def test_mumbai_and_bengaluru_are_configured_with_place_lists():
    assert (MUMBAI.country, MUMBAI.region, MUMBAI.timezone) == ("IN", "Maharashtra", "Asia/Kolkata")
    assert (BENGALURU.country, BENGALURU.region) == ("IN", "Karnataka")
    assert MUMBAI.covers(19.076, 72.8777) and not MUMBAI.covers(17.4, 78.5)
    assert BENGALURU.covers(12.9716, 77.5946) and not BENGALURU.covers(19.0, 72.8)
    assert len(resolver_for(MUMBAI)) > 5000 and len(resolver_for(BENGALURU)) > 5000
    assert MUMBAI.official_sources == ("mumbai-traffic-police-notifications",)
    assert BENGALURU.official_sources == ("bengaluru-traffic-police-website",)


@pytest.mark.parametrize(
    "source_id, city",
    [("mumbai-traffic-police-notifications", "mumbai"), ("bengaluru-traffic-police-website", "bengaluru")],
)
def test_the_listings_are_tier_one_and_removed_for_giving_no_location(source_id, city):
    registered = {s.definition.source_id: s for s in registered_sources()}[source_id]
    definition = registered.definition
    assert definition.source_class is SourceClass.AUTHORITATIVE_OFFICIAL
    assert definition.source_tier == 1 and definition.city == city
    # Removed on 15 October 2026 (decision 0029): their records give no coordinates.
    assert definition.integration_status is IntegrationStatus.NOT_USABLE
    assert definition.active is False and registered.create_connector is None
    assert definition.provides_geometry is False
    # Both authorities ask for permission before re-publication: recorded, not resolved.
    assert definition.terms_status is TermsStatus.REVIEW_REQUIRED
    assert definition.commercial_use is CommercialUse.UNKNOWN
    assert definition.attribution


def test_the_new_news_feeds_are_discovery_only_for_their_city():
    sources = {s.definition.source_id: s.definition for s in registered_sources()}
    assert sources["mid-day-mumbai"].city == "mumbai" and sources["mid-day-mumbai"].discovery_only
    assert sources["siasat-mumbai"].city == "mumbai"
    assert sources["the-hindu-bengaluru"].city == "bengaluru"
    assert all(sources[s].source_tier == 4 for s in ("mid-day-mumbai", "siasat-mumbai", "the-hindu-bengaluru"))


# --- stated text ------------------------------------------------------------


def test_dates_written_day_month_year_are_read_with_their_words():
    period = stated_dates("Routes shall be Closed on 26/08/2026", zone=IST)
    assert (period.start, period.end) == (
        datetime(2026, 8, 26, 0, 0, tzinfo=IST),
        datetime(2026, 8, 26, 23, 59, 59, tzinfo=IST),
    )
    assert period.text == "on 26/08/2026"
    until = stated_dates("closed until 31/05/2027", zone=IST)
    assert until.start is None and until.end == datetime(2027, 5, 31, 23, 59, 59, tzinfo=IST)
    both = stated_dates("from 14/09/2026 to 25/09/2026 24 hours", zone=IST)
    assert (both.start.day, both.end.day) == (14, 25) and both.text == "from 14/09/2026 to 25/09/2026"
    # Devanagari digits, as the Marathi orders write them.
    assert stated_dates("दि.१४/०९/२०२६ ते दि.२५/०९/२०२६", zone=IST) is None  # "ते" is not a word read
    assert stated_dates("from १४/०९/२०२६ to २५/०९/२०२६", zone=IST).start.day == 14
    assert stated_dates("Traffic Arrangement") is None


def test_a_distance_is_kept_in_the_sources_words_and_read_in_metres():
    assert stated_distance("from The Amrut Nagar circle Junction, to 100 meter Natioan muton shop") == "100 meter"
    assert stated_distance("a 2.56-km stretch of Sanjaynagar Main Road") == "2.56-km"
    assert stated_distance("Traffic Arrangement") is None
    # The number in one unit; the words stay the record. 20 m stays 20 m.
    assert distance_in_metres("100 meter") == 100.0
    assert distance_in_metres("2.56-km") == 2560.0
    assert distance_in_metres("20 m") == 20.0
    assert distance_in_metres("(१०० मीटर)".strip("()")) == 100.0
    assert distance_in_metres("a while") is None and distance_in_metres(None) is None

    record = mumbai_record("207/2026")  # parking-only: evidence, no structured reading
    assert record.structured is None
    from connectors.official.mumbai_traffic_police import structured_for
    structured = structured_for("Road closed", "Sagarpark Road closed from The Amrut Nagar circle to 100 meter", "Till Next Order", None)
    assert (structured.stated_distance, structured.stated_distance_m) == ("100 meter", 100.0)


# --- Mumbai Traffic Police notifications -----------------------------------------


def test_every_row_of_the_public_notice_list_is_read():
    records = mumbai_records()
    assert len(records) == 50
    assert all(record.source_id == "mumbai-traffic-police-notifications" for record in records)
    assert all(record.raw["row"]["notice_number"] for record in records)


def test_a_notification_keeps_its_number_date_subject_and_pdf_link_byte_for_byte():
    record = mumbai_record("209/2026")
    assert record.external_id == "823622"
    assert record.title == "Traffic Restrictions and Alternative Routes (Notification 209/2026)"
    assert record.published_at == datetime(2026, 10, 5, 0, 0, tzinfo=IST)
    # The file name carries spaces and a double-encoded narrow space; the
    # link only works when those bytes are percent-encoded exactly.
    assert record.url == (
        "https://mtperp.mahatrafficechallan.gov.in/GetPublicNotice/823622/"
        "202610050000_823622_DocScanner%206%20Oct%202026%2010-51%C3%A2%C2%80%C2%AFam.pdf"
    )
    assert record.raw["row"]["valid_till"] == "Till Next Order"
    structured = record.structured
    assert structured.event_type == EventType.TRAFFIC_DIVERSION.value
    assert structured.status == "Till Next Order" and structured.covers_city is True
    # The listing's English says nothing more: no road, no date, no distance;
    # the PDF's file name ("DocScanner 6 Oct 2026 10-51 am") is kept only as a hint.
    assert [place.kind for place in structured.locations] == ["file name"]
    assert structured.start is None and structured.end is None


def test_roads_named_in_the_english_summary_are_kept_as_unresolved_locations():
    record = mumbai_record("168/2026")
    assert record.structured.event_type == EventType.BRIDGE_TUNNEL_RESTRICTION.value
    assert [place.name for place in record.structured.locations if not place.fallback] == [
        "Poonya Shlok Ahilyabai Bridge",
        "Mumbai Central Junction",
    ]
    assert record.structured.affected_road == "Poonya Shlok Ahilyabai Bridge; Mumbai Central Junction"


def test_a_stated_day_becomes_the_period_with_its_words():
    record = mumbai_record("185/2026")
    assert record.structured.start == datetime(2026, 8, 26, 0, 0, tzinfo=IST)
    assert record.structured.end == datetime(2026, 8, 26, 23, 59, 59, tzinfo=IST)
    assert record.structured.stated_period == "on 26/08/2026"


def test_a_parking_only_notice_is_evidence_not_a_road_event():
    record = mumbai_record("207/2026")
    assert record.title == "No Parking (Notification 207/2026)"
    assert record.structured is None and "source_event" not in record.raw
    assert is_parking_only("There is 24 hours no parking on both sides of the road")
    assert not is_parking_only("Road Closed/ No Parking, Alternate Route")
    assert sum(record.structured is None for record in mumbai_records()) == 9


def test_the_notices_own_words_give_the_event_type_or_none():
    assert event_type_for("Changes in transportation routes for the Air Force Marathon") is EventType.MARATHON
    assert event_type_for("Alternate Roote For VVIP Vehicles Only") is EventType.VIP_MOVEMENT
    assert event_type_for("Excavation Route, Alternative Routes") is EventType.ROAD_WORKS
    assert event_type_for("Road Closed, No Entry, Diverted Route") is EventType.TRAFFIC_DIVERSION
    assert event_type_for("No Entry/Road Closure") is EventType.PLANNED_ROAD_CLOSURE
    assert event_type_for("Traffic Arrangement") is None


def test_a_notice_naming_a_known_place_is_located_there_approximately():
    record = mumbai_record("205/2026")
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event.title.startswith("Closure of roads in Dadar Division")
    assert event.city == "Mumbai" and event.status is EventStatus.VALIDATION_REQUIRED
    assert event.detection.location_class is LocationClass.APPROXIMATE
    assert event.detection.location.place_name == "Dadar"
    assert event.detection.location.method == "named_place"
    assert event.detection.location.reference.startswith("OpenStreetMap ")
    assert event.geometry.type == "Point" and MUMBAI.covers(*reversed(event.geometry.coordinates))
    assert event.detection.attribution.startswith("Source: Mumbai Traffic Police")


def test_a_notice_naming_no_known_place_is_an_event_with_an_unresolved_location():
    record = mumbai_record("209/2026")
    assert not any(not place.fallback for place in record.structured.locations)
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event is not None and event.geometry is None
    assert event.detection.location is None
    assert event.detection.location_class is LocationClass.UNRESOLVED
    assert event.source_reference.endswith(".pdf")


def test_a_record_without_geometry_or_places_from_a_feed_that_does_not_cover_a_city_is_not_an_event():
    record = mumbai_record("209/2026")
    structured = record.structured.model_copy(update={"covers_city": False})
    plain = record.model_copy(update={"structured": structured})
    assert not classify_source_record(plain, MUMBAI).is_relevant


def test_the_mumbai_connector_reads_the_page_and_keeps_the_newest_first():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "mtperp.mahatrafficechallan.gov.in"
        return httpx.Response(200, text=MUMBAI_PAGE, headers={"content-type": "text/html"})

    connector = MumbaiTrafficPoliceConnector(
        mumbai_source(scheduled=False), "test", max_records=30,
        client=httpx.Client(transport=httpx.MockTransport(handler)), clock=lambda: NOW,
    )  # fmt: skip
    records = connector.fetch()
    assert len(records) == 30
    assert records[0].external_id == "823622"
    assert records[0].published_at >= records[-1].published_at
    # The list is the 50 newest notices, not the orders in force, so nothing
    # is reported as observed or missing.
    assert not hasattr(connector, "observed_ids")


def test_a_refusal_or_a_page_without_the_table_is_an_error():
    def refused(request):
        return httpx.Response(503)

    connector = MumbaiTrafficPoliceConnector(
        mumbai_source(scheduled=False), "test", client=httpx.Client(transport=httpx.MockTransport(refused))
    )
    with pytest.raises(ConnectorError, match="rate limited"):
        connector.fetch()
    with pytest.raises(ConnectorError, match="Public Notice List"):
        parse_listing("<html><body>maintenance</body></html>", NOW)


# --- Bengaluru Traffic Police website -----------------------------------------


def test_the_events_list_is_read_from_the_view_all_dialog_without_repeats():
    lines = parse_items(BTP_PAGE)
    assert len(lines) == 39 == len(set(lines))
    assert lines[1].startswith("Department Work : White Topping Work at New Diagonal Road, Jayanagar.")


def test_an_item_keeps_the_sources_kind_dates_and_place_as_stated():
    record = next(r for r in btp_records() if "White Topping Work at New Diagonal Road" in r.title)
    assert record.title == "Department Work: White Topping Work at New Diagonal Road, Jayanagar"
    assert record.summary == "White Topping Work at New Diagonal Road, Jayanagar near 7th Main Road, Byrasandra"
    structured = record.structured
    assert structured.event_type == EventType.ROAD_WORKS.value and structured.category == "Department Work"
    assert structured.start == datetime(2026, 10, 7, 0, 0, tzinfo=IST)
    assert structured.end == datetime(2027, 1, 4, 23, 59, 59, tzinfo=IST)
    assert structured.stated_period == "Start : 00:00 Hrs 07-10-2026 and End : 04-01-2027"
    assert [place.name for place in structured.locations] == ["7th Main Road, Byrasandra"]
    # The line itself, as published, is the evidence and the item's identity.
    assert record.raw["line"].startswith("Department Work : White Topping Work")
    assert record.external_id == "496f17fb0890558e83ee4a9e" and record.url == "https://btp.karnataka.gov.in/en"


def test_the_administrative_tail_of_an_address_is_not_a_place():
    assert place_part(
        "7th Main Road, Byrasandra, Bengaluru South City Corporation, Bengaluru, Bengaluru Urban, "
        "Karnataka, 560011, India"
    ) == "7th Main Road, Byrasandra"
    assert place_part("Kalidasa Road, Gandhinagar, Bengaluru Central City Corporation, Bengaluru") == "Kalidasa Road, Gandhinagar"
    assert place_part("None") is None


def test_items_that_state_neither_a_description_nor_a_place_are_not_records():
    lines = parse_items(BTP_PAGE)
    dropped = [line for line in lines if btp_record(line, NOW) is None]
    assert len(dropped) == 13 and all(line.startswith(("Department Work : None near None", "Private Event : None near None", "Public Event : None near None")) for line in dropped)


def test_a_works_item_is_located_at_the_locality_it_names_and_keeps_the_address_unresolved():
    record = next(r for r in btp_records() if "White Topping Work at New Diagonal Road" in r.title)
    event = event_of(record, BENGALURU, resolver_for(BENGALURU))
    assert event.event_type is EventType.ROAD_WORKS and event.city == "Bengaluru"
    assert event.detection.location_class is LocationClass.APPROXIMATE
    assert event.detection.location.place_name == "Jayanagar"
    assert event.detection.location.found_in == "title"
    # "7th Main Road" is many roads in Bengaluru: known, not one spot.
    address = next(p for p in event.detection.affected_locations if p.name == "7th Main Road, Byrasandra")
    assert address.resolution is LocationClass.UNRESOLVED
    assert event.start_time == datetime(2026, 10, 7, 0, 0, tzinfo=IST)
    assert event.detection.stated_period == "Start : 00:00 Hrs 07-10-2026 and End : 04-01-2027"


def test_an_address_is_placed_by_its_most_exact_known_part():
    record = next(r for r in btp_records() if "Freedom Park" in r.title)
    event = event_of(record, BENGALURU, resolver_for(BENGALURU))
    assert event.event_type is EventType.SPECIAL_EVENT
    # Freedom Park is more than one OpenStreetMap feature (not one spot); the
    # item's "near" address starts with Kalidasa Road, which is one.
    assert event.detection.location.place_name == "Kalidasa Road"
    assert event.detection.location_class is LocationClass.APPROXIMATE


def test_a_private_event_at_a_mall_is_a_public_event_at_the_venue():
    record = next(r for r in btp_records() if "Orion Mall" in r.title)
    event = event_of(record, BENGALURU, resolver_for(BENGALURU))
    assert event.event_type is EventType.SPECIAL_EVENT
    assert event.detection.source_category == "Private Event"
    assert event.detection.location.place_name == "Orion Mall"


def test_the_bengaluru_connector_keeps_current_and_imminent_items_and_reports_what_it_saw():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "btp.karnataka.gov.in"
        return httpx.Response(200, text=BTP_PAGE, headers={"content-type": "text/html"})

    connector = BengaluruTrafficPoliceConnector(
        bengaluru_source(scheduled=False), "test", max_records=30,
        client=httpx.Client(transport=httpx.MockTransport(handler)), clock=lambda: NOW,
    )  # fmt: skip
    records = connector.fetch()
    assert len(connector.observed_ids) == 26
    # Items up to a year ahead are kept since 21 October 2026 (a week before).
    assert all(record.structured.start <= NOW + timedelta(days=365) for record in records)
    assert any("Palace Grounds, Bellary Road" in record.title for record in records)
    assert any("White Topping Work at New Diagonal Road" in record.title for record in records)
    # Soonest to start first.
    starts = [record.structured.start for record in records]
    assert starts == sorted(starts)


def test_an_unknown_line_form_is_skipped_and_a_page_without_the_list_is_an_error():
    assert btp_record("Something else entirely", NOW) is None
    with pytest.raises(ConnectorError, match="Upcoming Events"):
        parse_items("<html><body>nothing here</body></html>")


# --- the shared no-geometry path -----------------------------------------------


def test_a_structured_record_with_the_sources_own_geometry_is_never_relocated_by_name():
    structured = SourceEvent(
        event_type="ROAD_WORKS",
        geometry={"type": "Point", "coordinates": [72.84, 19.02]},
        locations=[SourceLocation(name="Dadar", kind="area")],
    )
    record = RawSourceRecord(
        source_id="test", external_id="1", url=None, title="Works at Ghatkopar", summary=None,
        content_text=None, categories=[], published_at=NOW, retrieved_at=NOW, raw={},
        content_hash="0" * 64, structured=structured,
    )  # fmt: skip
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event.detection.location_class is LocationClass.SOURCE_PROVIDED
    assert tuple(event.geometry.coordinates) == (72.84, 19.02)
    assert event.detection.location.method == "source_provided"


# --- where the point goes (9 October 2026 fix after the user's question) -------


def test_the_sources_own_address_outranks_a_place_in_the_title():
    record = next(r for r in btp_records() if "5TH MAIN CHAMARAJPET" in r.title)
    event = event_of(record, BENGALURU, resolver_for(BENGALURU))
    # The title names the ward (Chamarajpet); the item's "near" address names
    # Puttanna Chetty Road, which is the place the source gives for the work.
    assert event.detection.location.place_name == "Puttanna Chetty Road"
    assert event.detection.location.found_in == "source"
    assert event.detection.location_class is LocationClass.APPROXIMATE


def test_the_pdf_file_name_places_a_notice_only_when_nothing_else_does():
    assert file_name_place("GetPublicNotice/823226/202608240000_823226_Notification No 189, Ghatkopar Div 1.pdf") == "Notification No 189, Ghatkopar Div"
    assert file_name_place("GetPublicNotice/822797/202607200000_822797_40. Dadar - J. Bhatankar marg closed Notiication (1).pdf") == "Dadar J. Bhatankar marg closed Notiication"
    assert file_name_place("GetPublicNotice/823555/202609000000_823555_Notification No 195 compressed.pdf") == "Notification No 195"
    assert file_name_place(None) is None

    record = mumbai_record("189/2026")
    [fallback] = [place for place in record.structured.locations if place.fallback]
    assert fallback.kind == "file name"
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event.detection.location.place_name == "Ghatkopar"
    assert event.detection.location_class is LocationClass.APPROXIMATE
    assert any(place.kind == "file name" for place in event.detection.affected_locations)

    # A file name with no known place leaves the event unlocated and is not listed.
    record = mumbai_record("209/2026")
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event.geometry is None and event.detection.affected_locations == []
    assert "DocScanner" not in " ".join(event.detection.places)


def test_a_road_named_in_the_english_summary_outranks_the_file_name():
    record = mumbai_record("168/2026")
    event = event_of(record, MUMBAI, resolver_for(MUMBAI))
    assert event.detection.location.place_name == "Mumbai Central"


def test_a_stored_row_is_re_read_with_the_current_rules_without_altering_the_evidence():
    record = mumbai_record("189/2026")
    # What an earlier version of the connector stored: the row, and its
    # reading at the time (here without the file-name hint).
    stored_raw = dict(record.raw)
    stale = record.structured.model_copy(
        update={"locations": [p for p in record.structured.locations if not p.fallback]}
    )
    stored_raw["source_event"] = stale.model_dump(mode="json")
    rebuilt = mumbai_rebuild(stored_raw)
    assert rebuilt == record.structured
    assert any(place.fallback for place in rebuilt.locations)
    assert stored_raw["source_event"] == stale.model_dump(mode="json")  # the evidence is as it was

    parking = mumbai_record("207/2026")
    assert mumbai_rebuild(parking.raw) is None

    item = next(r for r in btp_records() if "Freedom Park" in r.title)
    assert btp_rebuild(item.raw) == item.structured
    assert btp_rebuild({}) is None
