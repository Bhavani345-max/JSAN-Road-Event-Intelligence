"""Location, stated dates and re-derivation, with the real articles and the real gazetteer."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.models import Event, SourceArtifact
from app.repositories.events import EventRepository
from app.repositories.sources import SourceRepository
from app.services.reprocess_service import record_from_artifact, reprocess_stored_evidence
from connectors.base import ConnectorError
from connectors.html import parse_article_page
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.telangana_today import TELANGANA_TODAY
from services.extraction import KeywordClassifier, build_event_from_article
from services.geo_resolution import default_resolver
from services.ingestion import event_for_record
from tests.support import RETRIEVED_AT, FakeConnector, iiit_junction_article, khajaguda_article


def no_place_article():
    """A real kind of false lead: traffic words, Hyderabad, but no place in the city."""
    title = "Holidays for Hyderabad schools: visit this car-free hill station"
    summary = "Spend a holiday in the hills without seeing traffic jams."
    body = "Matheran is a hill station where motor vehicles are not allowed."
    return khajaguda_article().model_copy(
        update={
            "external_id": "https://news.example.com/hill-station",
            "url": "https://news.example.com/hill-station",
            "title": title,
            "summary": summary,
            "content_text": body,
            "categories": ["Hyderabad"],
            "raw": {
                "title": title,
                "summary_html": summary,
                "content_html": body,
                "categories": ["Hyderabad"],
            },
        }
    )


@pytest.fixture
def located_client(engine, session):
    """The API as it runs for real, gazetteer included, fed three known articles."""
    SourceRepository(session).sync_registry([TELANGANA_TODAY, DECCAN_CHRONICLE])
    session.commit()
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False,
    )
    app = create_app(settings, engine=engine)
    app.state.ingestion_service.connector_factories = {
        "telangana-today": lambda: FakeConnector(
            [khajaguda_article(), no_place_article()], source=TELANGANA_TODAY
        ),
        "deccan-chronicle": lambda: FakeConnector([iiit_junction_article()], source=DECCAN_CHRONICLE),
    }
    with TestClient(app) as client:
        assert client.post("/api/ingestion/run").status_code == 200
        yield client


def events_by_title(client):
    items = client.get("/api/events?view=validation", params={"limit": 500}).json()["items"]
    return {item["title"]: item for item in items}


def test_an_event_is_located_by_the_place_its_article_names(located_client):
    event = events_by_title(located_client)[
        "Traffic diversions at Khajaguda junction for 60 days from September 26"
    ]
    assert event["geometry"]["type"] == "Point"
    location = event["detection"]["location"]
    assert location["method"] == "named_place"
    assert location["mention"] == "Khajaguda junction"
    assert location["reference"].startswith("OpenStreetMap ")
    # Located and dated, but still only a lead for a reviewer.
    assert event["status"] == "VALIDATION_REQUIRED"
    assert event["confidence"] is None and event["severity"] is None


def test_stated_dates_are_served_with_the_words_they_came_from(located_client):
    event = events_by_title(located_client)[
        "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works"
    ]
    assert event["start_time"].startswith("2026-06-30T18:30:00")  # 1 July, 00:00 IST
    assert event["end_time"].startswith("2026-09-28T18:29:59")  # 28 September, 23:59 IST
    assert event["detection"]["stated_period"].startswith("for a period of 90 days")
    assert event["detection"]["attributed_to"] == ["Cyberabad Police"]


def test_an_article_naming_no_place_is_kept_as_evidence_but_is_not_an_event(located_client, session):
    assert "Holidays for Hyderabad schools: visit this car-free hill station" not in events_by_title(
        located_client
    )
    stored = session.scalars(
        select(SourceArtifact).where(SourceArtifact.url == "https://news.example.com/hill-station")
    ).one()
    assert stored.classification == "RELEVANT_TRAFFIC_ARTICLE"


def test_an_ambiguous_place_name_makes_an_event_but_does_not_locate_it():
    """"Srinagar Colony" is a real name, but there is more than one in the city."""
    record = khajaguda_article().model_copy(
        update={
            "title": "Srinagar Colony Road Dug Up Just 6 Days After Relaying",
            "summary": "HYDERABAD: A road in Srinagar Colony was dug up after the road work.",
            "content_text": None,
        }
    )
    event = event_for_record(
        record, KeywordClassifier.from_file().classify(record), default_resolver(), now=RETRIEVED_AT
    )
    assert event is not None
    assert event.detection.places == ["Srinagar Colony"]
    assert event.geometry is None and event.detection.location is None


def test_a_located_event_still_cannot_be_approved_without_review(located_client):
    event = events_by_title(located_client)[
        "Traffic diversions at Khajaguda junction for 60 days from September 26"
    ]
    response = located_client.post(
        f"/api/events/{event['event_id']}/status", json={"status": "ACTIVE"}
    )
    assert response.status_code == 409


# --- re-deriving events from stored evidence ----------------------------------


class _AnyPlace:
    """Stands in for a gazetteer that knows the place every article names."""

    def find_places(self, **texts):
        return default_resolver().find_places(title="Tolichowki", summary=None, body=None)

    def __getattr__(self, name):
        # Placing (services/geo_resolution/placement.py) uses the real place list.
        return getattr(default_resolver(), name)



def test_reprocessing_rejects_what_the_rules_no_longer_support_and_keeps_history(
    located_client, session
):
    classifier, resolver = KeywordClassifier.from_file(), default_resolver()
    # Nothing changes when the rules have not changed.
    unchanged = reprocess_stored_evidence(session, classifier, resolver)
    assert (unchanged.created, unchanged.updated, unchanged.rejected) == (0, 0, 0)

    # An event created under looser rules, from an article that names no place.
    article = session.scalars(
        select(SourceArtifact).where(SourceArtifact.url == "https://news.example.com/hill-station")
    ).one()
    record = record_from_artifact(article)
    assert record.title.startswith("Holidays") and record.categories == ["Hyderabad"]
    stale = build_event_from_article(record, classifier.classify(record), now=RETRIEVED_AT)
    EventRepository(session).add(
        stale, artifact_id=article.artifact_id, change_reason="old rules", changed_by="ingestion"
    )
    session.commit()

    result = reprocess_stored_evidence(session, classifier, resolver)
    assert (result.created, result.updated, result.rejected) == (0, 0, 1)
    row = session.get(Event, stale.event_id)
    assert row.status == "REJECTED" and row.version == 2
    assert [version.changed_by for version in row.versions] == ["ingestion", "reprocessing"]
    assert "No longer detected" in row.versions[-1].change_reason

    # If later rules detect it again, reprocessing undoes its own rejection.
    looser = KeywordClassifier.from_file()
    restored = reprocess_stored_evidence(session, looser, resolver=_AnyPlace())
    assert restored.restored == 1
    session.refresh(row)
    assert row.status == "VALIDATION_REQUIRED" and row.version == 3
    assert "Detected again" in row.versions[-1].change_reason


def test_reprocessing_never_overrides_a_reviewers_decision(located_client, session):
    event = events_by_title(located_client)[
        "Traffic diversions at Khajaguda junction for 60 days from September 26"
    ]
    located_client.post(f"/api/events/{event['event_id']}/status", json={"status": "QC_PENDING"})
    row = session.get(Event, event["event_id"])
    session.refresh(row)
    row.geometry = None  # as if it had been derived before locations existed
    session.commit()

    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert result.updated == 0
    session.refresh(row)
    assert row.status == "QC_PENDING" and row.geometry is None


def test_reprocessing_creates_events_the_old_rules_missed(located_client, session):
    event = events_by_title(located_client)[
        "Traffic diversions at Khajaguda junction for 60 days from September 26"
    ]
    session.delete(session.get(Event, event["event_id"]))
    session.commit()

    result = reprocess_stored_evidence(session, KeywordClassifier.from_file(), default_resolver())
    assert result.created == 1
    row = session.get(Event, event["event_id"])  # the same deterministic id
    assert row.geometry["type"] == "Point" and row.versions[0].changed_by == "reprocessing"


# --- one article from its own page --------------------------------------------

PAGE = """<html><head>
<script type="application/ld+json">{"@type": "Organization", "name": "Example Daily"}</script>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "NewsArticle",
 "headline": "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works",
 "description": "DLF Gate No.1 to Gachibowli Traffic PS stretch to remain closed for 90 days",
 "datePublished": "2026-06-29T17:18:36+05:30",
 "articleBody": "Hyderabad: The Cyberabad Police have issued a traffic advisory.
The road is closed for a period of 90 days starting from July 1, 2026."}
</script></head><body><p>Page text for people is not read.</p></body></html>"""


def test_an_article_is_read_from_the_structured_data_of_its_page():
    url = "https://www.example.com/traffic-curbs-near-iiit-junction"
    record = parse_article_page(DECCAN_CHRONICLE, url, PAGE, retrieved_at=RETRIEVED_AT)
    assert record.source_id == "deccan-chronicle"
    assert record.external_id == record.url == url
    assert record.title == "Traffic Curbs Near IIIT Junction from July 1 for Flyover Works"
    assert record.summary.startswith("DLF Gate No.1")
    assert record.content_text.startswith("Hyderabad: The Cyberabad Police")
    assert record.published_at.isoformat() == "2026-06-29T11:48:36+00:00"
    # Kept as evidence exactly as the publisher gave it.
    assert record.raw["content_html"].startswith("Hyderabad:")
    assert "structured data" in record.raw["acquired_from"]

    classification = KeywordClassifier.from_file().classify(record)
    assert classification.is_relevant and classification.city == "Hyderabad"


def test_a_page_without_article_data_is_refused():
    with pytest.raises(ConnectorError):
        parse_article_page(
            DECCAN_CHRONICLE, "https://www.example.com/x", "<html></html>", retrieved_at=RETRIEVED_AT
        )
