import { describe, expect, it } from "vitest";
import { contrastRatio, hexToRgb, loginColors, relativeLuminance } from "./loginTheme";

describe("contrast helpers", () => {
  it("parses hex colours and computes WCAG luminance", () => {
    expect(hexToRgb("#FFFFFF")).toEqual([255, 255, 255]);
    expect(hexToRgb("#000")).toEqual([0, 0, 0]);
    expect(relativeLuminance("#FFFFFF")).toBeCloseTo(1, 5);
    expect(relativeLuminance("#000000")).toBe(0);
    expect(contrastRatio("#FFFFFF", "#000000")).toBeCloseTo(21, 5);
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
  });
});

describe("sign-in page colour pairs meet WCAG AA (4.5:1) for text on the light theme", () => {
  const textPairs: [string, string, string][] = [
    ["button text on enabled button", loginColors.buttonText, loginColors.buttonBackground],
    ["button text on hovered button", loginColors.buttonText, loginColors.buttonHoverBackground],
    ["disabled button text on disabled button", loginColors.buttonDisabledText, loginColors.buttonDisabledBackground],
    ["placeholder on input", loginColors.placeholderText, loginColors.inputBackground],
    ["typed value on input", loginColors.labelText, loginColors.inputBackground],
    ["label on card", loginColors.labelText, loginColors.cardBackground],
    ["body copy on card", loginColors.bodyText, loginColors.cardBackground],
    ["helper text on card", loginColors.helperText, loginColors.cardBackground],
    ["eyebrow on card", loginColors.eyebrowText, loginColors.cardBackground],
    ["error text on error box", loginColors.errorText, loginColors.errorBackground],
    ["success text on success box", loginColors.successText, loginColors.successBackground],
    ["header title on white header", loginColors.headerTitleText, loginColors.headerBackground],
    ["header subtitle on white header", loginColors.headerSubtitleText, loginColors.headerBackground],
    ["header pill text on pill", loginColors.headerPillText, loginColors.headerPillBackground],
    ["headline on page background", loginColors.headlineText, loginColors.pageBackground],
    ["headline accent on page background", loginColors.accentText, loginColors.pageBackground],
    ["eyebrow on page background", loginColors.eyebrowText, loginColors.pageBackground],
    ["hero copy on page background", loginColors.bodyText, loginColors.pageBackground],
    ["helper/footer text on page background", loginColors.helperText, loginColors.pageBackground],
    ["chip text on white chip", loginColors.chipText, loginColors.pageWhite],
    ["hero copy on the scene haze (scene dissolves into page)", loginColors.bodyText, loginColors.sceneHaze],
  ];

  it.each(textPairs)("%s", (_label, foreground, background) => {
    expect(contrastRatio(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the focus ring visible against the card, the input and the page (>= 3:1, non-text)", () => {
    expect(contrastRatio(loginColors.focusRing, loginColors.cardBackground)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(loginColors.focusRing, loginColors.inputBackground)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(loginColors.focusRing, loginColors.pageBackground)).toBeGreaterThanOrEqual(3);
  });

  it("documents that white on the road blue alone would fail, which is why the button is darker", () => {
    expect(contrastRatio("#FFFFFF", loginColors.roadBlue)).toBeLessThan(4.5);
    expect(contrastRatio(loginColors.buttonText, loginColors.buttonBackground)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the scene dissolving into the page: haze equals the page background", () => {
    expect(loginColors.sceneHaze).toBe(loginColors.pageBackground);
  });
});
