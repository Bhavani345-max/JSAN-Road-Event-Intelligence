import { describe, expect, it } from "vitest";
import type { ApiEvent } from "@/types/api";
import { mapApiEvent } from "./api/eventRepository";
import { DEFAULT_FILTERS, filterEvents, matchesLocation, setFilterCount } from "./filters";
import { historyStages, type EventVersionView } from "./history";
import { locationStatusOf, type RoadEvent } from "./model";
import { gisStatus } from "./presentation";
import { locatedApiEvent, realApiEvent } from "./testing/fixtures";

function event(overrides: Partial<ApiEvent>, detection: Partial<NonNullable<ApiEvent["detection"]>> = {}): RoadEvent {
  return mapApiEvent({
    ...locatedApiEvent,
    ...overrides,
    detection: { ...realApiEvent.detection!, ...detection },
  })!;
}

const gisPending = {
  engine: "t", network: "t", resolved_at: "2026-10-01T00:00:00Z", results: [], applied: true,
  not_applied_reason: null, review_status: "PENDING", reviewed_by: null, reviewed_at: null, review_reason: null,
};

describe("location status (map toolbar, sidebar filter, card badge)", () => {
  it("is one rule for all three", () => {
    expect(locationStatusOf(mapApiEvent(realApiEvent)!)).toBe("NOT_LOCATED");
    expect(locationStatusOf(event({}, { location_class: "SOURCE_PROVIDED" }))).toBe("SOURCE_PROVIDED");
    expect(locationStatusOf(event({}, { location_class: "APPROXIMATE" }))).toBe("APPROXIMATE");
    expect(locationStatusOf(event({}, { location_class: "UNRESOLVED" }))).toBe("NOT_LOCATED");
    expect(locationStatusOf(event({}, { location_class: "GIS_RESOLVED", gis: gisPending }))).toBe("GIS_PENDING");
    expect(gisStatus(event({}, { location_class: "GIS_RESOLVED", gis: gisPending }))?.label).toBe("GIS review pending");
  });

  it("filters the list and the map alike, and counts in the Filters badge", () => {
    const approximate = event({ event_id: "EVT-A" }, { location_class: "APPROXIMATE" });
    const exact = event({ event_id: "EVT-B" }, { location_class: "SOURCE_PROVIDED" });
    const filters = { ...DEFAULT_FILTERS, locations: ["APPROXIMATE" as const] };
    expect(filterEvents([approximate, exact], filters).map((e) => e.id)).toEqual(["EVT-A"]);
    expect(matchesLocation(exact, [])).toBe(true);
    expect(setFilterCount(filters)).toBe(1);
  });
});

describe("a filter choice no loaded event has", () => {
  const roadWorks = event({ event_id: "EVT-1", event_type: "ROAD_WORKS" }, { location_class: "SOURCE_PROVIDED" });

  it("stays chosen and empties the list, which then offers to clear it (30 Oct 2026 fix)", () => {
    // A choice the loaded events lack used to be dropped at once, so it unticked
    // itself in the Filters panel: in the operations view, nearly every type did.
    const filters = { ...DEFAULT_FILTERS, eventTypes: ["VIP_MOVEMENT" as const], locations: ["APPROXIMATE" as const] };
    expect(filterEvents([roadWorks], filters)).toEqual([]);
    expect(filters.eventTypes).toEqual(["VIP_MOVEMENT"]);
    expect(setFilterCount(filters)).toBe(2);
  });

  it("leaves the events it matches", () => {
    const filters = { ...DEFAULT_FILTERS, eventTypes: ["ROAD_WORKS" as const] };
    expect(filterEvents([roadWorks], filters).map((e) => e.id)).toEqual(["EVT-1"]);
  });
});

describe("validation history", () => {
  const v = (version: number, status: EventVersionView["status"], reason: string | null, changedBy = "ingestion"): EventVersionView => ({
    version, status, reason, changedBy, at: `2026-10-0${version}T08:00:00Z`,
  });

  it("names each step only from what its version records", () => {
    const stages = historyStages([
      v(3, "QC_PENDING", "Reviewer confirmed the article describes a road event", "reviewer@jsan.com"),
      v(1, "VALIDATION_REQUIRED", "Created from source artifact by keyword detection"),
      v(2, "VALIDATION_REQUIRED", "Located at Khajaguda Jn (17.42270, 78.38170) by a reviewer. Seen on site", "reviewer@jsan.com"),
      v(4, "APPROVED", "Reviewer approved in QC", "reviewer@jsan.com"),
      v(5, "APPROVED", "Not listed by the source for 3 refreshes", "source-update"),
      v(6, "EXPIRED", "Ended", "reviewer@jsan.com"),
    ]);
    expect(stages.map((s) => s.label)).toEqual([
      "Detected",
      "Location corrected",
      "Confirmed as a road event, sent to QC",
      "Validated",
      "Updated by the source",
      "Closed",
    ]);
    expect(stages[1].reason).toContain("Seen on site");
  });

  it("never invents a step: one version is only its detection", () => {
    expect(historyStages([v(1, "VALIDATION_REQUIRED", null)]).map((s) => s.label)).toEqual(["Detected"]);
  });

  it("names a rejection and a return to validation", () => {
    const stages = historyStages([
      v(1, "VALIDATION_REQUIRED", null),
      v(2, "REJECTED", "Not a road event", "reviewer@jsan.com"),
      v(3, "VALIDATION_REQUIRED", "Reviewer returned the event to validation", "reviewer@jsan.com"),
    ]);
    expect(stages.map((s) => s.label)).toEqual(["Detected", "Rejected", "Returned to validation"]);
  });
});
