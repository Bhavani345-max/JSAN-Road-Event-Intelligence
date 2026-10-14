import { describe, expect, it } from "vitest";
import { toEventMapData } from "@/features/map/geojson";
import type { ApiEvent } from "@/types/api";
import { mapApiEvent } from "./api/eventRepository";
import { realApiEvent } from "./testing/fixtures";

type ApiGis = NonNullable<NonNullable<ApiEvent["detection"]>["gis"]>;
type ApiResult = ApiGis["results"][number];

const junction: [number, number] = [78.405, 17.4];

const appliedResult: ApiResult = {
  mention: "Test Main Road and Cross Road Avenue",
  found_in: "title",
  kind: "crossing",
  confidence: "HIGH",
  ambiguous: false,
  chosen: {
    matched_name: "Test Main Road × Cross Road Avenue",
    method: "ROAD_INTERSECTION",
    geometry: { type: "Point", coordinates: junction },
    osm_ids: ["node/11"],
    reasons: ["the two roads share OSM node 11"],
  },
  alternatives: [],
  reasons: [],
  applied: true,
};

const ambiguousResult: ApiResult = {
  mention: "Twin Road",
  found_in: "title",
  kind: "road",
  confidence: "MEDIUM",
  ambiguous: true,
  chosen: null,
  alternatives: [
    {
      matched_name: "Twin Road",
      method: "EXACT_ROAD_NAME",
      geometry: { type: "LineString", coordinates: [[78.4, 17.4], [78.405, 17.395]] },
      osm_ids: ["way/5"],
      reasons: [],
    },
    {
      matched_name: "Twin Road",
      method: "EXACT_ROAD_NAME",
      geometry: { type: "LineString", coordinates: [[78.47, 17.46], [78.475, 17.46]] },
      osm_ids: ["way/6"],
      reasons: [],
    },
  ],
  reasons: ["2 separate roads are named “Twin Road”"],
  applied: false,
};

/** A test event with a GIS proposal (test data, shaped like the API's answer). */
const gisApiEvent: ApiEvent = {
  ...realApiEvent,
  event_id: "EVT-GIS000000001",
  geometry: { type: "Point", coordinates: junction },
  detection: {
    ...realApiEvent.detection!,
    location_class: "GIS_RESOLVED",
    gis: {
      engine: "osm-deterministic-1",
      network: "OpenStreetMap test-network",
      resolved_at: "2026-10-06T12:00:00Z",
      results: [appliedResult, ambiguousResult],
      applied: true,
      not_applied_reason: null,
      review_status: "PENDING",
      reviewed_by: null,
      reviewed_at: null,
      review_reason: null,
    },
  },
};

describe("GIS results", () => {
  const event = mapApiEvent(gisApiEvent)!;

  it("keeps every result with its confidence, method and OSM ids", () => {
    const gis = event.detection?.gis;
    expect(gis?.reviewStatus).toBe("PENDING");
    expect(gis?.results.map((r) => [r.mention, r.confidence, r.ambiguous])).toEqual([
      ["Test Main Road and Cross Road Avenue", "HIGH", false],
      ["Twin Road", "MEDIUM", true],
    ]);
    expect(gis?.results[0].chosen?.osmIds).toEqual(["node/11"]);
    expect(gis?.results[1].alternatives).toHaveLength(2);
  });

  it("marks the event's marker as GIS resolved, not as source or approximate", () => {
    const data = toEventMapData([event], null);
    expect(data.anchors.features[0].properties.locationClass).toBe("GIS_RESOLVED");
    expect(data.anchors.features[0].properties.approximate).toBe(false);
  });

  it("draws candidates that were not applied only for the selected event, as candidates", () => {
    const unselected = toEventMapData([event], null);
    expect(unselected.geometries.features.filter((f) => f.properties.candidate)).toHaveLength(0);
    const selected = toEventMapData([event], event.id);
    const candidates = selected.geometries.features.filter((f) => f.properties.candidate);
    expect(candidates).toHaveLength(2);
    expect(candidates.every((f) => f.properties.dashed && f.geometry.type === "LineString")).toBe(true);
  });

  it("an event without GIS results has none", () => {
    expect(mapApiEvent(realApiEvent)?.detection?.gis ?? null).toBeNull();
  });
});
