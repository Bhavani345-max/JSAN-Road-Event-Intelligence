import { useState } from "react";
import type { RoadEvent } from "@/features/events/model";
import { approveGis, chooseGis, confirmJunction, rejectGis } from "../api";

interface GisReviewProps {
  event: RoadEvent;
  onDecided: () => void;
}

const buttonClass =
  "h-7 cursor-pointer rounded-md px-2.5 text-[11px] font-semibold disabled:opacity-50";

/**
 * A reviewer's decisions on GIS results: approve or reject a proposed
 * location, choose one candidate of an ambiguous result, confirm a proposed
 * junction name. "Correct location" (placing the event by hand) stays below.
 */
export default function GisReview({ event, onDecided }: GisReviewProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const gis = event.detection?.gis;
  if (!gis) return null;

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onDecided();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The decision could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const pending = gis.applied && gis.reviewStatus === "PENDING";
  // Junction references a reviewer has not confirmed yet, proposed for this event.
  const unconfirmed = gis.results.flatMap((result) =>
    result.chosen && (result.chosen.method === "JUNCTION_REFERENCE" || result.chosen.method === "ALIAS_MATCH") &&
    result.confidence !== "HIGH"
      ? result.chosen.osmIds
          .filter((id) => id.startsWith("junction-reference/"))
          .map((id) => ({ id: Number(id.split("/")[1]), name: result.chosen!.matchedName }))
      : [],
  );
  // Results a reviewer can settle by choosing a candidate.
  const choosable = gis.results
    .map((result, index) => ({ result, index }))
    .filter(({ result }) => !result.applied && (result.chosen || result.alternatives.length > 0) && result.confidence !== "LOW");

  if (!pending && unconfirmed.length === 0 && choosable.length === 0) return null;

  return (
    <div className="mb-3 space-y-2 rounded-lg bg-white p-2.5 text-xs ring-1 ring-inset ring-teal-200">
      <p className="font-semibold text-slate-700">Road network (GIS)</p>
      {pending && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-600">Proposed location awaiting review:</span>
          <button type="button" disabled={busy} className={`${buttonClass} bg-teal-600 text-white hover:bg-teal-700`}
            onClick={() => run(() => approveGis(event.id, "Reviewer approved the GIS location"))}>
            Approve GIS location
          </button>
          <button type="button" disabled={busy} className={`${buttonClass} bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50`}
            onClick={() => run(() => rejectGis(event.id, "Reviewer rejected the GIS location"))}>
            Reject
          </button>
        </div>
      )}
      {unconfirmed.map((junction) => (
        <div key={junction.id} className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-600">
            Junction &ldquo;{junction.name}&rdquo; is not confirmed yet.
          </span>
          <button type="button" disabled={busy} className={`${buttonClass} bg-brand-600 text-white hover:bg-brand-700`}
            onClick={() => run(() => confirmJunction(junction.id, "Reviewer confirmed the junction position"))}>
            Confirm junction
          </button>
        </div>
      ))}
      {choosable.map(({ result, index }) => (
        <div key={index} className="space-y-1">
          <p className="text-slate-600">
            &ldquo;{result.mention}&rdquo;: {result.ambiguous ? "several candidates" : "a candidate needs a reviewer"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {result.chosen && (
              <button type="button" disabled={busy} className={`${buttonClass} bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50`}
                onClick={() => run(() => chooseGis(event.id, index, null, `Reviewer chose ${result.chosen!.matchedName}`))}>
                Use {result.chosen.matchedName}
              </button>
            )}
            {result.alternatives.slice(0, 4).map((alternative, altIndex) => (
              <button key={altIndex} type="button" disabled={busy} className={`${buttonClass} bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50`}
                onClick={() => run(() => chooseGis(event.id, index, altIndex, `Reviewer chose ${alternative.matchedName}`))}>
                Use {alternative.matchedName}
              </button>
            ))}
          </div>
        </div>
      ))}
      {error && <p className="text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
