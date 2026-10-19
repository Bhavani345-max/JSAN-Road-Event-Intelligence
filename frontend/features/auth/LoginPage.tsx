"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, isUnreachable } from "@/lib/apiClient";
import type { AuthUser } from "./types";

// The WebGL scene is only requested on large screens; phones and tablets keep
// the lightweight CSS backdrop and never download three.js.
const RoadScene = dynamic(() => import("./RoadScene"), { ssr: false });

const inputClass =
  "login-input h-12 w-full rounded-xl border border-white/[0.12] bg-white/[0.05] pl-10 pr-3.5 text-[14px] text-slate-50 outline-none transition duration-200 placeholder:text-slate-400/80 hover:border-white/20 hover:bg-white/[0.07] focus:border-cyan-300/60 focus:bg-white/[0.07] focus:ring-4 focus:ring-cyan-400/15 aria-[invalid=true]:border-rose-300/50";

function LockMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className={className} aria-hidden="true">
      <path d="M7.5 10V7.5a4.5 4.5 0 0 1 9 0V10m-11 0h13a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 14v2" strokeLinecap="round" />
    </svg>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <Image
        src="/jsan-mark.png"
        alt="JSAN"
        width={compact ? 36 : 40}
        height={compact ? 36 : 40}
        loading="eager"
        className={`${compact ? "h-9 w-9" : "h-10 w-10"} rounded-xl shadow-lg shadow-black/40 ring-1 ring-white/10`}
      />
      <div>
        <p className="text-[13px] font-semibold tracking-wide text-white">JSAN</p>
        <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-slate-300/70">Road Event Intelligence</p>
      </div>
    </div>
  );
}

const principles = [
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
    label: "Placed on the map",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4" aria-hidden="true">
        <path d="M10 17.5s-5.5-5.1-5.5-9a5.5 5.5 0 1 1 11 0c0 3.9-5.5 9-5.5 9Z" strokeLinejoin="round" />
        <circle cx="10" cy="8.5" r="1.9" />
      </svg>
    ),
  },
  {
    label: "Reviewed by people before it counts",
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
    <main className="relative isolate min-h-dvh overflow-hidden bg-[#050e18] text-white">
      {/* Decorative backdrop: CSS road grid everywhere, WebGL digital twin on desktop. */}
      <div aria-hidden="true" className="login-backdrop">
        <div className="login-floor" />
        <span className="login-beacon left-[82%] top-[21%] lg:left-[57%] lg:top-[63%]"><span className="login-beacon-beam" /></span>
        <span className="login-beacon login-beacon--teal hidden lg:block lg:left-[36%] lg:top-[73%]"><span className="login-beacon-beam" /></span>
        <span className="login-beacon hidden lg:block lg:left-[47%] lg:top-[51%]"><span className="login-beacon-beam" /></span>
      </div>
      {scene === "on" && (
        <div aria-hidden="true" className="absolute inset-0 hidden lg:block">
          <RoadScene onUnavailable={() => setScene("unavailable")} />
        </div>
      )}
      <div aria-hidden="true" className="login-veil" />

      <div className="relative z-10 mx-auto flex min-h-dvh w-full max-w-[1560px] flex-col px-5 py-5 sm:px-8 sm:py-6 lg:px-12 lg:py-7 xl:px-16">
        <header className="flex items-center justify-between gap-4 login-reveal">
          <Brand compact />
          <span className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-300/80 backdrop-blur-sm sm:inline-flex">
            <LockMark className="h-3.5 w-3.5 text-cyan-200/90" /> Private operations workspace
          </span>
        </header>

        <div className="flex flex-1 flex-col justify-center gap-10 py-8 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,430px)] lg:items-center lg:gap-16 lg:py-10 xl:grid-cols-[minmax(0,1fr)_minmax(0,450px)] xl:gap-24">
          <section className="max-w-[36rem] login-reveal" style={{ animationDelay: "90ms" }}>
            <p className="mb-5 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.26em] text-cyan-200/85 sm:text-[11px]">
              <span className="h-px w-8 bg-gradient-to-r from-cyan-300/90 to-cyan-300/0" /> Operations console
            </p>
            <h1 className="text-[2.1rem] font-semibold leading-[1.04] tracking-[-0.045em] text-white sm:text-[2.75rem] lg:text-[3.3rem] xl:text-[3.9rem] 2xl:text-[4.3rem]">
              See what&apos;s changing
              <br />
              <span className="bg-gradient-to-r from-cyan-200 via-sky-200 to-cyan-100/80 bg-clip-text text-transparent">on the road.</span>
            </h1>
            <p className="mt-5 max-w-[29rem] text-[14px] leading-7 text-slate-300/85 sm:text-[15px] lg:mt-6 lg:text-[16px] lg:leading-8">
              REI gathers road events from official feeds and local news, places each one on the map, and holds it for a person to review before it counts.
            </p>
            <ul className="mt-7 hidden flex-wrap gap-2.5 sm:flex lg:mt-9">
              {principles.map((principle) => (
                <li
                  key={principle.label}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] py-1.5 pl-2.5 pr-3.5 text-[12px] font-medium text-slate-200/90 backdrop-blur-sm"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-300/10 text-cyan-200">{principle.icon}</span>
                  {principle.label}
                </li>
              ))}
            </ul>
          </section>

          <section className="w-full max-w-[450px] self-center justify-self-end login-reveal lg:self-auto" style={{ animationDelay: "160ms" }}>
            <div className="login-panel rounded-[26px] border border-white/10 p-6 sm:p-8">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">Operator access</p>
                  <h2 className="mt-2 text-[1.75rem] font-semibold tracking-[-0.04em] text-white">Sign in</h2>
                </div>
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.02] text-cyan-100 shadow-inner shadow-white/5">
                  <LockMark />
                </div>
              </div>
              <p className="mt-2.5 text-[13px] leading-6 text-slate-300/80">
                Use the account provided by your REI administrator.
              </p>

              <form onSubmit={submit} className="mt-7 space-y-5">
                <div>
                  <label htmlFor="email" className="mb-2 block text-[12.5px] font-semibold text-slate-200">Work email</label>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true">
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
                      className={inputClass}
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <label htmlFor="password" className="block text-[12.5px] font-semibold text-slate-200">Password</label>
                    <span className="text-[11px] font-medium text-slate-400">Case sensitive</span>
                  </div>
                  <div className="relative">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true">
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
                      className={`${inputClass} pr-12`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((visible) => !visible)}
                      className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? (
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-[18px] w-[18px]" aria-hidden="true"><path d="M2 10s2.8-5 8-5 8 5 8 5-2.8 5-8 5-8-5-8-5Z" /><circle cx="10" cy="10" r="2" /><path d="m3 3 14 14" strokeLinecap="round" /></svg>
                      ) : (
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-[18px] w-[18px]" aria-hidden="true"><path d="M2 10s2.8-5 8-5 8 5 8 5-2.8 5-8 5-8-5-8-5Z" /><circle cx="10" cy="10" r="2" /></svg>
                      )}
                    </button>
                  </div>
                </div>

                {error && (
                  <div id="login-error" role="alert" className="flex gap-2.5 rounded-xl border border-rose-300/30 bg-rose-500/10 px-3.5 py-3 text-[12.5px] leading-5 text-rose-100">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="mt-0.5 h-4 w-4 shrink-0 text-rose-200" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M10 6v4m0 3h.01" strokeLinecap="round" /></svg>
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting || !email.trim() || password.length === 0}
                  className="group flex h-[50px] w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 px-4 text-[14px] font-semibold text-white shadow-[0_12px_30px_-10px_rgba(15,111,168,.85),inset_0_1px_0_rgba(255,255,255,.18)] transition duration-200 hover:-translate-y-0.5 hover:from-brand-400 hover:to-brand-500 hover:shadow-[0_16px_34px_-10px_rgba(15,111,168,.9),inset_0_1px_0_rgba(255,255,255,.22)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cyan-300/40 disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                >
                  {submitting ? (
                    <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/35 border-t-white" /> Signing in securely</>
                  ) : (
                    <>Sign in <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5" strokeLinecap="round" strokeLinejoin="round" /></svg></>
                  )}
                </button>
              </form>

              <p className="mt-6 flex items-start gap-2.5 border-t border-white/[0.08] pt-5 text-[12px] leading-5 text-slate-400">
                <LockMark className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
                Sessions expire automatically. Accounts are provisioned by your REI administrator.
              </p>
            </div>
          </section>
        </div>

        <footer className="flex items-center justify-between gap-3 border-t border-white/[0.08] pt-4 text-[11px] text-slate-400 login-reveal" style={{ animationDelay: "240ms" }}>
          <span>© {new Date().getFullYear()} JSAN Consulting</span>
          <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300/90 shadow-[0_0_10px_rgba(110,231,183,.6)]" /> Secure access</span>
        </footer>
      </div>
    </main>
  );
}
