from services.extraction.attribution import find_attributions


def test_finds_the_authority_an_article_says_announced_the_measure():
    text = "The Cyberabad Traffic Police have issued a traffic advisory for IIIT Junction."
    assert find_attributions(text) == ["Cyberabad Police"]


def test_a_specific_force_is_not_also_counted_as_traffic_police():
    text = "Hyderabad Traffic Police announced diversions. GHMC closed the road for repairs."
    assert find_attributions(text) == ["Hyderabad Police", "GHMC"]


def test_a_police_station_is_a_place_not_an_announcer():
    text = "Vehicles will be diverted at Gachibowli Traffic Police Station."
    assert find_attributions(text) == []


def test_the_generic_traffic_police_is_dropped_once_a_force_is_named():
    text = "Cyberabad Police issued an advisory. The traffic police urged commuters to plan ahead."
    assert find_attributions(text) == ["Cyberabad Police"]
    assert find_attributions("The traffic police announced diversions.") == ["Traffic Police"]


def test_an_authority_merely_mentioned_is_not_an_attribution():
    assert find_attributions("The GHMC headquarters is near the lake.") == []
    assert find_attributions("Residents blamed the traffic police.") == []


def test_no_text_no_attribution():
    assert find_attributions(None, "") == []
