import { describe, expect, it } from "vitest";
import type { ApiAnalytics } from "@/types/api";
import {
  analyticsQuery,
  DEFAULT_ANALYTICS_FILTERS,
  formatShare,
  kpis,
  lastDays,
  topWithOther,
} from "./analytics";

const answer: ApiAnalytics = {
  generated_at: "2026-10-30T09:00:00Z",
  time_zone: "UTC",
  definitions: { total: "T", awaiting_review: "A", validated: "V", closed: "C", rejected: "R", published: "P (a subset)", in_review_queue: "Q", gis_pending: "G" },
  totals: { total: 100, awaiting_review: 70, validated: 20, closed: 6, rejected: 4, published: 15, in_review_queue: 40, gis_pending: 33, merged: 9 },
  by_city: [], by_category: [], by_status: [], by_location: [], by_day: [], validation_by_city: [], by_source: [],
};

describe("KPIs", () => {
  it("shows the exclusive groups that add up to the total, apart from the overlapping subsets", () => {
    const { exclusive, subsets } = kpis(answer);
    const [total, ...groups] = exclusive;
    expect(total.value).toBe(100);
    expect(groups.map((g) => g.key)).toEqual(["awaiting_review", "validated", "closed", "rejected"]);
    expect(groups.reduce((sum, g) => sum + g.value, 0)).toBe(total.value);
    expect(subsets.map((s) => [s.key, s.value, s.shareOf])).toEqual([
      ["published", 15, "of validated"],
      ["in_review_queue", 40, "of awaiting validation"],
      ["gis_pending", 33, "of total"],
    ]);
    expect(subsets[0].share).toBeCloseTo(0.75);
    // Every number carries the API's own definition.
    expect([...exclusive, ...subsets].every((k) => k.definition !== "")).toBe(true);
  });

  it("never rounds a share to none or to all when it is neither", () => {
    expect(formatShare(43545 / 43563)).toBe(">99.9%");
    expect(formatShare(12 / 43563)).toBe("<0.1%");
    expect(formatShare(1)).toBe("100%");
    expect(formatShare(0)).toBe("0%");
    expect(formatShare(0.995)).toBe("99.5%");
    expect(formatShare(1 / 6)).toBe("17%");
    expect(formatShare(0.054)).toBe("5.4%");
  });

  it("shows no share of nothing", () => {
    const empty = { ...answer, totals: { ...answer.totals, total: 0, validated: 0, published: 0 } };
    expect(kpis(empty).subsets[0].share).toBeNull();
    expect(formatShare(null)).toBe("–");
  });
});

describe("the Other row", () => {
  it("keeps every count: nothing is dropped from a chart", () => {
    const rows = [5, 4, 3, 2, 1].map((count, i) => ({ label: `C${i}`, count }));
    const shown = topWithOther(rows, 3, (count, rest) => ({ label: `Other (${rest})`, count }));
    expect(shown.map((r) => r.label)).toEqual(["C0", "C1", "Other (3)"]);
    expect(shown.reduce((sum, r) => sum + r.count, 0)).toBe(15);
  });
});

describe("the query", () => {
  it("sends every filter and the time zone the days are read in", () => {
    const query = new URLSearchParams(
      analyticsQuery(
        { ...DEFAULT_ANALYTICS_FILTERS, cityId: "india", start: "2026-10-01", end: "2026-10-30", eventType: "ROAD_WORKS", statusGroup: "validated", sourceId: "telangana-today" },
        "Asia/Kolkata",
      ),
    );
    expect(Object.fromEntries(query)).toEqual({
      tz: "Asia/Kolkata", city: "india", start: "2026-10-01", end: "2026-10-30",
      event_type: "ROAD_WORKS", status_group: "validated", source_id: "telangana-today",
    });
    expect(analyticsQuery(DEFAULT_ANALYTICS_FILTERS, "UTC")).toBe("tz=UTC");
  });

  it("counts the last days in the place's own calendar", () => {
    // 20:00 UTC on 30 October is already 31 October in Hyderabad.
    const now = new Date("2026-10-30T20:00:00Z");
    expect(lastDays(7, now, "Asia/Kolkata")).toEqual({ start: "2026-10-25", end: "2026-10-31" });
    expect(lastDays(7, now, "UTC")).toEqual({ start: "2026-10-24", end: "2026-10-30" });
    expect(lastDays(30, new Date("2026-03-01T12:00:00Z"), "UTC")).toEqual({ start: "2026-01-31", end: "2026-03-01" });
  });
});
