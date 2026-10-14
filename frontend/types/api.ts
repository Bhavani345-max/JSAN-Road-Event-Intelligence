/**
 * Wire types of the REI API (backend/app), exactly as it returns them.
 * UI code does not use these directly: features map them to their own models.
 */

export interface ApiGeometry {
  type: string;
  coordinates: unknown;
}

/** A language model's reading of an article (packages/event_schema AiReading). */
export interface ApiAiReading {
  model: string;
  prompt_version: string;
  read_at: string;
  stage: string;
  is_road_event: boolean;
  why: string | null;
  intent: string | null;
  impact: string | null;
  cause: string | null;
  summary: string | null;
  city: string | null;
  in_scope: boolean | null;
  places: { name: string; role: string; found_in: string | null; quote: string | null }[];
  period_text: string | null;
  period_read_by: string | null;
  start_time: string | null;
  end_time: string | null;
  authority: string | null;
  evidence: string | null;
  discarded: string[];
}

export interface ApiEvent {
  event_id: string;
  source_id: string;
  source_reference: string | null;
  title: string;
  event_type: string | null;
  description: string | null;
  city: string | null;
  affected_road: string | null;
  start_time: string | null;
  end_time: string | null;
  status: string;
  severity: string | null;
  direction: string | null;
  geometry: ApiGeometry | null;
  confidence: number | null;
  detection: {
    method: string;
    /** Null for an event an official source states itself (no keywords scored). */
    score: number | null;
    matched_keywords: string[];
    road_mentions: string[];
    places?: string[];
    location?: {
      method: string;
      place_name: string;
      place_kind: string;
      precision: string;
      mention: string;
      found_in: string;
      reference: string;
      within?: string | null;
    } | null;
    /** APPROXIMATE, SOURCE_PROVIDED, GIS_RESOLVED, HUMAN_CORRECTED, QC_APPROVED or UNRESOLVED. */
    location_class?: string | null;
    affected_locations?: {
      name: string;
      kind: string | null;
      resolution: string;
      geometry: ApiGeometry | null;
      direction: string | null;
      closure: string | null;
      mention: string | null;
      found_in: string | null;
      reference: string | null;
      /** What the place is to the event, from an AI reading: CLOSED, DIVERSION_ROUTE … */
      role?: string | null;
    }[];
    source_category?: string | null;
    source_severity?: string | null;
    source_status?: string | null;
    attribution?: string | null;
    source_revision?: { revision: number; revised_at: string; changes: string[] } | null;
    pending_source_revision?: { revision: number; revised_at: string; changes: string[] } | null;
    source_reports_ended?: boolean;
    observation?: {
      last_seen_at: string | null;
      missing_since: string | null;
      missed_refreshes: number;
      review_required: boolean;
    } | null;
    provenance?: Record<string, { event_id: string; source_id: string }>;
    merge_conflicts?: { field: string; values: { event_id: string; source_id: string; value: unknown }[] }[];
    merge_review_required?: boolean;
    gis?: {
      engine: string;
      network: string;
      resolved_at: string;
      results: {
      mention: string;
      found_in: string;
      kind: string;
      confidence: string;
      ambiguous: boolean;
      chosen: { matched_name: string; method: string; geometry: ApiGeometry; osm_ids: string[]; reasons: string[] } | null;
      alternatives: { matched_name: string; method: string; geometry: ApiGeometry; osm_ids: string[]; reasons: string[] }[];
      reasons: string[];
      applied: boolean;
    }[];
      applied: boolean;
      not_applied_reason: string | null;
      review_status: string;
      reviewed_by: string | null;
      reviewed_at: string | null;
      review_reason: string | null;
    } | null;
    stated_period?: string | null;
    stated_distance?: string | null;
    stated_distance_m?: number | null;
    source_geometry_length_m?: number | null;
    attributed_to?: string[];
    basis?: string | null;
    location_revision?: {
      previous_place_name: string | null;
      reason: string;
      revised_by: string;
      revised_at: string;
    } | null;
    period_revision?: {
      previous_end: string | null;
      reason: string;
      revised_by: string;
      revised_at: string;
    } | null;
    qc_approval?: {
      approved_by: string;
      approved_at: string;
      reason: string | null;
      version: number;
      /** Approved anyway, overriding the QC checks listed in `overridden`. */
      forced?: boolean;
      overridden?: string[];
    } | null;
    /** A reviewer's REI severity: who, when and why (the value is `severity`). */
    severity_assessment?: {
      severity: string;
      assessed_by: string;
      assessed_at: string;
      reason: string | null;
      version: number;
    } | null;
    /** A language model's reading of the article, checked against the article. */
    ai?: ApiAiReading | null;
  } | null;
  created_at: string;
  updated_at: string;
  source: ApiSourceSummary;
  /** Set when this event was merged into another (then it is not listed alone). */
  merged_into?: string | null;
  /** The evidence of every event merged into this one. */
  other_evidence?: {
    event_id: string;
    source: ApiSourceSummary;
    artifact_id: string | null;
    url: string | null;
    title: string;
    published_at: string | null;
    retrieved_at: string | null;
    how: string | null;
  }[];
  /** For an event in QC_PENDING: every QC requirement it does not yet meet. */
  approval_blockers?: string[];
  /** Pending candidates: events that may be the same as this one. */
  merge_candidates?: {
    candidate_id: number;
    classification: string;
    status: string;
    reasons: string[];
    conflicts: { field: string; a: unknown; b: unknown }[];
    other_event_id: string;
    other_title: string;
    other_source: ApiSourceSummary;
  }[];
  evidence: {
    artifact_id: string;
    url: string | null;
    title: string;
    published_at: string | null;
    retrieved_at: string;
    content_hash: string;
  } | null;
  version: number;
}

export interface ApiEventList {
  items: ApiEvent[];
  total: number;
}

export interface ApiSource {
  source_id: string;
  source_name: string;
  source_type: string;
  organization: string | null;
  authority_type: string | null;
  source_tier: number | null;
  source_url: string | null;
  endpoint: string | null;
  access_method: string | null;
  /**
   * CONNECTED, DISCOVERED, VALIDATED, READY_FOR_INTEGRATION, TERMS_REVIEW_REQUIRED,
   * BLOCKED, NOT_USABLE, REQUIRES_ACCESS or MANUAL_ONLY.
   */
  integration_status: string;
  /**
   * AUTHORITATIVE_OFFICIAL, GOVERNMENT_OPEN_DATA, PARTNER, PUBLISHER, DISCOVERY or
   * COMMERCIAL; null for manual entry.
   */
  source_class: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  cost_category: string | null;
  rate_limit: string | null;
  terms_status: string;
  licence: string | null;
  attribution: string | null;
  commercial_use: string;
  provides_geometry: boolean;
  provides_segments: boolean;
  provides_direction: boolean;
  real_time: boolean;
  discovery_only: boolean;
  active: boolean;
  polling_frequency_minutes: number | null;
  language: string | null;
  events_supported: string[];
  parser_type: string | null;
  terms_reviewed: boolean;
  evidence_retention: string | null;
  notes: string | null;
  last_poll_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
  artifact_count: number;
  event_count: number;
}

export interface ApiIngestionResult {
  source_id: string;
  status: "ok" | "failed";
  error: string | null;
  fetched: number;
  new_artifacts: number;
  duplicates: number;
  /** Held records the source has revised since. */
  revised?: number;
  relevant: number;
  events_created: number;
  started_at: string;
  finished_at: string | null;
}

export interface ApiIngestionRun {
  results: ApiIngestionResult[];
}

export interface ApiPlace {
  name: string;
  /** junction, flyover, landmark, road or area. */
  kind: string;
}

/** A configured city (GET /api/cities). */
export interface ApiCity {
  id: string;
  name: string;
  country: string;
  region: string | null;
  timezone: string;
  language: string;
  /** south, west, north, east */
  bbox: [number, number, number, number];
  /** [longitude, latitude] */
  map_center: [number, number];
  map_zoom: number;
  scope_terms: string[];
  official_sources: string[];
  has_gazetteer: boolean;
}

/** The source of an event, as events carry it. */
export interface ApiSourceSummary {
    source_id: string;
    source_name: string;
    source_type: string;
    source_class?: string | null;
    source_tier?: number | null;
    discovery_only?: boolean;
  }
