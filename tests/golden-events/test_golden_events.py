"""Golden test: a known feed must always produce exactly these events.

If detection rules or event creation change on purpose, review the difference
and update expected_events.json in the same change.
"""

import json

from services.extraction import KeywordClassifier, build_event_from_article
from tests.support import FEEDS, RETRIEVED_AT

COMPARED_FIELDS = (
    "title",
    "source_reference",
    "event_type",
    "city",
    "affected_road",
    "status",
    "start_time",
    "end_time",
    "severity",
    "direction",
    "geometry",
    "confidence",
)


def test_sample_feed_produces_the_expected_events(records):
    classifier = KeywordClassifier.from_file()
    produced = []
    seen = set()
    for record in records:
        if record.external_id in seen:
            continue
        seen.add(record.external_id)
        classification = classifier.classify(record)
        if classification.is_relevant:
            event = build_event_from_article(record, classification, now=RETRIEVED_AT)
            dumped = event.model_dump(mode="json")
            produced.append(
                {name: dumped[name] for name in COMPARED_FIELDS}
                | {"matched_keywords": event.detection.matched_keywords}
            )

    expected = json.loads((FEEDS / "expected_events.json").read_text(encoding="utf-8"))
    assert produced == expected
