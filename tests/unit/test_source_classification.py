"""Source classification (6 October 2026): every source says what kind of body it is.

The class (official, open data, partner, publisher, discovery, commercial) is
separate from the format (RSS, API, …) and from REI's tier. Publishers and
search are discovery-only and never above tier 4, whatever an article says
the police announced.
"""

import pytest
from pydantic import ValidationError

from connectors.registry import registered_sources
from packages.source_models import (
    CostCategory,
    IntegrationStatus,
    SourceClass,
    SourceDefinition,
    SourceType,
    TermsStatus,
)

REGISTRY = {source.definition.source_id: source.definition for source in registered_sources("k")}


def test_every_source_but_manual_entry_has_a_class():
    unclassified = [
        source_id for source_id, d in REGISTRY.items() if d.source_class is None
    ]
    assert unclassified == ["manual-entry"]


@pytest.mark.parametrize(
    "source_id, source_class, tier",
    [
        ("telangana-today", SourceClass.PUBLISHER, 4),
        ("google-news-serper", SourceClass.DISCOVERY, 4),
        ("hyderabad-traffic-police", SourceClass.AUTHORITATIVE_OFFICIAL, 1),
        ("ghmc", SourceClass.AUTHORITATIVE_OFFICIAL, 1),
        ("open-data-telangana", SourceClass.GOVERNMENT_OPEN_DATA, 1),
        ("tgsrtc", SourceClass.PARTNER, 2),
        ("tomtom-traffic-incidents", SourceClass.COMMERCIAL, None),
        ("waze-for-cities", SourceClass.COMMERCIAL, None),
    ],
)
def test_sources_are_classified_and_tiered(source_id, source_class, tier):
    definition = REGISTRY[source_id]
    assert definition.source_class is source_class
    assert definition.source_tier == tier


def test_publishers_and_search_are_discovery_only_and_tier_four():
    for definition in REGISTRY.values():
        if definition.source_class in (SourceClass.PUBLISHER, SourceClass.DISCOVERY):
            assert definition.discovery_only and definition.source_tier == 4, definition.source_id
        if definition.discovery_only:
            assert definition.source_tier == 4, definition.source_id


def test_official_sources_are_never_discovery_only():
    for definition in REGISTRY.values():
        if definition.source_class in (
            SourceClass.AUTHORITATIVE_OFFICIAL,
            SourceClass.GOVERNMENT_OPEN_DATA,
        ):
            assert not definition.discovery_only, definition.source_id
            assert definition.source_tier == 1, definition.source_id


def test_commercial_providers_have_no_tier_until_approved():
    for definition in REGISTRY.values():
        if definition.source_class is SourceClass.COMMERCIAL:
            assert definition.source_tier is None, definition.source_id
            assert definition.integration_status in (
                IntegrationStatus.REQUIRES_ACCESS,
                IntegrationStatus.NOT_USABLE,
            )


def test_hyderabad_sources_say_where_they_are_about():
    for source_id in ("telangana-today", "the-hindu", "hyderabad-traffic-police", "ghmc"):
        definition = REGISTRY[source_id]
        assert (definition.country, definition.city) == ("IN", "hyderabad"), source_id


def test_no_source_claims_a_legal_review_or_unconditional_commercial_rights():
    """No terms have had a formal legal review. A licence that has been read may
    be recorded as permitting testing, or as restricting use, but never as
    settling commercial use."""
    for definition in REGISTRY.values():
        assert definition.terms_reviewed is False, definition.source_id
        assert definition.terms_status is not TermsStatus.PERMITS_COMMERCIAL, definition.source_id
        assert definition.commercial_use.value != "PERMITTED", definition.source_id


def test_a_cost_is_recorded_only_where_there_is_machine_access():
    assert REGISTRY["telangana-today"].cost_category is CostCategory.FREE_PUBLIC
    assert REGISTRY["google-news-serper"].cost_category is CostCategory.FREE_WITH_LIMITS
    assert REGISTRY["waze-for-cities"].cost_category is CostCategory.PARTNER_ONLY
    # Advisories on social media: there is nothing to price.
    assert REGISTRY["hyderabad-traffic-police"].cost_category is None


def _definition(**overrides) -> SourceDefinition:
    values = dict(
        source_id="x", source_name="X", source_type=SourceType.RSS, source_class=SourceClass.PUBLISHER,
        source_tier=4, discovery_only=True,
    )  # fmt: skip
    values.update(overrides)
    return SourceDefinition(**values)


def test_a_publisher_cannot_be_given_authority():
    with pytest.raises(ValidationError, match="discovery-only"):
        _definition(source_tier=1)
    with pytest.raises(ValidationError, match="discovery-only"):
        _definition(discovery_only=False)
    with pytest.raises(ValidationError, match="cannot be above tier 4"):
        _definition(source_class=SourceClass.AUTHORITATIVE_OFFICIAL, source_tier=1, discovery_only=True)


def test_reviewed_terms_need_a_status():
    with pytest.raises(ValidationError, match="terms_status"):
        _definition(terms_reviewed=True)
    reviewed = _definition(terms_reviewed=True, terms_status=TermsStatus.PERMITS_TESTING)
    assert reviewed.terms_status is TermsStatus.PERMITS_TESTING
