import type { EventSeverity, EventStatus, EventType } from "@/features/events/model";
import { apiFetch, apiPost } from "@/lib/apiClient";
import type { ApiEvent, ApiPlace } from "@/types/api";

/**
 * Records a human review decision. The API enforces which status changes are
 * allowed and rejects the rest (HTTP 409) with an explanation.
 */
export async function updateEventStatus(
  eventId: string,
  status: EventStatus,
  reason?: string,
  severity?: EventSeverity,
  force = false,
): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/status`, {
    status,
    reason,
    ...(severity ? { severity } : {}),
    // Approve anyway: the API records the QC checks the reviewer overrode.
    ...(force ? { force: true } : {}),
  });
}

/** Records a reviewer's REI severity (Low, Medium, High or Critical) for an event. */
export async function setEventSeverity(
  eventId: string,
  severity: EventSeverity,
  reason?: string,
): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/severity`, {
    severity,
    reason,
  });
}

/** A reviewer accepts the GIS location proposed for an event. */
export async function approveGis(eventId: string, reason: string): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/gis/approve`, { reason });
}

/** A reviewer rejects the GIS location; the previous location is restored. */
export async function rejectGis(eventId: string, reason: string): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/gis/reject`, { reason });
}

/** A reviewer picks one GIS candidate as the event's location. */
export async function chooseGis(
  eventId: string,
  resultIndex: number,
  alternativeIndex: number | null,
  reason: string,
): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/gis/choose`, {
    result_index: resultIndex,
    alternative_index: alternativeIndex,
    reason,
  });
}

/** A reviewer confirms a proposed junction reference, so the resolver may use it. */
export async function confirmJunction(junctionId: number, reason: string): Promise<void> {
  await apiPost<unknown>(`/junctions/${junctionId}/confirm`, { reason });
}

/**
 * A reviewer says all these candidates of one event are the same event: one
 * decision merges every report of the story, all evidence kept.
 */
export async function confirmAllMerges(candidateIds: number[], reason: string): Promise<void> {
  await apiPost<ApiEvent>("/merge-candidates/confirm-all", { candidate_ids: candidateIds, reason });
}

/** A reviewer says two events are the same: they are merged, all evidence kept. */
export async function confirmMerge(candidateId: number, reason: string): Promise<void> {
  await apiPost<ApiEvent>(`/merge-candidates/${candidateId}/confirm`, { reason });
}

/** A reviewer says two events are different: they stay apart and are not proposed again. */
export async function rejectMerge(candidateId: number, reason: string): Promise<void> {
  await apiPost<unknown>(`/merge-candidates/${candidateId}/reject`, { reason });
}

/**
 * Records that an event runs longer than recorded.
 *
 * @param endDate The new last day ("2026-12-31"), or null for until further notice.
 * @param reason How the reviewer knows; kept with the event.
 */
export async function extendEvent(
  eventId: string,
  endDate: string | null,
  reason: string,
): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/extend`, {
    end_date: endDate,
    reason,
  });
}

/** A road event as a reviewer enters it. Dates are whole days ("2026-10-05"). */
export interface ManualEventInput {
  title: string;
  eventType: EventType | null;
  place: string | null;
  startDate: string | null;
  endDate: string | null;
  description: string | null;
  referenceUrl: string | null;
  /** How the reviewer knows of the event. */
  basis: string;
}

/** The request body the API expects for a manual entry. */
export function toManualEventBody(input: ManualEventInput) {
  return {
    title: input.title,
    event_type: input.eventType,
    place: input.place,
    start_date: input.startDate,
    end_date: input.endDate,
    description: input.description,
    reference_url: input.referenceUrl,
    basis: input.basis,
  };
}

/** Saves a manually entered event and returns its id. */
export async function createManualEvent(input: ManualEventInput): Promise<string> {
  const event = await apiPost<ApiEvent>("/events", toManualEventBody(input));
  return event.event_id;
}

export type PlaceSuggestion = ApiPlace;

/** Known Hyderabad places matching what has been typed. */
export function suggestPlaces(query: string): Promise<PlaceSuggestion[]> {
  return apiFetch<ApiPlace[]>(`/places?q=${encodeURIComponent(query.trim())}`);
}

/** The spot a reviewer picked on the map for an event. */
export interface EventLocationInput {
  longitude: number;
  latitude: number;
  /** What is at that spot, e.g. "IIIT Junction". */
  placeName: string;
  /** How the reviewer knows the event is there; kept with the event. */
  reason: string;
}

/** Puts an event at the spot a reviewer picked on the map. */
export async function setEventLocation(eventId: string, input: EventLocationInput): Promise<void> {
  await apiPost<ApiEvent>(`/events/${encodeURIComponent(eventId)}/location`, {
    longitude: input.longitude,
    latitude: input.latitude,
    place_name: input.placeName,
    reason: input.reason,
  });
}
