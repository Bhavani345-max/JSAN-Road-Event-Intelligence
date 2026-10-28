"use client";

import { useState, type FormEvent } from "react";
import { ApiError, isUnreachable } from "@/lib/apiClient";
import { registerAccount, registrationProblem, type AuthOptions } from "./accountApi";

interface RegisterFormProps {
  options: AuthOptions;
  onBack: () => void;
}

/**
 * A new employee asks for an account (decision 0045): a link proves the email,
 * then an administrator approves. Closed, with the reason, until REI can send email.
 */
export default function RegisterForm({ options, onBack }: RegisterFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [received, setReceived] = useState<string | null>(null);

  const back = (
    <button type="button" onClick={onBack} className="login-link mx-auto block rounded text-[12.5px] font-semibold">
      Back to sign in
    </button>
  );

  if (!options.registration_open) {
    return (
      <div className="mt-5 space-y-4">
        <p className="login-note rounded-xl px-3.5 py-3 text-[13px] leading-5">
          Registration is not open yet: REI cannot send email until an administrator sets up an email service.
          Ask your REI administrator for an account.
        </p>
        {back}
      </div>
    );
  }

  if (received) {
    return (
      <div className="mt-5 space-y-4">
        <p role="status" className="login-status flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="m6.5 10.2 2.3 2.3 4.7-4.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span>{received}</span>
        </p>
        {back}
      </div>
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = registrationProblem({ name, email, password, confirmation }, options.allowed_domains);
    if (problem) {
      setError(problem);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await registerAccount(name, email, password);
      setReceived(result.message);
    } catch (cause) {
      if (isUnreachable(cause)) setError("We could not reach the sign-in service. Check the connection and retry.");
      else if (cause instanceof ApiError && cause.status === 422) setError("Check your name and email address.");
      else setError(cause instanceof Error ? cause.message : "The request could not be sent. Try again.");
      setSubmitting(false);
    }
  }

  const field = "login-input h-[46px] w-full rounded-xl px-3.5 text-[14.5px]";
  const label = "mb-1.5 block text-[13px] font-semibold text-[color:var(--login-label)]";
  const domains = options.allowed_domains.map((domain) => `@${domain}`).join(", ");
  return (
    <form onSubmit={submit} className="login-form mt-5 space-y-3.5" noValidate>
      <div>
        <label htmlFor="register-name" className={label}>Full name</label>
        <input id="register-name" autoComplete="name" className={field} value={name} maxLength={120} onChange={(event) => setName(event.target.value)} autoFocus />
      </div>
      <div>
        <label htmlFor="register-email" className={label}>Company email</label>
        <input
          id="register-email"
          type="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          placeholder={domains ? `name${domains.split(",")[0]}` : undefined}
          className={field}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="register-password" className={label}>Password</label>
          <input id="register-password" type="password" autoComplete="new-password" className={field} value={password} onChange={(event) => setPassword(event.target.value)} />
        </div>
        <div>
          <label htmlFor="register-again" className={label}>Again</label>
          <input id="register-again" type="password" autoComplete="new-password" className={field} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        </div>
      </div>
      <p className="text-[12px] leading-5 text-[color:var(--login-helper)]">
        At least 8 characters, not a common password. We email you a link to confirm the address; an administrator
        then approves your account.
      </p>
      {error && (
        <div role="alert" className="login-error flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M10 6v4m0 3h.01" strokeLinecap="round" /></svg>
          <span>{error}</span>
        </div>
      )}
      <button type="submit" disabled={submitting} className="login-button flex h-[50px] w-full items-center justify-center gap-2 rounded-xl px-4 text-[15px] font-semibold">
        {submitting ? (
          <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" /> Sending</>
        ) : (
          "Request account"
        )}
      </button>
      {back}
    </form>
  );
}
