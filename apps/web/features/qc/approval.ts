import type { RoadEvent } from "@/features/events/model";

/** The reason recorded with a QC approval from the console. */
export const QC_APPROVE_REASON =
  "Reviewer approved in QC: location and start time checked";

/** Whether the console offers QC approval for an event, and why it is blocked. */
export interface QcApprovalState {
  /** Only an event in QC_PENDING shows the Approve button. */
  offered: boolean;
  /** True when every QC requirement is met. */
  enabled: boolean;
  /** Every unmet requirement, in the API's words. */
  blockers: string[];
}

/**
 * The QC rules themselves live in the API (services/lifecycle), which lists
 * what an event in QC_PENDING still lacks. The console follows that list and
 * never decides on its own; the API checks again when the approval is sent.
 */
export function qcApprovalState(event: RoadEvent): QcApprovalState {
  const offered = event.status === "QC_PENDING";
  const blockers = offered ? event.approvalBlockers : [];
  return { offered, enabled: offered && blockers.length === 0, blockers };
}
