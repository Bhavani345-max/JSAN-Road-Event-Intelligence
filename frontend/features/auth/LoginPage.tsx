"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, isUnreachable } from "@/lib/apiClient";
import type { AuthUser } from "./types";
import { loginCssVariables } from "./loginTheme";

// The WebGL scene is only requested on large screens; phones and tablets keep
// the lightweight CSS backdrop and never download three.js.
const RoadScene = dynamic(() => import("./RoadScene"), { ssr: false });

const themeStyle = loginCssVariables as CSSProperties;

function LockMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className} aria-hidden="true">
      <path d="M7.5 10V7.5a4.5 4.5 0 0 1 9 0V10m-11 0h13a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 14v2" strokeLinecap="round" />
    </svg>
  );
}

function Brand() {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <Image src="/jsan-mark.png" alt="JSAN" width={36} height={36} loading="eager" className="h-9 w-9 shrink-0 rounded-lg" />
      <div className="min-w-0">
        <p className="truncate text-[15px] font-semibold leading-5 tracking-tight text-[color:var(--login-header-title)]">JSAN</p>
        <p className="truncate text-[10.5px] font-medium uppercase leading-4 tracking-[0.18em] text-[color:var(--login-header-subtitle)]">Road Event Intelligence</p>
      </div>
    </div>
  );
}

const indicators = [
  {
    label: "Official feeds and local news",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true">
        <path d="M4 5.5a10.5 10.5 0 0 1 10.5 10.5M4 9.5a6.5 6.5 0 0 1 6.5 6.5" strokeLinecap="round" />
        <circle cx="5" cy="15" r="1.2" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    label: "Geolocated events",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true">
        <path d="M10 17.5s-5.5-5.1-5.5-9a5.5 5.5 0 1 1 11 0c0 3.9-5.5 9-5.5 9Z" strokeLinejoin="round" />
        <circle cx="10" cy="8.5" r="1.9" />
      </svg>
    ),
  },
  {
    label: "Human-reviewed intelligence",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true">
        <path d="M10 2.5 16 5v4.2c0 3.7-2.5 6.3-6 8.3-3.5-2-6-4.6-6-8.3V5l6-2.5Z" strokeLinejoin="round" />
        <path d="m7.5 9.8 1.7 1.7 3.4-3.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [succeeded, setSucceeded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scene, setScene] = useState<"off" | "on" | "unavailable">("off");

  useEffect(() => {
    const query = window.matchMedia("(min-width: 1024px)");
    const sync = () => setScene((current) => (current === "unavailable" ? current : query.matches ? "on" : "off"));
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch<AuthUser>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      setSucceeded(true);
      const requested = new URLSearchParams(window.location.search).get("next");
      const safeDestination = requested?.startsWith("/") && !requested.startsWith("//")
        ? requested
        : "/";
      router.replace(safeDestination);
      router.refresh();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setError("That email and password combination did not match. Try again.");
      } else if (cause instanceof ApiError && cause.status === 429) {
        setError("Too many attempts. Wait a few minutes before trying again.");
      } else if (isUnreachable(cause)) {
        setError("We could not reach the sign-in service. Check the connection and retry.");
      } else {
        setError(cause instanceof Error ? cause.message : "Sign-in could not be completed.");
      }
      setSubmitting(false);
    }
  }

  return (
    <main className="relative isolate flex min-h-dvh flex-col bg-[color:var(--login-page)] text-[color:var(--login-headline)]" style={themeStyle}>
      {/* White header bar, matching the console header. */}
      <header className="login-header relative z-20 flex h-14 shrink-0 items-center justify-between gap-3 px-5 sm:px-8 lg:px-12 xl:px-16">
        <Brand />
        <span className="login-header-pill hidden shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium sm:inline-flex">
          <LockMark className="h-3.5 w-3.5" /> Private operations workspace
        </span>
      </header>

      <div className="relative flex flex-1 flex-col overflow-hidden">
        {/* Decorative backdrop: CSS perspective grid everywhere, WebGL road network on desktop. */}
        <div aria-hidden="true" className="login-backdrop">
          <div className="login-floor" />
          <span className="login-beacon hidden lg:block lg:left-[57%] lg:top-[63%]" />
          <span className="login-beacon hidden lg:block lg:left-[47%] lg:top-[51%]" />
        </div>
        {scene === "on" && (
          <div aria-hidden="true" className="absolute inset-0 hidden lg:block">
            <RoadScene onUnavailable={() => setScene("unavailable")} />
          </div>
        )}
        <div aria-hidden="true" className="login-veil" />

        <div className="relative z-10 mx-auto flex w-full max-w-[1560px] flex-1 flex-col px-5 pb-5 pt-6 sm:px-8 sm:pb-6 lg:px-12 lg:pb-7 xl:px-16">
        <div className="flex flex-1 flex-col justify-center gap-10 py-6 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,420px)] lg:items-center lg:gap-16 lg:py-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,440px)] xl:gap-24">
          <section className="max-w-[36rem] login-reveal" style={{ animationDelay: "90ms" }}>
            <p className="mb-5 flex items-center gap-3 text-[10.5px] font-semibold uppercase tracking-[0.26em] text-[color:var(--login-eyebrow)] sm:text-[11px]">
              <span className="h-px w-8 bg-[color:var(--login-eyebrow)] opacity-70" /> Operations console
            </p>
            <h1 className="login-headline text-[2.1rem] font-semibold leading-[1.05] tracking-[-0.04em] sm:text-[2.7rem] lg:text-[3.2rem] xl:text-[3.7rem] 2xl:text-[4rem]">
              See what&apos;s changing
              <br />
              <span className="login-headline-accent">on the road.</span>
            </h1>
            <p className="mt-5 max-w-[29rem] text-[14.5px] leading-7 text-[color:var(--login-body)] sm:text-[15px] lg:mt-6 lg:text-[16px] lg:leading-8">
              REI gathers road events from official feeds and local news, geolocates them, and sends them for human review.
            </p>
            <ul className="mt-7 hidden flex-wrap gap-2.5 sm:flex lg:mt-9" aria-label="How REI works">
              {indicators.map((indicator) => (
                <li key={indicator.label} className="login-chip inline-flex items-center gap-2 rounded-full py-1.5 pl-2 pr-3.5 text-[12.5px] font-medium">
                  <span className="login-chip-icon flex h-6 w-6 items-center justify-center rounded-full">{indicator.icon}</span>
                  {indicator.label}
                </li>
              ))}
            </ul>
          </section>

          <section className="w-full max-w-[440px] self-center justify-self-end login-reveal lg:self-auto" style={{ animationDelay: "160ms" }}>
            <div className={`login-panel rounded-2xl p-6 sm:p-8 ${succeeded ? "login-panel--success" : ""}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10.5px] font-semibold uppercase tracking-[0.22em] text-[color:var(--login-eyebrow)]">Operator access</p>
                  <h2 className="mt-2 text-[1.7rem] font-semibold tracking-[-0.035em] text-[color:var(--login-headline)]">Sign in</h2>
                </div>
                <div className="login-chip-icon flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
                  <LockMark />
                </div>
              </div>
              <p className="mt-2 text-[13.5px] leading-6 text-[color:var(--login-body)]">
                Use the account provided by your REI administrator.
              </p>

              <form onSubmit={submit} className="mt-7 space-y-5" noValidate={false}>
                <div>
                  <label htmlFor="email" className="mb-2 block text-[13px] font-semibold text-[color:var(--login-label)]">Work email</label>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--login-placeholder)]" aria-hidden="true">
                      <rect x="2.5" y="4" width="15" height="12" rx="2" />
                      <path d="m3.5 5 6.5 5 6.5-5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="you@company.com"
                      aria-invalid={Boolean(error)}
                      aria-describedby={error ? "login-error" : undefined}
                      className="login-input h-12 w-full rounded-xl pl-10 pr-3.5 text-[14.5px]"
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <label htmlFor="password" className="block text-[13px] font-semibold text-[color:var(--login-label)]">Password</label>
                    <span className="text-[11.5px] font-medium text-[color:var(--login-helper)]">Case sensitive</span>
                  </div>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--login-placeholder)]" aria-hidden="true">
                      <rect x="3" y="8" width="14" height="9" rx="2" />
                      <path d="M6 8V6a4 4 0 0 1 8 0v2m-4 4v2" strokeLinecap="round" />
                    </svg>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Enter your password"
                      aria-invalid={Boolean(error)}
                      aria-describedby={error ? "login-error" : undefined}
                      className="login-input h-12 w-full rounded-xl pl-10 pr-[5.5rem] text-[14.5px]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((visible) => !visible)}
                      className="login-toggle absolute right-2 top-1/2 flex h-8 -translate-y-1/2 items-center gap-1.5 rounded-lg px-2.5 text-[11.5px] font-semibold"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? (
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true"><path d="M2 10s2.8-5 8-5 8 5 8 5-2.8 5-8 5-8-5-8-5Z" /><circle cx="10" cy="10" r="2" /><path d="m3 3 14 14" strokeLinecap="round" /></svg>
                      ) : (
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true"><path d="M2 10s2.8-5 8-5 8 5 8 5-2.8 5-8 5-8-5-8-5Z" /><circle cx="10" cy="10" r="2" /></svg>
                      )}
                      <span aria-hidden="true">{showPassword ? "Hide" : "Show"}</span>
                    </button>
                  </div>
                </div>

                {error && (
                  <div id="login-error" role="alert" className="login-error flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M10 6v4m0 3h.01" strokeLinecap="round" /></svg>
                    <span>{error}</span>
                  </div>
                )}

                {succeeded && (
                  <p role="status" className="login-status flex gap-2.5 rounded-xl px-3.5 py-3 text-[13px] leading-5">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="m6.5 10.2 2.3 2.3 4.7-4.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <span>Signed in. Opening your workspace.</span>
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting || !email.trim() || password.length === 0}
                  className={`login-button group flex h-[50px] w-full items-center justify-center gap-2 rounded-xl px-4 text-[14.5px] font-semibold ${succeeded ? "login-button--success" : ""}`}
                >
                  {succeeded ? (
                    <>
                      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4" aria-hidden="true"><path d="m4.5 10.5 3.5 3.5 7.5-8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      Signed in, opening your workspace
                    </>
                  ) : submitting ? (
                    <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" /> Signing in</>
                  ) : (
                    <>Sign in <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5" strokeLinecap="round" strokeLinejoin="round" /></svg></>
                  )}
                </button>
              </form>

              <p className="mt-6 flex items-start gap-2.5 border-t border-[color:var(--login-card-border)] pt-5 text-[12.5px] leading-5 text-[color:var(--login-helper)]">
                <LockMark className="mt-0.5 h-4 w-4 shrink-0" />
                Sessions expire automatically. Accounts are provisioned by your REI administrator.
              </p>
            </div>
          </section>
        </div>

        <footer className="flex items-center justify-between gap-3 border-t border-slate-200/80 pt-4 text-[11.5px] text-[color:var(--login-helper)] login-reveal" style={{ animationDelay: "240ms" }}>
          <span>© {new Date().getFullYear()} JSAN Consulting</span>
          <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Secure access</span>
        </footer>
        </div>
      </div>
    </main>
  );
}
