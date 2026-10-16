from datetime import datetime, timezone

import httpx
import pytest

from tests.support import RETRIEVED_AT
from connectors.base import ConnectorError
from connectors.rss import RssConnector, create_rss_connector
from connectors.rss.telangana_today import TELANGANA_TODAY
from packages.source_models import SourceType


def test_parses_every_usable_item(records):
    # 8 items in the fixture; the one without a title is skipped.
    assert len(records) == 7
    assert all(record.source_id == "test-news" for record in records)
    assert all(record.retrieved_at == RETRIEVED_AT for record in records)


def test_extracts_article_fields(records):
    record = records[0]
    assert record.title == "Traffic diversions at Lakeview Junction for 30 days from Monday"
    assert record.url == "https://news.example.com/traffic-diversions-lakeview-junction"
    assert record.external_id == "https://news.example.com/?p=1001"
    assert record.published_at == datetime(2026, 10, 1, 6, 30, tzinfo=timezone.utc)
    assert record.categories == ["Hyderabad", "News"]
    # Summary and body are plain text...
    assert record.summary.startswith("Motorists heading towards Station Road")
    assert "<p>" not in record.summary
    assert record.content_text.endswith("The work is expected to take 30 days.")
    # ...while the original markup is preserved as evidence.
    assert "<p>" in record.raw["summary_html"]
    assert "<figure>" in record.raw["content_html"]
    assert record.raw["author"] == "Staff Reporter"


def test_missing_optional_fields_become_none(records):
    record = next(r for r in records if r.title.startswith("Road closure near Orchard Flyover"))
    assert record.published_at is None  # unparseable date
    assert record.summary is None
    assert record.content_text is None
    # No <guid>: the link identifies the item.
    assert record.external_id == "https://news.example.com/orchard-flyover-closure"


def test_content_hash_is_stable_and_content_sensitive(rss_connector, feed_bytes):
    first = rss_connector.parse(feed_bytes, retrieved_at=RETRIEVED_AT)
    second = rss_connector.parse(feed_bytes, retrieved_at=RETRIEVED_AT)
    assert [r.content_hash for r in first] == [r.content_hash for r in second]

    edited = rss_connector.parse(
        feed_bytes.replace(b"for 30 days from Monday", b"for 45 days from Monday"),
        retrieved_at=RETRIEVED_AT,
    )
    assert edited[0].content_hash != first[0].content_hash
    assert edited[0].external_id == first[0].external_id


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"this is not xml",
        b"<html><body><h1>503 Service Unavailable</h1></body></html>",
        b'{"error": "not a feed"}',
    ],
)
def test_invalid_feed_is_rejected(rss_connector, body):
    with pytest.raises(ConnectorError, match="invalid feed"):
        rss_connector.parse(body, retrieved_at=RETRIEVED_AT)


def test_the_article_body_is_found_after_an_empty_image_description(rss_connector):
    # The New Indian Express (16 October 2026): an image's empty <media:description>
    # comes first among the item's content elements, the article after it.
    body = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>t</title>
<item><title>Rain brings Delhi traffic to a crawl</title><link>https://example.com/a</link>
<guid isPermaLink="false">a1</guid><pubDate>Fri, 16 Oct 2026 08:38:59 +0000</pubDate>
<description></description>
<media:content url="https://example.com/a.jpg" medium="image"><media:description type="html"></media:description></media:content>
<content:encoded><![CDATA[<p>Waterlogging at ITO slowed traffic.</p>]]></content:encoded></item>
</channel></rss>"""
    (record,) = rss_connector.parse(body, retrieved_at=RETRIEVED_AT)
    assert record.content_text == "Waterlogging at ITO slowed traffic."


def test_feed_with_no_items_is_valid_and_empty(rss_connector):
    body = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'
    assert rss_connector.parse(body, retrieved_at=RETRIEVED_AT) == []


def test_network_failure_raises_connector_error(rss_connector, monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx, "get", fail)
    with pytest.raises(ConnectorError, match="Could not fetch"):
        rss_connector.fetch()


def test_http_error_status_raises_connector_error(rss_connector, monkeypatch):
    def not_found(url, **kwargs):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", not_found)
    with pytest.raises(ConnectorError, match="Could not fetch"):
        rss_connector.fetch()


def test_fetch_downloads_and_parses(rss_connector, feed_bytes, monkeypatch):
    def ok(url, **kwargs):
        assert kwargs["headers"]["User-Agent"]
        return httpx.Response(200, content=feed_bytes, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", ok)
    assert len(rss_connector.fetch()) == 7


def test_telangana_today_is_a_connected_rss_source():
    assert TELANGANA_TODAY.source_name == "Telangana Today"
    assert TELANGANA_TODAY.source_type is SourceType.RSS
    assert TELANGANA_TODAY.source_url == "https://telanganatoday.com/hyderabad"
    assert TELANGANA_TODAY.endpoint == "https://telanganatoday.com/hyderabad/feed"
    assert TELANGANA_TODAY.active is True
    assert isinstance(create_rss_connector(TELANGANA_TODAY), RssConnector)


def test_a_cloudflare_refusal_says_who_refused(rss_connector, monkeypatch):
    # The Hans India's feed from Railway's servers, 12-14 October 2026.
    def refused(url, **kwargs):
        headers = {
            "server": "cloudflare", "cf-ray": "a4a70e417f0469ae-SJC", "cf-mitigated": "challenge",
        }  # fmt: skip
        return httpx.Response(403, headers=headers, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", refused)
    with pytest.raises(ConnectorError) as error:
        rss_connector.fetch()
    message = str(error.value)
    assert "HTTP 403 Forbidden" in message
    assert "Cloudflare protection asked for a browser check" in message
    assert "a4a70e417f0469ae-SJC" in message


def test_a_refusal_from_anyone_else_is_reported_as_it_is(rss_connector, monkeypatch):
    def refused(url, **kwargs):
        return httpx.Response(403, headers={"server": "nginx"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", refused)
    with pytest.raises(ConnectorError) as error:
        rss_connector.fetch()
    assert str(error.value).endswith("HTTP 403 Forbidden")
