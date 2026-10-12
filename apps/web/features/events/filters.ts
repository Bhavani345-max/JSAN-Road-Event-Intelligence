import type { EventSeverity, EventStatus, EventType, RoadEvent } from "./model";
import { zonedInputToTime } from "./presentation";

export const ALL = "ALL";
export type All = typeof ALL;

export const EVENT_LIST_VIEWS = [
  "current_upcoming",
  "current",
  "upcoming",
  "validation",
  "history",
  "rejected",
] as const;
export type EventListView = (typeof EVENT_LIST_VIEWS)[number];

/** The choice that selects events with no type. */
export const UNCLASSIFIED = "UNCLASSIFIED";
export type TypeChoice = EventType | typeof UNCLASSIFIED;

export interface EventFilters {
  /** Free text. See `matchesLocally` and the server search for what it covers. */
  search: string;
  /** Event types to show; several may be chosen. Empty means every type. */
  eventTypes: TypeChoice[];
  status: EventStatus | All;
  severity: EventSeverity | All;
  /** Id of one source, or all sources. */
  sourceId: string | All;
  /**
   * Start and end of the period to show, as a date-time input gives them
   * ("2026-10-05T18:30", India Standard Time); "" when not set.
   */
  from: string;
  to: string;
}

export const DEFAULT_FILTERS: EventFilters = {
  search: "",
  eventTypes: [],
  status: ALL,
  severity: ALL,
  sourceId: ALL,
  from: "",
  to: "",
};

export function hasDateRange(filters: EventFilters): boolean {
  return filters.from !== "" || filters.to !== "";
}

export function hasActiveFilters(filters: EventFilters): boolean {
  return (
    filters.search.trim() !== "" ||
    filters.eventTypes.length > 0 ||
    filters.status !== ALL ||
    filters.severity !== ALL ||
    filters.sourceId !== ALL ||
    hasDateRange(filters)
  );
}

const MINUTE_MS = 60_000;

function toTime(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  return Number.isNaN(time) ? null : time;
}

/** A date-time input value, read in the time zone every time is shown in (the city's). */
function inputToTime(value: string): number | null {
  return zonedInputToTime(value);
}

/** Report time is used only by explicit date-range filtering, not current status. */
function getReportedTime(event: RoadEvent): number | null {
  return toTime(event.evidence?.publishedAt) ?? toTime(event.evidence?.retrievedAt);
}

export type TimeState = "upcoming" | "ongoing" | "ended";

/** Display label derived from stated event times; API filtering remains authoritative. */
export function getTimeState(event: RoadEvent, now: Date): TimeState | null {
  const start = toTime(event.startTime);
  const end = toTime(event.endTime);
  if (start === null && end === null) return null;
  if (end !== null && end < now.getTime()) return "ended";
  return start !== null && start > now.getTime() ? "upcoming" : "ongoing";
}

/** Whether the event belongs to a city; legacy records without a city are Hyderabad's. */
export function inCity(event: RoadEvent, cityName: string, isDefaultCity: boolean): boolean {
  return event.city === null ? isDefaultCity : event.city === cityName;
}

/** Whether the event's type is among the chosen ones (none chosen: every type). */
export function matchesType(event: RoadEvent, chosen: readonly TypeChoice[]): boolean {
  if (chosen.length === 0) return true;
  return chosen.includes(event.eventType ?? UNCLASSIFIED);
}

/**
 * Whether an event falls in the chosen period. An event with stated times
 * matches when its period overlaps; one without matches by when it was reported.
 */
function matchesDateRange(event: RoadEvent, filters: EventFilters): boolean {
  if (!hasDateRange(filters)) return true;
  const from = inputToTime(filters.from) ?? -Infinity;
  // "To" includes the whole of its minute.
  const to = (inputToTime(filters.to) ?? Infinity) + MINUTE_MS - 1;

  const start = toTime(event.startTime);
  const end = toTime(event.endTime);
  if (start !== null || end !== null) {
    return (start ?? -Infinity) <= to && (end ?? Infinity) >= from;
  }
  const reported = getReportedTime(event);
  return reported !== null && reported >= from && reported <= to;
}

/**
 * Whether the search text is found in what the browser already holds about an
 * event: title, description, road, location and source. Every word must be
 * found. (The article's full text is searched by the API.)
 */
export function matchesLocally(event: RoadEvent, search: string): boolean {
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const text = [
    event.title,
    event.description,
    event.affectedRoad,
    event.city,
    event.source.name,
    event.evidence?.title,
    ...(event.detection?.roadMentions ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return words.every((word) => text.includes(word));
}

/**
 * @param serverMatches Ids the API's search returned (it also covers the full
 *   article text), or null while there is no result for the current search.
 */
export function filterEvents(
  events: RoadEvent[],
  filters: EventFilters,
  serverMatches: ReadonlySet<string> | null = null,
): RoadEvent[] {
  return events.filter(
    (event) =>
      matchesType(event, filters.eventTypes) &&
      (filters.status === ALL || event.status === filters.status) &&
      (filters.severity === ALL || event.severity === filters.severity) &&
      (filters.sourceId === ALL || event.source.id === filters.sourceId) &&
      matchesDateRange(event, filters) &&
      (matchesLocally(event, filters.search) || (serverMatches?.has(event.id) ?? false)),
  );
}
