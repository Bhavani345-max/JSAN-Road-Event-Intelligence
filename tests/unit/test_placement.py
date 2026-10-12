"""Placing events by the names their sources state (services/geo_resolution/placement.py).

Real Hyderabad and Bengaluru place lists; Google Maps answers are written out
here and served through httpx.MockTransport, so nothing reaches the network.
"""

import json
from datetime import datetime, timezone

import httpx

from packages.cities import get_city
from services.ai_reading import AiConfig, ArticleText, read_full_answer
from services.geo_resolution import resolver_for
from services.geo_resolution.google_maps import GoogleMapsLookup
from services.geo_resolution.placement import Mention, Placer

HYDERABAD = get_city("hyderabad")
BENGALURU = get_city("bengaluru")
HYD = resolver_for(HYDERABAD)
BLR = resolver_for(BENGALURU)


def placer(city=HYDERABAD, resolver=HYD, google=None) -> Placer:
    return Placer.for_city(resolver, city, google)


def google_answering(tmp_path, answers: dict[str, list[dict]], daily_credits: int = 60) -> GoogleMapsLookup:
    """A Google Maps lookup whose answers are keyed by a word of the query."""
    asked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["q"]
        asked.append(query)
        places = next((value for word, value in answers.items() if word in query), [])
        return httpx.Response(200, json={"places": places, "credits": 1})

    lookup = GoogleMapsLookup("test-key", tmp_path / "cache.json", daily_credits=daily_credits, transport=httpx.MockTransport(handler))
    lookup.asked = asked
    return lookup


# --- OpenStreetMap ------------------------------------------------------------------------


def test_a_same_name_place_in_the_area_the_article_names_wins():
    # OSM has a "Holy Trinity Church" in west Hyderabad and a "Holy Trinity Church, Bolarum".
    placement = placer().place(
        [Mention("Holy Trinity Church Road", "CLOSED", "body"), Mention("Ammuguda Road", "CLOSED", "body")],
        title="Firearms heist solved, but Bolarum roads in SCB remain shut",
        body="LMA shut Richardson Road, Ammuguda Road, Holy Trinity Church Road after an arms theft.",
    )
    assert placement.best.name == "Holy Trinity Church, Bolarum"
    assert placement.best.how == "qualified"
    assert placement.best.reference.startswith("OpenStreetMap")


def test_junction_words_are_swapped_and_added():
    p = placer()
    text = dict(title="Traffic diversions", body="Old PS Saifabad and Indira Gandhi Rotary")
    rotary = p.place([Mention("Indira Gandhi Rotary", "AFFECTED", "body")], **text).best
    assert rotary.name == "Indira Gandhi Statue"
    saifabad = p.place([Mention("Old PS Saifabad", "AFFECTED", "body")], **text).best
    assert saifabad.name == "Old PS Saifabad Jn"


def test_a_road_matched_only_to_a_locality_elsewhere_is_not_placed():
    # Bengaluru's OSM "Sanjay Nagar" is another locality, 15 km from Sanjaynagar Main Road.
    placement = placer(BENGALURU, BLR).place(
        [Mention("Sanjaynagar Main Road", None, "title")], title="Sanjaynagar Main Road work near completion"
    )
    assert placement.best is None
    assert [m.name for m in placement.unplaced] == ["Sanjaynagar Main Road"]


def test_the_event_is_never_placed_at_a_diversion_route():
    placement = placer().place(
        [Mention("Lower Tank Bund", "DIVERSION_ROUTE", "body"), Mention("Tank Bund Road", "CLOSED", "body")],
        title="Tank Bund closed",
    )
    assert placement.best.name == "Tank Bund Road"
    assert {p.name for p in placement.placed} == {"Tank Bund Road", "Lower Tank Bund"}


def test_the_first_named_place_comes_before_a_more_specific_one_named_later():
    placement = placer().place(
        [Mention("KBR Park", None, "title"), Mention("Jubilee Check Post Jn", None, "summary")],
        title="Why has one-way traffic system around KBR Park been made permanent",
    )
    assert placement.best.name == "KBR Park"


def test_agencies_are_not_places():
    placement = placer().place([Mention("GHMC", None, "title")], title="GHMC ditches drain work")
    assert placement.best is None and placement.unplaced == []


# --- whole names in articles without an AI reading ---------------------------------------------


def test_whole_names_skip_a_match_inside_a_longer_name_and_extend_a_structure():
    p = placer()
    names = [m.name for m in p.whole_mentions("The patient was taken to Lake City Hospital near Tank Bund.", "summary")]
    assert "City Hospital" not in names
    names = [m.name for m in p.whole_mentions("Waterlogging near Hitech City railway station disrupted traffic.", "summary")]
    assert names == ["Hitech City railway station"]


def test_a_headline_written_like_this_is_not_extended_with_its_capitals():
    names = [m.name for m in placer().whole_mentions("Bathukamma Festival: Hyderabad Plans Tank Bund Events", "title")]
    assert "Tank Bund" in names


# --- Google Maps ----------------------------------------------------------------------------------


def test_google_places_a_name_osm_does_not_know_and_says_so(tmp_path):
    google = google_answering(tmp_path, {
        "Lok Bhavan": [{"title": "LOK BHAVAN", "address": "Raj Bhavan Rd, Somajiguda, Hyderabad", "latitude": 17.419672, "longitude": 78.46051, "cid": "42"}],
    })
    placement = placer(google=google).place([Mention("Lok Bhavan", "VENUE", "body")], title="March to Lok Bhavan")
    assert placement.best.name == "LOK BHAVAN"
    assert placement.best.reference == "Google Maps (Serper.dev) place 42"
    assert google.asked == ["Lok Bhavan, Hyderabad"]


def test_google_answers_that_do_not_carry_the_name_are_refused(tmp_path):
    google = google_answering(tmp_path, {
        # The city's own name is not the place's name.
        "Bengaluru roads": [{"title": "Bengaluru", "address": "Bengaluru, Karnataka", "latitude": 12.97, "longitude": 77.59}],
        # Another place, and one outside the city.
        "Byam Road": [{"title": "Road", "address": "Old Airport Rd, Hyderabad", "latitude": 17.4587, "longitude": 78.4705}],
        "Kothaguda Minar": [{"title": "Kothaguda Minar", "address": "", "latitude": 18.10738, "longitude": 78.842064}],
    })
    blr = placer(BENGALURU, BLR, google).place([Mention("Bengaluru roads", "AFFECTED", "title")], title="Heavy rain")
    assert blr.best is None
    hyd = placer(google=google)
    assert hyd.place([Mention("Byam Road", "CLOSED", "body")], title="Roads shut").best is None
    assert hyd.place([Mention("Kothaguda Minar", "AFFECTED", "body")], title="Diversions").best is None


def test_google_is_asked_once_per_name_and_within_the_days_credits(tmp_path):
    google = google_answering(tmp_path, {}, daily_credits=1)
    p = placer(google=google)
    p.place([Mention("Nowhere Lane One", "AFFECTED", "body")], title="t")
    p.place([Mention("Nowhere Lane One", "AFFECTED", "body")], title="t")
    p.place([Mention("Nowhere Lane Two", "AFFECTED", "body")], title="t")
    # One credit a day: the first name is asked once (its empty answer is kept), the second not at all.
    assert google.asked == ["Nowhere Lane One, Hyderabad"]
    assert google.credits_used_today() == 1
    again = GoogleMapsLookup("test-key", tmp_path / "cache.json", daily_credits=1, allow_network=False)
    assert again.places("Nowhere Lane One, Hyderabad") == []


# --- dates ------------------------------------------------------------------------------------------


def test_a_measure_that_began_on_a_day_and_continues_has_no_end():
    config = AiConfig.from_file()
    body = "LMA shut Richardson Road on August 31, and the roads remain shut."
    article = ArticleText("a1", "art", "Bolarum roads remain shut", None, body, datetime(2026, 10, 8, tzinfo=timezone.utc), HYDERABAD)
    answer = {"articles": [{
        "id": "a1", "road_event": True, "city": "Hyderabad", "intent": "EMERGENCY_ROAD_CLOSURE",
        "places": [{"name": "Richardson Road", "role": "CLOSED"}],
        "period": {"quote": "on August 31", "start_date": "2026-08-31", "end_date": None},
    }]}
    reading = read_full_answer(config, answer, [article], model="m", now=datetime(2026, 10, 9, tzinfo=timezone.utc),
                               in_scope=lambda a, r: True)["art"]
    assert reading.start_time.date().isoformat() == "2026-08-31"
    assert reading.end_time is None
    assert reading.prompt_version == config.full_version
