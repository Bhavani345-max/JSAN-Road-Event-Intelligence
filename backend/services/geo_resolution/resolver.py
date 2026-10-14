"""Locates an article by the Hyderabad places it names.

The article's own words are looked up in a gazetteer built from OpenStreetMap
(see build_gazetteer.py). Nothing is inferred: a place is found only when the
text names it, and the coordinates are those of the OpenStreetMap feature of
that name. The result is the location of the *named place*, not the surveyed
extent of a closure, and is recorded as such for the reviewer.
"""

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .names import name_tokens, spelling_variants

DEFAULT_GAZETTEER_PATH = Path(__file__).parent / "data" / "hyderabad_places.json"

# Longest place name, in words, that is looked for.
_MAX_WORDS = 7

# Where a name was found, most telling first.
FIELD_ORDER = ("title", "summary", "body")
# A named junction says more about where an event is than a whole locality.
_KIND_ORDER = ("junction", "flyover", "landmark", "road", "area", "ward")
# Kinds of place that are one spot rather than a stretch or an area.
SPOT_KINDS = ("junction", "flyover", "landmark")
# How far a named spot may lie from the locality the headline names and still
# be taken as the spot within it that the article means.
WITHIN_KM = 2.5

# Names the papers use for a place whose OpenStreetMap name differs. Each
# points at a real feature of the same place; none adds a position of its own.
KNOWN_AS: dict[str, str] = {
    "tank bund": "tank bund road",
    "secunderabad railway station": "secunderabad junction",
    "secunderabad station": "secunderabad junction",
    "jubilee hills check post": "jubilee check post junction",
    "jubilee hills checkpost": "jubilee check post junction",
    "paradise circle": "paradise crossroads",
    "paradise junction": "paradise crossroads",
    "hitech city": "hitec city",
    "hi tech city": "hitec city",
    "rgia": "rajiv gandhi international airport",
    "shamshabad airport": "rajiv gandhi international airport",
}


@dataclass(frozen=True)
class PlaceMatch:
    """A gazetteer place named in a text."""

    name: str
    kind: str
    # "place" (a junction, flyover or landmark), "road" or "area"; "none" for a
    # name that does not point to one spot, which has no position.
    precision: str
    # junction, flyover, landmark, road, area or ward.
    latitude: float | None
    longitude: float | None
    osm_ref: str | None
    # The words as the article wrote them, and the field they were found in.
    mention: str
    found_in: str

    @property
    def has_position(self) -> bool:
        return self.latitude is not None

    @property
    def is_spot(self) -> bool:
        return self.kind in SPOT_KINDS and self.has_position

    def distance_km(self, other: "PlaceMatch") -> float:
        """Distance between two located places, as the crow flies."""
        if not (self.has_position and other.has_position):
            return math.inf
        lat = math.radians((self.latitude + other.latitude) / 2)
        dx = (self.longitude - other.longitude) * 111.32 * math.cos(lat)
        dy = (self.latitude - other.latitude) * 110.57
        return math.hypot(dx, dy)


class PlaceResolver:
    def __init__(
        self,
        places: list[dict],
        data_timestamp: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> None:
        self.data_timestamp = data_timestamp
        # south, west, north, east of the area the gazetteer covers.
        self.bbox = bbox
        # Generic names ("Market Road") are left out even if the gazetteer file
        # still carries them from an earlier build.
        from .build_gazetteer import GENERIC_NAMES

        self._places: dict[tuple[str, ...], dict] = {
            tuple(place["key"].split()): place
            for place in places
            if place["key"] not in GENERIC_NAMES
        }
        # A name written joined or split ("Dilsukhnagar", "Dilsukh Nagar") is
        # the same place; a spelling that is itself a known name is left alone.
        for place in places:
            for variant in spelling_variants(place["key"]):
                self._places.setdefault(tuple(variant.split()), place)
        for written, osm_name in KNOWN_AS.items():
            place = self._places.get(tuple(osm_name.split()))
            if place is not None:
                self._places.setdefault(tuple(written.split()), place)
        # Places OpenStreetMap names with an area after a comma ("Holy Trinity
        # Church, Bolarum"), by the name before the comma: the same name may
        # belong to another place elsewhere in the city.
        self._qualified: dict[tuple[str, ...], list[tuple[dict, str]]] = {}
        for place in places:
            if "," not in place["name"] or "lat" not in place:
                continue
            base, qualifier = place["name"].split(",", 1)
            words = tuple(token for token, _ in name_tokens(base))
            if words and qualifier.strip():
                self._qualified.setdefault(words, []).append((place, qualifier.strip()))

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_GAZETTEER_PATH) -> "PlaceResolver":
        with open(path, encoding="utf-8") as file:
            document = json.load(file)
        bbox = document.get("bbox_south_west_north_east")
        return cls(
            document["places"], document.get("osm_data_timestamp"), tuple(bbox) if bbox else None
        )

    def covers(self, latitude: float, longitude: float) -> bool:
        """Whether a point lies in the area REI covers (Greater Hyderabad)."""
        if self.bbox is None:
            return True
        south, west, north, east = self.bbox
        return south <= latitude <= north and west <= longitude <= east

    def __len__(self) -> int:
        return len(self._places)

    @staticmethod
    def _match(place: dict, mention: str, found_in: str) -> PlaceMatch:
        return PlaceMatch(
            name=place["name"],
            kind=place["kind"],
            precision=place["precision"],
            latitude=place.get("lat"),
            longitude=place.get("lon"),
            osm_ref=place.get("osm"),
            mention=mention,
            found_in=found_in,
        )

    def lookup(self, name: str, *, found_in: str) -> PlaceMatch | None:
        """The place of exactly this name, however it is spelled or capitalised."""
        place = self._places.get(tuple(token for token, _ in name_tokens(name)))
        return self._match(place, name.strip(), found_in) if place else None

    def qualified(self, name: str, *, found_in: str) -> list[tuple[PlaceMatch, str]]:
        """Places named "<name>, <area>", with the area: "Holy Trinity Church, Bolarum"."""
        words = tuple(token for token, _ in name_tokens(name))
        return [
            (self._match(place, name.strip(), found_in), qualifier)
            for place, qualifier in self._qualified.get(words, [])
        ]

    def suggest(self, query: str, limit: int = 8) -> list[PlaceMatch]:
        """Places with a position whose name starts with, or contains, the query."""
        wanted = " ".join(token for token, _ in name_tokens(query))
        if len(wanted) < 2:
            return []
        hits = [
            (not key.startswith(wanted), len(key), key, place)
            for words, place in self._places.items()
            if "lat" in place and wanted in (key := " ".join(words))
        ]
        return [self._match(place, place["name"], "suggestion") for *_, place in sorted(hits)[:limit]]

    def find_in(
        self, text: str | None, found_in: str, *, require_capital: bool = True
    ) -> list[PlaceMatch]:
        """Gazetteer places named in `text`, in order of appearance.

        The longest name wins ("Khajaguda Junction" over "Khajaguda"). In an
        article a name counts only when written as a name, with a capital;
        `require_capital=False` is for text a person typed as a place.
        """
        if not text:
            return []
        tokens = name_tokens(text)
        matches: list[PlaceMatch] = []
        index = 0
        while index < len(tokens):
            for length in range(min(_MAX_WORDS, len(tokens) - index), 0, -1):
                words = tuple(token for token, _ in tokens[index : index + length])
                place = self._places.get(words)
                start = tokens[index][1]
                written_as_name = text[start].isupper() or text[start].isdigit()
                if place is None or (require_capital and not written_as_name):
                    continue
                last_word_start = tokens[index + length - 1][1]
                end = last_word_start
                while end < len(text) and text[end].isalnum():
                    end += 1
                matches.append(self._match(place, text[start:end], found_in))
                index += length - 1
                break
            index += 1
        return matches

    def find_places(
        self, *, title: str | None, summary: str | None = None, body: str | None = None
    ) -> list[PlaceMatch]:
        """Every place the article names, the best one to locate it by first.

        A place in the headline outranks one in the summary, which outranks one
        in the body; within a field, the more specific kind of place comes first.
        """
        found: dict[str, PlaceMatch] = {}
        for field, text in zip(FIELD_ORDER, (title, summary, body), strict=True):
            in_field = self.find_in(text, field)
            in_field.sort(key=lambda match: _KIND_ORDER.index(match.kind))
            for match in in_field:
                found.setdefault(match.name, match)
        return list(found.values())


def spot_within(area: PlaceMatch, candidates: list[PlaceMatch]) -> PlaceMatch | None:
    """The first named spot (junction, flyover, landmark) that lies within `area`.

    An article whose headline names a locality and whose headline or summary
    also names a junction in it is about that junction: "Gachibowli: traffic
    curbs near IIIT Junction". A spot further away than WITHIN_KM is somewhere
    else, so it does not locate the event.
    """
    if not area.has_position:
        return None
    return next(
        (
            candidate
            for candidate in candidates
            if candidate.is_spot
            and candidate.name != area.name
            and candidate.distance_km(area) <= WITHIN_KM
        ),
        None,
    )


@lru_cache(maxsize=1)
def default_resolver() -> PlaceResolver:
    return PlaceResolver.from_file()


@lru_cache(maxsize=16)
def _resolver_from(filename: str | None, bbox: tuple[float, float, float, float]) -> PlaceResolver:
    path = DEFAULT_GAZETTEER_PATH.parent / filename if filename else None
    if path is None or not path.exists():
        # No place list yet for the city: nothing can be located by name, but
        # reviewer-placed points are still checked against the city's area.
        return PlaceResolver([], None, bbox)
    return PlaceResolver.from_file(path)


def resolver_for(city) -> PlaceResolver:
    """The resolver for a configured city (packages.cities.City)."""
    return _resolver_from(city.gazetteer, tuple(city.bbox))
