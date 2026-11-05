"""Finding a place or postcode on the map (decision 0055).

Two lookups, both OpenStreetMap:

- REI's own place lists (the cities with an OSM gazetteer: Hyderabad, Mumbai …):
  local, so they may answer while the user types.
- OSM's public geocoder, Nominatim, for any country and for postcodes (an Indian
  PIN "500032", "SW1A 1AA", "00-950"), asked only when the user presses Enter.
  Its usage policy (operations.osmfoundation.org/policies/nominatim, read
  4 November 2026): "an absolute maximum of 1 request per second" for all of an
  application's users together, a User-Agent "identifying the application", no
  search-as-you-type ("you must not implement such a service on the client side
  using the API"), "Results must be cached on your side", attribution. So
  requests are serialised one per second for the whole API, answers are kept
  for a day, and results carry "© OpenStreetMap contributors".

The search is held to the chosen country (its ISO code) and prefers the chosen
city's box; each result says whether it lies in that box.
"""

import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

import httpx

from packages.cities import City
from services.geo_resolution import resolver_for

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "JSAN-REI/1.0 (road event intelligence; place search)"
ATTRIBUTION = "© OpenStreetMap contributors"
MIN_SECONDS_BETWEEN_REQUESTS = 1.1
CACHE_SECONDS = 24 * 3600
CACHE_SIZE = 1000
LIMIT = 8
# A postcode: digits with at most one space or dash, or a UK/Irish/Dutch-style
# code of letters and digits ("SW1A 1AA", "D02 X285", "1012 AB").
_POSTCODE = re.compile(
    r"^(?:\d{3,6}(?:[\s-]\d{2,4})?|\d{2}-\d{3}|[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}|[A-Za-z]\d{2}\s?[A-Za-z\d]{4}|\d{4}\s?[A-Za-z]{2})$"
)


class PlaceSearchFailed(Exception):
    """Nominatim did not answer usefully."""


def is_postcode(query: str) -> bool:
    return bool(_POSTCODE.match(query.strip()))


def _in_box(latitude: float, longitude: float, city: City | None) -> bool | None:
    if city is None or not city.bbox:
        return None
    south, west, north, east = city.bbox
    return south <= latitude <= north and west <= longitude <= east


def local_results(query: str, city: City | None) -> list[dict[str, Any]]:
    """Places of the city's own OSM place list whose name holds the query."""
    if city is None or not city.gazetteer:
        return []
    return [
        {
            "name": match.name,
            "detail": f"{match.kind} · {city.name}",
            "latitude": match.latitude,
            "longitude": match.longitude,
            "box": None,
            "kind": match.kind,
            "source": "place_list",
            "in_area": True,
        }
        for match in resolver_for(city).suggest(query, limit=LIMIT)
        if match.has_position
    ]


class PlaceSearch:
    """Asks Nominatim at most once a second for the whole API, and remembers answers for a day."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_request: float | None = None
        self._cache: OrderedDict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = OrderedDict()

    def search(self, query: str, city: City | None) -> list[dict[str, Any]]:
        """The city's own places first (if it has a list), then OSM's geocoder.

        A geocoder answer at the same spot as one of the city's places is the
        same OSM place: it is not listed twice, and its area (the box OSM gives
        it, such as a suburb's) is kept on the city's entry, which has only a
        point (decision 0056: the events in that area are the ones highlighted).
        """
        text = " ".join(query.split())
        found = local_results(text, city)
        seen = {(round(r["latitude"], 4), round(r["longitude"], 4)): r for r in found}
        for result in self._nominatim(text, city):
            key = (round(result["latitude"], 4), round(result["longitude"], 4))
            same = seen.get(key)
            if same is None:
                seen[key] = result
                found.append(result)
            elif same["source"] == "place_list" and same["box"] is None and result["box"] is not None:
                same["box"] = list(result["box"])
        return found[: LIMIT * 2]

    def _nominatim(self, text: str, city: City | None) -> list[dict[str, Any]]:
        cache_key = (text.casefold(), city.id if city else "")
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and self._clock() - cached[0] < CACHE_SECONDS:
                self._cache.move_to_end(cache_key)
                return cached[1]
            params: dict[str, str] = {"format": "jsonv2", "limit": str(LIMIT), "addressdetails": "0"}
            if is_postcode(text):
                params["postalcode"] = text
            else:
                params["q"] = text
            if city is not None:
                params["countrycodes"] = city.country.lower()
                if city.bbox:
                    south, west, north, east = city.bbox
                    params["viewbox"] = f"{west},{north},{east},{south}"
            if self._last_request is not None:
                wait = MIN_SECONDS_BETWEEN_REQUESTS - (self._clock() - self._last_request)
                if wait > 0:
                    self._sleep(wait)
            try:
                response = (self._client or httpx).get(
                    NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15
                )
            except httpx.HTTPError as error:
                raise PlaceSearchFailed(f"OpenStreetMap search could not be reached ({type(error).__name__})") from None
            finally:
                self._last_request = self._clock()
            if response.status_code != 200:
                raise PlaceSearchFailed(f"OpenStreetMap search answered HTTP {response.status_code}")
            try:
                rows = response.json()
            except ValueError:
                raise PlaceSearchFailed("OpenStreetMap search did not answer with JSON") from None
            results = [result for row in rows if isinstance(row, dict) and (result := self._result(row, city))]
            self._cache[cache_key] = (self._clock(), results)
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
            return results

    @staticmethod
    def _result(row: dict[str, Any], city: City | None) -> dict[str, Any] | None:
        try:
            latitude, longitude = float(row["lat"]), float(row["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        box = None
        bounding = row.get("boundingbox")
        if isinstance(bounding, list) and len(bounding) == 4:
            try:
                south, north, west, east = (float(value) for value in bounding)
                box = [west, south, east, north]
            except ValueError:
                box = None
        display = str(row.get("display_name") or "")
        name = str(row.get("name") or "") or display.split(",")[0].strip()
        detail = display[len(name):].lstrip(", ") if display.startswith(name) else display
        return {
            "name": name or display,
            "detail": detail[:160],
            "latitude": latitude,
            "longitude": longitude,
            "box": box,
            "kind": str(row.get("type") or row.get("category") or "place"),
            "source": "nominatim",
            "in_area": _in_box(latitude, longitude, city),
        }
