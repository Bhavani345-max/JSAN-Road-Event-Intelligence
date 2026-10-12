import { afterEach, describe, expect, it, vi } from "vitest";
import { toManualEventBody } from "@/features/qc/api";
import { isManualEntry } from "../model";
import { locatedApiEvent, realApiEvent } from "../testing/fixtures";
import { apiEventRepository, mapApiEvent, searchEventIds } from "./eventRepository";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response | Error) {
  const fetchMock = vi.fn(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("mapApiEvent", () => {
  it("keeps unknown fields of a real-source event empty", () => {
    const event = mapApiEvent(realApiEvent)!;

    expect(event.id).toBe("EVT-0123456789AB");
    expect(event.status).toBe("VALIDATION_REQUIRED");
    expect(event.source).toEqual({ id: "telangana-today", name: "Telangana Today", type: "RSS" });
    expect(event.sourceReference).toBe("https://news.example.com/traffic-diversions");
    expect(event.evidence?.publishedAt).toBe("2026-10-01T06:30:00Z");
    expect(event.detection?.matchedKeywords).toEqual(["traffic diversion", "motorists"]);

    // Nothing is filled in for what the source did not state.
    expect(event.geometry).toBeNull();
    expect(event.latitude).toBeNull();
    expect(event.longitude).toBeNull();
    expect(event.startTime).toBeNull();
    expect(event.endTime).toBeNull();
    expect(event.severity).toBeNull();
    expect(event.direction).toBeNull();
    expect(event.confidence).toBeNull();
  });

  it("maps a located event and derives its map marker from the geometry", () => {
    const event = mapApiEvent(locatedApiEvent)!;

    expect(event.eventType).toBe("PLANNED_ROAD_CLOSURE");
    expect(event.severity).toBe("HIGH");
    expect(event.geometry?.type).toBe("LineString");
    expect(event.longitude).toBeCloseTo(78.46);
    expect(event.latitude).toBeCloseTo(17.42);
    // Confidence stays empty until something actually assesses it.
    expect(event.confidence).toBeNull();
  });

  it("treats values it does not know as unknown instead of guessing", () => {
    const event = mapApiEvent({
      ...realApiEvent,
      event_type: "METEOR_STRIKE",
      severity: "APOCALYPTIC",
      geometry: { type: "MultiPolygon", coordinates: [] },
    })!;
    expect(event.eventType).toBeNull();
    expect(event.severity).toBeNull();
    expect(event.geometry).toBeNull();
  });

  it("skips an event with a lifecycle status it does not know", () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(mapApiEvent({ ...realApiEvent, status: "TELEPORTED" })).toBeNull();
  });
});

describe("searchEventIds", () => {
  it("asks the API to search and returns the ids it found", async () => {
    const fetchMock = stubFetch(json({ items: [locatedApiEvent], total: 1 }));

    const ids = await searchEventIds("  DLF Gate ");

    expect(fetchMock).toHaveBeenCalledWith("/api/events?limit=500&q=DLF%20Gate", expect.anything());
    expect([...ids]).toEqual(["EVT-LOCATED00001"]);
  });
});

describe("apiEventRepository.listEvents", () => {
  it("loads events from the API in the order the API returns them", async () => {
    const fetchMock = stubFetch(json({ items: [realApiEvent, locatedApiEvent], total: 2 }));

    const events = await apiEventRepository.listEvents();

    expect(fetchMock).toHaveBeenCalledWith("/api/events?limit=500", expect.anything());
    expect(events.map((event) => event.id)).toEqual(["EVT-0123456789AB", "EVT-LOCATED00001"]);
  });

  it("returns an empty list when there are no events", async () => {
    stubFetch(json({ items: [], total: 0 }));
    expect(await apiEventRepository.listEvents()).toEqual([]);
  });

  it("explains how to start the API when it cannot be reached", async () => {
    stubFetch(new TypeError("Failed to fetch"));
    await expect(apiEventRepository.listEvents()).rejects.toThrow(/REI API is not reachable/);
  });

  it("treats a proxy error (API server down) as unreachable", async () => {
    stubFetch(new Response("Internal Server Error", { status: 500 }));
    await expect(apiEventRepository.listEvents()).rejects.toThrow(/REI API is not reachable/);
  });

  it("surfaces the API's own error message", async () => {
    stubFetch(json({ detail: "Event not found" }, 404));
    await expect(apiEventRepository.listEvents()).rejects.toThrow("Event not found");
  });
});

describe("reviewer changes", () => {
  it("maps a manual entry with the basis the reviewer gave", () => {
    const event = mapApiEvent({
      ...realApiEvent,
      source_id: "manual-entry",
      source: { source_id: "manual-entry", source_name: "Manual entry", source_type: "MANUAL" },
      detection: {
        method: "manual_entry",
        score: 0,
        matched_keywords: [],
        road_mentions: [],
        basis: "Seen on site on 5 October",
      },
    })!;
    expect(isManualEntry(event)).toBe(true);
    expect(event.detection?.basis).toBe("Seen on site on 5 October");
    expect(event.source.name).toBe("Manual entry");
    expect(isManualEntry(mapApiEvent(realApiEvent)!)).toBe(false);
  });

  it("maps an extension, keeping the end the event had before", () => {
    const event = mapApiEvent({
      ...realApiEvent,
      end_time: "2026-12-31T18:29:59Z",
      detection: {
        ...realApiEvent.detection!,
        stated_period: "for 90 days from July 1",
        period_revision: {
          previous_end: "2026-09-28T18:29:59Z",
          reason: "Still closed, seen on site",
          revised_by: "local-reviewer",
          revised_at: "2026-10-05T09:00:00Z",
        },
      },
    })!;
    expect(event.detection?.periodRevision).toEqual({
      previousEnd: "2026-09-28T18:29:59Z",
      reason: "Still closed, seen on site",
      revisedAt: "2026-10-05T09:00:00Z",
    });
    expect(event.detection?.statedPeriod).toBe("for 90 days from July 1");
    expect(mapApiEvent(realApiEvent)!.detection?.periodRevision).toBeNull();
  });

  it("maps a spot a reviewer put on the map, keeping the name it was located by before", () => {
    const event = mapApiEvent({
      ...realApiEvent,
      geometry: { type: "Point", coordinates: [78.3519, 17.4455] },
      detection: {
        ...realApiEvent.detection!,
        location: {
          method: "reviewer_placed",
          place_name: "IIIT Junction",
          place_kind: "spot",
          precision: "place",
          mention: "IIIT Junction",
          found_in: "review",
          reference: "placed on the map by local-reviewer",
        },
        location_revision: {
          previous_place_name: "Gachibowli",
          reason: "Works are at the junction, seen on site",
          revised_by: "local-reviewer",
          revised_at: "2026-10-05T12:00:00Z",
        },
      },
    })!;
    expect(event.detection?.location?.method).toBe("reviewer_placed");
    expect(event.detection?.location?.placeName).toBe("IIIT Junction");
    expect(event.detection?.locationRevision).toEqual({
      previousPlaceName: "Gachibowli",
      reason: "Works are at the junction, seen on site",
      revisedAt: "2026-10-05T12:00:00Z",
    });
    // The marker is drawn at the reviewer's point.
    expect([event.longitude, event.latitude]).toEqual([78.3519, 17.4455]);
    expect(mapApiEvent(realApiEvent)!.detection?.locationRevision).toBeNull();
  });

  it("sends a manual entry to the API in its wire format, leaving unknowns empty", () => {
    expect(
      toManualEventBody({
        title: "DLF Road closed",
        eventType: null,
        place: "DLF road",
        startDate: "2026-07-01",
        endDate: null,
        description: null,
        referenceUrl: null,
        basis: "Seen on site",
      }),
    ).toEqual({
      title: "DLF Road closed",
      event_type: null,
      place: "DLF road",
      start_date: "2026-07-01",
      end_date: null,
      description: null,
      reference_url: null,
      basis: "Seen on site",
    });
  });
});
