import { afterEach, describe, expect, it } from "vitest";
import { toEventMapData } from "@/features/map/geojson";
import type { ApiEvent } from "@/types/api";
import { mapApiEvent } from "./api/eventRepository";
import { inCity, isCurrent } from "./filters";
import {
  DEFAULT_TIME_ZONE,
  describeSourceAuthority,
  formatDateTime,
  isWholeDayPeriod,
  setCityTimeZones,
  setDisplayTimeZone,
  timeZoneOf,
  timeZoneLabel,
  toDateInputValue,
  zonedInputToTime,
} from "./presentation";
import { realApiEvent } from "./testing/fixtures";

afterEach(() => setDisplayTimeZone(DEFAULT_TIME_ZONE));

/** Shaped like a Transport for London disruption after ingestion (test data). */
const officialApiEvent: ApiEvent = {
  ...realApiEvent,
  event_id: "EVT-OFFICIAL0001",
  source_id: "tfl-road-disruptions",
  city: "London",
  title: "Vehicle collision: [A13] NEWHAM WAY",
  event_type: "ACCIDENT",
  start_time: "2026-10-06T07:56:15Z",
  end_time: "2026-10-06T23:59:59Z",
  direction: "WESTBOUND",
  geometry: {
    type: "MultiPolygon",
    coordinates: [
      [
        [
          [0.0, 51.5],
          [0.01, 51.5],
          [0.01, 51.51],
          [0.0, 51.5],
        ],
      ],
    ],
  },
  source: {
    source_id: "tfl-road-disruptions",
    source_name: "Transport for London road disruptions",
    source_type: "API",
    source_class: "AUTHORITATIVE_OFFICIAL",
    source_tier: 1,
    discovery_only: false,
  },
  detection: {
    method: "source_provided",
    score: null,
    matched_keywords: [],
    road_mentions: [],
    location_class: "SOURCE_PROVIDED",
    affected_locations: [
      {
        name: "[A13] NEWHAM WAY",
        kind: "street",
        resolution: "SOURCE_PROVIDED",
        geometry: {
          type: "MultiLineString",
          coordinates: [
            [
              [0.0116, 51.516],
              [0.0115, 51.5159],
            ],
          ],
        },
        direction: "Westbound",
        closure: "Open",
        mention: "[A13] NEWHAM WAY",
        found_in: "source",
        reference: "TfL street segments",
      },
    ],
    source_category: "Collisions / Vehicle collision",
    source_severity: "Serious",
    attribution: "Powered by TfL Open Data.",
  },
};

const approximateApiEvent: ApiEvent = {
  ...realApiEvent,
  event_id: "EVT-APPROX00001",
  geometry: { type: "Point", coordinates: [78.38, 17.42] },
  detection: {
    ...realApiEvent.detection!,
    location: {
      method: "named_place",
      place_name: "Khajaguda Jn",
      place_kind: "junction",
      precision: "place",
      mention: "Khajaguda junction",
      found_in: "title",
      reference: "OpenStreetMap node/1",
    },
    location_class: "APPROXIMATE",
    affected_locations: [
      {
        name: "Khajaguda Jn",
        kind: "junction",
        resolution: "APPROXIMATE",
        geometry: { type: "Point", coordinates: [78.38, 17.42] },
        direction: null,
        closure: null,
        mention: "Khajaguda junction",
        found_in: "title",
        reference: "OpenStreetMap node/1",
      },
      {
        name: "Lakeview Colony",
        kind: null,
        resolution: "UNRESOLVED",
        geometry: null,
        direction: null,
        closure: null,
        mention: "Lakeview Colony",
        found_in: "summary",
        reference: null,
      },
    ],
  },
};

describe("an official source's event", () => {
  const event = mapApiEvent(officialApiEvent)!;

  it("keeps the source's authority apart from the source itself", () => {
    expect(event.source).toEqual({
      id: "tfl-road-disruptions",
      name: "Transport for London road disruptions",
      type: "API",
    });
    expect(event.sourceAuthority).toEqual({
      sourceClass: "AUTHORITATIVE_OFFICIAL",
      tier: 1,
      discoveryOnly: false,
    });
    expect(describeSourceAuthority(event.sourceAuthority)).toEqual({
      kind: "Official source",
      standing: "Tier 1 · authoritative",
      official: true,
    });
  });

  it("keeps the source's multi-part area and places its marker inside it", () => {
    expect(event.geometry?.type).toBe("MultiPolygon");
    expect(event.longitude).toBeGreaterThan(0);
    expect(event.longitude).toBeLessThan(0.011);
    expect(event.detection?.locationClass).toBe("SOURCE_PROVIDED");
    expect(event.detection?.sourceSeverity).toBe("Serious");
    expect(event.detection?.attribution).toBe("Powered by TfL Open Data.");
    // REI's own severity is not derived from the source's words.
    expect(event.severity).toBeNull();
  });

  it("draws the area and the street segments, as solid (not approximate) features", () => {
    const data = toEventMapData([event], null);
    expect(data.geometries.features.map((feature) => feature.geometry.type)).toEqual([
      "MultiPolygon",
      "MultiLineString",
    ]);
    expect(data.anchors.features[0].properties.approximate).toBe(false);
  });
});

describe("an approximate location", () => {
  const event = mapApiEvent(approximateApiEvent)!;

  it("is marked approximate, so the map draws it hollow", () => {
    expect(event.detection?.locationClass).toBe("APPROXIMATE");
    expect(toEventMapData([event], null).anchors.features[0].properties.approximate).toBe(true);
  });

  it("lists every place named, keeping the unplaced one as a name", () => {
    expect(
      event.detection?.affectedLocations.map((place) => [place.name, place.resolution]),
    ).toEqual([
      ["Khajaguda Jn", "APPROXIMATE"],
      ["Lakeview Colony", "UNRESOLVED"],
    ]);
    // A named place's point is never drawn as a separate shape.
    expect(toEventMapData([event], null).geometries.features).toHaveLength(1);
  });

  it("is mapped to null location data for events from before the location classes", () => {
    const old = mapApiEvent(realApiEvent)!;
    expect(old.detection?.locationClass).toBeNull();
    expect(old.detection?.affectedLocations).toEqual([]);
  });
});

describe("source authority wording", () => {
  it("never presents news or search as authoritative", () => {
    expect(
      describeSourceAuthority({ sourceClass: "PUBLISHER", tier: 4, discoveryOnly: true }),
    ).toEqual({ kind: "Publisher", standing: "Tier 4 · secondary, not confirmation", official: false });
    expect(
      describeSourceAuthority({ sourceClass: "DISCOVERY", tier: 4, discoveryOnly: true }),
    ).toEqual({ kind: "Discovery", standing: "Tier 4 · a lead only", official: false });
    expect(describeSourceAuthority({ sourceClass: null, tier: null, discoveryOnly: false }).kind).toBe(
      "Manual entry",
    );
  });
});

describe("cities", () => {
  it("shows an event in its own city, and one with no city in the default city", () => {
    const london = mapApiEvent(officialApiEvent)!;
    const noCity = mapApiEvent({ ...realApiEvent, city: null })!;
    expect(inCity(london, "London", false)).toBe(true);
    expect(inCity(london, "Hyderabad", true)).toBe(false);
    expect(inCity(noCity, "Hyderabad", true)).toBe(true);
    expect(inCity(noCity, "London", false)).toBe(false);
  });

  it("shows times in India Standard Time by default", () => {
    expect(timeZoneLabel()).toBe("IST");
    expect(formatDateTime("2026-10-06T07:56:15Z")).toBe("Tue, 6 Oct 2026, 13:26");
  });

  it("shows times in the selected city's zone, summer time included", () => {
    setDisplayTimeZone("Europe/London");
    expect(formatDateTime("2026-10-06T07:56:15Z")).toBe("Tue, 6 Oct 2026, 08:56");
    expect(timeZoneLabel(new Date("2026-10-06T12:00:00Z"))).toBe("BST");
    // A whole day in London time (British Summer Time, UTC+1).
    expect(isWholeDayPeriod("2026-10-09T23:00:00Z", "2026-10-11T22:59:59Z")).toBe(true);
    expect(isWholeDayPeriod("2026-10-09T18:30:00Z", "2026-10-11T18:29:59Z")).toBe(false);
    expect(toDateInputValue("2026-10-09T23:00:00Z")).toBe("2026-10-10");
    // A date-time typed in the filter is read as London time.
    expect(zonedInputToTime("2026-10-10T00:00")).toBe(Date.parse("2026-10-09T23:00:00Z"));
    // In winter, London is on UTC.
    expect(zonedInputToTime("2026-12-10T00:00")).toBe(Date.parse("2026-12-10T00:00:00Z"));
  });

  it("reads filter input as India Standard Time by default, as before", () => {
    expect(zonedInputToTime("2026-10-05T18:30")).toBe(Date.parse("2026-10-05T13:00:00Z"));
    expect(zonedInputToTime("")).toBeNull();
  });
});

describe("source revisions", () => {
  it("maps an applied revision and a pending one", () => {
    const event = mapApiEvent({
      ...officialApiEvent,
      detection: {
        ...officialApiEvent.detection!,
        source_revision: {
          revision: 2,
          revised_at: "2026-10-07T08:00:00Z",
          changes: ["end 2026-11-07 18:00 UTC → 2026-11-20 18:00 UTC"],
        },
        pending_source_revision: null,
      },
    })!;
    expect(event.detection?.sourceRevision).toEqual({
      revision: 2,
      revisedAt: "2026-10-07T08:00:00Z",
      changes: ["end 2026-11-07 18:00 UTC → 2026-11-20 18:00 UTC"],
    });
    expect(event.detection?.pendingSourceRevision).toBeNull();
    // Events from before revisions existed have neither.
    expect(mapApiEvent(realApiEvent)!.detection?.sourceRevision).toBeNull();
  });
});

describe("merged events", () => {
  const canonical = mapApiEvent({
    ...realApiEvent,
    other_evidence: [
      {
        event_id: "EVT-B",
        source: { source_id: "newsmeter", source_name: "NewsMeter", source_type: "RSS", source_class: "PUBLISHER" },
        artifact_id: "a2",
        url: "https://newsmeter.in/kbr",
        title: "Why has one-way traffic around KBR Park been made permanent",
        published_at: "2026-10-06T05:00:00Z",
        retrieved_at: "2026-10-06T05:10:00Z",
        how: "automatic",
      },
    ],
    merge_candidates: [
      {
        candidate_id: 7,
        classification: "POSSIBLE",
        status: "PENDING",
        reasons: ["both name kbr park"],
        conflicts: [{ field: "end_time", a: "x", b: "y" }],
        other_event_id: "EVT-C",
        other_title: "GHMC revises KBR Park flyover plans",
        other_source: { source_id: "the-hans-india", source_name: "The Hans India", source_type: "RSS" },
      },
    ],
    detection: {
      ...realApiEvent.detection!,
      provenance: { start_time: { event_id: "EVT-B", source_id: "newsmeter" } },
      merge_conflicts: [
        { field: "end_time", values: [{ event_id: "EVT-A", source_id: "telangana-today", value: "2026-11-24T18:29:59Z" }] },
      ],
      merge_review_required: true,
    },
  })!;

  it("keeps every other source's evidence, attributed", () => {
    expect(canonical.otherEvidence).toEqual([
      {
        eventId: "EVT-B",
        sourceName: "NewsMeter",
        sourceClass: "PUBLISHER",
        url: "https://newsmeter.in/kbr",
        title: "Why has one-way traffic around KBR Park been made permanent",
        publishedAt: "2026-10-06T05:00:00Z",
        how: "automatic",
      },
    ]);
    expect(canonical.detection?.provenance.start_time).toEqual({ eventId: "EVT-B", sourceId: "newsmeter" });
    expect(canonical.detection?.mergeReviewRequired).toBe(true);
    expect(canonical.detection?.mergeConflicts[0].field).toBe("end_time");
  });

  it("carries pending candidates for a reviewer", () => {
    expect(canonical.mergeCandidates).toEqual([
      {
        candidateId: 7,
        classification: "POSSIBLE",
        reasons: ["both name kbr park"],
        conflicts: [{ field: "end_time" }],
        otherEventId: "EVT-C",
        otherTitle: "GHMC revises KBR Park flyover plans",
        otherSourceName: "The Hans India",
      },
    ]);
  });

  it("has none of this for an event reported once", () => {
    const single = mapApiEvent(realApiEvent)!;
    expect(single.otherEvidence).toEqual([]);
    expect(single.mergeCandidates).toEqual([]);
  });
});

describe("an event the source reports ended", () => {
  it("is no longer current, whatever its stated end", () => {
    const now = new Date("2026-10-06T12:00:00Z");
    const live = mapApiEvent({ ...realApiEvent, start_time: "2026-10-01T00:00:00Z", end_time: "2026-12-01T00:00:00Z" })!;
    const cleared = mapApiEvent({
      ...realApiEvent,
      start_time: "2026-10-01T00:00:00Z",
      end_time: "2026-12-01T00:00:00Z",
      detection: { ...realApiEvent.detection!, source_reports_ended: true },
    })!;
    expect(isCurrent(live, now)).toBe(true);
    expect(isCurrent(cleared, now)).toBe(false);
  });
});

describe("all cities on one page", () => {
  it("shows each event's times in its own city's zone", () => {
    setCityTimeZones([
      { id: "hyderabad", name: "Hyderabad", timeZone: "Asia/Kolkata" },
      { id: "london", name: "London", timeZone: "Europe/London" },
      { id: "toronto", name: "Toronto", timeZone: "America/Toronto" },
    ]);
    const at = "2026-10-06T07:56:15Z";
    expect(formatDateTime(at, timeZoneOf("Hyderabad"))).toBe("Tue, 6 Oct 2026, 13:26");
    expect(formatDateTime(at, timeZoneOf("London"))).toBe("Tue, 6 Oct 2026, 08:56");
    expect(formatDateTime(at, timeZoneOf("toronto"))).toBe("Tue, 6 Oct 2026, 03:56");
    // No city: the display zone (India Standard Time by default).
    expect(timeZoneOf(null)).toBe(DEFAULT_TIME_ZONE);
    expect(timeZoneLabel(new Date(at), timeZoneOf("London"))).toBe("BST");
  });
});
