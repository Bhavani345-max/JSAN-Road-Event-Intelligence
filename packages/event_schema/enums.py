from enum import StrEnum


class EventStatus(StrEnum):
    """REI event lifecycle."""

    DISCOVERED = "DISCOVERED"
    EXTRACTED = "EXTRACTED"
    GEO_RESOLVED = "GEO_RESOLVED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    QC_PENDING = "QC_PENDING"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    EXPIRED = "EXPIRED"
    REOPENED = "REOPENED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXTENDED = "EXTENDED"
    MODIFIED = "MODIFIED"
    SUPERSEDED = "SUPERSEDED"


class EventType(StrEnum):
    PLANNED_ROAD_CLOSURE = "PLANNED_ROAD_CLOSURE"
    PUBLIC_PROCESSION = "PUBLIC_PROCESSION"
    ROAD_CONSTRUCTION = "ROAD_CONSTRUCTION"
    TRAFFIC_DIVERSION = "TRAFFIC_DIVERSION"
    FLOODING = "FLOODING"
    EMERGENCY_ROAD_CLOSURE = "EMERGENCY_ROAD_CLOSURE"
    # Added 6 October 2026 for official sources, which state these categories.
    # Works on or under a road by any party (utilities, the authority): not
    # necessarily building a road, which is ROAD_CONSTRUCTION.
    ROAD_WORKS = "ROAD_WORKS"
    WATERLOGGING = "WATERLOGGING"
    ACCIDENT = "ACCIDENT"
    SPECIAL_EVENT = "SPECIAL_EVENT"
    BRIDGE_TUNNEL_RESTRICTION = "BRIDGE_TUNNEL_RESTRICTION"
    LANE_RESTRICTION = "LANE_RESTRICTION"
    # A fault or obstruction on the road: failed signals, debris, a cave-in.
    ROAD_HAZARD = "ROAD_HAZARD"
    # Added 7 October 2026 so that each kind of event the user listed has its
    # own type. A marathon, run or walkathon on the roads.
    MARATHON = "MARATHON"
    # A cricket or football match, a race: crowds and closures around a venue.
    SPORTING_EVENT = "SPORTING_EVENT"
    # The movement of a VIP's convoy (Prime Minister, President, Chief Minister).
    VIP_MOVEMENT = "VIP_MOVEMENT"
    # A U-turn, free left or right turn closed or banned.
    TURN_RESTRICTION = "TURN_RESTRICTION"
    # Rain, storm or fallen trees closing or blocking a road (flooding has its own types).
    WEATHER_CLOSURE = "WEATHER_CLOSURE"


class LocationClass(StrEnum):
    """How an event's location was obtained, which says how far it can be trusted.

    Only GIS_RESOLVED, SOURCE_PROVIDED, HUMAN_CORRECTED and QC_APPROVED are
    positions of the event itself. APPROXIMATE is the position of a place the
    source names (a locality, a junction), drawn as such and never presented
    as the event's exact location.
    """

    # A place named in the source, looked up by name in the gazetteer.
    APPROXIMATE = "APPROXIMATE"
    # Geometry the source itself publishes (an official feed's points, lines, areas).
    SOURCE_PROVIDED = "SOURCE_PROVIDED"
    # Matched to the road network by the GIS Resolution Engine (not built yet).
    GIS_RESOLVED = "GIS_RESOLVED"
    # Placed by a reviewer on the map, with their reason.
    HUMAN_CORRECTED = "HUMAN_CORRECTED"
    # Accepted by a reviewer in QC: the event was approved with this location.
    QC_APPROVED = "QC_APPROVED"
    # Named, but not placed: no position is known.
    UNRESOLVED = "UNRESOLVED"


class EventSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventDirection(StrEnum):
    BOTH_DIRECTIONS = "BOTH_DIRECTIONS"
    NORTHBOUND = "NORTHBOUND"
    SOUTHBOUND = "SOUTHBOUND"
    EASTBOUND = "EASTBOUND"
    WESTBOUND = "WESTBOUND"
    UNKNOWN = "UNKNOWN"
