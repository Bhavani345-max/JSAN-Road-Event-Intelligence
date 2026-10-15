import { useState } from "react";
import { formatDateTime, timeZoneOf } from "@/features/events/presentation";
import {
  checkSourcesNow,
  type ConnectedSource,
  type IngestionOutcome,
  type SourceHealth,
} from "../sources";

interface SourceStatusBarProps {
  sources: ConnectedSource[];
  /** Called after sources have been checked, so events and sources can reload. */
  onChecked: () => void;
  /** Whether this account may run sources by hand (admins only); else no Check buttons. */
  canRun?: boolean;
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`;

const HEALTH: Record<SourceHealth, { label: string; dot: string; text: string }> = {
  healthy: { label: "Healthy", dot: "bg-emerald-400", text: "text-emerald-200" },
  failing: { label: "Failing", dot: "bg-red-400", text: "text-red-200" },
  "not-checked": { label: "Not checked yet", dot: "bg-white/40", text: "text-brand-200" },
  // Connected but not on a schedule: the test cities' official feeds.
  inactive: { label: "Run by hand", dot: "bg-white/30", text: "text-brand-200" },
};

type Message = { text: string; isError: boolean };

function describe(outcome: IngestionOutcome): Message {
  if (outcome.failures.length > 0) {
    return {
      text: outcome.failures.map((failure) => `${failure.sourceId}: ${failure.error}`).join(" · "),
      isError: true,
    };
  }
  const revised =
    outcome.revised > 0 ? ` ${plural(outcome.revised, "record")} revised by the source.` : "";
  return {
    text:
      (outcome.newArticles === 0
        ? "No new articles since the last check."
        : `${plural(outcome.newArticles, "new article")}, ${plural(outcome.newEvents, "new event")} to review.`) +
      revised,
    isError: false,
  };
}

/** Runs a check and reports the result; shared by "Check all" and each row. */
function useCheck(sourceId: string | undefined, onChecked: () => void) {
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<Message | null>(null);

  async function check() {
    setChecking(true);
    setMessage(null);
    try {
      setMessage(describe(await checkSourcesNow(sourceId)));
      onChecked();
    } catch (cause) {
      setMessage({
        text: cause instanceof Error ? cause.message : "The sources could not be checked.",
        isError: true,
      });
    } finally {
      setChecking(false);
    }
  }
  return { checking, message, check };
}

const buttonClass =
  "shrink-0 cursor-pointer rounded-lg bg-white/15 px-2.5 py-1 text-[11px] font-semibold text-white ring-1 ring-inset ring-white/25 transition hover:bg-white/25 disabled:cursor-wait disabled:opacity-60";

function StatusMessage({ message }: { message: Message }) {
  return (
    <p role="status" className={`text-[11px] ${message.isError ? "text-red-200" : "text-emerald-200"}`}>
      {message.text}
    </p>
  );
}

function SourceRow({
  source,
  onChecked,
  canRun,
}: {
  source: ConnectedSource;
  onChecked: () => void;
  canRun: boolean;
}) {
  const { checking, message, check } = useCheck(source.id, onChecked);
  const health = HEALTH[source.health];
  // In the source's own city's time zone.
  const zone = timeZoneOf(source.city, source.id);
  const lastSuccess = formatDateTime(source.lastSuccessAt, zone);
  const lastFailure = formatDateTime(source.lastFailureAt, zone);

  return (
    <li>
      <div className="flex items-center gap-2.5">
        <span className={`h-2 w-2 shrink-0 rounded-full ${health.dot}`} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-white">
            <span className="truncate">{source.name}</span>
            <span className="rounded bg-white/15 px-1 py-px text-[10px] font-medium text-brand-100">
              {source.type}
            </span>
            {source.sourceClass === "AUTHORITATIVE_OFFICIAL" && (
              <span
                className="rounded bg-emerald-400/20 px-1 py-px text-[10px] font-semibold text-emerald-100"
                title="An official source: the road or transport authority itself (tier 1)"
              >
                Official
              </span>
            )}
            <span className={`text-[11px] font-medium ${health.text}`}>{health.label}</span>
          </p>
          <p className="truncate text-[11px] text-brand-200">
            {lastSuccess ? `Last success ${lastSuccess}` : "No successful check yet"} ·{" "}
            {plural(source.articleCount, "article")} · {plural(source.candidateCount, "candidate")}
          </p>
        </div>
        {canRun && (
          <button type="button" onClick={check} disabled={checking} className={buttonClass}>
            {checking ? "Checking…" : "Check"}
          </button>
        )}
      </div>
      <div className="pl-[18px]">
        {/* A fresh result replaces the stored failure message. */}
        {message ? (
          <StatusMessage message={message} />
        ) : (
          source.lastError && (
            <p role="status" className="text-[11px] text-red-200">
              Last failure{lastFailure ? ` ${lastFailure}` : ""}: {source.lastError}
            </p>
          )
        )}
      </div>
    </li>
  );
}

/** Health of each connected source feeding the console, with manual checks. */
export default function SourceStatusBar({ sources, onChecked, canRun = true }: SourceStatusBarProps) {
  const [expanded, setExpanded] = useState(true);
  const all = useCheck(undefined, onChecked);
  if (sources.length === 0) return null;

  const failing = sources.filter((source) => source.health === "failing").length;
  // Sources run by hand are not part of "all healthy": nothing polls them.
  const scheduled = sources.filter((source) => source.health !== "inactive");
  const summary =
    failing > 0
      ? `${failing} of ${sources.length} failing`
      : scheduled.length === 0
        ? "run by hand"
        : scheduled.every((source) => source.health === "healthy")
          ? "all healthy"
          : "checking";

  return (
    <section
      aria-label="Data sources"
      className="rounded-lg bg-black/15 px-3 py-2 ring-1 ring-inset ring-white/10"
    >
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-1.5 text-left text-xs font-semibold text-white outline-none focus-visible:underline"
        >
          <svg
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className={`h-3 w-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
            aria-hidden="true"
          >
            <path d="m4 2 4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="truncate">
            {plural(sources.length, "source")} connected
            <span className={`ml-1.5 font-medium ${failing > 0 ? "text-red-200" : "text-emerald-200"}`}>
              · {summary}
            </span>
          </span>
        </button>
        {canRun && (
          <button type="button" onClick={all.check} disabled={all.checking} className={buttonClass}>
            {all.checking ? "Checking…" : "Check all"}
          </button>
        )}
      </div>
      {all.message && (
        <div className="mt-1 pl-[18px]">
          <StatusMessage message={all.message} />
        </div>
      )}
      {expanded && (
        <ul className="rei-sidebar-scroll mt-2 max-h-[8.75rem] space-y-2 overflow-y-auto border-t border-white/10 pt-2 pr-1">
          {sources.map((source) => (
            <SourceRow key={source.id} source={source} onChecked={onChecked} canRun={canRun} />
          ))}
        </ul>
      )}
    </section>
  );
}
