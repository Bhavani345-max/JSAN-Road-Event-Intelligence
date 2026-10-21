"""Scottish Road Works Register disruptions export (21 October 2026), on real
rows of the export saved that day. No test reaches the SRWR."""

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import String, select

from app.models import Event, EventVersion, Source, SourceArtifact
from app.repositories.ingestion_store import SqlIngestionStore
from app.repositories.sources import SourceRepository
from connectors.base import ConnectorError
from connectors.official import srwr
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import CommercialUse, IntegrationStatus, SourceClass
from services.extraction import KeywordClassifier
from services.ingestion import run_ingestion

FIXTURE = Path(__file__).parents[1] / "fixtures" / "srwr_current_activities_2026-10-21.csv"
CSV_TEXT = FIXTURE.read_text(encoding="utf-8")
ROWS = list(csv.DictReader(io.StringIO(CSV_TEXT, newline="")))
NOW = datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc)
# The listing the export's API gave on 21 October 2026.
LISTING = {
    "files": [
        {"name": f"SRWRDisruptionsExport202610{day}.zip", "file_size": "6.9 MB", "date": f"{day}/10/2026"}
        for day in ("21", "20", "19", "18", "17", "16", "15")
    ]
}
SIGNED = (
    "https://srwrexport.blob.core.windows.net/prod-disruptions-export/"
    "SRWRDisruptionsExport20261021.zip?sig=x"
)


def row(external_id: str) -> dict:
    return next(r for r in ROWS if srwr.external_id_of(r) == external_id)


def export_zip(csv_text: str = CSV_TEXT, member: str = srwr.MEMBER) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, csv_text)
        archive.writestr("CompletedActivities.csv", "Version\r\n")
    return buffer.getvalue()


def mock_client(archive: bytes, *, listing=LISTING, link=SIGNED, asked: list | None = None) -> httpx.Client:
    def answer(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if asked is not None:
            asked.append(url)
        if url == srwr.ENDPOINT:
            return httpx.Response(200, json=listing)
        if url.startswith(srwr.FILE_ENDPOINT):
            return httpx.Response(200, json={"url": link})
        if url == link:
            return httpx.Response(200, content=archive)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(answer))


def connector(client: httpx.Client) -> srwr.SrwrDisruptionsConnector:
    return srwr.SrwrDisruptionsConnector(
        srwr.srwr_source(scheduled=True), "ua", client=client, clock=lambda: NOW
    )


def test_type_comes_from_the_traffic_management_and_the_category():
    expected = {
        "CE010-S000000004534#1": EventType.PLANNED_ROAD_CLOSURE,  # Road Restriction / Road Closure
        "XQ001-NW/2025/38716/TRO1#1": EventType.PLANNED_ROAD_CLOSURE,  # Temporary Traffic Restriction
        "TE003-VM/CIP/385249#9": EventType.PLANNED_ROAD_CLOSURE,  # Remedial Other / Road Closure
        "AB001-BM-A00571-DM#1": EventType.EMERGENCY_ROAD_CLOSURE,  # Emergency / Road Closure
        "XR001-S45849#1": EventType.EMERGENCY_ROAD_CLOSURE,  # Emergency / Slip Closure
        "FA001-04455/ROADDES/DF#1": EventType.LANE_RESTRICTION,  # Lane Closure
        "RN002-LS02072401#1": EventType.LANE_RESTRICTION,  # Road Narrowing (Two Way Working)
        "CE001-L506#1": EventType.LANE_RESTRICTION,  # Contraflow
        "XS001-SEU/2026/26326B#1": EventType.LANE_RESTRICTION,  # Hard Shoulder Closure
        "AB001-SUBSID18-19-001#1": EventType.ROAD_WORKS,  # Emergency works under traffic lights
        "RN001-CITY-DEAL/AMIDS/002#1": EventType.ROAD_WORKS,  # Major / Give and Take
        "SW515-MDD/MOR/0150E/BM4#1": EventType.ROAD_WORKS,  # Stop/Go Boards
        "CG001-S000000053781#2": EventType.ROAD_WORKS,  # Diversionary Works / not yet known
        "MO002-E-23-G971-M-0139525#1": EventType.ROAD_WORKS,  # Priority System
        "SG025-MREP-SCN2695/01/DL#1": EventType.ROAD_WORKS,  # status Potential, kept in its words
        "AN001-L2446#1": EventType.SPECIAL_EVENT,  # Event / Road Closure
        # Neither works nor a closure nor a lane restriction: no type, for the reviewer.
        "XQ001-NW/2026/#1": None,  # Road Restriction / Convoy Working
        "EA001-ROC/24-25/115#1": None,  # Permission / Portable Traffic Lights
    }
    found = {}
    for item in ROWS:
        record = srwr.to_record(item, NOW)
        found[srwr.external_id_of(item)] = record.structured.event_type if record else "not taken"
    assert {key: found[key] for key in expected} == {
        key: (value.value if value else None) for key, value in expected.items()
    }
    # The carriageway is untouched: not a road event.
    assert found["NL001-L1219#1"] == "not taken"  # No Obstruction On C/W Or F/W
    assert found["SL001-L809#1"] == "not taken"  # Works Entirely On The Footway
    assert found["CE006-L3423#1"] == "not taken"  # an event on the footway
    assert len(found) == len(ROWS) == 21


def test_every_value_is_the_exports_own():
    item = row("CE010-S000000004534#1")
    record = srwr.to_record(item, NOW)
    event = record.structured
    assert event.geometry == {"type": "Point", "coordinates": [-3.18829, 55.9517]}
    assert (item["Latitude"], item["Longitude"]) == ("55.9517", "-3.18829")
    assert event.start == datetime(2018, 7, 2, 21, 0, tzinfo=timezone.utc)
    assert event.end == datetime(2026, 12, 31, 0, 0, tzinfo=timezone.utc)
    assert (event.severity, event.status) == ("Road Closure", "In Progress")
    assert event.category == "Road Restriction / Road Closure"
    assert event.affected_road == "North Bridge" and event.direction is None
    assert event.locations[0].name == "North Bridge, Old Town, Edinburgh"
    assert event.locations[0].reference == "7902031" and event.locations[0].closure == "Road Closure"
    assert event.attribution == srwr.ATTRIBUTION and "Open Government Licence v3.0" in event.attribution
    assert record.title == "Road Closure: North Bridge, Old Town, Edinburgh"
    assert record.summary.startswith(
        "Full width, footways and carriageway from High Street to Princes Street. North"
    )
    assert not record.summary.startswith('"') and '"' not in record.summary[-2:]
    assert record.published_at == datetime(2025, 10, 30, 14, 48, 56, 22000, tzinfo=timezone.utc)
    assert record.external_id == "CE010-S000000004534#1" and record.url == srwr.SOURCE_URL
    # The row is the evidence, British National Grid shape included.
    assert record.raw["item"] == item and record.raw["item"]["GeometryFull"].startswith("LINESTRING (325851")


def test_a_run_downloads_the_newest_export_and_keeps_what_has_not_ended():
    asked = []
    source = connector(mock_client(export_zip(), asked=asked))
    records = source.fetch()
    assert asked == [srwr.ENDPOINT, f"{srwr.FILE_ENDPOINT}SRWRDisruptionsExport20261021.zip/", SIGNED]
    assert source.export_name == "SRWRDisruptionsExport20261021.zip"
    kept = {record.external_id for record in records}
    # 21 rows: 3 leave the carriageway untouched; 1 ended on 20 October.
    assert len(records) == 17
    assert "TE003-VM/CIP/385249#9" not in kept and "TE003-VM/CIP/385249#9" in source.observed_ids
    assert source.observed_ids == kept | {"TE003-VM/CIP/385249#9"}
    assert all(r.structured.geometry and r.structured.start and r.structured.end for r in records)
    # The signed link is a credential: never kept on a record.
    assert all("sig=" not in json.dumps(r.raw, default=str) and r.url == srwr.SOURCE_URL for r in records)


def test_a_shape_longer_than_the_csv_default_field_limit_is_read():
    item = dict(row("FA001-04455/ROADDES/DF#1"))
    item["GeometryFull"] = "LINESTRING (" + ", ".join(["290000.5 680000.5"] * 20000) + ")"
    assert len(item["GeometryFull"]) > 131072
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(ROWS[0]), lineterminator="\r\n")
    writer.writeheader()
    writer.writerow(item)
    before = csv.field_size_limit()
    records = connector(mock_client(export_zip(buffer.getvalue()))).fetch()
    assert [record.external_id for record in records] == ["FA001-04455/ROADDES/DF#1"]
    assert csv.field_size_limit() == before


@pytest.mark.parametrize(
    "archive, listing, link, message",
    [
        (export_zip(), {"files": []}, SIGNED, "lists no disruptions export"),
        (export_zip(member="Other.csv"), LISTING, SIGNED, "holds no CurrentActivities.csv"),
        (b"not a zip", LISTING, SIGNED, "could not be read"),
        (export_zip(), LISTING, "", "gave no download link"),
        (export_zip("Version,Category\r\n00,Major\r\n"), LISTING, SIGNED, "no ActivityReference column"),
    ],
)
def test_an_unexpected_export_fails_the_run(archive, listing, link, message):
    with pytest.raises(ConnectorError, match=message):
        connector(mock_client(archive, listing=listing, link=link or "http://x")).fetch()


def test_the_definition():
    source = srwr.srwr_source(scheduled=False)
    assert (source.source_id, source.city, source.country, source.region) == (
        "scotland-srwr-disruptions", "united-kingdom", "GB", "Scotland",
    )  # fmt: skip
    assert source.integration_status is IntegrationStatus.CONNECTED and source.active is False
    assert srwr.srwr_source(scheduled=True).active is True
    assert source.source_tier == 1 and source.source_class is SourceClass.GOVERNMENT_OPEN_DATA
    assert source.commercial_use is CommercialUse.PERMITTED_WITH_ATTRIBUTION
    assert source.polling_frequency_minutes == 24 * 60 and source.provides_geometry
    limits = {
        column.name: column.type.length
        for column in Source.__table__.columns
        if isinstance(column.type, String) and column.type.length
    }
    values = source.model_dump(mode="json")
    too_long = {
        name: len(str(values[name]))
        for name, limit in limits.items()
        if values.get(name) is not None and len(str(values[name])) > limit
    }
    assert too_long == {}


def ingest(session, city):
    return run_ingestion(
        connector(mock_client(export_zip())),
        KeywordClassifier.from_file(),
        SqlIngestionStore(session),
        None,
        city,
    )


def test_events_through_the_pipeline_fit_their_columns_and_a_second_run_adds_nothing(session):
    source = srwr.srwr_source(scheduled=True)
    SourceRepository(session).sync_registry([source])
    session.commit()
    city = get_city("united-kingdom")
    first = ingest(session, city)
    session.commit()
    events = list(session.scalars(select(Event).where(Event.source_id == source.source_id)))
    assert first.events_created == len(events) == 17
    assert all(event.geometry and event.start_time and event.end_time for event in events)
    too_long = []
    for model in (Event, SourceArtifact, EventVersion):
        limits = {
            column.name: column.type.length
            for column in model.__table__.columns
            if isinstance(column.type, String) and column.type.length
        }
        for stored in session.scalars(select(model)).unique():
            for name, limit in limits.items():
                value = getattr(stored, name)
                if value is not None and len(str(value)) > limit:
                    too_long.append((model.__tablename__, name, len(str(value)), limit))
    assert not too_long, too_long
    second = ingest(session, city)
    session.commit()
    assert (second.events_created, second.revised, second.duplicates) == (0, 0, 17)
