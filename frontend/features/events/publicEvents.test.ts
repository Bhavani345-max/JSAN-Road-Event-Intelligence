import { describe, expect, it } from "vitest";
import type { ApiEvent } from "@/types/api";
import { mapApiEvent } from "./api/eventRepository";
import { publicEventLocation, type RoadEvent } from "./model";
import { locatedApiEvent, realApiEvent } from "./testing/fixtures";

/** Test events shaped like the API's answer (test data, not real events). */
function toEvent(dto: ApiEvent): RoadEvent {
  const event = mapApiEvent(dto);
  if (event === null) throw new Error("test event did not map");
  return event;
}

describe("a public event's exact location", () => {
  it("is shown as exact when the source gives the stretch", () => {
    const event = toEvent({
      ...locatedApiEvent,
      event_type: "SPECIAL_EVENT",
      affected_road: "Queen St W",
      detection: {
        ...locatedApiEvent.detection!,
        location_class: "SOURCE_PROVIDED",
        affected_locations: [
          { name: "Queen St W from Bay St to University Ave", kind: "road segment", resolution: "SOURCE_PROVIDED", geometry: null, direction: null, closure: "ROAD_CLOSED", mention: null, found_in: "source", reference: "City of Toronto polyline" },
        ],
      },
    });
    expect(publicEventLocation(event)).toEqual({
      exact: true,
      places: ["Queen St W from Bay St to University Ave", "Queen St W"],
    });
  });

  it("says the source gives no exact spot when only a place is named", () => {
    const event = toEvent({
      ...locatedApiEvent,
      event_type: "SPECIAL_EVENT",
      affected_road: null,
      detection: {
        ...locatedApiEvent.detection!,
        location_class: "APPROXIMATE",
        location: { method: "named_place", place_name: "LB Stadium", place_kind: "landmark", precision: "place", mention: "LB Stadium", found_in: "title", reference: "OpenStreetMap way/1", within: null },
        affected_locations: [],
      },
    });
    expect(publicEventLocation(event)).toEqual({ exact: false, places: ["LB Stadium"] });
  });

  it("is not asked of other events", () => {
    expect(publicEventLocation(toEvent({ ...realApiEvent, event_type: "TRAFFIC_DIVERSION" }))).toBeNull();
  });
});
