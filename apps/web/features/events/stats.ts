import { ROAD_CLOSURE_EVENT_TYPES, type RoadEvent } from "./model";

export interface EventStats {
  total: number;
  active: number;
  scheduled: number;
  roadClosures: number;
  /** Events waiting for a human to validate them. */
  needsReview: number;
}

export function computeEventStats(events: RoadEvent[]): EventStats {
  const count = (matches: (event: RoadEvent) => boolean) => events.filter(matches).length;
  return {
    total: events.length,
    active: count((event) => event.status === "ACTIVE"),
    scheduled: count((event) => event.status === "SCHEDULED"),
    roadClosures: count(
      (event) => event.eventType !== null && ROAD_CLOSURE_EVENT_TYPES.includes(event.eventType),
    ),
    needsReview: count((event) => event.status === "VALIDATION_REQUIRED"),
  };
}
