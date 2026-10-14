import type {
  EventDirection,
  EventSeverity,
  EventStatus,
  EventType,
  LocationClass,
  SourceAuthority,
} from "./model";

/**
 * Display vocabulary for the event model: labels, colours and map styling.
 * Shared by the map and the UI so both always agree.
 */

/** "VALIDATION_REQUIRED" -> "Validation Required". */
function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  PLANNED_ROAD_CLOSURE: "Planned Road Closure",
  PUBLIC_PROCESSION: "Procession / Parade",
  ROAD_CONSTRUCTION: "Road Construction",
  TRAFFIC_DIVERSION: "Traffic Diversion",
  FLOODING: "Flooding",
  EMERGENCY_ROAD_CLOSURE: "Emergency Road Closure",
  ROAD_WORKS: "Road Works",
  WATERLOGGING: "Waterlogging",
  ACCIDENT: "Accident",
  SPECIAL_EVENT: "Public Event",
  BRIDGE_TUNNEL_RESTRICTION: "Bridge / Tunnel Restriction",
  LANE_RESTRICTION: "Lane Restriction",
  ROAD_HAZARD: "Road Hazard",
  MARATHON: "Marathon / Run",
  SPORTING_EVENT: "Sporting Event",
  VIP_MOVEMENT: "VIP Movement",
  TURN_RESTRICTION: "Turn Restriction",
  WEATHER_CLOSURE: "Weather Closure",
};

/** Map + UI colour per event type (chosen to read on a light basemap). */
export const EVENT_TYPE_COLORS: Record<EventType, string> = {
  PLANNED_ROAD_CLOSURE: "#7c3aed",
  PUBLIC_PROCESSION: "#db2777",
  ROAD_CONSTRUCTION: "#d97706",
  TRAFFIC_DIVERSION: "#2563eb",
  FLOODING: "#0891b2",
  EMERGENCY_ROAD_CLOSURE: "#dc2626",
  ROAD_WORKS: "#ea580c",
  WATERLOGGING: "#0e7490",
  ACCIDENT: "#b91c1c",
  SPECIAL_EVENT: "#c026d3",
  BRIDGE_TUNNEL_RESTRICTION: "#4f46e5",
  LANE_RESTRICTION: "#0d9488",
  ROAD_HAZARD: "#a16207",
  MARATHON: "#16a34a",
  SPORTING_EVENT: "#65a30d",
  VIP_MOVEMENT: "#be123c",
  TURN_RESTRICTION: "#0369a1",
  WEATHER_CLOSURE: "#475569",
};

/** How a location was obtained, in a few words, and what that means for the reader. */
export const LOCATION_CLASS_LABELS: Record<LocationClass, { label: string; meaning: string }> = {
  APPROXIMATE: {
    label: "Approximate",
    meaning: "The position of a place the source names, not of the event itself.",
  },
  SOURCE_PROVIDED: {
    label: "Source provided",
    meaning: "The geometry the source itself publishes, unchanged.",
  },
  GIS_RESOLVED: {
    label: "GIS resolved",
    meaning: "Matched to the road network.",
  },
  HUMAN_CORRECTED: {
    label: "Corrected by a reviewer",
    meaning: "A reviewer placed the event on the map, with their reason.",
  },
  QC_APPROVED: {
    label: "QC approved",
    meaning: "A reviewer approved the event with this location.",
  },
  UNRESOLVED: {
    label: "Not located",
    meaning: "Named, but no position is known; not drawn on the map.",
  },
};

/** What kind of source an event came from, and how far its word carries, in plain words. */
export function describeSourceAuthority(authority: SourceAuthority): {
  kind: string;
  standing: string;
  official: boolean;
} {
  const tier = authority.tier ? `Tier ${authority.tier}` : "No tier";
  switch (authority.sourceClass) {
    case "AUTHORITATIVE_OFFICIAL":
      return { kind: "Official source", standing: `${tier} · authoritative`, official: true };
    case "GOVERNMENT_OPEN_DATA":
      return { kind: "Official open data", standing: `${tier} · authoritative`, official: true };
    case "PARTNER":
      return { kind: "Partner", standing: tier, official: false };
    case "PUBLISHER":
      return { kind: "Publisher", standing: `${tier} · secondary, not confirmation`, official: false };
    case "DISCOVERY":
      return { kind: "Discovery", standing: `${tier} · a lead only`, official: false };
    case "COMMERCIAL":
      return { kind: "Commercial", standing: tier, official: false };
    default:
      return { kind: "Manual entry", standing: "No tier", official: false };
  }
}

const UNCLASSIFIED_COLOR = "#64748b";

/** A null type means the source did not make the kind of event clear. */
export function getEventTypeLabel(eventType: EventType | null): string {
  return eventType ? EVENT_TYPE_LABELS[eventType] : "Unclassified";
}

export function getEventTypeColor(eventType: EventType | null): string {
  return eventType ? EVENT_TYPE_COLORS[eventType] : UNCLASSIFIED_COLOR;
}

export function getStatusLabel(status: EventStatus): string {
  return status === "QC_PENDING" ? "QC Pending" : titleCase(status);
}

export function getSeverityLabel(severity: EventSeverity): string {
  return titleCase(severity);
}

export const DIRECTION_LABELS: Record<EventDirection, string> = {
  BOTH_DIRECTIONS: "Both directions",
  NORTHBOUND: "Northbound",
  SOUTHBOUND: "Southbound",
  EASTBOUND: "Eastbound",
  WESTBOUND: "Westbound",
  UNKNOWN: "Not specified",
};

export type StatusPhase = "pending" | "upcoming" | "live" | "watch" | "closed";

const STATUS_PHASES: Record<EventStatus, StatusPhase> = {
  DISCOVERED: "pending",
  EXTRACTED: "pending",
  GEO_RESOLVED: "pending",
  VALIDATION_REQUIRED: "pending",
  QC_PENDING: "pending",
  APPROVED: "upcoming",
  SCHEDULED: "upcoming",
  ACTIVE: "live",
  REOPENED: "live",
  EXTENDED: "live",
  MODIFIED: "live",
  MONITORING: "watch",
  EXPIRED: "closed",
  REJECTED: "closed",
  CANCELLED: "closed",
  SUPERSEDED: "closed",
};

/** Collapses the 16 lifecycle statuses into the few phases we style by. */
export function getStatusPhase(status: EventStatus): StatusPhase {
  return STATUS_PHASES[status];
}

export interface StatusMapStyle {
  /** Dashed outline = not (yet) in effect on the road. */
  dashed: boolean;
  opacity: number;
}

const PHASE_MAP_STYLES: Record<StatusPhase, StatusMapStyle> = {
  pending: { dashed: true, opacity: 0.55 },
  upcoming: { dashed: true, opacity: 0.95 },
  live: { dashed: false, opacity: 0.95 },
  watch: { dashed: false, opacity: 0.6 },
  closed: { dashed: false, opacity: 0.3 },
};

export function getStatusMapStyle(status: EventStatus): StatusMapStyle {
  return PHASE_MAP_STYLES[getStatusPhase(status)];
}

/**
 * The time zone every time is shown in: the selected city's. India Standard
 * Time until a city is chosen, as it was before cities were configurable.
 */
export const DEFAULT_TIME_ZONE = "Asia/Kolkata";
let displayTimeZone = DEFAULT_TIME_ZONE;

export function setDisplayTimeZone(timeZone: string): void {
  displayTimeZone = timeZone;
}

export function getDisplayTimeZone(): string {
  return displayTimeZone;
}

/** Each configured city's time zone, by city name and by city id. */
const cityZones = new Map<string, string>();

export function setCityTimeZones(cities: { id: string; name: string; timeZone: string }[]): void {
  cityZones.clear();
  for (const city of cities) {
    cityZones.set(city.name, city.timeZone);
    cityZones.set(city.id, city.timeZone);
  }
}

/**
 * The zone an event's (or a source's) times are shown in: its own city's.
 * Takes a city name or id; the display zone when it has none or is unknown.
 */
export function timeZoneOf(city: string | null | undefined): string {
  return (city && cityZones.get(city)) || displayTimeZone;
}

/** "IST" for India, otherwise the zone's own short name ("BST", "EDT"). */
export function timeZoneLabel(at: Date = new Date(), zone: string = displayTimeZone): string {
  if (zone === DEFAULT_TIME_ZONE) return "IST";
  const part = new Intl.DateTimeFormat("en-GB", {
    timeZone: zone,
    timeZoneName: "short",
  })
    .formatToParts(at)
    .find((p) => p.type === "timeZoneName");
  return part?.value ?? zone;
}

const formats = new Map<string, Intl.DateTimeFormat>();

function cachedFormat(
  key: string,
  options: Intl.DateTimeFormatOptions,
  zone: string = displayTimeZone,
): Intl.DateTimeFormat {
  const id = `${key}|${zone}`;
  let format = formats.get(id);
  if (!format) {
    format = new Intl.DateTimeFormat("en-IN", { ...options, timeZone: zone });
    formats.set(id, format);
  }
  return format;
}

const DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  weekday: "short",
  day: "numeric",
  month: "short",
  // Events run across years (works into 2027), so the year is always shown.
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
};

/** The named parts of a formatted date, so they can be put together one way everywhere. */
function dateParts(format: Intl.DateTimeFormat, date: Date): Record<string, string> {
  return Object.fromEntries(format.formatToParts(date).map((part) => [part.type, part.value]));
}

/** "Sun, 4 Oct 2026, 04:30" in the display time zone; null if missing or invalid. */
export function formatDateTime(iso: string | null, zone: string = displayTimeZone): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const { weekday, day, month, year, hour, minute } = dateParts(
    cachedFormat("datetime", DATE_TIME_OPTIONS, zone),
    date,
  );
  return `${weekday}, ${day} ${month} ${year}, ${hour}:${minute}`;
}

/** "Sun, 4 Oct 2026" in the display time zone; null if missing or invalid. */
export function formatDate(iso: string | null, zone: string = displayTimeZone): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const { weekday, day, month, year } = dateParts(
    cachedFormat("date", { weekday: "short", day: "numeric", month: "short", year: "numeric" }, zone),
    date,
  );
  return `${weekday}, ${day} ${month} ${year}`;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** Year, month, day, hour, minute and second of a moment in the display time zone. */
function zonedParts(time: number, zone: string = displayTimeZone): Record<string, number> {
  const parts = dateParts(
    cachedFormat("parts", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    }, zone),
    new Date(time),
  );
  return Object.fromEntries(Object.entries(parts).map(([key, value]) => [key, Number(value)]));
}

/** How far the display time zone is ahead of UTC at a moment, in milliseconds. */
function zoneOffsetMs(time: number, zone: string = displayTimeZone): number {
  const p = zonedParts(time, zone);
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  return asUtc - Math.floor(time / 1000) * 1000;
}

/** Milliseconds into its day in the display time zone; null if missing or invalid. */
function timeOfDay(iso: string | null, zone: string = displayTimeZone): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return null;
  return (((time + zoneOffsetMs(time, zone)) % DAY_MS) + DAY_MS) % DAY_MS;
}

/**
 * A date-time input value ("2026-10-05T18:30") read as a time in the display
 * time zone; null if empty or invalid.
 */
export function zonedInputToTime(value: string): number | null {
  if (!value) return null;
  const asUtc = new Date(`${value}:00Z`).getTime();
  if (Number.isNaN(asUtc)) return null;
  // Correct by the zone's offset at that moment (twice, across a clock change).
  const first = asUtc - zoneOffsetMs(asUtc);
  return asUtc - zoneOffsetMs(first);
}

/**
 * Whether a period is given in whole days: it starts at the start of a day
 * and ends at the end of one. Such a period has dates but no times of day.
 */
export function isWholeDayPeriod(
  startTime: string | null,
  endTime: string | null,
  zone: string = displayTimeZone,
): boolean {
  const start = timeOfDay(startTime, zone);
  const end = timeOfDay(endTime, zone);
  if (start === null && end === null) return false;
  return (start === null || start === 0) && (end === null || end === DAY_MS - 1000);
}

/** The date in the display time zone as a date input holds it ("2026-10-05"); null if missing. */
export function toDateInputValue(iso: string | null, zone: string = displayTimeZone): string | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  return Number.isNaN(time)
    ? null
    : new Date(time + zoneOffsetMs(time, zone)).toISOString().slice(0, 10);
}

export const NOT_SPECIFIED = "Not specified";

/**
 * Start and end as display text. A known start with no end means the event
 * is open-ended; with no start at all, the source simply gave no times.
 *
 * @param wholeDays The source gave dates without times of day, so none is shown.
 */
export function formatEventPeriod(
  startTime: string | null,
  endTime: string | null,
  wholeDays = false,
  zone: string = displayTimeZone,
): { start: string; end: string } {
  const format = wholeDays ? formatDate : formatDateTime;
  const start = format(startTime, zone);
  const end = format(endTime, zone);
  return {
    start: start ?? NOT_SPECIFIED,
    end: end ?? (start ? "Until further notice" : NOT_SPECIFIED),
  };
}

/** The site an address belongs to, e.g. "thehindu.com"; null if it is not a web address. */
export function getSiteName(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** "85%", or null when confidence has not been assessed. */
export function formatConfidence(confidence: number | null): string | null {
  return confidence === null ? null : `${Math.round(confidence * 100)}%`;
}

/** What happens on the road, as an AI reading names it. */
export const IMPACT_LABELS: Record<string, string> = {
  CLOSURE: "Road closed",
  PARTIAL_CLOSURE: "Partly closed",
  DIVERSION: "Traffic diverted",
  LANE_RESTRICTION: "Lanes restricted",
  TURN_RESTRICTION: "Turn closed",
  ONE_WAY: "One-way",
  VEHICLE_RESTRICTION: "Vehicles barred",
  CONGESTION: "Heavy traffic",
  WATERLOGGING: "Waterlogging",
  HAZARD: "Hazard on the road",
  ADVISORY: "Advisory",
  OTHER: "Other",
};

/** What a place is to the event, as an AI reading gives it. */
export const PLACE_ROLE_LABELS: Record<string, string> = {
  CLOSED: "closed or restricted",
  AFFECTED: "traffic affected",
  STRETCH_FROM: "start of the affected stretch",
  STRETCH_TO: "end of the affected stretch",
  VENUE: "event venue",
  NEAR: "near the event",
  DIVERSION_ROUTE: "diversion route",
  ALTERNATE_ROUTE: "suggested alternative",
};

/** Roles that are where traffic is sent, not where the event is. */
export const ROUTE_ROLES: readonly string[] = ["DIVERSION_ROUTE", "ALTERNATE_ROUTE"];

/** Map colours for roles that do not take the event's own colour. */
export const PLACE_ROLE_COLORS: Record<string, string> = {
  DIVERSION_ROUTE: "#16a34a",
  ALTERNATE_ROUTE: "#16a34a",
  NEAR: "#64748b",
};
