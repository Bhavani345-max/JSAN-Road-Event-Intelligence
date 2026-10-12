import { describe, expect, it } from "vitest";
import { mapApiEvent } from "@/features/events/api/eventRepository";
import { realApiEvent } from "@/features/events/testing/fixtures";
import type { ApiEvent } from "@/types/api";
import { SEVERITY_CHOICES, initialSeverity, severityToSave } from "./severity";

function toEvent(overrides: Partial<ApiEvent>) {
  const event = mapApiEvent({ ...realApiEvent, ...overrides });
  if (event === null) throw new Error("test event did not map");
  return event;
}

describe("REI severity in the review form", () => {
  it("offers exactly Low, Medium, High and Critical", () => {
    expect(SEVERITY_CHOICES.map((choice) => choice.value)).toEqual(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
    expect(SEVERITY_CHOICES.map((choice) => choice.label)).toEqual(["Low", "Medium", "High", "Critical"]);
  });

  it("preselects nothing for an unreviewed event, whatever the source says", () => {
    const unreviewed = toEvent({
      severity: null,
      detection: { ...realApiEvent.detection!, source_severity: "Serious" },
    });
    expect(initialSeverity(unreviewed)).toBeNull();
    expect(unreviewed.detection?.sourceSeverity).toBe("Serious");
  });

  it("starts from the severity a reviewer saved", () => {
    expect(initialSeverity(toEvent({ severity: "HIGH" }))).toBe("HIGH");
  });

  it("sends a severity only when the reviewer chose one that differs from what is saved", () => {
    expect(severityToSave(null, null)).toBeUndefined();
    expect(severityToSave("HIGH", null)).toBe("HIGH");
    expect(severityToSave("HIGH", "HIGH")).toBeUndefined();
    expect(severityToSave("LOW", "HIGH")).toBe("LOW");
  });

  it("reads the reviewer's assessment separately from the source's severity", () => {
    const event = toEvent({
      severity: "HIGH",
      detection: {
        ...realApiEvent.detection!,
        source_severity: "Serious",
        severity_assessment: {
          severity: "HIGH",
          assessed_by: "local-reviewer",
          assessed_at: "2026-10-08T12:00:00Z",
          reason: "Both carriageways",
          version: 2,
        },
      },
    });
    expect(event.severity).toBe("HIGH");
    expect(event.detection?.sourceSeverity).toBe("Serious");
    expect(event.detection?.severityAssessment).toEqual({
      severity: "HIGH",
      assessedBy: "local-reviewer",
      assessedAt: "2026-10-08T12:00:00Z",
      reason: "Both carriageways",
      version: 2,
    });
    expect(toEvent({}).detection?.severityAssessment).toBeNull();
  });
});
