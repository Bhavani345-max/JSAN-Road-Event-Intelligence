"""A source the last poll could not reach is tried again sooner (decision 0041).

On 26 October 2026 this machine lost its connection for a few minutes; seven feeds
failed in the same second ("getaddrinfo failed") and NDW's planned feed then showed
"failing" until its next poll three hours later. A site that answered with a
refusal still waits its full interval.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app
from app.repositories.sources import SourceRepository
from app.services import ingestion_service
from app.services.ingestion_service import wait_before_next_poll
from connectors.base import ConnectorError, could_not_reach
from connectors.official import datex3_nl_lu as datex
from connectors.official.common import fetch_json
from connectors.registry import RegisteredSource
from packages.source_models import SourceDefinition
from tests.support import TEST_SOURCE, FakeConnector, khajaguda_article

FEED = "https://feed.example.org/situations.xml.gz"
SOURCE_ID = "nl-like-feed"


def _client(answer) -> httpx.Client:
    """A client whose every request gets `answer(request)` (a response, or an exception raised)."""

    def handler(request: httpx.Request) -> httpx.Response:
        outcome = answer(request)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return httpx.Client(transport=httpx.MockTransport(handler))


def no_name(request):
    return httpx.ConnectError("[Errno 11001] getaddrinfo failed", request=request)


def refused(request):
    return httpx.Response(503, request=request)


class Feed:
    """A feed read with the official feeds' own fetch; what the site does can change."""

    def __init__(self, source: SourceDefinition, state: dict) -> None:
        self.source, self.state = source, state

    def fetch(self):
        if self.state["site"] == "up":
            article = khajaguda_article().model_copy(update={"source_id": self.source.source_id})
            return FakeConnector([article], source=self.source).fetch()
        datex.fetch_bytes(FEED, "REI-test", client=_client(self.state["site"]))
        raise AssertionError("the site answered")


@pytest.fixture
def clock(monkeypatch):
    now = {"at": datetime(2026, 10, 26, 5, 40, tzinfo=timezone.utc)}
    monkeypatch.setattr(ingestion_service, "utc_now", lambda: now["at"])

    def advance(minutes: int) -> None:
        now["at"] += timedelta(minutes=minutes)

    return advance


@pytest.fixture
def feed(engine, session):
    """A service polling one feed every 180 minutes (as NDW's planned feed)."""
    settings = Settings(
        _env_file=None, database_url="sqlite://", auto_migrate=False,
        ingestion_scheduler_enabled=False, event_matching_after_ingestion=False,
    )  # fmt: skip
    service = create_app(settings, engine=engine).state.ingestion_service
    definition = SourceDefinition.model_validate(
        TEST_SOURCE.model_dump()
        | {"source_id": SOURCE_ID, "source_name": SOURCE_ID, "polling_frequency_minutes": 180}
    )
    service.sources = (*service.sources, RegisteredSource(definition))
    SourceRepository(session).sync_registry([definition])
    session.commit()
    state = {"site": no_name}
    service.connector_factories = {SOURCE_ID: lambda: Feed(definition, state)}
    service.resolver = None
    return service, state


def polled(service) -> list[str]:
    return [result.source_id for result in service.run_due()]


def test_a_feed_not_reached_is_tried_again_after_15_then_30_minutes(feed, clock, session):
    service, _ = feed
    [result] = service.run_due()
    assert result.status == "failed"
    assert result.error.startswith(f"Could not fetch {FEED}: [Errno 11001] getaddrinfo failed")
    assert result.error.endswith("The site could not be reached; REI tries again in 15 minutes.")
    # What the console shows as the reason it is failing.
    session.expire_all()
    assert "REI tries again in 15 minutes" in SourceRepository(session).get(SOURCE_ID).last_error

    clock(14)
    assert polled(service) == []
    clock(1)
    [result] = service.run_due()
    assert result.error.endswith("REI tries again in 30 minutes.")
    clock(29)
    assert polled(service) == []
    clock(1)
    assert polled(service) == [SOURCE_ID]


def test_once_the_site_answers_the_feed_waits_its_own_interval_again(feed, clock, session):
    service, state = feed
    service.run_due()
    clock(15)
    state["site"] = "up"
    [result] = service.run_due()
    assert result.status == "ok"
    session.expire_all()
    assert SourceRepository(session).get(SOURCE_ID).last_error is None

    clock(179)
    assert polled(service) == []
    clock(1)
    assert polled(service) == [SOURCE_ID]


def test_a_site_that_refused_is_not_asked_again_before_the_interval(feed, clock):
    service, state = feed
    state["site"] = refused
    [result] = service.run_due()
    assert "refused the request (HTTP 503)" in result.error
    assert "could not be reached" not in result.error

    clock(15)
    assert polled(service) == []
    clock(164)
    assert polled(service) == []
    clock(1)
    assert polled(service) == [SOURCE_ID]


def test_a_refusal_after_a_miss_brings_back_the_full_interval(feed, clock):
    service, state = feed
    service.run_due()
    clock(15)
    state["site"] = refused
    service.run_due()
    clock(30)
    assert polled(service) == []
    clock(150)
    assert polled(service) == [SOURCE_ID]


def test_the_wait_doubles_and_never_passes_the_interval():
    minutes = [wait_before_next_poll(180, misses) / timedelta(minutes=1) for misses in range(7)]
    assert minutes == [180, 15, 30, 60, 120, 180, 180]
    assert wait_before_next_poll(720, 6) == timedelta(minutes=480)
    assert wait_before_next_poll(1440, 1000) == timedelta(minutes=1440)
    # A feed polled every 15 minutes or less is not polled more often.
    assert wait_before_next_poll(10, 1) == timedelta(minutes=10)
    assert wait_before_next_poll(None, 3) == timedelta(0)


@pytest.mark.parametrize(
    "answer, reached",
    [
        (no_name, False),
        (lambda request: httpx.ConnectTimeout("timed out", request=request), False),
        (lambda request: httpx.ReadTimeout("timed out", request=request), False),
        (lambda request: httpx.RemoteProtocolError("Server disconnected", request=request), False),
        (refused, True),
        (lambda request: httpx.Response(429, request=request), True),
        (lambda request: httpx.Response(403, request=request), True),
        (lambda request: httpx.Response(200, text="not json", request=request), True),
    ],
)
def test_only_a_site_that_never_answered_counts_as_not_reached(answer, reached):
    # NDW's and CITA's reader, and the JSON reader of most other official feeds.
    for fetch in (
        lambda: datex.fetch_bytes(FEED, "REI-test", client=_client(answer)),
        lambda: fetch_json(
            "https://feed.example.org/events.json", "REI-test", client=_client(answer)
        ),
    ):
        try:
            fetch()
        except ConnectorError as error:
            assert could_not_reach(error) is not reached
        else:
            # The gzip reader takes any 200 body; the error comes when it is read.
            assert reached
