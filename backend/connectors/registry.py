"""The source registry: every source REI knows about, and how to read it.

CONNECTED sources have a connector and are polled. Researched sources that are
not connected (connectors/discovered.py) are listed too, inactive and without
a connector, so coverage is visible in one place.

To add an RSS source, define it in connectors/rss/ (as telangana_today.py
does) and list it below with `_rss(...)`. The ingestion service, the API and
the console pick it up from this registry; nothing else needs to change.
"""

from collections.abc import Callable, Collection
from dataclasses import dataclass
from functools import partial

from packages.source_models import IntegrationStatus, SourceDefinition

from packages.cities import load_cities

from .api.serper_news import SerperNewsConnector, serper_news_source
from .base import SourceConnector
from .discovered import DISCOVERED_SOURCES
from .discovered_2026_10_15 import DISCOVERED_2026_10_15
from .discovery.google_news_rss import GoogleNewsRssConnector, google_news_rss_source
from .official import (
    CalgaryConstructionDetoursConnector,
    DriveBcEventsConnector,
    EdmontonTrafficDisruptionsConnector,
    GoldCoastTemporaryClosuresConnector,
    MainRoadsWaConnector,
    OttawaTrafficEventsConnector,
    RoadsActPlannedClosuresConnector,
    WinnipegLaneClosuresConnector,
    WodongaRoadworksConnector,
    BisonFuteRoadEventsConnector,
    DialogTrafficOrdersConnector,
    FinlandDigitrafficConnector,
    LyonDisruptiveWorksConnector,
    NycStreetClosuresConnector,
    TflRoadDisruptionsConnector,
    TorontoRoadRestrictionsConnector,
    bengaluru_source,
    bison_fute_source,
    calgary_source,
    drivebc_source,
    edmonton_source,
    gold_coast_source,
    main_roads_wa_source,
    ottawa_source,
    roads_act_source,
    winnipeg_source,
    wodonga_source,
    dialog_source,
    finland_source,
    lyon_source,
    mumbai_source,
    nyc_events_source,
    nyc_source,
    tfl_source,
    toronto_source,
)
from .manual import MANUAL_ENTRY
from .restricted import RESTRICTED_PUBLISHERS
from .rss import create_rss_connector
from .rss.models import restricted_by_terms
from .rss.deccan_chronicle import DECCAN_CHRONICLE
from .rss.mid_day_mumbai import MID_DAY_MUMBAI
from .rss.newsmeter import NEWSMETER
from .rss.siasat import SIASAT
from .rss.siasat_mumbai import SIASAT_MUMBAI
from .rss.telangana_today import TELANGANA_TODAY
from .rss.the_hans_india import THE_HANS_INDIA
from .rss.the_hindu import THE_HINDU
from .rss.the_hindu_bengaluru import THE_HINDU_BENGALURU


@dataclass(frozen=True)
class RegisteredSource:
    definition: SourceDefinition
    # Builds the connector, given the HTTP User-Agent to identify REI with.
    # None for sources that are not connected.
    create_connector: Callable[[str], SourceConnector] | None = None


def _rss(definition: SourceDefinition) -> RegisteredSource:
    """An RSS source: read by the generic RSS connector, configured by its definition."""
    return RegisteredSource(definition, partial(create_rss_connector, definition))


CONNECTED_SOURCES: tuple[RegisteredSource, ...] = (
    _rss(TELANGANA_TODAY),
    _rss(NEWSMETER),
    # Mumbai (8 October 2026): the feed verified in docs/cities/mumbai-source-research.md.
    _rss(MID_DAY_MUMBAI),
)

# Feeds whose publisher's terms forbid automated access (decision 0024):
# registered without a connector, so they are never fetched, by the scheduler
# or by hand, while the evidence stored before then keeps its source.
RESTRICTED_SOURCES: tuple[RegisteredSource, ...] = (
    RegisteredSource(SIASAT),
    RegisteredSource(SIASAT_MUMBAI),
    # Decision 0032 (15 October 2026): their publishers' terms forbid automated
    # collection; disconnected until permission is obtained. Their parsers stay
    # (connectors/rss/the_hindu.py ...), so reconnecting is moving them back above.
    *(
        RegisteredSource(
            restricted_by_terms(
                definition,
                terms=RESTRICTED_PUBLISHERS[domain],
                licence=licence,
                since="15 October 2026",
            )
        )
        for definition, domain, licence in (
            (THE_HINDU, "thehindu.com", "Automated collection not permitted without permission"),
            (THE_HINDU_BENGALURU, "thehindu.com", "Automated collection not permitted without permission"),
            (DECCAN_CHRONICLE, "deccanchronicle.com", "Viewing only; no data mining or commercial use"),
        )
    ),
)

# Feeds the user removed from REI (decision 0026): registered without a
# connector, like the restricted ones, and never fetched.
REMOVED_SOURCES: tuple[RegisteredSource, ...] = (RegisteredSource(THE_HANS_INDIA),)


def _without_location(definition: SourceDefinition) -> SourceDefinition:
    """`definition`, removed because its records carry no location of their own (decision 0029).

    Registered without a connector, so it is never fetched; its stored
    evidence keeps its source. Its terms and licence stay as they were read.
    """
    return SourceDefinition.model_validate(
        definition.model_dump()
        | {
            "integration_status": IntegrationStatus.NOT_USABLE,
            "active": False,
            "access_method": "Not accessed: removed from REI, its records give no location",
            "notes": (
                f"{definition.notes} Removed from REI on 15 October 2026 by the user's "
                "decision: its records give no coordinates of their own (decision 0029)."
            ),
        }
    )


# Official feeds whose records name places but give no coordinates (decision 0029).
UNLOCATED_SOURCES: tuple[RegisteredSource, ...] = tuple(
    RegisteredSource(_without_location(make(scheduled=False)))
    for make in (nyc_events_source, mumbai_source, bengaluru_source)
)


def _google_news_rss_sources(enabled: bool) -> tuple[RegisteredSource, ...]:
    """One Google News RSS discovery source per configured city."""
    sources = []
    for city in load_cities().values():
        definition = google_news_rss_source(city, enabled=enabled)
        sources.append(
            RegisteredSource(
                definition,
                (
                    lambda user_agent, definition=definition, city=city: GoogleNewsRssConnector(
                        definition, city, user_agent
                    )
                )
                if enabled
                else None,
            )
        )
    return tuple(sources)


def _scheduled_if_chosen(
    make: Callable[..., SourceDefinition], everything: bool, chosen: frozenset[str]
) -> SourceDefinition:
    """The source's definition, scheduled when every feed is or it is one of those chosen."""
    definition = make(scheduled=everything)
    if not everything and definition.source_id in chosen:
        definition = make(scheduled=True)
    return definition


def _official_sources(
    scheduled: bool,
    max_records: int | None,
    tfl_app_key: str | None,
    chosen: frozenset[str] = frozenset(),
) -> tuple[RegisteredSource, ...]:
    """Connected official/open-data sources; scheduled or run by hand.

    `scheduled` schedules every one of them; `chosen` schedules only the
    sources it names, so feeds can be switched on one at a time.
    """
    tfl, toronto, nyc, france, dialog, lyon, finland = (
        _scheduled_if_chosen(make, scheduled, chosen)
        for make in (
            tfl_source, toronto_source, nyc_source, bison_fute_source, dialog_source,
            lyon_source, finland_source,
        )
    )  # fmt: skip
    # Canada and Australia (15 October 2026, decision 0029): every record kept.
    feature_feeds = tuple(
        (definition, connector)
        for make, connector in (
            (calgary_source, CalgaryConstructionDetoursConnector),
            (drivebc_source, DriveBcEventsConnector),
            (edmonton_source, EdmontonTrafficDisruptionsConnector),
            (gold_coast_source, GoldCoastTemporaryClosuresConnector),
            (main_roads_wa_source, MainRoadsWaConnector),
            (ottawa_source, OttawaTrafficEventsConnector),
            (roads_act_source, RoadsActPlannedClosuresConnector),
            (winnipeg_source, WinnipegLaneClosuresConnector),
            (wodonga_source, WodongaRoadworksConnector),
        )
        if (definition := _scheduled_if_chosen(make, scheduled, chosen))
    )
    return (
        RegisteredSource(
            tfl,
            lambda user_agent: TflRoadDisruptionsConnector(
                tfl, user_agent, app_key=tfl_app_key, max_records=max_records
            ),
        ),
        RegisteredSource(
            toronto,
            lambda user_agent: TorontoRoadRestrictionsConnector(
                toronto, user_agent, max_records=max_records
            ),
        ),
        # These public national/municipal feeds are larger than the initial
        # four-city test feeds, so retain every current/upcoming record.
        RegisteredSource(
            nyc,
            lambda user_agent: NycStreetClosuresConnector(nyc, user_agent),
        ),
        # DiaLog and Lyon: connected 14 October 2026 (decision 0027).
        RegisteredSource(
            france,
            lambda user_agent: BisonFuteRoadEventsConnector(france, user_agent),
        ),
        RegisteredSource(
            dialog,
            lambda user_agent: DialogTrafficOrdersConnector(dialog, user_agent),
        ),
        RegisteredSource(
            lyon,
            lambda user_agent: LyonDisruptiveWorksConnector(lyon, user_agent),
        ),
        RegisteredSource(
            finland,
            lambda user_agent: FinlandDigitrafficConnector(finland, user_agent),
        ),
    ) + tuple(
        RegisteredSource(
            definition,
            lambda user_agent, definition=definition, connector=connector: connector(definition, user_agent),
        )
        for definition, connector in feature_feeds
    )


def registered_sources(
    serper_api_key: str | None = None,
    google_news_rss_enabled: bool = False,
    *,
    official_feeds_scheduled: bool = False,
    official_feeds_scheduled_sources: Collection[str] = (),
    official_feed_max_records: int | None = 30,
    tfl_app_key: str | None = None,
) -> tuple[RegisteredSource, ...]:
    """Every source REI knows about, given the credentials and switches configured.

    Sources that need a key are connected only when it is present; without it
    they are listed as REQUIRES_ACCESS and never fetched. The Google News RSS
    feeds are connected only when switched on; otherwise they are listed as
    needing a terms review and never fetched. Official feeds are polled on
    their schedules when `official_feeds_scheduled` is on, or when named in
    `official_feeds_scheduled_sources`; otherwise only by hand.
    """
    if serper_api_key:
        definition = serper_news_source(connected=True)
        search = RegisteredSource(
            definition,
            lambda user_agent: SerperNewsConnector(definition, serper_api_key, user_agent),
        )
    else:
        search = RegisteredSource(serper_news_source(connected=False))
    return (
        CONNECTED_SOURCES
        + RESTRICTED_SOURCES
        + REMOVED_SOURCES
        + UNLOCATED_SOURCES
        + (search,)
        + _official_sources(
            official_feeds_scheduled,
            official_feed_max_records or None,
            tfl_app_key,
            frozenset(official_feeds_scheduled_sources),
        )
        + _google_news_rss_sources(google_news_rss_enabled)
        + (RegisteredSource(MANUAL_ENTRY),)
        + tuple(
            RegisteredSource(definition)
            for definition in DISCOVERED_SOURCES + DISCOVERED_2026_10_15
        )
    )


# The registry with no credentials configured.
REGISTERED_SOURCES: tuple[RegisteredSource, ...] = registered_sources()

# The official feeds OFFICIAL_FEEDS_SCHEDULED_SOURCES can name.
OFFICIAL_SOURCE_IDS: frozenset[str] = frozenset(
    source.definition.source_id for source in _official_sources(False, None, None)
)


def get_registered_source(source_id: str) -> RegisteredSource | None:
    return next(
        (source for source in REGISTERED_SOURCES if source.definition.source_id == source_id),
        None,
    )
