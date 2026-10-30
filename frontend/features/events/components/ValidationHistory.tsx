import { useEffect, useState } from "react";
import { fetchEventHistory } from "../api/eventRepository";
import { historyStages, type HistoryStage } from "../history";
import { formatDateTime, getStatusLabel } from "../presentation";

/** REI's own processes as a reader knows them; a reviewer is shown by their account. */
const PROCESS_NAMES: Record<string, string> = {
  ingestion: "REI ingestion",
  "source-update": "the source's update",
  reprocessing: "REI reprocessing",
  "ai-reading": "AI reading",
  "auto-merge": "automatic matching",
};

const KIND_DOT: Record<HistoryStage["kind"], string> = {
  detected: "bg-slate-400",
  review: "bg-amber-500",
  validated: "bg-emerald-500",
  rejected: "bg-red-500",
  closed: "bg-slate-500",
  change: "bg-sky-500",
};

// Long histories (official feeds revise often): the first steps and the latest.
const HEAD = 3;
const TAIL = 12;

type Loaded = { key: string; stages: HistoryStage[] } | { key: string; error: string };

/**
 * The event's validation history from its recorded versions (GET /events/{id},
 * read only): detection, review decisions, corrections, source updates. Loaded
 * again when the event changes version.
 */
export default function ValidationHistory({
  eventId,
  version,
  zone,
}: {
  eventId: string;
  version: number;
  zone: string;
}) {
  const key = `${eventId}@${version}`;
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchEventHistory(eventId)
      .then((versions) => {
        if (!cancelled) setLoaded({ key, stages: historyStages(versions) });
      })
      .catch((cause: unknown) => {
        if (!cancelled)
          setLoaded({ key, error: cause instanceof Error ? cause.message : "The history could not be loaded." });
      });
    return () => {
      cancelled = true;
    };
  }, [eventId, key, attempt]);

  if (!loaded || loaded.key !== key) {
    return (
      <ul className="space-y-2" aria-busy="true" aria-label="Loading the history">
        {[0, 1, 2].map((i) => (
          <li key={i} className="h-8 animate-pulse rounded-md bg-slate-100" />
        ))}
      </ul>
    );
  }
  if ("error" in loaded) {
    return (
      <p className="text-xs text-slate-500">
        The history could not be loaded: {loaded.error}{" "}
        <button
          type="button"
          onClick={() => setAttempt((n) => n + 1)}
          className="cursor-pointer font-semibold text-brand-600 hover:underline"
        >
          Try again
        </button>
      </p>
    );
  }

  const { stages } = loaded;
  const hidden = !showAll && stages.length > HEAD + TAIL ? stages.length - HEAD - TAIL : 0;
  const shown = hidden ? [...stages.slice(0, HEAD), ...stages.slice(-TAIL)] : stages;
  return (
    <>
      <ol className="relative space-y-3 pl-4 before:absolute before:inset-y-1 before:left-[3px] before:w-px before:bg-slate-200">
        {shown.map((stage, index) => (
          <li key={stage.version} className="relative">
            <span
              className={`absolute -left-4 top-1 h-[7px] w-[7px] rounded-full ring-2 ring-white ${KIND_DOT[stage.kind]}`}
              aria-hidden="true"
            />
            {hidden > 0 && index === HEAD && (
              <button
                type="button"
                onClick={() => setShowAll(true)}
                className="mb-3 cursor-pointer text-[11px] font-semibold text-brand-600 hover:underline"
              >
                Show {hidden} more updates
              </button>
            )}
            <p className="flex flex-wrap items-baseline gap-x-2 text-xs">
              <span className="font-semibold text-slate-800">{stage.label}</span>
              <span className="text-slate-400">{getStatusLabel(stage.status)}</span>
            </p>
            <p className="text-[11px] text-slate-500">
              {formatDateTime(stage.at, zone)} · by {PROCESS_NAMES[stage.changedBy] ?? stage.changedBy} · version{" "}
              {stage.version}
            </p>
            {stage.reason && (
              <p className="mt-0.5 line-clamp-3 text-[11px] leading-relaxed text-slate-500" title={stage.reason}>
                {stage.reason}
              </p>
            )}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-slate-400">
        Every step is a version REI recorded. REI records no separate &ldquo;published&rdquo; step.
      </p>
    </>
  );
}
