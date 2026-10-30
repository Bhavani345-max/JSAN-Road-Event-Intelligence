import { getRepresentativePoint } from "@/features/map/geometry";
import { apiFetch } from "@/lib/apiClient";
import type {
  ApiAiReading,
  ApiArticleImage,
  ApiEvent,
  ApiEventDetail,
  ApiEventList,
  ApiGeometry,
} from "@/types/api";
import type { EventListView } from "../filters";
import { toVersionViews, type EventVersionView } from "../history";
import {
  type AiReadingView,
  type ArticleImage,
  EVENT_DIRECTIONS,
  EVENT_SEVERITIES,
  EVENT_STATUSES,
  EVENT_TYPES,
  LOCATION_CLASSES,
  type EventGeometry,
  type RoadEvent,
} from "../model";

/**
 * How many events a list loads at first, and how many more each "Show more"
 * adds. The Netherlands' review queue held about 34,000 on 29 October 2026:
 * loaded whole, nothing showed for over a minute and phones gave up.
 */
export const LIST_STEP = 1000;

/** The newest events of a list, and how many the list holds in all. */
export interface EventPage {
  events: RoadEvent[];
  /** What the API lists for this view and place; more than `events` while not all are loaded. */
  total: number;
}

/** The single entry point the UI uses to obtain events. */
export interface EventRepository {
  listEvents(view: EventListView, cityId?: string | null, limit?: number): Promise<EventPage>;
}

/** `value` if it is one of `allowed`, otherwise null. */
function oneOf<T extends string>(allowed: readonly T[], value: string | null): T | null {
  return allowed.includes(value as T) ? (value as T) : null;
}

function toGeometry(geometry: ApiGeometry | null): EventGeometry | null {
  if (!geometry || !Array.isArray(geometry.coordinates)) return null;
  switch (geometry.type) {
    case "Point":
    case "LineString":
    case "Polygon":
      // The API validates coordinates against the same GeoJSON types.
      return geometry as EventGeometry;
    case "MultiLineString":
    case "MultiPolygon":
      // A multi-part shape with no parts says nothing about where the event is.
      return geometry.coordinates.length > 0 ? (geometry as EventGeometry) : null;
    default:
      return null;
  }
}

function toCandidate(candidate: {
  matched_name: string;
  method: string;
  geometry: ApiGeometry;
  osm_ids: string[];
  reasons: string[];
}) {
  return {
    matchedName: candidate.matched_name,
    method: candidate.method,
    geometry: toGeometry(candidate.geometry),
    osmIds: candidate.osm_ids,
    reasons: candidate.reasons,
  };
}

const IMAGE_STATUSES: Record<string, ArticleImage["status"]> = {
  AVAILABLE: "available",
  WITHHELD: "withheld",
};

/**
 * The article's image as the web model holds it. An available image without an
 * address, an unknown status or an API from before decision 0050 is no image.
 */
function toArticleImage(dto: ApiArticleImage | undefined, sourceName: string): ArticleImage {
  const status = (dto && IMAGE_STATUSES[dto.status]) ?? "none";
  const available = status === "available" && Boolean(dto?.url);
  return {
    status: status === "available" && !available ? "none" : status,
    url: available ? dto!.url : null,
    sourceUrl: dto?.source_url ?? null,
    sourceName,
    caption: dto?.caption ?? null,
    altText: dto?.alt_text ?? null,
    credit: dto?.credit ?? null,
    licence: dto?.licence ?? null,
    attribution: dto?.attribution ?? null,
    reason: dto?.reason ?? null,
  };
}

function toRevisionNote(
  note: { revision: number; revised_at: string; changes: string[] } | null | undefined,
) {
  return note ? { revision: note.revision, revisedAt: note.revised_at, changes: note.changes } : null;
}

/**
 * Converts an API event into the web model. Returns null for an event whose
 * lifecycle status this version of the app does not know, rather than
 * showing it under a wrong status.
 */
export function mapApiEvent(dto: ApiEvent): RoadEvent | null {
  const status = oneOf(EVENT_STATUSES, dto.status);
  if (!status) {
    console.warn(`Skipping event ${dto.event_id}: unknown status "${dto.status}"`);
    return null;
  }

  const geometry = toGeometry(dto.geometry);
  const anchor = geometry ? getRepresentativePoint(geometry) : null;

  return {
    id: dto.event_id,
    title: dto.title,
    eventType: oneOf(EVENT_TYPES, dto.event_type),
    description: dto.description,
    affectedRoad: dto.affected_road,
    city: dto.city,
    longitude: anchor ? anchor[0] : null,
    latitude: anchor ? anchor[1] : null,
    startTime: dto.start_time,
    endTime: dto.end_time,
    status,
    severity: oneOf(EVENT_SEVERITIES, dto.severity),
    direction: oneOf(EVENT_DIRECTIONS, dto.direction),
    geometry,
    confidence: dto.confidence,
    source: { id: dto.source.source_id, name: dto.source.source_name, type: dto.source.source_type },
    sourceAuthority: {
      sourceClass: dto.source.source_class ?? null,
      tier: dto.source.source_tier ?? null,
      discoveryOnly: dto.source.discovery_only ?? false,
    },
    otherEvidence: (dto.other_evidence ?? []).map((other) => ({
      eventId: other.event_id,
      sourceName: other.source.source_name,
      sourceClass: other.source.source_class ?? null,
      url: other.url,
      title: other.title,
      publishedAt: other.published_at,
      how: other.how,
      image: toArticleImage(other.image, other.source.source_name),
    })),
    mergeCandidates: (dto.merge_candidates ?? []).map((candidate) => ({
      candidateId: candidate.candidate_id,
      classification: candidate.classification,
      reasons: candidate.reasons,
      conflicts: candidate.conflicts.map((conflict) => ({ field: conflict.field })),
      otherEventId: candidate.other_event_id,
      otherTitle: candidate.other_title,
      otherSourceName: candidate.other_source.source_name,
    })),
    approvalBlockers: dto.approval_blockers ?? [],
    // An API from before decision 0038 lists only events its maps draw.
    mapEligible: dto.map_eligible ?? true,
    offMapReason: dto.off_map_reason ?? null,
    sourceReference: dto.source_reference,
    version: dto.version,
    evidence: dto.evidence && {
      url: dto.evidence.url,
      title: dto.evidence.title,
      publishedAt: dto.evidence.published_at,
      retrievedAt: dto.evidence.retrieved_at,
      image: toArticleImage(dto.evidence.image, dto.source.source_name),
    },
    detection: dto.detection && {
      method: dto.detection.method,
      matchedKeywords: dto.detection.matched_keywords,
      roadMentions: dto.detection.road_mentions,
      location: dto.detection.location
        ? {
            method: dto.detection.location.method,
            placeName: dto.detection.location.place_name,
            placeKind: dto.detection.location.place_kind,
            foundIn: dto.detection.location.found_in,
            reference: dto.detection.location.reference,
            within: dto.detection.location.within ?? null,
          }
        : null,
      statedPeriod: dto.detection.stated_period ?? null,
      statedDistance: dto.detection.stated_distance ?? null,
      statedDistanceM: dto.detection.stated_distance_m ?? null,
      sourceGeometryLengthM: dto.detection.source_geometry_length_m ?? null,
      attributedTo: dto.detection.attributed_to ?? [],
      basis: dto.detection.basis ?? null,
      locationRevision: dto.detection.location_revision
        ? {
            previousPlaceName: dto.detection.location_revision.previous_place_name,
            reason: dto.detection.location_revision.reason,
            revisedAt: dto.detection.location_revision.revised_at,
          }
        : null,
      periodRevision: dto.detection.period_revision
        ? {
            previousEnd: dto.detection.period_revision.previous_end,
            reason: dto.detection.period_revision.reason,
            revisedAt: dto.detection.period_revision.revised_at,
          }
        : null,
      qcApproval: dto.detection.qc_approval
        ? {
            approvedBy: dto.detection.qc_approval.approved_by,
            approvedAt: dto.detection.qc_approval.approved_at,
            reason: dto.detection.qc_approval.reason,
            version: dto.detection.qc_approval.version,
            forced: dto.detection.qc_approval.forced ?? false,
            overridden: dto.detection.qc_approval.overridden ?? [],
          }
        : null,
      locationClass: oneOf(LOCATION_CLASSES, dto.detection.location_class ?? null),
      affectedLocations: (dto.detection.affected_locations ?? []).flatMap((location) => {
        const resolution = oneOf(LOCATION_CLASSES, location.resolution);
        return resolution
          ? [
              {
                name: location.name,
                kind: location.kind,
                resolution,
                geometry: toGeometry(location.geometry),
                direction: location.direction,
                closure: location.closure,
                foundIn: location.found_in,
                role: location.role ?? null,
              },
            ]
          : [];
      }),
      sourceCategory: dto.detection.source_category ?? null,
      severityAssessment:
        dto.detection.severity_assessment &&
        oneOf(EVENT_SEVERITIES, dto.detection.severity_assessment.severity)
          ? {
              severity: oneOf(EVENT_SEVERITIES, dto.detection.severity_assessment.severity)!,
              assessedBy: dto.detection.severity_assessment.assessed_by,
              assessedAt: dto.detection.severity_assessment.assessed_at,
              reason: dto.detection.severity_assessment.reason,
              version: dto.detection.severity_assessment.version,
            }
          : null,
      sourceSeverity: dto.detection.source_severity ?? null,
      attribution: dto.detection.attribution ?? null,
      sourceRevision: toRevisionNote(dto.detection.source_revision),
      pendingSourceRevision: toRevisionNote(dto.detection.pending_source_revision),
      sourceReportsEnded: dto.detection.source_reports_ended ?? false,
      observation: dto.detection.observation
        ? {
            lastSeenAt: dto.detection.observation.last_seen_at,
            missingSince: dto.detection.observation.missing_since,
            missedRefreshes: dto.detection.observation.missed_refreshes,
            reviewRequired: dto.detection.observation.review_required,
          }
        : null,
      provenance: Object.fromEntries(
        Object.entries(dto.detection.provenance ?? {}).map(([field, origin]) => [
          field,
          { eventId: origin.event_id, sourceId: origin.source_id },
        ]),
      ),
      mergeConflicts: (dto.detection.merge_conflicts ?? []).map((conflict) => ({
        field: conflict.field,
        values: conflict.values.map((v) => ({ eventId: v.event_id, sourceId: v.source_id, value: v.value })),
      })),
      mergeReviewRequired: dto.detection.merge_review_required ?? false,
      gis: dto.detection.gis
        ? {
            network: dto.detection.gis.network,
            resolvedAt: dto.detection.gis.resolved_at,
            applied: dto.detection.gis.applied,
            notAppliedReason: dto.detection.gis.not_applied_reason,
            reviewStatus: dto.detection.gis.review_status,
            reviewedBy: dto.detection.gis.reviewed_by,
            reviewReason: dto.detection.gis.review_reason,
            results: dto.detection.gis.results.map((result) => ({
              mention: result.mention,
              foundIn: result.found_in,
              kind: result.kind,
              confidence: result.confidence,
              ambiguous: result.ambiguous,
              chosen: result.chosen ? toCandidate(result.chosen) : null,
              alternatives: result.alternatives.map(toCandidate),
              reasons: result.reasons,
              applied: result.applied,
            })),
          }
        : null,
      ai: toAiReading(dto.detection.ai ?? null),
    },
  };
}

function toAiReading(ai: ApiAiReading | null): AiReadingView | null {
  if (!ai) return null;
  return {
    model: ai.model,
    readAt: ai.read_at,
    stage: ai.stage,
    isRoadEvent: ai.is_road_event,
    why: ai.why,
    intent: oneOf(EVENT_TYPES, ai.intent),
    impact: ai.impact,
    cause: ai.cause,
    summary: ai.summary,
    city: ai.city,
    inScope: ai.in_scope,
    places: (ai.places ?? []).map((place) => ({
      name: place.name,
      role: place.role,
      foundIn: place.found_in,
      quote: place.quote,
    })),
    periodText: ai.period_text,
    periodReadBy: ai.period_read_by,
    startTime: ai.start_time,
    endTime: ai.end_time,
    authority: ai.authority,
    evidence: ai.evidence,
    discarded: ai.discarded ?? [],
  };
}

/** The API's pages of a list, newest first, until `limit` events or the end. */
async function fetchEventPages(
  path: string,
  params: URLSearchParams,
  limit: number,
): Promise<{ items: ApiEvent[]; total: number }> {
  const items: ApiEvent[] = [];
  let total = 0;
  do {
    params.set("limit", String(Math.min(500, limit - items.length)));
    params.set("offset", String(items.length));
    const page = await apiFetch<ApiEventList>(`${path}?${params.toString()}`);
    total = page.total;
    items.push(...page.items);
    if (page.items.length === 0) break;
  } while (items.length < Math.min(total, limit));
  return { items, total };
}

function toEventPage({ items, total }: { items: ApiEvent[]; total: number }): EventPage {
  return { events: items.map(mapApiEvent).filter((event) => event !== null), total };
}

/** Every recorded version of one event, oldest first (read only). */
export async function fetchEventHistory(eventId: string): Promise<EventVersionView[]> {
  const detail = await apiFetch<ApiEventDetail>(`/events/${encodeURIComponent(eventId)}`);
  return toVersionViews(detail.versions ?? []);
}

/** Events from the server-classified view, most recently published first. */
export const apiEventRepository: EventRepository = {
  async listEvents(view, cityId = null, limit = LIST_STEP) {
    const params = new URLSearchParams({ view });
    if (cityId) params.set("city", cityId);
    return toEventPage(await fetchEventPages("/events", params, limit));
  },
};

/**
 * The events matching a text search, newest first, at most LIST_STEP of them.
 * The API searches each event, its source, and the full text of the article
 * it came from, including events the list has not loaded.
 */
export async function searchEvents(
  query: string,
  view: EventListView,
  cityId?: string | null,
): Promise<EventPage> {
  const params = new URLSearchParams({ view, q: query.trim() });
  if (cityId) params.set("city", cityId);
  return toEventPage(await fetchEventPages("/events", params, LIST_STEP));
}
