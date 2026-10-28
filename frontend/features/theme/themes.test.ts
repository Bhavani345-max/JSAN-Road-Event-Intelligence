import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { BRAND_STEPS, DEFAULT_THEME_ID, THEMES, themeById, themeStyle } from "./themes";

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

describe("colour themes", () => {
  it("start from JSAN Blue, exactly the brand colours of the stylesheet", () => {
    const css = readFileSync(fileURLToPath(new URL("../../app/globals.css", import.meta.url)), "utf8");
    const jsan = themeById(DEFAULT_THEME_ID);
    expect(THEMES[0]).toBe(jsan);
    for (const step of BRAND_STEPS) {
      expect(css).toContain(`--color-brand-${step}: ${jsan.palette[step]};`);
    }
  });

  it("each have a name, a unique id and every step", () => {
    expect(new Set(THEMES.map((theme) => theme.id)).size).toBe(THEMES.length);
    for (const theme of THEMES) {
      expect(theme.name).not.toBe("");
      expect(Object.keys(theme.palette).map(Number)).toEqual([...BRAND_STEPS]);
      for (const value of Object.values(theme.palette)) expect(value).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it.each(THEMES.map((theme) => [theme.name, theme] as const))(
    "%s keeps the console's text as readable as JSAN Blue",
    (_name, theme) => {
      const { palette } = theme;
      // White text on the sidebar and on filled buttons.
      expect(contrast("#ffffff", palette[600])).toBeGreaterThanOrEqual(7);
      expect(contrast("#ffffff", palette[700])).toBeGreaterThanOrEqual(7);
      expect(contrast("#ffffff", palette[500])).toBeGreaterThanOrEqual(4.5);
      // Brand text on the light pills (country choice) and on white.
      expect(contrast(palette[700], palette[50])).toBeGreaterThanOrEqual(7);
      expect(contrast(palette[800], "#ffffff")).toBeGreaterThanOrEqual(7);
    },
  );

  it("fall back to JSAN Blue for no choice or one that no longer exists", () => {
    expect(themeById(null).id).toBe(DEFAULT_THEME_ID);
    expect(themeById("sunset").id).toBe(DEFAULT_THEME_ID);
    expect(themeById("teal").name).toBe("Teal");
  });

  it("set every brand colour variable", () => {
    const style = themeStyle(themeById("green"));
    expect(Object.keys(style)).toEqual(BRAND_STEPS.map((step) => `--color-brand-${step}`));
    expect(style["--color-brand-600"]).toBe("#026330");
  });
});
