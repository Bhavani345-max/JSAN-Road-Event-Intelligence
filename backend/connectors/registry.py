"""The source registry: every source REI knows about, and how to read it.

CONNECTED sources have a connector and are polled. Researched sources that are
not connected (connectors/discovered.py) are listed too, inactive and without
a connector, so coverage is visible in one place.

To add an RSS source, define it in connectors/rss/ (as telangana_today.py
does) and list it below with `_rss(...)`. The ingestion service, the API and
the console pick it up from this registry; nothing else needs to change.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from packages.source_models import SourceDefinition

from packages.cities import load_cities

from .api.serper_news import SerperNewsConnector, serper_news_source
from .base import SourceConnector
from .discovered import DISCOVERED_SOURCES
from .discovery.google_news_rss import GoogleNewsRssConnector, google_news_rss_source
from .official import (
    BengaluruTrafficPoliceConnector,
    BisonFuteRoadEventsConnector,
    DialogTrafficOrdersConnector,
    FinlandDigitrafficConnector,
    LyonDisruptiveWorksConnector,
    MumbaiTrafficPoliceConnector,
    NycPermittedEventsConnector,
    NycStreetClosuresConnector,
    TflRoadDisruptionsConnector,
    TorontoRoadRestrictionsConnector,
    bengaluru_source,
    bison_fute_source,
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
from .rss import create_rss_connector
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
    _rss(THE_HINDU),
    _rss(DECCAN_CHRONICLE),
    _rss(NEWSMETER),
    # Mumbai and Bengaluru (8 October 2026): the feeds verified in
    # docs/cities/*-source-research.md whose items carry text.
    _rss(MID_DAY_MUMBAI),
    _rss(THE_HINDU_BENGALURU),
)

# Feeds whose publisher's terms forbid automated access (decision 0024):
# registered without a connector, so they are never fetched, by the scheduler
# or by hand, while the evidence stored before then keeps its source.
RESTRICTED_SOURCES: tuple[RegisteredSource, ...] = (
    RegisteredSource(SIASAT),
    RegisteredSource(SIASAT_MUMBAI),
)

# Feeds the user removed from REI (decision 0026): registered without a
# connector, like the restricted ones, and never fetched.
REMOVED_SOURCES: tuple[RegisteredSource, ...] = (RegisteredSource(THE_HANS_INDIA),)


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


def _official_sources(
    scheduled: bool, max_records: int | None, tfl_app_key: str | None
) -> tuple[RegisteredSource, ...]:
    """Connected official/open-data sources; scheduled or run by hand."""
    tfl = tfl_source(scheduled=scheduled)
    toronto = toronto_source(scheduled=scheduled)
    mumbai = mumbai_source(scheduled=scheduled)
    bengaluru = bengaluru_source(scheduled=scheduled)
    nyc = nyc_source(scheduled=scheduled)
    nyc_events = nyc_events_source(scheduled=scheduled)
    france = bison_fute_source(scheduled=scheduled)
    dialog = dialog_source(scheduled=scheduled)
    lyon = lyon_source(scheduled=scheduled)
    finland = finland_source(scheduled=scheduled)
    return (
        RegisteredSource(
            mumbai,
            lambda user_agent: MumbaiTrafficPoliceConnector(
                mumbai, user_agent, max_records=max_records
            ),
        ),
        RegisteredSource(
            bengaluru,
            lambda user_agent: BengaluruTrafficPoliceConnector(
                bengaluru, user_agent, max_records=max_records
            ),
        ),
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
        # NYC permitted events, DiaLog and Lyon: connected 14 October 2026 (decision 0027).
        RegisteredSource(
            nyc_events,
            lambda user_agent: NycPermittedEventsConnector(nyc_events, user_agent),
        ),
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
    )


def registered_sources(
    serper_api_key: str | None = None,
    google_news_rss_enabled: bool = False,
    *,
    official_feeds_scheduled: bool = False,
    official_feed_max_records: int | None = 30,
    tfl_app_key: str | None = None,
) -> tuple[RegisteredSource, ...]:
    """Every source REI knows about, given the credentials and switches configured.

    Sources that need a key are connected only when it is present; without it
    they are listed as REQUIRES_ACCESS and never fetched. The Google News RSS
    feeds are connected only when switched on; otherwise they are listed as
    needing a terms review and never fetched.
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
        + (search,)
        + _official_sources(
            official_feeds_scheduled, official_feed_max_records or None, tfl_app_key
        )
        + _google_news_rss_sources(google_news_rss_enabled)
        + (RegisteredSource(MANUAL_ENTRY),)
        + tuple(RegisteredSource(definition) for definition in DISCOVERED_SOURCES)
    )


# The registry with no credentials configured.
REGISTERED_SOURCES: tuple[RegisteredSource, ...] = registered_sources()


def get_registered_source(source_id: str) -> RegisteredSource | None:
    return next(
        (source for source in REGISTERED_SOURCES if source.definition.source_id == source_id),
        None,
    )
