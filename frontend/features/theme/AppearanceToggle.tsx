"use client";

import { saveAppearance, useAppearance } from "./appearance";

/** Switches between the light (default) and dark appearance; kept in this browser. */
export default function AppearanceToggle() {
  const appearance = useAppearance();
  const dark = appearance === "dark";
  return (
    <button
      type="button"
      onClick={() => saveAppearance(dark ? "light" : "dark")}
      aria-pressed={dark}
      aria-label="Dark mode"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-slate-600 ring-1 ring-inset ring-slate-200 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      {dark ? (
        // A sun: back to light.
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4" aria-hidden="true">
          <circle cx="10" cy="10" r="3.2" />
          <path d="M10 2.5v1.8M10 15.7v1.8M2.5 10h1.8M15.7 10h1.8M4.7 4.7l1.3 1.3M14 14l1.3 1.3M4.7 15.3 6 14M14 6l1.3-1.3" strokeLinecap="round" />
        </svg>
      ) : (
        // A moon: to dark.
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-4 w-4" aria-hidden="true">
          <path d="M16.5 12.3A6.5 6.5 0 0 1 7.7 3.5a6.5 6.5 0 1 0 8.8 8.8Z" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  );
}
