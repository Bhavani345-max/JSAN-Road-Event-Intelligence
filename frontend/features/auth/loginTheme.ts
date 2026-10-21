/**
 * Colour tokens for the sign-in page (light theme). They are the single source
 * of truth: the page injects them as CSS custom properties, the 3D scene reads
 * the scene colours, and loginTheme.test.ts measures WCAG contrast on them.
 */
export const loginColors = {
  // Page and scene
  pageBackground: "#F4F7FB",
  pageWhite: "#FFFFFF",
  sceneHaze: "#F4F7FB",
  sceneGround: "#EDF1F6",
  sceneRoad: "#E2E8EF",
  sceneMassing: "#FFFFFF",
  roadBlue: "#168BCE",
  roadBlueDeep: "#0F6FA8",
  eventAmber: "#D97706",

  // Hero copy on the light page
  headlineText: "#0B1F33",
  accentText: "#0F6FA8",
  bodyText: "#475569",
  eyebrowText: "#004674",
  chipText: "#334155",

  // White header bar (matches the console header)
  headerBackground: "#FFFFFF",
  headerTitleText: "#002C4A",
  headerSubtitleText: "#5F6E80",
  headerPillBackground: "#EEF6FB",
  headerPillText: "#004674",

  // Sign-in card
  cardBackground: "#FFFFFF",
  cardBorder: "#E2E8F0",
  inputBackground: "#F8FAFC",
  inputBorder: "#CBD5E1",
  labelText: "#0F172A",
  placeholderText: "#5B6B7F",
  helperText: "#5B6B7F",
  focusRing: "#0F6FA8",

  // Primary button
  buttonBackground: "#0F6FA8",
  buttonHoverBackground: "#0B5C8C",
  buttonText: "#FFFFFF",
  buttonDisabledBackground: "#E2E8F0",
  buttonDisabledText: "#4B5A6C",

  // Feedback
  errorBackground: "#FFF1F2",
  errorText: "#9F1239",
  successBackground: "#ECFDF5",
  successText: "#065F46",
} as const;

export type LoginColor = keyof typeof loginColors;

/** CSS custom properties consumed by the login-* rules in globals.css. */
export const loginCssVariables: Record<string, string> = {
  "--login-page": loginColors.pageBackground,
  "--login-white": loginColors.pageWhite,
  "--login-headline": loginColors.headlineText,
  "--login-accent": loginColors.accentText,
  "--login-body": loginColors.bodyText,
  "--login-eyebrow": loginColors.eyebrowText,
  "--login-chip-text": loginColors.chipText,
  "--login-header-bg": loginColors.headerBackground,
  "--login-header-title": loginColors.headerTitleText,
  "--login-header-subtitle": loginColors.headerSubtitleText,
  "--login-header-pill-bg": loginColors.headerPillBackground,
  "--login-header-pill-text": loginColors.headerPillText,
  "--login-card": loginColors.cardBackground,
  "--login-card-border": loginColors.cardBorder,
  "--login-input-bg": loginColors.inputBackground,
  "--login-input-border": loginColors.inputBorder,
  "--login-label": loginColors.labelText,
  "--login-placeholder": loginColors.placeholderText,
  "--login-helper": loginColors.helperText,
  "--login-focus": loginColors.focusRing,
  "--login-button": loginColors.buttonBackground,
  "--login-button-hover": loginColors.buttonHoverBackground,
  "--login-button-text": loginColors.buttonText,
  "--login-button-disabled": loginColors.buttonDisabledBackground,
  "--login-button-disabled-text": loginColors.buttonDisabledText,
  "--login-error-bg": loginColors.errorBackground,
  "--login-error-text": loginColors.errorText,
  "--login-success-bg": loginColors.successBackground,
  "--login-success-text": loginColors.successText,
  "--login-road-blue": loginColors.roadBlue,
};

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const full = clean.length === 3 ? clean.split("").map((h) => h + h).join("") : clean;
  const value = Number.parseInt(full, 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

/** WCAG 2.x relative luminance of a hex colour. */
export function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG 2.x contrast ratio between two hex colours (1 to 21). */
export function contrastRatio(foreground: string, background: string): number {
  const a = relativeLuminance(foreground);
  const b = relativeLuminance(background);
  const [light, dark] = a > b ? [a, b] : [b, a];
  return (light + 0.05) / (dark + 0.05);
}
