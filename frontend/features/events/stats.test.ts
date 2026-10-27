import { describe, expect, it } from "vitest";
import { countWidthEm, formatCount, tileNumberSize } from "./stats";

// Geist semibold, tabular figures, as measured in Chrome (27 October 2026).
const MEASURED_DIGIT_EM = 0.624;
const MEASURED_COMMA_EM = 0.225;
const measured = (text: string) =>
  [...text].reduce((em, c) => em + (c === "," ? MEASURED_COMMA_EM : MEASURED_DIGIT_EM), 0);

/** The width inside one of the five tiles, in px, for a sidebar this wide. */
const tileInside = (sidebar: number) => (sidebar - 2 * 16 - 4 * 6) / 5 - 2 * 8;

/** The px size `tileNumberSize` gives inside a tile `inside` px wide. */
function resolve(size: string, inside: number): number {
  if (size === "1.5rem") return 24;
  const divisor = Number(/calc\(100cqi \/ ([\d.]+)\)/.exec(size)?.[1]);
  return Math.min(24, inside / divisor);
}

describe("stat tile numbers", () => {
  it("writes counts with thousands separators, as the rest of the console", () => {
    expect(formatCount(94804)).toBe("94,804");
    expect(formatCount(0)).toBe("0");
  });

  it("never measures a count narrower than it is drawn", () => {
    for (const text of ["0", "7", "1,284", "25,673", "94,804", "100,000", "1,000,000"]) {
      expect(countWidthEm(text)).toBeGreaterThanOrEqual(measured(text));
    }
  });

  it("keeps the full size while every number fits", () => {
    expect(tileNumberSize([0, 12, 340, 0, 5])).toBe("min(1.5rem, calc(100cqi / 1.92))");
    expect(resolve(tileNumberSize([0, 12, 340, 0, 5]), tileInside(420))).toBe(24);
    // Still loading: the tiles show placeholders.
    expect(tileNumberSize([])).toBe("1.5rem");
    expect(tileNumberSize([null, null])).toBe("1.5rem");
  });

  it("shrinks every number in the row to what the longest needs, so they match", () => {
    // Production on 27 October 2026: total 94,804, to review 94,800.
    const size = tileNumberSize([94804, 0, 0, 25673, 94800]);
    expect(size).toBe(tileNumberSize([94804]));
    expect(resolve(size, tileInside(420))).toBeLessThan(24);
  });

  it.each([
    ["the console's 420 px sidebar", 420],
    ["a 390 px phone", 390],
    ["a 360 px phone", 360],
  ])("fits up to seven digits in %s", (_, sidebar) => {
    const inside = tileInside(sidebar);
    for (const value of [9_999, 94_804, 999_999, 9_999_999]) {
      const px = resolve(tileNumberSize([value, 0]), inside);
      expect(measured(formatCount(value)) * px).toBeLessThanOrEqual(inside);
    }
  });
});
