import { describe, expect, it } from "vitest";
import { mapApiEvent } from "@/features/events/api/eventRepository";
import type { EventGeometry, RoadEvent } from "@/features/events/model";
import { locatedApiEvent, realApiEvent } from "@/features/events/testing/fixtures";
import { toEventMapData } from "./geojson";
import { getRepresentativePoint } from "./geometry";
import {
  defaultRange,
  describeCount,
  eventsInArea,
  hasOwnArea,
  placeAreaOf,
} from "./placeArea";
import type { FoundPlace } from "./placeSearch";

const located = mapApiEvent(locatedApiEvent)!;
const unlocated = mapApiEvent(realApiEvent)!;

/** An event drawn at `geometry`, its marker where the map would put it. */
function eventAt(id: string, geometry: EventGeometry): RoadEvent {
  const [longitude, latitude] = getRepresentativePoint(geometry);
  return { ...located, id, geometry, latitude, longitude };
}

// Gachibowli, Hyderabad: as OpenStreetMap answered on 5 November 2026.
const GACHIBOWLI: FoundPlace = {
  name: "Gachibowli",
  detail: "Ward 105 Gachibowli, Greater Hyderabad",
  latitude: 17.4401,
  longitude: 78.3489,
  box: [78.329, 17.42, 78.369, 17.46],
  kind: "suburb",
  source: "nominatim",
  in_area: true,
};
// PIN 500032: a point, with a 10 × 10 km box that is only an estimate.
const PIN: FoundPlace = { ...GACHIBOWLI, name: "500032", kind: "postcode", box: [78.30, 17.40, 78.40, 17.49] };
// One 220 m piece of a street.
const STREET: FoundPlace = { ...GACHIBOWLI, name: "Road Number 1", kind: "primary", box: [78.4480, 17.4150, 78.4488, 17.4170] };
// From REI's own place list: a point only.
const LISTED_AREA: FoundPlace = { ...GACHIBOWLI, box: null, kind: "area", source: "place_list" };
const LANDMARK: FoundPlace = { ...GACHIBOWLI, box: null, kind: "landmark", source: "place_list" };

// About 1 km of latitude.
const KM_LAT = 1 / 110.574;

describe("what counts as in a found place", () => {
  it("uses the place's own area only when OpenStreetMap gives it one", () => {
    expect(hasOwnArea(GACHIBOWLI)).toBe(true);
    expect(defaultRange(GACHIBOWLI)).toBe("area");
    // A postcode's box is an estimate, not its boundary; a street piece is not an area.
    expect(hasOwnArea(PIN)).toBe(false);
    expect(defaultRange(PIN)).toBe(2000);
    expect(hasOwnArea(STREET)).toBe(false);
    expect(defaultRange(STREET)).toBe(1000);
    expect(defaultRange(LISTED_AREA)).toBe(2000);
    expect(defaultRange(LANDMARK)).toBe(1000);
  });

  it("falls back to a distance when a place without an area is asked for its area", () => {
    const area = placeAreaOf(LANDMARK, "area");
    expect(area.range).toBe(1000);
    expect(area.shape.kind).toBe("circle");
  });

  it("draws a closed outline and frames the circle", () => {
    const area = placeAreaOf(LANDMARK, 2000);
    const ring = area.outline.coordinates[0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
    const [, south, , north] = area.bounds;
    expect((north - south) / KM_LAT).toBeCloseTo(4, 3);
  });

  it("says how many, and what in means", () => {
    expect(describeCount(0, 1000)).toBe("No events within 1 km");
    expect(describeCount(1, 500)).toBe("1 event within 500 m");
    expect(describeCount(4, "area")).toBe("4 events inside the outlined area");
  });
});

describe("events in a found place", () => {
  const { latitude: lat, longitude: lng } = LANDMARK;

  it("counts a point by its distance from the place", () => {
    const near = eventAt("near", { type: "Point", coordinates: [lng, lat + 0.5 * KM_LAT] });
    const far = eventAt("far", { type: "Point", coordinates: [lng, lat + 1.5 * KM_LAT] });
    expect([...eventsInArea([near, far], placeAreaOf(LANDMARK, 1000))]).toEqual(["near"]);
    expect([...eventsInArea([near, far], placeAreaOf(LANDMARK, 2000))].sort()).toEqual(["far", "near"]);
  });

  it("counts a road that crosses the place with no vertex in it", () => {
    // 4 km long, east to west through the place; its marker is outside too (moved below).
    const crossing: RoadEvent = {
      ...eventAt("crossing", { type: "LineString", coordinates: [[lng - 0.02, lat], [lng + 0.02, lat]] }),
      latitude: lat + 0.03,
    };
    const passing = eventAt("passing", {
      type: "LineString",
      coordinates: [[lng - 0.02, lat + 1.2 * KM_LAT], [lng + 0.02, lat + 1.2 * KM_LAT]],
    });
    expect([...eventsInArea([crossing, passing], placeAreaOf(LANDMARK, 1000))]).toEqual(["crossing"]);
  });

  it("counts an area that covers the whole place", () => {
    const zone = eventAt("zone", {
      type: "Polygon",
      coordinates: [[[lng - 0.1, lat - 0.1], [lng + 0.1, lat - 0.1], [lng + 0.1, lat + 0.1], [lng - 0.1, lat + 0.1], [lng - 0.1, lat - 0.1]]],
    });
    expect(eventsInArea([zone], placeAreaOf(LANDMARK, 500)).has("zone")).toBe(true);
  });

  it("uses the place's own box when it has one", () => {
    const area = placeAreaOf(GACHIBOWLI, "area");
    const inside = eventAt("inside", { type: "Point", coordinates: [78.33, 17.425] });
    const outside = eventAt("outside", { type: "Point", coordinates: [78.38, 17.44] });
    const across = eventAt("across", { type: "LineString", coordinates: [[78.32, 17.47], [78.375, 17.415]] });
    expect([...eventsInArea([inside, outside, across], area)].sort()).toEqual(["across", "inside"]);
  });

  it("never counts an event that has not been located", () => {
    expect(eventsInArea([unlocated], placeAreaOf(LANDMARK, 5000)).size).toBe(0);
  });
});

describe("the map with a place chosen", () => {
  const inside = eventAt("inside", { type: "Point", coordinates: [LANDMARK.longitude, LANDMARK.latitude] });
  const outside = eventAt("outside", { type: "Point", coordinates: [LANDMARK.longitude + 0.1, LANDMARK.latitude] });
  const other = eventAt("other", { type: "Point", coordinates: [LANDMARK.longitude - 0.1, LANDMARK.latitude] });

  it("rings the events in it and draws the others faint, except the selected one", () => {
    const data = toEventMapData([inside, outside, other], "other", new Set(["inside"]));
    const flags = Object.fromEntries(
      data.anchors.features.map((f) => [f.properties.eventId, [f.properties.inPlace, f.properties.dimmed]]),
    );
    expect(flags).toEqual({ inside: [true, false], outside: [false, true], other: [false, false] });
  });

  it("draws nothing faint while no place is chosen", () => {
    const data = toEventMapData([inside, outside], null);
    expect(data.anchors.features.every((f) => !f.properties.dimmed && !f.properties.inPlace)).toBe(true);
  });
});
