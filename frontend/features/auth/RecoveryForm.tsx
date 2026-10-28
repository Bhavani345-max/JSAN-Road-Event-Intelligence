"use client";

import { useState, type FormEvent } from "react";
import { MIN_PASSWORD_LENGTH, recoverWithCode, recoveryProblem } from "@/features/profile/profile";
import { ApiError, isUnreachable } from "@/lib/apiClient";

interface RecoveryFormProps {
  initialEmail: string;
  /** The password was reset: back to signing in, with the email and the codes left. */
  onDone: (email: string, codesLeft: number) => void;
  onBack: () => void;
}

/**
 * Forgot password, for an administrator with recovery codes (decision 0044): the
 * email, one code and a new password. Every wrong email or code gets the same
 * answer, and attempts count towards the account's sign-in limit.
 */
export default function RecoveryForm({ initialEmail, onDone, onBack }: RecoveryFormProps) {
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = recoveryProblem(email, code, next, confirmation);
    if (problem) {
      setError(problem);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await recoverWithCode(email, code, next);
      onDone(email.trim(), result.codes_left);
    } catch (cause) {
      if (isUnreachable(cause)) setError("We could not reach the sign-in service. Check the connection and retry.");
      else if (cause instanceof ApiError) setError(cause.message);
      else setError("The password could not be reset. Try again.");
      setSubmitting(false);
    }
  }

  const field = "login-input h-[46px] w-full rounded-xl px-3.5 text-[14.5px]";
  const label = "mb-1.5 block text-[13px] font-semibold text-[color:var(--login-label)]";
  return (
    <form onSubmit={submit} className="login-form mt-5 space-y-3.5" noValidate>
      <div>
        <label htmlFor="recover-email" className={label}>Work email</label>
        <input id="recover-email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} className={field} value={email} onChange={(event) => setEmail(event.target.value)} />
      </div>
      <div>
        <label htmlFor="recover-code" className={label}>Recovery code</label>
        <input
          id="recover-code"
          autoComplete="one-time-code"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="abcd-efgh-jkmn-pqrs"
          className={`${field} font-mono`}
          value={code}
          onChange={(event) => setCode(event.target.value)}
          autoFocus
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="recover-new" className={label}>New password</label>
          <input id="recover-new" type="password" autoComplete="new-password" className={field} value={next} onChange={(event) => setNext(event.target.value)} />
        </div>
        <div>
          <label htmlFor="recover-again" className={label}>Again</label>
          <input id="recover-again" type="password" autoComplete="new-password" className={field} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        </div>
      </div>
      <p className="text-[12px] leading-5 text-[color:var(--login-helper)]">
        At least {MIN_PASSWORD_LENGTH} characters. The code works once; you are signed out everywhere afterwards.
      </p>
      {error && (
        <div role="alert" className="login-error flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M10 6v4m0 3h.01" strokeLinecap="round" /></svg>
          <span>{error}</span>
        </div>
      )}
      <button type="submit" disabled={submitting} className="login-button flex h-[50px] w-full items-center justify-center gap-2 rounded-xl px-4 text-[15px] font-semibold">
        {submitting ? (
          <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" /> Resetting</>
        ) : (
          "Reset password"
        )}
      </button>
      <button type="button" onClick={onBack} className="login-link mx-auto block rounded text-[12.5px] font-semibold">
        Back to sign in
      </button>
    </form>
  );
}
