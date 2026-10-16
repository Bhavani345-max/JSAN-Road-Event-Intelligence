import type { EventListView } from "@/features/events/filters";
import type { ApiCityCoverage } from "@/types/api";
import { count as number, coverageTotals, notOnThisMap, shownOnMap } from "../sources";

interface CoverageSummaryProps {
  coverage: ApiCityCoverage[];
  /** What the choice covers (a city, or a country and its cities); null for every city together. */
  areaIds: string[] | null;
  /** The view on screen: its map is the one counted as "on this map". */
  view: EventListView;
}

/**
 * The events of the choice from detection to the map (GET /events/coverage,
 * decisions 0034, 0035): how many this view's map shows, then how many were
 * detected, await review and are validated, and why the rest are not on
 * this map. The operations map counts validated events only; an event
 * awaiting review is never counted as a confirmed one. The numbers are the
 * API's; nothing is estimated here.
 */
export default function CoverageSummary({ coverage, areaIds, view }: CoverageSummaryProps) {
  if (coverage.length === 0) return null;
  const totals = coverageTotals(coverage, areaIds);
  const review = view === "validation";
  const shown = shownOnMap(view, { review: totals.onMapReview, operations: totals.onMapOperations });
  const notShown = notOnThisMap(totals, view);

  return (
    <section aria-label="Events from detection to the map" className="space-y-0.5 text-[11px] text-brand-100">
      <p>
        <span className="font-semibold text-white">{number(shown)} on this map</span>
        {" · "}
        {review ? "awaiting review, not yet confirmed" : "validated, in effect or upcoming"}
      </p>
      <p>
        {number(totals.detected)} detected · {number(totals.pendingReview)} awaiting review ·{" "}
        {number(totals.validated)} validated
        {totals.rejected > 0 && ` · ${number(totals.rejected)} rejected`}
        {totals.closed > 0 && ` · ${number(totals.closed)} closed`}
        {totals.merged > 0 && ` (+${number(totals.merged)} duplicate rows merged)`}
      </p>
      {notShown.length > 0 && <p className="text-brand-200">Not on this map: {notShown.join(" · ")}</p>}
    </section>
  );
}
