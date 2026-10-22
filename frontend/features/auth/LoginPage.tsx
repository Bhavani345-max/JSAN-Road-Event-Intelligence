"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, isUnreachable } from "@/lib/apiClient";
import type { AuthUser } from "./types";
import { loginCssVariables } from "./loginTheme";

// The WebGL scene is only requested on large screens; phones and tablets show
// a still image of the same scene and never download three.js.
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

function EyeMark({ crossed }: { crossed: boolean }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-[18px] w-[18px]" aria-hidden="true">
      <path d="M2 10s2.8-5 8-5 8 5 8 5-2.8 5-8 5-8-5-8-5Z" />
      <circle cx="10" cy="10" r="2" />
      {crossed && <path d="m3 3 14 14" strokeLinecap="round" />}
    </svg>
  );
}

function Brand() {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <Image src="/jsan-mark.png" alt="" width={34} height={34} loading="eager" className="h-[34px] w-[34px] shrink-0 rounded-lg" />
      <span className="text-[19px] font-bold leading-none tracking-[-0.02em] text-[color:var(--login-header-title)]">JSAN</span>
      <span aria-hidden="true" className="h-6 w-px shrink-0 bg-[color:var(--login-divider)]" />
      <span className="truncate text-[10.5px] font-semibold uppercase leading-none tracking-[0.2em] text-[color:var(--login-header-subtitle)] sm:text-[11px]">
        Road Event Intelligence
      </span>
    </div>
  );
}

const features = [
  {
    title: "Official feeds & local news",
    detail: "Every event keeps its source",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]" aria-hidden="true">
        <path d="M4 5.5a10.5 10.5 0 0 1 10.5 10.5M4 9.5a6.5 6.5 0 0 1 6.5 6.5" strokeLinecap="round" />
        <circle cx="5" cy="15" r="1.2" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    title: "Geolocated events",
    detail: "Source geometry or OpenStreetMap places",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]" aria-hidden="true">
        <path d="M10 17.5s-5.5-5.1-5.5-9a5.5 5.5 0 1 1 11 0c0 3.9-5.5 9-5.5 9Z" strokeLinejoin="round" />
        <circle cx="10" cy="8.5" r="1.9" />
      </svg>
    ),
  },
  {
    title: "Human-reviewed intelligence",
    detail: "Approved by a reviewer, never automatically",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]" aria-hidden="true">
        <path d="M10 2.5 16 5v4.2c0 3.7-2.5 6.3-6 8.3-3.5-2-6-4.6-6-8.3V5l6-2.5Z" strokeLinejoin="round" />
        <path d="m7.5 9.8 1.7 1.7 3.4-3.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    title: "Monitor the lifecycle",
    detail: "From review to expiry",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-[18px] w-[18px]" aria-hidden="true">
        <path d="M4 16V11m4 5V7m4 9v-6m4 6V4" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showReset, setShowReset] = useState(false);
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
    <main className="login-screen relative isolate flex h-dvh flex-col overflow-hidden bg-[color:var(--login-page)] text-[color:var(--login-headline)]" style={themeStyle}>
      {/* Decorative backdrop: a still of the city everywhere, the live WebGL city on desktop. */}
      <div aria-hidden="true" className="login-backdrop" />
      {scene === "on" && (
        <div aria-hidden="true" className="absolute inset-0 hidden lg:block">
          <RoadScene onUnavailable={() => setScene("unavailable")} />
        </div>
      )}
      <div aria-hidden="true" className="login-veil" />

      <header className="relative z-20 mx-auto flex h-16 w-full max-w-[1560px] shrink-0 items-center justify-between gap-3 px-5 sm:px-8 lg:px-12 xl:px-16">
        <Brand />
        <span className="login-header-pill hidden shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[11.5px] font-medium sm:inline-flex">
          <LockMark className="h-3.5 w-3.5" /> Operations console
        </span>
      </header>

      <div className="relative z-10 mx-auto flex min-h-0 w-full max-w-[1560px] flex-1 flex-col px-5 pb-5 sm:px-8 sm:pb-6 lg:px-12 lg:pb-7 xl:px-16">
        <div className="flex min-h-0 flex-1 flex-col justify-center pt-4 sm:pt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,400px)] lg:items-center lg:gap-10 lg:py-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,452px)] xl:gap-24">
          <section className="login-hero max-w-[34rem] shrink-0 login-reveal" style={{ animationDelay: "90ms" }}>
            <h1 className="login-headline text-[2.5rem] font-bold leading-[1.02] tracking-[-0.045em] sm:text-[3.1rem] lg:text-[3.5rem] xl:text-[4.1rem] 2xl:text-[4.5rem]">
              See what&apos;s
              <br />
              <span className="login-headline-accent">changing</span>
              <br />
              on the road.
            </h1>
            <p className="login-hero-copy mt-5 max-w-[27rem] text-[15px] leading-7 lg:max-w-[24rem] xl:max-w-[27rem] text-[color:var(--login-body)] lg:mt-6 lg:text-[16.5px] lg:leading-8">
              REI collects road events from official feeds, detects them in local news, places each one on the map and sends it for human review.
            </p>
            <ul className="login-features mt-10 hidden lg:grid lg:grid-cols-1 lg:gap-y-[18px]" aria-label="How REI works">
              {features.map((feature) => (
                <li key={feature.title} className="flex items-center gap-3.5">
                  <span className="login-feature-icon flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">{feature.icon}</span>
                  <span className="min-w-0">
                    <span className="block text-[14.5px] font-semibold leading-5 text-[color:var(--login-headline)]">{feature.title}</span>
                    <span className="block text-[12.5px] leading-5 text-[color:var(--login-helper)]">{feature.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {/* Phones and tablets: a band of the city between the copy and the card. */}
          <div aria-hidden="true" className="login-city-band lg:hidden">
            <div className="login-city-image" />
          </div>

          <section className="relative w-full max-w-[452px] shrink-0 self-center justify-self-end login-reveal lg:self-auto" style={{ animationDelay: "160ms" }}>
            <div className={`login-panel rounded-[22px] p-6 sm:p-9 ${succeeded ? "login-panel--success" : ""}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[color:var(--login-eyebrow)]">Operator access</p>
                  <h2 className="mt-2 text-[1.9rem] font-bold tracking-[-0.035em] text-[color:var(--login-headline)]">Sign in</h2>
                </div>
                <div className="login-feature-icon flex h-11 w-11 shrink-0 items-center justify-center rounded-xl">
                  <LockMark />
                </div>
              </div>
              <p className="login-card-helper mt-1.5 text-[13.5px] leading-6 text-[color:var(--login-body)]">
                Use the account provided by your REI administrator.
              </p>

              {/* One message at a time keeps the card one height on the locked screen:
                  signing in closes the password note, opening the note clears an old error. */}
              <form
                onSubmit={(event) => {
                  setShowReset(false);
                  void submit(event);
                }}
                className="login-form mt-7 space-y-5"
                noValidate={false}
              >
                <div>
                  <label htmlFor="email" className="mb-2 block text-[13px] font-semibold text-[color:var(--login-label)]">Work email</label>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--login-placeholder)]" aria-hidden="true">
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
                      placeholder="Enter your work email"
                      aria-invalid={Boolean(error)}
                      aria-describedby={error ? "login-error" : undefined}
                      className="login-input h-[50px] w-full rounded-xl pl-11 pr-3.5 text-[14.5px]"
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <label htmlFor="password" className="block text-[13px] font-semibold text-[color:var(--login-label)]">Password</label>
                    <span className="text-[11.5px] font-medium text-[color:var(--login-helper)]">Case sensitive</span>
                  </div>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--login-placeholder)]" aria-hidden="true">
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
                      className="login-input h-[50px] w-full rounded-xl pl-11 pr-14 text-[14.5px]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((visible) => !visible)}
                      className="login-toggle absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      <EyeMark crossed={showPassword} />
                    </button>
                  </div>
                  <div className="mt-2.5 flex justify-end">
                    <button
                      type="button"
                      onClick={() => {
                        if (!showReset) setError(null);
                        setShowReset(!showReset);
                      }}
                      className="login-link rounded text-[12.5px] font-semibold"
                      aria-expanded={showReset}
                      aria-controls="login-reset-help"
                    >
                      Forgot password?
                    </button>
                  </div>
                  {showReset && (
                    <p id="login-reset-help" className="login-note mt-2 rounded-xl px-3.5 py-2.5 text-[12.5px] leading-5">
                      Passwords are reset by your REI administrator. Ask them to set a new one for your account.
                    </p>
                  )}
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
                  className={`login-button group flex h-[52px] w-full items-center justify-center gap-2 rounded-xl px-4 text-[15px] font-semibold ${succeeded ? "login-button--success" : ""}`}
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

              <p className="login-session-note mt-6 flex items-start gap-2.5 border-t border-[color:var(--login-card-border)] pt-5 text-[12.5px] leading-5 text-[color:var(--login-helper)]">
                <LockMark className="mt-0.5 h-4 w-4 shrink-0" />
                Sessions expire automatically. Accounts are provisioned by your REI administrator.
              </p>
            </div>
          </section>
        </div>

        <footer className="login-footer mt-4 flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-2 pt-3 text-[11.5px] text-[color:var(--login-helper)] login-reveal lg:mt-0" style={{ animationDelay: "240ms" }}>
          <span className="flex items-center gap-3">
            <span>© {new Date().getFullYear()} JSAN Consulting</span>
            <span aria-hidden="true" className="hidden h-3 w-px bg-[color:var(--login-divider)] sm:block" />
            <span className="hidden sm:inline">Road Event Intelligence</span>
          </span>
          <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Secure access</span>
        </footer>
      </div>
    </main>
  );
}
