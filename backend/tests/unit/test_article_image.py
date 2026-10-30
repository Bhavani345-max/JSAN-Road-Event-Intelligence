"""The image published with an event's article, and whether REI may show it (decision 0050)."""

from datetime import datetime, timezone

import pytest

from app.models import Event, Source, SourceArtifact
from app.repositories.events import to_event_out
from app.services import article_image as images
from app.services.article_image import ImagePermission, article_image, find_article_image

T0 = datetime(2026, 10, 30, tzinfo=timezone.utc)
FEATURED = (
    '<figure><img width="768" height="450" src="https://media.example.com/lead-768x450.jpg" '
    'class="attachment-large size-large wp-post-image" alt="Gachibowli flyover works" /></figure>'
    "<p>Traffic will be diverted at Lakeview Junction.</p>"
)
PERMISSION = ImagePermission(
    terms="Example Daily's image policy (read 30 October 2026): 'Our photographs may be shown with credit.'",
    attribution="Example Daily",
    image_hosts=("example.com",),
)


def source(source_id="example-daily", name="Example Daily", **terms) -> Source:
    return Source(source_id=source_id, source_name=name, source_type="RSS", **terms)


def artifact(markup: str | None = None, url="https://example.com/article", **raw) -> SourceArtifact:
    content = {"summary_html": "", "content_html": markup or "", **raw}
    return SourceArtifact(
        artifact_id="a1", source_id="example-daily", external_id=url, url=url, title="Article",
        published_at=T0, retrieved_at=T0, raw_content=content, content_hash="0" * 64,
        classification="RELEVANT_TRAFFIC_ARTICLE", classification_details={}, created_at=T0,
    )  # fmt: skip


@pytest.fixture
def permitted(monkeypatch):
    monkeypatch.setitem(images.IMAGE_PERMISSIONS, "example-daily", PERMISSION)


def test_no_publisher_is_permitted_yet():
    # 30 October 2026: no publisher's terms were found to permit showing its images.
    assert images.IMAGE_PERMISSIONS == {}


def test_a_permitted_publishers_article_image_is_shown_with_its_attribution(permitted):
    image = article_image(artifact(FEATURED), source())
    assert image.status == "AVAILABLE"
    assert image.url == "https://media.example.com/lead-768x450.jpg"
    assert image.source_url == "https://example.com/article"
    assert image.found_in == "article_markup"
    assert image.alt_text == "Gachibowli flyover works"
    assert image.attribution == "Example Daily"
    assert image.licence == PERMISSION.terms


def test_missing_credit_and_caption_stay_empty(permitted):
    image = article_image(artifact(FEATURED), source())
    # The feed states neither: nothing is made up.
    assert image.credit is None
    assert image.caption is None


def test_a_figure_caption_is_kept_as_the_publisher_wrote_it(permitted):
    markup = (
        '<figure><img src="https://example.com/p.jpg" /><figcaption>Commuters at the '
        "<b>Lakeview</b> junction. File photo</figcaption></figure>"
    )
    assert article_image(artifact(markup), source()).caption == "Commuters at the Lakeview junction. File photo"


def test_an_image_from_a_publisher_without_permission_is_withheld_without_its_address():
    image = article_image(artifact(FEATURED), source())
    assert image.status == "WITHHELD"
    assert image.url is None
    assert image.reason == "Example Daily has not given REI permission to show its images."


@pytest.mark.parametrize(
    "terms",
    [
        {"terms_status": "RESTRICTED", "commercial_use": "NOT_PERMITTED"},  # Deccan Chronicle, Siasat, The Hindu, Mid-day
        {"terms_status": "REVIEW_REQUIRED", "commercial_use": "NOT_PERMITTED"},  # The Hans India: removed from REI
    ],
)
def test_a_publisher_whose_terms_forbid_reis_use_is_never_shown_even_if_listed(permitted, terms):
    image = article_image(artifact(FEATURED), source(**terms))
    assert image.status == "WITHHELD"
    assert image.url is None
    assert image.reason == "Example Daily's terms do not permit REI's use of its content."


def test_an_image_hosted_elsewhere_is_withheld_as_its_owner_is_uncertain(permitted):
    markup = '<img src="https://images.stock-photos.example.net/road.jpg" />'
    image = article_image(artifact(markup), source())
    assert image.status == "WITHHELD"
    assert image.url is None
    assert image.reason == "The image is not on Example Daily's own site, so its owner is not certain."


def test_an_image_not_served_securely_is_withheld(permitted):
    image = article_image(artifact('<img src="http://example.com/a.jpg" />'), source())
    assert (image.status, image.url) == ("WITHHELD", None)
    assert image.reason == "The image is not served over a secure connection."


def test_an_article_without_an_image_has_none():
    assert article_image(artifact("<p>Road closed for repairs.</p>"), source()).status == "NONE"
    assert article_image(None, source()).status == "NONE"


def test_a_structured_source_record_has_no_image():
    # An official feed's record (NDW, TfL, ...): no article markup at all.
    record = artifact(None)
    record.raw_content = {"situation_id": "NDW01_123", "geometry": {"type": "Point"}}
    assert article_image(record, source()).status == "NONE"


def test_tracking_pixels_and_inline_data_are_not_article_images():
    markup = (
        '<img src="https://pixel.example.com/t.gif" width="1" height="1" />'
        '<img src="data:image/png;base64,AAAA" />'
    )
    assert find_article_image({"content_html": markup}) is None


def test_an_open_graph_tag_in_stored_markup_is_not_used():
    # Open Graph images are page metadata; REI does not read article pages for images.
    markup = '<meta property="og:image" content="https://example.com/og.jpg" /><p>Text</p>'
    assert find_article_image({"content_html": markup}) is None


def test_the_featured_image_leads_over_an_earlier_body_image():
    markup = (
        '<p><img src="https://example.com/inline.jpg" /></p>'
        '<img src="https://example.com/featured.jpg" class="wp-post-image" />'
    )
    assert find_article_image({"content_html": markup})["attrs"]["src"] == "https://example.com/featured.jpg"


def test_the_latest_version_of_the_article_is_read(permitted):
    from app.models import SourceArtifactRevision

    record = artifact('<img src="https://example.com/old.jpg" />')
    record.revisions.append(
        SourceArtifactRevision(
            revision=2, url="https://example.com/article", title="Article", published_at=T0,
            retrieved_at=T0, raw_content={"content_html": '<img src="https://example.com/new.jpg" />'},
            content_hash="1" * 64, classification="RELEVANT_TRAFFIC_ARTICLE", created_at=T0,
        )  # fmt: skip
    )
    assert article_image(record, source()).url == "https://example.com/new.jpg"


def test_the_same_image_on_two_articles_belongs_to_each(permitted):
    # Publishers reuse file photos: each article keeps its own image and link.
    first = article_image(artifact(FEATURED, url="https://example.com/one"), source())
    second = article_image(artifact(FEATURED, url="https://example.com/two"), source())
    assert first.url == second.url
    assert (first.source_url, second.source_url) == ("https://example.com/one", "https://example.com/two")


def test_reading_the_image_changes_nothing_in_the_evidence(permitted):
    record = artifact(FEATURED)
    before = dict(record.raw_content)
    article_image(record, source())
    assert record.raw_content == before


def event_row(event_id: str, evidence: SourceArtifact, src: Source) -> Event:
    return Event(
        event_id=event_id, source_id=src.source_id, source_artifact_id=evidence.artifact_id,
        source_reference=evidence.url, title="Lakeview Junction diversion", status="VALIDATION_REQUIRED",
        version=1, created_at=T0, updated_at=T0, source=src, artifact=evidence,
    )  # fmt: skip


def test_each_evidence_record_of_a_merged_event_carries_its_own_image(permitted):
    official = source("official-feed", "City Traffic Police")
    official_record = artifact(None, url="https://traffic.example.org/notice")
    official_record.raw_content = {"notice": "Diversion at Lakeview Junction"}
    news_record = artifact(FEATURED, url="https://example.com/article")
    canonical = event_row("EVT-A", official_record, official)
    member = event_row("EVT-B", news_record, source())

    out = to_event_out(canonical, members=[member])
    assert out.evidence.image.status == "NONE"
    assert out.other_evidence[0].image.status == "AVAILABLE"
    assert out.other_evidence[0].image.url == "https://media.example.com/lead-768x450.jpg"
