"use client";

import { useEffect, useId, useRef, useState } from "react";
import { canManageAccounts } from "@/features/auth/permissions";
import type { AuthUser } from "@/features/auth/types";
import { saveAppearance, useAppearance } from "@/features/theme/appearance";
import { saveTheme, THEMES, useTheme } from "@/features/theme/themes";
import {
  changePassword,
  initials,
  MAX_NAME_LENGTH,
  MIN_PASSWORD_LENGTH,
  passwordProblem,
  profileRequest,
  roleLabel,
  saveProfile,
} from "./profile";
import SecurityTab from "./SecurityTab";

interface ProfileDialogProps {
  open: boolean;
  onClose: () => void;
  user: AuthUser;
  onUserChange: (user: AuthUser) => void;
}

type Tab = "profile" | "password" | "theme" | "security";
const TABS: { id: Tab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "password", label: "Password" },
  { id: "theme", label: "Theme colour" },
];
// Administrators also keep recovery codes and reset other accounts' passwords (decision 0044).
const ADMIN_TABS: { id: Tab; label: string }[] = [...TABS, { id: "security", label: "Security" }];

type Outcome = { kind: "ok" | "error"; text: string } | null;

const INPUT =
  "h-9 w-full rounded-lg bg-white px-3 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 outline-none transition placeholder:text-slate-400 focus:ring-2 focus:ring-brand-500 disabled:bg-slate-50";
const LABEL = "mb-1 block text-xs font-medium text-slate-700";
const PRIMARY =
  "inline-flex h-9 items-center justify-center rounded-lg bg-brand-600 px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

function Message({ outcome }: { outcome: Outcome }) {
  if (!outcome) return null;
  return (
    <p
      role={outcome.kind === "error" ? "alert" : "status"}
      className={`text-xs font-medium ${outcome.kind === "error" ? "text-red-700" : "text-emerald-700"}`}
    >
      {outcome.text}
    </p>
  );
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "The change could not be saved. Try again.";
}

function ProfileTab({ user, onUserChange }: { user: AuthUser; onUserChange: (user: AuthUser) => void }) {
  const [name, setName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email);
  const [currentPassword, setCurrentPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const emailChanged = email.trim().toLowerCase() !== user.email;
  const { request, problem } = profileRequest(user, { name, email, currentPassword });

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (problem) return setOutcome({ kind: "error", text: problem });
    if (!request) return setOutcome({ kind: "ok", text: "Nothing has changed." });
    setSaving(true);
    setOutcome(null);
    try {
      const updated = await saveProfile(request);
      onUserChange(updated);
      setName(updated.display_name);
      setEmail(updated.email);
      setCurrentPassword("");
      setOutcome({
        kind: "ok",
        text: request.email
          ? "Saved. Sign in with your new email from now on; other browsers were signed out."
          : "Saved.",
      });
    } catch (error) {
      setOutcome({ kind: "error", text: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3.5" noValidate>
      <div>
        <label className={LABEL} htmlFor="profile-name">Name</label>
        <input
          id="profile-name"
          className={INPUT}
          value={name}
          maxLength={MAX_NAME_LENGTH}
          autoComplete="name"
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <div>
        <label className={LABEL} htmlFor="profile-email">Sign-in email</label>
        <input
          id="profile-email"
          type="email"
          className={INPUT}
          value={email}
          autoComplete="email"
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      {emailChanged && (
        <div>
          <label className={LABEL} htmlFor="profile-current-password">Current password</label>
          <input
            id="profile-current-password"
            type="password"
            className={INPUT}
            value={currentPassword}
            autoComplete="current-password"
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
          <p className="mt-1 text-[11px] leading-4 text-slate-500">
            Needed to change your sign-in email. Other browsers signed in to this account will be signed out.
          </p>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button type="submit" className={PRIMARY} disabled={saving || (!request && !problem)}>
          {saving ? "Saving…" : "Save changes"}
        </button>
        <Message outcome={outcome} />
      </div>
    </form>
  );
}

function PasswordTab() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [saving, setSaving] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const problem = passwordProblem(current, next, confirmation);
    if (problem) return setOutcome({ kind: "error", text: problem });
    setSaving(true);
    setOutcome(null);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirmation("");
      setOutcome({ kind: "ok", text: "Password changed. Other browsers signed in to this account were signed out." });
    } catch (error) {
      setOutcome({ kind: "error", text: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3.5" noValidate>
      <div>
        <label className={LABEL} htmlFor="password-current">Current password</label>
        <input id="password-current" type="password" className={INPUT} value={current} autoComplete="current-password" onChange={(event) => setCurrent(event.target.value)} />
      </div>
      <div>
        <label className={LABEL} htmlFor="password-new">New password</label>
        <input id="password-new" type="password" className={INPUT} value={next} autoComplete="new-password" onChange={(event) => setNext(event.target.value)} />
        <p className="mt-1 text-[11px] leading-4 text-slate-500">
          At least {MIN_PASSWORD_LENGTH} characters. A long random one from a password manager is safest.
        </p>
      </div>
      <div>
        <label className={LABEL} htmlFor="password-confirm">New password again</label>
        <input id="password-confirm" type="password" className={INPUT} value={confirmation} autoComplete="new-password" onChange={(event) => setConfirmation(event.target.value)} />
      </div>
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button type="submit" className={PRIMARY} disabled={saving}>
          {saving ? "Changing…" : "Change password"}
        </button>
        <Message outcome={outcome} />
      </div>
    </form>
  );
}

function ThemeTab() {
  const theme = useTheme();
  const appearance = useAppearance();
  return (
    <div className="space-y-3">
      {/* The header's light/dark switch too (decision 0051): one choice, kept in this browser. */}
      <div role="radiogroup" aria-label="Appearance" className="grid grid-cols-2 gap-2">
        {(["light", "dark"] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={appearance === option}
            onClick={() => saveAppearance(option)}
            className={`rounded-xl p-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
              appearance === option
                ? "bg-slate-50 text-slate-900 ring-2 ring-slate-900/70"
                : "text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {option === "light" ? "Light" : "Dark"}
          </button>
        ))}
      </div>
      <div role="radiogroup" aria-label="Theme colour" className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {THEMES.map((option) => {
          const checked = option.id === theme.id;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={checked}
              onClick={() => saveTheme(option.id)}
              className={`flex items-center gap-2.5 rounded-xl p-2 text-left text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                checked ? "bg-slate-50 text-slate-900 ring-2 ring-slate-900/70" : "text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
              }`}
            >
              <span
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                style={{ background: `linear-gradient(135deg, ${option.palette[500]}, ${option.palette[700]})` }}
              >
                {checked && (
                  <svg viewBox="0 0 16 16" fill="none" stroke="white" strokeWidth="2.2" className="h-3.5 w-3.5">
                    <path d="m3.5 8.5 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </span>
              {option.name}
            </button>
          );
        })}
      </div>
      <p className="text-[11px] leading-4 text-slate-500">
        Changes the sidebar, header and buttons at once. Kept in this browser only; event colours on the map stay
        the same.
      </p>
    </div>
  );
}

/** The signed-in account's details, password and theme colour (decision 0043). */
export default function ProfileDialog({ open, onClose, user, onUserChange }: ProfileDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [tab, setTab] = useState<Tab>("profile");
  const tabsId = useId();
  const tabs = canManageAccounts(user) ? ADMIN_TABS : TABS;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      // Straight into the first field, not the close button.
      dialog.querySelector<HTMLInputElement>("input")?.focus();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  function onTabKey(event: React.KeyboardEvent, index: number) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const nextIndex = (index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    setTab(tabs[nextIndex].id);
    document.getElementById(`${tabsId}-${tabs[nextIndex].id}`)?.focus();
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={`${tabsId}-title`}
      // Escape closes the dialog; tell the header.
      onClose={onClose}
      // A click on the dimmed backdrop (the dialog element itself) closes it.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className="m-auto max-h-[calc(100dvh-2rem)] w-[min(28rem,calc(100vw-2rem))] overflow-hidden rounded-2xl bg-white p-0 text-slate-900 shadow-2xl ring-1 ring-slate-900/10 backdrop:bg-slate-900/40"
    >
      {open && (
        <div className="flex max-h-[calc(100dvh-2rem)] flex-col">
          <div className="flex items-start gap-3 border-b border-slate-100 px-5 pb-4 pt-5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
              {initials(user)}
            </span>
            <div className="min-w-0 flex-1">
              <h2 id={`${tabsId}-title`} className="truncate text-sm font-semibold text-slate-900">
                {user.display_name}
              </h2>
              <p className="truncate text-xs text-slate-500">{user.email}</p>
              <span className="mt-1 inline-flex rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-100">
                {roleLabel(user.role)}
              </span>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="-mr-1 -mt-1 flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
                <path d="m4 4 8 8M12 4l-8 8" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div role="tablist" aria-label="Profile and settings" className="flex gap-1 border-b border-slate-100 px-4">
            {tabs.map((option, index) => (
              <button
                key={option.id}
                id={`${tabsId}-${option.id}`}
                type="button"
                role="tab"
                aria-selected={tab === option.id}
                aria-controls={`${tabsId}-${option.id}-panel`}
                tabIndex={tab === option.id ? 0 : -1}
                onClick={() => setTab(option.id)}
                onKeyDown={(event) => onTabKey(event, index)}
                className={`-mb-px border-b-2 px-2.5 py-2.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 ${
                  tab === option.id
                    ? "border-brand-600 text-brand-700"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div
            id={`${tabsId}-${tab}-panel`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-${tab}`}
            className="min-h-0 flex-1 overflow-y-auto px-5 py-4"
          >
            {tab === "profile" && <ProfileTab user={user} onUserChange={onUserChange} />}
            {tab === "password" && <PasswordTab />}
            {tab === "theme" && <ThemeTab />}
            {tab === "security" && canManageAccounts(user) && <SecurityTab user={user} />}
          </div>
        </div>
      )}
    </dialog>
  );
}
