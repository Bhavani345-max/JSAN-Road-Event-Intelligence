import { describe, expect, it } from "vitest";
import { mapApiEvent } from "@/features/events/api/eventRepository";
import type { RoadEvent } from "@/features/events/model";
import { locatedApiEvent } from "@/features/events/testing/fixtures";
import type { ApiEvent } from "@/types/api";
import { distinctEvents, spreadStacks, toEventMapData } from "./geojson";

const KBR_PARK: [number, number] = [78.420104, 17.420234];

/** A located test event (test data, shaped like the API's answer). */
function at(id: string, coordinates: [number, number]): RoadEvent {
  const dto: ApiEvent = {
    ...locatedApiEvent,
    event_id: id,
    title: `Test event ${id}`,
    geometry: { type: "Point", coordinates },
  };
  const event = mapApiEvent(dto);
  if (event === null) throw new Error("test event did not map");
  return event;
}

describe("markers that share a spot", () => {
  it("are all kept at their own position and told how many share it", () => {
    const events = [at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK), at("EVT-C", [78.43, 17.43])];
    const { anchors } = toEventMapData(events, null);

    expect(anchors.features.map((f) => f.geometry.coordinates)).toEqual([KBR_PARK, KBR_PARK, [78.43, 17.43]]);
    expect(anchors.features.map((f) => f.properties.stackSize)).toEqual([2, 2, 1]);
    // One marker of the stack is on top and carries the count.
    expect(anchors.features.map((f) => f.properties.stackTop)).toEqual([true, false, true]);
  });

  it("put the selected event on top of its stack", () => {
    const events = [at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK)];
    const { anchors } = toEventMapData(events, "EVT-B");
    expect(anchors.features.find((f) => f.properties.stackTop)?.properties.eventId).toBe("EVT-B");
  });

  it("do not change the geometry drawn for each event", () => {
    const { geometries } = toEventMapData([at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK)], null);
    expect(geometries.features.every((f) => f.properties.stackSize === 1)).toBe(true);
  });
});

describe("the events under a click", () => {
  it("are listed once each, top-most first", () => {
    const hits = [
      { properties: { eventId: "EVT-B", title: "B", detail: "Road closure · NYC DOT" } },
      { properties: { eventId: "EVT-A", title: "A" } },
      { properties: { eventId: "EVT-B", title: "B", detail: "Road closure · NYC DOT" } },
      { properties: null },
    ];
    expect(distinctEvents(hits)).toEqual([
      { id: "EVT-B", title: "B", detail: "Road closure · NYC DOT" },
      { id: "EVT-A", title: "A", detail: "" },
    ]);
  });
});

describe("events at one spot with the same title", () => {
  it("are told apart by their stated periods", () => {
    const first = { ...at("EVT-A", KBR_PARK), title: "Same title" };
    const second = { ...at("EVT-B", KBR_PARK), title: "Same title" };
    first.startTime = "2026-09-15T04:00:00Z";
    first.endTime = "2026-10-15T04:00:00Z";
    second.startTime = "2026-09-26T04:00:00Z";
    second.endTime = "2026-12-25T05:00:00Z";
    const { anchors } = toEventMapData([first, second], null);
    const [a, b] = anchors.features.map((f) => f.properties.detail);
    expect(a).not.toEqual(b);
    expect(a).toContain(first.source.name);
  });
});

describe("markers spread around a spot they share", () => {
  const PX_PER_DEGREE_AT = (zoom: number) => (512 * 2 ** zoom) / 360;

  it("each get a position of their own, and a lone marker stays put", () => {
    const events = [at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK), at("EVT-C", KBR_PARK), at("EVT-D", [78.43, 17.43])];
    const { anchors, leaders } = spreadStacks(toEventMapData(events, null).anchors, 15);
    const positions = anchors.features.map((f) => f.geometry.coordinates.join(","));
    expect(new Set(positions).size).toBe(4);
    expect(anchors.features.find((f) => f.properties.eventId === "EVT-D")?.geometry.coordinates).toEqual([78.43, 17.43]);
    // Every spread marker has a line back to the true spot.
    expect(leaders.features.map((f) => f.properties.eventId).sort()).toEqual(["EVT-A", "EVT-B", "EVT-C"]);
    for (const leader of leaders.features) expect(leader.geometry.coordinates[1]).toEqual(KBR_PARK);
  });

  it("sit the same number of pixels from the spot at every zoom", () => {
    const events = [at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK)];
    for (const zoom of [10, 14, 18]) {
      const { anchors } = spreadStacks(toEventMapData(events, null).anchors, zoom);
      for (const feature of anchors.features) {
        const [lng, lat] = feature.geometry.coordinates;
        const dxPx = (lng - KBR_PARK[0]) * PX_PER_DEGREE_AT(zoom);
        const dyPx = ((lat - KBR_PARK[1]) * PX_PER_DEGREE_AT(zoom)) / Math.cos((KBR_PARK[1] * Math.PI) / 180);
        expect(Math.hypot(dxPx, dyPx)).toBeCloseTo(16, 1);
      }
    }
  });

  it("move only what is drawn: event geometry and the input are unchanged", () => {
    const events = [at("EVT-A", KBR_PARK), at("EVT-B", KBR_PARK)];
    const data = toEventMapData(events, null);
    spreadStacks(data.anchors, 15);
    expect(data.anchors.features.map((f) => f.geometry.coordinates)).toEqual([KBR_PARK, KBR_PARK]);
    expect(data.geometries.features.map((f) => f.geometry)).toEqual(events.map((e) => e.geometry));
  });
});
