"""Article images through ingestion and the API (decision 0050): read only, permission first."""

from sqlalchemy import func, select

from app.models import Event, EventVersion, SourceArtifact
from app.services import article_image as images
from app.services.article_image import ImagePermission
from tests.support import TEST_SOURCE


def listed_events(client) -> dict[str, dict]:
    response = client.post("/api/ingestion/run", params={"source_id": TEST_SOURCE.source_id})
    assert response.status_code == 200
    items = client.get("/api/events?view=validation&include_hidden=true").json()["items"]
    return {event["title"].split()[0]: event for event in items}


def counts(session) -> tuple[int, ...]:
    session.expire_all()
    return tuple(
        session.scalar(select(func.count()).select_from(model))
        for model in (Event, SourceArtifact, EventVersion)
    )


def test_an_article_image_without_permission_is_withheld_and_its_address_not_sent(client):
    events = listed_events(client)
    # The feed item's <figure><img src="https://news.example.com/a.jpg"></figure>.
    image = events["Traffic"]["evidence"]["image"]
    assert image["status"] == "WITHHELD"
    assert image["url"] is None
    assert image["reason"] == "Example Daily has not given REI permission to show its images."
    assert "a.jpg" not in str(events["Traffic"])


def test_a_permitted_article_image_is_sent_with_its_article_and_attribution(client, monkeypatch):
    monkeypatch.setitem(
        images.IMAGE_PERMISSIONS,
        TEST_SOURCE.source_id,
        ImagePermission(terms="Test permission.", attribution="Example Daily", image_hosts=("news.example.com",)),
    )
    events = listed_events(client)
    image = events["Traffic"]["evidence"]["image"]
    assert image == {
        "status": "AVAILABLE",
        "url": "https://news.example.com/a.jpg",
        "source_url": "https://news.example.com/traffic-diversions-lakeview-junction",
        "found_in": "article_markup",
        "caption": None,
        "alt_text": None,
        "credit": None,
        "licence": "Test permission.",
        "attribution": "Example Daily",
        "reason": None,
    }
    # The article without an image has none; nothing is borrowed from another article.
    assert events["Heavy"]["evidence"]["image"]["status"] == "NONE"


def test_reading_images_writes_nothing(client, session, monkeypatch):
    listed_events(client)
    before = counts(session)
    monkeypatch.setitem(
        images.IMAGE_PERMISSIONS,
        TEST_SOURCE.source_id,
        ImagePermission(terms="Test permission.", attribution="Example Daily", image_hosts=("news.example.com",)),
    )
    for _ in range(2):
        items = client.get("/api/events?view=validation&include_hidden=true").json()["items"]
        for event in items:
            assert client.get(f"/api/events/{event['event_id']}").status_code == 200
    assert counts(session) == before
    versions = session.scalars(select(EventVersion.version)).all()
    assert set(versions) == {1}
