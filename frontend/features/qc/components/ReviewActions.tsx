import { useState } from "react";
import {
  isManualEntry,
  isSourceProvided,
  type EventSeverity,
  type EventStatus,
  type Position,
  type RoadEvent,
} from "@/features/events/model";
import { formatDateTime, getStatusPhase, timeZoneOf } from "@/features/events/presentation";
import { setEventSeverity, updateEventStatus } from "../api";
import { QC_APPROVE_REASON, qcApprovalState } from "../approval";
import { SEVERITY_CHOICES, initialSeverity, severityToSave } from "../severity";
import ExtendEvent from "./ExtendEvent";
import GisReview from "./GisReview";
import MergeCandidates from "./MergeCandidates";
import SetLocation from "./SetLocation";

interface ReviewAction {
  to: EventStatus;
  label: string;
  reason: string;
  tone: "primary" | "danger" | "neutral";
}

/** What a reviewer can do with an event in each review status. */
const REVIEW_ACTIONS: Partial<Record<EventStatus, { hint: string; actions: ReviewAction[] }>> = {
  VALIDATION_REQUIRED: {
    hint: "Read the original article, then decide whether this is a real road event.",
    actions: [
      {
        to: "QC_PENDING",
        label: "Confirm road event",
        reason: "Reviewer confirmed the article describes a road event",
        tone: "primary",
      },
      {
        to: "REJECTED",
        label: "Reject",
        reason: "Reviewer rejected: not a road event",
        tone: "danger",
      },
    ],
  },
  QC_PENDING: {
    hint: "Confirmed as a road event. Approve it once it has an exact location and a start time.",
    actions: [
      {
        to: "VALIDATION_REQUIRED",
        label: "Back to validation",
        reason: "Reviewer returned the event to validation",
        tone: "neutral",
      },
      {
        to: "REJECTED",
        label: "Reject",
        reason: "Reviewer rejected: not a road event",
        tone: "danger",
      },
    ],
  },
  REJECTED: {
    hint: "Rejected as not a road event.",
    actions: [
      {
        to: "VALIDATION_REQUIRED",
        label: "Reopen for validation",
        reason: "Reviewer reopened a rejected event",
        tone: "neutral",
      },
    ],
  },
};

const TONE_CLASSES: Record<ReviewAction["tone"], string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700",
  danger: "bg-white text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-50",
  neutral: "bg-white text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-slate-50",
};

interface ReviewActionsProps {
  event: RoadEvent;
  /** Called after a decision has been saved, so the caller can reload events. */
  onUpdated: () => void;
  /** The spot clicked on the map while the location is being corrected. */
  pickedPoint: Position | null;
  /** Tells the map when its clicks are choosing a spot rather than an event. */
  onPickingChange: (active: boolean) => void;
}

/** Human review controls for an event. */
export default function ReviewActions({
  event,
  onUpdated,
  pickedPoint,
  onPickingChange,
}: ReviewActionsProps) {
  const [pending, setPending] = useState<EventStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Which correction form is open in place of the buttons.
  const [editing, setEditing] = useState<"period" | "location" | null>(null);
  // Shown after a correction has been saved, until the next action.
  const [notice, setNotice] = useState<string | null>(null);
  // REI severity as the reviewer chooses it; nothing is preselected for an
  // event no reviewer has assessed.
  const savedSeverity = initialSeverity(event);
  const [severity, setSeverity] = useState<EventSeverity | null>(savedSeverity);
  const [savingSeverity, setSavingSeverity] = useState(false);
  // "Approve anyway": the reviewer's reason for overriding the unmet QC checks.
  const [forcing, setForcing] = useState(false);
  const [forceReason, setForceReason] = useState("");
  // Folded away by the reviewer to read the details; open for every new event.
  const [collapsed, setCollapsed] = useState(false);
  const assessment = event.detection?.severityAssessment ?? null;

  const review = REVIEW_ACTIONS[event.status];
  const approval = qcApprovalState(event);
  const approved = event.detection?.qcApproval ?? null;
  // An event that is over, or was never one, is reopened rather than corrected.
  const canCorrect = getStatusPhase(event.status) !== "closed";
  if (!review && !canCorrect) return null;
  const hint =
    event.status === "VALIDATION_REQUIRED" && isManualEntry(event)
      ? "Entered by a reviewer. Check the basis given, then decide whether this is a real road event."
      : event.status === "VALIDATION_REQUIRED" && isSourceProvided(event)
        ? "Published by an official source. Check the source record, then decide whether to take it forward."
        : review?.hint;

  async function saveSeverity() {
    const chosen = severityToSave(severity, savedSeverity);
    if (!chosen) return;
    setSavingSeverity(true);
    setError(null);
    setNotice(null);
    try {
      await setEventSeverity(event.id, chosen);
      setNotice("REI severity saved.");
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The severity could not be saved.");
    } finally {
      setSavingSeverity(false);
    }
  }

  async function approveAnyway() {
    setPending("APPROVED");
    setError(null);
    setNotice(null);
    try {
      await updateEventStatus(
        event.id,
        "APPROVED",
        forceReason.trim(),
        severityToSave(severity, savedSeverity),
        true,
      );
      setForcing(false);
      setForceReason("");
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The approval could not be saved.");
    } finally {
      setPending(null);
    }
  }

  async function apply(action: ReviewAction) {
    setPending(action.to);
    setError(null);
    setNotice(null);
    try {
      // A severity chosen but not yet saved goes with the decision.
      await updateEventStatus(
        event.id,
        action.to,
        action.reason,
        severityToSave(severity, savedSeverity),
      );
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The change could not be saved.");
    } finally {
      setPending(null);
    }
  }

  return (
    // Scrolls on its own, so long review content (merge candidates, GIS
    // results, approval blockers, correction forms) is never cut off and the
    // event details above keep their share of the panel.
    <div
      role="region"
      aria-label="Human review"
      className={`shrink-0 overscroll-contain border-t border-slate-200 bg-slate-50 px-4 [scrollbar-gutter:stable] ${
        // A phone's details sheet is short: the review keeps a smaller share of it.
        collapsed ? "py-2" : "max-h-[28dvh] overflow-y-auto py-3 wide:max-h-[45vh]"
      }`}
    >
      {/* Folding it away gives the details above the room; nothing in it is reset. */}
      <button
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
        className="flex w-full cursor-pointer items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-700"
      >
        <svg
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          className={`h-3 w-3 transition-transform ${collapsed ? "" : "rotate-90"}`}
          aria-hidden="true"
        >
          <path d="m6 3.5 4.5 4.5L6 12.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Human review
        {collapsed && <span className="ml-auto font-normal normal-case tracking-normal">Show actions</span>}
      </button>
      <div hidden={collapsed}>
      <MergeCandidates candidates={event.mergeCandidates} onDecided={onUpdated} />
      <GisReview event={event} onDecided={onUpdated} />
      {editing === "period" ? (
        <ExtendEvent
          event={event}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setNotice("End date saved.");
            onUpdated();
          }}
        />
      ) : editing === "location" ? (
        <SetLocation
          event={event}
          pickedPoint={pickedPoint}
          onPickingChange={onPickingChange}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setNotice("Location saved.");
            onUpdated();
          }}
        />
      ) : (
        <>
          {hint && <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{hint}</p>}
          {approved && !approved.forced && (
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              QC approved by {approved.approvedBy} on{" "}
              {formatDateTime(approved.approvedAt, timeZoneOf(event.city, event.source.id)) ?? approved.approvedAt}{" "}
              (version {approved.version})
              {approved.reason && <>: &ldquo;{approved.reason}&rdquo;</>}.
            </p>
          )}
          {approved?.forced && (
            <div
              role="note"
              className="mt-1 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900 ring-1 ring-inset ring-amber-200"
            >
              <p>
                <span className="font-semibold">Approved anyway</span> by {approved.approvedBy} on{" "}
                {formatDateTime(approved.approvedAt, timeZoneOf(event.city, event.source.id)) ?? approved.approvedAt} (version{" "}
                {approved.version}), overriding:
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                {approved.overridden.map((check) => (
                  <li key={check}>{check}</li>
                ))}
              </ul>
              {approved.reason && <p className="mt-1">Reason: &ldquo;{approved.reason}&rdquo;</p>}
            </div>
          )}
          {approval.blockers.length > 0 && (
            <div
              role="note"
              aria-label="Approval blocked"
              className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-inset ring-amber-200"
            >
              <p className="font-semibold">Approval is blocked:</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                {approval.blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
              {approval.offered && !forcing && (
                <button
                  type="button"
                  disabled={pending !== null}
                  onClick={() => setForcing(true)}
                  className="mt-2 cursor-pointer text-xs font-semibold text-amber-900 underline underline-offset-2 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Approve anyway…
                </button>
              )}
              {approval.offered && forcing && (
                <div className="mt-2">
                  <label htmlFor={`force-reason-${event.id}`} className="block text-[11px] font-semibold">
                    Why approve despite these checks? Your reason and the checks overridden are recorded in the
                    history; an approximate location stays marked approximate.
                  </label>
                  <textarea
                    id={`force-reason-${event.id}`}
                    value={forceReason}
                    maxLength={500}
                    rows={2}
                    onChange={(e) => setForceReason(e.target.value)}
                    placeholder="e.g. Confirmed with the traffic police; the closure starts today"
                    className="mt-1 w-full resize-none rounded-lg border-0 bg-white px-2.5 py-1.5 text-xs text-slate-800 shadow-sm ring-1 ring-inset ring-amber-300 placeholder:text-slate-400 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={pending !== null || forceReason.trim().length < 5}
                      onClick={approveAnyway}
                      title={forceReason.trim().length < 5 ? "Give a reason first" : "Approve despite the unmet checks"}
                      className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES.danger}`}
                    >
                      {pending === "APPROVED" ? "Saving…" : "Approve anyway"}
                    </button>
                    <button
                      type="button"
                      disabled={pending !== null}
                      onClick={() => {
                        setForcing(false);
                        setForceReason("");
                      }}
                      className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES.neutral}`}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
          {canCorrect && (
            <fieldset className="mt-2.5" aria-label="REI severity">
              <legend className="text-xs font-semibold text-slate-700">
                REI severity
                <span className="ml-1 font-normal text-slate-500">
                  (your judgment of the disruption; the source&rsquo;s own rating stays separate)
                </span>
              </legend>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                {SEVERITY_CHOICES.map((choice) => (
                  <label
                    key={choice.value}
                    className="flex cursor-pointer items-center gap-1 text-xs text-slate-700"
                    title={choice.meaning}
                  >
                    <input
                      type="radio"
                      name={`rei-severity-${event.id}`}
                      value={choice.value}
                      checked={severity === choice.value}
                      onChange={() => setSeverity(choice.value)}
                      disabled={pending !== null || savingSeverity}
                      className="h-3.5 w-3.5 accent-brand-600"
                    />
                    {choice.label}
                  </label>
                ))}
                {severityToSave(severity, savedSeverity) && (
                  <button
                    type="button"
                    disabled={pending !== null || savingSeverity}
                    onClick={saveSeverity}
                    className={`cursor-pointer rounded-lg px-2.5 py-1 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES.neutral}`}
                  >
                    {savingSeverity ? "Saving…" : "Save severity"}
                  </button>
                )}
              </div>
              {assessment && (
                <p className="mt-1 text-[11px] text-slate-500">
                  Set to {assessment.severity.toLowerCase()} by {assessment.assessedBy} on{" "}
                  {formatDateTime(assessment.assessedAt, timeZoneOf(event.city, event.source.id)) ?? assessment.assessedAt}{" "}
                  (version {assessment.version}){assessment.reason && <>: &ldquo;{assessment.reason}&rdquo;</>}.
                </p>
              )}
              {!assessment && severity === null && (
                <p className="mt-1 text-[11px] text-slate-500">Not assessed yet. Choose one before approving.</p>
              )}
            </fieldset>
          )}
          <div className="mt-2.5 flex flex-wrap gap-2">
            {approval.offered && (
              <button
                type="button"
                disabled={pending !== null || !approval.enabled}
                title={approval.enabled ? "Approve this event in QC" : "Approval is blocked; see the reasons above"}
                onClick={() =>
                  apply({ to: "APPROVED", label: "Approve", reason: QC_APPROVE_REASON, tone: "primary" })
                }
                className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES.primary}`}
              >
                {pending === "APPROVED" ? "Saving…" : "Approve"}
              </button>
            )}
            {review?.actions.map((action) => (
              <button
                key={action.to}
                type="button"
                disabled={pending !== null}
                onClick={() => apply(action)}
                className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES[action.tone]}`}
              >
                {pending === action.to ? "Saving…" : action.label}
              </button>
            ))}
            {canCorrect &&
              (
                [
                  ["period", "Extend end date"],
                  ["location", "Correct location"],
                ] as const
              ).map(([form, label]) => (
                <button
                  key={form}
                  type="button"
                  disabled={pending !== null}
                  onClick={() => {
                    setEditing(form);
                    setNotice(null);
                  }}
                  className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${TONE_CLASSES.neutral}`}
                >
                  {label}
                </button>
              ))}
          </div>
        </>
      )}
      {notice && (
        <p role="status" className="mt-2 text-xs font-medium text-emerald-700">
          {notice}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {error}
        </p>
      )}
      </div>
    </div>
  );
}
