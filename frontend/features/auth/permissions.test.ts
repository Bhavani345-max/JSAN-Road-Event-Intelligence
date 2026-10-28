import { describe, expect, it } from "vitest";
import { canManageAccounts, canReview, canRunSources } from "./permissions";

const account = (role: string) => ({ id: "1", email: `${role}@example.com`, display_name: role, role });

describe("what an account may do in the console", () => {
  it("lets the admin review and run sources", () => {
    expect(canReview(account("admin"))).toBe(true);
    expect(canRunSources(account("admin"))).toBe(true);
  });

  it("lets the User only view", () => {
    expect(canReview(account("user"))).toBe(false);
    expect(canRunSources(account("user"))).toBe(false);
  });

  it("treats an unknown role, or no account, as view only", () => {
    expect(canReview(account("something-else"))).toBe(false);
    expect(canRunSources(null)).toBe(false);
  });
});

describe("managing accounts (decision 0044)", () => {
  it("is for the admin only: recovery codes, other accounts' temporary passwords", () => {
    expect(canManageAccounts(account("admin"))).toBe(true);
    for (const role of ["user", "reviewer", "viewer"]) expect(canManageAccounts(account(role))).toBe(false);
    expect(canManageAccounts(null)).toBe(false);
  });
});
