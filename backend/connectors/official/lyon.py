"""Métropole de Lyon: works that disrupt traffic (chantiers perturbants).

    GET https://data.grandlyon.com/geoserver/metropole-de-lyon/ows
        ?SERVICE=WFS&VERSION=2.0.0&request=GetFeature
        &typename=metropole-de-lyon:pvo_patrimoine_voirie.pvochantierperturbant
        &outputFormat=application/json&SRSNAME=EPSG:4326

The Métropole's roads department lists the works on its streets that close a
road or reduce traffic, with the work site as a polygon, the street, the
commune and the work dates. On 14 October 2026: 417 works in 29 communes, 272
under way and 145 to come, keyless. The address is the one the Métropole
lists for the dataset on data.gouv.fr; neither host has a robots.txt.

Dates are days without a time: whole days in Paris time.

Licence Ouverte 2.0 (data.gouv.fr record of the Métropole de Lyon,
https://www.data.gouv.fr/datasets/chantiers-perturbants-de-la-metropole-de-lyon/),
updated daily.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.time import end_of_day, start_of_day, utc_now
from packages.event_schema import EventType
from packages.source_models import (
    CommercialUse,
    CostCategory,
    IntegrationStatus,
    RawSourceRecord,
    SourceClass,
    SourceDefinition,
    SourceEvent,
    SourceLocation,
    SourceType,
    TermsStatus,
)

from .common import content_key, fetch_json, select_for_run

SOURCE_ID = "lyon-disruptive-works"
ENDPOINT = "https://data.grandlyon.com/geoserver/metropole-de-lyon/ows"
PARAMS = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "request": "GetFeature",
    "typename": "metropole-de-lyon:pvo_patrimoine_voirie.pvochantierperturbant",
    "outputFormat": "application/json",
    "SRSNAME": "EPSG:4326",
}
SOURCE_URL = "https://www.data.gouv.fr/datasets/chantiers-perturbants-de-la-metropole-de-lyon/"
ATTRIBUTION = "Source: Métropole de Lyon, Chantiers perturbants, Licence Ouverte 2.0."
PARIS_TIME_ZONE = ZoneInfo("Europe/Paris")


def lyon_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("france")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Métropole de Lyon works disrupting traffic",
        organization="Métropole de Lyon",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region=city.region,
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Grand Lyon WFS GeoJSON; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
        ),
        parser_type="grand_lyon_chantiers_perturbants",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="Licence Ouverte 2.0 (data.gouv.fr record of the Métropole de Lyon)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each work as the WFS returns it and the structured event derived from it."
        ),
        notes=(
            "Works on the Métropole's streets that close a road or reduce traffic, with the work "
            "site as a polygon. Fetched without a key on 14 October 2026: 417 works, 272 under "
            "way and 145 to come. Dates are whole days in Paris time. Updated daily."
        ),
    )


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(_clean(value)[:10])
    except ValueError:
        return None


def _event_type(disruption: str) -> str:
    """'Circulation interdite (de jour)': closed; reduced, alternating or one-way: restricted."""
    if disruption.lower().startswith("circulation interdite"):
        return EventType.PLANNED_ROAD_CLOSURE.value
    if disruption:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict):
        return None
    external_id = _clean(properties.get("gid"))
    if not external_id:
        return None

    street = _clean(properties.get("nom"))
    commune = _clean(properties.get("commune1"))
    detail = _clean(properties.get("precisionlocalisation"))
    disruption = _clean(properties.get("typeperturbation"))
    works = _clean(properties.get("nomchantier"))
    location = ", ".join(part for part in (street, detail, commune) if part)
    first, last = _day(properties.get("debutchantier")), _day(properties.get("finchantier"))
    structured = SourceEvent(
        event_type=_event_type(disruption),
        category=" / ".join(part for part in ("Chantier perturbant", disruption) if part),
        start=start_of_day(first, PARIS_TIME_ZONE) if first else None,
        end=end_of_day(last, PARIS_TIME_ZONE) if last else None,
        geometry=geometry if isinstance(geometry, dict) else None,
        locations=(
            [
                SourceLocation(
                    name=location,
                    kind="work site",
                    geometry=geometry if isinstance(geometry, dict) else None,
                    closure=disruption or None,
                )
            ]
            if location
            else []
        ),
        affected_road=street or None,
        attribution=ATTRIBUTION,
    )
    # "Autre" (other) names nobody.
    contractor = _clean(properties.get("intervenant"))
    summary = ". ".join(
        part
        for part in (
            works,
            _clean(properties.get("descripchantierinternet")),
            f"Works by: {contractor}" if contractor and contractor.lower() != "autre" else "",
        )
        if part
    )
    categories = [part for part in ("chantier perturbant", disruption) if part]
    place = ", ".join(part for part in (street or works, commune) if part)
    return RawSourceRecord(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=_clean(properties.get("url_document")) or SOURCE_URL,
        title=f"{disruption or 'Chantier'}: {place}",
        summary=summary or None,
        content_text=None,
        categories=categories,
        published_at=None,
        retrieved_at=retrieved_at,
        raw={
            "feature": feature,
            "summary_html": summary,
            "categories": categories,
            "source_event": structured.model_dump(mode="json"),
        },
        content_hash=content_key(feature, frozenset()),
        structured=structured,
    )


class LyonDisruptiveWorksConnector:
    def __init__(
        self,
        source: SourceDefinition,
        user_agent: str,
        *,
        max_records: int | None = None,
        client: httpx.Client | None = None,
        clock=utc_now,
    ) -> None:
        self.source = source
        self._user_agent = user_agent
        self.max_records = max_records
        self._client = client
        self._clock = clock

    @staticmethod
    def revision_key(raw: dict) -> str:
        return content_key(raw.get("feature", {}), frozenset())

    def fetch(self) -> list[RawSourceRecord]:
        body = fetch_json(ENDPOINT, self._user_agent, client=self._client, params=PARAMS)
        features = body.get("features") if isinstance(body, dict) else None
        if not isinstance(features, list):
            raise ConnectorError(f"{ENDPOINT} did not return a GeoJSON feature list")
        retrieved_at = self._clock()
        records = [
            record
            for item in features
            if isinstance(item, dict) and (record := to_record(item, retrieved_at))
        ]
        # The layer is the full list of works under way or to come.
        self.observed_ids = {record.external_id for record in records}
        return select_for_run(
            records,
            now=retrieved_at,
            start=lambda record: record.structured.start,
            end=lambda record: record.structured.end,
            order=lambda record: record.structured.start or record.retrieved_at,
            limit=self.max_records,
        )
