"""The API with every connected RSS source ingesting through the same pipeline."""

from tests.support import FakeConnector

# source id -> (articles stored, events created) from each fixture feed
EXPECTED = {
    "telangana-today": (6, 3),
    "the-hindu": (5, 2),
    "deccan-chronicle": (5, 2),
    "newsmeter": (5, 2),
}
TOTAL_EVENTS = sum(events for _, events in EXPECTED.values())
SOURCE_NAMES = {
    "telangana-today": "Telangana Today",
    "the-hindu": "The Hindu",
    "deccan-chronicle": "Deccan Chronicle",
    "newsmeter": "NewsMeter",
}


def ingest_all(client):
    response = client.post("/api/ingestion/run")
    assert response.status_code == 200
    return {result["source_id"]: result for result in response.json()["results"]}


def test_one_run_ingests_every_connected_source_and_nothing_else(news_client):
    results = ingest_all(news_client)
    assert sorted(results) == sorted(EXPECTED)
    for source_id, (articles, events) in EXPECTED.items():
        assert results[source_id]["status"] == "ok"
        assert results[source_id]["new_artifacts"] == articles
        assert results[source_id]["events_created"] == events


def test_events_from_all_sources_are_returned_with_their_source(news_client):
    ingest_all(news_client)
    events = news_client.get("/api/events?view=validation").json()["items"]
    assert len(events) == TOTAL_EVENTS

    assert {event["source_id"]: event["source"]["source_name"] for event in events} == SOURCE_NAMES
    for event in events:
        assert event["status"] == "VALIDATION_REQUIRED"
        assert event["source"]["source_type"] == "RSS"
        assert event["source_reference"].startswith("https://")
        assert event["evidence"]["url"] == event["source_reference"]
        assert event["evidence"]["retrieved_at"]


def test_events_can_be_filtered_by_source(news_client):
    ingest_all(news_client)
    for source_id, (_, expected_events) in EXPECTED.items():
        body = news_client.get("/api/events", params={"view": "validation", "source_id": source_id}).json()
        assert body["total"] == expected_events
        assert {event["source_id"] for event in body["items"]} == {source_id}
    assert news_client.get("/api/events", params={"view": "validation", "source_id": "unknown"}).json()["total"] == 0


def test_each_connected_source_reports_its_own_health_and_counts(news_client):
    ingest_all(news_client)
    sources = {source["source_id"]: source for source in news_client.get("/api/sources").json()}
    for source_id, (articles, events) in EXPECTED.items():
        source = sources[source_id]
        assert source["source_type"] == "RSS"
        assert source["integration_status"] == "CONNECTED"
        assert source["active"] is True
        assert source["last_success_at"] is not None
        assert source["last_failure_at"] is None
        assert source["artifact_count"] == articles
        assert source["event_count"] == events


def test_repeated_polling_adds_nothing_for_any_source(news_client):
    ingest_all(news_client)
    second = ingest_all(news_client)
    for source_id in EXPECTED:
        assert second[source_id]["new_artifacts"] == 0
        assert second[source_id]["events_created"] == 0
        assert second[source_id]["duplicates"] == second[source_id]["fetched"]
    assert news_client.get("/api/events?view=validation").json()["total"] == TOTAL_EVENTS


def test_one_failing_source_does_not_stop_the_others(news_client):
    news_client.app.state.ingestion_service.connector_factories["the-hindu"] = lambda: FakeConnector(
        [], error="feed unreachable"
    )
    results = ingest_all(news_client)

    assert results["the-hindu"]["status"] == "failed"
    assert results["the-hindu"]["error"] == "feed unreachable"
    for source_id, (_, events) in EXPECTED.items():
        if source_id != "the-hindu":
            assert results[source_id]["status"] == "ok"
            assert results[source_id]["events_created"] == events

    sources = {source["source_id"]: source for source in news_client.get("/api/sources").json()}
    assert sources["the-hindu"]["last_failure_at"] is not None
    assert sources["the-hindu"]["last_error"] == "feed unreachable"
    assert sources["the-hindu"]["artifact_count"] == 0
    assert sources["telangana-today"]["last_failure_at"] is None


def test_single_source_can_be_ingested_on_its_own(news_client):
    response = news_client.post("/api/ingestion/run", params={"source_id": "deccan-chronicle"})
    assert [result["source_id"] for result in response.json()["results"]] == ["deccan-chronicle"]
    events = news_client.get("/api/events?view=validation").json()["items"]
    assert {event["source_id"] for event in events} == {"deccan-chronicle"}
