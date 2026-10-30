/**
 * Which of the map's own layers are drawn. These change only how the events
 * look on the map, never which events there are: the list, the counts and the
 * events themselves are the same whatever is chosen here.
 */
export interface MapLayers {
  /** Event markers, lines and areas. */
  markers: boolean;
  /** Nearby markers drawn as one numbered circle while zoomed out. */
  clusters: boolean;
  /** Where events are dense, as a heat layer under the markers (never clickable). */
  heatmap: boolean;
}

export const DEFAULT_MAP_LAYERS: MapLayers = { markers: true, clusters: true, heatmap: false };
