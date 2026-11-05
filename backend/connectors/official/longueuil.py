"""Ville de Longueuil works and obstructions ("Info-travaux et entraves", 5 November 2026).

    GET https://geomatique.longueuil.quebec/public/rest/services/Communication/
        Gestion_des_entraves_Diffusion/FeatureServer/0/query
    GET .../FeatureServer/0?f=json   (the layer's coded-value domains, once a run)

"Couche d'entités présentant toutes les entraves prévues ou en cours dans
l'année" (ArcGIS item deba69e106d94b1dbd5ef62ed93e414d, owner VilleLongueuil;
update frequency "Quotidienne"): one point per obstruction, with its name
(`NOM_ENTRAVE`), a category (`TYPE_ENTRAVE`), a status (`STATUT_ENTRAVE`),
who is responsible (`RESPONSABLE`), its nature and its effects
(`NATURE_ENTRAVE`, `REPERCUSSIONS_ENTRAVE`: comma-separated codes such as
"Fermeture_Complete,Circ_Deviee_Alternance", kept as written: the layer
defines no labels for them) and its period. In French. The category,
status, responsible and planned-month fields are numbers the layer's own
domains name ("Voies de circulation et trottoirs", "Entraves en cours",
"Mai"); the run reads those names from the layer and keeps them with each
point (`labels`).

Taken: obstructions of roads and sidewalks (`TYPE_ENTRAVE` 4) and special
events (5) that are published (status 0 "terminées", 1 "en cours", 2
"planifiées dans l'année"; 3 "proposées (non publiée)" is not published and
is left out) and that state an effect on road traffic: a full closure, a
diverted or alternating flow, or another effect described in words
("Fermeture_Complete", "Circ_Deviee_Alternance", "Autre"). Obstructions that
only remove parking or close sidewalks, cycle links or trails, or state
"Aucune", are left out, as are parks, the cycling network, municipal
buildings and filming (categories 1, 2, 3, 6). A finished obstruction
(status 0) is kept as reported ended.

`DATE_DEBUT`/`DATE_FIN` are dates: milliseconds since 1970 at local noon
(16:00 or 17:00 UTC), so each is read as a day in Eastern time and the
period runs from the start of the first day to the end of the last.
Obstructions planned for a month or season only (`DEBUT_PREVU`/`FIN_PREVUE`
without `DATE_DEBUT`/`DATE_FIN`) keep no times: no day is made up; the
planned months are kept as the stated period, and such records stay hidden
until the City gives the dates.

On 5 November 2026: 457 points; 264 are published road or special-event
obstructions with an effect on traffic (193 left out: other categories, no
effect on traffic, or not published); 182 of the 264 had ended. A run keeps
82: 28 current with both days, 2 upcoming, 5 with only a first or only a
last day, and 47 with a planned month or season only (no days); 16 of the
82 are marked finished and kept as reported ended. One obstruction can be
several points under one name (each point is its own record, as the City
lists it). The layer carries no personal data (the responsible fields name
organisations). Licence: "Cette donnée est mise à
disposition selon les termes de la Licence Creative Commons Attribution 4.0
International" (the item's licence, read 5 November 2026).
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
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

from .common import fetch_json
from .feature_feed import (
    FeatureFeedConnector,
    clean,
    fetch_arcgis_features,
    item_record,
    local_day,
    whole_days,
)
from .feed_text import sentences

SOURCE_ID = "ca-longueuil-entraves"
LAYER = (
    "https://geomatique.longueuil.quebec/public/rest/services/Communication/"
    "Gestion_des_entraves_Diffusion/FeatureServer/0"
)
SOURCE_URL = "https://www.arcgis.com/home/item.html?id=deba69e106d94b1dbd5ef62ed93e414d"
ATTRIBUTION = "Ville de Longueuil, Info-travaux et entraves. Licence CC BY 4.0."
EASTERN = ZoneInfo("America/Toronto")
# The coded fields whose names the layer's domains give.
CODED = ("TYPE_ENTRAVE", "STATUT_ENTRAVE", "RESPONSABLE", "DEBUT_PREVU", "FIN_PREVUE")
ROADS, SPECIAL_EVENTS = 4, 5
FINISHED, IN_PROGRESS, PLANNED, PROPOSED = 0, 1, 2, 3
PUBLISHED = frozenset({FINISHED, IN_PROGRESS, PLANNED})
# Effects on road traffic, as the layer writes them.
CLOSURE, DIVERTED, OTHER = "Fermeture_Complete", "Circ_Deviee_Alternance", "Autre"
TRAFFIC = frozenset({CLOSURE, DIVERTED, OTHER})
NO_DESCRIPTION = {"", "sans objet"}


def longueuil_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("canada")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Ville de Longueuil info-travaux et entraves (works and obstructions)",
        organization="Ville de Longueuil, Service de la géomatique",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Québec (Longueuil)",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service, GeoJSON, and the layer's domains (f=json); no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=720,
        language="fr",
        events_supported=(
            EventType.PLANNED_ROAD_CLOSURE.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ROAD_WORKS.value,
            EventType.SPECIAL_EVENT.value,
        ),
        parser_type="longueuil_entraves",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; updated daily; polled twice a day (two requests).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "Creative Commons Attribution 4.0 International (CC BY 4.0), the ArcGIS item's licence "
            "(deba69e106d94b1dbd5ef62ed93e414d)"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention=(
            "Each point as the service returns it, with the names the layer's domains give its "
            "coded values, and the structured event."
        ),
        notes=(
            "The City's obstructions planned or in progress this year, one point each, in French, "
            "updated daily. Fetched without a key on 5 November 2026: 457 points; 264 road and "
            "special-event obstructions with an effect on traffic; 82 kept by a run (28 current, "
            "2 upcoming, 5 with one day only, 47 with a planned month only, kept without times; "
            "16 marked finished). Dates are whole Eastern days."
        ),
    )


# --- the layer's domains ----------------------------------------------------------------


def domain_names(domains: dict[str, Any]) -> dict[str, dict[int, str]]:
    """{field: {code: name}} from coded-value domains keyed by field name."""
    names: dict[str, dict[int, str]] = {}
    for field, domain in domains.items():
        values = domain.get("codedValues") if isinstance(domain, dict) else None
        if isinstance(values, list):
            names[field] = {
                value["code"]: clean(value.get("name"))
                for value in values
                if isinstance(value, dict) and "code" in value
            }
    return names


def layer_domains(layer: dict[str, Any]) -> dict[str, Any]:
    """The coded-value domains of a layer description (f=json), keyed by field name."""
    return {
        field["name"]: field["domain"]
        for field in layer.get("fields") or []
        if isinstance(field, dict) and isinstance(field.get("domain"), dict)
    }


def labelled(feature: dict[str, Any], names: dict[str, dict[int, str]]) -> dict[str, Any]:
    """The feature with the names of its coded values, as the layer's domains give them."""
    properties = feature.get("properties") or {}
    labels = {
        field: names[field][properties[field]]
        for field in CODED
        if field in names and properties.get(field) in names[field]
    }
    return {**feature, "labels": labels}


# --- one obstruction --------------------------------------------------------------------


def codes(value: Any) -> list[str]:
    """The codes of a comma-separated list ("Repavage,Travaux_Souterrains"), as written."""
    return [part for part in (clean(text) for text in clean(value).split(",")) if part]


def effects(properties: dict[str, Any]) -> list[str]:
    return codes(properties.get("REPERCUSSIONS_ENTRAVE"))


def is_road_event(properties: dict[str, Any]) -> bool:
    return (
        properties.get("TYPE_ENTRAVE") in (ROADS, SPECIAL_EVENTS)
        and properties.get("STATUT_ENTRAVE") in PUBLISHED
        and bool(TRAFFIC & set(effects(properties)))
    )


def _event_type(properties: dict[str, Any]) -> str:
    if properties.get("TYPE_ENTRAVE") == SPECIAL_EVENTS:
        return EventType.SPECIAL_EVENT.value
    stated = set(effects(properties))
    if CLOSURE in stated:
        return EventType.PLANNED_ROAD_CLOSURE.value
    if DIVERTED in stated:
        return EventType.LANE_RESTRICTION.value
    return EventType.ROAD_WORKS.value


def _stated_period(first: date | None, last: date | None, labels: dict[str, str]) -> str | None:
    """'du 2026-06-01 au 2026-11-30 (début prévu juin, fin prévue novembre)', as stated."""
    days = " ".join(
        f"{word} {day.isoformat()}" for word, day in (("du", first), ("au", last)) if day
    )
    planned = ", ".join(
        f"{word} {labels[field].lower()}"
        for field, word in (("DEBUT_PREVU", "début prévu"), ("FIN_PREVUE", "fin prévue"))
        if labels.get(field)
    )
    if days and planned:
        return f"{days} ({planned})"
    return days or planned or None


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    external_id = clean(properties.get("GLOBALID"))
    if not external_id or not is_road_event(properties):
        return None
    labels = feature.get("labels") or {}
    first = local_day(properties.get("DATE_DEBUT"), EASTERN)
    last = local_day(properties.get("DATE_FIN"), EASTERN)
    start, end = whole_days(first, last, EASTERN)
    name = clean(properties.get("NOM_ENTRAVE"))
    kind = labels.get("TYPE_ENTRAVE") or ""
    stated = ", ".join(effects(properties))
    nature = ", ".join(codes(properties.get("NATURE_ENTRAVE")))
    responsible = labels.get("RESPONSABLE") or ""
    other_responsible = clean(properties.get("AUTRE_RESPONSABLE"))
    if other_responsible:
        responsible = f"{responsible} ({other_responsible})" if responsible else other_responsible
    description = clean(properties.get("DESCRIPTION"))
    other_nature = clean(properties.get("AUTRE_NATURE"))
    other_effects = clean(properties.get("AUTRES_REPERCUSSIONS"))
    link = clean(properties.get("URL"))
    structured = SourceEvent(
        event_type=_event_type(properties),
        category=" / ".join(part for part in (kind, stated) if part) or None,
        status=labels.get("STATUT_ENTRAVE") or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[
            SourceLocation(name=name, kind="entrave", geometry=geometry, closure=stated or None)
        ]
        if name
        else [],
        attribution=ATTRIBUTION,
        reported_ended=properties.get("STATUT_ENTRAVE") == FINISHED,
        stated_period=_stated_period(first, last, labels),
        covers_city=True,
    )
    summary = sentences(
        "" if description.lower() in NO_DESCRIPTION else description,
        f"Nature : {nature}" if nature else "",
        f"Autre nature : {other_nature}" if other_nature else "",
        f"Répercussions : {stated}" if stated else "",
        f"Autres répercussions : {other_effects}" if other_effects else "",
        f"Responsable : {responsible}" if responsible else "",
        f"Plus d'information : {link}" if link else "",
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{name or kind or 'Entrave'} (Longueuil)",
        summary=summary,
        categories=[part.lower() for part in (kind, *effects(properties)) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_obstructions(
    user_agent: str, *, client: httpx.Client | None = None, now=None
) -> list[dict]:
    layer = fetch_json(LAYER, user_agent, client=client, params={"f": "json"})
    if not isinstance(layer, dict) or "error" in layer or not isinstance(layer.get("fields"), list):
        raise ConnectorError(f"{LAYER} did not describe its fields and domains")
    names = domain_names(layer_domains(layer))
    # Without the categories and statuses named, nothing could be checked: stop.
    if not {"TYPE_ENTRAVE", "STATUT_ENTRAVE"} <= set(names):
        raise ConnectorError(f"{LAYER} no longer names its categories and statuses in domains")
    # The layer holds the year's obstructions only (a few hundred points).
    features = fetch_arcgis_features(LAYER, user_agent, client=client)
    return [labelled(feature, names) for feature in features]


class LongueuilEntravesConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_obstructions)
    to_record = staticmethod(to_record)
