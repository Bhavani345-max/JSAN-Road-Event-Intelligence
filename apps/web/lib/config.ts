/** Browser-side configuration. Override via .env.local (see .env.example). */

export const mapConfig = {
  /** MapLibre style JSON URL for the basemap. */
  styleUrl:
    process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/positron",
  /** Served from /public; copied from node_modules by scripts/copy-maplibre-worker.mjs. */
  workerUrl: "/maplibre/maplibre-gl-worker.mjs",
};

/** Basemaps the user can switch between. */
export const BASEMAPS = ["map", "satellite"] as const;
export type Basemap = (typeof BASEMAPS)[number];

/** Raster imagery shown in satellite view. */
export const satelliteConfig = {
  /** XYZ tile URL template. */
  tilesUrl:
    process.env.NEXT_PUBLIC_SATELLITE_TILES_URL ||
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  attribution:
    process.env.NEXT_PUBLIC_SATELLITE_ATTRIBUTION ||
    "Imagery © Esri, Maxar, Earthstar Geographics",
  maxZoom: 18,
};

/** Initial map area for the PoC: Hyderabad, Telangana, India. */
export const HYDERABAD_VIEW = {
  center: [78.4675, 17.4065] as [number, number],
  zoom: 11.6,
};
