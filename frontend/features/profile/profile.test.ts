import { describe, expect, it } from "vitest";
import type { AuthUser } from "@/features/auth/types";
import {
  initials,
  looksLikeRecoveryCode,
  passwordProblem,
  profileRequest,
  recoveryCodesFile,
  recoveryProblem,
  roleLabel,
} from "./profile";

const USER: AuthUser = { id: "1", email: "admin@example.com", display_name: "Admin", role: "admin" };
const form = (changes: Partial<{ name: string; email: string; currentPassword: string }> = {}) => ({
  name: USER.display_name,
  email: USER.email,
  currentPassword: "",
  ...changes,
});

describe("profile form", () => {
  it("sends nothing when nothing changed", () => {
    expect(profileRequest(USER, form())).toEqual({ request: null, problem: null });
    // The same email in another case, a name with extra spaces.
    expect(profileRequest(USER, form({ name: "  Admin ", email: " Admin@Example.com " }))).toEqual({
      request: null,
      problem: null,
    });
  });

  it("sends a new name alone, tidied", () => {
    expect(profileRequest(USER, form({ name: " Pavan   Kumar " })).request).toEqual({ display_name: "Pavan Kumar" });
  });

  it("asks for the current password before a new email", () => {
    expect(profileRequest(USER, form({ email: "new@example.com" })).problem).toBe(
      "Enter your current password to change your email.",
    );
    expect(profileRequest(USER, form({ email: "New@Example.com", currentPassword: "secret 123" })).request).toEqual({
      email: "new@example.com",
      current_password: "secret 123",
    });
  });

  it("refuses a blank or long name and an email that is not one", () => {
    expect(profileRequest(USER, form({ name: "   " })).problem).toBe("Enter your name.");
    expect(profileRequest(USER, form({ name: "x".repeat(121) })).problem).toMatch("at most 120");
    for (const email of ["", "admin", "admin@", "a b@example.com", "admin@example"]) {
      expect(profileRequest(USER, form({ email, currentPassword: "x" })).problem).toBe("Enter a valid email address.");
    }
  });
});

describe("new password", () => {
  it("needs the current one, eight characters, the same twice and a change", () => {
    expect(passwordProblem("", "new password", "new password")).toBe("Enter your current password.");
    expect(passwordProblem("old", "short", "short")).toMatch("at least 8");
    expect(passwordProblem("old", "new password", "new passw0rd")).toBe("The two new passwords are not the same.");
    expect(passwordProblem("same password", "same password", "same password")).toMatch("same as the current");
    expect(passwordProblem("old", "new password", "new password")).toBeNull();
  });
});

describe("account badge", () => {
  it("shows up to two initials, or the email's first letter", () => {
    expect(initials({ display_name: "Pavan Kumar", email: "p@example.com" })).toBe("PK");
    expect(initials({ display_name: "Ana María de la Cruz", email: "a@example.com" })).toBe("AC");
    expect(initials({ display_name: "admin", email: "a@example.com" })).toBe("A");
    expect(initials({ display_name: " ", email: "zed@example.com" })).toBe("Z");
  });

  it("names the roles", () => {
    expect(roleLabel("admin")).toBe("Administrator");
    expect(roleLabel("user")).toBe("View-only");
    expect(roleLabel("reviewer")).toBe("Reviewer");
  });
});

describe("forgot password with a recovery code (decision 0044)", () => {
  const CODE = "abcd-efgh-jkmn-pqrs";

  it("takes a code with or without dashes, in any case", () => {
    for (const code of [CODE, "ABCD-EFGH-JKMN-PQRS", "abcd efgh jkmn pqrs", "abcdefghjkmnpqrs"]) {
      expect(looksLikeRecoveryCode(code)).toBe(true);
    }
    // Too short, or with characters a code never has (i, l, o, 0, 1).
    for (const code of ["abcd-efgh", "abcd-efgh-jkmn-pqr0", "ilo1-efgh-jkmn-pqrs", ""]) {
      expect(looksLikeRecoveryCode(code)).toBe(false);
    }
  });

  it("checks the form before sending it", () => {
    expect(recoveryProblem("admin", CODE, "new password", "new password")).toBe("Enter your sign-in email.");
    expect(recoveryProblem("admin@example.com", "1234", "new password", "new password")).toMatch("recovery codes");
    expect(recoveryProblem("admin@example.com", CODE, "short", "short")).toMatch("at least 8");
    expect(recoveryProblem("admin@example.com", CODE, "new password", "other password")).toMatch("not the same");
    expect(recoveryProblem(" Admin@Example.com ", CODE.toUpperCase(), "new password", "new password")).toBeNull();
  });

  it("saves new codes as a text file that says how to use them", () => {
    const text = recoveryCodesFile("admin@example.com", [CODE, "qrst-uvwx-yz23-4567"], new Date("2026-10-28T11:20:00Z"));
    expect(text).toContain("Account: admin@example.com");
    expect(text).toContain("Created: 2026-10-28 11:20 UTC");
    expect(text).toContain("Each code works once");
    expect(text.trim().split("\n").slice(-2)).toEqual([CODE, "qrst-uvwx-yz23-4567"]);
  });
});
