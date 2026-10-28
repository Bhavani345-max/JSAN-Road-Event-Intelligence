import { apiFetch, apiPost } from "@/lib/apiClient";

/** An account as User management shows it (GET /api/admin/users, decision 0045). */
export interface ManagedAccount {
  id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  email_verified: boolean;
  must_change_password: boolean;
  registered_at: string | null;
  decided_at: string | null;
  decided_by: string | null;
  created_at: string;
}

export interface AccountEvent {
  kind: string;
  occurred_at: string;
  by: string;
  detail: string | null;
}

export type Decision = "approve" | "reject" | "suspend" | "reactivate";

// "suspended" in the API is what the page calls deactivated (decision 0046).
export const DECISION_LABEL: Record<Decision, string> = {
  approve: "Approve",
  reject: "Reject",
  suspend: "Deactivate",
  reactivate: "Activate",
};

/**
 * The sections of the page, in order. Registrations exist only while
 * self-registration is on (it is off, decision 0046): their sections show only
 * when they hold an account.
 */
export const SECTIONS: { status: string; label: string; empty: string; hideWhenEmpty?: boolean }[] = [
  { status: "pending_approval", label: "Waiting for approval", empty: "", hideWhenEmpty: true },
  { status: "active", label: "Active", empty: "No active account." },
  { status: "suspended", label: "Deactivated", empty: "No deactivated account." },
  { status: "rejected", label: "Rejected registrations", empty: "", hideWhenEmpty: true },
];

/** The roles an administrator gives (decision 0046). */
export type AssignableRole = "admin" | "user";
export const ROLE_CHOICES: { role: AssignableRole; label: string; detail: string }[] = [
  { role: "user", label: "User", detail: "View-only: events, maps and dashboards." },
  { role: "admin", label: "Admin", detail: "Full access, User management included." },
];

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Why a new account cannot be created yet, or null (the API checks the same). */
export function newAccountProblem(name: string, email: string): string | null {
  if (name.trim() === "") return "Enter the person's full name.";
  if (name.trim().length > 120) return "A name can have at most 120 characters.";
  if (!EMAIL.test(email.trim().toLowerCase())) return "Enter a valid email address.";
  return null;
}

export function inSection(accounts: ManagedAccount[], status: string): ManagedAccount[] {
  return accounts.filter((account) => account.status === status);
}

/**
 * What an administrator may decide about an account, as the API allows: a
 * registration that confirmed its email is approved or rejected (one that did not
 * only rejected); another active account suspended; a suspended one reactivated.
 */
export function decisionsFor(account: ManagedAccount, selfId: string): Decision[] {
  if (account.status === "pending_approval") return account.email_verified ? ["approve", "reject"] : ["reject"];
  if (account.status === "active") return account.id === selfId ? [] : ["suspend"];
  if (account.status === "suspended") return ["reactivate"];
  return [];
}

/** Whether the administrator can give this account a temporary password: any other
 * active account, another administrator's too (decisions 0044, 0046). */
export function canResetPassword(account: ManagedAccount, selfId: string): boolean {
  return account.status === "active" && account.id !== selfId;
}

/** Whether the administrator can change this account's role: another active account. */
export function canChangeRole(account: ManagedAccount, selfId: string): boolean {
  return account.status === "active" && account.id !== selfId;
}

/** Registrations that confirmed their email and wait for a decision: the header's badge. */
export function waitingCount(accounts: ManagedAccount[]): number {
  return accounts.filter((account) => account.status === "pending_approval" && account.email_verified).length;
}

const EVENT_LABEL: Record<string, string> = {
  registered: "Registered",
  email_verified: "Confirmed the email",
  account_approved: "Approved",
  account_rejected: "Rejected",
  account_suspended: "Deactivated",
  account_reactivated: "Activated",
  password_changed: "Changed the password",
  email_changed: "Changed the sign-in email",
  temporary_password_set: "Given a temporary password",
  temporary_password_set_on_server: "Given a temporary password on the server",
  account_created: "Account created",
  role_changed: "Role changed",
  recovery_codes_created: "Created recovery codes",
  recovery_codes_revoked: "Recovery codes cancelled",
  recovered_with_code: "Used a recovery code",
  sign_in_locked: "Locked after failed sign-ins",
  password_reset_requested: "Asked for a reset link",
  password_reset_with_link: "Reset the password with a link",
};

/** A security event in words; an unknown kind as it is. */
export function eventLabel(kind: string): string {
  return EVENT_LABEL[kind] ?? kind.replaceAll("_", " ");
}

export function listUsers(): Promise<ManagedAccount[]> {
  return apiFetch<ManagedAccount[]>("/admin/users");
}

export function decide(accountId: string, decision: Decision): Promise<ManagedAccount> {
  return apiPost<ManagedAccount>(`/admin/users/${encodeURIComponent(accountId)}/${decision}`);
}

export function createAccount(
  name: string,
  email: string,
  role: AssignableRole,
  currentPassword: string,
): Promise<{ account: ManagedAccount; temporary_password: string }> {
  return apiPost("/admin/users", {
    display_name: name.trim(),
    email: email.trim(),
    role,
    current_password: currentPassword,
  });
}

export function changeRole(accountId: string, role: AssignableRole, currentPassword: string): Promise<ManagedAccount> {
  return apiPost<ManagedAccount>(`/admin/users/${encodeURIComponent(accountId)}/role`, {
    role,
    current_password: currentPassword,
  });
}

export function accountHistory(accountId: string): Promise<AccountEvent[]> {
  return apiFetch<AccountEvent[]>(`/admin/users/${encodeURIComponent(accountId)}/history`);
}
