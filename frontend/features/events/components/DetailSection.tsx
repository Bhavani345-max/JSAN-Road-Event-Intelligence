import { useState } from "react";

interface DetailSectionProps {
  title: string;
  /** A few words shown beside the title, also while the section is closed. */
  summary?: React.ReactNode;
  defaultOpen?: boolean;
  /** Render the content only once opened (it loads something). */
  lazy?: boolean;
  children: React.ReactNode;
}

/**
 * A collapsible part of the event details. A native <details>, so the keyboard
 * and screen readers handle it; its open state stays as the reviewer left it
 * while they move from event to event.
 */
export default function DetailSection({
  title,
  summary,
  defaultOpen = true,
  lazy = false,
  children,
}: DetailSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="rei-detail-section group/section rounded-xl bg-white ring-1 ring-inset ring-slate-200"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-3 py-2.5 outline-none transition hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden">
        <svg
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          className="h-3 w-3 shrink-0 text-slate-400 transition-transform group-open/section:rotate-90"
          aria-hidden="true"
        >
          <path d="m6 3.5 4.5 4.5L6 12.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">{title}</span>
        {summary && (
          <span className="ml-auto min-w-0 truncate text-[11px] text-slate-400">{summary}</span>
        )}
      </summary>
      <div className="border-t border-slate-100 px-3 pb-3 pt-3">{(!lazy || open) && children}</div>
    </details>
  );
}
