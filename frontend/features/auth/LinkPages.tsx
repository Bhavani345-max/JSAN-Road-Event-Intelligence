"use client";

import Link from "next/link";
import { useState, useSyncExternalStore, type FormEvent, type ReactNode } from "react";
import { isUnreachable } from "@/lib/apiClient";
import { linkToken, resetWithLink, strongPasswordProblem, verifyEmail } from "./accountApi";

// The address does not change while the page is open.
const subscribeToNothing = () => () => {};

/** The link's token, read in the browser (the page is not rendered with it on the server). */
function useLinkToken(): string | null | undefined {
  return useSyncExternalStore(
    subscribeToNothing,
    () => linkToken(window.location.search),
    () => undefined,
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-5 py-8 text-slate-900">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-900/5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">JSAN REI</p>
        <h1 className="mt-3 text-xl font-semibold tracking-tight">{title}</h1>
        {children}
      </section>
    </main>
  );
}

const BUTTON =
  "inline-flex h-10 w-full items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-60";
const INPUT =
  "h-10 w-full rounded-lg bg-white px-3 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 outline-none transition focus:ring-2 focus:ring-brand-500";

function Outcome({ kind, children }: { kind: "ok" | "error"; children: ReactNode }) {
  return (
    <p
      role={kind === "ok" ? "status" : "alert"}
      className={`mt-4 rounded-lg px-3 py-2.5 text-sm leading-6 ring-1 ring-inset ${
        kind === "ok" ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-red-50 text-red-700 ring-red-200"
      }`}
    >
      {children}
    </p>
  );
}

const SIGN_IN = (
  <Link href="/login" className="mt-5 block text-center text-sm font-semibold text-brand-700 underline-offset-2 hover:underline">
    Go to sign in
  </Link>
);

function failure(cause: unknown): string {
  if (isUnreachable(cause)) return "We could not reach REI. Check the connection and retry.";
  return cause instanceof Error ? cause.message : "That did not work. Try again.";
}

/**
 * The registration's emailed link (decision 0045). Confirmed by a button, not by
 * opening the page: mail scanners that open links never use the token up.
 */
export function VerifyEmailPage() {
  const token = useLinkToken();
  const [state, setState] = useState<"ready" | "busy" | "done">("ready");
  const [error, setError] = useState<string | null>(null);
  if (token === undefined) return null;
  return (
    <Card title="Confirm your email">
      {!token ? (
        <Outcome kind="error">This link is incomplete. Open the link from the email again, or register again.</Outcome>
      ) : state === "done" ? (
        <Outcome kind="ok">
          Email confirmed. An administrator now reviews your registration; you will get an email when it is decided.
        </Outcome>
      ) : (
        <>
          <p className="mt-2 text-sm leading-6 text-slate-600">Confirm that this email address is yours to finish your registration.</p>
          {error && <Outcome kind="error">{error}</Outcome>}
          <button
            type="button"
            className={`${BUTTON} mt-5`}
            disabled={state === "busy"}
            onClick={async () => {
              setState("busy");
              setError(null);
              try {
                await verifyEmail(token);
                setState("done");
              } catch (cause) {
                setError(failure(cause));
                setState("ready");
              }
            }}
          >
            {state === "busy" ? "Confirming…" : "Confirm my email"}
          </button>
        </>
      )}
      {SIGN_IN}
    </Card>
  );
}

/** The emailed reset link (decision 0045): a new password, then every session ends. */
export function ResetPasswordPage() {
  const token = useLinkToken();
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (token === undefined) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = strongPasswordProblem(next) ?? (next !== confirmation ? "The two passwords are not the same." : null);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetWithLink(token as string, next);
      setDone(true);
    } catch (cause) {
      setError(failure(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Choose a new password">
      {!token ? (
        <Outcome kind="error">This link is incomplete. Open the link from the email again, or ask for a new one.</Outcome>
      ) : done ? (
        <Outcome kind="ok">Password changed. You were signed out everywhere: sign in with the new password.</Outcome>
      ) : (
        <form onSubmit={submit} className="mt-4 space-y-3.5" noValidate>
          <div>
            <label htmlFor="link-new" className="mb-1 block text-xs font-medium text-slate-700">New password</label>
            <input id="link-new" type="password" autoComplete="new-password" className={INPUT} value={next} onChange={(event) => setNext(event.target.value)} autoFocus />
            <p className="mt-1 text-[11px] leading-4 text-slate-500">At least 8 characters, not a common password.</p>
          </div>
          <div>
            <label htmlFor="link-again" className="mb-1 block text-xs font-medium text-slate-700">New password again</label>
            <input id="link-again" type="password" autoComplete="new-password" className={INPUT} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </div>
          {error && <Outcome kind="error">{error}</Outcome>}
          <button type="submit" className={BUTTON} disabled={busy}>{busy ? "Saving…" : "Save new password"}</button>
        </form>
      )}
      {SIGN_IN}
    </Card>
  );
}
