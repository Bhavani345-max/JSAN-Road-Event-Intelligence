import { describe, expect, it } from "vitest";
import type { ApiCityCoverage, ApiSource } from "@/types/api";
import {
  coverageTotals,
  groupSources,
  notOnThisMap,
  shownOnMap,
  sourceCounts,
  sourcesForCity,
  toRegistrySource,
} from "./sources";

function apiSource(overrides: Partial<ApiSource>): ApiSource {
  return {
    source_id: "telangana-today",
    source_name: "Telangana Today",
    source_type: "RSS",
    organization: null,
    authority_type: null,
    source_tier: 4,
    source_url: null,
    endpoint: null,
    access_method: null,
    integration_status: "CONNECTED",
    source_class: "PUBLISHER",
    country: "IN",
    region: null,
    city: "hyderabad",
    cost_category: null,
    rate_limit: null,
    terms_status: "NOT_REVIEWED",
    licence: null,
    attribution: null,
    commercial_use: "UNKNOWN",
    provides_geometry: false,
    provides_segments: false,
    provides_direction: false,
    real_time: false,
    discovery_only: true,
    active: true,
    polling_frequency_minutes: 30,
    language: "en",
    events_supported: [],
    parser_type: "rss",
    terms_reviewed: false,
    evidence_retention: null,
    notes: null,
    last_poll_at: "2026-10-16T12:00:00Z",
    last_success_at: "2026-10-16T12:00:00Z",
    last_failure_at: null,
    last_error: null,
    artifact_count: 10,
    event_count: 3,
    status: "COLLECTING",
    status_label: "Active: collecting",
    status_reason: "3 road events detected in the last 7 days.",
    polled: true,
    recent_event_count: 3,
    pending_review_count: 2,
    validated_count: 1,
    on_map_review_count: 2,
    on_map_operations_count: 0,
    ...overrides,
  };
}

describe("sources in the console", () => {
  it("shows the state the API derived, never one of its own", () => {
    const gdelt = toRegistrySource(
      apiSource({
        source_id: "gdelt-delhi",
        integration_status: "DISABLED",
        active: false,
        status: "DISABLED",
        status_label: "Off: disabled by configuration",
        polled: false,
        last_success_at: "2026-10-16T10:58:00Z",
      }),
    );
    expect(gdelt.status).toBe("DISABLED");
    expect(gdelt.statusLabel).toBe("Off: disabled by configuration");
    // A disabled source is never run from the console, whatever it recorded before.
    expect(gdelt.checkable).toBe(false);
    expect(gdelt.polled).toBe(false);
  });

  it("lets connected sources be checked, even when not scheduled here", () => {
    const official = toRegistrySource(
      apiSource({ source_id: "tfl", active: false, status: "NOT_SCHEDULED", polled: false }),
    );
    expect(official.checkable).toBe(true);
    const pending = toRegistrySource(
      apiSource({ integration_status: "TERMS_REVIEW_REQUIRED", active: false, status: "AWAITING_PERMISSION" }),
    );
    expect(pending.checkable).toBe(false);
  });

  it("groups every source: polled first, failing at the top; nothing is left out", () => {
    const sources = [
      apiSource({ source_id: "a", source_name: "A", status: "COLLECTING" }),
      apiSource({ source_id: "b", source_name: "B", status: "FAILING" }),
      apiSource({ source_id: "c", source_name: "C", status: "DISABLED", integration_status: "DISABLED" }),
      apiSource({ source_id: "d", source_name: "D", status: "AWAITING_PERMISSION" }),
      apiSource({ source_id: "e", source_name: "E", status: "REMOVED" }),
    ].map(toRegistrySource);
    const groups = groupSources(sources);
    expect(groups.map((group) => group.key)).toEqual(["polled", "off", "unavailable"]);
    expect(groups[0].sources.map((source) => source.id)).toEqual(["b", "a"]);
    expect(groups.flatMap((group) => group.sources)).toHaveLength(sources.length);
  });
});

describe("coverage from detection to the map, per view", () => {
  const row = (cityId: string, values: Partial<ApiCityCoverage>): ApiCityCoverage => ({
    city_id: cityId,
    city_name: cityId,
    country: "IN",
    detected: 0,
    merged: 0,
    rejected: 0,
    closed: 0,
    pending_review: 0,
    validated: 0,
    recent: 0,
    on_map_review: 0,
    on_map_operations: 0,
    hidden_review: {},
    hidden_operations: {},
    ...values,
  });
  // As counted locally on 16 October 2026: 3,982 US work zones await review, none validated.
  const coverage = [
    row("hyderabad", {
      detected: 95, pending_review: 84, validated: 2, rejected: 9, on_map_review: 12, on_map_operations: 1,
      hidden_review: { no_start: 46, no_location: 14, ended: 12 }, hidden_operations: { ended: 1 },
    }),
    row("united-states", {
      country: "US", detected: 3982, pending_review: 3982, on_map_review: 3979, hidden_review: { ended: 3 },
    }),
    row("new-york", { country: "US", detected: 2351, pending_review: 2351, on_map_review: 2082, hidden_review: { ended: 269 } }),
  ];

  it("never counts events awaiting review on the operations map", () => {
    const us = coverageTotals(coverage, ["united-states"]);
    expect(shownOnMap("current_upcoming", { review: us.onMapReview, operations: us.onMapOperations })).toBe(0);
    expect(notOnThisMap(us, "current_upcoming")).toEqual([
      "3,982 awaiting review, not confirmed (the review queue's map shows 3,979)",
    ]);
  });

  it("counts the review queue's map separately, with why the others are hidden", () => {
    const us = coverageTotals(coverage, ["united-states"]);
    expect(shownOnMap("validation", { review: us.onMapReview, operations: us.onMapOperations })).toBe(3979);
    expect(notOnThisMap(us, "validation")).toEqual(["3 awaiting review (3 ended)"]);
  });

  it("tells validated events hidden from the operations map apart from those awaiting review", () => {
    const hyderabad = coverageTotals(coverage, ["hyderabad"]);
    expect(hyderabad).toMatchObject({ detected: 95, pendingReview: 84, validated: 2, rejected: 9, onMapOperations: 1 });
    expect(notOnThisMap(hyderabad, "current_upcoming")).toEqual([
      "84 awaiting review, not confirmed (the review queue's map shows 12)",
      "1 validated (1 ended)",
    ]);
    expect(notOnThisMap(hyderabad, "validation")).toEqual([
      "72 awaiting review (46 no stated start, 14 no location, 12 ended)",
      "2 validated (the operations map shows 1)",
    ]);
  });

  it("says how many events off the review map the queue lists below (decision 0038)", () => {
    // 46 without a stated start, of which 30 are recent reports or end-only: listed for review.
    const listed = coverageTotals(
      [row("hyderabad", { pending_review: 84, on_map_review: 12, listed_review: 42, hidden_review: { no_start: 46, no_location: 26 } })],
      ["hyderabad"],
    );
    expect(notOnThisMap(listed, "validation")).toEqual([
      "72 awaiting review (46 no stated start, 26 no location)",
      "30 of them listed below for review",
    ]);
    // An API from before decision 0038 lists only what the map shows: nothing more is claimed.
    expect(coverageTotals(coverage, ["united-states"]).listedReview).toBe(3979);
  });

  it("adds a country entry and its cities together, each row once", () => {
    const us = coverageTotals(coverage, ["united-states", "new-york"]);
    expect(us).toMatchObject({ detected: 6333, pendingReview: 6333, onMapReview: 6061 });
    expect(us.hiddenReview).toEqual({ ended: 272 });
    expect(coverageTotals(coverage, ["new-york"]).detected).toBe(2351);
  });

  it("adds every row once for all cities together", () => {
    const all = coverageTotals(coverage, null);
    expect(all).toMatchObject({ detected: 6428, pendingReview: 6417, validated: 2, onMapReview: 6073, onMapOperations: 1 });
    expect(all.hiddenOperations).toEqual({ ended: 1 });
  });

  it("says per source how many of its events this view's map shows", () => {
    const source = toRegistrySource(
      apiSource({ pending_review_count: 127, validated_count: 3, on_map_review_count: 109, on_map_operations_count: 0 }),
    );
    expect(sourceCounts(source, "current_upcoming")).toEqual(["127 awaiting review", "3 validated", "0 on this map"]);
    expect(sourceCounts(source, "validation")).toEqual(["127 awaiting review", "3 validated", "109 on this map"]);
  });
});

describe("which sources a choice lists", () => {
  const sources = [
    apiSource({ source_id: "gdelt-delhi", city: "delhi", country: "IN" }),
    apiSource({ source_id: "telangana-today", city: "hyderabad", country: "IN" }),
    apiSource({ source_id: "nhai", city: null, country: "IN" }),
    apiSource({ source_id: "autobahn", city: null, country: "DE" }),
    apiSource({ source_id: "manual-entry", city: null, country: null }),
    apiSource({ source_id: "drivebc-events", city: "canada", country: "CA" }),
    apiSource({ source_id: "toronto-road-restrictions", city: "toronto", country: "CA" }),
    apiSource({ source_id: "wzdx-deldot", city: "united-states", country: "US" }),
    apiSource({ source_id: "nyc-street-closures", city: "new-york", country: "US" }),
  ].map(toRegistrySource);
  const ids = (area: { ids: string[]; country: string } | null) =>
    sourcesForCity(sources, area).map((source) => source.id);

  it("lists the city's own, its country's and the general ones, not another country's catalogue", () => {
    expect(ids({ ids: ["delhi"], country: "IN" })).toEqual(["gdelt-delhi", "nhai", "manual-entry"]);
  });

  it("lists Canada's sources and Toronto's for Canada, Toronto's only for Toronto", () => {
    expect(ids({ ids: ["canada", "toronto"], country: "CA" })).toEqual([
      "manual-entry", "drivebc-events", "toronto-road-restrictions",
    ]);
    expect(ids({ ids: ["toronto"], country: "CA" })).toEqual(["manual-entry", "toronto-road-restrictions"]);
  });

  it("lists the United States' sources and New York City's for the United States", () => {
    expect(ids({ ids: ["united-states", "new-york"], country: "US" })).toEqual([
      "manual-entry", "wzdx-deldot", "nyc-street-closures",
    ]);
    expect(ids({ ids: ["new-york"], country: "US" })).toEqual(["manual-entry", "nyc-street-closures"]);
  });

  it("lists every source for all cities together", () => {
    expect(ids(null)).toHaveLength(sources.length);
  });
});
