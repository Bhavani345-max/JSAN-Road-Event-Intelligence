"""Official sources: road and transport authorities that publish their own events.

Each is an AUTHORITATIVE_OFFICIAL source of tier 1. Its records carry the
event's own fields (type, times, geometry, direction), which go into
`RawSourceRecord.structured`; the event is built from them rather than
detected from text. Tier 1 is not approval: every event still starts as
VALIDATION_REQUIRED.

Two kinds so far: feeds with geometry (Transport for London, the City of
Toronto) and listings without it (the Mumbai and Bengaluru traffic police),
whose events are located by a named place, marked approximate.
"""

from .bengaluru_traffic_police import BengaluruTrafficPoliceConnector, bengaluru_source
from .bison_fute import BisonFuteRoadEventsConnector, bison_fute_source
from .finland import FinlandDigitrafficConnector, finland_source
from .mumbai_traffic_police import MumbaiTrafficPoliceConnector, mumbai_source
from .nyc import NycStreetClosuresConnector, nyc_source
from .tfl import TflRoadDisruptionsConnector, tfl_source
from .toronto import TorontoRoadRestrictionsConnector, toronto_source

__all__ = [
    "BengaluruTrafficPoliceConnector",
    "BisonFuteRoadEventsConnector",
    "FinlandDigitrafficConnector",
    "MumbaiTrafficPoliceConnector",
    "NycStreetClosuresConnector",
    "TflRoadDisruptionsConnector",
    "TorontoRoadRestrictionsConnector",
    "bengaluru_source",
    "bison_fute_source",
    "finland_source",
    "mumbai_source",
    "nyc_source",
    "tfl_source",
    "toronto_source",
]
