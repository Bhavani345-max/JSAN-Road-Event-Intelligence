import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, endsSession, isSessionEnded, isUnreachable, SESSION_ENDED } from "./apiClient";

afterEach(() => vi.unstubAllGlobals());

describe("an API that cannot be reached", () => {
  it("is told apart from an API that answers with an error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("connection refused")));
    const down = await apiFetch("/events").catch((error: unknown) => error);
    expect(isUnreachable(down)).toBe(true);
    expect(String(down)).toMatch(/reconnects by itself/);
    expect(String(down)).toMatch(/start-rei\.cmd/);

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Event not found" }), { status: 404 })));
    const refused = await apiFetch("/events/NOPE").catch((error: unknown) => error);
    expect(isUnreachable(refused)).toBe(false);
  });
});

describe("a session that ended", () => {
  it("is a 401 from a route that needs one", () => {
    for (const path of ["/sources", "/events/coverage", "/events?view=validation", "/admin/users", "/auth/profile", "/auth/password", "/auth/recovery-codes"]) {
      expect(endsSession(path, 401)).toBe(true);
    }
  });

  it("is not a refused sign-in, a missing session or another failure", () => {
    for (const path of ["/auth/login", "/auth/me", "/auth/logout", "/auth/recover", "/auth/register", "/auth/forgot", "/auth/reset-password", "/auth/verify-email"]) {
      expect(endsSession(path, 401)).toBe(false);
    }
    expect(endsSession("/sources", 403)).toBe(false);
    expect(endsSession("/sources", 500)).toBe(false);
    expect(endsSession("/sources", null)).toBe(false);
  });

  it("is told apart from other errors", () => {
    expect(isSessionEnded(new ApiError("Authentication required.", 401))).toBe(true);
    expect(isSessionEnded(new ApiError("Not allowed.", 403))).toBe(false);
    expect(isSessionEnded(new Error("x"))).toBe(false);
  });

  it("is announced to the page, so AuthGate goes back to signing in", async () => {
    const dispatchEvent = vi.fn();
    vi.stubGlobal("window", { dispatchEvent });
    const refused = () => new Response(JSON.stringify({ detail: "Authentication required." }), { status: 401 });
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => refused()));
    const error = await apiFetch("/sources").catch((cause: unknown) => cause);
    expect(isSessionEnded(error)).toBe(true);
    expect(dispatchEvent).toHaveBeenCalledTimes(1);
    expect((dispatchEvent.mock.calls[0][0] as Event).type).toBe(SESSION_ENDED);
    // A wrong password at sign-in is not an ended session.
    await apiFetch("/auth/login", { method: "POST" }).catch(() => undefined);
    expect(dispatchEvent).toHaveBeenCalledTimes(1);
  });
});
