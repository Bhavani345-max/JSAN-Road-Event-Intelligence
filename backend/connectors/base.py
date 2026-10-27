from typing import Protocol

import httpx

from packages.source_models import RawSourceRecord, SourceDefinition


class ConnectorError(Exception):
    """The source could not be fetched or its response could not be read."""


def could_not_reach(error: BaseException) -> bool:
    """Whether a fetch failed before the site answered: no network, its name not
    found, the connection dropped or no answer in time (an httpx transport error
    the connector raised its error from). A site that answered, even with a
    refusal (429, 503, 403) or something unreadable, was reached."""
    cause = error.__cause__
    while cause is not None:
        if isinstance(cause, httpx.TransportError):
            return True
        cause = cause.__cause__
    return False


class SourceConnector(Protocol):
    """What the ingestion service needs from any connector, whatever its type."""

    source: SourceDefinition

    def fetch(self) -> list[RawSourceRecord]:
        """Fetch the source's current items. Raises ConnectorError on failure."""
        ...


def refusal_detail(response: httpx.Response) -> str:
    """Who refused a request, as far as the response says; empty when it says nothing.

    A refusal from Cloudflare is the site's bot protection judging the network
    address the request came from, not REI's request: The Hans India's feed
    answered 403 to Railway's servers on 12-14 October 2026 and 200 to the
    same request from an office connection.
    """
    if response.status_code not in (401, 403, 429, 503):
        return ""
    if "cloudflare" not in response.headers.get("server", "").lower():
        return ""
    if response.headers.get("cf-mitigated") == "challenge":
        what = "asked for a browser check"
    else:
        what = "refused the request"
    ray = response.headers.get("cf-ray")
    return (
        f": the site's Cloudflare protection {what}"
        + (f" (Cloudflare ray {ray})" if ray else "")
        + ". Cloudflare judges the network address the request comes from, so the "
        "same request can succeed from another network"
    )
