import { describe, expect, it } from "vitest";
import { revealDelta } from "./reveal";

describe("revealDelta", () => {
  const view = { top: 100, bottom: 500 };

  it("leaves an item that is already visible where it is", () => {
    expect(revealDelta({ top: 200, bottom: 300 }, view)).toBe(0);
  });

  it("scrolls down just enough for an item below the view", () => {
    expect(revealDelta({ top: 520, bottom: 600 }, view)).toBe(108);
  });

  it("scrolls up just enough for an item above the view", () => {
    expect(revealDelta({ top: 40, bottom: 120 }, view)).toBe(-68);
  });

  it("aligns an item taller than the view by its top edge", () => {
    expect(revealDelta({ top: 300, bottom: 1000 }, view)).toBe(192);
  });
});
