"use client";

import { useSyncExternalStore } from "react";
import { APPEARANCE_STORAGE_KEY } from "./appearanceScript";

/**
 * Light or dark appearance (decision 0051), kept in this browser like the
 * colour theme (themes.ts). Light is the default. The root layout's inline
 * script (appearanceScript.ts) applies a saved "dark" before the first paint,
 * so a page never flashes light first; the console's CSS reads
 * <html data-theme="dark">.
 */

export type Appearance = "light" | "dark";

const listeners = new Set<() => void>();

function current(): Appearance {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function apply(appearance: Appearance): void {
  if (appearance === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
}

export function saveAppearance(appearance: Appearance): void {
  apply(appearance);
  try {
    window.localStorage.setItem(APPEARANCE_STORAGE_KEY, appearance);
  } catch {
    // Private windows may refuse storage: the choice then lasts this page.
  }
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  // Another tab changed it: follow.
  const onStorage = (event: StorageEvent) => {
    if (event.key !== APPEARANCE_STORAGE_KEY) return;
    apply(event.newValue === "dark" ? "dark" : "light");
    listener();
  };
  listeners.add(listener);
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function useAppearance(): Appearance {
  return useSyncExternalStore(subscribe, current, () => "light");
}
