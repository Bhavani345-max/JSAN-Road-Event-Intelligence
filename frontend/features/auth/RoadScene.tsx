"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { createRng, generateRoadNetwork, polylineLength, type Point, type Polyline } from "./roadNetwork";

/**
 * Decorative night-time "digital twin" of a city road network: glowing
 * arterials and streets on a dark ground with depth fog, light particles
 * flowing along the roads, amber closure beacons and a teal detour route.
 *
 * Purely procedural (no textures, fonts or models are downloaded) and purely
 * illustrative: it does not show any real place or any product data.
 */

type RoadSceneProps = {
  /** Called once the first frame has been drawn. */
  onReady?: () => void;
  /** Called when WebGL cannot be used; the page then keeps its CSS backdrop. */
  onUnavailable?: () => void;
};

const BACKGROUND = 0x050e18;
const GROUND_HEIGHT = 0;
const ROAD_LIFT = 0.03;


const palette = {
  street: "rgba(62, 128, 176, 0.34)",
  blockFill: "rgba(32, 88, 136, 1)",
  avenueGlow: "rgba(56, 189, 248, 0.42)",
  avenueCore: "rgba(190, 236, 255, 0.88)",
  avenueLine: 0x67c9f3,
  streetLine: 0x285a80,
  trafficCool: new THREE.Color(0x8be4ff),
  trafficWarm: new THREE.Color(0xc8eaff),
  trafficBrand: new THREE.Color(0x5fb3e6),
  amber: new THREE.Color(0x76d7f5),
  amberDeep: new THREE.Color(0x278fca),
  teal: new THREE.Color(0x2dd4bf),
  cyan: new THREE.Color(0x67e8f9),
};

function worldToTexture(point: Point, size: number, pixels: number) {
  return {
    x: ((point.x + size / 2) / size) * pixels,
    y: ((point.z + size / 2) / size) * pixels,
  };
}

/** Paints the ground: faint block footprints, minor streets and glowing avenues. */
function paintGroundTexture(size: number, arterials: Polyline[], streets: [Point, Point][], blocks: ReturnType<typeof generateRoadNetwork>["blocks"]): THREE.CanvasTexture | null {
  const pixels = 1024;
  const canvas = document.createElement("canvas");
  canvas.width = pixels;
  canvas.height = pixels;
  const context = canvas.getContext("2d");
  if (!context) return null;
  const scale = pixels / size;

  context.fillStyle = "#06111c";
  context.fillRect(0, 0, pixels, pixels);

  context.fillStyle = palette.blockFill;
  for (const block of blocks) {
    if (block.density <= 0.01) continue;
    context.globalAlpha = Math.min(0.2, block.density * 0.22);
    const origin = worldToTexture(block, size, pixels);
    context.fillRect(origin.x, origin.y, block.w * scale, block.d * scale);
  }
  context.globalAlpha = 1;

  context.strokeStyle = palette.street;
  context.lineWidth = 1;
  context.beginPath();
  for (const [from, to] of streets) {
    const a = worldToTexture(from, size, pixels);
    const b = worldToTexture(to, size, pixels);
    context.moveTo(a.x, a.y);
    context.lineTo(b.x, b.y);
  }
  context.stroke();

  const traceArterials = () => {
    context.beginPath();
    for (const line of arterials) {
      line.forEach((point, index) => {
        const p = worldToTexture(point, size, pixels);
        if (index === 0) context.moveTo(p.x, p.y);
        else context.lineTo(p.x, p.y);
      });
    }
  };

  context.lineCap = "round";
  context.lineJoin = "round";
  context.strokeStyle = palette.avenueGlow;
  context.lineWidth = 4.5;
  context.shadowColor = "rgba(56, 189, 248, 0.85)";
  context.shadowBlur = 10;
  traceArterials();
  context.stroke();

  context.shadowBlur = 0;
  context.strokeStyle = palette.avenueCore;
  context.lineWidth = 1.5;
  traceArterials();
  context.stroke();

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.needsUpdate = true;
  return texture;
}

/** Soft round sprite used for the traffic particles. */
function createSpriteTexture(): THREE.CanvasTexture | null {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (!context) return null;
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.25, "rgba(255,255,255,0.8)");
  gradient.addColorStop(0.6, "rgba(255,255,255,0.18)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/** Flat ribbon following a polyline, with flowing dashes in the shader. */
function createRibbon(line: Polyline, width: number, color: THREE.Color): THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial> {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  let travelled = 0;
  for (let index = 1; index < line.length; index += 1) {
    const from = line[index - 1];
    const to = line[index];
    const length = Math.hypot(to.x - from.x, to.z - from.z);
    const nx = (-(to.z - from.z) / length) * width;
    const nz = ((to.x - from.x) / length) * width;
    const base = positions.length / 3;
    positions.push(
      from.x + nx, ROAD_LIFT, from.z + nz,
      from.x - nx, ROAD_LIFT, from.z - nz,
      to.x + nx, ROAD_LIFT, to.z + nz,
      to.x - nx, ROAD_LIFT, to.z - nz,
    );
    uvs.push(travelled, 0, travelled, 1, travelled + length, 0, travelled + length, 1);
    indices.push(base, base + 1, base + 2, base + 1, base + 3, base + 2);
    travelled += length;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  const material = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: color }, uTime: { value: 0 } },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uTime;
      varying vec2 vUv;
      void main() {
        float edge = pow(1.0 - abs(vUv.y * 2.0 - 1.0), 1.3);
        float flow = fract(vUv.x * 0.32 - uTime * 0.55);
        float dash = smoothstep(0.0, 0.3, flow) * (1.0 - smoothstep(0.5, 1.0, flow));
        float alpha = edge * (0.34 + 0.66 * dash);
        gl_FragColor = vec4(uColor * (0.85 + 0.55 * dash), alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  return new THREE.Mesh(geometry, material);
}

function createBeamMaterial(color: THREE.Color, strength: number): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: color }, uTime: { value: 0 }, uStrength: { value: strength } },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uStrength;
      varying vec2 vUv;
      void main() {
        float fade = pow(1.0 - vUv.y, 2.2);
        float shimmer = 0.88 + 0.12 * sin(uTime * 2.4 + vUv.y * 9.0);
        gl_FragColor = vec4(uColor, fade * uStrength * shimmer);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
}

type Pulse = { mesh: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>; phase: number; speed: number; reach: number };

type Traveller = { line: number; distance: number; speed: number; length: number };

export default function RoadScene({ onReady, onUnavailable }: RoadSceneProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onReady, onUnavailable });

  useEffect(() => {
    callbacks.current = { onReady, onUnavailable };
  }, [onReady, onUnavailable]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    // Probe for WebGL first so an unsupported browser gets the CSS backdrop
    // without three.js logging context-creation errors.
    const probe = document.createElement("canvas");
    const probeContext = probe.getContext("webgl2") ?? probe.getContext("webgl");
    if (!probeContext) {
      callbacks.current.onUnavailable?.();
      return;
    }
    probeContext.getExtension("WEBGL_lose_context")?.loseContext();

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "low-power",
        stencil: false,
      });
    } catch {
      callbacks.current.onUnavailable?.();
      return;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
    renderer.setPixelRatio(pixelRatio);
    renderer.setClearColor(BACKGROUND, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    const canvas = renderer.domElement;
    canvas.style.position = "absolute";
    canvas.style.inset = "0";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.opacity = "0";
    canvas.style.transition = reducedMotion ? "none" : "opacity 1400ms ease";
    host.appendChild(canvas);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(BACKGROUND);
    scene.fog = new THREE.FogExp2(BACKGROUND, 0.0118);

    const camera = new THREE.PerspectiveCamera(46, 1, 0.5, 260);
    const cameraBase = new THREE.Vector3(2, 21, 30);
    const lookTarget = new THREE.Vector3(3, 0, -26);
    camera.position.copy(cameraBase);
    camera.lookAt(lookTarget);

    const network = generateRoadNetwork(7, 160);
    const disposables: { dispose: () => void }[] = [];
    const track = <T extends { dispose: () => void }>(item: T): T => {
      disposables.push(item);
      return item;
    };

    // Ground --------------------------------------------------------------
    const groundTexture = paintGroundTexture(network.size, network.arterials, network.streets, network.blocks);
    if (groundTexture) track(groundTexture);
    const groundMaterial = track(new THREE.MeshBasicMaterial({ map: groundTexture, color: 0xffffff }));
    const ground = new THREE.Mesh(track(new THREE.PlaneGeometry(network.size, network.size)), groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = GROUND_HEIGHT;
    scene.add(ground);

    // Crisp line cores on top of the painted roads --------------------------
    const streetPositions: number[] = [];
    for (const [from, to] of network.streets) {
      streetPositions.push(from.x, ROAD_LIFT, from.z, to.x, ROAD_LIFT, to.z);
    }
    const streetGeometry = track(new THREE.BufferGeometry());
    streetGeometry.setAttribute("position", new THREE.Float32BufferAttribute(streetPositions, 3));
    scene.add(new THREE.LineSegments(streetGeometry, track(new THREE.LineBasicMaterial({
      color: palette.streetLine,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
    }))));

    const avenueMaterial = track(new THREE.LineBasicMaterial({
      color: palette.avenueLine,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
    }));
    for (const line of network.arterials) {
      const geometry = track(new THREE.BufferGeometry().setFromPoints(line.map((p) => new THREE.Vector3(p.x, ROAD_LIFT + 0.01, p.z))));
      scene.add(new THREE.Line(geometry, avenueMaterial));
    }

    // Traffic ---------------------------------------------------------------
    const random = createRng(23);
    const travellers: Traveller[] = [];
    const trafficCount = 420;
    const lineLengths = network.arterials.map(polylineLength);
    const totalLength = lineLengths.reduce((sum, value) => sum + value, 0);
    for (let index = 0; index < trafficCount; index += 1) {
      let pick = random() * totalLength;
      let line = 0;
      while (line < lineLengths.length - 1 && pick > lineLengths[line]) {
        pick -= lineLengths[line];
        line += 1;
      }
      const direction = random() < 0.5 ? -1 : 1;
      travellers.push({ line, distance: pick, speed: direction * (2.2 + random() * 3.4), length: lineLengths[line] });
    }
    const trafficPositions = new Float32Array(trafficCount * 3);
    const trafficColors = new Float32Array(trafficCount * 3);
    travellers.forEach((_, index) => {
      const roll = random();
      const color = roll < 0.55 ? palette.trafficCool : roll < 0.85 ? palette.trafficWarm : palette.trafficBrand;
      trafficColors.set([color.r, color.g, color.b], index * 3);
    });
    const trafficGeometry = track(new THREE.BufferGeometry());
    trafficGeometry.setAttribute("position", new THREE.BufferAttribute(trafficPositions, 3));
    trafficGeometry.setAttribute("color", new THREE.BufferAttribute(trafficColors, 3));
    const spriteTexture = createSpriteTexture();
    if (spriteTexture) track(spriteTexture);
    const trafficMaterial = track(new THREE.PointsMaterial({
      size: 0.85,
      map: spriteTexture,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
    }));
    const traffic = new THREE.Points(trafficGeometry, trafficMaterial);
    traffic.position.y = ROAD_LIFT + 0.08;
    traffic.frustumCulled = false;
    scene.add(traffic);

    // Precomputed cumulative distances for quick lookups along each arterial.
    const cumulative = network.arterials.map((line) => {
      const distances = [0];
      for (let index = 1; index < line.length; index += 1) {
        distances.push(distances[index - 1] + Math.hypot(line[index].x - line[index - 1].x, line[index].z - line[index - 1].z));
      }
      return distances;
    });
    const placeTraveller = (traveller: Traveller, target: Float32Array, offset: number) => {
      const line = network.arterials[traveller.line];
      const distances = cumulative[traveller.line];
      let low = 1;
      let high = distances.length - 1;
      while (low < high) {
        const mid = (low + high) >> 1;
        if (distances[mid] < traveller.distance) low = mid + 1;
        else high = mid;
      }
      const from = line[low - 1];
      const to = line[low];
      const span = distances[low] - distances[low - 1] || 1;
      const t = (traveller.distance - distances[low - 1]) / span;
      target[offset] = from.x + (to.x - from.x) * t;
      target[offset + 1] = 0;
      target[offset + 2] = from.z + (to.z - from.z) * t;
    };
    const updateTraffic = (delta: number) => {
      travellers.forEach((traveller, index) => {
        traveller.distance += traveller.speed * delta;
        if (traveller.distance < 0) traveller.distance += traveller.length;
        if (traveller.distance > traveller.length) traveller.distance -= traveller.length;
        placeTraveller(traveller, trafficPositions, index * 3);
      });
      trafficGeometry.attributes.position.needsUpdate = true;
    };
    updateTraffic(0);

    // Road events -----------------------------------------------------------
    const pulses: Pulse[] = [];
    const beamMaterials: THREE.ShaderMaterial[] = [];
    const ringGeometry = track(new THREE.RingGeometry(0.72, 0.86, 56));
    const discGeometry = track(new THREE.CircleGeometry(0.34, 32));
    const haloGeometry = track(new THREE.CircleGeometry(1.5, 40));
    const beamGeometry = track(new THREE.CylinderGeometry(0.06, 0.3, 9, 14, 1, true));
    const smallRingGeometry = track(new THREE.RingGeometry(0.42, 0.5, 40));
    const smallDiscGeometry = track(new THREE.CircleGeometry(0.17, 24));
    const smallBeamGeometry = track(new THREE.CylinderGeometry(0.03, 0.09, 2.6, 10, 1, true));

    
network.closures.forEach((closure, index) => {
  const group = new THREE.Group();
  group.position.set(closure.x, ROAD_LIFT + 0.02, closure.z);
  scene.add(group);

  const halo = new THREE.Mesh(
    haloGeometry,
    track(
      new THREE.MeshBasicMaterial({
        color: palette.amberDeep,
        transparent: true,
        opacity: 0.09,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    )
  );
  halo.rotation.x = -Math.PI / 2;
  group.add(halo);

  const disc = new THREE.Mesh(
    discGeometry,
    track(
      new THREE.MeshBasicMaterial({
        color: palette.amber,
        toneMapped: false,
      })
    )
  );
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = 0.01;
  group.add(disc);

  const staticRing = new THREE.Mesh(
    ringGeometry,
    track(
      new THREE.MeshBasicMaterial({
        color: palette.amber,
        transparent: true,
        opacity: 0.48,
        depthWrite: false,
        side: THREE.DoubleSide,
      })
    )
  );
  staticRing.rotation.x = -Math.PI / 2;
  group.add(staticRing);

  for (let pulseIndex = 0; pulseIndex < 2; pulseIndex += 1) {
    const pulse = new THREE.Mesh(
      ringGeometry,
      track(
        new THREE.MeshBasicMaterial({
          color: palette.amber,
          transparent: true,
          opacity: 0,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
          side: THREE.DoubleSide,
        })
      )
    );
    pulse.rotation.x = -Math.PI / 2;
    pulse.position.y = 0.015;
    group.add(pulse);

    pulses.push({
      mesh: pulse,
      phase: pulseIndex * 0.5 + index * 0.23,
      speed: 0.34,
      reach: 3.6,
    });
  }

  const beamMaterial = track(
    createBeamMaterial(palette.amber, index === 0 ? 0.6 : 0.42)
  );
  beamMaterials.push(beamMaterial);

  const beam = new THREE.Mesh(beamGeometry, beamMaterial);
  beam.position.y = 9 / 2;
  group.add(beam);
});

    const detour = createRibbon(network.detour, 0.34, palette.teal);
    track(detour.geometry);
    track(detour.material);
    scene.add(detour);
    const ribbonMaterials = [detour.material];

    network.markers.forEach((marker, index) => {
      const group = new THREE.Group();
      group.position.set(marker.x, ROAD_LIFT + 0.02, marker.z);
      scene.add(group);
      const disc = new THREE.Mesh(smallDiscGeometry, track(new THREE.MeshBasicMaterial({ color: palette.cyan, toneMapped: false })));
      disc.rotation.x = -Math.PI / 2;
      group.add(disc);
      const ring = new THREE.Mesh(smallRingGeometry, track(new THREE.MeshBasicMaterial({
        color: palette.cyan,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
      })));
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.01;
      group.add(ring);
      pulses.push({ mesh: ring, phase: index * 0.37, speed: 0.28, reach: 2.4 });
      const beamMaterial = track(createBeamMaterial(palette.cyan, 0.3));
      beamMaterials.push(beamMaterial);
      const beam = new THREE.Mesh(smallBeamGeometry, beamMaterial);
      beam.position.y = 2.6 / 2;
      group.add(beam);
    });

    // Post-processing (bloom) -----------------------------------------------
    const composer = new EffectComposer(renderer);
    const renderPass = new RenderPass(scene, camera);
    const bloomPass = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.55, 0.5, 0.7);
    const outputPass = new OutputPass();
    composer.addPass(renderPass);
    composer.addPass(bloomPass);
    composer.addPass(outputPass);
    let bloomEnabled = true;

    const render = () => {
      if (bloomEnabled) composer.render();
      else renderer.render(scene, camera);
    };

    // Sizing ----------------------------------------------------------------
    let width = 0;
    let height = 0;
    const resize = () => {
      const nextWidth = host.clientWidth;
      const nextHeight = host.clientHeight;
      if (!nextWidth || !nextHeight) return;
      width = nextWidth;
      height = nextHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      composer.setSize(width, height);
      bloomPass.setSize(Math.ceil(width / 2), Math.ceil(height / 2));
      render();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    resize();

    // Pointer parallax --------------------------------------------------------
    const pointer = new THREE.Vector2(0, 0);
    const pointerTarget = new THREE.Vector2(0, 0);
    const onPointerMove = (event: PointerEvent) => {
      pointerTarget.set((event.clientX / window.innerWidth) * 2 - 1, (event.clientY / window.innerHeight) * 2 - 1);
    };
    if (!reducedMotion) window.addEventListener("pointermove", onPointerMove, { passive: true });

    // Animation loop ----------------------------------------------------------
    const clock = new THREE.Clock(false);
    let frameId = 0;
    let running = false;
    let intersecting = true;
    let ready = false;
    let sampledFrames = 0;
    let sampledTime = 0;
    const cameraOffset = new THREE.Vector3();

    const markReady = () => {
      if (ready) return;
      ready = true;
      canvas.style.opacity = "1";
      callbacks.current.onReady?.();
    };

    const tick = () => {
      frameId = window.requestAnimationFrame(tick);
      const delta = Math.min(clock.getDelta(), 0.05);
      const elapsed = clock.elapsedTime;

      pointer.lerp(pointerTarget, 0.04);
      cameraOffset.set(
        Math.sin(elapsed * 0.11) * 1.3 + pointer.x * 1.4,
        Math.sin(elapsed * 0.07) * 0.35 - pointer.y * 0.45,
        Math.cos(elapsed * 0.09) * 0.9,
      );
      camera.position.copy(cameraBase).add(cameraOffset);
      camera.lookAt(lookTarget.x + pointer.x * 1.2, lookTarget.y, lookTarget.z);

      updateTraffic(delta);
      for (const pulse of pulses) {
        const phase = (elapsed * pulse.speed + pulse.phase) % 1;
        pulse.mesh.scale.setScalar(1 + phase * pulse.reach);
        pulse.mesh.material.opacity = Math.pow(1 - phase, 1.8) * 0.55;
      }
      for (const material of beamMaterials) material.uniforms.uTime.value = elapsed;
      for (const material of ribbonMaterials) material.uniforms.uTime.value = elapsed;

      render();
      markReady();

      // Adaptive quality: if the first seconds run slowly, drop bloom and
      // render at 1x so the page stays smooth on weak GPUs.
      if (bloomEnabled && sampledFrames < 90) {
        sampledFrames += 1;
        if (sampledFrames > 20) sampledTime += delta;
        if (sampledFrames === 90 && sampledTime / 70 > 0.034) {
          bloomEnabled = false;
          renderer.setPixelRatio(1);
          renderer.setSize(width, height, false);
        }
      }
    };

    const start = () => {
      if (running || reducedMotion) return;
      running = true;
      clock.start();
      tick();
    };
    const stop = () => {
      if (!running) return;
      running = false;
      clock.stop();
      window.cancelAnimationFrame(frameId);
    };
    const syncRunning = () => {
      if (intersecting && !document.hidden) start();
      else stop();
    };

    if (reducedMotion) {
      updateTraffic(0);
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
      intersectionObserver.disconnect();
      resizeObserver.disconnect();
      bloomPass.dispose();
      outputPass.dispose();
      renderPass.dispose();
      composer.dispose();
      for (const item of disposables) item.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    };
  }, []);

  return <div ref={hostRef} aria-hidden="true" className="absolute inset-0 overflow-hidden" />;
}
