"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, isUnreachable } from "@/lib/apiClient";
import type { AuthUser } from "./types";

const RoadGlobe = dynamic(() => import("./RoadGlobe"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-full bg-cyan-300/[0.035] motion-reduce:animate-none" />,
});

function LockMark() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-5 w-5" aria-hidden="true">
      <path d="M7.5 10V7.5a4.5 4.5 0 0 1 9 0V10m-11 0h13a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 14v2" strokeLinecap="round" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <main className="min-h-dvh bg-[#f8fafc] lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)]">
      <section className="relative hidden min-h-dvh overflow-hidden bg-[#061622] text-white lg:flex lg:flex-col lg:justify-between lg:px-9 lg:py-8 xl:px-14 xl:py-10 2xl:px-[5vw]">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_74%_47%,rgba(8,145,178,0.18),transparent_44%),linear-gradient(135deg,#081c2c_0%,#061622_55%,#071b26_100%)]" />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.12] [background-image:linear-gradient(rgba(148,214,226,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(148,214,226,0.12)_1px,transparent_1px)] [background-size:76px_76px] [mask-image:linear-gradient(to_bottom,transparent,black_20%,black_80%,transparent)]" />

        <div className="pointer-events-none absolute inset-y-0 right-[-11%] z-0 w-[78%] opacity-90">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(14,116,144,0.12),transparent_60%)]" />
          <RoadGlobe />
        </div>

        <div className="relative z-10 flex items-center gap-3 login-reveal">
          <Image src="/jsan-mark.png" alt="JSAN" width={42} height={42} priority className="h-[42px] w-[42px] rounded-xl shadow-lg shadow-cyan-950/40" />
          <div>
            <p className="text-sm font-semibold tracking-wide">JSAN</p>
            <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-white/45">Road Event Intelligence</p>
          </div>
          <span className="ml-3 hidden h-6 items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-2.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-white/55 xl:inline-flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,.7)]" /> Operations
          </span>
        </div>

        <div className="pointer-events-none absolute right-[9%] top-[22%] z-10 login-float-slow">
          <div className="rounded-2xl border border-cyan-100/15 bg-[#0a2232]/65 px-4 py-3 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-[9px] font-semibold uppercase tracking-[0.18em] text-cyan-100/65">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /> Source footprint
            </div>
            <div className="mt-2 flex items-baseline gap-2.5 text-white">
              <span className="text-2xl font-semibold tracking-tight">08</span>
              <span className="text-[11px] text-white/55">regions</span>
              <span className="mx-0.5 h-4 w-px bg-white/15" />
              <span className="text-2xl font-semibold tracking-tight">06</span>
              <span className="text-[11px] text-white/55">countries</span>
            </div>
          </div>
        </div>

        <div className="pointer-events-none absolute bottom-[19%] right-[12%] z-10 login-float-delayed">
          <div className="flex max-w-[235px] items-center gap-3 rounded-2xl border border-white/10 bg-[#0a2232]/70 px-3.5 py-3 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-300/10 text-emerald-200 ring-1 ring-inset ring-emerald-200/15">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" className="h-[18px] w-[18px]" aria-hidden="true">
                <path d="M10 2.5 16 5v4.2c0 3.7-2.5 6.3-6 8.3-3.5-2-6-4.6-6-8.3V5l6-2.5Z" strokeLinejoin="round" />
                <path d="m7.5 9.8 1.7 1.7 3.4-3.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-white/90">Evidence first</p>
              <p className="mt-0.5 text-[10px] leading-4 text-white/45">Human reviewed road signals</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 max-w-[34rem] pb-7 xl:pb-10 login-reveal" style={{ animationDelay: "100ms" }}>
          <p className="mb-5 flex items-center gap-2.5 text-[10px] font-semibold uppercase tracking-[0.24em] text-cyan-200/75">
            <span className="h-px w-7 bg-cyan-300/70" /> A clearer view of the road
          </p>
          <h1 className="max-w-[31rem] text-[2.8rem] font-semibold leading-[1.06] tracking-[-0.055em] xl:text-[3.5rem] 2xl:text-[4rem]">
            See what&apos;s changing. <span className="text-cyan-200/90">Move with clarity.</span>
          </h1>
          <p className="mt-5 max-w-[27rem] text-[14px] leading-7 text-slate-300/70 xl:text-[15px]">
            Bring trusted local sources together. Review each event with its evidence, timing and exact location.
          </p>
          <div className="mt-8 flex items-center gap-3 text-[11px] text-white/50">
            <span className="flex -space-x-1.5" aria-hidden="true">
              <span className="h-6 w-6 rounded-full border-2 border-[#071827] bg-cyan-300" />
              <span className="h-6 w-6 rounded-full border-2 border-[#071827] bg-emerald-300" />
              <span className="h-6 w-6 rounded-full border-2 border-[#071827] bg-sky-400" />
            </span>
            <span>One workspace for evidence, context and decisions</span>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between border-t border-white/[0.09] pt-4 text-[10px] text-white/35">
          <span>© {new Date().getFullYear()} JSAN Consulting</span>
          <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300/80" /> Private operations workspace</span>
        </div>
      </section>

      <section className="flex min-h-dvh flex-col px-5 py-5 sm:px-9 lg:px-5 lg:py-7 xl:px-9 2xl:px-14">
        <div className="flex items-center gap-3 lg:hidden">
          <Image src="/jsan-mark.png" alt="JSAN" width={38} height={38} priority className="h-[38px] w-[38px] rounded-xl" />
          <div>
            <p className="text-sm font-semibold tracking-tight text-brand-900">JSAN Road Event Intelligence</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400">Secure workspace</p>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-[390px] flex-1 flex-col justify-center py-10 login-reveal" style={{ animationDelay: "80ms" }}>
          <div className="mb-8">
            <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100">
              <LockMark />
            </div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-brand-700">Operator access</p>
            <h2 className="mt-2 text-[2rem] font-semibold tracking-[-0.045em] text-slate-950">Welcome back</h2>
            <p className="mt-2.5 text-[13px] leading-6 text-slate-500">
              Sign in to continue to your road event operations workspace.
            </p>
          </div>

          <form onSubmit={submit} className="space-y-4.5">
            <div>
              <label htmlFor="email" className="mb-2 block text-[12px] font-semibold text-slate-700">Work email</label>
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
                  className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3.5 text-[13px] text-slate-900 shadow-sm shadow-slate-900/[0.025] outline-none transition duration-200 placeholder:text-slate-400 hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                />
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="password" className="block text-[12px] font-semibold text-slate-700">Password</label>
                <span className="text-[10px] font-medium text-slate-400">Case sensitive</span>
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
                  className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-12 text-[13px] text-slate-900 shadow-sm shadow-slate-900/[0.025] outline-none transition duration-200 placeholder:text-slate-400 hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
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
              <div id="login-error" role="alert" className="flex gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-[12px] leading-5 text-rose-800">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M10 6v4m0 3h.01" strokeLinecap="round" /></svg>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !email.trim() || password.length === 0}
              className="group flex h-[50px] w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-4 text-[13px] font-semibold text-white shadow-[0_8px_20px_-8px_rgba(0,70,116,.65)] transition duration-200 hover:-translate-y-0.5 hover:bg-brand-800 hover:shadow-[0_12px_24px_-9px_rgba(0,70,116,.6)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-200 disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-55 disabled:shadow-none"
            >
              {submitting ? (
                <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/35 border-t-white" /> Signing in securely</>
              ) : (
                <>Sign in <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5" strokeLinecap="round" strokeLinejoin="round" /></svg></>
              )}
            </button>
          </form>

          <div className="mt-6 flex items-start gap-3 rounded-xl border border-slate-200/80 bg-white/75 px-3.5 py-3.5 shadow-sm shadow-slate-900/[0.02]">
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
              <LockMark />
            </div>
            <p className="text-[11px] leading-[1.65] text-slate-500">Sessions expire automatically. Accounts are provisioned by your REI administrator.</p>
          </div>
        </div>

        <footer className="mx-auto flex w-full max-w-[390px] items-center justify-between gap-3 border-t border-slate-200/75 py-4 text-[10px] text-slate-400 lg:border-0">
          <span>© {new Date().getFullYear()} JSAN Consulting</span>
          <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Secure access</span>
        </footer>
      </section>
    </main>
  );
}
