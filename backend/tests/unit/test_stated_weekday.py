"""The model's dates are checked against the weekday the article names.

The first cases are the real ones found on 2 and 4 November 2026: a model
counting weekdays from the publication day landed a day or more off.
"""

from datetime import datetime, timezone

from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.event_schema import AiReading
from packages.source_models import RawSourceRecord
from services.ai_reading import AiConfig, ArticleText, read_full_answer
from services.extraction.ai_event import check_reading_weekdays
from services.extraction.stated_weekday import check_stated_weekdays

HYDERABAD = get_city("hyderabad")
IST = HYDERABAD.tz
CONFIG = AiConfig.from_file()


def at(day: str, clock: str = "00:00") -> datetime:
    return datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=IST)


def check(words, start, end=None, *, published, known=True, context=()):
    return check_stated_weekdays(
        words=words,
        start=start,
        end=end,
        published_at=published,
        zone=IST,
        publication_day_known=known,
        context=context,
    )


# --- the real cases --------------------------------------------------------------------------


def test_friday_night_in_saturdays_paper_is_the_friday_before():
    # EVT-0BD7B3F5E453: published Sat 31 Oct, the model said Sun 1 Nov.
    result = check(
        "on Friday night",
        at("2026-11-01"),
        at("2026-11-01", "23:59:59"),
        published=at("2026-10-31", "15:45"),
    )
    assert result.start == at("2026-10-30") and result.end == at("2026-10-30", "23:59:59")
    assert result.note == (
        "The model dated “on Friday night” Sunday 1 Nov 2026, which is not a Friday; Friday 30 Oct 2026 "
        "is used instead, counted from the publication day Saturday 31 Oct 2026"
    )


def test_sunday_in_a_sunday_article_is_that_day():
    # EVT-153580661195: published Sun 18 Oct, the model said Fri 23 Oct.
    result = check("for over six hours on Sunday", at("2026-10-23"), published=at("2026-10-18", "13:38"))
    assert result.start == at("2026-10-18") and result.end is None


def test_a_weekday_beside_clock_times_is_read_from_the_sentence_before():
    # EVT-DAB920541B01: "on Monday ... between 1 pm and 7 pm", published Mon 2 Nov,
    # the model said Tue 3 Nov.
    summary = (
        "Hyderabad commuters are likely to face traffic restrictions on Monday as the Hyderabad "
        "Traffic Police implement diversions for a BJP padayatra from BJR Statue to MJ Market. "
        "Restrictions will remain in force on several key roads and junctions between 1 pm and 7 pm."
    )
    result = check(
        "between 1 pm and 7 pm",
        at("2026-11-03", "13:00"),
        at("2026-11-03", "19:00"),
        published=at("2026-11-02", "10:21"),
        context=("Hyderabad traffic diversions on Monday for BJP padayatra", summary, None),
    )
    assert result.start == at("2026-11-02", "13:00") and result.end == at("2026-11-02", "19:00")
    assert "the article names Monday beside these words" in result.note


def test_an_end_weekday_moves_only_the_end():
    result = check(
        "until Thursday evening",
        at("2026-10-12"),
        at("2026-10-16", "23:59:59"),
        published=at("2026-10-14", "13:43"),
    )
    assert result.start == at("2026-10-12")
    assert result.end == at("2026-10-15", "23:59:59")


# --- left alone ------------------------------------------------------------------------------


def test_dates_already_on_the_named_weekday_are_not_moved():
    for words, start, published in (
        ("on Wednesday at 7 pm", at("2026-10-14", "19:00"), at("2026-10-13", "17:00")),
        ("around 11 pm on Thursday", at("2026-10-15", "23:00"), at("2026-10-16", "09:00")),
        ("on Saturday", at("2026-10-17"), at("2026-10-18", "09:06")),
        ("Thursday evening", at("2026-10-15"), at("2026-10-17", "13:42")),
    ):
        result = check(words, start, published=published)
        assert result.note is None and result.start == start, words


def test_a_calendar_date_or_another_day_word_governs():
    # The article's own "Sunday, October 12" is not a Sunday in 2026; its date wins.
    for words in ("on Sunday, October 12", "from 10 am today", "on Monday or tomorrow", "11/10/2026 Sunday"):
        result = check(words, at("2026-10-12"), published=at("2026-10-08"))
        assert result.note is None, words


def test_clock_times_beside_a_calendar_date_are_left_alone():
    body = (
        "Hyderabad: Motorists will not be able to use Tank Bund Road between 5 am and 9 am "
        "on Sunday, October 12, as the cycling festival takes place."
    )
    result = check(
        "between 5 am and 9 am",
        at("2026-10-12", "05:00"),
        at("2026-10-12", "09:00"),
        published=at("2026-10-08"),
        context=("Cyclists to take over Tank Bund on Sunday morning", None, body),
    )
    assert result.note is None


def test_plural_weekdays_and_more_than_one_weekday_nearby_are_left_alone():
    assert check("on Sundays", at("2026-10-13"), published=at("2026-10-12")).note is None
    context = ("Rally on Saturday, roads shut on Monday", "Diversions between 1 pm and 7 pm.", None)
    result = check("between 1 pm and 7 pm", at("2026-11-03", "13:00"), published=at("2026-11-02"), context=context)
    assert result.note is None


def test_without_a_weekday_or_with_no_dates_nothing_changes():
    assert check("for 60 days", at("2026-10-13"), published=at("2026-10-12")).note is None
    assert check("on Friday", None, None, published=at("2026-10-12")).note is None


# --- choosing the day ------------------------------------------------------------------------


def test_next_and_last_are_honoured():
    published = at("2026-11-02", "09:00")  # a Monday
    assert check("next Monday", at("2026-11-03"), published=published).start == at("2026-11-09")
    assert check("last Saturday", at("2026-11-01"), published=published).start == at("2026-10-31")


def test_the_side_of_the_publication_day_follows_the_models_date():
    published = at("2026-10-21", "09:00")  # a Wednesday
    # The model meant the coming Saturday but miscounted to Friday 23rd.
    assert check("on Saturday", at("2026-10-23"), published=published).start == at("2026-10-24")
    # The model meant the past Monday but miscounted to Tuesday 20th.
    assert check("on Monday", at("2026-10-20"), published=published).start == at("2026-10-19")


def test_a_range_of_two_weekdays_is_checked_at_both_ends():
    result = check(
        "From Monday To Thursday",
        at("2026-10-20"),
        at("2026-10-23", "23:59:59"),
        published=at("2026-10-19", "22:29"),
    )
    assert result.start == at("2026-10-19") and result.end == at("2026-10-22", "23:59:59")


def test_an_unknown_publication_day_removes_the_wrong_dates():
    result = check("on Friday night", at("2026-11-01"), published=at("2026-10-31"), known=False)
    assert result.removed and result.start is None and result.end is None
    assert "publication day is not known" in result.note


# --- in the AI reading and in stored readings ------------------------------------------------


PUBLISHED = datetime(2026, 11, 2, 4, 51, tzinfo=timezone.utc)  # Mon 2 Nov, 10:21 in Hyderabad
TITLE = "Hyderabad traffic diversions on Monday for BJP padayatra; check affected routes"
SUMMARY = (
    "Hyderabad commuters are likely to face traffic restrictions on Monday as the Hyderabad Traffic "
    "Police implement diversions for a BJP padayatra from BJR Statue to MJ Market. Restrictions will "
    "remain in force on several key roads and junctions between 1 pm and 7 pm."
)


def padayatra_answer() -> dict:
    return {
        "articles": [
            {
                "id": "a1",
                "road_event": True,
                "why": "Diversions for a padayatra.",
                "city": "Hyderabad",
                "intent": "PUBLIC_PROCESSION",
                "impact": "DIVERSION",
                "places": [{"name": "MJ Market", "role": "AFFECTED", "quote": "to MJ Market"}],
                "period": {
                    "quote": "between 1 pm and 7 pm",
                    "start_date": "2026-11-03",
                    "start_time": "13:00",
                    "end_time": "19:00",
                },
            }
        ]
    }


def test_a_new_reading_gets_the_articles_weekday():
    article = ArticleText("a1", "art-padayatra", TITLE, SUMMARY, None, PUBLISHED, HYDERABAD)
    reading = read_full_answer(
        CONFIG, padayatra_answer(), [article], model="m", now=PUBLISHED, in_scope=lambda *_: True
    )["art-padayatra"]
    assert reading.period_read_by == "ai"
    assert reading.start_time == at("2026-11-02", "13:00") and reading.end_time == at("2026-11-02", "19:00")
    assert any("not a Monday" in item for item in reading.discarded)


def test_a_search_results_guessed_day_removes_the_wrong_dates_from_a_new_reading():
    article = ArticleText(
        "a1", "art-padayatra", TITLE, SUMMARY, None, PUBLISHED, HYDERABAD, publication_day_known=False
    )
    reading = read_full_answer(
        CONFIG, padayatra_answer(), [article], model="m", now=PUBLISHED, in_scope=lambda *_: True
    )["art-padayatra"]
    assert reading.period_text is None and reading.start_time is None


def test_a_stored_reading_is_corrected_when_its_event_is_derived_again():
    stored = AiReading(
        model="m",
        prompt_version="v",
        read_at=PUBLISHED,
        stage="full",
        is_road_event=True,
        period_text="between 1 pm and 7 pm",
        period_read_by="ai",
        start_time=at("2026-11-03", "13:00"),
        end_time=at("2026-11-03", "19:00"),
    )
    record = RawSourceRecord(
        source_id="telangana-today",
        external_id="https://news.example.com/padayatra",
        url="https://news.example.com/padayatra",
        title=TITLE,
        summary=SUMMARY,
        content_text=None,
        categories=[],
        published_at=PUBLISHED,
        retrieved_at=PUBLISHED,
        raw={"title": TITLE},
        content_hash=sha256_hex(TITLE + SUMMARY),
    )
    corrected = check_reading_weekdays(stored, record, IST)
    assert corrected.start_time == at("2026-11-02", "13:00")
    assert len(corrected.discarded) == 1
    # Checked again, it passes unchanged: no second note.
    assert check_reading_weekdays(corrected, record, IST) is corrected
