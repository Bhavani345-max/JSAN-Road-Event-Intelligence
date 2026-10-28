"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { AuthUser } from "@/features/auth/types";
import ConfirmWithPassword, { copyText, errorText, PRIMARY, SECONDARY } from "./ConfirmWithPassword";
import { createRecoveryCodes, recoveryCodesFile, recoveryCodesStatus, type RecoveryCodesStatus } from "./profile";

function RecoveryCodes({ user }: { user: AuthUser }) {
  const [status, setStatus] = useState<RecoveryCodesStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [codes, setCodes] = useState<{ list: string[]; createdAt: Date } | null>(null);
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    recoveryCodesStatus()
      .then((loaded) => !cancelled && setStatus(loaded))
      .catch((error: unknown) => !cancelled && setLoadError(errorText(error)));
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  if (codes) {
    const file = recoveryCodesFile(user.email, codes.list, codes.createdAt);
    return (
      <div className="space-y-3">
        <p role="alert" className="rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900 ring-1 ring-inset ring-amber-200">
          <span className="font-semibold">Shown only now.</span> Save or print these codes and keep them somewhere
          safe and private (a password manager, or printed and locked away). Each works once. Your earlier codes no
          longer work.
        </p>
        <ol className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl bg-slate-50 p-3 font-mono text-[13px] text-slate-900 ring-1 ring-inset ring-slate-200">
          {codes.list.map((code) => (
            <li key={code}>{code}</li>
          ))}
        </ol>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={SECONDARY} onClick={async () => setCopied((await copyText(file)) ? "yes" : "no")}>
            Copy all
          </button>
          <a className={SECONDARY} href={`data:text/plain;charset=utf-8,${encodeURIComponent(file)}`} download="rei-recovery-codes.txt">
            Download .txt
          </a>
          <button
            type="button"
            className={PRIMARY}
            onClick={() => {
              setCodes(null);
              setCopied(null);
              setRefresh((n) => n + 1);
            }}
          >
            I have stored them
          </button>
          {copied && (
            <span role="status" className="text-xs text-slate-500">
              {copied === "yes" ? "Copied." : "Copying is blocked here: select the codes and copy them."}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <p className="text-xs leading-5 text-slate-600">
        If you forget your password, use one of these codes on the sign-in page under &ldquo;Forgot password?&rdquo;.
        Each code works once.
      </p>
      {loadError && <p role="alert" className="text-xs font-medium text-red-700">{loadError}</p>}
      {status && (
        <p className="text-xs font-medium text-slate-800">
          {status.total === 0
            ? "No recovery codes yet."
            : `${status.remaining} of ${status.total} codes left · created ${new Date(status.created_at ?? "").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`}
        </p>
      )}
      {status && status.remaining <= 3 && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900 ring-1 ring-inset ring-amber-200">
          {status.total === 0
            ? "Create them now: without a code, a forgotten administrator password can only be reset by a developer on the server."
            : `Only ${status.remaining} left: create a new set.`}
        </p>
      )}
      {confirming ? (
        <ConfirmWithPassword
          id="recovery-codes-password"
          action="Create codes"
          onCancel={() => setConfirming(false)}
          onConfirm={async (password) => {
            const created = await createRecoveryCodes(password);
            setConfirming(false);
            setCodes({ list: created.codes, createdAt: new Date(created.created_at) });
          }}
        />
      ) : (
        <button type="button" className={PRIMARY} onClick={() => setConfirming(true)}>
          {status && status.total > 0 ? "Create new codes" : "Create recovery codes"}
        </button>
      )}
      {status && status.total > 0 && !confirming && (
        <p className="text-[11px] leading-4 text-slate-500">Creating new codes cancels the current ones.</p>
      )}
    </div>
  );
}

/** Administrators: recovery codes for their own account (decision 0044); other accounts in User management (0045, 0046). */
export default function SecurityTab({ user }: { user: AuthUser }) {
  return (
    <div className="space-y-5">
      <section aria-labelledby="security-codes">
        <h3 id="security-codes" className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Your recovery codes
        </h3>
        <RecoveryCodes user={user} />
      </section>
      <section aria-labelledby="security-accounts" className="border-t border-slate-100 pt-4">
        <h3 id="security-accounts" className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Other accounts
        </h3>
        <p className="text-xs leading-5 text-slate-600">
          Add users, give them the Admin or User role, deactivate accounts, and give someone who forgot their
          password a temporary one.
        </p>
        <Link href="/users" className={`${SECONDARY} mt-2.5`}>
          Open User management
        </Link>
      </section>
    </div>
  );
}
