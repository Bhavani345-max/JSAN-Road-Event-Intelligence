"""Helpers shared by the test suites (imported as `tests.support`).

Nothing here is ever loaded by the application: fixtures live under tests/
and reach a database only inside a test.
"""

import json
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import User
from app.services.auth_service import create_session
from connectors.base import ConnectorError
from connectors.rss import create_rss_connector
from connectors.rss.deccan_chronicle import DECCAN_CHRONICLE
from connectors.rss.models import news_rss_source
from connectors.rss.newsmeter import NEWSMETER
from connectors.rss.telangana_today import TELANGANA_TODAY
from connectors.rss.the_hindu import THE_HINDU
from packages.common.hashing import sha256_hex
from packages.common.text import html_to_text
from packages.common.time import utc_now
from packages.event_schema import ReiEvent
from packages.source_models import RawSourceRecord, SourceDefinition

# Synthetic feeds in each publisher's format.
FEEDS = Path(__file__).parent / "golden-events"
# Regression fixtures: real published articles, and located events for map tests.
FIXTURES = Path(__file__).parent / "fixtures"
RETRIEVED_AT = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)
IST = timezone(timedelta(hours=5, minutes=30))

TEST_SOURCE = news_rss_source(
    source_id="test-news",
    source_name="Example Daily",
    organization="Example Daily",
    source_url="https://news.example.com",
    endpoint="https://news.example.com/feed",
    notes="Test source.",
)

# Each connected Hyderabad RSS source, with a synthetic feed in a matching format.
# Siasat is not here: its terms forbid automated access (decision 0024). Nor is
# The Hans India: disconnected until its publisher agrees (decision 0026).
SOURCE_FIXTURES: tuple[tuple[SourceDefinition, str], ...] = (
    (TELANGANA_TODAY, "news_feed_sample.xml"),
    (THE_HINDU, "the_hindu_style_feed.xml"),
    (DECCAN_CHRONICLE, "deccan_chronicle_style_feed.xml"),
    # Same publishing system, and so the same feed format, as Deccan Chronicle.
    (NEWSMETER, "deccan_chronicle_style_feed.xml"),
)


def parse_fixture(source: SourceDefinition, filename: str) -> list[RawSourceRecord]:
    """Parse a synthetic feed with the generic RSS connector, as `source`."""
    return create_rss_connector(source).parse(
        (FEEDS / filename).read_bytes(), retrieved_at=RETRIEVED_AT
    )


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def khajaguda_article() -> RawSourceRecord:
    """The real Telangana Today article on the Khajaguda Junction diversions."""
    fixture = load_fixture("telangana_today_khajaguda_2026-09-24.json")
    raw = fixture["raw"]
    return RawSourceRecord(
        source_id=fixture["source_id"],
        external_id=fixture["external_id"],
        url=fixture["url"],
        title=html_to_text(raw["title"]),
        summary=html_to_text(raw["summary_html"]) or None,
        content_text=html_to_text(raw["content_html"]) or None,
        categories=[category for category in raw["categories"] if category],
        published_at=datetime(2026, 9, 24, 6, 25, 13, tzinfo=timezone.utc),
        retrieved_at=RETRIEVED_AT,
        raw=raw,
        content_hash=sha256_hex(raw["title"] + raw["summary_html"] + raw["content_html"]),
    )


def iiit_junction_article() -> RawSourceRecord:
    """The real Deccan Chronicle article on the DLF / IIIT Junction closure."""
    fixture = load_fixture("deccan_chronicle_iiit_junction_2026-06-29.json")
    return RawSourceRecord(
        source_id=fixture["source_id"],
        external_id=fixture["url"],
        url=fixture["url"],
        title=fixture["title"],
        summary=fixture["summary"],
        content_text=fixture["body"],
        categories=fixture["categories"],
        published_at=datetime.fromisoformat(fixture["published"]),
        retrieved_at=RETRIEVED_AT,
        raw={"title": fixture["title"], "summary_html": fixture["summary"], "content_html": fixture["body"]},
        content_hash=sha256_hex(fixture["title"] + fixture["summary"] + fixture["body"]),
    )


def _resolve_time(today_ist: date, spec: dict | None) -> datetime | None:
    if spec is None:
        return None
    day = today_ist + timedelta(days=spec["day_offset"])
    return datetime.combine(day, time.fromisoformat(spec["time"]), tzinfo=IST)


def load_located_events(now: datetime, source_id: str = TEST_SOURCE.source_id) -> list[ReiEvent]:
    """Invented events WITH geometry, for exercising geometry handling and the map.

    Test data only. The application never loads these.
    """
    document = load_fixture("located_events.json")
    today_ist = now.astimezone(IST).date()
    events = []
    for entry in document["events"]:
        entry = dict(entry)
        start, end = entry.pop("start"), entry.pop("end")
        events.append(
            ReiEvent(
                **entry,
                source_id=source_id,
                city=document["city"],
                start_time=_resolve_time(today_ist, start),
                end_time=_resolve_time(today_ist, end),
                created_at=now,
                updated_at=now,
            )
        )
    return events


REVIEWER_EMAIL = "reviewer@example.com"


def sign_in(client: TestClient) -> TestClient:
    """Give `client` a real reviewer session cookie, as signing in to the console does.

    The account has no usable password (hashing one takes half a second per
    test); signing in with a password is tested in test_auth.py.
    """
    app = client.app
    with app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == REVIEWER_EMAIL))
        if user is None:
            now = utc_now()
            user = User(
                user_id=str(uuid.uuid4()),
                email=REVIEWER_EMAIL,
                display_name="Test Reviewer",
                password_hash="!",
                role="admin",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.flush()
        token = create_session(session, user, lifetime_hours=1)
        session.commit()
    client.cookies.set(app.state.settings.auth_cookie_name, token)
    return client


class FakeConnector:
    """A connector that returns fixed records, or fails, without any network."""

    def __init__(
        self,
        records: list[RawSourceRecord],
        source: SourceDefinition = TEST_SOURCE,
        error: str | None = None,
    ) -> None:
        self.source = source
        self.records = records
        self.error = error

    def fetch(self) -> list[RawSourceRecord]:
        if self.error:
            raise ConnectorError(self.error)
        return self.records
