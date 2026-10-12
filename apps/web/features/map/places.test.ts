import { describe, expect, it } from "vitest";
import { mapApiEvent } from "@/features/events/api/eventRepository";
import { EVENT_TYPE_COLORS } from "@/features/events/presentation";
import { locatedApiEvent } from "@/features/events/testing/fixtures";
import type { ApiAiReading, ApiEvent } from "@/types/api";
import { toEventMapData } from "./geojson";

const TANK_BUND: [number, number] = [78.484462, 17.421474];
const LOWER_TANK_BUND: [number, number] = [78.485716, 17.416255];

/** Test data shaped like the API's answer for an event an AI reading found. */
const reading: ApiAiReading = {
  model: "google/gemma-4-26b-a4b-it:free",
  prompt_version: "2026-10-09",
  read_at: "2026-10-09T08:00:00Z",
  stage: "full",
  is_road_event: true,
  why: "Tank Bund Road closed for a cycling festival.",
  intent: "MARATHON",
  impact: "CLOSURE",
  cause: "cycling festival",
  summary: "Tank Bund Road is closed on Sunday morning.",
  city: "Hyderabad",
  in_scope: true,
  places: [
    { name: "Tank Bund Road", role: "CLOSED", found_in: "body", quote: null },
    { name: "Lower Tank Bund", role: "DIVERSION_ROUTE", found_in: "body", quote: null },
  ],
  period_text: "between 5 am and 9 am",
  period_read_by: "ai",
  start_time: "2026-10-12T05:00:00+05:30",
  end_time: "2026-10-12T09:00:00+05:30",
  authority: null,
  evidence: null,
  discarded: ["place 'Banjara Hills' is not in the article"],
};

function located(name: string, coordinates: [number, number], role: string | null) {
  return {
    name,
    kind: "road",
    resolution: "APPROXIMATE",
    geometry: { type: "Point" as const, coordinates },
    direction: null,
    closure: null,
    mention: name,
    found_in: "body",
    reference: "OpenStreetMap way/1",
    role,
  };
}

const dto: ApiEvent = {
  ...locatedApiEvent,
  event_id: "EVT-AI",
  event_type: "MARATHON",
  geometry: { type: "Point", coordinates: TANK_BUND },
  detection: {
    method: "ai_reading",
    score: 2,
    matched_keywords: [],
    road_mentions: ["Tank Bund Road"],
    location: null,
    stated_period: "between 5 am and 9 am",
    location_class: "APPROXIMATE",
    affected_locations: [
      located("Tank Bund Road", TANK_BUND, "CLOSED"),
      located("Lower Tank Bund", LOWER_TANK_BUND, "DIVERSION_ROUTE"),
      // No role: drawn as before, not as a role marker.
      located("Khairatabad", [78.4622, 17.411771], null),
    ],
    ai: reading,
  } as ApiEvent["detection"],
};

describe("an event an AI reading found", () => {
  const event = mapApiEvent(dto)!;

  it("carries the checked reading to the console", () => {
    expect(event.detection?.method).toBe("ai_reading");
    expect(event.detection?.ai?.intent).toBe("MARATHON");
    expect(event.detection?.ai?.impact).toBe("CLOSURE");
    expect(event.detection?.ai?.places.map((p) => p.role)).toEqual(["CLOSED", "DIVERSION_ROUTE"]);
    expect(event.detection?.ai?.discarded).toHaveLength(1);
  });

  it("draws each place by its role only when the event is selected", () => {
    expect(toEventMapData([event], null).places.features).toHaveLength(0);

    const places = toEventMapData([event], "EVT-AI").places.features;
    expect(places.map((f) => [f.properties.name, f.properties.role, f.properties.route])).toEqual([
      ["Tank Bund Road", "CLOSED", false],
      ["Lower Tank Bund", "DIVERSION_ROUTE", true],
    ]);
    // The closed place takes the event's colour; the diversion route is green.
    expect(places[0].properties.color).toBe(EVENT_TYPE_COLORS.MARATHON);
    expect(places[1].properties.color).toBe("#16a34a");
    expect(places[1].properties.label).toBe("Lower Tank Bund · diversion route");
    // Positions are the places' own (OpenStreetMap), unchanged.
    expect(places.map((f) => f.geometry.coordinates)).toEqual([TANK_BUND, LOWER_TANK_BUND]);
  });
});
