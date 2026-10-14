"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, isUnreachable } from "@/lib/apiClient";
import type { AuthUser } from "./types";

interface AuthContextValue {
  user: AuthUser;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthGate.");
  return value;
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [checking, setChecking] = useState(true);
  const [apiDown, setApiDown] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiFetch<AuthUser>("/auth/me")
      .then((signedInUser) => {
        if (cancelled) return;
        setUser(signedInUser);
        setApiDown(false);
        setChecking(false);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          const next = `${window.location.pathname}${window.location.search}`;
          router.replace(`/login?next=${encodeURIComponent(next)}`);
          return;
        }
        if (isUnreachable(error)) {
          setApiDown(true);
          setChecking(false);
          return;
        }
        setApiDown(true);
        setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt, router]);

  const signOut = useCallback(async () => {
    try {
      await apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" });
    } catch {
      // Continue to the sign-in page even if the API is momentarily unavailable.
    } finally {
      setChecking(true);
      setUser(null);
      router.replace("/login");
    }
  }, [router]);
  const context = useMemo(() => (user ? { user, signOut } : null), [user, signOut]);

  if (checking || (!user && !apiDown)) {
    return (
      <main className="flex h-dvh items-center justify-center bg-[#071827] text-white">
        <div className="flex flex-col items-center gap-4" role="status" aria-live="polite">
          <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/15">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/25 border-t-cyan-300" />
          </span>
          <span className="text-sm font-medium text-white/75">Securing your workspace…</span>
        </div>
      </main>
    );
  }

  if (apiDown || !user || !context) {
    return (
      <main className="flex h-dvh items-center justify-center bg-slate-50 px-5 text-slate-900">
        <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-xl shadow-slate-900/5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">JSAN REI</p>
          <h1 className="mt-3 text-xl font-semibold tracking-tight">Workspace unavailable</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The authentication service could not be reached. Check that the REI API is running, then try again.
          </p>
          <button
            type="button"
            onClick={() => {
              setApiDown(false);
              setChecking(true);
              setAttempt((value) => value + 1);
            }}
            className="mt-6 inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
          >
            Retry connection
          </button>
        </section>
      </main>
    );
  }

  return <AuthContext.Provider value={context}>{children}</AuthContext.Provider>;
}
