"""AI reading: the model's answer is checked against the article before use.

No network: the OpenRouter client is driven through httpx.MockTransport and
the model's answers are written out here.
"""

import json
from datetime import datetime, timezone

import httpx
import pytest

from packages.cities import get_city
from packages.common.hashing import sha256_hex
from packages.event_schema import AiReading, EventType, LocationClass
from packages.source_models import RawSourceRecord
from services.ai_reading.client import provider_name
from services.ai_reading.reading import DEFAULT_CONFIG_PATH
from services.ai_reading import (
    AiConfig,
    AiError,
    ArticleText,
    OpenRouterClient,
    contains,
    full_prompt,
    normalise,
    parse_json_answer,
    read_full_answer,
    read_triage_answer,
    triage_prompt,
)
from services.extraction import KeywordClassifier
from services.extraction.ai_event import build_event_from_ai
from services.geo_resolution import default_resolver
from services.ingestion import event_for_record
from tests.support import khajaguda_article

CONFIG = AiConfig.from_file()
HYDERABAD = get_city("hyderabad")
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)
PUBLISHED = datetime(2026, 10, 8, 5, 0, tzinfo=timezone.utc)

TITLE = "Cyclists to take over Tank Bund on Sunday morning"
SUMMARY = "Hyderabad cycling festival returns this weekend."
BODY = (
    "Hyderabad: Motorists will not be able to use Tank Bund Road between 5 am and 9 am "
    "on Sunday, October 12, as the cycling festival takes place. Traffic will be sent via "
    "Lower Tank Bund, the Hyderabad Traffic Police said."
)


def cycling_record() -> RawSourceRecord:
    raw = {"title": TITLE, "summary_html": SUMMARY, "content_html": BODY, "categories": []}
    return RawSourceRecord(
        source_id="telangana-today",
        external_id="https://news.example.com/cycling",
        url="https://news.example.com/cycling",
        title=TITLE,
        summary=SUMMARY,
        content_text=BODY,
        categories=[],
        published_at=PUBLISHED,
        retrieved_at=NOW,
        raw=raw,
        content_hash=sha256_hex(TITLE + SUMMARY + BODY),
    )


def cycling_article(key: str = "a1") -> ArticleText:
    return ArticleText(
        key=key,
        artifact_id="art-cycling",
        title=TITLE,
        summary=SUMMARY,
        body=BODY,
        published_at=PUBLISHED,
        city=HYDERABAD,
    )


def full_answer(**overrides) -> dict:
    entry = {
        "id": "a1",
        "road_event": True,
        "why": "Tank Bund Road closed for a cycling festival.",
        "city": "Hyderabad",
        "intent": "MARATHON",
        "impact": "CLOSURE",
        "cause": "cycling festival",
        "summary": "Tank Bund Road is closed on Sunday morning for a cycling festival.",
        "places": [
            {"name": "Tank Bund Road", "role": "CLOSED", "quote": "Motorists will not be able to use Tank Bund Road"},
            {"name": "Lower Tank Bund", "role": "DIVERSION_ROUTE", "quote": "Traffic will be sent via Lower Tank Bund"},
            # Not in the article: the model must not add it.
            {"name": "Banjara Hills", "role": "AFFECTED", "quote": "near Banjara Hills"},
        ],
        "period": {
            "quote": "between 5 am and 9 am on Sunday, October 12",
            "start_date": "2026-10-12",
            "end_date": "2026-10-12",
            "start_time": "05:00",
            "end_time": "09:00",
        },
        "authority": "Hyderabad Traffic Police",
        "evidence": "Motorists will not be able to use Tank Bund Road between 5 am and 9 am",
    }
    entry.update(overrides)
    return {"articles": [entry]}


def always_in_scope(article, reading) -> bool:
    return True


# --- checking text against the article ---------------------------------------------------


def test_contains_ignores_case_punctuation_and_spacing():
    text = normalise("Motorists will not be able to use Tank Bund Road, between 5 am.")
    assert contains(text, "tank bund road")
    assert contains(text, "use  Tank-Bund Road")
    assert contains(text, "Motorists will ... Tank Bund Road")
    assert not contains(text, "Necklace Road")
    assert not contains(text, "")


def test_contains_keeps_letters_of_other_scripts():
    text = normalise("ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಸಂಚಾರ ನಿರ್ಬಂಧ")
    assert contains(text, "ಸಂಚಾರ ನಿರ್ಬಂಧ")
    assert not contains(text, "ಮೈಸೂರು")


def test_json_answer_is_found_in_fences_and_stray_text():
    assert parse_json_answer('```json\n{"articles": []}\n```') == {"articles": []}
    assert parse_json_answer('Here you go: {"a": 1} hope it helps') == {"a": 1}
    with pytest.raises(AiError):
        parse_json_answer("no json at all")


# --- prompts --------------------------------------------------------------------------------


def test_prompts_carry_the_configured_choices_and_the_articles():
    triage = triage_prompt(CONFIG, [cycling_article()], NOW.date())
    full = full_prompt(CONFIG, [cycling_article()], NOW.date())
    for prompt in (triage, full):
        assert "MARATHON" in prompt and TITLE in prompt and '"feed_city": "Hyderabad"' in prompt
    assert "DIVERSION_ROUTE" in full and "Tank Bund Road between 5 am" in full


# --- reading the answers -----------------------------------------------------------------------


def test_triage_answer_gives_a_verdict_and_an_allowed_intent_only():
    answer = {
        "articles": [
            {"id": "a1", "road_event": True, "intent": "MARATHON", "why": "closure"},
            {"id": "a2", "road_event": True, "intent": "ALIEN_INVASION", "why": "?"},
            {"id": "zz", "road_event": True},
        ]
    }
    articles = [cycling_article("a1"), ArticleText("a2", "art-2", "x", None, None, PUBLISHED, HYDERABAD)]
    readings = read_triage_answer(CONFIG, answer, articles, model="m", now=NOW)
    assert readings["art-cycling"].intent is EventType.MARATHON
    assert readings["art-cycling"].stage == "triage"
    assert readings["art-2"].intent is None
    assert "ALIEN_INVASION" in readings["art-2"].discarded[0]


def test_full_answer_keeps_only_what_the_article_contains():
    reading = read_full_answer(
        CONFIG, full_answer(), [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]

    assert reading.is_road_event and reading.in_scope
    assert reading.intent is EventType.MARATHON
    assert reading.impact == "CLOSURE"
    assert [(p.name, p.role) for p in reading.places] == [
        ("Tank Bund Road", "CLOSED"),
        ("Lower Tank Bund", "DIVERSION_ROUTE"),
    ]
    assert reading.places[0].found_in == "body"
    assert any("Banjara Hills" in item for item in reading.discarded)
    assert reading.authority == "Hyderabad Traffic Police"
    assert reading.evidence.startswith("Motorists will not")


def test_period_is_read_by_rei_rules_first():
    body = "Hyderabad: Tank Bund Road will stay closed from October 10 to October 18 for repairs."
    article = ArticleText("a1", "art-works", "Tank Bund Road closed", None, body, PUBLISHED, HYDERABAD)
    answer = full_answer(
        places=[{"name": "Tank Bund Road", "role": "CLOSED"}],
        # The model's own dates are wrong; REI's rules read the article's words instead.
        period={"quote": "from October 10 to October 18", "start_date": "2026-10-11", "end_date": "2026-10-19"},
        evidence=None,
    )
    reading = read_full_answer(CONFIG, answer, [article], model="m", now=NOW, in_scope=always_in_scope)["art-works"]
    assert reading.period_read_by == "rules"
    assert reading.start_time.date().isoformat() == "2026-10-10"
    assert reading.end_time.date().isoformat() == "2026-10-18"


def test_period_falls_back_to_the_models_dates_only_with_the_articles_words():
    answer = full_answer(
        period={"quote": "between 5 am and 9 am", "start_date": "2026-10-12", "start_time": "05:00", "end_time": "09:00"}
    )
    reading = read_full_answer(
        CONFIG, answer, [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]
    assert reading.period_read_by == "ai"
    assert (reading.start_time.hour, reading.end_time.hour) == (5, 9)

    invented = full_answer(period={"quote": "all of next week", "start_date": "2026-10-13", "end_date": "2026-10-19"})
    reading = read_full_answer(
        CONFIG, invented, [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]
    assert reading.start_time is None and reading.period_text is None
    assert any("all of next week" in item for item in reading.discarded)


def test_invented_evidence_and_authority_are_dropped():
    answer = full_answer(evidence="The road will be closed for a month.", authority="GHMC Commissioner")
    reading = read_full_answer(
        CONFIG, answer, [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]
    assert reading.evidence is None and reading.authority is None
    assert len(reading.discarded) >= 2


def test_not_a_road_event_keeps_only_the_verdict():
    answer = {"articles": [{"id": "a1", "road_event": False, "why": "A festival notice.", "places": [{"name": "Tank Bund Road"}]}]}
    reading = read_full_answer(
        CONFIG, answer, [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]
    assert not reading.is_road_event and reading.places == [] and reading.why == "A festival notice."


# --- the event built from a reading ---------------------------------------------------------------


def checked_reading() -> AiReading:
    return read_full_answer(
        CONFIG, full_answer(), [cycling_article()], model="m", now=NOW, in_scope=always_in_scope
    )["art-cycling"]


def test_event_is_placed_at_the_closed_place_never_at_the_diversion_route():
    classifier = KeywordClassifier.for_city(HYDERABAD, default_resolver())
    record = cycling_record()
    classification = classifier.classify(record)
    # The keywords alone do not find this event.
    assert not classification.is_relevant

    event = event_for_record(
        record, classification, default_resolver(), now=NOW, city=HYDERABAD, ai=checked_reading()
    )
    assert event is not None
    assert event.detection.method == "ai_reading"
    assert event.event_type is EventType.MARATHON
    assert event.detection.location.place_name == "Tank Bund Road"
    assert event.detection.location_class is LocationClass.APPROXIMATE
    roles = {loc.name: loc.role for loc in event.detection.affected_locations}
    assert roles == {"Tank Bund Road": "CLOSED", "Lower Tank Bund": "DIVERSION_ROUTE"}
    # Every position is the OpenStreetMap place's.
    lower = next(l for l in event.detection.affected_locations if l.role == "DIVERSION_ROUTE")
    assert lower.reference.startswith("OpenStreetMap") and lower.resolution is LocationClass.APPROXIMATE
    # REI's date rules cannot read "on Sunday, October 12"; the model's checked times are used.
    assert (event.start_time.hour, event.end_time.hour) == (5, 9)
    assert event.detection.ai.period_read_by == "ai"
    assert event.status.value == "VALIDATION_REQUIRED"


def test_a_reading_with_only_route_places_gives_no_event_of_its_own():
    reading = checked_reading()
    reading.places = [p for p in reading.places if p.role == "DIVERSION_ROUTE"]
    classifier = KeywordClassifier.for_city(HYDERABAD, default_resolver())
    record = cycling_record()
    assert build_event_from_ai(
        record, classifier.classify(record), reading, now=NOW, resolver=default_resolver(), city=HYDERABAD
    ) is None


def test_a_reading_out_of_the_city_does_not_make_an_event():
    reading = checked_reading()
    reading.in_scope = False
    classifier = KeywordClassifier.for_city(HYDERABAD, default_resolver())
    record = cycling_record()
    assert event_for_record(
        record, classifier.classify(record), default_resolver(), now=NOW, city=HYDERABAD, ai=reading
    ) is None


def test_a_model_that_disagrees_with_the_keywords_is_shown_not_obeyed():
    record = khajaguda_article()
    classifier = KeywordClassifier.for_city(HYDERABAD, default_resolver())
    classification = classifier.classify(record)
    assert classification.is_relevant
    verdict = AiReading(
        model="m", prompt_version=CONFIG.version, read_at=NOW, stage="full",
        is_road_event=False, why="Not a road event.",
    )
    event = event_for_record(record, classification, default_resolver(), now=NOW, city=HYDERABAD, ai=verdict)
    assert event is not None and event.detection.method == "keyword_rules"
    assert event.detection.ai.is_road_event is False


# --- the OpenRouter client ------------------------------------------------------------------------


def _client(handler, **kwargs) -> OpenRouterClient:
    return OpenRouterClient(
        "test-key", "google/gemma-4-26b-a4b-it:free",
        transport=httpx.MockTransport(handler), sleep=lambda seconds: None, **kwargs,
    )


def _reply(content: str, model: str = "google/gemma-4-26b-a4b-it:free") -> httpx.Response:
    return httpx.Response(200, json={"model": model, "choices": [{"message": {"content": content}}]})


def test_client_sends_the_configured_model_reasoning_and_json_format():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        seen["auth"] = request.headers["Authorization"]
        return _reply('{"articles": []}')

    client = _client(handler, fallback_models=["nvidia/nemotron-3-super-120b-a12b:free"])
    result = client.chat_json("system", "user", max_tokens=100)
    assert result.content == {"articles": []}
    assert seen["models"] == ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-super-120b-a12b:free"]
    assert seen["reasoning"] == {"enabled": True}
    assert seen["response_format"] == {"type": "json_object"}
    assert seen["auth"] == "Bearer test-key"
    assert client.requests_sent == 1


def test_client_asks_a_thinking_model_not_to_think_only_when_configured():
    # NVIDIA NIM's Nemotron thinks by default and filled max_tokens with thinking (30 Oct 2026).
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _reply('{"articles": []}')

    _client(handler, reasoning=False, disable_thinking=True).chat_json("system", "user", max_tokens=100)
    _client(handler).chat_json("system", "user", max_tokens=100)
    assert bodies[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert "reasoning" not in bodies[0]
    # OpenRouter's requests stay exactly as they were.
    assert "chat_template_kwargs" not in bodies[1]


NVIDIA_NIM = "https://integrate.api.nvidia.com/v1"


def test_messages_name_the_configured_provider():
    assert provider_name("https://openrouter.ai/api/v1") == "OpenRouter"
    assert provider_name(NVIDIA_NIM) == "NVIDIA NIM"
    assert provider_name("https://llm.example.org/v1") == "llm.example.org"

    def refused(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "User not found."}})

    for base_url, expected in ((NVIDIA_NIM, "NVIDIA NIM answered 401"), (None, "OpenRouter answered 401")):
        client = _client(refused, **({"base_url": base_url} if base_url else {}))
        with pytest.raises(AiError) as raised:
            client.chat_json("system", "user", max_tokens=100)
        assert str(raised.value).startswith(expected)


def test_only_openrouter_is_asked_for_the_free_requests_left():
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.path)
        return httpx.Response(404)

    # NVIDIA NIM has no /key: it is not asked (no pointless request each run).
    assert _client(handler, base_url=NVIDIA_NIM).free_requests_remaining() is None
    assert asked == []


def test_client_waits_and_asks_again_when_rate_limited_and_counts_only_answers():
    replies = iter([
        httpx.Response(429, json={"error": {"message": "Provider returned error", "metadata": {"raw": "rate-limited upstream"}}}),
        _reply('{"ok": true}'),
    ])
    client = _client(lambda request: next(replies))
    assert client.chat_json("s", "u", max_tokens=10).content == {"ok": True}
    assert (client.attempts, client.requests_sent) == (2, 1)


def test_client_gives_up_on_a_bad_key_at_once():
    client = _client(lambda request: httpx.Response(401, json={"error": {"message": "No auth"}}))
    with pytest.raises(AiError) as error:
        client.chat_json("s", "u", max_tokens=10)
    assert "401" in str(error.value) and client.attempts == 1


def test_client_reads_the_free_requests_left():
    def handler(request):
        return httpx.Response(200, json={"data": {"free_model_daily_requests": {"used": 3, "limit": 50, "remaining": 47}}})

    assert _client(handler).free_requests_remaining() == 47


def test_config_names_only_event_types_rei_has(tmp_path):
    data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["intents"]["TELEPORTATION"] = "not a thing"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        AiConfig.from_file(bad)


def test_client_reports_an_answer_cut_off_at_the_token_limit():
    def handler(request):
        return httpx.Response(200, json={"model": "m", "choices": [{"finish_reason": "length", "message": {"content": '{"articles": [{"id": "a1", "road'}}]})

    client = _client(handler, retries=0)
    with pytest.raises(AiError) as error:
        client.chat_json("s", "u", max_tokens=10)
    assert "cut off" in str(error.value)
