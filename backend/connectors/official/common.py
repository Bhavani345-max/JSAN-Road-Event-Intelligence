"""What the official-feed connectors share: fetching JSON politely and choosing
the records an international test run keeps."""

import json
import re
import time
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Any, TypeVar

import httpx

from connectors.base import ConnectorError, refusal_detail

MAX_RESPONSE_BYTES = 20 * 1024 * 1024
# A run keeps records in effect now or starting within this long: a planned
# closure is stored as soon as its source lists it, up to a year ahead (7 days
# during the first test phase, until 21 October 2026).
UPCOMING_WINDOW = timedelta(days=365)
# A dropped connection, a timeout or a server error (500, 502, 504) is tried once
# more after this pause before the run fails (21 October 2026: Bison Futé's
# server reset connections twice in a day, Main Roads WA's once, each fine at
# the next run). A refusal (429, 503) is not retried: the source asked REI to wait.
RETRY_DELAY_SECONDS = 3.0
_RETRIED_STATUSES = frozenset({500, 502, 504})
_sleep = time.sleep

T = TypeVar("T")


def _get(url: str, *, client: httpx.Client | None, **options: Any) -> httpx.Response:
    """GET once, and once more after RETRY_DELAY_SECONDS when the failure looks
    temporary. The second attempt's error, or its response, is what counts."""
    for attempt in (1, 2):
        try:
            response = (client or httpx).get(url, **options)
        except httpx.TransportError:
            if attempt == 2:
                raise
        else:
            if response.status_code not in _RETRIED_STATUSES or attempt == 2:
                return response
        _sleep(RETRY_DELAY_SECONDS)
    raise AssertionError("unreachable")


# For a feed that needs the raw response (a zip, a gzip file): the same retry.
get_with_retry = _get


def fetch_json(
    url: str,
    user_agent: str,
    *,
    client: httpx.Client | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """GET a JSON document. A refusal (429, 503), a timeout or bad JSON is a ConnectorError
    (a dropped connection, timeout or 500/502/504 is tried once more first)."""
    try:
        response = _get(
            url,
            client=client,
            params=params,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=60,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not fetch {url}: {error}") from error
    if response.status_code in (429, 503):
        raise ConnectorError(
            f"{url} refused the request (HTTP {response.status_code}): rate limited; "
            "retried at the next run"
        )
    if response.status_code != 200:
        raise ConnectorError(
            f"Could not fetch {url}: HTTP {response.status_code}" + refusal_detail(response)
        )
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as error:
        first_error = error
    # A feed may write a lone backslash in a text ("Water \ Sewer", City of
    # Toronto, 7 October 2026), which is not valid JSON and would make the
    # whole feed unreadable. Read it as the backslash it is; nothing else is
    # changed.
    try:
        return json.loads(repair_invalid_escapes(response.text))
    except (json.JSONDecodeError, ValueError):
        raise ConnectorError(f"{url} did not return JSON: {first_error}") from first_error


def fetch_text(
    url: str,
    user_agent: str,
    *,
    client: httpx.Client | None = None,
    params: dict[str, str] | None = None,
) -> str:
    """GET an HTML page as text. A refusal (429, 503), a timeout or a non-200 is a ConnectorError."""
    try:
        response = _get(
            url,
            client=client,
            params=params,
            headers={"User-Agent": user_agent, "Accept": "text/html"},
            timeout=60,
            follow_redirects=True,
        )
    except httpx.HTTPError as error:
        raise ConnectorError(f"Could not fetch {url}: {error}") from error
    if response.status_code in (429, 503):
        raise ConnectorError(
            f"{url} refused the request (HTTP {response.status_code}): rate limited; "
            "retried at the next run"
        )
    if response.status_code != 200:
        raise ConnectorError(
            f"Could not fetch {url}: HTTP {response.status_code}" + refusal_detail(response)
        )
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ConnectorError(f"Response from {url} is larger than the allowed maximum")
    return response.text


# A valid JSON escape, or a backslash that starts none.
_ESCAPE = re.compile(r'\\(["\\/bfnrt]|u[0-9a-fA-F]{4})|\\')


def repair_invalid_escapes(text: str) -> str:
    """Doubles each backslash that does not start a valid JSON escape."""
    return _ESCAPE.sub(lambda m: m.group(0) if m.group(1) else "\\\\", text)


def content_key(payload: Any, ignore: frozenset[str]) -> str:
    """A fingerprint of a source record's content, leaving out bookkeeping fields.

    Official feeds touch records without changing them (a new "last modified"
    time, a display order). Comparing this key rather than the whole record
    means only a change of content counts as a revision.
    """
    from packages.common.hashing import sha256_hex

    if not isinstance(payload, dict):
        return sha256_hex(json.dumps(payload, sort_keys=True, default=str))
    kept = {key: value for key, value in payload.items() if key not in ignore}
    return sha256_hex(json.dumps(kept, sort_keys=True, default=str))


def parse_json_text(value: Any) -> Any:
    """A value some feeds send as JSON text ("[0.1,51.5]") and others as JSON."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def select_for_run(
    items: Iterable[T],
    *,
    now: datetime,
    start: Callable[[T], datetime | None],
    end: Callable[[T], datetime | None],
    order: Callable[[T], Any],
    limit: int | None,
) -> list[T]:
    """The records a run keeps: in effect now, or starting within UPCOMING_WINDOW.

    Ordered by `order` (largest first: most recently updated, say) and cut to
    `limit` when one is set. During the international test phase a limit keeps
    each city to a small number of real events; it is a setting
    (OFFICIAL_FEED_MAX_RECORDS), not a property of the source.
    """
    kept = [
        item
        for item in items
        if (end(item) is None or end(item) >= now)
        and (start(item) is None or start(item) <= now + UPCOMING_WINDOW)
    ]
    kept.sort(key=order, reverse=True)
    return kept[:limit] if limit else kept
