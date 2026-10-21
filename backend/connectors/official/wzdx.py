"""US work zones in the WZDx standard: one reader, several state and county feeds (decision 0034).

    GET <feed url>   GeoJSON FeatureCollection, WZDx v4.0–4.2; no key

The Work Zone Data Exchange (WZDx) is the US Department of Transportation's
open specification for work-zone feeds; USDOT lists the feeds in its WZDx
feed registry on data.transportation.gov (read 16 October 2026). Each feed
below was fetched without a key on 16 October 2026 and states its licence
in its own `feed_info.license`: CC0 1.0, a public-domain dedication
(https://creativecommons.org/publicdomain/zero/1.0/). No attribution is
required; REI names the publishing agency anyway.

A `work-zone` road event becomes one record:

- what it does to traffic from WZDx's `vehicle_impact`: "all-lanes-closed"
  is a planned road closure; lanes closed, alternating one-way traffic,
  flagging or a temporary signal is a lane restriction; anything else
  (lanes open, unknown) is road works;
- its road names, direction, cross streets or mileposts and types of work,
  in the feed's words;
- its start and end as the feed states them (ISO 8601), with WZDx's own
  "verified" flags kept;
- its geometry as given: a LineString; a MultiPoint (begin and end points)
  is kept as its first point, as REI stores no MultiPoint.

A `detour` road event describes the route traffic is sent along, not where
the road is affected, so it is not taken as an event here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from .common import fetch_json, parse_json_text
from .feature_feed import FeatureFeedConnector, clean, item_record

REGISTRY_URL = "https://data.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Exchange-WZDx-Feed-Registry/69qe-yiui"
LICENCE = "CC0 1.0 Universal (public-domain dedication), stated in each feed's feed_info.license"
CLOSED = frozenset({"all-lanes-closed"})
# WZDx directions that are compass directions (EventDirection); others stay words only.
COMPASS = {
    "northbound": "NORTHBOUND", "southbound": "SOUTHBOUND", "eastbound": "EASTBOUND",
    "westbound": "WESTBOUND", "both": "BOTH_DIRECTIONS",
}  # fmt: skip
RESTRICTED = frozenset({
    "some-lanes-closed", "some-lanes-closed-merge-left", "some-lanes-closed-merge-right",
    "some-lanes-closed-split", "alternating-one-way", "flagging", "temporary-traffic-signal",
})  # fmt: skip


@dataclass(frozen=True)
class WzdxFeed:
    key: str
    state: str
    organization: str
    url: str
    # The zone the feed's times are shown in (the feed states them with offsets).
    zone: str
    # Features listed on the day it was checked (`listed_on`), for the notes.
    listed: int
    listed_on: str = "16 October 2026"
    # Where the feed's licence is stated when not in its own feed_info.license.
    licence_note: str | None = None


FEEDS: tuple[WzdxFeed, ...] = (
    WzdxFeed("deldot", "Delaware", "Delaware DOT", "https://wzdx.e-dot.com/del_dot_feed_wzdx_v4.1.geojson", "America/New_York", 19),
    WzdxFeed("indot", "Indiana", "Indiana DOT", "https://in.carsprogram.org/carsapi_v1/api/wzdx", "America/Indiana/Indianapolis", 1235),
    WzdxFeed("kdot", "Kansas", "Kansas DOT", "https://ks.carsprogram.org/carsapi_v1/api/wzdx", "America/Chicago", 421),
    WzdxFeed("kytc", "Kentucky", "Kentucky Transportation Cabinet", "https://storage.googleapis.com/kytc-its-2020-openrecords/public/feeds/WZDx/kytc_wzdx_v4.1.geojson", "America/New_York", 269),
    WzdxFeed("ladotd", "Louisiana", "Louisiana DOTD", "https://wzdx.e-dot.com/la_dot_d_feed_wzdx_v4.1.geojson", "America/Chicago", 5),
    WzdxFeed("mcdot", "Arizona (Maricopa County)", "Maricopa County DOT", "https://wzdxapi.aztech.org/construction", "America/Phoenix", 2514),
    WzdxFeed("mdot", "Maryland", "Maryland DOT (State Highway Administration)", "https://filter.ritis.org/wzdx_v4.1/mdot.geojson", "America/New_York", 99),
    WzdxFeed("mndot", "Minnesota", "Minnesota DOT", "https://mn.carsprogram.org/carsapi_v1/api/wzdx", "America/Chicago", 471),
    WzdxFeed("njdot", "New Jersey", "New Jersey DOT (NJIT smart work zones)", "https://smartworkzones.njit.edu/nj/wzdx", "America/New_York", 365),
    WzdxFeed("nddot", "North Dakota", "North Dakota DOT", "https://travelfiles.dot.nd.gov/geojson_nc/wzdx_geojson.json", "America/Chicago", 79),
    WzdxFeed("stcharles", "Missouri (St. Charles County)", "St. Charles County", "https://scc.ridsi-dash.com:5000/wzdx.geojson", "America/Chicago", 100),
    # 21 October 2026 (decision 0039). Austin: CC0 1.0 in its feed_info.license.
    WzdxFeed("austin", "Texas (Austin)", "City of Austin Transportation and Public Works", "https://data.austintexas.gov/download/d9mm-cjw9", "America/Chicago", 2728, "21 October 2026"),
    # SFMTA: feed_info is empty; the dataset's licence on DataSF is CC0 1.0
    # (https://data.sfgov.org/api/views/4ftp-yz2f.json, licenseId CC0_10, read 21 October 2026).
    WzdxFeed(
        "sfmta", "California (San Francisco)", "San Francisco Municipal Transportation Agency (SFMTA)",
        "https://data.sfgov.org/download/4ftp-yz2f", "America/Los_Angeles", 4279, "21 October 2026",
        "CC0 1.0 Universal, stated in the dataset's licence on DataSF (dataset 4ftp-yz2f, attribution SFMTA)",
    ),
)  # fmt: skip


def source_id_for(feed: WzdxFeed) -> str:
    return f"wzdx-{feed.key}"


def wzdx_source(feed: WzdxFeed, *, scheduled: bool) -> SourceDefinition:
    city = get_city("united-states")
    return SourceDefinition(
        source_id=source_id_for(feed),
        source_name=f"{feed.organization} work zones (WZDx)",
        organization=feed.organization,
        authority_type="STATE_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region=feed.state,
        city=city.id,
        source_url=REGISTRY_URL,
        endpoint=feed.url,
        access_method="WZDx GeoJSON feed listed in USDOT's WZDx feed registry; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="en",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="wzdx_v4",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; polled hourly (feeds update every 1–60 minutes).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=feed.licence_note or LICENCE,
        attribution=f"Work zones: {feed.organization} (WZDx feed, CC0 1.0).",
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        provides_direction=True,
        real_time=True,
        evidence_retention="Each work-zone feature as received.",
        notes=(
            f"{feed.state}: {feed.listed} road events listed on {feed.listed_on} (work zones and "
            "detours; detours are not taken as events). Every feature carries a start, an end and "
            "geometry."
        ),
    )


def _event_type(impact: str) -> str:
    if impact in CLOSED:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if impact in RESTRICTED:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _geometry(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("type") in ("LineString", "MultiLineString", "Point", "Polygon", "MultiPolygon"):
        return value
    if value.get("type") == "MultiPoint" and value.get("coordinates"):
        return {"type": "Point", "coordinates": value["coordinates"][0]}
    return None


def _time(value: Any) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def to_record_for(feed: WzdxFeed):
    def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            return None
        core = properties.get("core_details") or {}
        if clean(core.get("event_type")) != "work-zone":
            return None
        external_id = clean(feature.get("id") or properties.get("road_event_id"))
        geometry = _geometry(feature.get("geometry"))
        start, end = _time(properties.get("start_date")), _time(properties.get("end_date"))
        if not external_id or geometry is None:
            return None
        roads = [clean(road) for road in core.get("road_names") or [] if clean(road)]
        road = roads[0] if roads else None
        # The feed's words ("northbound", "inner-loop", "undefined" ...) for the title;
        # a compass direction only where the feed states one.
        direction = clean(core.get("direction"))
        if direction in ("unknown", "undefined"):
            direction = ""
        compass = COMPASS.get(direction)
        impact = clean(properties.get("vehicle_impact"))
        event_type = _event_type(impact)
        cross = [clean(properties.get(name)) for name in ("beginning_cross_street", "ending_cross_street")]
        between = " and ".join(part for part in cross if part)
        works = ", ".join(
            clean(work.get("type_name")).replace("-", " ")
            for work in properties.get("types_of_work") or []
            if isinstance(work, dict) and clean(work.get("type_name"))
        )
        description = clean(core.get("description"))
        verified = {
            "start_verified": properties.get("is_start_date_verified"),
            "end_verified": properties.get("is_end_date_verified"),
        }
        structured = SourceEvent(
            event_type=event_type,
            category=" / ".join(part for part in ("Work zone", impact.replace("-", " ") or None, works or None) if part),
            start=start,
            end=end,
            geometry=geometry,
            locations=[
                SourceLocation(
                    name=" ".join(part for part in (road or "Work zone", direction) if part),
                    kind="work zone",
                    geometry=geometry,
                    closure=impact.replace("-", " ") or None,
                )
            ],
            affected_road=road,
            direction=compass,
            attribution=f"Work zones: {feed.organization} (WZDx feed, CC0 1.0).",
            stated_period=(
                f"start {clean(properties.get('start_date'))} ({'verified' if verified['start_verified'] else 'not verified'}), "
                f"end {clean(properties.get('end_date'))} ({'verified' if verified['end_verified'] else 'not verified'})"
            ),
            covers_city=True,
        )
        label = {
            EventType.PLANNED_ROAD_CLOSURE.value: "Road closed",
            EventType.LANE_RESTRICTION.value: "Lane restriction",
        }.get(event_type, "Road works")
        place = " ".join(part for part in (road, direction) if part) or "work zone"
        return item_record(
            source_id=source_id_for(feed),
            external_id=external_id,
            url=feed.url,
            title=f"{label}: {place}{f' between {between}' if between else ''} ({feed.state})",
            summary=". ".join(part for part in (description, works) if part) or None,
            categories=["work-zone", *([impact] if impact else [])],
            item=feature,
            structured=structured,
            retrieved_at=retrieved_at,
        )

    return to_record


def fetch_for(feed: WzdxFeed):
    def fetch_features(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
        body = fetch_json(feed.url, user_agent, client=client)
        # New Jersey's feed (16 October 2026) sends the document as a JSON string.
        if isinstance(body, str):
            body = parse_json_text(body)
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{feed.url} did not return a WZDx feature collection")
        return [feature for feature in features if isinstance(feature, dict)]

    return fetch_features


def connector_for(feed: WzdxFeed) -> type[FeatureFeedConnector]:
    """A FeatureFeedConnector class reading this feed."""
    return type(
        f"Wzdx{feed.key.title()}Connector",
        (FeatureFeedConnector,),
        {"fetch_items": staticmethod(fetch_for(feed)), "to_record": staticmethod(to_record_for(feed))},
    )
