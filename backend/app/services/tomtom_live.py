"""TomTom live incidents for the map: fetched per view, never stored (decision 0054).

TomTom's developer terms (docs.tomtom.com/legal/terms-and-conditions, read
4 November 2026) prohibit "the caching or storing of any Results" beyond a
client's cache within the response's cache-control max-age (11.4), building a
"secondary or derived database" (11.6.1), and, without a paid plan, any use but
internal evaluation and testing (2.2). So TomTom incidents never become REI
events: a signed-in user's map asks for the area on screen, this service asks
TomTom once, passes the answer through as GeoJSON with the cache-control header
TomTom sent (or no-store), and keeps nothing but a count of requests made today.
Attribution is TomTom's own caption from its Copyright API (17.3).

Only road events are asked for (TomTom's categoryFilter): accidents, dangerous
conditions, lane and road closures, road works, flooding and broken-down
vehicles; never jams or weather, as for every REI source. TomTom answers for
areas of up to 10,000 km², so the map asks only when zoomed in to a city.
"""

import math
import threading
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from packages.common.time import utc_now

INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
CAPTION_URL = "https://api.tomtom.com/map/2/copyrights/caption.json"
# TomTom's limit for one request's bounding box.
MAX_AREA_KM2 = 10_000.0
# TomTom's icon categories REI shows, with REI's words for them.
CATEGORIES: dict[int, tuple[str, str]] = {
    1: ("ACCIDENT", "Accident"),
    3: ("ROAD_HAZARD", "Dangerous conditions"),
    7: ("LANE_RESTRICTION", "Lane closed"),
    8: ("ROAD_CLOSURE", "Road closed"),
    9: ("ROAD_WORKS", "Road works"),
    11: ("WATERLOGGING", "Flooding"),
    14: ("ROAD_HAZARD", "Broken-down vehicle"),
}
FIELDS = (
    "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,"
    "events{description,code,iconCategory},startTime,endTime,from,to,length,delay,roadNumbers,"
    "timeValidity,probabilityOfOccurrence,lastReportTime}}}"
)
DELAY = {0: "unknown", 1: "minor", 2: "moderate", 3: "major", 4: "undefined (closure)"}


class LiveUnavailable(Exception):
    """No key configured: the layer is off."""


class LiveRefused(Exception):
    """A request REI will not send: a bad or too large area, or the day's requests used."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class LiveFailed(Exception):
    """TomTom did not answer usefully."""


@dataclass(frozen=True)
class LiveAnswer:
    collection: dict[str, Any]
    # TomTom's own cache-control header, passed on to the browser (else no-store).
    cache_control: str


def parse_bbox(text: str) -> tuple[float, float, float, float]:
    """'minLon,minLat,maxLon,maxLat' as numbers, checked; LiveRefused otherwise."""
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in text.split(","))
    except ValueError:
        raise LiveRefused("bbox must be minLon,minLat,maxLon,maxLat", 400) from None
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise LiveRefused("bbox is not a valid WGS 84 box", 400)
    return min_lon, min_lat, max_lon, max_lat


def area_km2(bbox: tuple[float, float, float, float]) -> float:
    """The box's approximate area (equirectangular, at its middle latitude)."""
    min_lon, min_lat, max_lon, max_lat = bbox
    middle = math.radians((min_lat + max_lat) / 2)
    width = (max_lon - min_lon) * 111.32 * math.cos(middle)
    height = (max_lat - min_lat) * 110.57
    return abs(width * height)


def _feature(incident: dict[str, Any]) -> dict[str, Any] | None:
    properties = incident.get("properties") or {}
    category = CATEGORIES.get(properties.get("iconCategory"))
    geometry = incident.get("geometry")
    if category is None or not isinstance(geometry, dict) or geometry.get("type") not in ("Point", "LineString"):
        return None
    descriptions = [
        str(event.get("description")).strip()
        for event in properties.get("events") or []
        if isinstance(event, dict) and event.get("description")
    ]
    return {
        "type": "Feature",
        "geometry": {"type": geometry["type"], "coordinates": geometry.get("coordinates")},
        "properties": {
            "id": properties.get("id"),
            "category": category[0],
            "label": category[1],
            "description": "; ".join(dict.fromkeys(descriptions)) or None,
            "from": properties.get("from"),
            "to": properties.get("to"),
            "roads": properties.get("roadNumbers") or [],
            "start": properties.get("startTime"),
            "end": properties.get("endTime"),
            "delay": DELAY.get(properties.get("magnitudeOfDelay")),
            "length_m": properties.get("length"),
            "time_validity": properties.get("timeValidity"),
        },
    }


class TomTomLive:
    """Asks TomTom for one area at a time; keeps only today's request count."""

    def __init__(self, api_key: str | None, daily_limit: int, *, client: httpx.Client | None = None) -> None:
        self._key = api_key or None
        self._daily_limit = daily_limit
        self._client = client
        self._lock = threading.Lock()
        self._day: date | None = None
        self._used = 0

    @property
    def configured(self) -> bool:
        return self._key is not None

    def status(self) -> dict[str, Any]:
        with self._lock:
            used = self._used if self._day == utc_now().date() else 0
        return {"configured": self.configured, "requests_today": used, "daily_limit": self._daily_limit}

    def _count(self, requests: int) -> None:
        with self._lock:
            today = utc_now().date()
            if self._day != today:
                self._day, self._used = today, 0
            if self._used + requests > self._daily_limit:
                raise LiveRefused(
                    "Today's TomTom requests for the live layer are used up; it resumes tomorrow (UTC).", 429
                )
            self._used += requests

    def _get(self, url: str, params: dict[str, str]) -> httpx.Response:
        try:
            return (self._client or httpx).get(
                url, params={**params, "key": self._key}, timeout=20, headers={"Accept": "application/json"}
            )
        except httpx.HTTPError as error:
            raise LiveFailed(f"TomTom could not be reached ({type(error).__name__})") from None

    def incidents(self, bbox_text: str) -> LiveAnswer:
        if not self.configured:
            raise LiveUnavailable("TomTom live incidents are not configured (TOMTOM_API_KEY)")
        bbox = parse_bbox(bbox_text)
        if area_km2(bbox) > MAX_AREA_KM2:
            raise LiveRefused("Zoom in: TomTom answers for areas up to 10,000 km² (about a city).", 400)
        self._count(2)
        response = self._get(
            INCIDENTS_URL,
            {
                "bbox": ",".join(f"{value:.5f}" for value in bbox),
                "fields": FIELDS,
                "language": "en-GB",
                "categoryFilter": ",".join(str(category) for category in CATEGORIES),
                "timeValidityFilter": "present,future",
            },
        )
        if response.status_code in (401, 403):
            raise LiveFailed(f"TomTom refused the key (HTTP {response.status_code})")
        if response.status_code == 429:
            raise LiveRefused("TomTom is limiting requests; try again in a minute.", 429)
        if response.status_code != 200:
            raise LiveFailed(f"TomTom answered HTTP {response.status_code}")
        try:
            incidents = response.json().get("incidents") or []
        except ValueError:
            raise LiveFailed("TomTom's answer was not JSON") from None
        features = [feature for incident in incidents if isinstance(incident, dict) and (feature := _feature(incident))]
        return LiveAnswer(
            collection={
                "type": "FeatureCollection",
                "features": features,
                "attribution": self._caption(),
                "fetched_at": utc_now().isoformat(),
            },
            cache_control=response.headers.get("cache-control") or "no-store",
        )

    def _caption(self) -> str:
        """TomTom's copyright caption from its Copyright API (terms 17.3), asked with each answer."""
        response = self._get(CAPTION_URL, {})
        try:
            caption = response.json().get("copyrightsCaption") if response.status_code == 200 else None
        except ValueError:
            caption = None
        return str(caption).strip() if caption else "© TomTom"
