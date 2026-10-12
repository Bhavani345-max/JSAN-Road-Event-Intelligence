import { useState } from "react";
import type { MergeCandidate } from "@/features/events/model";
import { confirmAllMerges, confirmMerge, rejectMerge } from "../api";

/** The candidate id the "merge all" decision is pending under. */
const ALL = -1;

interface MergeCandidatesProps {
  candidates: MergeCandidate[];
  /** Called once a decision is saved; the caller reloads. */
  onDecided: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  start_time: "start",
  end_time: "end",
  geometry: "location",
  direction: "direction",
  event_type: "type",
  source_status: "status",
};

/**
 * Events that may be the same as this one. Nothing is merged until a
 * reviewer says so; where the sources disagree, that is shown first.
 */
export default function MergeCandidates({ candidates, onDecided }: MergeCandidatesProps) {
  const [pending, setPending] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (candidates.length === 0) return null;

  async function decide(candidate: MergeCandidate, same: boolean) {
    setPending(candidate.candidateId);
    setError(null);
    try {
      if (same) {
        await confirmMerge(candidate.candidateId, "Reviewer confirmed: the same real-world event");
      } else {
        await rejectMerge(candidate.candidateId, "Reviewer decided: different events");
      }
      onDecided();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The decision could not be saved.");
    } finally {
      setPending(null);
    }
  }

  async function mergeAll() {
    setPending(ALL);
    setError(null);
    try {
      await confirmAllMerges(
        candidates.map((c) => c.candidateId),
        "Reviewer confirmed: all these reports are the same real-world event",
      );
      onDecided();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The decision could not be saved.");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="mb-3 space-y-2">
      {candidates.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-amber-50 p-2.5 text-xs ring-1 ring-inset ring-amber-200">
          <p className="min-w-0 flex-1 text-slate-700">
            <span className="font-semibold">{candidates.length} other reports</span> may be this same
            event. Check them below, then decide once, or one by one.
          </p>
          <button
            type="button"
            disabled={pending !== null}
            onClick={mergeAll}
            className="h-7 cursor-pointer rounded-md bg-brand-600 px-2.5 text-[11px] font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {pending === ALL ? "Merging…" : `All ${candidates.length + 1} are the same: merge all`}
          </button>
        </div>
      )}
      {candidates.map((candidate) => (
        <div
          key={candidate.candidateId}
          className="rounded-lg bg-white p-2.5 text-xs ring-1 ring-inset ring-amber-200"
        >
          <p className="font-semibold text-slate-700">
            {candidate.classification === "SAME" ? "Probably the same event as" : "Possibly the same event as"}
          </p>
          <p className="mt-0.5 text-slate-600">
            &ldquo;{candidate.otherTitle}&rdquo;{" "}
            <span className="text-slate-400">({candidate.otherSourceName})</span>
          </p>
          {candidate.reasons.length > 0 && (
            <p className="mt-1 text-[11px] text-slate-500">{candidate.reasons.join("; ")}.</p>
          )}
          {candidate.conflicts.length > 0 && (
            <p className="mt-1 text-[11px] font-medium text-amber-700">
              The sources disagree on{" "}
              {candidate.conflicts.map((c) => FIELD_LABELS[c.field] ?? c.field).join(", ")}. Merging keeps
              both values.
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            <button
              type="button"
              disabled={pending !== null}
              onClick={() => decide(candidate, true)}
              className="h-7 cursor-pointer rounded-md bg-brand-600 px-2.5 text-[11px] font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Same event: merge
            </button>
            <button
              type="button"
              disabled={pending !== null}
              onClick={() => decide(candidate, false)}
              className="h-7 cursor-pointer rounded-md bg-white px-2.5 text-[11px] font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
            >
              Different events
            </button>
          </div>
        </div>
      ))}
      {error && <p className="text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
