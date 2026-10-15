import type { AuthUser } from "./types";

/**
 * What an account may do in the console, mirroring the API's checks
 * (backend/app/api/auth_deps.py, decision 0032). The API refuses anything
 * else regardless; the console only leaves out what would be refused.
 */
const REVIEW_ROLES: readonly string[] = ["admin", "reviewer"];
const ADMIN_ROLES: readonly string[] = ["admin"];

/** Record review decisions: status, severity, location, extensions, merges, manual entries. */
export function canReview(user: AuthUser | null | undefined): boolean {
  return !!user && REVIEW_ROLES.includes(user.role);
}

/** Run sources by hand ("Check", "Check all"). */
export function canRunSources(user: AuthUser | null | undefined): boolean {
  return !!user && ADMIN_ROLES.includes(user.role);
}
