"""Finding a place or postcode on the map (decision 0055).

No network: Nominatim is driven through httpx.MockTransport with answers in its
jsonv2 shape; the throttle runs on a fake clock.
"""

import httpx
import pytest

from app.services.place_search import PlaceSearch, PlaceSearchFailed, is_postcode, local_results
from packages.cities import get_city

GACHIBOWLI_WARD = {
    "lat": "17.4407", "lon": "78.3530", "name": "500032", "type": "postcode",
    "display_name": "500032, Ward 105 Gachibowli, Greater Hyderabad Municipal Corporation West Zone, Telangana, India",
    "boundingbox": ["17.4207", "17.4607", "78.3330", "78.3730"],
}


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def nominatim(seen: list[httpx.Request], rows=None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=[GACHIBOWLI_WARD] if rows is None else rows)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_postcodes_are_recognised():
    for code in ("500032", "560 001", "00-950", "SW1A 1AA", "D02 X285", "1012 AB"):
        assert is_postcode(code), code
    for words in ("Gachibowli", "Marszałkowska 10", "KBR Park"):
        assert not is_postcode(words), words


def test_a_pincode_is_asked_as_a_postcode_within_the_country_and_city():
    seen: list[httpx.Request] = []
    clock = Clock()
    search = PlaceSearch(client=nominatim(seen), clock=clock.time, sleep=clock.sleep)
    results = search.search("500032", get_city("hyderabad"))
    params = seen[0].url.params
    assert params["postalcode"] == "500032" and "q" not in params
    assert params["countrycodes"] == "in"
    south, west, north, east = get_city("hyderabad").bbox
    assert params["viewbox"] == f"{west},{north},{east},{south}"
    assert seen[0].headers["User-Agent"].startswith("JSAN-REI/1.0")
    ward = results[-1]
    assert ward["source"] == "nominatim" and ward["name"] == "500032"
    assert ward["detail"].startswith("Ward 105 Gachibowli") and ward["in_area"] is True
    assert ward["box"] == [78.333, 17.4207, 78.373, 17.4607]


def test_the_citys_own_place_list_answers_first_and_alone_while_typing():
    local = local_results("Gachibowli", get_city("hyderabad"))
    assert local and local[0]["source"] == "place_list" and "Gachibowli" in local[0]["name"]
    # A country entry has no place list of its own: nothing until Enter.
    assert local_results("Gachibowli", get_city("india")) == []


def test_at_most_one_request_a_second_and_answers_are_remembered():
    seen: list[httpx.Request] = []
    clock = Clock()
    search = PlaceSearch(client=nominatim(seen, rows=[]), clock=clock.time, sleep=clock.sleep)
    search.search("Warszawa Centralna", get_city("poland"))
    search.search("Kraków Główny", get_city("poland"))
    assert clock.slept and clock.slept[0] == pytest.approx(1.1)
    search.search("warszawa  centralna", get_city("poland"))  # the same question again
    assert len(seen) == 2


def test_a_refusal_is_a_failure():
    with pytest.raises(PlaceSearchFailed):
        PlaceSearch(client=nominatim([], status=429)).search("Dublin Port", get_city("ireland"))


def test_the_route(app, client):
    seen: list[httpx.Request] = []
    app.state.place_search = PlaceSearch(client=nominatim(seen))
    typing = client.get("/api/places/search", params={"q": "Gachi", "city": "hyderabad", "local_only": "true"})
    assert typing.status_code == 200 and seen == []
    assert all(r["source"] == "place_list" for r in typing.json()["results"])

    entered = client.get("/api/places/search", params={"q": "500032", "city": "hyderabad"}).json()
    assert entered["scope"] == "Hyderabad" and entered["attribution"] == "© OpenStreetMap contributors"
    assert entered["results"][-1]["name"] == "500032" and len(seen) == 1

    assert client.get("/api/places/search", params={"q": "x1", "city": "atlantis"}).status_code == 422
