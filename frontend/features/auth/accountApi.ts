import { MIN_PASSWORD_LENGTH } from "@/features/profile/profile";
import { apiFetch, apiPost } from "@/lib/apiClient";

/** What the sign-in page can offer (decision 0045): registration and reset links need email. */
export interface AuthOptions {
  registration_open: boolean;
  email_reset: boolean;
  allowed_domains: string[];
}

export const CLOSED: AuthOptions = { registration_open: false, email_reset: false, allowed_domains: [] };

export function authOptions(): Promise<AuthOptions> {
  return apiFetch<AuthOptions>("/auth/options");
}

export function registerAccount(fullName: string, email: string, password: string): Promise<{ message: string }> {
  return apiPost("/auth/register", { full_name: fullName.trim(), email: email.trim(), password });
}

export function verifyEmail(token: string): Promise<{ ok: boolean }> {
  return apiPost("/auth/verify-email", { token });
}

export function requestResetLink(email: string): Promise<{ message: string }> {
  return apiPost("/auth/forgot", { email: email.trim() });
}

export function resetWithLink(token: string, next: string): Promise<{ ok: boolean }> {
  return apiPost("/auth/reset-password", { token, new_password: next });
}

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

// The same short list the API refuses (backend/app/services/account_service.py).
const COMMON = new Set([
  "password", "password1", "password123", "passw0rd", "12345678", "123456789", "1234567890",
  "qwerty123", "qwertyuiop", "11111111", "00000000", "iloveyou", "welcome1", "letmein1",
  "admin123", "administrator", "changeme", "abc12345", "jsan1234", "jsanconsulting",
]);

/** Why a chosen password is not accepted, as the API says it, or null. */
export function strongPasswordProblem(password: string, email = ""): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) return `Passwords must contain at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (COMMON.has(password.toLowerCase()) || new Set(password).size < 4) {
    return "This password is too easy to guess: use a longer phrase or a random password.";
  }
  const name = email.trim().toLowerCase().split("@")[0] ?? "";
  if (name.length >= 3 && password.toLowerCase().includes(name)) return "The password must not contain your email's name.";
  return null;
}

export interface RegistrationForm {
  name: string;
  email: string;
  password: string;
  confirmation: string;
}

/** Why the registration form cannot be sent, or null. */
export function registrationProblem(form: RegistrationForm, allowedDomains: string[]): string | null {
  if (form.name.trim() === "") return "Enter your full name.";
  const email = form.email.trim().toLowerCase();
  if (!EMAIL.test(email)) return "Enter your company email address.";
  if (allowedDomains.length > 0 && !allowedDomains.includes(email.split("@")[1])) {
    return `Use your company email address (${allowedDomains.map((domain) => `@${domain}`).join(", ")}).`;
  }
  const weak = strongPasswordProblem(form.password, email);
  if (weak) return weak;
  if (form.password !== form.confirmation) return "The two passwords are not the same.";
  return null;
}

/** The single-use token of an emailed link (?token=…), or null. */
export function linkToken(search: string): string | null {
  const token = new URLSearchParams(search).get("token");
  return token && token.length <= 200 ? token : null;
}
