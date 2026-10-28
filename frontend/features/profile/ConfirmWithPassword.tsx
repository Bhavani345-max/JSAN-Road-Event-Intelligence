"use client";

import { useState, type FormEvent } from "react";

const INPUT =
  "h-9 w-full rounded-lg bg-white px-3 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 outline-none transition focus:ring-2 focus:ring-brand-500";
export const PRIMARY =
  "inline-flex h-8 items-center justify-center rounded-lg bg-brand-600 px-3 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";
export const SECONDARY =
  "inline-flex h-8 items-center justify-center rounded-lg bg-white px-3 text-xs font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-50";

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "That did not work. Try again.";
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** Asks for the administrator's own password before a sensitive change (decision 0044). */
export default function ConfirmWithPassword({
  id,
  action,
  onConfirm,
  onCancel,
}: {
  id: string;
  action: string;
  onConfirm: (password: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!password) {
      setError("Enter your password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(password);
    } catch (cause) {
      setError(errorText(cause));
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="mt-2.5 space-y-2 rounded-xl bg-slate-50 p-3 ring-1 ring-inset ring-slate-200" noValidate>
      <label htmlFor={id} className="block text-xs font-medium text-slate-700">Your password, to confirm</label>
      <input id={id} type="password" autoComplete="current-password" className={INPUT} value={password} onChange={(event) => setPassword(event.target.value)} autoFocus />
      {error && <p role="alert" className="text-xs font-medium text-red-700">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className={PRIMARY} disabled={busy}>{busy ? "Working…" : action}</button>
        <button type="button" className={SECONDARY} onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  );
}
