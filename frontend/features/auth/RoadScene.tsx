"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { FullScreenQuad } from "three/examples/jsm/postprocessing/Pass.js";
import { createRng, generateRoadNetwork, type ElevatedRoad, type Point, type Polyline } from "./roadNetwork";
import { loginColors } from "./loginTheme";

/**
 * Decorative night-time road network for the sign-in page: an oblique view of
 * ground avenues and streets, a flyover and a higher viaduct on pillars with
 * ramps, soft shadows from the elevated decks, restrained blue/cyan road-edge
 * lighting, a few small event markers and slow traffic lights.
 *
 * Real 3D: all geometry, lighting, the shadow map (rendered once) and the
 * depth-based depth of field. Purely procedural and purely illustrative: it
 * does not show any real place or any product data.
 */

type RoadSceneProps = {
  /** Called once the first frame has been drawn. */
  onReady?: () => void;
  /** Called when WebGL cannot be used; the page then keeps its CSS backdrop. */
  onUnavailable?: () => void;
};

const SKY = new THREE.Color("#081522");
const HAZE = new THREE.Color(loginColors.sceneHaze).multiplyScalar(1.35);
const ROAD_BLUE = new THREE.Color(loginColors.roadBlue);
const ROAD_CYAN = new THREE.Color(loginColors.roadCyan);
const EVENT_AMBER = new THREE.Color(loginColors.eventAmber);
const DECK_THICKNESS = 0.6;
const TARGET_FPS = 30;
const IDLE_STOP_MS = 15_000;

type Route = { line: Polyline; heights: number[] | null; cumulative: number[]; length: number };
type Traveller = { route: number; distance: number; speed: number };
type Pulse = { mesh: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>; phase: number; speed: number; reach: number; peak: number };

function cumulativeDistances(line: Polyline): number[] {
  const distances = [0];
  for (let index = 1; index < line.length; index += 1) {
    distances.push(distances[index - 1] + Math.hypot(line[index].x - line[index - 1].x, line[index].z - line[index - 1].z));
  }
  return distances;
}

function sideNormal(from: Point, to: Point): [number, number] {
  const length = Math.hypot(to.x - from.x, to.z - from.z) || 1;
  return [-(to.z - from.z) / length, (to.x - from.x) / length];
}

/** Flat strip following a polyline at a constant height (ground roads, detour). */
function createStripGeometry(line: Polyline, halfWidth: number, y: number): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  let travelled = 0;
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const to = line[index];
    const [nx, nz] = sideNormal(from, to);
    const length = Math.hypot(to.x - from.x, to.z - from.z);
    const base = positions.length / 3;
    positions.push(
      from.x + nx * halfWidth, y, from.z + nz * halfWidth,
      from.x - nx * halfWidth, y, from.z - nz * halfWidth,
      to.x + nx * halfWidth, y, to.z + nz * halfWidth,
      to.x - nx * halfWidth, y, to.z - nz * halfWidth,
    );
    normals.push(0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0);
    uvs.push(travelled, 0, travelled, 1, travelled + length, 0, travelled + length, 1);
    indices.push(base, base + 2, base + 1, base + 1, base + 2, base + 3);
    travelled += length;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  return geometry;
}

/** Polyline offset sideways and lifted, for road-edge lines. */
function edgePoints(line: Polyline, offset: number, heights: number[] | null, lift: number): THREE.Vector3[] {
  return line.map((point, index) => {
    const previous = line[Math.max(0, index - 1)];
    const next = line[Math.min(line.length - 1, index + 1)];
    const [nx, nz] = sideNormal(previous, next);
    const y = (heights ? heights[index] : 0) + lift;
    return new THREE.Vector3(point.x + nx * offset, y, point.z + nz * offset);
  });
}

/** Solid deck (top, underside and both sides) following an elevated road. */
function createDeckGeometry(road: ElevatedRoad): THREE.BufferGeometry {
  const positions: number[] = [];
  const half = road.width / 2;
  const quad = (a: number[], b: number[], c: number[], d: number[]) => {
    positions.push(...a, ...b, ...c, ...a, ...c, ...d);
  };
  const { line, heights } = road;
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const to = line[index];
    const [nx, nz] = sideNormal(from, to);
    const topFrom = heights[index - 1];
    const topTo = heights[index];
    const bottomFrom = topFrom - DECK_THICKNESS;
    const bottomTo = topTo - DECK_THICKNESS;
    const fl = [from.x + nx * half, topFrom, from.z + nz * half];
    const fr = [from.x - nx * half, topFrom, from.z - nz * half];
    const tl = [to.x + nx * half, topTo, to.z + nz * half];
    const tr = [to.x - nx * half, topTo, to.z - nz * half];
    const flb = [fl[0], bottomFrom, fl[2]];
    const frb = [fr[0], bottomFrom, fr[2]];
    const tlb = [tl[0], bottomTo, tl[2]];
    const trb = [tr[0], bottomTo, tr[2]];
    quad(fl, tl, tr, fr); // top
    quad(frb, trb, tlb, flb); // underside
    quad(fl, flb, tlb, tl); // left wall
    quad(fr, tr, trb, frb); // right wall
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}

/** Soft round sprite used for the traffic lights. */
function createSpriteTexture(): THREE.CanvasTexture | null {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 32;
  const context = canvas.getContext("2d");
  if (!context) return null;
  const gradient = context.createRadialGradient(16, 16, 0, 16, 16, 16);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.35, "rgba(255,255,255,0.55)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 32, 32);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const quadVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const blurFragmentShader = `
  uniform sampler2D tInput;
  uniform vec2 uStep;
  varying vec2 vUv;
  void main() {
    vec4 sum = texture2D(tInput, vUv) * 0.227027;
    sum += (texture2D(tInput, vUv + uStep * 1.384615) + texture2D(tInput, vUv - uStep * 1.384615)) * 0.316216;
    sum += (texture2D(tInput, vUv + uStep * 3.230769) + texture2D(tInput, vUv - uStep * 3.230769)) * 0.070270;
    gl_FragColor = sum;
  }
`;

const compositeFragmentShader = `
  #include <packing>
  uniform sampler2D tSharp;
  uniform sampler2D tBlur;
  uniform sampler2D tDepth;
  uniform float uNear;
  uniform float uFar;
  uniform float uFocusStart;
  uniform float uFocusEnd;
  uniform float uNearBlurEnd;
  varying vec2 vUv;
  void main() {
    float depth = texture2D(tDepth, vUv).x;
    float dist = -perspectiveDepthToViewZ(depth, uNear, uFar);
    float farBlur = smoothstep(uFocusStart, uFocusEnd, dist);
    float nearBlur = (1.0 - smoothstep(0.0, uNearBlurEnd, dist)) * 0.7;
    float amount = clamp(max(farBlur, nearBlur), 0.0, 1.0);
    vec3 sharp = texture2D(tSharp, vUv).rgb;
    vec3 blurred = texture2D(tBlur, vUv).rgb;
    gl_FragColor = vec4(mix(sharp, blurred, amount), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export default function RoadScene({ onReady, onUnavailable }: RoadSceneProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onReady, onUnavailable });

  useEffect(() => {
    callbacks.current = { onReady, onUnavailable };
  }, [onReady, onUnavailable]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    // three r186 needs WebGL 2. Probe first so unsupported browsers get the CSS
    // backdrop without context-creation errors in the console.
    const probe = document.createElement("canvas");
    const probeContext = probe.getContext("webgl2");
    if (!probeContext) {
      callbacks.current.onUnavailable?.();
      return;
    }
    probeContext.getExtension("WEBGL_lose_context")?.loseContext();

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "low-power", stencil: false });
    } catch {
      callbacks.current.onUnavailable?.();
      return;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
    renderer.setPixelRatio(pixelRatio);
    renderer.setClearColor(SKY, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.4;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = false; // static geometry and light: rendered once
    renderer.shadowMap.needsUpdate = true;
    const canvas = renderer.domElement;
    canvas.style.position = "absolute";
    canvas.style.inset = "0";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.opacity = "0";
    canvas.style.transition = reducedMotion ? "none" : "opacity 1200ms ease";
    host.appendChild(canvas);

    const disposables: { dispose: () => void }[] = [];
    const track = <T extends { dispose: () => void }>(item: T): T => {
      disposables.push(item);
      return item;
    };

    const scene = new THREE.Scene();
    scene.background = SKY;
    scene.fog = new THREE.Fog(HAZE, 55, 200);

    const camera = new THREE.PerspectiveCamera(44, 1, 1, 320);
    const cameraBase = new THREE.Vector3(3, 14, 31);
    const lookTarget = new THREE.Vector3(3, 0, -30);
    camera.position.copy(cameraBase);
    camera.lookAt(lookTarget);

    // Lighting: cool ambient sky light, one shadow-casting key light from the
    // upper left and a faint blue fill from the right.
    scene.add(new THREE.HemisphereLight(0x2f5a85, 0x07111d, 2.1));
    const key = new THREE.DirectionalLight(0xbdd7f0, 2.6);
    key.position.set(-46, 72, 14);
    key.target.position.set(0, 0, -24);
    key.castShadow = true;
    key.shadow.mapSize.set(1536, 1536);
    key.shadow.camera.left = -64;
    key.shadow.camera.right = 64;
    key.shadow.camera.top = 64;
    key.shadow.camera.bottom = -64;
    key.shadow.camera.near = 8;
    key.shadow.camera.far = 220;
    key.shadow.bias = -0.0005;
    key.shadow.normalBias = 0.05;
    scene.add(key, key.target);
    track(key.shadow);
    const fill = new THREE.DirectionalLight(ROAD_BLUE, 0.6);
    fill.position.set(50, 30, -20);
    scene.add(fill);

    const network = generateRoadNetwork(7, 160);

    // Sky: a far gradient quad from navy down to the horizon haze.
    const skyMaterial = track(new THREE.ShaderMaterial({
      uniforms: { uTop: { value: SKY }, uHorizon: { value: HAZE.clone().multiplyScalar(1.15) } },
      vertexShader: `
        varying float vY;
        void main() {
          vY = position.y;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uTop;
        uniform vec3 uHorizon;
        varying float vY;
        void main() {
          gl_FragColor = vec4(mix(uHorizon, uTop, smoothstep(0.0, 90.0, vY)), 1.0);
        }
      `,
      depthWrite: false,
      fog: false,
    }));
    const sky = new THREE.Mesh(track(new THREE.PlaneGeometry(1600, 500)), skyMaterial);
    sky.position.set(3, 150, -300);
    scene.add(sky);

    // Ground, blocks and ground roads --------------------------------------
    const groundMaterial = track(new THREE.MeshStandardMaterial({ color: 0x0c1a2b, roughness: 0.5, metalness: 0.18 }));
    const ground = new THREE.Mesh(track(new THREE.PlaneGeometry(240, 240)), groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const visibleBlocks = network.blocks.filter((block) => block.density > 0.12);
    const blockRng = createRng(99);
    const blockGeometry = track(new THREE.BoxGeometry(1, 1, 1));
    const blockMaterial = track(new THREE.MeshStandardMaterial({ color: 0x102238, roughness: 0.9, metalness: 0.05 }));
    const blocks = new THREE.InstancedMesh(blockGeometry, blockMaterial, visibleBlocks.length);
    const matrix = new THREE.Matrix4();
    visibleBlocks.forEach((block, index) => {
      const height = 0.15 + block.density * 1.1 * (0.5 + blockRng() * 0.9);
      matrix.makeScale(block.w, height, block.d);
      matrix.setPosition(block.x + block.w / 2, height / 2, block.z + block.d / 2);
      blocks.setMatrixAt(index, matrix);
    });
    blocks.castShadow = true;
    blocks.receiveShadow = true;
    scene.add(blocks);

    const streetPositions: number[] = [];
    for (const [from, to] of network.streets) streetPositions.push(from.x, 0.012, from.z, to.x, 0.012, to.z);
    const streetGeometry = track(new THREE.BufferGeometry());
    streetGeometry.setAttribute("position", new THREE.Float32BufferAttribute(streetPositions, 3));
    scene.add(new THREE.LineSegments(streetGeometry, track(new THREE.LineBasicMaterial({
      color: ROAD_BLUE, transparent: true, opacity: 0.2, depthWrite: false,
    }))));

    const avenueSurface = track(new THREE.MeshStandardMaterial({ color: 0x142a42, roughness: 0.72, metalness: 0.1 }));
    const avenueEdge = track(new THREE.LineBasicMaterial({ color: ROAD_BLUE, transparent: true, opacity: 0.72, depthWrite: false }));
    network.arterials.forEach((line, index) => {
      const lift = 0.02 + index * 0.004;
      const strip = new THREE.Mesh(track(createStripGeometry(line, 1.25, lift)), avenueSurface);
      strip.receiveShadow = true;
      scene.add(strip);
      for (const side of [1.25, -1.25]) {
        scene.add(new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(edgePoints(line, side, null, lift + 0.03))), avenueEdge));
      }
    });

    // Elevated roads: decks, pillars, caps and edge lights -----------------
    const deckMaterial = track(new THREE.MeshStandardMaterial({ color: 0x1d3a58, roughness: 0.62, metalness: 0.12 }));
    const pillarMaterial = track(new THREE.MeshStandardMaterial({ color: 0x14283f, roughness: 0.85 }));
    const deckEdge = track(new THREE.LineBasicMaterial({ color: ROAD_CYAN, transparent: true, opacity: 0.6, depthWrite: false }));
    const pillarGeometry = track(new THREE.CylinderGeometry(0.34, 0.42, 1, 12));
    const capGeometry = track(new THREE.BoxGeometry(1, 1, 1));
    type PillarSpot = { x: number; z: number; height: number; angle: number; width: number };
    const pillarSpots: PillarSpot[] = [];
    for (const road of network.elevated) {
      const deck = new THREE.Mesh(track(createDeckGeometry(road)), deckMaterial);
      deck.castShadow = true;
      deck.receiveShadow = true;
      scene.add(deck);
      for (const side of [road.width / 2, -road.width / 2]) {
        scene.add(new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(edgePoints(road.line, side, road.heights, 0.03))), deckEdge));
      }
      for (let index = 0; index < road.line.length; index += 2) {
        const height = road.heights[index] - DECK_THICKNESS;
        if (height < 1.1) continue;
        const previous = road.line[Math.max(0, index - 1)];
        const next = road.line[Math.min(road.line.length - 1, index + 1)];
        pillarSpots.push({ x: road.line[index].x, z: road.line[index].z, height, angle: -Math.atan2(next.z - previous.z, next.x - previous.x), width: road.width });
      }
    }
    const pillars = new THREE.InstancedMesh(pillarGeometry, pillarMaterial, pillarSpots.length);
    const caps = new THREE.InstancedMesh(capGeometry, pillarMaterial, pillarSpots.length);
    const rotation = new THREE.Quaternion();
    const up = new THREE.Vector3(0, 1, 0);
    pillarSpots.forEach((spot, index) => {
      matrix.makeScale(1, spot.height, 1);
      matrix.setPosition(spot.x, spot.height / 2, spot.z);
      pillars.setMatrixAt(index, matrix);
      rotation.setFromAxisAngle(up, spot.angle);
      matrix.compose(new THREE.Vector3(spot.x, spot.height - 0.22, spot.z), rotation, new THREE.Vector3(1.0, 0.44, spot.width * 0.94));
      caps.setMatrixAt(index, matrix);
    });
    pillars.castShadow = true;
    pillars.receiveShadow = true;
    caps.castShadow = true;
    scene.add(pillars, caps);

    // Traffic lights along avenues and elevated decks ------------------------
    const routes: Route[] = [
      ...network.arterials.map((line) => ({ line, heights: null, cumulative: cumulativeDistances(line), length: 0 })),
      ...network.elevated.map((road) => ({ line: road.line, heights: road.heights, cumulative: cumulativeDistances(road.line), length: 0 })),
    ];
    for (const route of routes) route.length = route.cumulative[route.cumulative.length - 1];
    const totalLength = routes.reduce((sum, route) => sum + route.length, 0);
    const rng = createRng(23);
    const trafficCount = 260;
    const travellers: Traveller[] = [];
    for (let index = 0; index < trafficCount; index += 1) {
      let pick = rng() * totalLength;
      let route = 0;
      while (route < routes.length - 1 && pick > routes[route].length) {
        pick -= routes[route].length;
        route += 1;
      }
      travellers.push({ route, distance: pick, speed: (rng() < 0.5 ? -1 : 1) * (2 + rng() * 3) });
    }
    const trafficPositions = new Float32Array(trafficCount * 3);
    const trafficColors = new Float32Array(trafficCount * 3);
    const cool = new THREE.Color(0xd6f1ff);
    const cyanish = new THREE.Color(0x9fe3f7);
    travellers.forEach((_, index) => {
      const color = rng() < 0.6 ? cool : cyanish;
      trafficColors.set([color.r, color.g, color.b], index * 3);
    });
    const trafficGeometry = track(new THREE.BufferGeometry());
    trafficGeometry.setAttribute("position", new THREE.BufferAttribute(trafficPositions, 3));
    trafficGeometry.setAttribute("color", new THREE.BufferAttribute(trafficColors, 3));
    const spriteTexture = createSpriteTexture();
    if (spriteTexture) track(spriteTexture);
    const traffic = new THREE.Points(trafficGeometry, track(new THREE.PointsMaterial({
      size: 0.34, map: spriteTexture, vertexColors: true, transparent: true, opacity: 0.62, depthWrite: false, sizeAttenuation: true, blending: THREE.AdditiveBlending,
    })));
    traffic.frustumCulled = false;
    scene.add(traffic);
    const placeTraveller = (traveller: Traveller, offset: number) => {
      const route = routes[traveller.route];
      const { line, cumulative, heights } = route;
      let low = 1;
      let high = cumulative.length - 1;
      while (low < high) {
        const mid = (low + high) >> 1;
        if (cumulative[mid] < traveller.distance) low = mid + 1;
        else high = mid;
      }
      const span = cumulative[low] - cumulative[low - 1] || 1;
      const t = (traveller.distance - cumulative[low - 1]) / span;
      const from = line[low - 1];
      const to = line[low];
      const y = heights ? heights[low - 1] + (heights[low] - heights[low - 1]) * t : 0;
      trafficPositions[offset] = from.x + (to.x - from.x) * t;
      trafficPositions[offset + 1] = y + 0.14;
      trafficPositions[offset + 2] = from.z + (to.z - from.z) * t;
    };
    const updateTraffic = (delta: number) => {
      travellers.forEach((traveller, index) => {
        const length = routes[traveller.route].length;
        traveller.distance += traveller.speed * delta;
        if (traveller.distance < 0) traveller.distance += length;
        if (traveller.distance > length) traveller.distance -= length;
        placeTraveller(traveller, index * 3);
      });
      trafficGeometry.attributes.position.needsUpdate = true;
    };
    updateTraffic(0);

    // Event markers: two small amber pins (closures) and a few cyan dots -----
    const pulses: Pulse[] = [];
    const discGeometry = track(new THREE.CircleGeometry(0.26, 28));
    const ringGeometry = track(new THREE.RingGeometry(0.4, 0.47, 40));
    const smallDiscGeometry = track(new THREE.CircleGeometry(0.14, 20));
    const smallRingGeometry = track(new THREE.RingGeometry(0.24, 0.29, 32));
    const postGeometry = track(new THREE.CylinderGeometry(0.035, 0.035, 1.2, 8));
    const headGeometry = track(new THREE.SphereGeometry(0.13, 12, 10));
    const amberFlat = track(new THREE.MeshBasicMaterial({ color: EVENT_AMBER, toneMapped: false }));
    const amberRing = track(new THREE.MeshBasicMaterial({ color: EVENT_AMBER, transparent: true, opacity: 0.55, depthWrite: false, side: THREE.DoubleSide }));
    const cyanFlat = track(new THREE.MeshBasicMaterial({ color: ROAD_CYAN }));
    const cyanRing = track(new THREE.MeshBasicMaterial({ color: ROAD_CYAN, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide }));

    const addPulse = (parent: THREE.Object3D, geometry: THREE.BufferGeometry, color: THREE.Color, phase: number, reach: number, peak: number) => {
      const ring = new THREE.Mesh(geometry, track(new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide })));
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.015;
      parent.add(ring);
      pulses.push({ mesh: ring, phase, speed: 0.22, reach, peak });
    };

    network.closures.forEach((closure, index) => {
      const group = new THREE.Group();
      group.position.set(closure.x, 0.06, closure.z);
      scene.add(group);
      const disc = new THREE.Mesh(discGeometry, amberFlat);
      disc.rotation.x = -Math.PI / 2;
      group.add(disc);
      const ring = new THREE.Mesh(ringGeometry, amberRing);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.01;
      group.add(ring);
      addPulse(group, ringGeometry, EVENT_AMBER, index * 0.5, 1.9, 0.3);
      const post = new THREE.Mesh(postGeometry, amberFlat);
      post.position.y = 0.6;
      group.add(post);
      const head = new THREE.Mesh(headGeometry, amberFlat);
      head.position.y = 1.25;
      group.add(head);
    });

    network.markers.forEach((marker, index) => {
      const group = new THREE.Group();
      group.position.set(marker.x, 0.06, marker.z);
      scene.add(group);
      const disc = new THREE.Mesh(smallDiscGeometry, cyanFlat);
      disc.rotation.x = -Math.PI / 2;
      group.add(disc);
      const ring = new THREE.Mesh(smallRingGeometry, cyanRing);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.01;
      group.add(ring);
      addPulse(group, smallRingGeometry, ROAD_CYAN, index * 0.37, 1.5, 0.16);
    });

    // Highlighted detour around the first closure (quiet cyan strip).
    const detourMaterial = track(new THREE.ShaderMaterial({
      uniforms: { uColor: { value: ROAD_CYAN }, uTime: { value: 0 } },
      vertexShader: quadVertexShader,
      fragmentShader: `
        uniform vec3 uColor;
        uniform float uTime;
        varying vec2 vUv;
        void main() {
          float edge = pow(1.0 - abs(vUv.y * 2.0 - 1.0), 1.2);
          float flow = fract(vUv.x * 0.25 - uTime * 0.3);
          float dash = smoothstep(0.0, 0.35, flow) * (1.0 - smoothstep(0.55, 1.0, flow));
          gl_FragColor = vec4(uColor, edge * (0.18 + 0.3 * dash));
        }
      `,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));
    scene.add(new THREE.Mesh(track(createStripGeometry(network.detour, 0.24, 0.07)), detourMaterial));

    // Depth of field: scene to a target with depth, half-res blur, composite ---
    const sceneTarget = track(new THREE.WebGLRenderTarget(1, 1, {
      samples: 4,
      depthTexture: new THREE.DepthTexture(1, 1),
      colorSpace: THREE.SRGBColorSpace,
    }));
    const blurA = track(new THREE.WebGLRenderTarget(1, 1, { colorSpace: THREE.SRGBColorSpace }));
    const blurB = track(new THREE.WebGLRenderTarget(1, 1, { colorSpace: THREE.SRGBColorSpace }));
    const blurMaterial = track(new THREE.ShaderMaterial({
      uniforms: { tInput: { value: null }, uStep: { value: new THREE.Vector2() } },
      vertexShader: quadVertexShader,
      fragmentShader: blurFragmentShader,
      depthTest: false,
      depthWrite: false,
    }));
    const compositeMaterial = track(new THREE.ShaderMaterial({
      uniforms: {
        tSharp: { value: sceneTarget.texture },
        tBlur: { value: blurA.texture },
        tDepth: { value: sceneTarget.depthTexture },
        uNear: { value: camera.near },
        uFar: { value: camera.far },
        uFocusStart: { value: 78 },
        uFocusEnd: { value: 165 },
        uNearBlurEnd: { value: 18 },
      },
      vertexShader: quadVertexShader,
      fragmentShader: compositeFragmentShader,
      depthTest: false,
      depthWrite: false,
    }));
    const quad = new FullScreenQuad(blurMaterial);
    let dofEnabled = true;

    const blurStep = new THREE.Vector2();
    const render = () => {
      if (!dofEnabled) {
        renderer.setRenderTarget(null);
        renderer.render(scene, camera);
        return;
      }
      renderer.setRenderTarget(sceneTarget);
      renderer.render(scene, camera);
      quad.material = blurMaterial;
      const passes: [THREE.WebGLRenderTarget, THREE.Texture, number, number][] = [
        [blurB, sceneTarget.texture, 1, 0],
        [blurA, blurB.texture, 0, 1],
        [blurB, blurA.texture, 2, 0],
        [blurA, blurB.texture, 0, 2],
      ];
      for (const [target, input, dx, dy] of passes) {
        blurMaterial.uniforms.tInput.value = input;
        blurStep.set(dx / blurA.width, dy / blurA.height);
        blurMaterial.uniforms.uStep.value.copy(blurStep);
        renderer.setRenderTarget(target);
        quad.render(renderer);
      }
      quad.material = compositeMaterial;
      renderer.setRenderTarget(null);
      quad.render(renderer);
    };

    // Sizing ----------------------------------------------------------------
    let width = 0;
    let height = 0;
    const applySize = () => {
      renderer.setPixelRatio(pixelRatio);
      renderer.setSize(width, height, false);
      const w = Math.max(1, Math.round(width * pixelRatio));
      const h = Math.max(1, Math.round(height * pixelRatio));
      sceneTarget.setSize(w, h);
      blurA.setSize(Math.ceil(w / 2), Math.ceil(h / 2));
      blurB.setSize(Math.ceil(w / 2), Math.ceil(h / 2));
    };
    const resize = () => {
      const nextWidth = host.clientWidth;
      const nextHeight = host.clientHeight;
      if (!nextWidth || !nextHeight) return;
      width = nextWidth;
      height = nextHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      applySize();
      render();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    resize();

    // Pointer parallax and activity tracking ------------------------------------
    const pointer = new THREE.Vector2(0, 0);
    const pointerTarget = new THREE.Vector2(0, 0);
    let lastActivity = performance.now();
    let idle = false;
    const onPointerMove = (event: PointerEvent) => {
      pointerTarget.set((event.clientX / window.innerWidth) * 2 - 1, (event.clientY / window.innerHeight) * 2 - 1);
      noteActivity();
    };

    // Animation loop: capped at ~30 fps, paused when hidden or off-screen, and
    // stopped after 15 s without pointer, keyboard or focus activity.
    const clock = new THREE.Clock(false);
    let frameId = 0;
    let running = false;
    let intersecting = true;
    let ready = false;
    let lastFrameAt = 0;
    let sampledFrames = 0;
    let sampledTime = 0;
    const frameInterval = 1000 / TARGET_FPS;
    const cameraOffset = new THREE.Vector3();

    const markReady = () => {
      if (ready) return;
      ready = true;
      canvas.style.opacity = "1";
      callbacks.current.onReady?.();
    };

    const tick = (now: number) => {
      frameId = window.requestAnimationFrame(tick);
      if (now - lastActivity > IDLE_STOP_MS) {
        idle = true;
        stop();
        return;
      }
      if (now - lastFrameAt < frameInterval - 1) return;
      lastFrameAt = now;
      const delta = Math.min(clock.getDelta(), 0.08);
      const elapsed = clock.elapsedTime;

      pointer.lerp(pointerTarget, 0.06);
      cameraOffset.set(
        Math.sin(elapsed * 0.09) * 0.8 + pointer.x * 1.0,
        Math.sin(elapsed * 0.06) * 0.25 - pointer.y * 0.35,
        Math.cos(elapsed * 0.07) * 0.5,
      );
      camera.position.copy(cameraBase).add(cameraOffset);
      camera.lookAt(lookTarget.x + pointer.x * 0.8, lookTarget.y, lookTarget.z);

      updateTraffic(delta);
      for (const pulse of pulses) {
        const phase = (elapsed * pulse.speed + pulse.phase) % 1;
        pulse.mesh.scale.setScalar(1 + phase * pulse.reach);
        pulse.mesh.material.opacity = Math.pow(1 - phase, 2) * pulse.peak;
      }
      detourMaterial.uniforms.uTime.value = elapsed;

      render();
      markReady();

      // Adaptive quality: if the first seconds run slowly, drop the depth of
      // field and render at 1x so the page stays smooth on weak GPUs.
      if (dofEnabled && sampledFrames < 60) {
        sampledFrames += 1;
        if (sampledFrames > 15) sampledTime += delta;
        if (sampledFrames === 60 && sampledTime / 45 > 0.05) {
          dofEnabled = false;
          pixelRatio = 1;
          applySize();
        }
      }
    };

    const start = () => {
      if (running || reducedMotion) return;
      running = true;
      clock.start();
      lastFrameAt = 0;
      frameId = window.requestAnimationFrame(tick);
    };
    const stop = () => {
      if (!running) return;
      running = false;
      clock.stop();
      window.cancelAnimationFrame(frameId);
    };
    const syncRunning = () => {
      if (intersecting && !document.hidden && !idle) start();
      else stop();
    };
    function noteActivity() {
      lastActivity = performance.now();
      if (idle) {
        idle = false;
        syncRunning();
      }
    }

    const activityEvents: (keyof WindowEventMap)[] = ["pointerdown", "keydown", "focusin", "touchstart", "wheel"];
    if (!reducedMotion) {
      window.addEventListener("pointermove", onPointerMove, { passive: true });
      for (const type of activityEvents) window.addEventListener(type, noteActivity, { passive: true });
    }

    if (reducedMotion) {
      render();
      markReady();
    } else {
      syncRunning();
    }

    const intersectionObserver = new IntersectionObserver(([entry]) => {
      intersecting = entry.isIntersecting;
      syncRunning();
    });
    intersectionObserver.observe(host);
    document.addEventListener("visibilitychange", syncRunning);

    return () => {
      stop();
      document.removeEventListener("visibilitychange", syncRunning);
      window.removeEventListener("pointermove", onPointerMove);
      for (const type of activityEvents) window.removeEventListener(type, noteActivity);
      intersectionObserver.disconnect();
      resizeObserver.disconnect();
      quad.dispose();
      sceneTarget.depthTexture?.dispose();
      for (const item of disposables) item.dispose();
      renderer.setRenderTarget(null);
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    };
  }, []);

  return <div ref={hostRef} aria-hidden="true" className="absolute inset-0 overflow-hidden" />;
}
