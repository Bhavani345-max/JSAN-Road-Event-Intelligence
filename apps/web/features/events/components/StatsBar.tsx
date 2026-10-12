import type { EventStats } from "../stats";

interface StatsBarProps {
  /** Stats for the events currently shown; null while events are loading. */
  stats: EventStats | null;
  /** Count of all loaded events, shown when filters hide some of them. */
  unfilteredTotal: number;
}

interface StatTileProps {
  label: string;
  /** Full name, for the tooltip. */
  title: string;
  value: number | null;
  hint?: string;
  /** Draws attention when there is something to act on. */
  highlight?: boolean;
}

function StatTile({ label, title, value, hint, highlight = false }: StatTileProps) {
  const emphasised = highlight && value !== null && value > 0;
  return (
    <div
      title={title}
      className={`rounded-lg px-2 py-2 ring-1 ring-inset ${
        emphasised ? "bg-amber-300/20 ring-amber-200/50" : "bg-white/10 ring-white/15"
      }`}
    >
      <dt
        className={`truncate text-[11px] font-medium tracking-tight ${
          emphasised ? "text-amber-100" : "text-brand-100"
        }`}
      >
        {label}
      </dt>
      <dd className="mt-0.5 flex items-baseline gap-1">
        {value === null ? (
          <span className="my-1 h-6 w-7 animate-pulse rounded bg-white/20" />
        ) : (
          <span className="text-2xl font-semibold tabular-nums leading-8 text-white">{value}</span>
        )}
        {hint && <span className="text-[10px] text-brand-200">{hint}</span>}
      </dd>
    </div>
  );
}

export default function StatsBar({ stats, unfilteredTotal }: StatsBarProps) {
  const isFiltered = stats !== null && stats.total !== unfilteredTotal;
  return (
    <dl className="grid grid-cols-5 gap-1.5">
      <StatTile
        label="Total"
        title="Total events"
        value={stats?.total ?? null}
        hint={isFiltered ? `/ ${unfilteredTotal}` : undefined}
      />
      <StatTile label="Active" title="Active events" value={stats?.active ?? null} />
      <StatTile label="Scheduled" title="Scheduled events" value={stats?.scheduled ?? null} />
      <StatTile label="Closures" title="Road closures" value={stats?.roadClosures ?? null} />
      <StatTile
        label="To review"
        title="Events waiting for human validation"
        value={stats?.needsReview ?? null}
        highlight
      />
    </dl>
  );
}
