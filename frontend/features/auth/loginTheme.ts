/**
 * Colour tokens for the sign-in page. They are the single source of truth:
 * the page injects them as CSS custom properties, the 3D scene reads the
 * scene colours, and loginTheme.test.ts measures WCAG contrast on them.
 */
export const loginColors = {
  // Page and scene
  pageBackground: "#050D17",
  sceneHaze: "#0B1A2C",
  roadBlue: "#168BCE",
  roadCyan: "#63D9F2",
  eventAmber: "#E9B44C",

  // White header bar (matches the console header)
  headerBackground: "#FFFFFF",
  headerTitleText: "#002C4A",
  headerSubtitleText: "#5F6E80",
  headerPillBackground: "#EEF6FB",
  headerPillText: "#004674",

  // Sign-in card (solid base colour under the slight translucency)
  cardBackground: "#0B1A2C",
  inputBackground: "#13233A",
  labelText: "#E6EDF5",
  bodyText: "#C5D1DE",
  placeholderText: "#9AAABB",
  helperText: "#A3B3C4",
  eyebrowText: "#63D9F2",
  focusRing: "#63D9F2",

  // Primary button
  buttonBackground: "#0F6FA8",
  buttonHoverBackground: "#0B5C8C",
  buttonText: "#FFFFFF",
  buttonDisabledBackground: "#1B2F46",
  buttonDisabledText: "#B3C2D3",

  // Feedback
  errorBackground: "#2B1B27",
  errorText: "#FFD9DD",
  successBackground: "#10302C",
  successText: "#C9F5E3",
} as const;

export type LoginColor = keyof typeof loginColors;

/** CSS custom properties consumed by the login-* rules in globals.css. */
export const loginCssVariables: Record<string, string> = {
  "--login-page": loginColors.pageBackground,
  "--login-header-bg": loginColors.headerBackground,
  "--login-header-title": loginColors.headerTitleText,
  "--login-header-subtitle": loginColors.headerSubtitleText,
  "--login-header-pill-bg": loginColors.headerPillBackground,
  "--login-header-pill-text": loginColors.headerPillText,
  "--login-card": loginColors.cardBackground,
  "--login-input-bg": loginColors.inputBackground,
  "--login-label": loginColors.labelText,
  "--login-body": loginColors.bodyText,
  "--login-placeholder": loginColors.placeholderText,
  "--login-helper": loginColors.helperText,
  "--login-eyebrow": loginColors.eyebrowText,
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
