import type { AuthUser } from "@/features/auth/types";
import { apiFetch, apiPost } from "@/lib/apiClient";

/** As the API requires (backend/app/services/auth_service.py). */
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_NAME_LENGTH = 120;

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Up to two letters for the account's round badge: "Pavan Kumar" -> "PK". */
export function initials(user: Pick<AuthUser, "display_name" | "email">): string {
  const words = user.display_name.split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  const text = letters.map((word) => [...word][0]).join("");
  return (text || [...user.email][0] || "?").toUpperCase();
}

/** The role as the console names it (decision 0032). */
export function roleLabel(role: string): string {
  if (role === "admin") return "Administrator";
  if (role === "reviewer") return "Reviewer";
  return "View-only";
}

export interface ProfileForm {
  name: string;
  email: string;
  currentPassword: string;
}

/** What POST /api/auth/profile takes: only what changes. */
export interface ProfileRequest {
  display_name?: string;
  email?: string;
  current_password?: string;
}

/**
 * The request for what the form changes, or why it cannot be sent. Both null:
 * nothing changed. A new email needs the current password.
 */
export function profileRequest(
  user: AuthUser,
  form: ProfileForm,
): { request: ProfileRequest | null; problem: string | null } {
  const name = form.name.split(/\s+/).filter(Boolean).join(" ");
  if (name === "") return { request: null, problem: "Enter your name." };
  if (name.length > MAX_NAME_LENGTH) {
    return { request: null, problem: `A name can have at most ${MAX_NAME_LENGTH} characters.` };
  }
  const email = form.email.trim().toLowerCase();
  if (!EMAIL.test(email)) return { request: null, problem: "Enter a valid email address." };
  const request: ProfileRequest = {};
  if (name !== user.display_name) request.display_name = name;
  if (email !== user.email) {
    if (form.currentPassword === "") {
      return { request: null, problem: "Enter your current password to change your email." };
    }
    request.email = email;
    request.current_password = form.currentPassword;
  }
  return { request: Object.keys(request).length > 0 ? request : null, problem: null };
}

/** Why a new password cannot be sent, or null. */
export function passwordProblem(current: string, next: string, confirmation: string): string | null {
  if (current === "") return "Enter your current password.";
  if (next.length < MIN_PASSWORD_LENGTH) {
    return `The new password needs at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (next !== confirmation) return "The two new passwords are not the same.";
  if (next === current) return "The new password is the same as the current one.";
  return null;
}

export function saveProfile(request: ProfileRequest): Promise<AuthUser> {
  return apiPost<AuthUser>("/auth/profile", request);
}

export function changePassword(current: string, next: string): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>("/auth/password", { current_password: current, new_password: next });
}

// --- account recovery (decision 0044) -------------------------------------------------

export interface RecoveryCodesStatus {
  remaining: number;
  total: number;
  created_at: string | null;
}

/** The characters of a recovery code (backend/app/services/auth_service.py): no i, l, o, 0 or 1. */
const CODE = /^[abcdefghjkmnpqrstuvwxyz23456789]{16}$/;

/** Whether what was typed can be a recovery code: 16 of its characters, dashes and spaces aside, any case. */
export function looksLikeRecoveryCode(text: string): boolean {
  return CODE.test(text.replace(/[\s-]/g, "").toLowerCase());
}

/** Why the forgot-password form cannot be sent, or null. */
export function recoveryProblem(email: string, code: string, next: string, confirmation: string): string | null {
  if (!EMAIL.test(email.trim().toLowerCase())) return "Enter your sign-in email.";
  if (!looksLikeRecoveryCode(code)) return "Enter one of your recovery codes, like abcd-efgh-jkmn-pqrs.";
  if (next.length < MIN_PASSWORD_LENGTH) {
    return `The new password needs at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (next !== confirmation) return "The two new passwords are not the same.";
  return null;
}

/** The text of the file a new set of codes is saved as. */
export function recoveryCodesFile(email: string, codes: string[], createdAt: Date): string {
  return [
    "JSAN Road Event Intelligence: recovery codes",
    `Account: ${email}`,
    `Created: ${createdAt.toISOString().slice(0, 16).replace("T", " ")} UTC`,
    "",
    "Each code works once, on the sign-in page under \"Forgot password?\".",
    "Keep them somewhere safe and private. Creating new codes cancels these.",
    "",
    ...codes,
    "",
  ].join("\n");
}

export function resetAccountPassword(
  accountId: string,
  currentPassword: string,
): Promise<{ account: AuthUser; temporary_password: string }> {
  return apiPost(`/auth/accounts/${encodeURIComponent(accountId)}/temporary-password`, {
    current_password: currentPassword,
  });
}

export function recoveryCodesStatus(): Promise<RecoveryCodesStatus> {
  return apiFetch<RecoveryCodesStatus>("/auth/recovery-codes");
}

export function createRecoveryCodes(currentPassword: string): Promise<{ codes: string[]; created_at: string }> {
  return apiPost("/auth/recovery-codes", { current_password: currentPassword });
}

export function recoverWithCode(
  email: string,
  code: string,
  next: string,
): Promise<{ ok: boolean; codes_left: number }> {
  return apiPost("/auth/recover", { email: email.trim(), recovery_code: code, new_password: next });
}
