import { useEffect, useRef } from "react";
import { revealInScroller } from "@/lib/reveal";
import { getTimeState, type TimeState } from "../filters";
import { isManualEntry, type RoadEvent } from "../model";
import {
  formatConfidence,
  formatDateTime,
  formatEventPeriod,
  getEventTypeColor,
  isWholeDayPeriod,
  offMapNote,
  timeZoneOf,
} from "../presentation";
import {
  AttributionBadge,
  EventTypeLabel,
  GisPendingBadge,
  SeverityIndicator,
  SourceBadge,
  StatusBadge,
} from "./EventBadges";

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

  return (
    <li>
      <button
        ref={ref}
        type="button"
        onClick={() => onSelect(event.id)}
        aria-pressed={isSelected}
        className={`relative w-full cursor-pointer rounded-xl bg-white p-3 pl-4 text-left outline-none transition focus-visible:ring-2 focus-visible:ring-white ${
          isSelected
            ? "shadow-lg ring-[3px] ring-sky-300"
            : "opacity-95 shadow-sm hover:opacity-100 hover:shadow-md"
        }`}
      >
        <span
          className="absolute inset-y-3 left-1.5 w-[3px] rounded-full"
          style={{ backgroundColor: getEventTypeColor(event.eventType) }}
          aria-hidden="true"
        />
        <span className="flex items-start justify-between gap-2">
          <span
            className="line-clamp-2 text-sm font-semibold leading-5 text-slate-900"
            title={event.title}
          >
            {event.title}
          </span>
          <StatusBadge status={event.status} />
        </span>
        <span
          className={`mt-0.5 block truncate text-xs ${
            place ? "text-slate-500" : "italic text-slate-400"
          }`}
        >
          {place ?? "Road not identified yet"}
        </span>
        <span className="mt-2 flex items-center justify-between gap-2">
          <EventTypeLabel eventType={event.eventType} />
          {event.severity && <SeverityIndicator severity={event.severity} />}
        </span>
        <span className="mt-1.5 block text-[11px] text-slate-400">{getTimeLine(event, now)}</span>
        {!event.mapEligible && (
          <span className="mt-1 block text-[11px] font-medium text-amber-700">
            {offMapNote(event.offMapReason)}
          </span>
        )}
        {matchedInArticle && (
          <span className="mt-1.5 block text-[11px] font-medium text-brand-600">
            Search matched the article text
          </span>
        )}
        <span className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-2">
          <SourceBadge event={event} />
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
          {!event.geometry && <GisPendingBadge />}
          {attributedTo.length > 0 && <AttributionBadge authorities={attributedTo} />}
          <span className="ml-auto text-[11px] text-slate-400">
            Confidence{" "}
            <span className={confidence ? "font-semibold text-slate-600" : ""}>
              {confidence ?? "not assessed"}
            </span>
          </span>
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

export type EventListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      events: RoadEvent[];
      now: Date;
      isFiltered: boolean;
    };

interface EventListProps {
  state: EventListState;
  selectedEventId: string | null;
  /** Events the search found only through their article text. */
  articleMatchIds: ReadonlySet<string>;
  onSelect: (eventId: string) => void;
  onClearFilters: () => void;
  onRetry: () => void;
  /** The selected city, named in the empty-list message. */
  cityName?: string;
}

export default function EventList({
  state,
  selectedEventId,
  articleMatchIds,
  onSelect,
  onClearFilters,
  onRetry,
  cityName = "Hyderabad",
}: EventListProps) {
  if (state.status === "loading") {
    return (
      <ul className="space-y-2" aria-busy="true" aria-label="Loading events">
        {[0, 1, 2, 3].map((i) => (
          <li key={i} className="animate-pulse rounded-xl bg-white/10 p-3">
            <div className="h-4 w-2/3 rounded bg-white/25" />
            <div className="mt-2 h-3 w-1/2 rounded bg-white/15" />
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
    return state.isFiltered ? (
      <ListMessage title="No events match your filters">
        <p>Try a different search term or loosen the filters.</p>
        <button type="button" onClick={onClearFilters} className={linkButtonClass}>
          Clear filters
        </button>
      </ListMessage>
    ) : (
      <ListMessage title="No current events">
        <p>
          Upcoming and ongoing events appear here when a connected source reports them for{" "}
          {cityName}. Completed ones are not shown.
        </p>
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
