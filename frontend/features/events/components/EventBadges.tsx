import {
  EVENT_SEVERITIES,
  type EventSeverity,
  type EventStatus,
  type EventType,
  type RoadEvent,
} from "../model";
import {
  getEventTypeColor,
  getEventTypeLabel,
  getSeverityLabel,
  getStatusLabel,
  getStatusPhase,
  type GisStatus,
  type StatusPhase,
} from "../presentation";

const BADGE_BASE =
  "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset whitespace-nowrap";

const PHASE_CLASSES: Record<StatusPhase, { badge: string; dot: string }> = {
  pending: { badge: "bg-slate-100 text-slate-600 ring-slate-200", dot: "bg-slate-400" },
  upcoming: { badge: "bg-indigo-50 text-indigo-700 ring-indigo-200", dot: "bg-indigo-500" },
  live: { badge: "bg-emerald-50 text-emerald-700 ring-emerald-200", dot: "bg-emerald-500" },
  watch: { badge: "bg-amber-50 text-amber-700 ring-amber-200", dot: "bg-amber-500" },
  closed: { badge: "bg-slate-50 text-slate-400 ring-slate-200", dot: "bg-slate-300" },
};

export function StatusBadge({ status }: { status: EventStatus }) {
  const classes = PHASE_CLASSES[getStatusPhase(status)];
  return (
    <span className={`${BADGE_BASE} ${classes.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${classes.dot}`} />
      {getStatusLabel(status)}
    </span>
  );
}

const SEVERITY_CLASSES: Record<EventSeverity, { text: string; bar: string }> = {
  LOW: { text: "text-slate-600", bar: "bg-slate-400" },
  MEDIUM: { text: "text-amber-700", bar: "bg-amber-500" },
  HIGH: { text: "text-orange-700", bar: "bg-orange-500" },
  CRITICAL: { text: "text-red-700", bar: "bg-red-600" },
};

/** Severity as a label plus a four-step meter. */
export function SeverityIndicator({ severity }: { severity: EventSeverity }) {
  const level = EVENT_SEVERITIES.indexOf(severity);
  const classes = SEVERITY_CLASSES[severity];
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] font-medium ${classes.text}`}
    >
      <span className="flex items-end gap-0.5" aria-hidden="true">
        {EVENT_SEVERITIES.map((step, index) => (
          <span
            key={step}
            className={`w-[3px] rounded-sm ${index <= level ? classes.bar : "bg-slate-200"}`}
            style={{ height: 4 + index * 2 }}
          />
        ))}
      </span>
      {getSeverityLabel(severity)}
    </span>
  );
}

export function EventTypeLabel({ eventType }: { eventType: EventType | null }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${
        eventType ? "text-slate-600" : "text-slate-400"
      }`}
    >
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: getEventTypeColor(eventType) }}
      />
      {getEventTypeLabel(eventType)}
    </span>
  );
}

/** The source an event was created from. `className` may cap its width: a long name is cut with "…". */
export function SourceBadge({ event, className = "" }: { event: RoadEvent; className?: string }) {
  return (
    <span
      className={`${BADGE_BASE} bg-brand-50 font-semibold text-brand-700 ring-brand-200 ${className}`}
      title={`Source: ${event.source.name}`}
    >
      <svg viewBox="0 0 16 16" fill="currentColor" className="h-2.5 w-2.5 shrink-0" aria-hidden="true">
        <circle cx="3.5" cy="12.5" r="1.8" />
        <path d="M2 6.2v2.3A5.5 5.5 0 0 1 7.5 14h2.3A7.8 7.8 0 0 0 2 6.2Z" />
        <path d="M2 1.7V4a10 10 0 0 1 10 10h2.3A12.3 12.3 0 0 0 2 1.7Z" />
      </svg>
      <span className="min-w-0 truncate">{event.source.name}</span>
    </span>
  );
}

/** The authority the article says announced the measure. */
export function AttributionBadge({ authorities }: { authorities: string[] }) {
  return (
    <span
      className={`${BADGE_BASE} bg-emerald-50 text-emerald-700 ring-emerald-200`}
      title={`The article attributes this to ${authorities.join(", ")}. It is a news report of the announcement, not the announcement itself.`}
    >
      Cites {authorities[0]}
    </span>
  );
}

const GIS_TONE_CLASSES: Record<GisStatus["tone"], string> = {
  exact: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  approximate: "bg-amber-50 text-amber-700 ring-amber-200",
  pending: "bg-sky-50 text-sky-700 ring-sky-200",
  none: "bg-white text-slate-500 ring-slate-300",
};

/** Where an event stands with its location: how it was placed, a match awaiting review, or not located. */
export function GisStatusBadge({ status }: { status: GisStatus }) {
  return (
    <span className={`${BADGE_BASE} ${GIS_TONE_CLASSES[status.tone]}`} title={status.meaning}>
      <svg
        viewBox="0 0 16 16"
        fill={status.tone === "exact" ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.5"
        className="h-2.5 w-2.5"
        aria-hidden="true"
      >
        <path d="M8 14.5s4.5-4 4.5-7.6A4.5 4.5 0 0 0 3.5 6.9c0 3.6 4.5 7.6 4.5 7.6Z" />
        {status.tone === "none" && <path d="m2 1.5 12 13" strokeLinecap="round" />}
      </svg>
      <span className="sr-only">Location: </span>
      {status.label}
    </span>
  );
}
