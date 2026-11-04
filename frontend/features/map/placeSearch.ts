/**
 * Finding a place or postcode to move the map to (decision 0055).
 *
 * While typing, only REI's own OpenStreetMap place lists answer (local, for the
 * cities that have one). On Enter, OpenStreetMap's geocoder answers too, through
 * REI's API: its usage policy forbids search-as-you-type and allows one request
 * a second for all of REI's users, so it is asked only when the user presses Enter.
 */

import { apiFetch } from "@/lib/apiClient";

export interface FoundPlace {
  name: string;
  detail: string;
  latitude: number;
  longitude: number;
  /** West, south, east, north, when the place is an area. */
  box: [number, number, number, number] | null;
  kind: string;
  /** "place_list": REI's own OSM list of the city; "nominatim": OpenStreetMap's geocoder. */
  source: "place_list" | "nominatim";
  /** Whether it lies in the chosen city's or country's area; null when none is chosen. */
  in_area: boolean | null;
}

export interface PlaceSearchAnswer {
  results: FoundPlace[];
  /** The city or country searched in; null for everywhere. */
  scope: string | null;
  attribution: string;
}

/** A place the map is moved to, with a key so choosing the same place again moves it again. */
export interface FocusedPlace extends FoundPlace {
  key: number;
}

export function searchPlaces(
  query: string,
  cityId: string | null,
  { localOnly = false, signal }: { localOnly?: boolean; signal?: AbortSignal } = {},
): Promise<PlaceSearchAnswer> {
  const params = new URLSearchParams({ q: query.trim() });
  if (cityId) params.set("city", cityId);
  if (localOnly) params.set("local_only", "true");
  return apiFetch<PlaceSearchAnswer>(`/places/search?${params.toString()}`, { signal });
}

/** What a result list says about where a result is. */
export function placeNote(place: FoundPlace, scope: string | null): string | null {
  if (place.in_area === false && scope) return `outside ${scope}`;
  return null;
}
