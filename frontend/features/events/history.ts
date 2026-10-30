import { EVENT_STATUSES, type EventStatus } from "./model";

/** One recorded version of an event, as the API's event detail returns it. */
export interface EventVersionView {
  version: number;
  status: EventStatus;
  reason: string | null;
  /** Who made the change: a reviewer's email, or a REI process (ingestion, source-update …). */
  changedBy: string;
  at: string;
}

/** A step of an event's validation history, named from what its version records. */
export interface HistoryStage {
  version: number;
  label: string;
  /** detected, review, validated, rejected, closed or change: colours the timeline dot. */
  kind: "detected" | "review" | "validated" | "rejected" | "closed" | "change";
  status: EventStatus;
  reason: string | null;
  changedBy: string;
  at: string;
}

const REVIEW: readonly EventStatus[] = ["DISCOVERED", "EXTRACTED", "GEO_RESOLVED", "VALIDATION_REQUIRED"];
const OPERATIONAL: readonly EventStatus[] = [
  "APPROVED", "SCHEDULED", "ACTIVE", "MONITORING", "EXTENDED", "MODIFIED", "REOPENED",
];
const CLOSED: readonly EventStatus[] = ["EXPIRED", "CANCELLED", "SUPERSEDED"];

/** A version that changed the status: named after where the event went. */
function statusStage(status: EventStatus, previous: EventStatus): Pick<HistoryStage, "label" | "kind"> {
  if (status === "QC_PENDING") return { label: "Confirmed as a road event, sent to QC", kind: "review" };
  if (OPERATIONAL.includes(status)) return { label: "Validated", kind: "validated" };
  if (status === "REJECTED") return { label: "Rejected", kind: "rejected" };
  if (CLOSED.includes(status)) return { label: "Closed", kind: "closed" };
  if (REVIEW.includes(status) && !REVIEW.includes(previous)) return { label: "Returned to validation", kind: "review" };
  return { label: "Status changed", kind: "change" };
}

/** A version that kept the status: named only from the words REI recorded with it. */
function changeLabel(reason: string | null, changedBy: string): string {
  const text = reason ?? "";
  if (text.startsWith("Located at ")) return "Location corrected";
  if (text.startsWith("Extended until ")) return "End date extended";
  if (text.startsWith("REI severity set")) return "Severity set";
  if (text.startsWith("Merged into ")) return "Merged into another event";
  if (changedBy === "source-update") return "Updated by the source";
  if (changedBy === "auto-merge") return "Merged with another report";
  return "Updated";
}

/**
 * The event's history as steps, oldest first: only what its recorded versions
 * show, with each version's own reason. Nothing is inferred beyond the status
 * and the recorded words (REI records no separate "published" step).
 */
export function historyStages(versions: readonly EventVersionView[]): HistoryStage[] {
  const ordered = [...versions].sort((a, b) => a.version - b.version);
  return ordered.map((version, index) => {
    const previous = ordered[index - 1];
    const named =
      index === 0
        ? { label: "Detected", kind: "detected" as const }
        : previous && version.status !== previous.status
          ? statusStage(version.status, previous.status)
          : { label: changeLabel(version.reason, version.changedBy), kind: "change" as const };
    return {
      version: version.version,
      ...named,
      status: version.status,
      reason: version.reason,
      changedBy: version.changedBy,
      at: version.at,
    };
  });
}

/** The API's version records as the web model holds them; unknown statuses are dropped. */
export function toVersionViews(
  versions: readonly { version: number; status: string; change_reason: string | null; changed_by: string; created_at: string }[],
): EventVersionView[] {
  return versions
    .filter((v) => (EVENT_STATUSES as readonly string[]).includes(v.status))
    .map((v) => ({
      version: v.version,
      status: v.status as EventStatus,
      reason: v.change_reason,
      changedBy: v.changed_by,
      at: v.created_at,
    }));
}
