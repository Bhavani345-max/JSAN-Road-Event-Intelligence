import { isManualEntry, isSourceProvided, publicEventLocation, REVIEWER_PLACED, type RoadEvent } from "../model";
import {
  describeSourceAuthority,
  DIRECTION_LABELS,
  LOCATION_CLASS_LABELS,
  timeZoneLabel,
  timeZoneOf,
  formatConfidence,
  formatDate,
  formatDateTime,
  formatEventPeriod,
  getEventTypeColor,
  getEventTypeLabel,
  getSiteName,
  googleMapsUrl,
  isWholeDayPeriod,
  streetViewUrl,
} from "../presentation";
import { SeverityIndicator, SourceBadge, StatusBadge } from "./EventBadges";
import AiSection from "./AiSection";
import GisSection from "./GisSection";

interface EventDetailsPanelProps {
  event: RoadEvent;
  onClose: () => void;
  /** Review controls, rendered at the bottom of the panel. */
  footer?: React.ReactNode;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-800">{children}</dd>
    </div>
  );
}

/** Placeholder for a value that is not known. Nothing is ever filled in for it. */
function Unknown({ children }: { children: React.ReactNode }) {
  return <span className="italic text-slate-400">{children}</span>;
}

const NOT_AVAILABLE = <Unknown>Not available</Unknown>;

/**
 * See the place on the ground: Google Street View, and Google Maps for the
 * surroundings, at the event's map point, each in a new tab. A point that is
 * only a named place's position says so, since the panorama may not show the
 * exact spot.
 */
function StreetViewActions({ event }: { event: RoadEvent }) {
  if (event.latitude === null || event.longitude === null) return null;
  const approximate = event.detection?.locationClass === "APPROXIMATE";
  const linkClass =
    "inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1";
  return (
    <div className="px-4 pb-3">
      <div className="flex flex-wrap items-center gap-2">
        <a
          href={streetViewUrl(event.latitude, event.longitude)}
          target="_blank"
          rel="noopener noreferrer"
          className={`${linkClass} bg-brand-600 text-white shadow-sm hover:bg-brand-700`}
          title="Open Google Street View at this event's map point (new tab)"
        >
          {/* A person standing on the street: Street View */}
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
            <circle cx="10" cy="4" r="2.2" />
            <path d="M7.4 7.6a2.6 2.6 0 0 1 5.2 0v3.6a1 1 0 0 1-1 1h-.3l-.4 4.3a.9.9 0 0 1-1.8 0l-.4-4.3h-.3a1 1 0 0 1-1-1V7.6Z" />
            <ellipse cx="10" cy="18" rx="4.5" ry="1" opacity="0.35" />
          </svg>
          Street View
        </a>
        <a
          href={googleMapsUrl(event.latitude, event.longitude)}
          target="_blank"
          rel="noopener noreferrer"
          className={`${linkClass} bg-white text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-slate-50 hover:text-slate-900`}
          title="Open this point on Google Maps (new tab)"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4" aria-hidden="true">
            <path d="M10 17.5s5-4.6 5-8.6a5 5 0 1 0-10 0c0 4 5 8.6 5 8.6Z" strokeLinejoin="round" />
            <circle cx="10" cy="8.8" r="1.8" />
          </svg>
          Google Maps
        </a>
      </div>
      <p className="mt-1.5 text-[11px] leading-4 text-slate-500">
        {approximate
          ? "Opens at the named place's position, which may not be the exact spot of the event."
          : "Opens at the event's map point."}{" "}
        Imagery is Google&apos;s and may be older than the event.
      </p>
    </div>
  );
}

/** Who named the place an event is located by, as a phrase. */
const FOUND_IN_PHRASES: Record<string, string> = {
  title: "named in the article\u2019s headline",
  summary: "named in the article\u2019s summary",
  body: "named in the article\u2019s text",
  entry: "the reviewer named",
};
const NOT_ASSESSED = <Unknown>Not assessed</Unknown>;

/** A conflicting value as a reader understands it. */
function formatConflictValue(value: unknown, zone: string): string {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return formatDateTime(value, zone) ?? value;
  if (value && typeof value === "object" && "coordinates" in value) {
    const coordinates = (value as { coordinates: unknown }).coordinates;
    return Array.isArray(coordinates) && typeof coordinates[0] === "number"
      ? `${(coordinates[1] as number).toFixed(4)}, ${(coordinates[0] as number).toFixed(4)}`
      : "a shape";
  }
  return String(value);
}

/** The source and the stored article the event was derived from. */
function Evidence({ event }: { event: RoadEvent }) {
  const zone = timeZoneOf(event.city, event.source.id);
  const published = formatDateTime(event.evidence?.publishedAt ?? null, zone);
  const retrieved = formatDateTime(event.evidence?.retrievedAt ?? null, zone);
  const keywords = event.detection?.matchedKeywords ?? [];
  const site = getSiteName(event.sourceReference);
  const manual = isManualEntry(event);
  const official = isSourceProvided(event);
  const authority = describeSourceAuthority(event.sourceAuthority);
  return (
    <div className="rounded-lg bg-brand-50/70 p-3 ring-1 ring-inset ring-brand-100">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5">
        <div className="col-span-2">
          <Field label="Source">
            <span className="font-medium">{event.source.name}</span>
            <span className="text-slate-500"> · {event.source.type}</span>
          </Field>
        </div>
        <Field label="Type">{authority.kind}</Field>
        <Field label="Authority">
          <span className={authority.official ? "font-medium text-emerald-700" : undefined}>
            {authority.standing}
          </span>
        </Field>
        {manual ? (
          <>
            <Field label="Entered">{retrieved ?? NOT_AVAILABLE}</Field>
            <div className="col-span-2">
              <Field label="How the reviewer knows">
                {event.detection?.basis ?? NOT_AVAILABLE}
              </Field>
            </div>
          </>
        ) : (
          <>
            <Field label={official ? "Last updated by the source" : "Published"}>
              {published ?? NOT_AVAILABLE}
            </Field>
            <Field label="Retrieved">{retrieved ?? NOT_AVAILABLE}</Field>
          </>
        )}
        {official && (
          <>
            <Field label="Category (source's words)">
              {event.detection?.sourceCategory ?? NOT_AVAILABLE}
            </Field>
            <Field label="Severity as the source states it">
              {event.detection?.sourceSeverity ?? NOT_AVAILABLE}
            </Field>
          </>
        )}
      </dl>
      {event.detection?.sourceRevision && (
        <p className="mt-2.5 text-[11px] leading-relaxed text-slate-600">
          <span className="font-semibold">
            Revised by the source on {formatDateTime(event.detection.sourceRevision.revisedAt, zone)}
          </span>{" "}
          (version {event.detection.sourceRevision.revision}):{" "}
          {event.detection.sourceRevision.changes.join("; ")}.
        </p>
      )}
      {event.detection?.pendingSourceRevision && (
        <p
          role="note"
          className="mt-2.5 rounded-md bg-amber-50 px-2 py-1.5 text-[11px] leading-relaxed text-amber-800 ring-1 ring-inset ring-amber-200"
        >
          <span className="font-semibold">
            The source revised this record after it was decided
          </span>{" "}
          (version {event.detection.pendingSourceRevision.revision},{" "}
          {formatDateTime(event.detection.pendingSourceRevision.revisedAt, zone)}). Not applied:{" "}
          {event.detection.pendingSourceRevision.changes.join("; ")}. A reviewer should look at it.
        </p>
      )}
      {event.otherEvidence.length > 0 && (
        <div className="mt-2.5 border-t border-brand-100 pt-2.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Also reported by {event.otherEvidence.length}{" "}
            {event.otherEvidence.length === 1 ? "source" : "sources"}
          </p>
          <ul className="mt-1 space-y-1.5">
            {event.otherEvidence.map((other) => (
              <li key={other.eventId} className="text-xs leading-snug">
                <span className="font-medium text-slate-700">{other.sourceName}</span>
                <span className="text-slate-400">
                  {other.publishedAt && ` · ${formatDateTime(other.publishedAt, zone)}`}
                  {other.how && ` · merged ${other.how === "automatic" ? "automatically" : "by a reviewer"}`}
                </span>
                {other.url ? (
                  <a
                    href={other.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block truncate text-brand-600 hover:text-brand-800 hover:underline"
                  >
                    {other.title}
                  </a>
                ) : (
                  <span className="block truncate text-slate-500">{other.title}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(event.detection?.mergeConflicts.length ?? 0) > 0 && (
        <div
          role="note"
          className="mt-2.5 rounded-md bg-amber-50 px-2 py-1.5 text-[11px] leading-relaxed text-amber-800 ring-1 ring-inset ring-amber-200"
        >
          <span className="font-semibold">The sources disagree</span>: both values are kept and none was
          chosen automatically.
          <ul className="mt-1 space-y-0.5">
            {event.detection!.mergeConflicts.map((conflict) => (
              <li key={conflict.field}>
                {conflict.field.replace("_time", "").replace("_", " ")}:{" "}
                {conflict.values.map((v) => `${v.sourceId}: ${formatConflictValue(v.value, zone)}`).join(" · ")}
              </li>
            ))}
          </ul>
        </div>
      )}
      {event.detection?.observation?.reviewRequired && (
        <p
          role="note"
          className="mt-2.5 rounded-md bg-amber-50 px-2 py-1.5 text-[11px] leading-relaxed text-amber-800 ring-1 ring-inset ring-amber-200"
        >
          <span className="font-semibold">
            Not listed by the source for {event.detection.observation.missedRefreshes} refreshes
          </span>
          {event.detection.observation.missingSince &&
            ` (since ${formatDateTime(event.detection.observation.missingSince, zone)})`}
          . This does not mean it has ended; a reviewer should check it.
        </p>
      )}
      {event.detection?.sourceReportsEnded && (
        <p className="mt-2.5 text-[11px] font-semibold text-slate-600">
          The source reports this event as cleared or ended.
        </p>
      )}
      {event.detection?.attribution && (
        <p className="mt-2.5 text-[11px] leading-relaxed text-slate-500">{event.detection.attribution}</p>
      )}
      {keywords.length > 0 && (
        <p className="mt-2.5 flex flex-wrap items-center gap-1 text-xs text-slate-500">
          {event.detection?.method === "ai_reading" ? "Found by the AI reading. Keywords also matched:" : "Detected by:"}
          {keywords.map((keyword) => (
            <span
              key={keyword}
              className="rounded bg-white px-1.5 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-inset ring-brand-100"
            >
              {keyword}
            </span>
          ))}
        </p>
      )}
      {event.sourceReference ? (
        <a
          href={event.sourceReference}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2.5 inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-800 hover:underline"
        >
          {manual ? "Open the link given" : official ? "Open the source record" : "Open original article"}
          {site && ` on ${site}`}
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-3 w-3" aria-hidden="true">
            <path d="M6 3h7v7M13 3 4 12" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      ) : (
        <p className="mt-2.5 text-xs italic text-slate-400">
          {manual ? "No link was given." : "No link to the original was provided."}
        </p>
      )}
    </div>
  );
}

/** How the event was located, in the reader's terms, and every place it affects. */
/** For a public event's road block: its exact location, or that the source gives none. */
function PublicEventWhere({ event }: { event: RoadEvent }) {
  const where = publicEventLocation(event);
  if (!where) return null;
  const places = where.places.join("; ");
  return (
    <div
      className={`col-span-2 rounded-lg px-3 py-2 text-xs ring-1 ring-inset ${
        where.exact ? "bg-emerald-50 text-emerald-900 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-amber-200"
      }`}
    >
      <p className="font-semibold">Public event: exact location</p>
      {where.exact ? (
        <p className="mt-0.5">{places || "As drawn on the map by the source."}</p>
      ) : (
        <p className="mt-0.5 leading-relaxed">
          The source does not give the exact spot.
          {places && <> It names {places}; the marker is that place&rsquo;s position.</>} Use
          &ldquo;Correct location&rdquo; to mark the venue or the closed stretch before approval.
        </p>
      )}
    </div>
  );
}

function LocationSummary({ event }: { event: RoadEvent }) {
  const locationClass = event.detection?.locationClass ?? null;
  const places = event.detection?.affectedLocations ?? [];
  if (!locationClass && places.length === 0) return null;
  const described = locationClass ? LOCATION_CLASS_LABELS[locationClass] : null;
  const exact = locationClass !== null && locationClass !== "APPROXIMATE" && locationClass !== "UNRESOLVED";
  return (
    <Field label="Location">
      {described && (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${
            exact
              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
              : "bg-amber-50 text-amber-700 ring-amber-200"
          }`}
          title={described.meaning}
        >
          {described.label}
        </span>
      )}
      {described && <span className="mt-0.5 block text-xs text-slate-400">{described.meaning}</span>}
      {places.length > 0 && (
        <ul className="mt-1.5 space-y-1">
          {places.map((place, index) => (
            <li key={`${place.name}-${index}`} className="flex flex-wrap items-baseline gap-x-1.5 text-xs">
              <span className="font-medium text-slate-700">{place.name}</span>
              <span className="text-slate-400">
                {LOCATION_CLASS_LABELS[place.resolution].label.toLowerCase()}
                {place.direction && ` · ${place.direction}`}
                {place.closure && ` · ${place.closure}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Field>
  );
}

export default function EventDetailsPanel({ event, onClose, footer }: EventDetailsPanelProps) {
  const zone = timeZoneOf(event.city, event.source.id);
  const typeColor = getEventTypeColor(event.eventType);
  const statedPeriod = event.detection?.statedPeriod ?? null;
  const statedDistance = event.detection?.statedDistance ?? null;
  const sourceLength = event.detection?.sourceGeometryLengthM ?? null;
  const revision = event.detection?.periodRevision ?? null;
  const manual = isManualEntry(event);
  const official = isSourceProvided(event);
  const hasPeriod = event.startTime !== null || event.endTime !== null;
  const period = formatEventPeriod(
    event.startTime,
    event.endTime,
    isWholeDayPeriod(event.startTime, event.endTime, zone),
    zone,
  );
  const confidence = formatConfidence(event.confidence);
  const location = event.detection?.location ?? null;
  const locationRevision = event.detection?.locationRevision ?? null;
  const attributedTo = event.detection?.attributedTo ?? [];

  return (
    <section
      aria-label="Event details"
      className="flex max-h-full flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl ring-1 ring-slate-900/10 wide:rounded-2xl"
    >
      <div className="h-1 shrink-0" style={{ backgroundColor: typeColor }} />

      <header className="flex items-start gap-3 px-4 pb-3 pt-3.5">
        <div className="min-w-0 flex-1">
          <SourceBadge event={event} />
          <h2 className="mt-1.5 text-lg font-semibold leading-6 text-slate-900">{event.title}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close event details"
          className="-mr-1 flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
            <path d="m5 5 10 10M15 5 5 15" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      <StreetViewActions event={event} />

      <div className="min-h-0 space-y-3.5 overflow-y-auto border-t border-slate-100 px-4 py-3.5">
        <Evidence event={event} />

        <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5">
          <Field label="Event type">
            {event.eventType ? (
              <span className="font-medium" style={{ color: typeColor }}>
                {getEventTypeLabel(event.eventType)}
              </span>
            ) : (
              <Unknown>Unclassified</Unknown>
            )}
          </Field>
          <Field label="Status">
            <StatusBadge status={event.status} />
          </Field>
          <div className="col-span-2">
            <Field label="Affected road">
              {event.affectedRoad ? (
                <>
                  <span className="font-medium">{event.affectedRoad}</span>
                  {event.city && <span className="text-slate-500">, {event.city}</span>}
                  <span className="mt-0.5 block text-xs text-slate-400">
                    {manual
                      ? "As the reviewer wrote it; not matched to the road network."
                      : official
                        ? "As the source states it."
                        : "As named in the article; not matched to the road network."}
                  </span>
                </>
              ) : (
                <>
                  {NOT_AVAILABLE}
                  {event.city && <span className="text-slate-500"> · {event.city}</span>}
                </>
              )}
            </Field>
          </div>
          <Field label="Start">{event.startTime ? period.start : NOT_AVAILABLE}</Field>
          <Field label="End">{hasPeriod ? period.end : NOT_AVAILABLE}</Field>
          {statedPeriod && !revision && (
            <p className="col-span-2 -mt-2 text-xs text-slate-400">
              Dates as the {official ? "source" : "article"} states them: &ldquo;{statedPeriod}
              &rdquo;. It may end earlier or run longer.
            </p>
          )}
          {statedDistance && (
            <p className="col-span-2 -mt-2 text-xs text-slate-400">
              Distance as the source states it: &ldquo;{statedDistance}&rdquo;. Not measured by REI.
            </p>
          )}
          {sourceLength !== null && (
            <p className="col-span-2 -mt-2 text-xs text-slate-400">
              Length of the stretch the source draws: {Math.round(sourceLength)} m, measured on
              the source&rsquo;s own line. Short stretches are kept as drawn.
            </p>
          )}
          {revision && (
            <p className="col-span-2 -mt-2 text-xs text-slate-500">
              <span className="font-medium text-slate-600">
                End extended by a reviewer on {formatDate(revision.revisedAt, zone)}
              </span>
              : &ldquo;{revision.reason}&rdquo;.{" "}
              {revision.previousEnd
                ? `Recorded before as ending ${formatDate(revision.previousEnd, zone)}`
                : "No end was recorded before"}
              {statedPeriod && <> (the article: &ldquo;{statedPeriod}&rdquo;)</>}.
            </p>
          )}
          <div className="col-span-2">
            <Field label="Announced by">
              {attributedTo.length > 0 ? (
                <>
                  <span className="font-medium">{attributedTo.join(", ")}</span>
                  <span className="mt-0.5 block text-xs text-slate-400">
                    According to the article; the official notice itself has not been checked.
                  </span>
                </>
              ) : (
                <Unknown>{manual ? "Not recorded" : "Not stated in the article"}</Unknown>
              )}
            </Field>
          </div>
          <Field label="REI severity">
            {event.severity ? <SeverityIndicator severity={event.severity} /> : NOT_ASSESSED}
          </Field>
          <Field label="Direction">
            {event.direction ? DIRECTION_LABELS[event.direction] : NOT_AVAILABLE}
          </Field>
          <Field label="Confidence">{confidence ?? NOT_ASSESSED}</Field>
          <PublicEventWhere event={event} />
          {event.detection?.ai && (
            <div className="col-span-2">
              <AiSection ai={event.detection.ai} zone={zone} eventColor={getEventTypeColor(event.eventType)} />
            </div>
          )}
          <div className="col-span-2">
            <LocationSummary event={event} />
          </div>
          {event.detection?.gis && (
            <div className="col-span-2">
              <GisSection gis={event.detection.gis} />
            </div>
          )}
          <Field label="Map location">
            {location ? (
              <>
                <span className="font-medium">{location.placeName}</span>
                {location.method === REVIEWER_PLACED ? (
                  <span className="mt-0.5 block text-xs text-slate-500">
                    <span className="font-medium text-slate-600">
                      Placed on the map by a reviewer
                      {locationRevision && ` on ${formatDate(locationRevision.revisedAt, zone)}`}
                    </span>
                    {locationRevision && <>: &ldquo;{locationRevision.reason}&rdquo;</>}.
                    {locationRevision?.previousPlaceName &&
                      ` Located before by the name \u201c${locationRevision.previousPlaceName}\u201d.`}
                  </span>
                ) : (
                  <span className="mt-0.5 block text-xs text-slate-400">
                    Approximate: the {location.placeKind === "google" ? "place" : location.placeKind}{" "}
                    {FOUND_IN_PHRASES[location.foundIn] ?? "named"}
                    {location.within && `, within ${location.within}`}, at its position on{" "}
                    {location.reference}.
                  </span>
                )}
              </>
            ) : event.geometry ? (
              "Located"
            ) : (
              <span
                className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-inset ring-slate-200"
                title="No known place is named for this event, so it is not shown on the map."
              >
                Not located
              </span>
            )}
          </Field>
          <div className="col-span-2">
            <Field label={manual ? "Details" : "Article summary"}>
              {event.description ? (
                <span className="leading-relaxed text-slate-600">{event.description}</span>
              ) : (
                NOT_AVAILABLE
              )}
            </Field>
          </div>
        </dl>

        <p className="border-t border-slate-100 pt-3 text-[11px] leading-relaxed text-slate-400">
          <span className="font-mono">{event.id}</span> · Times in {timeZoneLabel(new Date(), zone)} ·{" "}
          {manual
            ? "Entered by a reviewer and not verified against an official notice."
            : official
              ? "Published by an official source; still to be reviewed before it is approved."
              : "Detected automatically from a news article and not verified."}
          {!event.geometry && " Not shown on the map: no known place is named to locate it by."}
        </p>
      </div>

      {footer}
    </section>
  );
}
