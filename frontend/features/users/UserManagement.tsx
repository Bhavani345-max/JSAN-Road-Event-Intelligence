"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { useAuth } from "@/features/auth/AuthGate";
import { canManageAccounts } from "@/features/auth/permissions";
import ConfirmWithPassword, { copyText, errorText, PRIMARY, SECONDARY } from "@/features/profile/ConfirmWithPassword";
import { resetAccountPassword, roleLabel } from "@/features/profile/profile";
import { themeStyle, useTheme } from "@/features/theme/themes";
import {
  accountHistory,
  canChangeRole,
  canResetPassword,
  changeRole,
  createAccount,
  decide,
  DECISION_LABEL,
  decisionsFor,
  eventLabel,
  inSection,
  listUsers,
  newAccountProblem,
  ROLE_CHOICES,
  SECTIONS,
  type AccountEvent,
  type AssignableRole,
  type Decision,
  type ManagedAccount,
} from "./users";

const DANGER =
  "inline-flex h-8 items-center justify-center rounded-lg bg-white px-3 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-200 transition hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 disabled:opacity-50";

// What each decision does, said before it is made.
const CONSEQUENCE: Record<Decision, string> = {
  approve: "They can sign in with the view-only User role.",
  reject: "They cannot sign in. Their request stays on record.",
  suspend: "They are signed out at once and cannot sign in until activated again.",
  reactivate: "They can sign in again.",
};

const INPUT =
  "h-9 w-full rounded-lg bg-white px-3 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 outline-none transition focus:ring-2 focus:ring-brand-500";

/** A temporary password, shown once, with what to do with it. */
function TemporaryPassword({ name, password, onDone }: { name: string; password: string; onDone: () => void }) {
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);
  return (
    <div className="mt-3 space-y-2.5 rounded-xl bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
      <p className="text-xs text-slate-700">Temporary password for {name}:</p>
      <p className="rounded-lg bg-white p-2.5 text-center font-mono text-base tracking-wide text-slate-900 ring-1 ring-inset ring-slate-200">{password}</p>
      <p role="alert" className="text-xs leading-5 text-amber-900">
        <span className="font-semibold">Shown only now.</span> Give it to them in person or by phone. They choose
        their own password when they sign in.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={SECONDARY} onClick={async () => setCopied((await copyText(password)) ? "yes" : "no")}>Copy</button>
        <button type="button" className={PRIMARY} onClick={onDone}>Done</button>
        {copied && <span role="status" className="text-xs text-slate-500">{copied === "yes" ? "Copied." : "Copying is blocked here: select it and copy it."}</span>}
      </div>
    </div>
  );
}

/** Creating an account (decision 0046): name, email, role; a temporary password shown once. */
function AddUser({ onCreated }: { onCreated: (account: ManagedAccount) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AssignableRole>("user");
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ account: ManagedAccount; password: string } | null>(null);

  function reset() {
    setOpen(false);
    setName("");
    setEmail("");
    setRole("user");
    setConfirming(false);
    setError(null);
    setCreated(null);
  }

  function next(event: FormEvent) {
    event.preventDefault();
    const problem = newAccountProblem(name, email);
    setError(problem);
    if (!problem) setConfirming(true);
  }

  if (!open) {
    return (
      <button type="button" className={PRIMARY} onClick={() => setOpen(true)}>
        Add a user
      </button>
    );
  }
  return (
    <section aria-labelledby="add-user" className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
      <h2 id="add-user" className="text-sm font-semibold text-slate-900">Add a user</h2>
      {created ? (
        <>
          <p role="status" className="mt-2 text-xs font-medium text-emerald-700">
            Account created for {created.account.display_name} ({created.account.email}) as{" "}
            {ROLE_CHOICES.find((choice) => choice.role === created.account.role)?.label ?? created.account.role}.
          </p>
          <TemporaryPassword name={created.account.display_name} password={created.password} onDone={reset} />
        </>
      ) : (
        <form onSubmit={next} className="mt-3 space-y-3" noValidate>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="new-user-name" className="mb-1 block text-xs font-medium text-slate-700">Full name</label>
              <input id="new-user-name" className={INPUT} value={name} maxLength={120} disabled={confirming} onChange={(event) => setName(event.target.value)} autoFocus />
            </div>
            <div>
              <label htmlFor="new-user-email" className="mb-1 block text-xs font-medium text-slate-700">Official email</label>
              <input id="new-user-email" type="email" autoCapitalize="none" spellCheck={false} className={INPUT} value={email} disabled={confirming} onChange={(event) => setEmail(event.target.value)} />
            </div>
          </div>
          <fieldset>
            <legend className="mb-1 text-xs font-medium text-slate-700">Role</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {ROLE_CHOICES.map((choice) => (
                <label
                  key={choice.role}
                  className={`flex cursor-pointer items-start gap-2.5 rounded-lg p-2.5 text-xs ring-1 ring-inset ${
                    role === choice.role ? "bg-brand-50 ring-brand-300" : "ring-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <input type="radio" name="new-user-role" value={choice.role} checked={role === choice.role} disabled={confirming} onChange={() => setRole(choice.role)} className="mt-0.5" />
                  <span>
                    <span className="block font-semibold text-slate-900">{choice.label}</span>
                    <span className="text-slate-600">{choice.detail}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && <p role="alert" className="text-xs font-medium text-red-700">{error}</p>}
          {!confirming && (
            <div className="flex gap-2">
              <button type="submit" className={PRIMARY}>Continue</button>
              <button type="button" className={SECONDARY} onClick={reset}>Cancel</button>
            </div>
          )}
        </form>
      )}
      {/* Its own form, after the details: a form inside a form is not valid HTML. */}
      {!created && confirming && (
        <ConfirmWithPassword
          id="new-user-password"
          action="Create account"
          onCancel={() => setConfirming(false)}
          onConfirm={async (password) => {
            const result = await createAccount(name, email, role, password);
            setConfirming(false);
            setCreated({ account: result.account, password: result.temporary_password });
            onCreated(result.account);
          }}
        />
      )}
    </section>
  );
}

function when(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function History({ accountId }: { accountId: string }) {
  const [events, setEvents] = useState<AccountEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    accountHistory(accountId)
      .then((loaded) => !cancelled && setEvents(loaded))
      .catch((cause: unknown) => !cancelled && setError(errorText(cause)));
    return () => {
      cancelled = true;
    };
  }, [accountId]);
  if (error) return <p role="alert" className="mt-3 text-xs text-red-700">{error}</p>;
  if (!events) return <p className="mt-3 text-xs text-slate-500">Loading history…</p>;
  if (events.length === 0) return <p className="mt-3 text-xs text-slate-500">Nothing recorded yet.</p>;
  return (
    <ol className="mt-3 space-y-1.5 border-l-2 border-slate-200 pl-3">
      {events.map((event, index) => (
        <li key={`${event.occurred_at}-${index}`} className="text-xs leading-5 text-slate-700">
          <span className="font-semibold text-slate-900">{eventLabel(event.kind)}</span>
          {event.detail && <span className="text-slate-500"> · {event.detail}</span>}
          <span className="block text-[11px] text-slate-500">
            {when(event.occurred_at)} · by {event.by}
          </span>
        </li>
      ))}
    </ol>
  );
}

function AccountRow({ account, selfId, onChanged }: { account: ManagedAccount; selfId: string; onChanged: (account: ManagedAccount) => void }) {
  const [confirming, setConfirming] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [temporary, setTemporary] = useState<string | null>(null);
  const [changingRole, setChangingRole] = useState(false);
  const decisions = decisionsFor(account, selfId);
  const otherRole = ROLE_CHOICES.find((choice) => choice.role !== account.role) ?? ROLE_CHOICES[0];

  async function run(decision: Decision) {
    setBusy(true);
    setError(null);
    try {
      onChanged(await decide(account.id, decision));
      setConfirming(null);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {account.display_name}
            {account.id === selfId && <span className="font-normal text-slate-500"> (you)</span>}
          </p>
          <p className="truncate text-xs text-slate-500">{account.email}</p>
          <p className="mt-1.5 flex flex-wrap gap-1.5">
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{roleLabel(account.role)}</span>
            {account.status === "pending_approval" && (
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${
                  account.email_verified ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-amber-50 text-amber-800 ring-amber-200"
                }`}
              >
                {account.email_verified ? "Email confirmed" : "Email not confirmed yet"}
              </span>
            )}
            {account.must_change_password && (
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800 ring-1 ring-inset ring-amber-200">
                Temporary password, not yet changed
              </span>
            )}
          </p>
          <p className="mt-1.5 text-[11px] leading-4 text-slate-500">
            {account.registered_at ? `Registered ${when(account.registered_at)}` : `Created ${when(account.created_at)}`}
            {account.decided_at && ` · last decision ${when(account.decided_at)}${account.decided_by ? ` by ${account.decided_by}` : ""}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {decisions.map((decision) => (
            <button
              key={decision}
              type="button"
              disabled={busy}
              className={decision === "approve" || decision === "reactivate" ? PRIMARY : DANGER}
              onClick={() => setConfirming(decision)}
            >
              {DECISION_LABEL[decision]}
            </button>
          ))}
          {account.status === "pending_approval" && !account.email_verified && (
            <span className="self-center text-[11px] text-slate-500" title="Approval needs a confirmed email">
              Approve after they confirm
            </span>
          )}
          {canChangeRole(account, selfId) && !changingRole && (
            <button type="button" className={SECONDARY} onClick={() => setChangingRole(true)}>Make {otherRole.label}</button>
          )}
          {canResetPassword(account, selfId) && !resetting && !temporary && (
            <button type="button" className={SECONDARY} onClick={() => setResetting(true)}>Reset password</button>
          )}
          <button type="button" className={SECONDARY} aria-expanded={showHistory} onClick={() => setShowHistory((open) => !open)}>
            {showHistory ? "Hide history" : "History"}
          </button>
        </div>
      </div>

      {confirming && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
          <p className="min-w-0 flex-1 text-xs leading-5 text-slate-700">
            <span className="font-semibold">{DECISION_LABEL[confirming]} {account.display_name}?</span> {CONSEQUENCE[confirming]}
          </p>
          <button type="button" disabled={busy} className={confirming === "approve" || confirming === "reactivate" ? PRIMARY : DANGER} onClick={() => run(confirming)}>
            {busy ? "Working…" : DECISION_LABEL[confirming]}
          </button>
          <button type="button" disabled={busy} className={SECONDARY} onClick={() => setConfirming(null)}>Cancel</button>
        </div>
      )}
      {error && <p role="alert" className="mt-2 text-xs font-medium text-red-700">{error}</p>}

      {resetting && (
        <ConfirmWithPassword
          id={`reset-${account.id}`}
          action="Set temporary password"
          onCancel={() => setResetting(false)}
          onConfirm={async (password) => {
            const result = await resetAccountPassword(account.id, password);
            setResetting(false);
            setTemporary(result.temporary_password);
            onChanged({ ...account, must_change_password: true });
          }}
        />
      )}
      {temporary && <TemporaryPassword name={account.display_name} password={temporary} onDone={() => setTemporary(null)} />}
      {changingRole && (
        <>
          <p className="mt-3 text-xs leading-5 text-slate-700">
            <span className="font-semibold">Make {account.display_name} {otherRole.label === "Admin" ? "an Admin" : "a User"}?</span>{" "}
            {otherRole.detail} It applies at once.
          </p>
          <ConfirmWithPassword
            id={`role-${account.id}`}
            action={`Make ${otherRole.label}`}
            onCancel={() => setChangingRole(false)}
            onConfirm={async (password) => {
              onChanged(await changeRole(account.id, otherRole.role, password));
              setChangingRole(false);
            }}
          />
        </>
      )}
      {showHistory && <History accountId={account.id} />}
    </li>
  );
}

/** Administrators' User management (decision 0045): registrations, accounts, their history. */
export default function UserManagement() {
  const { user } = useAuth();
  const theme = useTheme();
  const [accounts, setAccounts] = useState<ManagedAccount[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = canManageAccounts(user);

  const load = useCallback(() => {
    listUsers()
      .then(setAccounts)
      .catch((cause: unknown) => setError(errorText(cause)));
  }, []);
  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const replace = (changed: ManagedAccount) =>
    setAccounts((list) => list?.map((account) => (account.id === changed.id ? changed : account)) ?? null);

  return (
    <div className="min-h-dvh bg-slate-50 text-slate-900" style={themeStyle(theme) as CSSProperties}>
      <header className="flex h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Image src="/jsan-mark.png" alt="JSAN" width={32} height={32} className="h-8 w-8 shrink-0" />
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-brand-800">User management</h1>
        </div>
        <Link href="/" className={SECONDARY}>Back to the console</Link>
      </header>
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-6">
        {isAdmin && accounts && (
          <AddUser onCreated={(created) => setAccounts((list) => (list ? [created, ...list] : [created]))} />
        )}
        {!isAdmin ? (
          <p className="rounded-xl bg-white p-5 text-sm text-slate-700 ring-1 ring-inset ring-slate-200">
            Only administrators manage users.
          </p>
        ) : error ? (
          <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700 ring-1 ring-inset ring-red-200">{error}</p>
        ) : !accounts ? (
          <p className="text-sm text-slate-500">Loading accounts…</p>
        ) : (
          SECTIONS.map((section) => {
            const listed = inSection(accounts, section.status);
            if (section.hideWhenEmpty && listed.length === 0) return null;
            return (
              <section key={section.status} aria-labelledby={`section-${section.status}`}>
                <h2 id={`section-${section.status}`} className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {section.label} <span className="text-slate-400">({listed.length})</span>
                </h2>
                {listed.length === 0 ? (
                  <p className="text-xs text-slate-500">{section.empty}</p>
                ) : (
                  <ul className="space-y-2.5">
                    {listed.map((account) => (
                      <AccountRow key={account.id} account={account} selfId={user.id} onChanged={replace} />
                    ))}
                  </ul>
                )}
              </section>
            );
          })
        )}
      </main>
    </div>
  );
}
