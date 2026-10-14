"""Manual entry: road events a reviewer adds because no connected source reported them.

Not a connector: nothing is fetched. It is in the source registry so that
manually entered events have a source like every other event, and can be told
apart from detected ones everywhere.
"""

from packages.source_models import IntegrationStatus, SourceDefinition, SourceType

MANUAL_ENTRY = SourceDefinition(
    source_id="manual-entry",
    source_name="Manual entry",
    organization="JSAN REI reviewers",
    authority_type="REVIEWER",
    # No tier: an entry is as reliable as the basis the reviewer states for it.
    source_tier=None,
    source_type=SourceType.MANUAL,
    # Not a source of its own: the reviewer's basis is the evidence.
    source_class=None,
    access_method="Entered in the console by a reviewer",
    integration_status=IntegrationStatus.MANUAL_ONLY,
    active=False,
    language="en",
    evidence_retention=(
        "The entry exactly as typed, with who entered it, when, and the basis they gave."
    ),
    notes=(
        "For road events that reviewers know of and no connected source reported. "
        "Each entry needs a stated basis and still goes through validation."
    ),
)
