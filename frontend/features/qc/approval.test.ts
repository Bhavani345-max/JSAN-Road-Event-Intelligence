import { describe, expect, it } from "vitest";
import { mapApiEvent } from "@/features/events/api/eventRepository";
import { realApiEvent } from "@/features/events/testing/fixtures";
import type { ApiEvent } from "@/types/api";
import { qcApprovalState } from "./approval";
import type { RoadEvent } from "@/features/events/model";

const APPROXIMATE =
  "The location is approximate (the position of a place the source names): " +
  "correct the location on the map first.";
const NO_START = "It has no start time.";

/** The console form of a test event; every test event here maps. */
function toEvent(dto: ApiEvent): RoadEvent {
  const event = mapApiEvent(dto);
  if (event === null) throw new Error("test event did not map");
  return event;
}

/** Test events shaped like the API's answer (test data, not real events). */
function apiEvent(overrides: Partial<ApiEvent>): ApiEvent {
  return { ...realApiEvent, ...overrides };
}

describe("QC approval", () => {
  it("reads the API's blockers and approval record", () => {
    const event = toEvent(
      apiEvent({
        status: "APPROVED",
        detection: {
          ...realApiEvent.detection!,
          qc_approval: {
            approved_by: "local-reviewer",
            approved_at: "2026-10-07T09:00:00Z",
            reason: "Location and start time checked",
            version: 4,
          },
        },
      }),
    );
    expect(event.approvalBlockers).toEqual([]);
    expect(event.detection?.qcApproval).toEqual({
      approvedBy: "local-reviewer",
      approvedAt: "2026-10-07T09:00:00Z",
      reason: "Location and start time checked",
      version: 4,
      forced: false,
      overridden: [],
    });
  });

  it("reads an approval made anyway, with the checks it overrode", () => {
    const event = toEvent(
      apiEvent({
        status: "APPROVED",
        detection: {
          ...realApiEvent.detection!,
          qc_approval: {
            approved_by: "local-reviewer",
            approved_at: "2026-10-09T12:00:00Z",
            reason: "Confirmed with the traffic police",
            version: 5,
            forced: true,
            overridden: [NO_START, APPROXIMATE],
          },
        },
      }),
    );
    expect(event.detection?.qcApproval?.forced).toBe(true);
    expect(event.detection?.qcApproval?.overridden).toEqual([NO_START, APPROXIMATE]);
  });

  it("treats an answer from before approval existed as having no blockers or record", () => {
    const event = toEvent(realApiEvent);
    expect(event.approvalBlockers).toEqual([]);
    expect(event.detection?.qcApproval).toBeNull();
  });

  it("enables Approve only for an event in QC_PENDING with no blockers", () => {
    const ready = toEvent(apiEvent({ status: "QC_PENDING", approval_blockers: [] }));
    expect(qcApprovalState(ready)).toEqual({ offered: true, enabled: true, blockers: [] });
  });

  it("disables Approve and lists every reason when a requirement fails", () => {
    const blocked = toEvent(
      apiEvent({ status: "QC_PENDING", approval_blockers: [NO_START, APPROXIMATE] }),
    );
    expect(qcApprovalState(blocked)).toEqual({
      offered: true,
      enabled: false,
      blockers: [NO_START, APPROXIMATE],
    });
  });

  it.each(["VALIDATION_REQUIRED", "APPROVED", "REJECTED"] as const)(
    "does not offer Approve for an event in %s",
    (status) => {
      const event = toEvent(apiEvent({ status, approval_blockers: [APPROXIMATE] }));
      expect(qcApprovalState(event)).toEqual({ offered: false, enabled: false, blockers: [] });
    },
  );
});
