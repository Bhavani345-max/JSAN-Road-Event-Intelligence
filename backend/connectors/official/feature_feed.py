"""What the open-data feature feeds of 15 October 2026 share (decision 0029).

Canada's and Australia's municipal and state feeds publish road events as
features with their own geometry, through two platforms: ArcGIS feature
services and Socrata (SODA). A source module gives its definition, how to
fetch its items and how to read one; `FeatureFeedConnector` does the rest the
same way for all: keep each item as evidence, keep the records in effect now
or starting within the run window, report what the feed lists.
"""

from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.common.time import utc_now
from packages.source_models import RawSourceRecord, SourceDefinition

from .common import content_key, fetch_json, select_for_run

# ArcGIS answers at most this many features a request; most layers allow 1,000-2,000.
ARCGIS_PAGE_SIZE = 1000
# A layer larger than this many pages is not a road-event list; stop rather than loop.
ARCGIS_MAX_PAGES = 10


def fetch_arcgis_features(
    layer_url: str,
    user_agent: str,
    *,
    where: str = "1=1",
    order_by: str = "OBJECTID",
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Every feature of an ArcGIS feature layer matching `where`, as GeoJSON in WGS 84."""
    features: list[dict[str, Any]] = []
    for page in range(ARCGIS_MAX_PAGES):
        body = fetch_json(
            f"{layer_url}/query",
            user_agent,
            client=client,
            params={
                "where": where,
                "outFields": "*",
                "outSR": "4326",
                "orderByFields": order_by,
                "resultOffset": str(page * ARCGIS_PAGE_SIZE),
                "resultRecordCount": str(ARCGIS_PAGE_SIZE),
                "f": "geojson",
            },
        )
        if not isinstance(body, dict) or "error" in body:
            detail = body.get("error") if isinstance(body, dict) else body
            raise ConnectorError(f"{layer_url} answered with an error: {str(detail)[:200]}")
        batch = body.get("features")
        if not isinstance(batch, list):
            raise ConnectorError(f"{layer_url} did not return a GeoJSON feature list")
        features.extend(item for item in batch if isinstance(item, dict))
        more = body.get("exceededTransferLimit") or (body.get("properties") or {}).get(
            "exceededTransferLimit"
        )
        if not more or not batch:
            return features
    raise ConnectorError(f"{layer_url} lists more than {ARCGIS_MAX_PAGES} pages of features")


def fetch_socrata_rows(
    resource_url: str,
    user_agent: str,
    *,
    where: str | None = None,
    client: httpx.Client | None = None,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """The rows of a Socrata (SODA) resource matching `where`, in one request."""
    params = {"$limit": str(limit)}
    if where:
        params["$where"] = where
    body = fetch_json(resource_url, user_agent, client=client, params=params)
    if not isinstance(body, list):
        raise ConnectorError(f"{resource_url} did not return a list of rows")
    if len(body) >= limit:
        raise ConnectorError(f"{resource_url} returned {limit} rows or more; the list is cut")
    return [row for row in body if isinstance(row, dict)]


# --- reading values -----------------------------------------------------------------


def clean(value: Any) -> str:
    """Text with its whitespace collapsed; '' for nothing."""
    return " ".join(str(value or "").split()).strip()


def local_time(value: Any, zone: ZoneInfo, formats: tuple[str, ...]) -> datetime | None:
    """A local date-time written without an offset, in the source's `zone`."""
    text = clean(value)
    for pattern in formats:
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=zone)
        except ValueError:
            continue
    return None


def epoch_ms(value: Any) -> datetime | None:
    """ArcGIS dates: milliseconds since 1970 (UTC)."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=ZoneInfo("UTC"))
    return None


def local_day(value: Any, zone: ZoneInfo) -> date | None:
    """The day a date-only value names, read in the source's zone.

    Socrata writes dates as '2026-10-24T00:00:00.000'; ArcGIS as milliseconds
    at the local midnight.
    """
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=zone).date()
    text = clean(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def whole_days(first: date | None, last: date | None, zone: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """A period stated in days: from the start of the first to the end of the last."""
    start = datetime.combine(first, time.min, tzinfo=zone) if first else None
    end = datetime.combine(last, time(23, 59, 59), tzinfo=zone) if last else None
    return start, end


# --- the connector --------------------------------------------------------------------


class FeatureFeedConnector:
    """A connector for one feature feed: `fetch_items` gets the items, `to_record` reads one."""

    fetch_items: Callable[..., list[dict[str, Any]]]
    to_record: Callable[[dict[str, Any], datetime], RawSourceRecord | None]

    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        max_records: int | None = None,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        self.source = source
        self._user_agent = user_agent
        self.max_records = max_records
        self._client = client
        self._clock = clock

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("item", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        now = self._clock()
        items = type(self).fetch_items(self._user_agent, client=self._client, now=now)
        records = [
            record for item in items if (record := type(self).to_record(item, now)) is not None
        ]
        # Each feed lists everything it has in force or planned (ended items are
        # asked away or dropped by the run window below).
        self.observed_ids = {record.external_id for record in records}
        return select_for_run(
            records,
            now=now,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )


def item_record(
    *,
    source_id: str,
    external_id: str,
    url: str,
    title: str,
    summary: str | None,
    categories: list[str],
    item: dict[str, Any],
    structured,
    retrieved_at: datetime,
    published_at: datetime | None = None,
) -> RawSourceRecord:
    """The stored record of one feed item: the item itself is the evidence."""
    return RawSourceRecord(
        source_id=source_id,
        external_id=external_id,
        url=url,
        title=title,
        summary=summary or None,
        content_text=None,
        categories=categories,
        published_at=published_at,
        retrieved_at=retrieved_at,
        raw={
            "item": item,
            "summary_html": summary or "",
            "categories": categories,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=content_key(item, frozenset()),
        structured=structured,
    )
