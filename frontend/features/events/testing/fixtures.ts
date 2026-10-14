import type { ApiEvent } from "@/types/api";

/** A real-source event exactly as the API returns it right after ingestion. */
export const realApiEvent: ApiEvent = {
  event_id: "EVT-0123456789AB",
  source_id: "telangana-today",
  source_reference: "https://news.example.com/traffic-diversions",
  title: "Traffic diversions at Lakeview Junction",
  event_type: "TRAFFIC_DIVERSION",
  description: "Motorists heading to Gachibowli will be diverted at Lakeview Junction.",
  city: "Hyderabad",
  affected_road: "Lakeview Junction",
  start_time: null,
  end_time: null,
  status: "VALIDATION_REQUIRED",
  severity: null,
  direction: null,
  geometry: null,
  confidence: null,
  detection: {
    method: "keyword_rules",
    score: 4,
    matched_keywords: ["traffic diversion", "motorists"],
    road_mentions: ["Lakeview Junction"],
  },
  created_at: "2026-10-02T08:00:00Z",
  updated_at: "2026-10-02T08:00:00Z",
  source: { source_id: "telangana-today", source_name: "Telangana Today", source_type: "RSS" },
  evidence: {
    artifact_id: "a1",
    url: "https://news.example.com/traffic-diversions",
    title: "Traffic diversions at Lakeview Junction",
    published_at: "2026-10-01T06:30:00Z",
    retrieved_at: "2026-10-02T08:00:00Z",
    content_hash: "0".repeat(64),
  },
  version: 1,
};

/**
 * An event that has been located, as it will look once GIS resolution and
 * review exist. Test data: no such event is produced by the application yet.
 */
export const locatedApiEvent: ApiEvent = {
  ...realApiEvent,
  event_id: "EVT-LOCATED00001",
  source_id: "the-hindu",
  source: { source_id: "the-hindu", source_name: "The Hindu", source_type: "RSS" },
  title: "Necklace Road closed for city marathon",
  event_type: "PLANNED_ROAD_CLOSURE",
  description: "Test event.",
  affected_road: "Necklace Road",
  start_time: "2026-10-04T04:30:00+05:30",
  end_time: "2026-10-04T10:00:00+05:30",
  status: "SCHEDULED",
  severity: "HIGH",
  direction: "BOTH_DIRECTIONS",
  geometry: {
    type: "LineString",
    coordinates: [
      [78.46, 17.41],
      [78.46, 17.43],
    ],
  },
  detection: null,
  source_reference: "https://news.example.com/necklace-road-marathon",
  evidence: {
    artifact_id: "a2",
    url: "https://news.example.com/necklace-road-marathon",
    title: "Necklace Road closed for city marathon",
    published_at: "2026-10-01T09:00:00Z",
    retrieved_at: "2026-10-02T08:00:00Z",
    content_hash: "1".repeat(64),
  },
};
