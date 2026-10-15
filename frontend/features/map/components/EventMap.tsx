"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
  type GeoJSONSource,
  type MapMouseEvent,
  type PointLike,
  type SymbolLayerSpecification,
} from "maplibre-gl";

type SymbolLayout = NonNullable<SymbolLayerSpecification["layout"]>;
import "maplibre-gl/dist/maplibre-gl.css";
import { HYDERABAD_VIEW, mapConfig, satelliteConfig, type Basemap } from "@/lib/config";
import { isLocated, type Position, type RoadEvent } from "@/features/events/model";
import type { CityBubbleCollection } from "@/features/cities/overview";
import {
  CLUSTER_MAX_ZOOM,
  distinctEvents,
  markersAtZoom,
  toEventMapData,
  type StackedEvent,
} from "../geojson";
import { getBoundingBox } from "../geometry";

interface EventMapProps {
  /** Events to draw. Events that have no geometry yet are simply not drawn. */
  events: RoadEvent[];
  selectedEventId: string | null;
  onSelectEvent: (eventId: string | null) => void;
  basemap?: Basemap;
  initialView?: { center: [number, number]; zoom: number };
  /** The selected city's view; the map moves there when the city changes. */
  cityView?: { center: [number, number]; zoom: number };
  /**
   * While true, a click chooses a spot (reported through `onPickPoint`)
   * instead of selecting an event: a reviewer is correcting a location.
   */
  picking?: boolean;
  /** The spot chosen so far, shown as a pin. */
  pickedPoint?: Position | null;
  onPickPoint?: (point: Position) => void;
  /**
   * The overview of all cities: one bubble per city with its count, drawn
   * instead of events; clicking one opens that city.
   */
  cityBubbles?: CityBubbleCollection | null;
  onSelectCity?: (cityId: string) => void;
}

type MapStatus = "loading" | "ready" | "error";

const GEOMETRY_SOURCE = "rei-event-geometries";
const ANCHOR_SOURCE = "rei-event-anchors";
const PLACE_SOURCE = "rei-event-places";
// Lines from markers spread around a shared spot back to the spot.
const LEADER_SOURCE = "rei-event-leaders";
// The overview's bubbles, one per city.
const CITY_SOURCE = "rei-city-bubbles";
// Nearby markers drawn as one numbered circle while zoomed out (in pixels).
const CLUSTER_RADIUS = 46;

const SATELLITE_SOURCE = "rei-satellite";
const SATELLITE_LAYER = "rei-satellite";

const LAYERS = {
  fill: "rei-event-fill",
  halo: "rei-event-line-halo",
  casing: "rei-event-line-casing",
  line: "rei-event-line",
  lineDashed: "rei-event-line-dashed",
  leaders: "rei-event-leaders",
  anchorHalo: "rei-event-anchor-halo",
  anchor: "rei-event-anchor",
  clusters: "rei-event-clusters",
  clusterCount: "rei-event-cluster-count",
  cityBubble: "rei-city-bubble",
  cityCount: "rei-city-count",
  cityName: "rei-city-name",
  locationPoints: "rei-event-location-points",
  places: "rei-event-places",
  placeLabels: "rei-event-place-labels",
} as const;

/** Layers a click or hover can hit, and how forgiving the hit test is. */
const INTERACTIVE_LAYERS = [LAYERS.anchor, LAYERS.line, LAYERS.lineDashed, LAYERS.fill];
const HIT_TOLERANCE_PX = 6;

const EMPTY_COLLECTION = { type: "FeatureCollection" as const, features: [] };

/**
 * Adds satellite imagery as a hidden layer underneath the basemap's labels,
 * so switching to satellite view keeps place and road names readable.
 */
function addSatelliteLayer(map: MapLibreMap) {
  map.addSource(SATELLITE_SOURCE, {
    type: "raster",
    tiles: [satelliteConfig.tilesUrl],
    tileSize: 256,
    maxzoom: satelliteConfig.maxZoom,
    attribution: satelliteConfig.attribution,
  });
  const firstLabelLayer = map.getStyle().layers.find((layer) => layer.type === "symbol");
  map.addLayer(
    {
      id: SATELLITE_LAYER,
      type: "raster",
      source: SATELLITE_SOURCE,
      layout: { visibility: "none" },
    },
    firstLabelLayer?.id,
  );
}

/** A basemap text label layer and its original paint, so it can be restored. */
type SymbolPaint = NonNullable<SymbolLayerSpecification["paint"]>;

interface LabelLayerPaint {
  id: string;
  color: SymbolPaint["text-color"];
  haloColor: SymbolPaint["text-halo-color"];
  haloWidth: SymbolPaint["text-halo-width"];
}

/**
 * The basemap's plain text labels (place and road names). Labels drawn on an
 * icon, such as highway shields, are left alone.
 */
function getTextLabelLayers(map: MapLibreMap): LabelLayerPaint[] {
  return map
    .getStyle()
    .layers.filter(
      (layer) => layer.type === "symbol" && layer.layout?.["text-field"] && !layer.layout["icon-image"],
    )
    .map(({ id }) => ({
      id,
      color: map.getPaintProperty(id, "text-color"),
      haloColor: map.getPaintProperty(id, "text-halo-color"),
      haloWidth: map.getPaintProperty(id, "text-halo-width"),
    }));
}

/** Shows or hides imagery, switching labels to white-on-dark over imagery. */
function applyBasemap(map: MapLibreMap, labelLayers: LabelLayerPaint[], basemap: Basemap) {
  const satellite = basemap === "satellite";
  map.setLayoutProperty(SATELLITE_LAYER, "visibility", satellite ? "visible" : "none");
  for (const label of labelLayers) {
    map.setPaintProperty(label.id, "text-color", satellite ? "#ffffff" : label.color);
    map.setPaintProperty(label.id, "text-halo-color", satellite ? "rgba(0, 0, 0, 0.8)" : label.haloColor);
    map.setPaintProperty(label.id, "text-halo-width", satellite ? 1.4 : label.haloWidth);
  }
}

/** The basemap's own label font, so map text needs no other glyphs. */
function labelFont(map: MapLibreMap): SymbolLayout["text-font"] | undefined {
  const layer = map
    .getStyle()
    .layers.find((candidate) => candidate.type === "symbol" && candidate.layout?.["text-font"]);
  return layer?.type === "symbol" ? layer.layout?.["text-font"] : undefined;
}

function addEventLayers(map: MapLibreMap) {
  map.addSource(GEOMETRY_SOURCE, { type: "geojson", data: EMPTY_COLLECTION });
  map.addSource(ANCHOR_SOURCE, {
    type: "geojson",
    data: EMPTY_COLLECTION,
    cluster: true,
    clusterMaxZoom: CLUSTER_MAX_ZOOM,
    clusterRadius: CLUSTER_RADIUS,
  });

  map.addLayer({
    id: LAYERS.fill,
    type: "fill",
    source: GEOMETRY_SOURCE,
    filter: ["in", ["geometry-type"], ["literal", ["Polygon", "MultiPolygon"]]],
    paint: {
      "fill-color": ["get", "color"],
      "fill-opacity": ["case", ["get", "selected"], 0.3, 0.16],
    },
  });
  map.addLayer({
    id: LAYERS.halo,
    type: "line",
    source: GEOMETRY_SOURCE,
    filter: ["all", ["!=", ["geometry-type"], "Point"], ["get", "selected"]],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["get", "color"], "line-width": 18, "line-opacity": 0.22 },
  });
  map.addLayer({
    id: LAYERS.casing,
    type: "line",
    source: GEOMETRY_SOURCE,
    filter: ["in", ["geometry-type"], ["literal", ["LineString", "MultiLineString"]]],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#ffffff", "line-width": ["case", ["get", "selected"], 9, 7] },
  });
  map.addLayer({
    id: LAYERS.line,
    type: "line",
    source: GEOMETRY_SOURCE,
    filter: ["all", ["!=", ["geometry-type"], "Point"], ["!", ["get", "dashed"]]],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["case", ["get", "selected"], 6, 4],
      "line-opacity": ["get", "opacity"],
    },
  });
  map.addLayer({
    id: LAYERS.lineDashed,
    type: "line",
    source: GEOMETRY_SOURCE,
    filter: ["all", ["!=", ["geometry-type"], "Point"], ["get", "dashed"]],
    layout: { "line-join": "round" },
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["case", ["get", "selected"], 6, 4],
      "line-opacity": ["get", "opacity"],
      "line-dasharray": [1.6, 1.1],
    },
  });
  // The selected event's places by role: the event's colour where the road is
  // closed or affected, green where traffic is sent instead. Drawn under the
  // event's own marker.
  map.addSource(PLACE_SOURCE, { type: "geojson", data: EMPTY_COLLECTION });
  map.addLayer({
    id: LAYERS.places,
    type: "circle",
    source: PLACE_SOURCE,
    paint: {
      "circle-color": ["get", "color"],
      "circle-radius": ["case", ["get", "route"], 4.5, 5.5],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });
  map.addLayer({
    id: LAYERS.placeLabels,
    type: "symbol",
    source: PLACE_SOURCE,
    layout: {
      "text-field": ["get", "label"],
      "text-size": 11,
      "text-offset": [0, 1.1],
      "text-anchor": "top",
      "text-max-width": 14,
      "text-optional": true,
    },
    paint: {
      "text-color": ["get", "color"],
      "text-halo-color": "#ffffff",
      "text-halo-width": 1.6,
    },
  });
  // Several events at one spot each get their own marker around it; a thin
  // line points from each back to the spot they share.
  map.addSource(LEADER_SOURCE, { type: "geojson", data: EMPTY_COLLECTION });
  map.addLayer({
    id: LAYERS.leaders,
    type: "line",
    source: LEADER_SOURCE,
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["case", ["get", "selected"], 2, 1.2],
      "line-opacity": 0.75,
    },
  });
  map.addLayer({
    id: LAYERS.anchorHalo,
    type: "circle",
    source: ANCHOR_SOURCE,
    filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "selected"], true]],
    paint: { "circle-color": ["get", "color"], "circle-radius": 17, "circle-opacity": 0.22 },
  });
  map.addLayer({
    id: LAYERS.anchor,
    type: "circle",
    source: ANCHOR_SOURCE,
    filter: ["!", ["has", "point_count"]],
    // How the location was obtained shows in the marker: source geometry a
    // solid dot with a white ring; GIS-resolved a solid dot with a teal ring;
    // corrected by a reviewer a solid dot with a black ring; approximate (a
    // named place's position, not the event's) a hollow ring, never read as exact.
    // Markers sharing a spot are spread around it; the selected one is on top.
    layout: { "circle-sort-key": ["case", ["get", "selected"], 1, 0] },
    paint: {
      "circle-color": ["case", ["get", "approximate"], "#ffffff", ["get", "color"]],
      "circle-radius": ["case", ["get", "selected"], 8.5, 6.5],
      "circle-stroke-color": [
        "match",
        ["get", "locationClass"],
        "APPROXIMATE", ["get", "color"],
        "GIS_RESOLVED", "#0f766e",
        "HUMAN_CORRECTED", "#0f172a",
        "QC_APPROVED", "#0f172a",
        "#ffffff",
      ],
      "circle-stroke-width": [
        "match",
        ["get", "locationClass"],
        "APPROXIMATE", 3,
        "GIS_RESOLVED", 3,
        "HUMAN_CORRECTED", 3,
        "QC_APPROVED", 3,
        2.5,
      ],
    },
  });
}

/** Numbered circles for nearby markers while zoomed out, and the overview's city bubbles. */
function addGroupLayers(map: MapLibreMap) {
  const font = labelFont(map);
  const text = (size: number): SymbolLayout => ({
    "text-size": size,
    ...(font ? { "text-font": font } : {}),
  });
  map.addLayer({
    id: LAYERS.clusters,
    type: "circle",
    source: ANCHOR_SOURCE,
    filter: ["has", "point_count"],
    paint: {
      "circle-color": "#00558c",
      "circle-opacity": 0.92,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
      "circle-radius": ["step", ["get", "point_count"], 13, 10, 16, 50, 20, 250, 25, 1000, 30],
    },
  });
  map.addLayer({
    id: LAYERS.clusterCount,
    type: "symbol",
    source: ANCHOR_SOURCE,
    filter: ["has", "point_count"],
    layout: {
      ...text(11),
      "text-field": ["get", "point_count_abbreviated"],
      "text-allow-overlap": true,
      "text-ignore-placement": true,
    },
    paint: { "text-color": "#ffffff" },
  });
  map.addSource(CITY_SOURCE, { type: "geojson", data: EMPTY_COLLECTION });
  map.addLayer({
    id: LAYERS.cityBubble,
    type: "circle",
    source: CITY_SOURCE,
    // Where bubbles overlap (Toronto by New York), the smaller is drawn on top.
    layout: { "circle-sort-key": ["-", 0, ["get", "count"]] },
    paint: {
      "circle-color": ["case", [">", ["get", "count"], 0], "#00558c", "#94a3b8"],
      "circle-opacity": 0.92,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2.5,
      "circle-radius": ["interpolate", ["linear"], ["sqrt", ["get", "count"]], 0, 14, 80, 32],
    },
  });
  map.addLayer({
    id: LAYERS.cityCount,
    type: "symbol",
    source: CITY_SOURCE,
    layout: {
      ...text(12),
      "text-field": ["get", "countLabel"],
      "symbol-sort-key": ["get", "count"],
      "text-allow-overlap": true,
      "text-ignore-placement": true,
    },
    paint: { "text-color": "#ffffff" },
  });
  map.addLayer({
    id: LAYERS.cityName,
    type: "symbol",
    source: CITY_SOURCE,
    layout: {
      ...text(12),
      "text-field": ["get", "name"],
      "text-anchor": "top",
      "text-offset": [0, 2.3],
      "text-optional": true,
    },
    paint: { "text-color": "#0f172a", "text-halo-color": "#ffffff", "text-halo-width": 1.8 },
  });
}

function addLocationPointLayer(map: MapLibreMap) {
  // Places resolved on the road network (junctions) and point candidates under review.
  map.addLayer({
    id: LAYERS.locationPoints,
    type: "circle",
    source: GEOMETRY_SOURCE,
    filter: ["==", ["geometry-type"], "Point"],
    paint: {
      "circle-color": ["case", ["get", "candidate"], "#ffffff", ["get", "color"]],
      "circle-radius": 5,
      "circle-stroke-color": ["case", ["get", "candidate"], "#64748b", "#0f766e"],
      "circle-stroke-width": 2.5,
    },
  });
}

function hitBox(e: MapMouseEvent): [PointLike, PointLike] {
  return [
    [e.point.x - HIT_TOLERANCE_PX, e.point.y - HIT_TOLERANCE_PX],
    [e.point.x + HIT_TOLERANCE_PX, e.point.y + HIT_TOLERANCE_PX],
  ];
}

function pickEvent(map: MapLibreMap, e: MapMouseEvent): { id: string; title: string } | null {
  // Results are ordered top-most first, so markers win over lines over fills.
  const [feature] = map.queryRenderedFeatures(hitBox(e), { layers: INTERACTIVE_LAYERS });
  if (!feature) return null;
  return { id: String(feature.properties.eventId), title: String(feature.properties.title) };
}

/** Every event whose marker is under the pointer: several when markers share a spot. */
function pickMarkers(map: MapLibreMap, e: MapMouseEvent): StackedEvent[] {
  return distinctEvents(map.queryRenderedFeatures(hitBox(e), { layers: [LAYERS.anchor] }));
}

/** The events at one spot, each with its type, period and source, to choose which to open. */
function stackChooser(events: StackedEvent[], onChoose: (eventId: string) => void): HTMLElement {
  const root = document.createElement("div");
  root.className = "max-w-72 text-xs";
  const heading = document.createElement("p");
  heading.className = "mb-1.5 font-semibold text-slate-700";
  heading.textContent = `${events.length} events at this spot`;
  const note = document.createElement("p");
  note.className = "mb-2 text-[11px] leading-snug text-slate-500";
  note.textContent = "Separate events at the same spot. Choose one to open.";
  const list = document.createElement("ul");
  list.className = "max-h-56 space-y-1 overflow-y-auto";
  for (const event of events) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "w-full cursor-pointer rounded-md px-2 py-1.5 text-left leading-snug text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-slate-50";
    const title = document.createElement("span");
    title.className = "block";
    title.textContent = event.title;
    button.append(title);
    if (event.detail) {
      const detail = document.createElement("span");
      detail.className = "mt-0.5 block text-[11px] text-slate-500";
      detail.textContent = event.detail;
      button.append(detail);
    }
    button.addEventListener("click", () => onChoose(event.id));
    item.append(button);
    list.append(item);
  }
  root.append(heading, note, list);
  return root;
}

function fitToEvents(
  map: MapLibreMap,
  events: RoadEvent[],
  { detailsPanelOpen }: { detailsPanelOpen: boolean },
) {
  const located = events.filter(isLocated);
  // Nothing to frame: e.g. the selected event is still awaiting GIS resolution.
  if (located.length === 0) return;

  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const event of located) {
    const box = getBoundingBox(event.geometry);
    west = Math.min(west, box[0]);
    south = Math.min(south, box[1]);
    east = Math.max(east, box[2]);
    north = Math.max(north, box[3]);
  }
  const { clientWidth, clientHeight } = map.getContainer();
  // On wide layouts the legend covers the top-left of the map and the details
  // panel, when open, its right edge.
  const isWide = clientWidth >= 720;
  const leftPadding = isWide ? 210 : 48;
  const rightPadding = isWide && detailsPanelOpen ? 440 : 64;
  const verticalPadding = Math.min(90, clientHeight / 5);
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    {
      padding: { top: verticalPadding, bottom: verticalPadding, left: leftPadding, right: rightPadding },
      maxZoom: 15,
      duration: 700,
    },
  );
}

/**
 * Interactive MapLibre map of road events. Knows only the `RoadEvent`
 * model — not where events come from or how they are filtered.
 */
export default function EventMap({
  events,
  selectedEventId,
  onSelectEvent,
  basemap = "map",
  initialView = HYDERABAD_VIEW,
  cityView,
  picking = false,
  pickedPoint = null,
  onPickPoint,
  cityBubbles = null,
  onSelectCity,
}: EventMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<MapStatus>("loading");
  // The map whose style has finished loading. Layers can only be touched on
  // this one: during a development reload the map is rebuilt while `status`
  // still says "ready" from the map before it.
  const [loadedMap, setLoadedMap] = useState<MapLibreMap | null>(null);
  // The zoom markers sharing a spot are spread for (a ring of fixed pixel size).
  const [spreadZoom, setSpreadZoom] = useState(initialView.zoom);

  const onSelectEventRef = useRef(onSelectEvent);
  const pickingRef = useRef(picking);
  const onPickPointRef = useRef(onPickPoint);
  const onSelectCityRef = useRef(onSelectCity);
  useEffect(() => {
    onSelectEventRef.current = onSelectEvent;
    pickingRef.current = picking;
    onPickPointRef.current = onPickPoint;
    onSelectCityRef.current = onSelectCity;
  });

  // Id of an event the user just picked on the map itself; the camera should
  // not jump away from where they clicked.
  const pickedOnMapRef = useRef<string | null>(null);
  const focusedIdRef = useRef<string | null>(null);

  const initialViewRef = useRef(initialView);
  const labelLayersRef = useRef<LabelLayerPaint[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let map: MapLibreMap;
    try {
      setWorkerUrl(mapConfig.workerUrl);
      map = new MapLibreMap({
        container,
        style: mapConfig.styleUrl,
        center: initialViewRef.current.center,
        zoom: initialViewRef.current.zoom,
        attributionControl: { compact: true },
      });
    } catch (error) {
      // Typically: WebGL is unavailable in this browser.
      console.error("Failed to initialise map", error);
      queueMicrotask(() => setStatus("error"));
      return;
    }
    mapRef.current = map;
    let loaded = false;

    map.addControl(new NavigationControl({ visualizePitch: false }), "bottom-right");
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

    const hoverPopup = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 12,
      className: "rei-hover-popup",
    });
    let hoveredId: string | null = null;
    // Lists the events at a spot several markers share.
    const chooserPopup = new Popup({ closeButton: true, closeOnClick: false, offset: 12, maxWidth: "300px" });

    map.on("load", () => {
      labelLayersRef.current = getTextLabelLayers(map);
      addSatelliteLayer(map);
      addEventLayers(map);
      addLocationPointLayer(map);
      addGroupLayers(map);
      // Keep the event's selectable marker above GIS point features. A GIS
      // candidate or resolved junction can share its coordinates and would
      // otherwise paint over the selected event marker.
      map.moveLayer(LAYERS.leaders);
      map.moveLayer(LAYERS.anchorHalo);
      map.moveLayer(LAYERS.anchor);
      for (const id of [LAYERS.clusters, LAYERS.clusterCount, LAYERS.cityBubble, LAYERS.cityCount, LAYERS.cityName]) {
        map.moveLayer(id);
      }
      loaded = true;
      setLoadedMap(map);
      setStatus("ready");
    });

    map.on("zoomend", () => {
      setSpreadZoom(Math.round(map.getZoom() * 4) / 4);
    });

    map.on("error", (e) => {
      console.error("Map error", e.error);
      // Before load, an error means the basemap style could not be fetched.
      if (!loaded) setStatus("error");
    });

    map.on("click", (e) => {
      if (!loaded) return;
      if (pickingRef.current) {
        onPickPointRef.current?.([e.lngLat.lng, e.lngLat.lat]);
        return;
      }
      chooserPopup.remove();
      // The overview: a city's bubble opens that city.
      const [bubble] = map.queryRenderedFeatures(hitBox(e), { layers: [LAYERS.cityBubble] });
      if (bubble) {
        hoverPopup.remove();
        onSelectCityRef.current?.(String(bubble.properties.cityId));
        return;
      }
      // A numbered circle: zoom in until its markers come apart.
      const [cluster] = map.queryRenderedFeatures(hitBox(e), { layers: [LAYERS.clusters] });
      if (cluster && cluster.geometry.type === "Point") {
        const center = cluster.geometry.coordinates as [number, number];
        map
          .getSource<GeoJSONSource>(ANCHOR_SOURCE)
          ?.getClusterExpansionZoom(Number(cluster.properties.cluster_id))
          .then((zoom) => map.easeTo({ center, zoom: Math.min(zoom, CLUSTER_MAX_ZOOM + 1.5) }))
          .catch(() => map.easeTo({ center, zoom: map.getZoom() + 2 }));
        return;
      }
      const stacked = pickMarkers(map, e);
      if (stacked.length > 1) {
        // Several events at this spot: the reviewer chooses which, rather
        // than getting whichever is drawn on top.
        hoverPopup.remove();
        chooserPopup
          .setLngLat(e.lngLat)
          .setDOMContent(
            stackChooser(stacked, (eventId) => {
              chooserPopup.remove();
              pickedOnMapRef.current = eventId;
              onSelectEventRef.current(eventId);
            }),
          )
          .addTo(map);
        return;
      }
      const picked = pickEvent(map, e);
      pickedOnMapRef.current = picked?.id ?? null;
      onSelectEventRef.current(picked?.id ?? null);
    });

    map.on("mousemove", (e) => {
      if (!loaded) return;
      if (pickingRef.current) {
        map.getCanvas().style.cursor = "crosshair";
        hoveredId = null;
        hoverPopup.remove();
        return;
      }
      const [group] = map.queryRenderedFeatures(hitBox(e), {
        layers: [LAYERS.cityBubble, LAYERS.clusters],
      });
      if (group) {
        map.getCanvas().style.cursor = "pointer";
        const key = `group:${group.properties.cityId ?? group.properties.cluster_id}`;
        hoverPopup.setLngLat(e.lngLat);
        if (key !== hoveredId) {
          hoveredId = key;
          hoverPopup
            .setText(
              group.layer.id === LAYERS.cityBubble
                ? `${group.properties.name}: ${group.properties.countLabel} events. Click to open`
                : `${group.properties.point_count_abbreviated} events here. Click to zoom in`,
            )
            .addTo(map);
        }
        return;
      }
      const picked = pickEvent(map, e);
      map.getCanvas().style.cursor = picked ? "pointer" : "";
      if (!picked) {
        hoveredId = null;
        hoverPopup.remove();
        return;
      }
      hoverPopup.setLngLat(e.lngLat);
      const stacked = pickMarkers(map, e);
      const hoverKey = stacked.length > 1 ? stacked.map((s) => s.id).join("|") : picked.id;
      if (hoverKey !== hoveredId) {
        hoveredId = hoverKey;
        hoverPopup
          .setText(
            stacked.length > 1 ? `${stacked.length} events at this spot: click to choose` : picked.title,
          )
          .addTo(map);
      }
    });

    map.on("mouseout", () => {
      hoveredId = null;
      hoverPopup.remove();
    });

    return () => {
      mapRef.current = null;
      map.remove();
    };
  }, []);

  const mapData = useMemo(
    () => toEventMapData(events, selectedEventId),
    [events, selectedEventId],
  );
  const markers = useMemo(() => markersAtZoom(mapData.anchors, spreadZoom), [mapData, spreadZoom]);

  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    applyBasemap(map, labelLayersRef.current, basemap);
  }, [loadedMap, basemap]);

  // Show the spot a reviewer has chosen, and a crosshair while they choose.
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    map.getCanvas().style.cursor = picking ? "crosshair" : "";
    if (!picking || !pickedPoint) return;
    const pin = new Marker({ color: "#00558c" }).setLngLat(pickedPoint).addTo(map);
    return () => {
      pin.remove();
    };
  }, [loadedMap, picking, pickedPoint]);

  // Push event data into the map whenever events or the selection change.
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    map.getSource<GeoJSONSource>(GEOMETRY_SOURCE)?.setData(mapData.geometries);
    map.getSource<GeoJSONSource>(PLACE_SOURCE)?.setData(mapData.places);
  }, [loadedMap, mapData]);

  // Markers, with those sharing a spot spread around it at the current zoom.
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    map.getSource<GeoJSONSource>(ANCHOR_SOURCE)?.setData(markers.anchors);
    map.getSource<GeoJSONSource>(LEADER_SOURCE)?.setData(markers.leaders);
  }, [loadedMap, markers]);

  // The overview's city bubbles (none once a city is open).
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    map.getSource<GeoJSONSource>(CITY_SOURCE)?.setData(cityBubbles ?? EMPTY_COLLECTION);
  }, [loadedMap, cityBubbles]);

  // Frame every city's bubble when the overview opens (not again when only counts change).
  const bubbleKey = cityBubbles ? cityBubbles.features.map((f) => f.properties.cityId).join("|") : "";
  const framedBubblesRef = useRef("");
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    if (!bubbleKey || !cityBubbles) {
      framedBubblesRef.current = "";
      return;
    }
    if (framedBubblesRef.current === bubbleKey) return;
    framedBubblesRef.current = bubbleKey;
    const positions = cityBubbles.features.map((f) => f.geometry.coordinates);
    const lngs = positions.map(([lng]) => lng);
    const lats = positions.map(([, lat]) => lat);
    const { clientWidth } = map.getContainer();
    const isWide = clientWidth >= 720;
    map.fitBounds(
      [
        [Math.min(...lngs), Math.min(...lats)],
        [Math.max(...lngs), Math.max(...lats)],
      ],
      { padding: { top: 70, bottom: 70, left: isWide ? 260 : 48, right: 70 }, maxZoom: 4, duration: 700 },
    );
  }, [loadedMap, bubbleKey, cityBubbles]);

  // Bring a newly selected event into view.
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    if (selectedEventId === focusedIdRef.current) return;
    focusedIdRef.current = selectedEventId;

    const pickedOnMap = pickedOnMapRef.current === selectedEventId;
    pickedOnMapRef.current = null;
    if (!selectedEventId || pickedOnMap) return;

    const event = events.find((candidate) => candidate.id === selectedEventId);
    if (!event) return;

    fitToEvents(map, [event], { detailsPanelOpen: true });
  }, [loadedMap, selectedEventId, events]);

  // Move to the selected city. Runs before the framing below, which then
  // fits the city's located events if it has any.
  const cityKey = cityView ? `${cityView.center.join(",")}|${cityView.zoom}` : "";
  const cityKeyRef = useRef(cityKey);
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current || !cityView) return;
    if (cityKeyRef.current === cityKey) return;
    cityKeyRef.current = cityKey;
    map.jumpTo({ center: cityView.center, zoom: cityView.zoom });
  }, [loadedMap, cityKey, cityView]);

  // Frame the located events when they arrive and whenever filtering changes them.
  const visibleIdsKey = events.map((event) => event.id).join("|");
  const framedIdsKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const map = loadedMap;
    if (!map || map !== mapRef.current) return;
    const previousKey = framedIdsKeyRef.current;
    framedIdsKeyRef.current = visibleIdsKey;
    // The selection effect above owns the camera while an event is selected.
    // With no located event, the initial Hyderabad view stays.
    if (previousKey === visibleIdsKey || selectedEventId) return;
    fitToEvents(map, events, { detailsPanelOpen: false });
  }, [loadedMap, visibleIdsKey, events, selectedEventId]);

  return (
    <div className="relative h-full w-full bg-slate-100">
      <div ref={containerRef} className="h-full w-full" aria-label="Map of road events" />

      {status === "loading" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-100/70">
          <div className="flex items-center gap-2.5 rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm ring-1 ring-slate-200">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
            Loading map…
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-100 p-6">
          <div className="max-w-sm rounded-xl bg-white p-5 text-center shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold text-slate-900">The map could not be loaded</p>
            <p className="mt-1.5 text-sm text-slate-500">
              Check your network connection and the basemap style URL, then reload the page. The
              event list is still available.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
