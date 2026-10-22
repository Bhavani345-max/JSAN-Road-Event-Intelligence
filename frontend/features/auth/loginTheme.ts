/**
 * Colour tokens for the sign-in page (light theme). They are the single source
 * of truth: the page injects them as CSS custom properties, the 3D scene reads
 * the scene colours, and loginTheme.test.ts measures WCAG contrast on them.
 */
export const loginColors = {
  // Page and scene
  pageBackground: "#F3F7FC",
  pageWhite: "#FFFFFF",
  sceneHaze: "#F3F7FC",
  sceneGround: "#E7EDF4",
  sceneMassing: "#FFFFFF",

  // Hero copy on the light page
  headlineText: "#0B1F3A",
  accentText: "#1667D6",
  bodyText: "#475569",
  eyebrowText: "#1D5FB8",
  featureIconBackground: "#E6F0FC",

  // Header (sits on the page, no bar)
  headerTitleText: "#0B1F3A",
  headerSubtitleText: "#5F6E80",
  headerPillBackground: "#FFFFFF",
  headerPillBorder: "#D3E2F3",
  headerPillText: "#1D4F91",
  divider: "#C5D2E1",

  // Sign-in card
  cardBackground: "#FFFFFF",
  cardBorder: "#E3EAF2",
  inputBackground: "#FFFFFF",
  inputBorder: "#CFD9E5",
  labelText: "#0F172A",
  placeholderText: "#5B6B7F",
  helperText: "#5B6B7F",
  focusRing: "#1667D6",
  linkText: "#1667D6",
  noteBackground: "#EEF5FD",
  noteText: "#1D4F91",

  // Primary button: a vertical blue gradient (both stops carry white text)
  buttonBackground: "#1A6FDB",
  buttonBackgroundEnd: "#0E5BC4",
  buttonHoverBackground: "#155FC4",
  buttonHoverBackgroundEnd: "#0B4FAD",
  buttonText: "#FFFFFF",
  buttonDisabledBackground: "#D7E5F8",
  buttonDisabledText: "#1D4F91",

  // Feedback
  errorBackground: "#FFF1F2",
  errorText: "#9F1239",
  successBackground: "#ECFDF5",
  successText: "#065F46",
} as const;

export type LoginColor = keyof typeof loginColors;

/**
 * Event colours used by the decorative scene. They are copies of
 * EVENT_TYPE_COLORS in features/events/presentation.ts (kept in sync by
 * loginTheme.test.ts) so the sign-in page matches the console map without
 * pulling the events module into the login bundle.
 */
export const loginEventColors = {
  EMERGENCY_ROAD_CLOSURE: "#dc2626",
  ROAD_CONSTRUCTION: "#d97706",
  TRAFFIC_DIVERSION: "#2563eb",
  MARATHON: "#16a34a",
} as const;

/** Realistic scene colours (asphalt, concrete, glass, greenery, water, vehicles, route lines). */
export const loginSceneColors = {
  asphalt: "#6B7583",
  minorStreet: "#A7B0BB",
  kerb: "#E4E9EF",
  concrete: "#E2E7ED",
  barrier: "#D2D9E1",
  park: "#CBE6CD",
  water: "#9FCDEC",
  windowGlass: "#BFD6EC",
  towerGlass: "#9DC1E3",
  treeTrunk: "#8B6B4A",
  treeCrowns: ["#6FAE69", "#5E9F5B", "#86BE7F"],
  cars: ["#F4F6F8", "#F4F6F8", "#F4F6F8", "#C9CED4", "#C9CED4", "#3A4049", "#1F3A5F", "#B91C1C", "#2563EB"],
  trailBlue: "#3B82F6",
  trailCyan: "#7DD3FC",
  route: "#1D74E8",
} as const;

/** CSS custom properties consumed by the login-* rules in globals.css. */
export const loginCssVariables: Record<string, string> = {
  "--login-page": loginColors.pageBackground,
  "--login-white": loginColors.pageWhite,
  "--login-headline": loginColors.headlineText,
  "--login-accent": loginColors.accentText,
  "--login-body": loginColors.bodyText,
  "--login-eyebrow": loginColors.eyebrowText,
  "--login-feature-bg": loginColors.featureIconBackground,
  "--login-header-title": loginColors.headerTitleText,
  "--login-header-subtitle": loginColors.headerSubtitleText,
  "--login-header-pill-bg": loginColors.headerPillBackground,
  "--login-header-pill-border": loginColors.headerPillBorder,
  "--login-header-pill-text": loginColors.headerPillText,
  "--login-divider": loginColors.divider,
  "--login-card": loginColors.cardBackground,
  "--login-card-border": loginColors.cardBorder,
  "--login-input-bg": loginColors.inputBackground,
  "--login-input-border": loginColors.inputBorder,
  "--login-label": loginColors.labelText,
  "--login-placeholder": loginColors.placeholderText,
  "--login-helper": loginColors.helperText,
  "--login-focus": loginColors.focusRing,
  "--login-link": loginColors.linkText,
  "--login-note-bg": loginColors.noteBackground,
  "--login-note-text": loginColors.noteText,
  "--login-button": loginColors.buttonBackground,
  "--login-button-end": loginColors.buttonBackgroundEnd,
  "--login-button-hover": loginColors.buttonHoverBackground,
  "--login-button-hover-end": loginColors.buttonHoverBackgroundEnd,
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
