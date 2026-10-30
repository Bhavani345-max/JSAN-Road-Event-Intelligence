import { useEffect, useRef } from "react";
import { revealInScroller } from "@/lib/reveal";
import { getTimeState, type TimeState } from "../filters";
import { isManualEntry, isSourceProvided, type RoadEvent } from "../model";
import {
  formatConfidence,
  formatDateTime,
  formatEventPeriod,
  formatShortDate,
  getEventTypeColor,
  gisStatus,
  isWholeDayPeriod,
  offMapNote,
  timeZoneOf,
} from "../presentation";
import {
  AttributionBadge,
  EventTypeLabel,
  GisStatusBadge,
  SeverityIndicator,
  SourceBadge,
  StatusBadge,
} from "./EventBadges";
import EventThumbnail from "./EventThumbnail";

interface EventListItemProps {
  event: RoadEvent;
  isSelected: boolean;
  /** The search matched the article's text rather than anything shown on the card. */
  matchedInArticle: boolean;
  /** When the events were loaded; decides what is upcoming, ongoing or ended. */
  now: Date;
  onSelect: (eventId: string) => void;
}

const TIME_STATE_LABELS: Record<TimeState, string> = {
  upcoming: "Upcoming",
  ongoing: "Ongoing",
  ended: "Ended",
};

/** When the event happens; or, if the source gave no times, when it was reported. */
function getTimeLine(event: RoadEvent, now: Date): string {
  // Each event's times are shown in its own city's zone.
  const zone = timeZoneOf(event.city, event.source.id);
  const state = getTimeState(event, now);
  if (state) {
    const wholeDays = isWholeDayPeriod(event.startTime, event.endTime, zone);
    const { start, end } = formatEventPeriod(event.startTime, event.endTime, wholeDays, zone);
    // An event with an end but no stated start: only the end is known.
    const period = event.startTime ? `${start} → ${end}` : `until ${end}`;
    return `${TIME_STATE_LABELS[state]} · ${period}`;
  }
  if (isManualEntry(event)) {
    const added = formatDateTime(event.evidence?.retrievedAt ?? null, zone);
    return added ? `Added ${added} · event time not given` : "Event time not given";
  }
  const published = formatDateTime(event.evidence?.publishedAt ?? null, zone);
  return published ? `Reported ${published} · event time not available` : "Event time not available";
}

/**
 * When the source published its report (news) or last updated its record
 * (official feeds), as a short date with the full time on hover. Null when the
 * time line already says it ("Reported …", "Added …").
 */
function getPublishedLine(event: RoadEvent, now: Date): { text: string; title: string } | null {
  if (isManualEntry(event) || !getTimeState(event, now)) return null;
  const zone = timeZoneOf(event.city, event.source.id);
  const at = event.evidence?.publishedAt ?? null;
  const date = formatShortDate(at, now, zone);
  if (!date) return null;
  const verb = isSourceProvided(event) ? "Updated" : "Published";
  return { text: `${verb} ${date}`, title: `${verb} by ${event.source.name}: ${formatDateTime(at, zone)}` };
}

function EventListItem({
  event,
  isSelected,
  matchedInArticle,
  now,
  onSelect,
}: EventListItemProps) {
  const ref = useRef<HTMLButtonElement>(null);

  // Keep the selected row visible when the selection was made on the map,
  // scrolling the list only (never the page).
  useEffect(() => {
    if (isSelected && ref.current) revealInScroller(ref.current);
  }, [isSelected]);

  const confidence = formatConfidence(event.confidence);
  const place = event.affectedRoad ?? event.detection?.location?.placeName ?? null;
  const attributedTo = event.detection?.attributedTo ?? [];
  const gis = gisStatus(event);
  const published = getPublishedLine(event, now);
  const where = [event.city, place].filter(Boolean).join(" · ");
  const timeLine = getTimeLine(event, now);

  return (
    <li>
      <button
        ref={ref}
        type="button"
        onClick={() => onSelect(event.id)}
        aria-pressed={isSelected}
        // Hover and selection change only shadows and rings (painted outside the
        // layout), never size or position: the list does not shift.
        className={`rei-event-card group relative w-full cursor-pointer rounded-xl bg-white p-3 pl-4 text-left outline-none transition-shadow duration-150 ease-out focus-visible:ring-2 focus-visible:ring-white ${
          isSelected
            ? "rei-event-card-selected shadow-lg ring-[3px] ring-sky-300"
            : "shadow-[0_1px_2px_rgb(15_23_42/0.08)] ring-1 ring-slate-900/5 hover:shadow-md hover:ring-slate-900/10"
        }`}
      >
        <span
          className="absolute inset-y-3 left-1.5 w-[3px] rounded-full"
          style={{ backgroundColor: getEventTypeColor(event.eventType) }}
          aria-hidden="true"
        />
        <span className="flex items-start gap-3">
          <EventThumbnail event={event} />
          <span className="min-w-0 flex-1">
            <span
              className="line-clamp-2 text-[15px] font-semibold leading-[1.3] tracking-[-0.01em] text-slate-900 group-hover:text-brand-800"
              title={event.title}
            >
              {event.title}
            </span>
            <span className="mt-1 block truncate text-xs text-slate-500" title={where || undefined}>
              {event.city && <span className="font-medium text-slate-600">{event.city}</span>}
              {event.city && " · "}
              {place ?? <span className="italic text-slate-400">Road not identified yet</span>}
            </span>
            <span className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
              <EventTypeLabel eventType={event.eventType} />
              {event.severity && <SeverityIndicator severity={event.severity} />}
              <span className="ml-auto">
                <StatusBadge status={event.status} />
              </span>
            </span>
          </span>
        </span>
        <span className="mt-2.5 block text-[11px] leading-4 text-slate-500" title={timeLine}>
          {timeLine}
        </span>
        {!event.mapEligible && (
          <span className="mt-1 block text-[11px] font-medium leading-4 text-amber-700">
            {offMapNote(event.offMapReason)}
          </span>
        )}
        {matchedInArticle && (
          <span className="mt-1 block text-[11px] font-medium leading-4 text-brand-600">
            Search matched the article text
          </span>
        )}
        <span className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-2">
          <SourceBadge event={event} className="max-w-[9.5rem]" />
          {gis && <GisStatusBadge status={gis} />}
          {event.otherEvidence.length > 0 && (
            <span
              className="inline-flex items-center rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-200"
              title={`Also reported by ${event.otherEvidence.map((o) => o.sourceName).join(", ")}`}
            >
              +{event.otherEvidence.length} {event.otherEvidence.length === 1 ? "source" : "sources"}
            </span>
          )}
          {event.mergeCandidates.length > 0 && (
            <span
              className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200"
              title="May be the same event as another report: a reviewer decides"
            >
              Possible duplicate
            </span>
          )}
          {attributedTo.length > 0 && <AttributionBadge authorities={attributedTo} />}
          {(published || confidence) && (
            <span className="ml-auto flex items-center gap-2 whitespace-nowrap text-[11px] text-slate-400">
              {published && <span title={published.title}>{published.text}</span>}
              {/* Shown once assessed; the details panel says when it is not. */}
              {confidence && (
                <span>
                  Confidence <span className="font-semibold text-slate-600">{confidence}</span>
                </span>
              )}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}

function ListMessage({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <p className="text-sm font-semibold text-white">{title}</p>
      <div className="mt-1 text-sm text-brand-100">{children}</div>
    </div>
  );
}

const linkButtonClass =
  "mt-3 cursor-pointer rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 shadow-sm transition hover:bg-brand-50";

/** What an empty list says: whether filters hide events, or why there are none to list. */
export interface EmptyListMessage {
  title: string;
  lines: string[];
  /** The filters hide the loaded events: offer to clear them. */
  clearFilters: boolean;
}

export type EventListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      events: RoadEvent[];
      now: Date;
      /** Shown when `events` is empty. */
      empty: EmptyListMessage;
    };

interface EventListProps {
  state: EventListState;
  selectedEventId: string | null;
  /** Events the search found only through their article text. */
  articleMatchIds: ReadonlySet<string>;
  onSelect: (eventId: string) => void;
  onClearFilters: () => void;
  onRetry: () => void;
}

export default function EventList({
  state,
  selectedEventId,
  articleMatchIds,
  onSelect,
  onClearFilters,
  onRetry,
}: EventListProps) {
  if (state.status === "loading") {
    return (
      <ul className="space-y-2" aria-busy="true" aria-label="Loading events">
        {[0, 1, 2, 3].map((i) => (
          <li key={i} className="animate-pulse rounded-xl bg-white/10 p-3">
            <div className="flex gap-3">
              <div className="h-16 w-16 shrink-0 rounded-lg bg-white/20" />
              <div className="min-w-0 flex-1">
                <div className="h-4 w-4/5 rounded bg-white/25" />
                <div className="mt-2 h-3 w-1/2 rounded bg-white/15" />
                <div className="mt-3 h-3 w-2/3 rounded bg-white/15" />
              </div>
            </div>
            <div className="mt-3 h-3 w-full rounded bg-white/15" />
          </li>
        ))}
      </ul>
    );
  }

  if (state.status === "error") {
    return (
      <ListMessage title="Events could not be loaded">
        <p>{state.message}</p>
        <button type="button" onClick={onRetry} className={linkButtonClass}>
          Try again
        </button>
      </ListMessage>
    );
  }

  if (state.events.length === 0) {
    const { title, lines, clearFilters } = state.empty;
    return (
      <ListMessage title={title}>
        {lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
        {clearFilters && (
          <button type="button" onClick={onClearFilters} className={linkButtonClass}>
            Clear filters
          </button>
        )}
      </ListMessage>
    );
  }

  return (
    <ul className="space-y-2">
      {state.events.map((event) => (
        <EventListItem
          key={event.id}
          event={event}
          isSelected={event.id === selectedEventId}
          matchedInArticle={articleMatchIds.has(event.id)}
          now={state.now}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}
