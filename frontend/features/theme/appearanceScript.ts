/** Where the light/dark choice is kept in this browser (features/theme/appearance.ts). */
export const APPEARANCE_STORAGE_KEY = "rei-appearance";

/**
 * Runs in <head> before anything paints (app/layout.tsx): a saved "dark"
 * appearance is applied at once, so no page flashes light first. Plain text
 * for the server layout, not a client module.
 */
export const APPEARANCE_SCRIPT = `try{if(localStorage.getItem("${APPEARANCE_STORAGE_KEY}")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`;
