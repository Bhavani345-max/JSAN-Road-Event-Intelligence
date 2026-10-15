"""Official sources: road and transport authorities that publish their own events.

Each is an AUTHORITATIVE_OFFICIAL source of tier 1. Its records carry the
event's own fields (type, times, geometry, direction), which go into
`RawSourceRecord.structured`; the event is built from them rather than
detected from text. Tier 1 is not approval: every event still starts as
VALIDATION_REQUIRED.

Two kinds so far: feeds with geometry (Transport for London, the City of
Toronto, NYC DOT, Bison Futé, DiaLog, the Métropole de Lyon, Fintraffic, and
since 15 October 2026 five Canadian and four Australian feeds) and
listings without it (the Mumbai and Bengaluru traffic police, NYC permitted
events), whose events are located by a named place where the city has a place
list, marked approximate, and otherwise stay unlocated.
"""

from .bengaluru_traffic_police import BengaluruTrafficPoliceConnector, bengaluru_source
from .calgary import CalgaryConstructionDetoursConnector, calgary_source
from .drivebc import DriveBcEventsConnector, drivebc_source
from .edmonton import EdmontonTrafficDisruptionsConnector, edmonton_source
from .gold_coast import GoldCoastTemporaryClosuresConnector, gold_coast_source
from .main_roads_wa import MainRoadsWaConnector, main_roads_wa_source
from .ottawa import OttawaTrafficEventsConnector, ottawa_source
from .roads_act import RoadsActPlannedClosuresConnector, roads_act_source
from .winnipeg import WinnipegLaneClosuresConnector, winnipeg_source
from .wodonga import WodongaRoadworksConnector, wodonga_source
from .bison_fute import BisonFuteRoadEventsConnector, bison_fute_source
from .dialog import DialogTrafficOrdersConnector, dialog_source
from .finland import FinlandDigitrafficConnector, finland_source
from .lyon import LyonDisruptiveWorksConnector, lyon_source
from .mumbai_traffic_police import MumbaiTrafficPoliceConnector, mumbai_source
from .nyc import NycStreetClosuresConnector, nyc_source
from .nyc_events import NycPermittedEventsConnector, nyc_events_source
from .tfl import TflRoadDisruptionsConnector, tfl_source
from .toronto import TorontoRoadRestrictionsConnector, toronto_source

__all__ = [
    "CalgaryConstructionDetoursConnector",
    "DriveBcEventsConnector",
    "EdmontonTrafficDisruptionsConnector",
    "GoldCoastTemporaryClosuresConnector",
    "MainRoadsWaConnector",
    "OttawaTrafficEventsConnector",
    "RoadsActPlannedClosuresConnector",
    "WinnipegLaneClosuresConnector",
    "WodongaRoadworksConnector",
    "calgary_source",
    "drivebc_source",
    "edmonton_source",
    "gold_coast_source",
    "main_roads_wa_source",
    "ottawa_source",
    "roads_act_source",
    "winnipeg_source",
    "wodonga_source",
    "BengaluruTrafficPoliceConnector",
    "BisonFuteRoadEventsConnector",
    "DialogTrafficOrdersConnector",
    "FinlandDigitrafficConnector",
    "LyonDisruptiveWorksConnector",
    "MumbaiTrafficPoliceConnector",
    "NycPermittedEventsConnector",
    "NycStreetClosuresConnector",
    "TflRoadDisruptionsConnector",
    "TorontoRoadRestrictionsConnector",
    "bengaluru_source",
    "bison_fute_source",
    "dialog_source",
    "finland_source",
    "lyon_source",
    "mumbai_source",
    "nyc_events_source",
    "nyc_source",
    "tfl_source",
    "toronto_source",
]
