import { describe, expect, it } from "vitest";
import {
  canChangeRole,
  canResetPassword,
  DECISION_LABEL,
  decisionsFor,
  eventLabel,
  inSection,
  newAccountProblem,
  SECTIONS,
  waitingCount,
  type ManagedAccount,
} from "./users";

const SELF = "admin-1";
const account = (changes: Partial<ManagedAccount>): ManagedAccount => ({
  id: "u-1",
  email: "someone@jsan.example",
  display_name: "Someone",
  role: "user",
  status: "active",
  email_verified: true,
  must_change_password: false,
  registered_at: null,
  decided_at: null,
  decided_by: null,
  created_at: "2026-10-28T10:00:00Z",
  ...changes,
});

describe("User management (decision 0045)", () => {
  it("offers what the API allows for each status", () => {
    expect(decisionsFor(account({ status: "pending_approval" }), SELF)).toEqual(["approve", "reject"]);
    expect(decisionsFor(account({ status: "pending_approval", email_verified: false }), SELF)).toEqual(["reject"]);
    expect(decisionsFor(account({ status: "active" }), SELF)).toEqual(["suspend"]);
    expect(decisionsFor(account({ status: "suspended" }), SELF)).toEqual(["reactivate"]);
    expect(decisionsFor(account({ status: "rejected" }), SELF)).toEqual([]);
  });

  it("never offers administrators to stop themselves", () => {
    expect(decisionsFor(account({ id: SELF, role: "admin" }), SELF)).toEqual([]);
    expect(canResetPassword(account({ id: SELF, role: "admin" }), SELF)).toBe(false);
  });

  it("offers a temporary password and a role change for another active account, another admin's too (decision 0046)", () => {
    for (const can of [canResetPassword, canChangeRole]) {
      expect(can(account({}), SELF)).toBe(true);
      expect(can(account({ role: "admin", id: "admin-2" }), SELF)).toBe(true);
      expect(can(account({ id: SELF, role: "admin" }), SELF)).toBe(false);
      expect(can(account({ status: "suspended" }), SELF)).toBe(false);
      expect(can(account({ status: "pending_approval" }), SELF)).toBe(false);
    }
  });

  it("calls suspending deactivating, and shows registration sections only when they hold someone", () => {
    expect([DECISION_LABEL.suspend, DECISION_LABEL.reactivate]).toEqual(["Deactivate", "Activate"]);
    const shown = SECTIONS.filter((section) => !section.hideWhenEmpty).map((section) => section.label);
    expect(shown).toEqual(["Active", "Deactivated"]);
  });

  it("checks a new account's name and email before asking for the password", () => {
    expect(newAccountProblem("  ", "a@b.com")).toBe("Enter the person's full name.");
    expect(newAccountProblem("x".repeat(121), "a@b.com")).toMatch("120");
    expect(newAccountProblem("Asha Rao", "asha")).toBe("Enter a valid email address.");
    expect(newAccountProblem(" Asha Rao ", " Asha@Example.com ")).toBeNull();
  });

  it("counts only confirmed registrations as waiting", () => {
    const accounts = [
      account({ id: "a", status: "pending_approval" }),
      account({ id: "b", status: "pending_approval", email_verified: false }),
      account({ id: "c", status: "active" }),
    ];
    expect(waitingCount(accounts)).toBe(1);
    expect(inSection(accounts, "pending_approval").map((a) => a.id)).toEqual(["a", "b"]);
  });

  it("names the recorded events", () => {
    expect(eventLabel("account_approved")).toBe("Approved");
    expect(eventLabel("account_created")).toBe("Account created");
    expect(eventLabel("account_suspended")).toBe("Deactivated");
    expect(eventLabel("sign_in_locked")).toBe("Locked after failed sign-ins");
    expect(eventLabel("something_new")).toBe("something new");
  });
});
