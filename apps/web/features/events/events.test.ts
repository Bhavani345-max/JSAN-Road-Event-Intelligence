import { describe, expect, it } from "vitest";
import { toEventMapData } from "@/features/map/geojson";
import { mapApiEvent } from "./api/eventRepository";
import {
  DEFAULT_FILTERS,
  filterEvents,
  hasActiveFilters,
  getTimeState,
  isCurrent,
  keepCurrent,
  UNCLASSIFIED,
  matchesLocally,
} from "./filters";
import {
  formatConfidence,
  formatEventPeriod,
  getEventTypeLabel,
  getSiteName,
  isWholeDayPeriod,
  toDateInputValue,
} from "./presentation";
import { computeEventStats } from "./stats";
import { locatedApiEvent, realApiEvent } from "./testing/fixtures";

const real = mapApiEvent(realApiEvent)!;
const located = mapApiEvent(locatedApiEvent)!;
const events = [real, located];

describe("filterEvents", () => {
  it("returns everything with default filters", () => {
    expect(filterEvents(events, DEFAULT_FILTERS)).toEqual(events);
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
  });

  it("filters by an individual source", () => {
    const only = (sourceId: string) => filterEvents(events, { ...DEFAULT_FILTERS, sourceId });

    expect(only("telangana-today")).toEqual([real]);
    expect(only("the-hindu")).toEqual([located]);
    // A connected source with no events yet simply shows nothing.
    expect(only("deccan-chronicle")).toEqual([]);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, sourceId: "the-hindu" })).toBe(true);
  });

  it("keeps the source of each event as metadata", () => {
    expect(real.source).toEqual({ id: "telangana-today", name: "Telangana Today", type: "RSS" });
    expect(located.source).toEqual({ id: "the-hindu", name: "The Hindu", type: "RSS" });
  });

  it("has no notion of demo data", () => {
    expect(real).not.toHaveProperty("isDemo");
    expect(DEFAULT_FILTERS).not.toHaveProperty("origin");
  });

  it("filters by status, type and severity, including events with unknown values", () => {
    expect(filterEvents(events, { ...DEFAULT_FILTERS, status: "VALIDATION_REQUIRED" })).toEqual([real]);
    expect(filterEvents(events, { ...DEFAULT_FILTERS, eventTypes: ["PLANNED_ROAD_CLOSURE"] })).toEqual([located]);
    // The real event has no severity, so it never matches a severity filter.
    expect(filterEvents(events, { ...DEFAULT_FILTERS, severity: "HIGH" })).toEqual([located]);
    // The source's own severity words never match the filter: REI severity only.
    const ratedBySource = {
      ...real,
      severity: null,
      detection: { ...real.detection!, sourceSeverity: "Serious" },
    };
    expect(filterEvents([ratedBySource], { ...DEFAULT_FILTERS, severity: "HIGH" })).toEqual([]);
  });
});

describe("search", () => {
  const search = (text: string, serverMatches: ReadonlySet<string> | null = null) =>
    filterEvents(events, { ...DEFAULT_FILTERS, search: text }, serverMatches);

  it("matches title, road, description, location and source", () => {
    expect(search("DIVERSIONS")).toEqual([real]); // title
    expect(search("necklace")).toEqual([located]); // road
    expect(search("gachibowli")).toEqual([real]); // description
    expect(search("hyderabad")).toEqual(events); // location
    expect(search("the hindu")).toEqual([located]); // source
    expect(search("lakeview hyderabad")).toEqual([real]); // every word must match
    expect(search("lakeview necklace")).toEqual([]);
  });

  it("tolerates events without a road or description", () => {
    const bare = { ...real, affectedRoad: null, description: null };
    expect(matchesLocally(bare, "lakeview")).toBe(true);
    expect(matchesLocally(bare, "gachibowli")).toBe(false);
  });

  it("also shows events the API found in the article text", () => {
    // "radisson" appears nowhere in what the browser holds…
    expect(search("radisson")).toEqual([]);
    // …but the API, which searches the stored article, says this event matches.
    expect(search("radisson", new Set([located.id]))).toEqual([located]);
    // A server result never hides what matched locally.
    expect(search("necklace", new Set())).toEqual([located]);
  });

  it("combines search with the other filters", () => {
    const filters = { ...DEFAULT_FILTERS, search: "hyderabad", sourceId: "the-hindu" };
    expect(filterEvents(events, filters, new Set([real.id]))).toEqual([located]);
  });
});

describe("type filter", () => {
  const works = { ...real, eventType: "ROAD_CONSTRUCTION" as const };
  const untyped = { ...real, id: "EVT-UNTYPED00001", eventType: null };
  const events = [located, works, untyped];

  it("shows every type when none is chosen", () => {
    expect(filterEvents(events, DEFAULT_FILTERS)).toEqual(events);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, eventTypes: [] })).toBe(false);
  });

  it("selects one or several types at once", () => {
    expect(filterEvents(events, { ...DEFAULT_FILTERS, eventTypes: ["ROAD_CONSTRUCTION"] })).toEqual([works]);
    expect(
      filterEvents(events, { ...DEFAULT_FILTERS, eventTypes: ["ROAD_CONSTRUCTION", "PLANNED_ROAD_CLOSURE"] }),
    ).toEqual([located, works]);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, eventTypes: ["ROAD_CONSTRUCTION"] })).toBe(true);
  });

  it("can pick out events that have no type yet", () => {
    expect(filterEvents(events, { ...DEFAULT_FILTERS, eventTypes: [UNCLASSIFIED] })).toEqual([untyped]);
    expect(
      filterEvents(events, { ...DEFAULT_FILTERS, eventTypes: [UNCLASSIFIED, "ROAD_CONSTRUCTION"] }),
    ).toEqual([works, untyped]);
  });
});

describe("isCurrent", () => {
  // `real` was reported on 1 Oct and states no times; `located` runs on 4 Oct, 04:30–10:00 IST.
  const at = (iso: string) => new Date(iso);

  it("keeps upcoming and ongoing events and drops completed ones", () => {
    expect(isCurrent(located, at("2026-10-03T12:00:00+05:30"))).toBe(true); // upcoming
    expect(isCurrent(located, at("2026-10-04T08:00:00+05:30"))).toBe(true); // ongoing
    expect(isCurrent(located, at("2026-10-04T10:01:00+05:30"))).toBe(false); // completed
  });

  it("keeps an event with no stated end until further notice", () => {
    expect(isCurrent({ ...located, endTime: null }, at("2026-12-01T00:00:00+05:30"))).toBe(true);
  });

  it("names where now falls in a stated period", () => {
    expect(getTimeState(located, at("2026-10-03T12:00:00+05:30"))).toBe("upcoming");
    expect(getTimeState(located, at("2026-10-04T08:00:00+05:30"))).toBe("ongoing");
    expect(getTimeState(located, at("2026-10-04T10:01:00+05:30"))).toBe("ended");
    expect(getTimeState(real, at("2026-10-04T08:00:00+05:30"))).toBeNull();
  });

  it("drops events that have ended, been cancelled or been rejected", () => {
    const now = at("2026-10-03T12:00:00+05:30");
    expect(isCurrent({ ...located, status: "EXPIRED" }, now)).toBe(false);
    expect(isCurrent({ ...located, status: "CANCELLED" }, now)).toBe(false);
    expect(isCurrent({ ...real, status: "REJECTED" }, now)).toBe(false);
  });

  it("keeps a report of road works for longer, as works run for months", () => {
    const works = { ...real, eventType: "ROAD_CONSTRUCTION" as const };
    expect(isCurrent(works, at("2026-10-20T00:00:00Z"))).toBe(true);
    expect(isCurrent(works, at("2026-11-01T00:00:00Z"))).toBe(false);
  });

  it("keeps an official record with no stated end whatever its age: no expiry is invented", () => {
    const official = { ...real, detection: { ...real.detection!, method: "source_provided" } };
    expect(isCurrent(official, at("2027-01-01T00:00:00Z"))).toBe(true);
    expect(isCurrent({ ...official, status: "REJECTED" }, at("2027-01-01T00:00:00Z"))).toBe(false);
    const ended = { ...official, detection: { ...official.detection, sourceReportsEnded: true } };
    expect(isCurrent(ended, at("2027-01-01T00:00:00Z"))).toBe(false);
  });

  it("brings history back only when asked", () => {
    const now = at("2026-11-01T00:00:00Z");
    expect(keepCurrent([real], now)).toEqual([]);
    expect(keepCurrent([real], now, true)).toEqual([real]);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, showHistory: true })).toBe(true);
  });

  it("keeps an event without stated times only while its report is recent", () => {
    expect(isCurrent(real, at("2026-10-08T06:30:00Z"))).toBe(true);
    expect(isCurrent(real, at("2026-10-08T06:31:00Z"))).toBe(false);
  });
});

describe("date range filter", () => {
  const between = (from: string, to: string) =>
    filterEvents(events, { ...DEFAULT_FILTERS, from, to });

  it("counts as an active filter", () => {
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, from: "2026-10-01T00:00" })).toBe(true);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, to: "2026-10-01T00:00" })).toBe(true);
  });

  it("matches an event with stated times when its period overlaps the range", () => {
    expect(between("2026-10-04T09:00", "2026-10-04T12:00")).toEqual([located]);
    expect(between("2026-10-04T10:01", "")).toEqual([]);
    expect(between("2026-10-02T00:00", "2026-10-04T04:29")).toEqual([]);
    // "To" includes its whole minute, read as India Standard Time.
    expect(between("2026-10-02T00:00", "2026-10-04T04:30")).toEqual([located]);
  });

  it("matches an event without stated times by when it was reported", () => {
    // Reported 1 Oct, 06:30 UTC = 12:00 IST.
    expect(between("2026-10-01T12:00", "2026-10-01T12:00")).toEqual([real]);
    expect(between("2026-10-01T12:01", "2026-10-03T00:00")).toEqual([]);
    expect(between("", "2026-10-01T11:59")).toEqual([]);
  });

  it("narrows the current events and never brings a completed one back", () => {
    // On 4 Oct at 12:00 the marathon closure (04:30–10:00) is over; the report of 1 Oct is recent.
    const current = keepCurrent(events, new Date("2026-10-04T12:00:00+05:30"));
    expect(current).toEqual([real]);
    const all = { ...DEFAULT_FILTERS, from: "2026-10-01T00:00", to: "2026-10-31T23:59" };
    expect(filterEvents(current, all)).toEqual([real]);
    expect(filterEvents(current, { ...all, from: "2026-10-04T00:00" })).toEqual([]);
  });
});

describe("keepCurrent", () => {
  const now = new Date("2026-10-03T12:00:00+05:30");

  it("keeps upcoming, ongoing and recently reported events", () => {
    expect(keepCurrent(events, now)).toEqual(events);
  });

  it("leaves out completed, rejected, cancelled and old events", () => {
    const ended = { ...located, id: "ended", endTime: "2026-10-01T10:00:00+05:30" };
    const rejected = { ...real, id: "rejected", status: "REJECTED" as const };
    const cancelled = { ...located, id: "cancelled", status: "CANCELLED" as const };
    expect(keepCurrent([ended, rejected, cancelled, real], now)).toEqual([real]);
    // A month on, the undated report is old too, and nothing is left.
    expect(keepCurrent([ended, rejected, real], new Date("2026-11-03T12:00:00+05:30"))).toEqual([]);
  });
});

describe("computeEventStats", () => {
  it("counts events awaiting review separately", () => {
    expect(computeEventStats(events)).toEqual({
      total: 2,
      active: 0,
      scheduled: 1,
      roadClosures: 1,
      needsReview: 1,
    });
  });

  it("is all zeros when there are no events", () => {
    expect(computeEventStats([])).toEqual({
      total: 0,
      active: 0,
      scheduled: 0,
      roadClosures: 0,
      needsReview: 0,
    });
  });
});

describe("toEventMapData", () => {
  it("draws only events that have geometry — none is invented for the rest", () => {
    const data = toEventMapData(events, located.id);
    expect(data.geometries.features.map((feature) => feature.properties.eventId)).toEqual([located.id]);
    expect(data.anchors.features).toHaveLength(1);
    expect(data.geometries.features[0].properties.selected).toBe(true);
  });

  it("is empty when no event has been located", () => {
    const data = toEventMapData([real], real.id);
    expect(data.geometries.features).toEqual([]);
    expect(data.anchors.features).toEqual([]);
  });
});

describe("presentation of missing values", () => {
  it("labels unknown values honestly", () => {
    expect(getEventTypeLabel(null)).toBe("Unclassified");
    expect(formatConfidence(null)).toBeNull();
    expect(formatConfidence(0.954)).toBe("95%");
    expect(formatEventPeriod(null, null)).toEqual({ start: "Not specified", end: "Not specified" });
  });

  it("names the site an article is on, so a search result shows its publisher", () => {
    expect(getSiteName("https://www.thehindu.com/news/cities/Hyderabad/x.ece")).toBe("thehindu.com");
    expect(getSiteName("not a link")).toBeNull();
    expect(getSiteName(null)).toBeNull();
  });

  it("recognises a period given in whole days, which has no times of day to show", () => {
    // 26 September to 24 November 2026, whole days in India Standard Time.
    const start = "2026-09-25T18:30:00Z";
    const end = "2026-11-24T18:29:59Z";
    expect(isWholeDayPeriod(start, end)).toBe(true);
    expect(isWholeDayPeriod(start, null)).toBe(true);
    expect(isWholeDayPeriod(null, end)).toBe(true);
    expect(isWholeDayPeriod("2026-10-04T04:30:00+05:30", "2026-10-04T10:00:00+05:30")).toBe(false);
    expect(isWholeDayPeriod(null, null)).toBe(false);
    expect(formatEventPeriod(start, end, true)).toEqual({
      start: "Sat, 26 Sept 2026",
      end: "Tue, 24 Nov 2026",
    });
    // With a time of day, the year is shown as well.
    expect(formatEventPeriod("2027-05-06T04:30:00+05:30", null).start).toBe(
      "Thu, 6 May 2027, 04:30",
    );
  });

  it("gives a date input the day in India Standard Time", () => {
    expect(toDateInputValue("2026-09-28T18:29:59Z")).toBe("2026-09-28");
    expect(toDateInputValue("2026-09-28T18:30:00Z")).toBe("2026-09-29");
    expect(toDateInputValue(null)).toBeNull();
  });

  it("shows an open-ended event as running until further notice", () => {
    const period = formatEventPeriod("2026-10-04T04:30:00+05:30", null);
    expect(period.start).toContain("04:30");
    expect(period.end).toBe("Until further notice");
  });
});
