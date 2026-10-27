import { formatCount, tileNumberSize, type EventStats } from "../stats";

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
  /** The row's number size, so every tile's number fits and they match. */
  numberSize: string;
  hint?: string;
  /** Draws attention when there is something to act on. */
  highlight?: boolean;
}

function StatTile({ label, title, value, numberSize, hint, highlight = false }: StatTileProps) {
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
      {/* The tile's inner width is the container the number's size is read against. */}
      <dd className="@container mt-0.5 flex flex-wrap items-baseline gap-x-1">
        {value === null ? (
          <span className="my-1 h-6 w-7 animate-pulse rounded bg-white/20" />
        ) : (
          <span
            className="whitespace-nowrap font-semibold tabular-nums leading-8 text-white"
            style={{ fontSize: numberSize }}
          >
            {formatCount(value)}
          </span>
        )}
        {hint && <span className="text-[10px] text-brand-200">{hint}</span>}
      </dd>
    </div>
  );
}

export default function StatsBar({ stats, unfilteredTotal }: StatsBarProps) {
  const isFiltered = stats !== null && stats.total !== unfilteredTotal;
  const numberSize = tileNumberSize(
    stats === null
      ? []
      : [stats.total, stats.active, stats.scheduled, stats.roadClosures, stats.needsReview],
  );
  return (
    <dl className="grid grid-cols-5 gap-1.5">
      <StatTile
        label="Total"
        title="Total events"
        value={stats?.total ?? null}
        numberSize={numberSize}
        hint={isFiltered ? `/ ${formatCount(unfilteredTotal)}` : undefined}
      />
      <StatTile
        label="Active"
        title="Active events"
        value={stats?.active ?? null}
        numberSize={numberSize}
      />
      <StatTile
        label="Scheduled"
        title="Scheduled events"
        value={stats?.scheduled ?? null}
        numberSize={numberSize}
      />
      <StatTile
        label="Closures"
        title="Road closures"
        value={stats?.roadClosures ?? null}
        numberSize={numberSize}
      />
      <StatTile
        label="To review"
        title="Events waiting for human validation"
        value={stats?.needsReview ?? null}
        numberSize={numberSize}
        highlight
      />
    </dl>
  );
}
