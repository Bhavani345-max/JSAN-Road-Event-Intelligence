"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { FullScreenQuad } from "three/examples/jsm/postprocessing/Pass.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { createRng, generateRoadNetwork, headingAt, type ElevatedRoad, type Point, type Polyline, type SceneEventType } from "./roadNetwork";
import { loginColors, loginEventColors, loginSceneColors } from "./loginTheme";

/**
 * Decorative daylight "smart city" for the sign-in page, seen from a high,
 * almost isometric angle: white buildings with glass windows, glass towers on
 * the skyline, asphalt avenues with lane markings, a flyover and a viaduct on
 * pillars with blue light trails, street trees, a canal, small cars in both
 * directions, a blue route line around a closure and four map pins in the
 * console's own event colours, each with a glowing ring on the road.
 *
 * Real 3D: all geometry, the sun/sky lighting, the shadow map (rendered once)
 * and the depth-based depth of field. Purely procedural and purely
 * illustrative: no real place and no product data.
 */

type RoadSceneProps = {
  onReady?: () => void;
  onUnavailable?: () => void;
};

const SKY = new THREE.Color(loginColors.pageBackground);
const HAZE = new THREE.Color(loginColors.sceneHaze);
const DECK_THICKNESS = 0.6;
const TARGET_FPS = 30;
const IDLE_STOP_MS = 15_000;
const AVENUE_HALF = 1.3;
const ROAD_TILE = 12; // world units covered by one repeat of the asphalt texture
const CAMERA_FOV = 34;
const CAMERA_POSITION = new THREE.Vector3(-12, 40, 42);
const CAMERA_TARGET = new THREE.Vector3(5, 0, -18);

type Route = { line: Polyline; heights: number[] | null; cumulative: number[]; length: number; width: number };
type Car = { route: number; distance: number; speed: number; direction: 1 | -1; lane: number };

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

/** The polyline moved sideways by `offset` (positive = left of travel). */
function offsetLine(line: Polyline, offset: number): Polyline {
  return line.map((point, index) => {
    const [nx, nz] = sideNormal(line[Math.max(0, index - 1)], line[Math.min(line.length - 1, index + 1)]);
    return { x: point.x + nx * offset, z: point.z + nz * offset };
  });
}

/** Flat strip following a polyline; optional per-point heights (deck tops). */
function createStripGeometry(line: Polyline, halfWidth: number, lift: number, heights: number[] | null = null): THREE.BufferGeometry {
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
    const yFrom = (heights ? heights[index - 1] : 0) + lift;
    const yTo = (heights ? heights[index] : 0) + lift;
    const base = positions.length / 3;
    positions.push(
      from.x + nx * halfWidth, yFrom, from.z + nz * halfWidth,
      from.x - nx * halfWidth, yFrom, from.z - nz * halfWidth,
      to.x + nx * halfWidth, yTo, to.z + nz * halfWidth,
      to.x - nx * halfWidth, yTo, to.z - nz * halfWidth,
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

/** Thin vertical wall along a polyline edge (crash barriers). */
function createWallGeometry(line: Polyline, offset: number, heights: number[], lift: number, height: number): THREE.BufferGeometry {
  const positions: number[] = [];
  const indices: number[] = [];
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const to = line[index];
    const [nx, nz] = sideNormal(from, to);
    const base = positions.length / 3;
    const yFrom = heights[index - 1] + lift;
    const yTo = heights[index] + lift;
    positions.push(
      from.x + nx * offset, yFrom, from.z + nz * offset,
      from.x + nx * offset, yFrom + height, from.z + nz * offset,
      to.x + nx * offset, yTo, to.z + nz * offset,
      to.x + nx * offset, yTo + height, to.z + nz * offset,
    );
    indices.push(base, base + 2, base + 1, base + 1, base + 2, base + 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
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
    const fl = [from.x + nx * half, topFrom, from.z + nz * half];
    const fr = [from.x - nx * half, topFrom, from.z - nz * half];
    const tl = [to.x + nx * half, topTo, to.z + nz * half];
    const tr = [to.x - nx * half, topTo, to.z - nz * half];
    const flb = [fl[0], topFrom - DECK_THICKNESS, fl[2]];
    const frb = [fr[0], topFrom - DECK_THICKNESS, fr[2]];
    const tlb = [tl[0], topTo - DECK_THICKNESS, tl[2]];
    const trb = [tr[0], topTo - DECK_THICKNESS, tr[2]];
    quad(fl, tl, tr, fr);
    quad(frb, trb, tlb, flb);
    quad(fl, flb, tlb, tl);
    quad(fr, tr, trb, frb);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}

function canvasTexture(width: number, height: number, paint: (context: CanvasRenderingContext2D) => void): THREE.CanvasTexture | null {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return null;
  paint(context);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

/** Asphalt with solid white edges, dashed lane lines and a double amber centre. */
function createAsphaltTexture(rng: () => number): THREE.CanvasTexture | null {
  const texture = canvasTexture(512, 128, (context) => {
    context.fillStyle = loginSceneColors.asphalt;
    context.fillRect(0, 0, 512, 128);
    for (let index = 0; index < 1400; index += 1) {
      const shade = 90 + Math.floor(rng() * 60);
      context.fillStyle = `rgba(${shade}, ${shade + 6}, ${shade + 12}, 0.3)`;
      context.fillRect(rng() * 512, rng() * 128, 2, 2);
    }
    context.fillStyle = "rgba(255,255,255,0.95)";
    context.fillRect(0, 6, 512, 3);
    context.fillRect(0, 119, 512, 3);
    for (let x = 0; x < 512; x += 48) {
      context.fillRect(x, 34, 22, 2.5);
      context.fillRect(x, 92, 22, 2.5);
    }
    context.fillStyle = "rgba(236, 186, 72, 0.95)";
    context.fillRect(0, 60, 512, 2.5);
    context.fillRect(0, 66, 512, 2.5);
  });
  if (texture) {
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.repeat.set(1 / ROAD_TILE, 1);
  }
  return texture;
}

function createStripeTexture(colour: string): THREE.CanvasTexture | null {
  const texture = canvasTexture(128, 32, (context) => {
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, 128, 32);
    context.fillStyle = colour;
    for (let x = -32; x < 160; x += 32) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x + 16, 0);
      context.lineTo(x + 32, 32);
      context.lineTo(x + 16, 32);
      context.closePath();
      context.fill();
    }
  });
  if (texture) texture.wrapS = THREE.RepeatWrapping;
  return texture;
}

function createZebraTexture(): THREE.CanvasTexture | null {
  return canvasTexture(128, 64, (context) => {
    context.clearRect(0, 0, 128, 64);
    context.fillStyle = "rgba(255,255,255,0.95)";
    for (let x = 6; x < 128; x += 20) context.fillRect(x, 4, 11, 56);
  });
}

/** Box with darker vertex colours at the base (cheap contact-occlusion feel). */
function createShadedBox(): THREE.BoxGeometry {
  const geometry = new THREE.BoxGeometry(1, 1, 1);
  const position = geometry.attributes.position;
  const colors = new Float32Array(position.count * 3);
  for (let index = 0; index < position.count; index += 1) {
    const shade = position.getY(index) < 0 ? 0.86 : 1;
    colors.set([shade, shade, shade], index * 3);
  }
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return geometry;
}

/**
 * Procedural windows on the walls of instanced boxes, computed from world
 * position so every building gets real floor heights whatever its size. They
 * fade out with distance to avoid shimmering.
 */
function addWindows(material: THREE.MeshStandardMaterial, key: string, glass: string, floor: number, column: number, cover: number) {
  material.customProgramCacheKey = () => `rei-windows-${key}`;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uGlass = { value: new THREE.Color(glass) };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vReiWorld;\nvarying vec3 vReiNormal;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        mat4 reiModel = modelMatrix;
        #ifdef USE_INSTANCING
          reiModel = modelMatrix * instanceMatrix;
        #endif
        vReiWorld = (reiModel * vec4(position, 1.0)).xyz;
        vReiNormal = normalize(mat3(reiModel) * normal);`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 uGlass;\nvarying vec3 vReiWorld;\nvarying vec3 vReiNormal;")
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        if (abs(vReiNormal.y) < 0.5) {
          float along = abs(vReiNormal.x) > 0.5 ? vReiWorld.z : vReiWorld.x;
          float band = fract(vReiWorld.y / ${floor.toFixed(3)});
          float col = fract(along / ${column.toFixed(3)});
          float edge = 0.5 * (1.0 - ${cover.toFixed(3)});
          float pane = smoothstep(edge, edge + 0.06, band) * (1.0 - smoothstep(1.0 - edge - 0.06, 1.0 - edge, band))
            * smoothstep(edge, edge + 0.06, col) * (1.0 - smoothstep(1.0 - edge - 0.06, 1.0 - edge, col))
            * step(0.3, vReiWorld.y);
          float fade = 1.0 - smoothstep(70.0, 125.0, length(vViewPosition));
          diffuseColor.rgb = mix(diffuseColor.rgb, uGlass, pane * fade * 0.9);
        }`,
      );
  };
}

function mixHex(colour: string, other: string, amount: number): string {
  return `#${new THREE.Color(colour).lerp(new THREE.Color(other), amount).getHexString()}`;
}

type IconPainter = (context: CanvasRenderingContext2D, colour: string) => void;

/** White icons drawn inside a pin head centred on (128, 112). */
const PIN_ICONS: Record<SceneEventType, IconPainter> = {
  // No entry: a white bar.
  EMERGENCY_ROAD_CLOSURE: (context) => {
    context.beginPath();
    context.roundRect(80, 98, 96, 28, 8);
    context.fill();
  },
  // A traffic cone with two coloured bands.
  ROAD_CONSTRUCTION: (context, colour) => {
    context.beginPath();
    context.moveTo(118, 58);
    context.lineTo(138, 58);
    context.lineTo(162, 148);
    context.lineTo(94, 148);
    context.closePath();
    context.fill();
    context.beginPath();
    context.roundRect(80, 146, 96, 16, 6);
    context.fill();
    context.fillStyle = colour;
    context.fillRect(100, 82, 56, 14);
    context.fillRect(94, 112, 68, 14);
  },
  // A detour arrow: up, then turning right.
  TRAFFIC_DIVERSION: (context) => {
    context.lineWidth = 18;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.beginPath();
    context.moveTo(100, 160);
    context.lineTo(100, 118);
    context.quadraticCurveTo(100, 90, 128, 90);
    context.lineTo(138, 90);
    context.stroke();
    context.beginPath();
    context.moveTo(134, 60);
    context.lineTo(170, 90);
    context.lineTo(134, 120);
    context.closePath();
    context.fill();
  },
  // A start/finish flag for a marathon.
  MARATHON: (context) => {
    context.beginPath();
    context.roundRect(92, 60, 12, 106, 5);
    context.fill();
    context.beginPath();
    context.moveTo(104, 64);
    context.bezierCurveTo(128, 54, 142, 78, 168, 66);
    context.lineTo(168, 116);
    context.bezierCurveTo(142, 128, 128, 104, 104, 114);
    context.closePath();
    context.fill();
  },
};

/** A map pin (coloured teardrop, white rim and icon, soft shadow) as a sprite texture. */
function createPinTexture(type: SceneEventType): THREE.CanvasTexture | null {
  const colour = loginEventColors[type];
  return canvasTexture(256, 320, (context) => {
    const cx = 128;
    const cy = 112;
    const radius = 92;
    const tipY = 300;
    const tangent = Math.asin(radius / (tipY - cy));
    const start = Math.PI / 2 + (Math.PI / 2 - tangent);
    const end = Math.PI / 2 - (Math.PI / 2 - tangent);
    const teardrop = () => {
      context.beginPath();
      context.arc(cx, cy, radius, start, end, false);
      context.lineTo(cx, tipY);
      context.closePath();
    };
    context.save();
    context.shadowColor = "rgba(15, 23, 42, 0.32)";
    context.shadowBlur = 16;
    context.shadowOffsetY = 6;
    teardrop();
    context.fillStyle = "#ffffff";
    context.fill();
    context.restore();
    context.save();
    context.translate(cx, cy + 6);
    context.scale(0.9, 0.9);
    context.translate(-cx, -(cy + 6));
    teardrop();
    const gradient = context.createLinearGradient(0, cy - radius, 0, tipY);
    gradient.addColorStop(0, mixHex(colour, "#ffffff", 0.22));
    gradient.addColorStop(1, mixHex(colour, "#000000", 0.12));
    context.fillStyle = gradient;
    context.fill();
    context.restore();
    context.fillStyle = "#ffffff";
    context.strokeStyle = "#ffffff";
    PIN_ICONS[type](context, colour);
  });
}

const quadVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

/** Faint lane line with bright streaks travelling along it (uv.x is distance in world units). */
const trailFragmentShader = `
  uniform vec3 uColor;
  uniform float uTime;
  uniform float uSpeed;
  varying vec2 vUv;
  void main() {
    float across = smoothstep(0.0, 0.4, vUv.y) * smoothstep(1.0, 0.6, vUv.y);
    float s = fract(vUv.x * 0.045 - uTime * uSpeed);
    float streak = smoothstep(0.0, 0.015, s) * (1.0 - smoothstep(0.015, 0.4, s));
    gl_FragColor = vec4(mix(uColor, vec3(1.0), streak * 0.35), across * (0.22 + 0.78 * streak));
  }
`;

/** Glowing ring on the road under a pin, with a slow outward pulse. */
const haloFragmentShader = `
  uniform vec3 uColor;
  uniform float uTime;
  uniform float uPhase;
  varying vec2 vUv;
  void main() {
    float r = length(vUv * 2.0 - 1.0);
    if (r > 1.0) discard;
    float disc = (1.0 - smoothstep(0.0, 0.6, r)) * 0.32;
    float ring = smoothstep(0.5, 0.57, r) * (1.0 - smoothstep(0.6, 0.68, r)) * 0.8;
    float t = fract(uTime * 0.4 + uPhase);
    float wave = smoothstep(t - 0.08, t, r) * (1.0 - smoothstep(t, t + 0.05, r)) * (1.0 - t) * 0.7;
    gl_FragColor = vec4(uColor, max(disc, max(ring, wave)));
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
  varying vec2 vUv;
  void main() {
    float depth = texture2D(tDepth, vUv).x;
    float dist = -perspectiveDepthToViewZ(depth, uNear, uFar);
    float amount = smoothstep(uFocusStart, uFocusEnd, dist);
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
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;
    renderer.info.autoReset = false;
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
    const standard = (options: THREE.MeshStandardMaterialParameters) => track(new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0, ...options }));

    const scene = new THREE.Scene();
    scene.background = SKY;
    scene.fog = new THREE.Fog(HAZE, 80, 190);

    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1, 1, 400);
    camera.position.copy(CAMERA_POSITION);
    camera.lookAt(CAMERA_TARGET);

    // Daylight: warm sun with one static soft shadow map, cool sky fill.
    scene.add(new THREE.HemisphereLight(0xe3edf8, 0xf1f4f7, 1.45));
    const sun = new THREE.DirectionalLight(0xfff4e6, 2.0);
    sun.position.set(-46, 72, 30);
    sun.target.position.set(0, 0, -24);
    sun.castShadow = true;
    sun.shadow.intensity = 0.45;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -72;
    sun.shadow.camera.right = 72;
    sun.shadow.camera.top = 72;
    sun.shadow.camera.bottom = -72;
    sun.shadow.camera.near = 8;
    sun.shadow.camera.far = 240;
    sun.shadow.bias = -0.0005;
    sun.shadow.normalBias = 0.05;
    scene.add(sun, sun.target);
    track(sun.shadow);
    const fill = new THREE.DirectionalLight(0xdbe9f5, 0.5);
    fill.position.set(50, 30, -20);
    scene.add(fill);

    const network = generateRoadNetwork(7, 160);
    const rng = createRng(23);
    const matrix = new THREE.Matrix4();
    const rotation = new THREE.Quaternion();
    const up = new THREE.Vector3(0, 1, 0);
    const position = new THREE.Vector3();
    const scale = new THREE.Vector3();

    // Ground, canal, parks -----------------------------------------------------
    const ground = new THREE.Mesh(track(new THREE.PlaneGeometry(260, 260)), standard({ color: loginColors.sceneGround, roughness: 0.95 }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const river = new THREE.Mesh(track(createStripGeometry(network.river, 3.8, 0.012)), standard({ color: loginSceneColors.water, roughness: 0.25, metalness: 0.1 }));
    river.receiveShadow = true;
    const banks = new THREE.Mesh(
      track(mergeGeometries([1, -1].map((side) => createStripGeometry(offsetLine(network.river, side * 4.05), 0.28, 0.02)))),
      standard({ color: loginSceneColors.kerb }),
    );
    banks.receiveShadow = true;
    scene.add(river, banks);

    const parkGeometry = track(new THREE.PlaneGeometry(1, 1));
    parkGeometry.rotateX(-Math.PI / 2);
    const parks = new THREE.InstancedMesh(parkGeometry, standard({ color: loginSceneColors.park, roughness: 1 }), network.parks.length);
    network.parks.forEach((park, index) => {
      matrix.makeScale(park.w, 1, park.d);
      matrix.setPosition(park.x + park.w / 2, 0.015, park.z + park.d / 2);
      parks.setMatrixAt(index, matrix);
    });
    parks.receiveShadow = true;
    scene.add(parks);

    // Buildings: white massing with windows and darker bases; glass towers ---
    const blockGeometry = track(createShadedBox());
    const buildingMaterial = standard({ color: loginColors.sceneMassing, vertexColors: true });
    addWindows(buildingMaterial, "building", loginSceneColors.windowGlass, 0.46, 0.38, 0.5);
    const buildings = new THREE.InstancedMesh(blockGeometry, buildingMaterial, network.buildings.length);
    network.buildings.forEach((building, index) => {
      matrix.makeScale(building.w, building.h, building.d);
      matrix.setPosition(building.x + building.w / 2, building.h / 2, building.z + building.d / 2);
      buildings.setMatrixAt(index, matrix);
    });
    buildings.castShadow = true;
    buildings.receiveShadow = true;
    scene.add(buildings);

    const towerMaterial = standard({ color: 0xf6f9fc, vertexColors: true, roughness: 0.45, metalness: 0.08 });
    addWindows(towerMaterial, "tower", loginSceneColors.towerGlass, 0.4, 0.3, 0.72);
    const towers = new THREE.InstancedMesh(blockGeometry, towerMaterial, network.towers.length);
    const roofUnits = new THREE.InstancedMesh(blockGeometry, standard({ color: 0xe6ebf1, vertexColors: true }), network.towers.length * 2);
    network.towers.forEach((tower, index) => {
      const height = 7 + rng() * 9;
      const w = tower.w * 0.82;
      const d = tower.d * 0.82;
      const cx = tower.x + tower.w / 2;
      const cz = tower.z + tower.d / 2;
      matrix.makeScale(w, height, d);
      matrix.setPosition(cx, height / 2, cz);
      towers.setMatrixAt(index, matrix);
      matrix.makeScale(0.6, 0.35, 0.5);
      matrix.setPosition(cx - w * 0.22, height + 0.17, cz - d * 0.2);
      roofUnits.setMatrixAt(index * 2, matrix);
      matrix.makeScale(0.4, 0.25, 0.4);
      matrix.setPosition(cx + w * 0.22, height + 0.12, cz + d * 0.22);
      roofUnits.setMatrixAt(index * 2 + 1, matrix);
    });
    towers.castShadow = true;
    towers.receiveShadow = true;
    roofUnits.castShadow = true;
    scene.add(towers, roofUnits);

    // Trees ---------------------------------------------------------------------
    const trunkGeometry = track(new THREE.CylinderGeometry(0.05, 0.07, 0.6, 6));
    const crownGeometry = track(new THREE.IcosahedronGeometry(0.46, 1));
    const trunks = new THREE.InstancedMesh(trunkGeometry, standard({ color: loginSceneColors.treeTrunk }), network.trees.length);
    const crowns = new THREE.InstancedMesh(crownGeometry, standard({ color: 0xffffff }), network.trees.length);
    const crownColour = new THREE.Color();
    network.trees.forEach((tree, index) => {
      const size = 0.7 + rng() * 0.45;
      matrix.makeScale(1, size, 1);
      matrix.setPosition(tree.x, size * 0.3, tree.z);
      trunks.setMatrixAt(index, matrix);
      matrix.makeScale(size, size * 0.95, size);
      matrix.setPosition(tree.x, size * 0.62 + 0.34, tree.z);
      crowns.setMatrixAt(index, matrix);
      crownColour.set(loginSceneColors.treeCrowns[index % loginSceneColors.treeCrowns.length]);
      crowns.setColorAt(index, crownColour);
    });
    crowns.castShadow = true;
    scene.add(trunks, crowns);

    // Roads: kerbs, asphalt avenues with markings, minor streets, crossings -----
    const asphaltTexture = createAsphaltTexture(rng);
    if (asphaltTexture) track(asphaltTexture);
    const asphaltMaterial = standard({ color: 0xffffff, map: asphaltTexture, roughness: 0.95 });
    const kerbMaterial = standard({ color: loginSceneColors.kerb });
    const minorMaterial = standard({ color: loginSceneColors.minorStreet });

    const kerbs = track(mergeGeometries(network.arterials.map((line, index) => createStripGeometry(line, network.arterialHalfWidths[index] + 0.5, 0.018 + index * 0.003))));
    const kerbMesh = new THREE.Mesh(kerbs, kerbMaterial);
    kerbMesh.receiveShadow = true;
    scene.add(kerbMesh);
    const avenues = track(mergeGeometries(network.arterials.map((line, index) => createStripGeometry(line, network.arterialHalfWidths[index], 0.03 + index * 0.003))));
    const avenueMesh = new THREE.Mesh(avenues, asphaltMaterial);
    avenueMesh.receiveShadow = true;
    scene.add(avenueMesh);

    const minorStreets = track(mergeGeometries(network.streets.map(([from, to]) => createStripGeometry([from, to], 0.38, 0.014))));
    const minorMesh = new THREE.Mesh(minorStreets, minorMaterial);
    minorMesh.receiveShadow = true;
    scene.add(minorMesh);

    const zebraTexture = createZebraTexture();
    if (zebraTexture) track(zebraTexture);
    const zebraGeometry = track(new THREE.PlaneGeometry(1.6, 2.3));
    zebraGeometry.rotateX(-Math.PI / 2);
    const crossings = new THREE.InstancedMesh(zebraGeometry, track(new THREE.MeshBasicMaterial({ map: zebraTexture, transparent: true, depthWrite: false })), network.crossings.length);
    network.crossings.forEach((crossing, index) => {
      rotation.setFromAxisAngle(up, crossing.angle);
      matrix.compose(position.set(crossing.point.x, 0.08, crossing.point.z), rotation, scale.set(1, 1, 1));
      crossings.setMatrixAt(index, matrix);
    });
    scene.add(crossings);

    // Elevated roads: concrete decks, asphalt tops, barriers, pillars ---------
    const concrete = standard({ color: loginSceneColors.concrete });
    const barrierMaterial = standard({ color: loginSceneColors.barrier, side: THREE.DoubleSide });
    const deckMesh = new THREE.Mesh(track(mergeGeometries(network.elevated.map(createDeckGeometry))), concrete);
    deckMesh.castShadow = true;
    deckMesh.receiveShadow = true;
    scene.add(deckMesh);
    const deckTops = new THREE.Mesh(
      track(mergeGeometries(network.elevated.map((road) => createStripGeometry(road.line, road.width / 2 - 0.3, 0.02, road.heights)))),
      asphaltMaterial,
    );
    deckTops.receiveShadow = true;
    scene.add(deckTops);
    const barriers = new THREE.Mesh(
      track(mergeGeometries(network.elevated.flatMap((road) => [
        createWallGeometry(road.line, road.width / 2 - 0.12, road.heights, 0, 0.42),
        createWallGeometry(road.line, -(road.width / 2 - 0.12), road.heights, 0, 0.42),
      ]))),
      barrierMaterial,
    );
    scene.add(barriers);

    const pillarGeometry = track(new THREE.CylinderGeometry(0.34, 0.42, 1, 12));
    const capGeometry = track(new THREE.BoxGeometry(1, 1, 1));
    type PillarSpot = { x: number; z: number; height: number; angle: number; width: number };
    const pillarSpots: PillarSpot[] = [];
    for (const road of network.elevated) {
      for (let index = 0; index < road.line.length; index += 2) {
        const height = road.heights[index] - DECK_THICKNESS;
        if (height < 1.1) continue;
        pillarSpots.push({ x: road.line[index].x, z: road.line[index].z, height, angle: headingAt(road.line, index), width: road.width });
      }
    }
    const pillarMaterial = standard({ color: 0xedf1f5 });
    const pillars = new THREE.InstancedMesh(pillarGeometry, pillarMaterial, pillarSpots.length);
    const caps = new THREE.InstancedMesh(capGeometry, pillarMaterial, pillarSpots.length);
    pillarSpots.forEach((spot, index) => {
      matrix.makeScale(1, spot.height, 1);
      matrix.setPosition(spot.x, spot.height / 2, spot.z);
      pillars.setMatrixAt(index, matrix);
      rotation.setFromAxisAngle(up, spot.angle);
      matrix.compose(position.set(spot.x, spot.height - 0.22, spot.z), rotation, scale.set(1.0, 0.44, spot.width * 0.94));
      caps.setMatrixAt(index, matrix);
    });
    pillars.castShadow = true;
    pillars.receiveShadow = true;
    caps.castShadow = true;
    scene.add(pillars, caps);

    // Light trails on the decks and the ring road (one per direction) -------
    const trailMaterial = (colour: string, speed: number) =>
      track(new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color(colour) }, uTime: { value: 0 }, uSpeed: { value: speed } },
        vertexShader: quadVertexShader,
        fragmentShader: trailFragmentShader,
        transparent: true,
        depthWrite: false,
        fog: false,
      }));
    const trailsAhead = trailMaterial(loginSceneColors.trailBlue, 0.55);
    const trailsBack = trailMaterial(loginSceneColors.trailCyan, -0.48);
    const ring = network.arterials[7];
    const trailGeometry = (side: 1 | -1) =>
      track(mergeGeometries([
        ...network.elevated.map((road) => createStripGeometry(offsetLine(road.line, side * (road.width / 4)), 0.16, 0.07, road.heights)),
        createStripGeometry(offsetLine(ring, side * AVENUE_HALF * 0.5), 0.12, 0.07),
      ]));
    scene.add(new THREE.Mesh(trailGeometry(-1), trailsAhead), new THREE.Mesh(trailGeometry(1), trailsBack));

    // Road events: works cones, closure barrier, route line around it ---------
    const closure = network.closures[0];
    const closureIndex = network.arterials[0].findIndex((point) => point === closure);
    const closureAngle = headingAt(network.arterials[0], Math.max(0, closureIndex));

    const coneGeometry = track(new THREE.ConeGeometry(0.17, 0.52, 10));
    const cones = new THREE.InstancedMesh(coneGeometry, standard({ color: 0xffffff, roughness: 0.7 }), network.works.length * 2);
    const coneColour = new THREE.Color(loginEventColors.ROAD_CONSTRUCTION);
    network.works.forEach((point, index) => {
      const angle = headingAt(network.works, index);
      [0.55, -0.55].forEach((side, sideIndex) => {
        matrix.makeTranslation(point.x + Math.sin(angle) * side, 0.3, point.z + Math.cos(angle) * side);
        cones.setMatrixAt(index * 2 + sideIndex, matrix);
        cones.setColorAt(index * 2 + sideIndex, coneColour);
      });
    });
    cones.castShadow = true;
    scene.add(cones);

    const stripeTexture = createStripeTexture(loginEventColors.EMERGENCY_ROAD_CLOSURE);
    if (stripeTexture) track(stripeTexture);
    const barrier = new THREE.Mesh(track(new THREE.BoxGeometry(2.4, 0.36, 0.1)), standard({ color: 0xffffff, map: stripeTexture, roughness: 0.6 }));
    barrier.position.set(closure.x, 0.5, closure.z);
    barrier.rotation.y = closureAngle + Math.PI / 2;
    barrier.castShadow = true;
    scene.add(barrier);
    const legGeometry = track(new THREE.BoxGeometry(0.08, 0.5, 0.5));
    const legs = new THREE.InstancedMesh(legGeometry, standard({ color: 0x9aa3ad }), 2);
    [-1, 1].forEach((side, index) => {
      rotation.setFromAxisAngle(up, closureAngle + Math.PI / 2);
      matrix.compose(position.set(closure.x + Math.sin(closureAngle) * side * 1.05, 0.25, closure.z + Math.cos(closureAngle) * side * 1.05), rotation, scale.set(1, 1, 1));
      legs.setMatrixAt(index, matrix);
    });
    scene.add(legs);

    // The diversion as a GIS route line: a soft glow under a flowing core.
    const routeColour = new THREE.Color(loginSceneColors.route);
    scene.add(new THREE.Mesh(
      track(createStripGeometry(network.detour, 0.7, 0.05)),
      track(new THREE.MeshBasicMaterial({ color: routeColour, transparent: true, opacity: 0.16, depthWrite: false })),
    ));
    const routeMaterial = track(new THREE.ShaderMaterial({
      uniforms: { uColor: { value: routeColour }, uTime: { value: 0 } },
      vertexShader: quadVertexShader,
      fragmentShader: `
        uniform vec3 uColor; uniform float uTime; varying vec2 vUv;
        void main() {
          float edge = smoothstep(0.0, 0.25, vUv.y) * smoothstep(1.0, 0.75, vUv.y);
          float flow = fract(vUv.x * 0.5 - uTime * 0.35);
          float dash = smoothstep(0.0, 0.1, flow) * (1.0 - smoothstep(0.6, 0.7, flow));
          gl_FragColor = vec4(mix(uColor, vec3(1.0), dash * 0.25), edge * (0.55 + 0.45 * dash));
        }
      `,
      transparent: true,
      depthWrite: false,
    }));
    scene.add(new THREE.Mesh(track(createStripGeometry(network.detour, 0.24, 0.07)), routeMaterial));

    // Map pins (sprites, always readable) over glowing rings on the road ------
    const haloGeometry = track(new THREE.PlaneGeometry(1, 1));
    haloGeometry.rotateX(-Math.PI / 2);
    type Pin = { sprite: THREE.Sprite; lift: number; phase: number; halo: THREE.ShaderMaterial };
    const pins: Pin[] = network.events.map((event, index) => {
      const texture = createPinTexture(event.type);
      if (texture) track(texture);
      const sprite = new THREE.Sprite(track(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false, depthWrite: false, fog: false })));
      sprite.center.set(0.5, 0.02);
      sprite.scale.set(2.5, 3.1, 1);
      sprite.position.set(event.point.x, event.lift + 0.25, event.point.z);
      sprite.renderOrder = 10;
      const halo = track(new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color(loginEventColors[event.type]) }, uTime: { value: 0 }, uPhase: { value: index * 0.27 } },
        vertexShader: quadVertexShader,
        fragmentShader: haloFragmentShader,
        transparent: true,
        depthWrite: false,
      }));
      const haloMesh = new THREE.Mesh(haloGeometry, halo);
      haloMesh.scale.set(5.2, 1, 5.2);
      haloMesh.position.set(event.point.x, event.lift + 0.09, event.point.z);
      haloMesh.renderOrder = 5;
      scene.add(haloMesh, sprite);
      return { sprite, lift: event.lift, phase: index * 1.3, halo };
    });
    const placePins = (elapsed: number) => {
      for (const pin of pins) {
        pin.sprite.position.y = pin.lift + 0.25 + Math.sin(elapsed * 1.4 + pin.phase) * 0.14;
        pin.halo.uniforms.uTime.value = elapsed;
      }
    };
    placePins(0);

    // Cars: one instanced mesh, lane-aware, both directions, slower near events
    const bodyGeometry = new THREE.BoxGeometry(0.46, 0.15, 0.22);
    bodyGeometry.translate(0, 0.075, 0);
    const cabinGeometry = new THREE.BoxGeometry(0.24, 0.11, 0.19);
    cabinGeometry.translate(-0.02, 0.2, 0);
    const carGeometry = track(mergeGeometries([bodyGeometry, cabinGeometry]));
    bodyGeometry.dispose();
    cabinGeometry.dispose();
    const routes: Route[] = [
      ...network.arterials.map((line, index) => ({ line, heights: null, cumulative: cumulativeDistances(line), length: 0, width: network.arterialHalfWidths[index] })),
      ...network.elevated.map((road) => ({ line: road.line, heights: road.heights, cumulative: cumulativeDistances(road.line), length: 0, width: road.width / 2 - 0.3 })),
    ];
    for (const route of routes) route.length = route.cumulative[route.cumulative.length - 1];
    const totalLength = routes.reduce((sum, route) => sum + route.length, 0);
    const carCount = 260;
    const cars: Car[] = [];
    for (let index = 0; index < carCount; index += 1) {
      let pick = rng() * totalLength;
      let route = 0;
      while (route < routes.length - 1 && pick > routes[route].length) {
        pick -= routes[route].length;
        route += 1;
      }
      const direction: 1 | -1 = rng() < 0.5 ? -1 : 1;
      cars.push({ route, distance: pick, speed: 2.6 + rng() * 2.2, direction, lane: routes[route].width * 0.5 });
    }
    const carMesh = new THREE.InstancedMesh(carGeometry, standard({ color: 0xffffff, roughness: 0.35, metalness: 0.25 }), carCount);
    const carColour = new THREE.Color();
    cars.forEach((_, index) => {
      carColour.set(loginSceneColors.cars[Math.floor(rng() * loginSceneColors.cars.length)]);
      carMesh.setColorAt(index, carColour);
    });
    scene.add(carMesh);
    const slowZones = network.events.filter((event) => event.lift === 0).map((event) => event.point);
    const updateCars = (delta: number) => {
      cars.forEach((car, index) => {
        const route = routes[car.route];
        const { line, cumulative, heights } = route;
        let low = 1;
        let high = cumulative.length - 1;
        while (low < high) {
          const mid = (low + high) >> 1;
          if (cumulative[mid] < car.distance) low = mid + 1;
          else high = mid;
        }
        const span = cumulative[low] - cumulative[low - 1] || 1;
        const t = (car.distance - cumulative[low - 1]) / span;
        const from = line[low - 1];
        const to = line[low];
        const x = from.x + (to.x - from.x) * t;
        const z = from.z + (to.z - from.z) * t;
        const y = heights ? heights[low - 1] + (heights[low] - heights[low - 1]) * t : 0;
        const [nx, nz] = sideNormal(from, to);
        // Right-hand traffic: offset to the right of the travel direction.
        const side = -car.lane * car.direction;
        const heading = Math.atan2(-(to.z - from.z) * car.direction, (to.x - from.x) * car.direction);
        rotation.setFromAxisAngle(up, heading);
        matrix.compose(position.set(x + nx * side, y + 0.05, z + nz * side), rotation, scale.set(1, 1, 1));
        carMesh.setMatrixAt(index, matrix);
        const slow = !heights && slowZones.some((zone) => Math.hypot(x - zone.x, z - zone.z) < 8);
        car.distance += car.speed * (slow ? 0.3 : 1) * car.direction * delta;
        if (car.distance < 0) car.distance += route.length;
        if (car.distance > route.length) car.distance -= route.length;
      });
      carMesh.instanceMatrix.needsUpdate = true;
    };
    updateCars(0);

    // Depth of field ----------------------------------------------------------
    const sceneTarget = track(new THREE.WebGLRenderTarget(1, 1, { samples: 4, depthTexture: new THREE.DepthTexture(1, 1), colorSpace: THREE.SRGBColorSpace }));
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
        uFocusStart: { value: 82 },
        uFocusEnd: { value: 150 },
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
      renderer.info.reset();
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
    const publishInfo = () => {
      host.dataset.renderInfo = JSON.stringify({
        calls: renderer.info.render.calls,
        triangles: renderer.info.render.triangles,
        geometries: renderer.info.memory.geometries,
        textures: renderer.info.memory.textures,
        dof: dofEnabled,
        pixelRatio,
      });
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
    // Narrower windows (4:3, 5:4) see less of the city across: pull the camera
    // back a little and shift it, so the pins stay between the copy and the card.
    const framedPosition = CAMERA_POSITION.clone();
    const framedTarget = CAMERA_TARGET.clone();
    const frame = () => {
      const narrow = THREE.MathUtils.clamp((1.6 - camera.aspect) / 0.27, 0, 1);
      framedTarget.set(CAMERA_TARGET.x + 1.5 * narrow, CAMERA_TARGET.y, CAMERA_TARGET.z);
      framedPosition.copy(CAMERA_POSITION).sub(CAMERA_TARGET).multiplyScalar(1 + 0.25 * narrow).add(framedTarget);
      camera.position.copy(framedPosition);
      camera.lookAt(framedTarget);
    };
    const resize = () => {
      const nextWidth = host.clientWidth;
      const nextHeight = host.clientHeight;
      if (!nextWidth || !nextHeight) return;
      width = nextWidth;
      height = nextHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      frame();
      applySize();
      render();
      publishInfo();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    resize();

    // Pointer parallax, activity, loop ------------------------------------------
    const pointer = new THREE.Vector2(0, 0);
    const pointerTarget = new THREE.Vector2(0, 0);
    let lastActivity = performance.now();
    let idle = false;
    const onPointerMove = (event: PointerEvent) => {
      pointerTarget.set((event.clientX / window.innerWidth) * 2 - 1, (event.clientY / window.innerHeight) * 2 - 1);
      noteActivity();
    };

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
        Math.sin(elapsed * 0.09) * 0.9 + pointer.x * 1.2,
        Math.sin(elapsed * 0.06) * 0.3 - pointer.y * 0.5,
        Math.cos(elapsed * 0.07) * 0.6,
      );
      camera.position.copy(framedPosition).add(cameraOffset);
      camera.lookAt(framedTarget.x + pointer.x * 0.8, framedTarget.y, framedTarget.z);

      updateCars(delta);
      placePins(elapsed);
      routeMaterial.uniforms.uTime.value = elapsed;
      trailsAhead.uniforms.uTime.value = elapsed;
      trailsBack.uniforms.uTime.value = elapsed;

      render();
      markReady();
      if (sampledFrames === 30) publishInfo();

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
      publishInfo();
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
