"""État de Genève, major works affecting mobility (Infomobilité, chantiers principaux), Switzerland (5 November 2026).

    GET https://vector.sitg.ge.ch/arcgis/rest/services/INFOMOB_CHANTIER_POINT/FeatureServer/0/query
        ?where=1=1&outFields=*&outSR=4326&f=geojson

The Canton of Geneva's transport office (Office cantonal des transports)
publishes, through the canton's geodata system SITG, the works sites that have
a large impact on mobility ("chantiers ayant un impact important sur la
mobilité"), shown "as far as possible 7 days before the works start and until
they are finished" (catalogue: opendata.swiss, "Infomobilité - Chantiers
principaux impactant la mobilité", organisation canton-geneve, updated daily;
data from the canton's Plateforme Chantiers Mobilité). An ArcGIS feature layer,
read as GeoJSON in WGS 84, longitude first. Each feature is a point with the
address (`ADRESSE`), the disruption in the canton's words (`PERTURBATION`, one
effect a line: "Fermeture de la route, déviations.", "Suppression de voie,
ralentissements."), the first and last day (`DATE_DEBUT`, `DATE_FIN`, written
20260630, and in words in `DUREE`, "du 30-06-2026 au 31-12-2026"), who
commissioned the works (`MOA`, maître d'ouvrage: "Etat de Genève", "SIG",
"Ville de Genève", "Commune", "Privé" …), a status (`DATE_STATUT`) and for
about half an information sheet (`FICHE_INFO`, a PDF on ge.ch). Fetched without
a key on 5 November 2026: 64 works, all with both days; 63 in force and 1 to
come (the Nations tunnel, closed the nights of 9 to 11 November).

`DATE_STATUT` reads "Ouvert" (62), ">12 mois" (1) or "Termine" (1) and is not
documented. The one "Termine" (private works in Rue François-Dussaud) runs to
18 December 2026 by its days, and the layer lists works until they are
finished, so it is kept as the source's status word and not read as ended.

Only works that change traffic on the road are road events (as for Copenhagen
and Tallinn, decision 0053). A works is left out when every line of its
disruption is about pedestrians ("piétons", "pédestre"), parking
("stationnement", "parking") or bus stops and replacement shuttles ("arrêts",
"navettes"), and none of those lines names road traffic (circulation, trafic,
voies, route, rue, ralentissements, sens unique, impasse, gabarits, tunnel,
pont …); one that states no disruption is kept. On 5 November 2026 that leaves
out 5 of the 64: parking only (Rue Butini), pedestrian detours and parking
(Rue du Vélodrome), parking and moved bus stops (Route de Malagnou),
pedestrians, parking and replacement shuttles (Route de Peney), and the access
ramp to the Voie Verte, a path for pedestrians and cyclists (Chemin du
Pré-du-Couvent). 59 are kept, 58 in force and 1 to come. Every kept works is
road works (ROAD_WORKS); the disruption is kept in the source's words and not
read as a closure, since a line such as "Fermeture de route" may hold for some
nights of a longer works only.

`OBJECTID` runs from 1 to 64 without a gap, the mark of a layer reloaded whole
(it is updated daily), so it is not an id. A record's id is made from what the
source states: its address, first day, commissioner and point. A changed end
or text is a revision of the same record; a moved point is a new one.

Personal data: none is published. The commissioner is a kind of body ("Privé"
for a private one), never a name.

Licence: opendata.swiss terms "Freie Nutzung" / "Utilisation libre"
(terms_open, as the catalogue entry states on every distribution): "Sie dürfen
diesen Datensatz für kommerzielle Zwecke nutzen. Eine Quellenangabe wird
empfohlen" (https://opendata.swiss/de/terms-of-use, read 5 November 2026).
Credit is recommended and given.
"""

import json
import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from connectors.base import ConnectorError
from packages.cities import get_city
from packages.common.hashing import sha256_hex
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

from .common import content_key
from .feature_feed import FeatureFeedConnector, clean, fetch_arcgis_features, item_record, whole_days
from .feed_text import sentences

SOURCE_ID = "ch-ge-infomobilite-works"
SERVICE_URL = "https://vector.sitg.ge.ch/arcgis/rest/services/INFOMOB_CHANTIER_POINT/FeatureServer"
LAYER = f"{SERVICE_URL}/0"
SOURCE_URL = "https://opendata.swiss/fr/dataset/infomobilite-chantiers-principaux-impactant-la-mobilite1"
ATTRIBUTION = (
    "République et canton de Genève, Office cantonal des transports: Infomobilité - Chantiers "
    "principaux impactant la mobilité (SITG, opendata.swiss)"
)
GENEVA = ZoneInfo("Europe/Zurich")
# The server's row number (renumbered at each reload): not content.
ROW_NUMBERS = frozenset({"OBJECTID"})
# A disruption line about pedestrians, parking or bus stops and shuttles …
OFF_ROAD = re.compile(r"piéton|pédestre|stationnement|parking|arrêt|navette", re.IGNORECASE)
# … unless it also names road traffic (the Voie Verte is a path, not a lane).
ROAD_TRAFFIC = re.compile(
    r"circulation|trafic|\bvoies?\b(?!\s+verte)|\broutes?\b|\brues?\b|ralentissement|sens unique"
    r"|double sens|impasse|gabarit|clignotant|ripage|tourne-à|\btunnel|\bpont\b",
    re.IGNORECASE,
)


def ge_infomobilite_source(*, scheduled: bool) -> SourceDefinition:
    country = get_city("switzerland")
    return SourceDefinition(
        source_id=SOURCE_ID,
        source_name="Geneva major works affecting mobility (Infomobilité)",
        organization="République et canton de Genève, Office cantonal des transports (SITG)",
        authority_type="REGIONAL_ROAD_AUTHORITY",
        source_tier=1,
        source_type=SourceType.API,
        source_class=SourceClass.GOVERNMENT_OPEN_DATA,
        country=country.country,
        region="Genève",
        city=country.id,
        source_url=SOURCE_URL,
        endpoint=LAYER,
        access_method="ArcGIS feature service (SITG), layer INFOMOB_CHANTIER_POINT, GeoJSON in WGS 84; no key",
        integration_status=IntegrationStatus.CONNECTED,
        active=scheduled,
        polling_frequency_minutes=360,
        language="fr",
        events_supported=(EventType.ROAD_WORKS.value,),
        parser_type="ch_ge_infomobilite_works",
        cost_category=CostCategory.FREE_PUBLIC,
        rate_limit="None published; updated daily; polled every six hours (one request).",
        terms_status=TermsStatus.PERMITS_TESTING,
        licence=(
            "opendata.swiss Freie Nutzung / Utilisation libre (terms_open): commercial use permitted, "
            "credit recommended (https://opendata.swiss/de/terms-of-use)"
        ),
        attribution=ATTRIBUTION,
        # Recorded as permitted with attribution, never as settled: no legal review (decision 0009).
        commercial_use=CommercialUse.PERMITTED_WITH_ATTRIBUTION,
        provides_geometry=True,
        real_time=False,
        evidence_retention="Each works as the service returns it (it holds no personal data).",
        notes=(
            "Works sites in the Canton of Geneva with a large impact on mobility, current and coming, "
            "each a point with a first and a last day. Fetched without a key on 5 November 2026: 64 "
            "works, 63 in force and 1 to come; the 59 whose disruption touches road traffic are kept "
            "(parking, pedestrian and bus-stop changes alone are not)."
        ),
    )


def _day(value: Any) -> date | None:
    """'20260630': year, month, day."""
    try:
        return datetime.strptime(clean(value), "%Y%m%d").date()
    except ValueError:
        return None


def disruption_lines(text: Any) -> list[str]:
    return [line for line in (clean(part) for part in str(text or "").splitlines()) if line]


def on_the_road(disruption: Any) -> bool:
    """False when every stated effect is on pedestrians, parking or bus stops alone; True otherwise."""
    lines = disruption_lines(disruption)
    return not lines or any(not OFF_ROAD.search(line) or ROAD_TRAFFIC.search(line) for line in lines)


def works_id(properties: dict[str, Any], geometry: dict[str, Any]) -> str:
    """Its address, first day, commissioner and point, as stated: none of them renumbers."""
    position = [round(value, 6) for value in geometry.get("coordinates") or [] if isinstance(value, (int, float))]
    stated = [clean(properties.get(key)) for key in ("ADRESSE", "DATE_DEBUT", "MOA")] + [position]
    return f"works:{sha256_hex(json.dumps(stated, ensure_ascii=False))[:20]}"


def to_record(feature: dict[str, Any], retrieved_at: datetime) -> RawSourceRecord | None:
    """One works as REI's record; None when it changes no traffic on the road or has no point."""
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    if not on_the_road(properties.get("PERTURBATION")):
        return None
    address = clean(properties.get("ADRESSE"))
    first, last = clean(properties.get("DATE_DEBUT")), clean(properties.get("DATE_FIN"))
    start, end = whole_days(_day(first), _day(last), GENEVA)
    status = clean(properties.get("DATE_STATUT"))
    commissioner = clean(properties.get("MOA"))
    sheet = clean(properties.get("FICHE_INFO"))
    stated = clean(properties.get("DUREE")) or (f"{first} – {last}" if first or last else "")
    structured = SourceEvent(
        event_type=EventType.ROAD_WORKS.value,
        status=status or None,
        start=start,
        end=end,
        geometry=geometry,
        locations=[SourceLocation(name=address, kind="location", geometry=geometry)] if address else [],
        affected_road=address or None,
        attribution=ATTRIBUTION,
        stated_period=stated or None,
        covers_city=True,
    )
    return item_record(
        source_id=SOURCE_ID,
        external_id=works_id(properties, geometry),
        # The works' information sheet on ge.ch, when there is one.
        url=sheet if sheet.startswith(("https://ge.ch/", "https://www.ge.ch/")) else SOURCE_URL,
        title=f"Road works: {address} (Genève)" if address else "Road works (Genève)",
        summary=sentences(
            *disruption_lines(properties.get("PERTURBATION")),
            f"Maître d'ouvrage : {commissioner}" if commissioner else "",
        ),
        categories=[part for part in ("Chantier impactant la mobilité", commissioner) if part],
        item=feature,
        structured=structured,
        retrieved_at=retrieved_at,
    )


def fetch_works(user_agent: str, *, client: httpx.Client | None = None, now=None) -> list[dict]:
    features = fetch_arcgis_features(LAYER, user_agent, client=client)
    for feature in features:
        position = (feature.get("geometry") or {}).get("coordinates")
        # Geneva lies at about 6.1° E, 46.2° N: a first number above the second is a latitude.
        if isinstance(position, list) and len(position) >= 2 and position[0] > position[1]:
            raise ConnectorError(f"{LAYER} returned coordinates in latitude-longitude order")
    return features


class GeInfomobiliteWorksConnector(FeatureFeedConnector):
    fetch_items = staticmethod(fetch_works)
    to_record = staticmethod(to_record)

    @staticmethod
    def revision_key(raw: dict) -> str:
        """The works' content: a new row number alone is not a revision."""
        item = raw.get("item", {})
        properties = {
            key: value for key, value in (item.get("properties") or {}).items() if key not in ROW_NUMBERS
        }
        return content_key({**item, "properties": properties}, frozenset({"id"}))
