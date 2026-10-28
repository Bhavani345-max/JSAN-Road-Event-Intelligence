"use client";

import { useState, type FormEvent } from "react";
import { isUnreachable } from "@/lib/apiClient";
import { requestResetLink } from "./accountApi";

interface ResetLinkFormProps {
  initialEmail: string;
  onBack: () => void;
}

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Forgot password: email me a reset link (decision 0045). The same answer for every address. */
export default function ResetLinkForm({ initialEmail, onBack }: ResetLinkFormProps) {
  const [email, setEmail] = useState(initialEmail);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!EMAIL.test(email.trim())) {
      setError("Enter your sign-in email.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      setSent((await requestResetLink(email)).message);
    } catch (cause) {
      setError(
        isUnreachable(cause)
          ? "We could not reach the sign-in service. Check the connection and retry."
          : cause instanceof Error
            ? cause.message
            : "The request could not be sent. Try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="login-form mt-5 space-y-4" noValidate>
      {sent ? (
        <p role="status" className="login-status flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="m6.5 10.2 2.3 2.3 4.7-4.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span>{sent}</span>
        </p>
      ) : (
        <>
          <div>
            <label htmlFor="reset-link-email" className="mb-1.5 block text-[13px] font-semibold text-[color:var(--login-label)]">Work email</label>
            <input id="reset-link-email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} className="login-input h-[46px] w-full rounded-xl px-3.5 text-[14.5px]" value={email} onChange={(event) => setEmail(event.target.value)} autoFocus />
          </div>
          <p className="text-[12px] leading-5 text-[color:var(--login-helper)]">
            For accounts whose email was confirmed. The link works once, for 30 minutes.
          </p>
          {error && (
            <div role="alert" className="login-error flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
              <span>{error}</span>
            </div>
          )}
          <button type="submit" disabled={submitting} className="login-button flex h-[50px] w-full items-center justify-center gap-2 rounded-xl px-4 text-[15px] font-semibold">
            {submitting ? "Sending" : "Email me a reset link"}
          </button>
        </>
      )}
      <button type="button" onClick={onBack} className="login-link mx-auto block rounded text-[12.5px] font-semibold">
        Back to sign in
      </button>
    </form>
  );
}
