/**
 * The REI event as the web app uses it.
 *
 * Mirrors the canonical event schema of the backend
 * (packages/event_schema). Everything in the UI and the map works with this
 * model only; `api/eventRepository.ts` is the one place that knows the API's
 * wire format.
 *
 * A field is null when the source did not state it. Nothing is guessed.
 */

/** Full REI event lifecycle. */
export const EVENT_STATUSES = [
  "DISCOVERED",
  "EXTRACTED",
  "GEO_RESOLVED",
  "VALIDATION_REQUIRED",
  "QC_PENDING",
  "APPROVED",
  "SCHEDULED",
  "ACTIVE",
  "MONITORING",
  "EXPIRED",
  "REOPENED",
  "REJECTED",
  "CANCELLED",
  "EXTENDED",
  "MODIFIED",
  "SUPERSEDED",
] as const;
export type EventStatus = (typeof EVENT_STATUSES)[number];

export const EVENT_TYPES = [
  "PLANNED_ROAD_CLOSURE",
  "PUBLIC_PROCESSION",
  "ROAD_CONSTRUCTION",
  "TRAFFIC_DIVERSION",
  "FLOODING",
  "EMERGENCY_ROAD_CLOSURE",
  // Stated by official sources (6 October 2026).
  "ROAD_WORKS",
  "WATERLOGGING",
  "ACCIDENT",
  "SPECIAL_EVENT",
  "BRIDGE_TUNNEL_RESTRICTION",
  "LANE_RESTRICTION",
  "ROAD_HAZARD",
  "MARATHON",
  "SPORTING_EVENT",
  "VIP_MOVEMENT",
  "TURN_RESTRICTION",
  "WEATHER_CLOSURE",
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

/** Event types that count as a road closure in dashboard statistics. */
export const ROAD_CLOSURE_EVENT_TYPES: readonly EventType[] = [
  "PLANNED_ROAD_CLOSURE",
  "EMERGENCY_ROAD_CLOSURE",
];

/**
 * Public events: meetings, speeches, parades, runs, matches, VIP visits. Their
 * road blocks are kept at any length, and their exact location is shown.
 * The same list as the API's (packages/source_models/road_block.py).
 */
export const PUBLIC_EVENT_TYPES: readonly EventType[] = [
  "SPECIAL_EVENT",
  "PUBLIC_PROCESSION",
  "MARATHON",
  "SPORTING_EVENT",
  "VIP_MOVEMENT",
];

/** Where a public event's road block is, as exactly as the source states it. */
export interface PublicEventLocation {
  /** The source gives the exact spot or stretch (or a reviewer placed it). */
  exact: boolean;
  /** The place names as stated: the venue, road stretch or named place. */
  places: string[];
}

export function publicEventLocation(event: RoadEvent): PublicEventLocation | null {
  if (!event.eventType || !PUBLIC_EVENT_TYPES.includes(event.eventType)) return null;
  const detection = event.detection;
  const locationClass = detection?.locationClass ?? "UNRESOLVED";
  const exact = locationClass !== "APPROXIMATE" && locationClass !== "UNRESOLVED";
  const named = [
    ...(detection?.affectedLocations ?? []).map((place) => place.name),
    detection?.location?.placeName,
    event.affectedRoad,
  ].filter((name): name is string => Boolean(name));
  return { exact, places: [...new Set(named)] };
}

/** Ordered from least to most severe. */
export const EVENT_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type EventSeverity = (typeof EVENT_SEVERITIES)[number];

export const EVENT_DIRECTIONS = [
  "BOTH_DIRECTIONS",
  "NORTHBOUND",
  "SOUTHBOUND",
  "EASTBOUND",
  "WESTBOUND",
  "UNKNOWN",
] as const;
export type EventDirection = (typeof EVENT_DIRECTIONS)[number];

/** GeoJSON position: [longitude, latitude]. */
export type Position = [longitude: number, latitude: number];

export interface PointGeometry {
  type: "Point";
  coordinates: Position;
}
export interface LineStringGeometry {
  type: "LineString";
  coordinates: Position[];
}
export interface PolygonGeometry {
  type: "Polygon";
  coordinates: Position[][];
}
/** Several lines: the street segments of one disruption, as an official source gives them. */
export interface MultiLineStringGeometry {
  type: "MultiLineString";
  coordinates: Position[][];
}
export interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: Position[][][];
}
/** GeoJSON geometry describing where an event affects the road network. */
export type EventGeometry =
  | PointGeometry
  | LineStringGeometry
  | PolygonGeometry
  | MultiLineStringGeometry
  | MultiPolygonGeometry;

/**
 * How an event's location was obtained. Only SOURCE_PROVIDED, GIS_RESOLVED,
 * HUMAN_CORRECTED and QC_APPROVED are positions of the event itself;
 * APPROXIMATE is the position of a place the source names.
 */
export const LOCATION_CLASSES = [
  "APPROXIMATE",
  "SOURCE_PROVIDED",
  "GIS_RESOLVED",
  "HUMAN_CORRECTED",
  "QC_APPROVED",
  "UNRESOLVED",
] as const;
export type LocationClass = (typeof LOCATION_CLASSES)[number];

/** One place an event affects; an event may affect several. */
export interface AffectedLocation {
  name: string;
  kind: string | null;
  resolution: LocationClass;
  geometry: EventGeometry | null;
  /** As the source states it, e.g. "Westbound". */
  direction: string | null;
  /** As the source states it, e.g. "Closed". */
  closure: string | null;
  foundIn: string | null;
  /** What the place is to the event, from an AI reading (CLOSED, DIVERSION_ROUTE …); null otherwise. */
  role: string | null;
}

/** A place an AI reading found in the article, with its role. */
export interface AiPlaceView {
  name: string;
  role: string;
  foundIn: string | null;
  quote: string | null;
}

/** A language model's reading of the article, after REI checked it against the article. */
export interface AiReadingView {
  model: string;
  readAt: string;
  /** "triage" (headline check) or "full" (whole article). */
  stage: string;
  isRoadEvent: boolean;
  why: string | null;
  intent: EventType | null;
  impact: string | null;
  cause: string | null;
  summary: string | null;
  city: string | null;
  inScope: boolean | null;
  places: AiPlaceView[];
  periodText: string | null;
  /** "rules" when REI's date rules read the words, "ai" when only the model did. */
  periodReadBy: string | null;
  startTime: string | null;
  endTime: string | null;
  authority: string | null;
  evidence: string | null;
  discarded: string[];
}

/** What kind of source an event came from, and how far its word carries. */
export interface SourceAuthority {
  /** AUTHORITATIVE_OFFICIAL, GOVERNMENT_OPEN_DATA, PARTNER, PUBLISHER, DISCOVERY, COMMERCIAL; null for manual entry. */
  sourceClass: string | null;
  /** 1 official … 4 discovery; null when not assigned. */
  tier: number | null;
  /** News and search: finds reports, never confirms them. */
  discoveryOnly: boolean;
}

/** Where an event was acquired from. */
export interface EventSource {
  id: string;
  name: string;
  /** RSS, API, MANUAL, … */
  type: string;
}

/** The stored original (e.g. a news article) an event was derived from. Every event has one. */
export interface EventEvidence {
  url: string | null;
  title: string;
  publishedAt: string | null;
  retrievedAt: string;
}

/**
 * How an event was placed on the map: by a place its source names, at that
 * place's position on OpenStreetMap. Not a surveyed extent of the event.
 */
export interface EventLocation {
  /**
   * "named_place" (looked up by name), "reviewer_placed" (a reviewer's point) or
   * "source_provided" (geometry the source publishes).
   */
  method: string;
  placeName: string;
  /** junction, flyover, landmark, road or area. */
  placeKind: string;
  /** Where the source names the place: title, summary or body. */
  foundIn: string;
  /** The map feature the position comes from. */
  reference: string;
  /** The locality the headline names, when the event is placed at a spot inside it. */
  within: string | null;
}

/** A reviewer's extension of an event beyond the end first recorded. */
export interface PeriodRevision {
  /** The end the event had before, e.g. the one its article stated. */
  previousEnd: string | null;
  /** How the reviewer knows, in their words. */
  reason: string;
  revisedAt: string;
}

/** A reviewer's correction of where an event is. */
export interface LocationRevision {
  /** The place the event was located by before, if it was located. */
  previousPlaceName: string | null;
  /** How the reviewer knows where it is, in their words. */
  reason: string;
  revisedAt: string;
}

/** A reviewer's REI severity for an event: REI's own judgment, never read from text. */
export interface SeverityAssessment {
  severity: EventSeverity;
  assessedBy: string;
  assessedAt: string;
  reason: string | null;
  version: number;
}

/** A reviewer's QC approval of an event. */
export interface QcApproval {
  approvedBy: string;
  approvedAt: string;
  /** The reviewer's reason, as given with the decision. */
  reason: string | null;
  /** The event version the approval created, in its history. */
  version: number;
  /** Approved anyway: the reviewer overrode the QC checks in `overridden`. */
  forced: boolean;
  overridden: string[];
}

/** The location method of a point a reviewer put on the map. */
export const REVIEWER_PLACED = "reviewer_placed";

/** How a manually entered event is told apart from a detected one. */
export const MANUAL_ENTRY_METHOD = "manual_entry";

/** Why a source item was detected as a road event. */
export interface EventDetection {
  /** "ai_reading" or "keyword_rules" for a detected article, "manual_entry" for a reviewer's entry. */
  method: string;
  matchedKeywords: string[];
  /** Road names found verbatim in the source text; unverified. */
  roadMentions: string[];
  location: EventLocation | null;
  /** The source's own words the start and end were read from. */
  statedPeriod: string | null;
  /** A distance the source states, in its own words ("100 meter"); never measured by REI. */
  statedDistance: string | null;
  /** The stated distance in metres, read from its unit. */
  statedDistanceM: number | null;
  /** Length measured on the source's own line, in metres; null when it draws none. */
  sourceGeometryLengthM: number | null;
  /** Authorities the source says announced the measure. */
  attributedTo: string[];
  /** For a manual entry: how the reviewer knows of the event. */
  basis: string | null;
  periodRevision: PeriodRevision | null;
  locationRevision: LocationRevision | null;
  /** Set when a reviewer approved the event in QC. */
  qcApproval: QcApproval | null;
  /** A reviewer's REI severity assessment: who set it, when and why. */
  severityAssessment: SeverityAssessment | null;
  /** How the location was obtained; null for an event from before 6 October 2026's API. */
  locationClass: LocationClass | null;
  /** Every place the event affects, located or not. */
  affectedLocations: AffectedLocation[];
  /** What an official source states, in its own words. */
  sourceCategory: string | null;
  sourceSeverity: string | null;
  /** The attribution the source's licence requires. */
  attribution: string | null;
  /** The latest revision the source made to its record, applied to the event. */
  sourceRevision: SourceRevisionNote | null;
  /** A revision that came after a reviewer decided the event: not applied. */
  pendingSourceRevision: SourceRevisionNote | null;
  /** The source itself reports the event cleared, cancelled or ended. */
  sourceReportsEnded: boolean;
  /** Official sources: whether recent refreshes still listed the record. */
  observation: {
    lastSeenAt: string | null;
    missingSince: string | null;
    missedRefreshes: number;
    reviewRequired: boolean;
  } | null;
  /** Which event (and source) each field of a merged event came from. */
  provenance: Record<string, { eventId: string; sourceId: string }>;
  /** Fields the merged sources disagree on; every value is kept. */
  mergeConflicts: { field: string; values: { eventId: string; sourceId: string; value: unknown }[] }[];
  mergeReviewRequired: boolean;
  /** The latest GIS resolution; null when the resolver has not run on this event. */
  gis: GisResolutionView | null;
  /** A language model's reading of the article; null when none was made. */
  ai: AiReadingView | null;
}

/** A road-network candidate, with how and why it was found. */
export interface GisCandidateView {
  matchedName: string;
  method: string;
  geometry: EventGeometry | null;
  osmIds: string[];
  reasons: string[];
}

/** What the GIS resolver found for one place the event names. */
export interface GisResultView {
  mention: string;
  foundIn: string;
  kind: string;
  /** HIGH, MEDIUM, LOW or UNRESOLVED. */
  confidence: string;
  ambiguous: boolean;
  chosen: GisCandidateView | null;
  alternatives: GisCandidateView[];
  reasons: string[];
  applied: boolean;
}

export interface GisResolutionView {
  network: string;
  resolvedAt: string;
  results: GisResultView[];
  applied: boolean;
  notAppliedReason: string | null;
  /** PENDING, APPROVED, REJECTED, SUPERSEDED or NOT_APPLIED. */
  reviewStatus: string;
  reviewedBy: string | null;
  reviewReason: string | null;
}

/** The evidence of an event merged into another, with its source. */
export interface OtherEvidence {
  eventId: string;
  sourceName: string;
  sourceClass: string | null;
  url: string | null;
  title: string;
  publishedAt: string | null;
  /** "automatic" or "reviewer". */
  how: string | null;
}

/** An event that may be the same as this one, awaiting a reviewer. */
export interface MergeCandidate {
  candidateId: number;
  /** SAME or POSSIBLE. */
  classification: string;
  reasons: string[];
  conflicts: { field: string }[];
  otherEventId: string;
  otherTitle: string;
  otherSourceName: string;
}

/** A source's revision of the record an event came from. */
export interface SourceRevisionNote {
  /** The version of the source record; the original is 1. */
  revision: number;
  revisedAt: string;
  /** What changed, in plain words. */
  changes: string[];
}

/** The detection method of an event an official source states itself. */
export const SOURCE_PROVIDED_METHOD = "source_provided";

export function isSourceProvided(event: RoadEvent): boolean {
  return event.detection?.method === SOURCE_PROVIDED_METHOD;
}

export function isManualEntry(event: RoadEvent): boolean {
  return event.detection?.method === MANUAL_ENTRY_METHOD;
}

/**
 * A road event. Named `RoadEvent` rather than `Event` to avoid shadowing the
 * DOM's global `Event` type.
 */
export interface RoadEvent {
  id: string;
  title: string;
  eventType: EventType | null;
  description: string | null;
  affectedRoad: string | null;
  city: string | null;
  /** Representative point of the geometry, for the map marker. */
  latitude: number | null;
  longitude: number | null;
  /** ISO 8601. */
  startTime: string | null;
  endTime: string | null;
  status: EventStatus;
  severity: EventSeverity | null;
  direction: EventDirection | null;
  /** Null until GIS resolution has located the event. */
  geometry: EventGeometry | null;
  /** 0–1; null until a confidence assessment exists. */
  confidence: number | null;
  source: EventSource;
  sourceAuthority: SourceAuthority;
  /** Evidence of the events merged into this one: every other source that reported it. */
  otherEvidence: OtherEvidence[];
  /** Events that may be the same, awaiting a reviewer's decision. */
  mergeCandidates: MergeCandidate[];
  /**
   * For an event in QC_PENDING: every QC requirement it does not yet meet, as
   * the API states them. Empty when it can be approved (and for other statuses).
   */
  approvalBlockers: string[];
  /** Link to the event within its source, e.g. the article URL. */
  sourceReference: string | null;
  evidence: EventEvidence | null;
  detection: EventDetection | null;
}

/** An event that has been located and can be drawn on the map. */
export type LocatedEvent = RoadEvent & {
  geometry: EventGeometry;
  latitude: number;
  longitude: number;
};

export function isLocated(event: RoadEvent): event is LocatedEvent {
  return event.geometry !== null && event.latitude !== null && event.longitude !== null;
}
