import { useEffect, useId, useState } from "react";
import { EVENT_TYPES, type EventType } from "@/features/events/model";
import { EVENT_TYPE_LABELS } from "@/features/events/presentation";
import { createManualEvent, suggestPlaces, type PlaceSuggestion } from "../api";

interface AddEventPanelProps {
  onClose: () => void;
  /** Called with the new event's id once it has been saved. */
  onCreated: (eventId: string) => void;
}

const SUGGEST_DEBOUNCE_MS = 250;

const fieldClass =
  "w-full rounded-lg bg-white px-2.5 text-sm text-slate-900 shadow-sm outline-none ring-1 ring-inset ring-slate-200 transition placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-brand-400";

function Field({
  label,
  hint,
  required = false,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
        {required && <span className="text-red-600"> *</span>}
      </span>
      <span className="mt-1 block">{children}</span>
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}

/** Known places matching what has been typed, for the place field's suggestions. */
function usePlaceSuggestions(text: string): PlaceSuggestion[] {
  const query = text.trim();
  const [result, setResult] = useState<{ query: string; places: PlaceSuggestion[] } | null>(null);

  useEffect(() => {
    if (query.length < 2) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      suggestPlaces(query)
        .then((places) => {
          if (!cancelled) setResult({ query, places });
        })
        // Suggestions are a convenience; the entry can be saved without them.
        .catch(() => undefined);
    }, SUGGEST_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return result?.query === query ? result.places : [];
}

/**
 * Form for entering a road event that no connected source reported. The
 * entry is stored with the reviewer's stated basis and still goes through
 * validation like every other event.
 */
export default function AddEventPanel({ onClose, onCreated }: AddEventPanelProps) {
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<EventType | "">("");
  const [place, setPlace] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [description, setDescription] = useState("");
  const [referenceUrl, setReferenceUrl] = useState("");
  const [basis, setBasis] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestions = usePlaceSuggestions(place);
  const suggestionsId = useId();
  const isKnownPlace = suggestions.some(
    (suggestion) => suggestion.name.toLowerCase() === place.trim().toLowerCase(),
  );

  // The button is always available; what is missing is said when it is pressed.
  async function save(submit: React.FormEvent) {
    submit.preventDefault();
    if (title.trim().length < 5) {
      setError("Say what is happening, in a few words.");
      return;
    }
    if (basis.trim().length < 5) {
      setError("Say briefly how you know. It is kept with the event.");
      return;
    }
    setSaving(true);
    setError(null);
    let eventId: string;
    try {
      eventId = await createManualEvent({
        title: title.trim(),
        eventType: eventType || null,
        place: place.trim() || null,
        startDate: startDate || null,
        endDate: endDate || null,
        description: description.trim() || null,
        referenceUrl: referenceUrl.trim() || null,
        basis: basis.trim(),
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The event could not be saved.");
      return;
    } finally {
      setSaving(false);
    }
    onCreated(eventId);
  }

  return (
    <section
      aria-label="Add a road event"
      className="flex max-h-full flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl ring-1 ring-slate-900/10 md:rounded-2xl"
    >
      <div className="h-1 shrink-0 bg-brand-600" />
      <header className="flex items-start gap-3 px-4 pb-3 pt-3.5">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold leading-6 text-slate-900">Add a road event</h2>
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
            For an event you know of that no source has reported. Enter only what you know.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="-mr-1 flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
            <path d="m5 5 10 10M15 5 5 15" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      <form onSubmit={save} className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 space-y-3 overflow-y-auto border-t border-slate-100 px-4 py-3.5">
          <Field label="What is happening" required>
            <input
              type="text"
              value={title}
              maxLength={200}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. DLF Road closed between Gate No.1 and Gachibowli Traffic PS"
              className={`${fieldClass} h-9`}
            />
          </Field>
          <Field label="Type">
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value as EventType | "")}
              className={`${fieldClass} h-9 cursor-pointer`}
            >
              <option value="">Not sure</option>
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {EVENT_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Place"
            hint={
              place.trim() === ""
                ? "A junction, road, landmark or area. Choose a suggested name to put the event on the map."
                : isKnownPlace
                  ? "Known place: the event will be shown on the map there."
                  : "Not a known place name yet. The event is saved, but only a suggested name puts it on the map."
            }
          >
            <input
              type="text"
              value={place}
              maxLength={200}
              list={suggestionsId}
              onChange={(e) => setPlace(e.target.value)}
              placeholder="e.g. DLF road"
              className={`${fieldClass} h-9`}
            />
            <datalist id={suggestionsId}>
              {suggestions.map((suggestion) => (
                <option key={suggestion.name} value={suggestion.name}>
                  {suggestion.kind}
                </option>
              ))}
            </datalist>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date">
              <input
                type="date"
                value={startDate}
                max={endDate || undefined}
                onChange={(e) => setStartDate(e.target.value)}
                className={`${fieldClass} h-9`}
              />
            </Field>
            <Field label="End date">
              <input
                type="date"
                value={endDate}
                min={startDate || undefined}
                onChange={(e) => setEndDate(e.target.value)}
                className={`${fieldClass} h-9`}
              />
            </Field>
          </div>
          <Field label="Details">
            <textarea
              value={description}
              maxLength={2000}
              rows={3}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Which stretch, which direction, the diversion in place…"
              className={`${fieldClass} resize-none py-2`}
            />
          </Field>
          <Field label="Link" hint="Where you saw it, if it is on the web.">
            <input
              type="url"
              value={referenceUrl}
              maxLength={1000}
              onChange={(e) => setReferenceUrl(e.target.value)}
              placeholder="https://"
              className={`${fieldClass} h-9`}
            />
          </Field>
          <Field
            label="How do you know?"
            required
            hint="Kept with the event so others can judge it."
          >
            <input
              type="text"
              value={basis}
              maxLength={500}
              onChange={(e) => setBasis(e.target.value)}
              placeholder="e.g. Seen on site on 5 Oct; Cyberabad Traffic Police post on X"
              className={`${fieldClass} h-9`}
            />
          </Field>
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving…" : "Add event"}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="cursor-pointer rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50"
            >
              Cancel
            </button>
            <span className="ml-auto text-[11px] text-slate-400">
              Saved as &ldquo;Validation Required&rdquo;
            </span>
          </div>
          {error && (
            <p role="alert" className="mt-2 text-xs text-red-700">
              {error}
            </p>
          )}
        </div>
      </form>
    </section>
  );
}
