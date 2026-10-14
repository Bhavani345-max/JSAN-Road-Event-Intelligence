import { useEffect, useRef, useState } from "react";
import type { Position, RoadEvent } from "@/features/events/model";
import { setEventLocation } from "../api";

interface SetLocationProps {
  event: RoadEvent;
  /** The spot the reviewer has clicked on the map, if any yet. */
  pickedPoint: Position | null;
  /** Tells the map to hand clicks to this form while it is open. */
  onPickingChange: (active: boolean) => void;
  onCancel: () => void;
  /** Called once the location has been saved; the caller closes the form and reloads. */
  onSaved: () => void;
}

const MIN_REASON_LENGTH = 5;
const NO_SPOT_YET = "Click the spot on the map first.";

const fieldClass =
  "h-8 w-full rounded-lg bg-white px-2 text-xs text-slate-800 shadow-sm outline-none ring-1 ring-inset ring-slate-200 transition placeholder:text-slate-400 focus-visible:ring-2 focus-visible:ring-brand-400";

/**
 * Lets a reviewer put an event at the exact spot, by clicking the map. For an
 * event the automatic lookup placed only roughly (at a locality's label, say)
 * or could not place at all.
 */
export default function SetLocation({
  event,
  pickedPoint,
  onPickingChange,
  onCancel,
  onSaved,
}: SetLocationProps) {
  const [placeName, setPlaceName] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const reasonRef = useRef<HTMLInputElement>(null);

  // The map picks points for exactly as long as this form is open.
  useEffect(() => {
    onPickingChange(true);
    return () => onPickingChange(false);
  }, [onPickingChange]);

  async function save(submit: React.FormEvent) {
    submit.preventDefault();
    if (!pickedPoint) {
      setError(NO_SPOT_YET);
      return;
    }
    if (placeName.trim().length < 2) {
      setError("Say what is at that spot, e.g. the junction's name.");
      nameRef.current?.focus();
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
      await setEventLocation(event.id, {
        longitude: pickedPoint[0],
        latitude: pickedPoint[1],
        placeName: placeName.trim(),
        reason: reason.trim(),
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The location could not be saved.");
      return;
    } finally {
      setSaving(false);
    }
    onSaved();
  }

  // Once a spot has been clicked, the reminder to click one no longer applies.
  const shownError = error === NO_SPOT_YET && pickedPoint ? null : error;

  return (
    <form onSubmit={save} className="mt-2.5 space-y-2">
      <p className="text-xs leading-relaxed text-slate-500">
        {pickedPoint ? (
          <>
            <span className="font-medium text-slate-700">
              Spot chosen: {pickedPoint[1].toFixed(5)}, {pickedPoint[0].toFixed(5)}.
            </span>{" "}
            Click the map again to change it.
          </>
        ) : (
          "Click the exact spot on the map. Move or zoom the map first if you need to."
        )}
      </p>
      <label className="block">
        <span className="text-[11px] font-medium text-slate-500">What is at this spot?</span>
        <input
          ref={nameRef}
          type="text"
          value={placeName}
          maxLength={120}
          onChange={(e) => {
            setPlaceName(e.target.value);
            setError(null);
          }}
          placeholder="e.g. IIIT Junction"
          className={fieldClass}
        />
      </label>
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
          placeholder="e.g. The works are at the junction itself, seen on site"
          className={fieldClass}
        />
      </label>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="cursor-pointer rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save location"}
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
      {shownError && (
        <p role="alert" className="text-xs text-red-700">
          {shownError}
        </p>
      )}
    </form>
  );
}
