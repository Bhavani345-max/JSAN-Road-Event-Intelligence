import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, isUnreachable } from "./apiClient";

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
