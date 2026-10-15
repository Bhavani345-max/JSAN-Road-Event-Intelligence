"""The application holds real source data only: no seeded events, no invented values."""

from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.telangana_today import TELANGANA_TODAY
from tests.support import FakeConnector, iiit_junction_article, khajaguda_article

UNKNOWN_UNTIL_ESTABLISHED = ("start_time", "end_time", "severity", "direction", "geometry", "confidence")


def ingest_all(client):
    assert client.post("/api/ingestion/run").status_code == 200


# --- No demo data ---------------------------------------------------------------


def test_no_demo_events_or_demo_source_exist(news_client):
    assert news_client.get("/api/events?view=validation&include_hidden=true").json()["total"] == 0
    ingest_all(news_client)

    events = news_client.get("/api/events", params={"view": "validation", "include_hidden": "true", "limit": 500}).json()["items"]
    assert events
    for event in events:
        assert "is_demo" not in event
        assert not event["event_id"].startswith("DEMO")
        assert event["evidence"] is not None  # every event has stored source evidence
    assert all(s["source_id"] != "rei-demo" for s in news_client.get("/api/sources").json())
    # The old demo filter is gone rather than hidden.
    assert news_client.get("/api/events", params={"view": "validation", "include_hidden": "true", "is_demo": "true"}).json()["total"] == len(events)


def test_no_event_carries_an_invented_value(news_client):
    ingest_all(news_client)
    for event in news_client.get("/api/events", params={"view": "validation", "include_hidden": "true", "limit": 500}).json()["items"]:
        assert event["status"] == "VALIDATION_REQUIRED"
        for name in UNKNOWN_UNTIL_ESTABLISHED:
            assert event[name] is None, f"{event['event_id']}: {name}"
        # A road is recorded only if the article's own text contains it.
        for road in event["detection"]["road_mentions"]:
            assert road.lower() in (event["title"] + " " + (event["description"] or "")).lower()


# --- Source registry ------------------------------------------------------------


def test_registry_separates_connected_from_researched_sources(news_client):
    sources = news_client.get("/api/sources").json()
    connected = [s for s in sources if s["integration_status"] == "CONNECTED"]
    others = [s for s in sources if s["integration_status"] != "CONNECTED"]

    assert {s["source_id"] for s in connected} >= {
        "telangana-today", "the-hindu", "deccan-chronicle", "newsmeter",
    }
    # Siasat's terms forbid automated access (decision 0024), and The Hans India
    # was removed (decision 0026): listed, not connected.
    assert not {"siasat", "siasat-mumbai", "the-hans-india"} & {s["source_id"] for s in connected}
    assert len(others) >= 15
    for source in others:
        # A researched source is never polled and is never presented as active.
        assert source["active"] is False, source["source_id"]
        assert source["last_poll_at"] is None
        assert source["artifact_count"] == 0 and source["event_count"] == 0
        assert source["integration_status"] in {
            "DISCOVERED", "NOT_USABLE", "REQUIRES_ACCESS", "MANUAL_ONLY",
            # Added 6 October 2026 with the source research.
            "VALIDATED", "READY_FOR_INTEGRATION", "TERMS_REVIEW_REQUIRED", "BLOCKED",
        }
        assert source["notes"]


def test_registry_can_be_filtered_by_integration_status(news_client):
    connected = news_client.get("/api/sources", params={"integration_status": "CONNECTED"}).json()
    assert all(s["integration_status"] == "CONNECTED" for s in connected)
    manual = news_client.get("/api/sources", params={"integration_status": "MANUAL_ONLY"}).json()
    assert "hyderabad-traffic-police" in {s["source_id"] for s in manual}
    assert news_client.get("/api/sources", params={"integration_status": "NOPE"}).status_code == 422


def test_registry_records_the_descriptive_fields(news_client):
    source = news_client.get("/api/sources/telangana-today").json()
    assert source["organization"] == "Telangana Today"
    assert source["authority_type"] == "NEWS_MEDIA"
    assert source["source_tier"] == 4
    assert source["source_url"] == "https://telanganatoday.com/hyderabad"
    assert source["endpoint"] == "https://telanganatoday.com/hyderabad/feed"
    assert source["access_method"]
    assert source["language"] == "en"
    assert source["parser_type"] == "rss"
    assert source["terms_reviewed"] is False
    assert "TRAFFIC_DIVERSION" in source["events_supported"]
    assert source["evidence_retention"]

    police = news_client.get("/api/sources/hyderabad-traffic-police").json()
    assert police["source_tier"] == 1 and police["authority_type"] == "POLICE"
    assert police["endpoint"] is None  # no machine-readable address exists

    # A commercial provider is not given a tier until it is an approved source.
    assert news_client.get("/api/sources/tomtom-traffic-incidents").json()["source_tier"] is None


def test_a_run_never_fetches_an_unconnected_source(news_client):
    results = news_client.post("/api/ingestion/run").json()["results"]
    fetched = {result["source_id"] for result in results}
    assert "hyderabad-traffic-police" not in fetched
    assert "ndma-sachet-telangana" not in fetched  # has a working feed, still not connected
    assert "times-of-india-hyderabad" not in fetched


# --- Search across event, source and evidence ------------------------------------


def search(client, text):
    body = client.get("/api/events", params={"view": "validation", "include_hidden": "true", "q": text}).json()
    return {event["title"] for event in body["items"]}, body["total"]


def ingest_real_cases(client):
    """Ingest only the two real regression articles: Khajaguda and IIIT Junction."""
    factories = client.app.state.ingestion_service.connector_factories
    factories["telangana-today"] = lambda: FakeConnector(
        [khajaguda_article()], source=TELANGANA_TODAY
    )
    factories["deccan-chronicle"] = lambda: FakeConnector(
        [iiit_junction_article()], source=DECCAN_CHRONICLE
    )
    for source_id in ("telangana-today", "deccan-chronicle"):
        assert client.post("/api/ingestion/run", params={"source_id": source_id}).status_code == 200
    return client


KHAJAGUDA = "Traffic diversions at Khajaguda junction for 60 days from September 26"
IIIT = "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works"


def test_search_finds_events_by_title_road_and_source(news_client):
    client = ingest_real_cases(news_client)
    assert search(client, "khajaguda") == ({KHAJAGUDA}, 1)
    assert search(client, "IIIT Junction") == ({IIIT}, 1)
    assert search(client, "Biodiversity Junction") == ({KHAJAGUDA}, 1)  # road mention
    assert search(client, "deccan chronicle") == ({IIIT}, 1)  # source name
    assert search(client, "telangana today")[1] == 1


def test_search_reaches_the_summary_and_the_article_text(news_client):
    client = ingest_real_cases(news_client)
    # "Gachibowli" is in neither headline: it is in the summaries and bodies.
    assert search(client, "gachibowli") == ({KHAJAGUDA, IIIT}, 2)
    # Only in the article body of each.
    assert search(client, "DLF Gate") == ({IIIT}, 1)
    assert search(client, "Timberlake Colony") == ({KHAJAGUDA}, 1)
    assert search(client, "radisson") == ({IIIT}, 1)


def test_search_requires_every_word_and_combines_with_filters(news_client):
    client = ingest_real_cases(news_client)
    assert search(client, "gachibowli pipeline") == ({KHAJAGUDA}, 1)
    assert search(client, "gachibowli necklace")[1] == 0
    assert search(client, "no-such-place")[1] == 0
    assert search(client, "   ")[1] == 2  # blank search is no search

    body = client.get("/api/events", params={"view": "validation", "include_hidden": "true", "q": "gachibowli", "source_id": "deccan-chronicle"}).json()
    assert [event["title"] for event in body["items"]] == [IIIT]
    paged = client.get("/api/events", params={"view": "validation", "include_hidden": "true", "q": "gachibowli", "limit": 1}).json()
    assert paged["total"] == 2 and len(paged["items"]) == 1
