/**
 * TomTom live incidents (decision 0054): asked for the area on screen, drawn
 * under REI's own events, never stored. TomTom's terms forbid storing its
 * results, so these are not REI events: they are not in the list, the counts
 * or the review queue, and nothing here keeps them once the map moves on.
 */

import { apiFetch } from "@/lib/apiClient";
import { formatDateTime } from "@/features/events/presentation";

/** TomTom answers for areas of up to 10,000 km² (about a city). */
export const MAX_LIVE_AREA_KM2 = 10_000;

export interface LiveIncidentProperties {
  id: string | null;
  /** REI's word for TomTom's category (ROAD_CLOSURE, ROAD_WORKS …). */
  category: string;
  label: string;
  description: string | null;
  from: string | null;
  to: string | null;
  roads: string[];
  start: string | null;
  end: string | null;
  delay: string | null;
}

export interface LiveIncidentFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] } | { type: "LineString"; coordinates: [number, number][] };
  properties: LiveIncidentProperties;
}

export interface LiveIncidentCollection {
  type: "FeatureCollection";
  features: LiveIncidentFeature[];
  /** TomTom's own copyright caption (its Copyright API), shown with the layer. */
  attribution: string;
  fetched_at: string;
}

/** West, south, east, north in degrees. */
export type Box = [number, number, number, number];

/** The box's approximate area in km² (equirectangular, at its middle latitude). */
export function boxAreaKm2([west, south, east, north]: Box): number {
  const middle = (((south + north) / 2) * Math.PI) / 180;
  const width = (east - west) * 111.32 * Math.cos(middle);
  const height = (north - south) * 110.57;
  return Math.abs(width * height);
}

/** The query value for the area on screen, or null when it is too large to ask TomTom for. */
export function liveBbox(box: Box): string | null {
  const [west, south, east, north] = [
    Math.max(-180, box[0]),
    Math.max(-90, box[1]),
    Math.min(180, box[2]),
    Math.min(90, box[3]),
  ];
  if (!(west < east && south < north)) return null;
  if (boxAreaKm2([west, south, east, north]) > MAX_LIVE_AREA_KM2) return null;
  return [west, south, east, north].map((value) => value.toFixed(5)).join(",");
}

export function fetchLiveIncidents(bbox: string, signal?: AbortSignal): Promise<LiveIncidentCollection> {
  return apiFetch<LiveIncidentCollection>(`/live/tomtom-incidents?bbox=${encodeURIComponent(bbox)}`, {
    signal,
    cache: "no-store",
  });
}

/** One line about an incident: "Road closed · Literacka → Literacka · since Tue, 3 Nov 2026, 13:44". */
export function describeIncident(incident: LiveIncidentProperties): string {
  const where =
    incident.from && incident.to && incident.from !== incident.to
      ? `${incident.from} → ${incident.to}`
      : incident.from ?? incident.to ?? null;
  const start = formatDateTime(incident.start);
  const end = formatDateTime(incident.end);
  const when = start && end ? `${start} – ${end}` : start ? `since ${start}` : end ? `until ${end}` : null;
  return [incident.label, where, incident.roads.length ? incident.roads.join(", ") : null, when]
    .filter(Boolean)
    .join(" · ");
}
