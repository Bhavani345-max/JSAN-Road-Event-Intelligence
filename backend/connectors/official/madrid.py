"""Madrid street incidents (Informo), Spain (decision 0034).

    GET https://informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml

Madrid City Council's incidents on the city's public roads ("Tráfico.
Incidencias en vía pública", Informo), an XML list of `Incidencia` elements,
each with its id, type code and name (`cod_tipo_incidencia`,
`nom_tipo_incidencia`), flags for works and accidents, a description in
Spanish, a start and an end (`fh_inicio`, `fh_final`, Madrid local time
written without an offset, with seven fractional digits) and a WGS 84 point
(`latitud`, `longitud`; a UTM copy is ignored). The portal says the file is
refreshed about every 5 minutes. Fetched without a key on 21 October 2026:
113 incidents, every one with a start, an end and a point; most have already
ended, and the file was byte-for-byte the one fetched on 16 October.

The type comes from the source's own code and flags: Carriles cortados (LCS,
lanes closed) is a lane restriction; an incident flagged as an accident
(`es_accidente` S) an accident; one flagged as works (`es_obras` S: road
maintenance, road works, long-term road works) road works. Anything else
keeps its words with no type. The description's own words (a night closure,
the hours) are kept as the summary and never read into a type or a time.

Licence: CC BY 4.0, as the dataset page states; the portal's conditions
permit commercial reuse. Credit "Ayuntamiento de Madrid"
(docs/data-sources/spain-connectors-2026-10-21.md).
"""

import xml.etree.ElementTree as ET
from datetime import datetime
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

from .common import fetch_text
from .feature_feed import FeatureFeedConnector, clean, item_record, local_time

SOURCE_ID = "madrid-informo-incidents"
ENDPOINT = "https://informo.madrid.es/informo/tmadrid/incid_aytomadrid.xml"
SOURCE_URL = "https://datos.madrid.es/dataset/202062-0-trafico-incidencias-viapublica"
ATTRIBUTION = "Ayuntamiento de Madrid, Tráfico. Incidencias en vía pública (Informo), CC BY 4.0"
MADRID = ZoneInfo("Europe/Madrid")
LANES_CLOSED = "LCS"


def madrid_source(*, scheduled: bool) -> SourceDefinition:
    city = get_city("madrid")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Madrid street incidents (Informo)",
        organization="Ayuntamiento de Madrid (DG Gestión y Vigilancia de la Circulación)",
        authority_type="MUNICIPAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=city.country,
        region="Community of Madrid",
        city=city.id,
        source_url=SOURCE_URL,
        endpoint=ENDPOINT,
        access_method="Public XML file (Informo), WGS 84 points; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=60,
        language="es",
        events_supported=(
            EventType.ROAD_WORKS.value,
            EventType.LANE_RESTRICTION.value,
            EventType.ACCIDENT.value,
        ),
        parser_type="madrid_informo_incidents",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; the file is said to refresh every 5 minutes; polled hourly.",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence="CC BY 4.0 (datos.madrid.es dataset page; conditions permit commercial reuse)",
        attribution=ATTRIBUTION,
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=True,
        evidence_retention="Each incident as received.",
        notes=(
            "Incidents on Madrid's public roads (mostly works), each a point with a start and an "
            "end. Fetched without a key on 21 October 2026: 113 incidents, most already ended; the "
            "file was identical to the one fetched on 16 October, so it may not be refreshed as "
            "the portal says."
        ),
    )


def _time(value: Any) -> datetime | None:
    """"2026-09-28T10:00:00.0000000" in Madrid time (fraction of a second dropped)."""
    return local_time(clean(value)[:19], MADRID, ("%Y-%m-%dT%H:%M:%S",))


def to_record(item: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    external_id = clean(item.get("id_incidencia"))
    try:
        latitude, longitude = float(clean(item.get("latitud"))), float(clean(item.get("longitud")))
    except ValueError:
        return None
    if not external_id or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    geometry = {"type": "Point", "coordinates": [longitude, latitude]}
    code, name = clean(item.get("cod_tipo_incidencia")), clean(item.get("nom_tipo_incidencia"))
    if code == LANES_CLOSED:
        event_type, label = EventType.LANE_RESTRICTION.value, "Lanes closed"
    elif clean(item.get("es_accidente")) == "S":
        event_type, label = EventType.ACCIDENT.value, "Accident"
    elif clean(item.get("es_obras")) == "S":
        event_type, label = EventType.ROAD_WORKS.value, "Road works"
    else:
        event_type, label = None, "Incident"
    description = clean(item.get("descripcion"))
    # The place is written only inside the description ("Túnel de pza. Castilla.
    # Previsión de ..."); it is not cut out of it (abbreviations end in a full
    # stop too), so the title quotes the description's start as written.
    shown = description if len(description) <= 120 else description[:119].rstrip() + "…"
    flags = [
        word
        for field, word in (("incid_prevista", "foreseen"), ("incid_planificada", "planned"))
        if clean(item.get(field)) == "S"
    ]
    structured = SourceEvent(
        event_type=event_type,
        category=" / ".join(part for part in (code, name) if part),
        status=f"incid_estado {clean(item.get('incid_estado'))}" if clean(item.get("incid_estado")) else None,
        start=_time(item.get("fh_inicio")),
        end=_time(item.get("fh_final")),
        geometry=geometry,
        locations=[SourceLocation(name=shown or "Madrid", kind="incident point", geometry=geometry)],
        attribution=ATTRIBUTION,
        stated_period=f"{clean(item.get('fh_inicio'))} – {clean(item.get('fh_final'))} (Madrid time)",
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=external_id,
        url=SOURCE_URL,
        title=f"{label} ({name or code or 'incidencia'}): {shown or 'Madrid'}",
        summary=". ".join(
            part
            for part in (
                description,
                f"Type: {name} ({code})" if name or code else "",
                f"Source flags: {', '.join(flags)}" if flags else "",
                f"Code {clean(item.get('codigo'))}" if clean(item.get("codigo")) else "",
            )
            if part
        )
        or None,
        categories=[part for part in (code, name) if part],
        item=item,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_incidents(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    """Each `Incidencia` as a flat dict of its fields."""
    body = fetch_text(ENDPOINT, user_agent, client=client)
    try:
        root = ET.fromstring(body.lstrip("﻿"))
    except ET.ParseError as error:
        raise ConnectorError(f"{ENDPOINT} did not return readable XML: {error}") from error
    if root.tag != "Incidencias":
        raise ConnectorError(f"{ENDPOINT} did not return an incident list (root {root.tag!r})")
    return [{child.tag: clean(child.text) for child in incident} for incident in root.iter("Incidencia")]


class MadridInformoConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_incidents)
    to_record = staticmethod(to_record)
