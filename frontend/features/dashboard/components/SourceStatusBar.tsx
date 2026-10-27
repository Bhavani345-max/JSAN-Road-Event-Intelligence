import { useState } from "react";
import type { EventListView } from "@/features/events/filters";
import { formatDateTime, timeZoneOf } from "@/features/events/presentation";
import {
  checkFailureMessage,
  checkSourcesNow,
  groupSources,
  sourceCounts,
  type IngestionOutcome,
  type RegistrySource,
  type SourceStatus,
} from "../sources";

interface SourceStatusBarProps {
  sources: RegistrySource[];
  /** The view on screen: each source says how many of its events this view's map shows. */
  view: EventListView;
  /** Called after sources have been checked, so events and sources can reload. */
  onChecked: () => void;
  /** Whether this account may run sources by hand (admins only); else no Check buttons. */
  canRun?: boolean;
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`;

// How each state looks; the words come from the API (status_label).
const LOOK: Record<SourceStatus, { dot: string; text: string }> = {
  COLLECTING: { dot: "bg-emerald-400", text: "text-emerald-200" },
  NO_RECENT_EVENTS: { dot: "bg-sky-300", text: "text-sky-100" },
  FAILING: { dot: "bg-red-400", text: "text-red-200" },
  NOT_POLLED_YET: { dot: "bg-white/40", text: "text-brand-200" },
  NOT_SCHEDULED: { dot: "bg-white/30", text: "text-brand-200" },
  DISABLED: { dot: "bg-amber-300", text: "text-amber-100" },
  AWAITING_PERMISSION: { dot: "bg-amber-300", text: "text-amber-100" },
  NEEDS_CREDENTIALS: { dot: "bg-amber-300/70", text: "text-amber-100" },
  BLOCKED_BY_TERMS: { dot: "bg-rose-300", text: "text-rose-100" },
  BLOCKED: { dot: "bg-rose-300/70", text: "text-rose-100" },
  REMOVED: { dot: "bg-white/20", text: "text-brand-200" },
  RESEARCHED: { dot: "bg-white/20", text: "text-brand-200" },
  MANUAL_ONLY: { dot: "bg-white/20", text: "text-brand-200" },
};
const UNKNOWN_LOOK = { dot: "bg-white/20", text: "text-brand-200" };

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
      setMessage({ text: checkFailureMessage(cause), isError: true });
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

/**
 * What a source has given, in its own words: polls and real event counts.
 * "On this map" is the view's map only: events awaiting review on the
 * review queue's, validated ones on the operations map (decision 0035).
 */
function activity(source: RegistrySource, zone: string, view: EventListView): string {
  const parts: string[] = [];
  const lastSuccess = formatDateTime(source.lastSuccessAt, zone);
  if (source.checkable) {
    parts.push(lastSuccess ? `Last success ${lastSuccess}` : "No successful poll yet");
  }
  parts.push(...sourceCounts(source, view));
  if (!source.checkable && source.articleCount) parts.push(`${plural(source.articleCount, "item")} kept as evidence`);
  return parts.join(" · ");
}

function SourceRow({
  source,
  view,
  onChecked,
  canRun,
}: {
  source: RegistrySource;
  view: EventListView;
  onChecked: () => void;
  canRun: boolean;
}) {
  const { checking, message, check } = useCheck(source.id, onChecked);
  const look = LOOK[source.status] ?? UNKNOWN_LOOK;
  // In the source's own city's time zone.
  const zone = timeZoneOf(source.city, source.id);
  const details = activity(source, zone, view);
  // Collecting needs no explanation; every other state says why.
  const reason = source.status === "COLLECTING" ? null : source.statusReason;

  return (
    <li>
      <div className="flex items-center gap-2.5">
        <span className={`h-2 w-2 shrink-0 rounded-full ${look.dot}`} aria-hidden="true" />
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
          </p>
          <p className={`text-[11px] font-medium ${look.text}`}>{source.statusLabel}</p>
          {details && <p className="truncate text-[11px] text-brand-200">{details}</p>}
        </div>
        {canRun && source.checkable && (
          <button type="button" onClick={check} disabled={checking} className={buttonClass}>
            {checking ? "Checking…" : "Check"}
          </button>
        )}
      </div>
      <div className="pl-[18px]">
        {/* A fresh result replaces the stored reason. */}
        {message ? (
          <StatusMessage message={message} />
        ) : (
          reason && (
            <p
              role={source.status === "FAILING" ? "status" : undefined}
              className={`text-[11px] ${source.status === "FAILING" ? "text-red-200" : "text-brand-200"}`}
            >
              {reason}
            </p>
          )
        )}
      </div>
    </li>
  );
}

/** Every source in the registry, grouped by state, with checks for connected ones. */
export default function SourceStatusBar({ sources, view, onChecked, canRun = true }: SourceStatusBarProps) {
  // Folded to its summary line, so the console fits one screen; opened on request.
  const [expanded, setExpanded] = useState(false);
  // Only the polled group opens by itself; the others on request.
  const [openGroups, setOpenGroups] = useState<ReadonlySet<string>>(new Set(["polled"]));
  const all = useCheck(undefined, onChecked);
  if (sources.length === 0) return null;

  const groups = groupSources(sources);
  const polled = sources.filter((source) => source.polled);
  const failing = polled.filter((source) => source.status === "FAILING").length;
  const collecting = polled.filter((source) => source.status === "COLLECTING").length;
  const summary =
    failing > 0
      ? `${failing} of ${polled.length} polled failing`
      : polled.length === 0
        ? "none polled here"
        : `${collecting} of ${polled.length} polled collecting`;

  const toggle = (key: string) =>
    setOpenGroups((open) => {
      const next = new Set(open);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

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
          <Chevron open={expanded} />
          <span className="truncate">
            {plural(sources.length, "source")}
            <span className={`ml-1.5 font-medium ${failing > 0 ? "text-red-200" : "text-emerald-200"}`}>
              · {summary}
            </span>
          </span>
        </button>
        {canRun && polled.length > 0 && (
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
        <div className="rei-sidebar-scroll mt-2 max-h-[14rem] space-y-2 overflow-y-auto border-t border-white/10 pt-2 pr-1">
          {groups.map((group) => {
            const open = openGroups.has(group.key);
            return (
              <div key={group.key}>
                <button
                  type="button"
                  onClick={() => toggle(group.key)}
                  aria-expanded={open}
                  className="flex w-full cursor-pointer items-center gap-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-brand-100 outline-none focus-visible:underline"
                >
                  <Chevron open={open} />
                  {group.label} ({group.sources.length})
                </button>
                {open && (
                  <ul className="mt-1.5 space-y-2">
                    {group.sources.map((source) => (
                      <SourceRow
                        key={source.id}
                        source={source}
                        view={view}
                        onChecked={onChecked}
                        canRun={canRun}
                      />
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className={`h-3 w-3 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
      aria-hidden="true"
    >
      <path d="m4 2 4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
