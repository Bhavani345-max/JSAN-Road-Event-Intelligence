import type { GisResolutionView } from "../model";

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  MEDIUM: "bg-amber-50 text-amber-700 ring-amber-200",
  LOW: "bg-slate-100 text-slate-600 ring-slate-200",
  UNRESOLVED: "bg-slate-100 text-slate-500 ring-slate-200",
};

const METHOD_LABELS: Record<string, string> = {
  JUNCTION_REFERENCE: "confirmed junction reference",
  ALIAS_MATCH: "junction reference (alias)",
  OSM_NAMED_JUNCTION: "junction named in OSM",
  ROAD_INTERSECTION: "where two named roads meet",
  EXACT_ROAD_NAME: "road named in OSM",
  ROAD_STRETCH: "stretch of a named road",
  NEARBY_ROAD: "road through the junction",
  REVIEWER_CONFIRMED: "chosen by a reviewer",
};

const REVIEW_LABELS: Record<string, string> = {
  PENDING: "Proposed: awaiting review",
  APPROVED: "Approved by a reviewer",
  REJECTED: "Rejected by a reviewer",
  SUPERSEDED: "Superseded by a reviewer's own placement",
  NOT_APPLIED: "Candidates only: nothing applied",
};

function osmLink(id: string): string | null {
  const [type, number] = id.split("/");
  return ["way", "node", "relation"].includes(type) ? `https://www.openstreetmap.org/${type}/${number}` : null;
}

/** What the GIS Resolution Engine found for each place the event names, and why. */
export default function GisSection({ gis }: { gis: GisResolutionView }) {
  return (
    <div className="rounded-lg bg-white p-3 ring-1 ring-inset ring-slate-200">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Road network (GIS)</p>
      <p className="mt-1 text-xs text-slate-600">
        <span className="font-semibold">{REVIEW_LABELS[gis.reviewStatus] ?? gis.reviewStatus}</span>
        {gis.notAppliedReason && <span className="text-slate-500">: {gis.notAppliedReason}</span>}.
      </p>
      <ul className="mt-2 space-y-2">
        {gis.results.map((result, index) => (
          <li key={`${result.mention}-${index}`} className="text-xs leading-snug">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-medium text-slate-800">&ldquo;{result.mention}&rdquo;</span>
              <span
                className={`rounded-full px-1.5 py-px text-[10px] font-semibold ring-1 ring-inset ${
                  CONFIDENCE_STYLES[result.confidence] ?? CONFIDENCE_STYLES.LOW
                }`}
              >
                {result.confidence}
                {result.ambiguous && " · ambiguous"}
              </span>
              {result.applied && (
                <span className="rounded-full bg-teal-50 px-1.5 py-px text-[10px] font-semibold text-teal-700 ring-1 ring-inset ring-teal-200">
                  event location
                </span>
              )}
              <span className="text-slate-400">({result.kind}, {result.foundIn})</span>
            </div>
            {result.chosen && (
              <p className="mt-0.5 text-slate-600">
                {result.chosen.matchedName}{" "}
                <span className="text-slate-400">· {METHOD_LABELS[result.chosen.method] ?? result.chosen.method}</span>
                {result.chosen.osmIds.slice(0, 3).map((id) => {
                  const href = osmLink(id);
                  return href ? (
                    <a key={id} href={href} target="_blank" rel="noopener noreferrer" className="ml-1 text-brand-600 hover:underline">
                      {id}
                    </a>
                  ) : (
                    <span key={id} className="ml-1 text-slate-400">{id}</span>
                  );
                })}
              </p>
            )}
            {[...result.reasons, ...(result.chosen?.reasons ?? [])].length > 0 && (
              <p className="mt-0.5 text-[11px] text-slate-500">
                {[...result.reasons, ...(result.chosen?.reasons ?? [])].join("; ")}.
              </p>
            )}
            {result.alternatives.length > 0 && (
              <p className="mt-0.5 text-[11px] text-slate-500">
                {result.alternatives.length} other candidate{result.alternatives.length === 1 ? "" : "s"}:{" "}
                {result.alternatives.map((a) => a.matchedName).join("; ")}.
              </p>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[10px] text-slate-400">
        {gis.network}. Road data © OpenStreetMap contributors (ODbL). Not navigation-grade map matching.
      </p>
    </div>
  );
}
