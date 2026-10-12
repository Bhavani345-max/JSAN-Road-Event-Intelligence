"""Google Maps answers through Serper.dev, cached on disk, within a daily credit limit.

/places costs 1 credit and answers a named place; /maps costs 3 and searches
more widely around a point. Each query is asked once: the answer (even an
empty one) is kept in the cache file, so reprocessing costs nothing. When the
day's credits are used, or no key is configured, nothing is asked and the
caller places what it can without Google.

Used only to place a name an article states (placement.py); every answer is
checked there before it is used.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev"
PLACES_CREDITS = 1
MAPS_CREDITS = 3


class GoogleMapsLookup:
    def __init__(
        self,
        api_key: str,
        cache_path: Path,
        *,
        daily_credits: int = 60,
        allow_network: bool = True,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self._key = api_key
        self._path = Path(cache_path)
        self._daily = daily_credits
        self.allow_network = allow_network
        self._transport = transport
        self._timeout = timeout_seconds
        self._lock = threading.Lock()
        self._data = self._load()

    # --- cache -------------------------------------------------------------------

    def _load(self) -> dict:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data.setdefault("queries", {})
        data.setdefault("usage", {})
        return data

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self._path)
        except OSError:
            logger.warning("Could not save the Google Maps cache at %s", self._path)

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def credits_used_today(self) -> int:
        usage = self._data["usage"]
        return int(usage.get("credits", 0)) if usage.get("date") == self._today() else 0

    def _spend(self, credits: int) -> bool:
        if self.credits_used_today() + credits > self._daily:
            return False
        self._data["usage"] = {"date": self._today(), "credits": self.credits_used_today() + credits}
        return True

    # --- asking --------------------------------------------------------------------

    def _ask(self, cache_key: str, endpoint: str, body: dict, credits: int) -> list[dict] | None:
        with self._lock:
            held = self._data["queries"].get(cache_key)
            if held is not None:
                return held["places"]
            if not self.allow_network or not self._key or not self._spend(credits):
                return None
            try:
                with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
                    response = http.post(
                        f"{SERPER_URL}/{endpoint}", headers={"X-API-KEY": self._key}, json=body
                    )
                response.raise_for_status()
                places = response.json().get("places") or []
            except (httpx.HTTPError, ValueError) as error:
                logger.warning("Google Maps lookup failed for %r: %s", body.get("q"), error)
                return None
            self._data["queries"][cache_key] = {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "places": [
                    {
                        key: place.get(key)
                        for key in ("title", "address", "latitude", "longitude", "type", "cid")
                    }
                    for place in places[:5]
                ],
            }
            self._save()
            return self._data["queries"][cache_key]["places"]

    def places(self, query: str) -> list[dict] | None:
        """Google's places for the query (1 credit), or None when it could not be asked."""
        return self._ask(f"places|{query}", "places", {"q": query, "gl": "in"}, PLACES_CREDITS)

    def maps(self, query: str, centre: tuple[float, float]) -> list[dict] | None:
        """Google Maps' wider search around a point (3 credits), or None when it could not be asked."""
        return self._ask(
            f"maps|{query}",
            "maps",
            {"q": query, "ll": f"@{centre[0]},{centre[1]},12z", "gl": "in"},
            MAPS_CREDITS,
        )
