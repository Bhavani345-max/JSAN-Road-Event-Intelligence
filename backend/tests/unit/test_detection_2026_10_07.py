"""Detection rules of 7 October 2026: every kind of road event the user listed.

Each kind is detected, and typed, when a story reports a measure on the road
(a closure, diversion or restriction) in Hyderabad. A word that names an event
(a marathon, a match, a VIP visit) never makes a story a road event by itself.
The headlines are written in the style of Hyderabad papers (test data).
"""

from datetime import datetime, timezone

import pytest

from packages.event_schema import EventType
from packages.source_models import RawSourceRecord
from services.extraction import KeywordClassifier

NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)
T = EventType


def article(title, summary=""):
    return RawSourceRecord(
        source_id="test-news", external_id=title, url=None, title=title, summary=summary or None,
        content_text=None, categories=["Hyderabad"], published_at=NOW, retrieved_at=NOW,
        raw={}, content_hash="0" * 64,
    )  # fmt: skip


@pytest.fixture(scope="module")
def classifier():
    return KeywordClassifier.from_file()


@pytest.mark.parametrize(
    "title, expected",
    [
        # Marathons
        ("Hyderabad Marathon: traffic restrictions on Necklace Road on Sunday", T.MARATHON),
        ("Traffic diversions in Hyderabad for 10K run at Gachibowli", T.MARATHON),
        # Parades
        ("Traffic restrictions in Hyderabad for Republic Day parade at Parade Grounds", T.PUBLIC_PROCESSION),
        # Sporting events
        ("IPL match at Uppal stadium: Hyderabad traffic police issue advisory", T.SPORTING_EVENT),
        ("Hyderabad: traffic diversions around Gachibowli stadium for cricket match", T.SPORTING_EVENT),
        # Road construction
        ("Hyderabad: road dug up again at Srinagar Colony for pipeline works", T.ROAD_CONSTRUCTION),
        # Works with a diversion: the diversion is the event on the road, the works its cause.
        ("Hyderabad flyover works: traffic diversions at Khajaguda for 60 days", T.TRAFFIC_DIVERSION),
        # Lane restrictions
        ("Hyderabad: one lane closed on PVNR Expressway for repairs", T.LANE_RESTRICTION),
        # Police diversions
        ("Hyderabad traffic police announce traffic diversion at Panjagutta", T.TRAFFIC_DIVERSION),
        # Flooding
        ("Hyderabad: roads flooded in Tolichowki after overnight rain, traffic hit", T.FLOODING),
        ("Hyderabad waterlogging: traffic diverted at Raj Bhavan Road", T.FLOODING),
        # Emergency closures
        ("Hyderabad: road closed after accident on ORR near Shamshabad", T.EMERGENCY_ROAD_CLOSURE),
        ("Hyderabad: stretch closed following pipeline burst at Ameerpet", T.EMERGENCY_ROAD_CLOSURE),
        # Accidents
        ("Hyderabad: traffic jam on ORR after a lorry accident near Gachibowli", T.ACCIDENT),
        # Public events
        ("Numaish: Hyderabad traffic police announce traffic restrictions at Nampally", T.SPECIAL_EVENT),
        ("Bathukamma celebrations: traffic restrictions around Tank Bund in Hyderabad", T.SPECIAL_EVENT),
        # Meetings, speeches and roadshows
        ("Traffic restrictions around LB Stadium for CM's public meeting in Hyderabad", T.SPECIAL_EVENT),
        ("Hyderabad: roads closed near Parade Grounds for Vijaya Sankalpa Sabha", T.SPECIAL_EVENT),
        ("Traffic diversions in Hyderabad for roadshow at Secunderabad", T.SPECIAL_EVENT),
        # VIP movements
        ("PM visit: traffic restrictions in Hyderabad on Tuesday", T.VIP_MOVEMENT),
        ("Hyderabad traffic restrictions for VIP movement at Begumpet", T.VIP_MOVEMENT),
        # A VIP visit with a public meeting: the specific kind wins over "public event".
        ("Traffic restrictions in Hyderabad for PM visit and public meeting at LB Stadium", T.VIP_MOVEMENT),
        # Temporary turn restrictions
        ("Hyderabad: U-turn at Masab Tank closed for a week", T.TURN_RESTRICTION),
        ("No right turn at Khairatabad junction from Monday, Hyderabad traffic police say", T.TURN_RESTRICTION),
        # Bridge / tunnel restrictions
        ("Hyderabad: Punjagutta flyover closed for repairs till Friday", T.BRIDGE_TUNNEL_RESTRICTION),
        ("Hyderabad: Kukatpally underpass shut for maintenance tonight", T.BRIDGE_TUNNEL_RESTRICTION),
        # Weather-related closures
        ("Hyderabad: tree fall blocks road at Banjara Hills, traffic diverted", T.WEATHER_CLOSURE),
        ("Heavy rain in Hyderabad: road closed at Somajiguda", T.WEATHER_CLOSURE),
    ],
)
def test_each_kind_of_road_event_is_detected_and_typed(classifier, title, expected):
    result = classifier.classify(article(title))
    assert result.is_relevant, result.matched_keywords
    assert result.event_type is expected, result.matched_keywords


@pytest.mark.parametrize(
    "title",
    [
        "Hyderabad Marathon 2026: registrations open for runners",
        "IPL: Sunrisers Hyderabad win at Uppal stadium",
        "Chief Minister visits Hyderabad schools to review mid-day meals",
        "Heavy rain likely in Hyderabad this week, says IMD",
        "Bathukamma celebrations begin across Telangana",
        "Chief Minister addresses public meeting in Hyderabad, promises jobs",
        "Hyderabad: GHMC plans storm water drains in 30 colonies",
    ],
)
def test_an_event_without_a_measure_on_the_road_is_not_a_road_event(classifier, title):
    assert not classifier.classify(article(title)).is_relevant


def test_an_accident_only_counts_when_one_happened(classifier):
    result = classifier.classify(article(
        "Whose silt is it anyway? GHMC ditches drain cleaning work at Ramnagar",
        "Residents urge GHMC to clear the silt to prevent traffic jams and accidents in Ramnagar.",
    ))  # fmt: skip
    assert result.event_type is not T.ACCIDENT


def test_a_storm_water_drain_is_not_a_storm(classifier):
    result = classifier.classify(article("Hyderabad: traffic diversion at Lakdikapul as storm water drain is laid"))
    assert result.is_relevant and "storm" not in result.matched_keywords
    assert result.event_type is T.TRAFFIC_DIVERSION


def test_a_plain_closure_states_no_type(classifier):
    # Planned or an emergency? The story does not say, so neither does REI.
    assert classifier.classify(article("Hyderabad: road closure at Lakdikapul this weekend")).event_type is None
