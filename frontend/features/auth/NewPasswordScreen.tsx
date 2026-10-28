"use client";

import { useState, type FormEvent } from "react";
import { changePassword, MIN_PASSWORD_LENGTH, passwordProblem } from "@/features/profile/profile";
import type { AuthUser } from "./types";

interface NewPasswordScreenProps {
  user: AuthUser;
  onDone: (user: AuthUser) => void;
  onSignOut: () => Promise<void>;
}

const INPUT =
  "h-10 w-full rounded-lg bg-white px-3 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 outline-none transition focus:ring-2 focus:ring-brand-500";

/**
 * Signed in with a temporary password (decision 0044): the account chooses its
 * own before it sees anything else. The API refuses everything else meanwhile.
 */
export default function NewPasswordScreen({ user, onDone, onSignOut }: NewPasswordScreenProps) {
  const [temporary, setTemporary] = useState("");
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = passwordProblem(temporary, next, confirmation);
    if (problem) {
      setError(problem.replace("current password", "temporary password"));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await changePassword(temporary, next);
      onDone({ ...user, must_change_password: false });
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message.replace("current password", "temporary password")
          : "The password could not be changed. Try again.",
      );
      setSaving(false);
    }
  }

  return (
    <main className="flex h-dvh items-center justify-center bg-slate-50 px-5 text-slate-900">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-900/5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">JSAN REI</p>
        <h1 className="mt-3 text-xl font-semibold tracking-tight">Choose your own password</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Your administrator set a temporary password for <span className="font-medium text-slate-800">{user.email}</span>.
          Choose your own before you continue. Only you will know it.
        </p>
        <form onSubmit={submit} className="mt-5 space-y-3.5" noValidate>
          <div>
            <label htmlFor="temporary-password" className="mb-1 block text-xs font-medium text-slate-700">Temporary password</label>
            <input id="temporary-password" type="password" autoComplete="current-password" className={INPUT} value={temporary} onChange={(event) => setTemporary(event.target.value)} autoFocus />
          </div>
          <div>
            <label htmlFor="new-password" className="mb-1 block text-xs font-medium text-slate-700">New password</label>
            <input id="new-password" type="password" autoComplete="new-password" className={INPUT} value={next} onChange={(event) => setNext(event.target.value)} />
            <p className="mt-1 text-[11px] leading-4 text-slate-500">At least {MIN_PASSWORD_LENGTH} characters.</p>
          </div>
          <div>
            <label htmlFor="new-password-again" className="mb-1 block text-xs font-medium text-slate-700">New password again</label>
            <input id="new-password-again" type="password" autoComplete="new-password" className={INPUT} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </div>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-200">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={saving}
            className="inline-flex h-10 w-full items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save and continue"}
          </button>
        </form>
        <button
          type="button"
          onClick={() => void onSignOut()}
          className="mt-4 w-full rounded text-center text-xs font-semibold text-slate-500 underline-offset-2 hover:text-slate-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          Sign out instead
        </button>
      </section>
    </main>
  );
}
