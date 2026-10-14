import { EVENT_SEVERITIES, type EventSeverity, type RoadEvent } from "@/features/events/model";

/** The four REI severities a reviewer chooses from, with what each means. */
export const SEVERITY_CHOICES: { value: EventSeverity; label: string; meaning: string }[] = [
  { value: "LOW", label: "Low", meaning: "little or limited traffic disruption" },
  { value: "MEDIUM", label: "Medium", meaning: "noticeable but manageable disruption" },
  { value: "HIGH", label: "High", meaning: "significant traffic disruption" },
  { value: "CRITICAL", label: "Critical", meaning: "major disruption needing urgent attention" },
];

/**
 * What the form starts with: the severity a reviewer already assigned, or
 * nothing. An unreviewed event never has a preselected severity.
 */
export function initialSeverity(event: RoadEvent): EventSeverity | null {
  return event.severity && EVENT_SEVERITIES.includes(event.severity) ? event.severity : null;
}

/** The severity to send with a decision: only a choice that differs from what is saved. */
export function severityToSave(
  selected: EventSeverity | null,
  saved: EventSeverity | null,
): EventSeverity | undefined {
  return selected !== null && selected !== saved ? selected : undefined;
}
