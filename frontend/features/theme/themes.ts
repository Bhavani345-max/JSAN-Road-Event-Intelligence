"use client";

import { useSyncExternalStore } from "react";

/**
 * The console's colour themes (decision 0043). Each recolours the brand-*
 * colours (sidebar, header, buttons, the map's bubbles) with JSAN Blue's
 * lightness at every step and only another hue, so white text keeps the same
 * contrast (at least 7:1 on the sidebar's 600). The choice is kept in this
 * browser only: two people sharing an account keep their own.
 */

export const BRAND_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const;
export type BrandStep = (typeof BRAND_STEPS)[number];

export interface Theme {
  id: string;
  name: string;
  palette: Record<BrandStep, string>;
}

export const DEFAULT_THEME_ID = "jsan";

export const THEMES: readonly Theme[] = [
  {
    id: DEFAULT_THEME_ID,
    name: "JSAN Blue",
    // The same values as app/globals.css (checked by themes.test.ts).
    palette: {
      50: "#eef6fb", 100: "#d9eaf5", 200: "#b3d4ea", 300: "#7fb5d8", 400: "#3f8fc0",
      500: "#0f6fa8", 600: "#00558c", 700: "#004674", 800: "#00395f", 900: "#002c4a",
    },
  },
  {
    id: "teal",
    name: "Teal",
    palette: {
      50: "#edf7f7", 100: "#d6ecec", 200: "#acd9d8", 300: "#70bdbc", 400: "#059a9a",
      500: "#027879", 600: "#025e5e", 700: "#014e4e", 800: "#013f3f", 900: "#003131",
    },
  },
  {
    id: "green",
    name: "Green",
    palette: {
      50: "#f0f7f1", 100: "#dcece0", 200: "#b9d8c0", 300: "#89bc96", 400: "#509966",
      500: "#227c45", 600: "#026330", 700: "#035127", 800: "#03421f", 900: "#033317",
    },
  },
  {
    id: "indigo",
    name: "Indigo",
    palette: {
      50: "#f2f4fc", 100: "#e2e6f7", 200: "#c5cdee", 300: "#9faade", 400: "#7481c7",
      500: "#5661ad", 600: "#414a8f", 700: "#353c77", 800: "#2a3162", 900: "#20254c",
    },
  },
  {
    id: "purple",
    name: "Purple",
    palette: {
      50: "#f7f3fa", 100: "#ede3f2", 200: "#dbc6e4", 300: "#c09fcf", 400: "#9f72b3",
      500: "#835198", 600: "#693b7c", 700: "#563067", 800: "#472754", 900: "#371d41",
    },
  },
  {
    id: "graphite",
    name: "Graphite",
    palette: {
      50: "#f4f5f6", 100: "#e5e7ea", 200: "#cbcfd4", 300: "#a8aeb6", 400: "#7f8792",
      500: "#616a76", 600: "#4a525d", 700: "#3d444d", 800: "#31373e", 900: "#252a30",
    },
  },
];

/** The theme with this id; JSAN Blue for none or one that no longer exists. */
export function themeById(id: string | null | undefined): Theme {
  return THEMES.find((theme) => theme.id === id) ?? THEMES[0];
}

/** The custom properties Tailwind's brand-* classes read, for an element's style. */
export function themeStyle(theme: Theme): Record<`--color-brand-${BrandStep}`, string> {
  return Object.fromEntries(
    BRAND_STEPS.map((step) => [`--color-brand-${step}`, theme.palette[step]]),
  ) as Record<`--color-brand-${BrandStep}`, string>;
}

const STORAGE_KEY = "rei-theme";
const listeners = new Set<() => void>();
// The choice made in this tab, kept even where the browser refuses storage.
let chosenId: string | null = null;

function storedThemeId(): string {
  if (chosenId !== null) return chosenId;
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? DEFAULT_THEME_ID;
  } catch {
    return DEFAULT_THEME_ID;
  }
}

/** Keeps the theme for this browser; every open console follows. */
export function saveTheme(id: string): void {
  chosenId = themeById(id).id;
  try {
    window.localStorage.setItem(STORAGE_KEY, chosenId);
  } catch {
    // Private windows may refuse storage: the theme then lasts this visit.
  }
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  // Another tab of the console changed it.
  const onStorage = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY) return;
    chosenId = null;
    listener();
  };
  listeners.add(listener);
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

/** The theme chosen in this browser. */
export function useTheme(): Theme {
  return themeById(useSyncExternalStore(subscribe, storedThemeId, () => DEFAULT_THEME_ID));
}
