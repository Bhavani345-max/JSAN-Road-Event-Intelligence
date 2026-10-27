import { ROAD_CLOSURE_EVENT_TYPES, type RoadEvent } from "./model";

export interface EventStats {
  total: number;
  active: number;
  scheduled: number;
  roadClosures: number;
  /** Events waiting for a human to validate them. */
  needsReview: number;
}

/** A count as the console writes it ("94,804"). */
export const formatCount = (value: number) => value.toLocaleString("en-GB");

// Geist semibold's tabular figures, measured in Chrome on 27 October 2026: a digit
// is 0.624 em wide, a comma 0.225 em. Rounded up (about 2.5 %) so a tile never
// clips a number where a browser draws the font a little wider.
const DIGIT_EM = 0.64;
const SEPARATOR_EM = 0.24;
/** The size a tile's number has when it fits (Tailwind's text-2xl). */
const TILE_NUMBER_MAX = "1.5rem";

/** How wide a written count is, in ems of the tiles' number font. */
export function countWidthEm(text: string): number {
  let em = 0;
  for (const character of text) {
    em += character === "," || character === "." ? SEPARATOR_EM : DIGIT_EM;
  }
  return em;
}

/**
 * One font size for every number in a row of stat tiles: 1.5rem, or smaller when
 * the longest number would not fit inside its tile. 100cqi is the width inside the
 * tile (the number's container), so the size follows the tile on any screen.
 */
export function tileNumberSize(values: (number | null)[]): string {
  const widest = Math.max(
    0,
    ...values.map((value) => (value === null ? 0 : countWidthEm(formatCount(value)))),
  );
  if (widest === 0) return TILE_NUMBER_MAX;
  return `min(${TILE_NUMBER_MAX}, calc(100cqi / ${widest.toFixed(2)}))`;
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
