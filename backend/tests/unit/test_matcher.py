"""Cross-source matching rules (6 October 2026): same, possible, or different."""

from datetime import datetime, timedelta, timezone

from services.merging import EventFacts, MatchClass, compare, headline_similarity

DAY = timedelta(days=1)
T0 = datetime(2026, 9, 26, tzinfo=timezone.utc)
KHAJAGUDA = (78.3817, 17.4227)
NEAR_KHAJAGUDA = (78.3890, 17.4280)  # about 1 km away


def facts(event_id, **overrides) -> EventFacts:
    values = dict(
        event_id=event_id, source_id="telangana-today", source_tier=4, official=False,
        title="Traffic diversions at Khajaguda junction for 60 days", url=None,
        event_type="TRAFFIC_DIVERSION", start=None, end=None, direction=None,
        position=KHAJAGUDA, approximate=True, place_kind="junction", place_name="Khajaguda Jn",
        places=frozenset({"khajaguda jn"}), roads=frozenset(), reported_at=T0,
        reviewed=False, source_status=None, city="Hyderabad",
    )  # fmt: skip
    values.update(overrides)
    return EventFacts(**values)


# --- clearly the same ------------------------------------------------------------------


def test_the_same_article_from_two_sources_is_the_same_event_and_merges():
    a = facts("A", source_id="newsmeter")
    b = facts("B", source_id="google-news-serper", title="Hyderabad: Traffic diversions at Khajaguda junction for 60 days")
    match = compare(a, b)
    assert match.classification is MatchClass.SAME
    assert match.auto_merge
    assert "the same article (identical headline or link)" in match.reasons


def test_the_same_link_is_the_same_article_whatever_the_headline():
    match = compare(facts("A", url="https://x.in/a"), facts("B", title="Other words", url="https://x.in/a"))
    assert match.classification is MatchClass.SAME


def test_two_reports_with_the_same_type_period_and_place_are_the_same_event():
    period = dict(start=T0, end=T0 + 59 * DAY)
    a = facts("A", **period)
    b = facts("B", source_id="the-hindu", title="Khajaguda junction curbs from September 26", **period)
    match = compare(a, b)
    assert match.classification is MatchClass.SAME and match.auto_merge


# --- possible: a reviewer decides --------------------------------------------------------


def test_repeated_articles_about_one_event_are_a_possible_match():
    a = facts("A", title="KBR flyover plan changed due to success of one way traffic", event_type=None,
              place_kind="landmark", place_name="KBR Park", places=frozenset({"kbr park"}))
    b = facts("B", source_id="siasat", title="GHMC revises KBR Park flyover plans, mulls permanent one-way", event_type=None,
              place_kind="landmark", place_name="KBR Park", places=frozenset({"kbr park"}))  # fmt: skip
    match = compare(a, b)
    assert match.classification is MatchClass.POSSIBLE
    assert not match.auto_merge
    assert "both name kbr park" in match.reasons


def test_conflicting_dates_are_kept_and_block_an_automatic_merge():
    a = facts("A", start=T0, end=T0 + 59 * DAY)
    b = facts("B", source_id="the-hindu", title="Traffic diversions at Khajaguda junction for 60 days",
              start=T0, end=T0 + 89 * DAY)  # fmt: skip
    match = compare(a, b)
    assert match.classification is MatchClass.SAME
    assert [c["field"] for c in match.conflicts] == ["end_time"]
    assert not match.auto_merge
    assert any("disagree" in note for note in match.notes)


def test_conflicting_precise_positions_are_kept_and_block_an_automatic_merge():
    a = facts("A", approximate=False, roads=frozenset({"nh 65"}), place_kind=None, place_name=None)
    b = facts("B", source_id="the-hindu", approximate=False, position=NEAR_KHAJAGUDA,
              roads=frozenset({"nh 65"}), place_kind=None, place_name=None)  # fmt: skip
    match = compare(a, b)
    assert "geometry" in [c["field"] for c in match.conflicts]
    assert not match.auto_merge


def test_an_official_source_and_a_news_report_are_never_merged_automatically():
    official = facts("A", source_id="tfl-road-disruptions", source_tier=1, official=True, approximate=False)
    news = facts("B", source_id="the-hindu", title=official.title, approximate=True)
    match = compare(official, news)
    assert match.classification is MatchClass.SAME
    assert not match.auto_merge
    assert any("official source and a news report" in note for note in match.notes)


def test_two_news_reports_can_merge_automatically_but_not_once_reviewed():
    a = facts("A")
    b = facts("B", source_id="google-news-serper")
    assert compare(a, b).auto_merge
    assert not compare(a, facts("B", source_id="google-news-serper", reviewed=True)).auto_merge


# --- clearly different ---------------------------------------------------------------------


def test_different_events_on_the_same_road_are_different():
    works = facts("A", event_type="ROAD_CONSTRUCTION", roads=frozenset({"nh 65"}), title="NH-65 widening works")
    flooding = facts("B", event_type="FLOODING", roads=frozenset({"nh 65"}), title="NH-65 waterlogged after rain")
    assert compare(works, flooding).classification is MatchClass.DIFFERENT


def test_similar_names_on_different_dates_are_different():
    september = facts("A", start=T0, end=T0 + 2 * DAY)
    november = facts("B", source_id="the-hindu", start=T0 + 50 * DAY, end=T0 + 52 * DAY)
    match = compare(september, november)
    assert match.classification is MatchClass.DIFFERENT
    assert match.reasons == ("stated periods do not overlap",)


def test_events_at_nearby_but_different_junctions_are_different():
    a = facts("A")
    b = facts("B", source_id="the-hindu", title="Traffic diversions at Biodiversity junction",
              position=NEAR_KHAJAGUDA, place_name="Biodiversity Junction",
              places=frozenset({"biodiversity junction"}))  # fmt: skip
    match = compare(a, b)
    assert match.classification is MatchClass.DIFFERENT
    assert "different junctions" in match.reasons[0]


def test_two_records_of_one_official_source_are_different_events():
    a = facts("A", source_id="tfl-road-disruptions", official=True, source_tier=1)
    b = facts("B", source_id="tfl-road-disruptions", official=True, source_tier=1)
    assert compare(a, b).classification is MatchClass.DIFFERENT


def test_reports_weeks_apart_with_no_dates_are_different():
    a = facts("A")
    b = facts("B", source_id="the-hindu", reported_at=T0 + 30 * DAY)
    assert compare(a, b).classification is MatchClass.DIFFERENT


def test_different_cities_are_different():
    assert compare(facts("A"), facts("B", city="London")).classification is MatchClass.DIFFERENT


def test_nothing_in_common_is_different():
    other = facts("B", title="Waterlogging at Tolichowki", event_type=None, position=(78.41, 17.40),
                  place_kind="area", place_name="Tolichowki", places=frozenset({"tolichowki"}))  # fmt: skip
    assert compare(facts("A"), other).classification is MatchClass.DIFFERENT


def test_headline_similarity_ignores_datelines_plurals_and_common_words():
    assert headline_similarity("Hyderabad: GHMC revises KBR Park flyovers", "GHMC revises KBR Park flyover") == 1.0
    assert headline_similarity("Traffic in the city", "Road and traffic") == 0.0
