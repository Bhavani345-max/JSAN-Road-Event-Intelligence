import type { AiReadingView } from "../model";
import { formatDateTime, getEventTypeLabel, IMPACT_LABELS, PLACE_ROLE_LABELS, PLACE_ROLE_COLORS } from "../presentation";

/**
 * What a language model read from the article, after REI checked it against
 * the article. Its free-text answers are shown as the model's words; places,
 * dates and quotes were kept only where the article contains them.
 */
export default function AiSection({ ai, zone, eventColor }: { ai: AiReadingView; zone: string; eventColor: string }) {
  const verdict = ai.isRoadEvent
    ? ai.inScope === false
      ? { text: "Road event, but not in this city", style: "bg-amber-50 text-amber-800 ring-amber-200" }
      : ai.stage === "triage"
        ? { text: "Road event (headline check; full reading pending)", style: "bg-sky-50 text-sky-800 ring-sky-200" }
        : { text: "Road event", style: "bg-emerald-50 text-emerald-800 ring-emerald-200" }
    : { text: "Not a road event", style: "bg-amber-50 text-amber-800 ring-amber-200" };

  return (
    <div className="rounded-lg bg-white p-3 ring-1 ring-inset ring-slate-200">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">AI reading</p>
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${verdict.style}`}>
          {verdict.text}
        </span>
      </div>

      {ai.isRoadEvent && (ai.intent || ai.impact) && (
        <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-slate-700">
          {ai.intent && (
            <span className="inline-flex items-center gap-1 font-semibold">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: eventColor }} aria-hidden="true" />
              {getEventTypeLabel(ai.intent)}
            </span>
          )}
          {ai.impact && (
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
              {IMPACT_LABELS[ai.impact] ?? ai.impact}
            </span>
          )}
        </p>
      )}
      {ai.cause && (
        <p className="mt-1.5 text-xs text-slate-700">
          <span className="font-semibold">Reason:</span> {ai.cause}
        </p>
      )}
      {ai.summary && <p className="mt-1 text-xs leading-relaxed text-slate-600">{ai.summary}</p>}
      {!ai.summary && ai.why && <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{ai.why}</p>}

      {ai.places.length > 0 && (
        <ul className="mt-2 space-y-1">
          {ai.places.map((place) => (
            <li key={`${place.name}|${place.role}`} className="flex items-start gap-1.5 text-xs text-slate-700">
              <span
                className="mt-1 h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: PLACE_ROLE_COLORS[place.role] ?? eventColor }}
                aria-hidden="true"
              />
              <span>
                <span className="font-medium">{place.name}</span>{" "}
                <span className="text-slate-500">· {PLACE_ROLE_LABELS[place.role] ?? place.role}</span>
                {place.quote && <span className="block text-[11px] italic text-slate-400">“{place.quote}”</span>}
              </span>
            </li>
          ))}
        </ul>
      )}

      {ai.periodText && (
        <p className="mt-2 text-[11px] text-slate-500">
          When, in the article&rsquo;s words: <span className="italic">“{ai.periodText}”</span>
          {ai.periodReadBy === "ai" && " (dates read by the model; REI's date rules could not read these words)"}
          {ai.startTime && ` · from ${formatDateTime(ai.startTime, zone)}`}
          {ai.endTime && ` · until ${formatDateTime(ai.endTime, zone)}`}
        </p>
      )}
      {ai.authority && (
        <p className="mt-1 text-[11px] text-slate-500">Announced by: {ai.authority}</p>
      )}
      {ai.evidence && (
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
          Evidence: <span className="italic">“{ai.evidence}”</span>
        </p>
      )}
      {ai.discarded.length > 0 && (
        <details className="mt-2 text-[11px] text-slate-500">
          <summary className="cursor-pointer">Not used: {ai.discarded.length} answer(s) the article does not support</summary>
          <ul className="mt-1 list-disc pl-4">
            {ai.discarded.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="mt-2 text-[10px] leading-relaxed text-slate-400">
        Read by {ai.model} on {formatDateTime(ai.readAt, zone)}. Places, dates and quotes were kept only where the
        article contains them; positions come from OpenStreetMap or Google Maps, never from the model.
      </p>
    </div>
  );
}
