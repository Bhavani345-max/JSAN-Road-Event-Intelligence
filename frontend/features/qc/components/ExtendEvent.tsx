import { useRef, useState } from "react";
import type { RoadEvent } from "@/features/events/model";
import { formatDate, timeZoneOf, toDateInputValue } from "@/features/events/presentation";
import { extendEvent } from "../api";

interface ExtendEventProps {
  event: RoadEvent;
  onCancel: () => void;
  /** Called once the extension has been saved; the caller closes the form and reloads. */
  onSaved: () => void;
}

const MIN_REASON_LENGTH = 5;

const DAY_MS = 24 * 60 * 60 * 1000;

const fieldClass =
  "h-8 w-full rounded-lg bg-white px-2 text-xs text-slate-800 shadow-sm outline-none ring-1 ring-inset ring-slate-200 transition placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-brand-400";

/**
 * Lets a reviewer record that an event runs longer than recorded, for
 * example a closure that has overrun the end its article stated.
 */
export default function ExtendEvent({ event, onCancel, onSaved }: ExtendEventProps) {
  const [endDate, setEndDate] = useState("");
  const [openEnded, setOpenEnded] = useState(false);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dateRef = useRef<HTMLInputElement>(null);
  const reasonRef = useRef<HTMLInputElement>(null);

  // Dates are whole days in the event's own city.
  const zone = timeZoneOf(event.city, event.source.id);
  const currentEnd = formatDate(event.endTime, zone);
  // The first day that would be an extension: the day after the current end.
  const earliest =
    toDateInputValue(
      event.endTime
        ? new Date(new Date(event.endTime).getTime() + DAY_MS).toISOString()
        : event.startTime,
      zone,
    ) ?? undefined;
  // "Until further notice" only means something for an event with a start and an end.
  const canBeOpenEnded = event.startTime !== null && event.endTime !== null;

  // Save is always available. What is missing is said when it is pressed,
  // rather than the button sitting disabled with no explanation.
  async function save(submit: React.FormEvent) {
    submit.preventDefault();
    if (!openEnded && endDate === "") {
      setError("Choose the new end date first.");
      dateRef.current?.focus();
      return;
    }
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setError("Say briefly how you know. It is kept with the event.");
      reasonRef.current?.focus();
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await extendEvent(event.id, openEnded ? null : endDate, reason.trim());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The extension could not be saved.");
      return;
    } finally {
      // Never left on "Saving…", whether it worked or not.
      setSaving(false);
    }
    onSaved();
  }

  return (
    <form onSubmit={save} className="mt-2.5 space-y-2">
      <p className="text-xs leading-relaxed text-slate-500">
        {currentEnd
          ? `Recorded end: ${currentEnd}. Extend it if you know the event is still in effect.`
          : "No end is recorded. Give the last day you know the event to be in effect."}
      </p>
      <div className="flex items-end gap-3">
        <label className="min-w-0 flex-1">
          <span className="text-[11px] font-medium text-slate-500">New end date</span>
          <input
            ref={dateRef}
            type="date"
            value={openEnded ? "" : endDate}
            min={earliest}
            disabled={openEnded}
            onChange={(e) => {
              setEndDate(e.target.value);
              setError(null);
            }}
            className={`${fieldClass} disabled:bg-slate-100 disabled:text-slate-400`}
          />
        </label>
        {canBeOpenEnded && (
          <label className="flex h-8 cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-slate-600">
            <input
              type="checkbox"
              checked={openEnded}
              onChange={(e) => {
                setOpenEnded(e.target.checked);
                setError(null);
              }}
              className="h-3.5 w-3.5 accent-brand-600"
            />
            Until further notice
          </label>
        )}
      </div>
      <label className="block">
        <span className="text-[11px] font-medium text-slate-500">How do you know?</span>
        <input
          ref={reasonRef}
          type="text"
          value={reason}
          maxLength={500}
          onChange={(e) => {
            setReason(e.target.value);
            setError(null);
          }}
          placeholder="e.g. Still closed on 5 Oct, seen on site"
          className={fieldClass}
        />
      </label>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="cursor-pointer rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save extension"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="cursor-pointer rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}
