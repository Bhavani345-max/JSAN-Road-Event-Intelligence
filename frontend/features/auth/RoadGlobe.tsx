"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

type City = { latitude: number; longitude: number };

const cities: City[] = [
  { latitude: 40.7, longitude: -74 },
  { latitude: 51.5, longitude: -0.1 },
  { latitude: 60.2, longitude: 24.9 },
  { latitude: 48.9, longitude: 2.3 },
  { latitude: 19.1, longitude: 72.9 },
  { latitude: 12.9, longitude: 77.6 },
  { latitude: 43.7, longitude: -79.4 },
];

function pointOnGlobe(city: City, radius: number): THREE.Vector3 {
  const latitude = THREE.MathUtils.degToRad(city.latitude);
  const longitude = THREE.MathUtils.degToRad(city.longitude);
  return new THREE.Vector3(
    -radius * Math.cos(latitude) * Math.cos(longitude),
    radius * Math.sin(latitude),
    radius * Math.cos(latitude) * Math.sin(longitude),
  );
}

function addGraticule(globe: THREE.Group, radius: number) {
  const material = new THREE.LineBasicMaterial({
    color: 0x83d9e7,
    transparent: true,
    opacity: 0.13,
    depthWrite: false,
  });

  for (let latitude = -75; latitude <= 75; latitude += 15) {
    const points: THREE.Vector3[] = [];
    for (let longitude = -180; longitude <= 180; longitude += 4) {
      points.push(pointOnGlobe({ latitude, longitude }, radius));
    }
    const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), material);
    globe.add(line);
  }

  for (let longitude = -180; longitude < 180; longitude += 15) {
    const points: THREE.Vector3[] = [];
    for (let latitude = -90; latitude <= 90; latitude += 4) {
      points.push(pointOnGlobe({ latitude, longitude }, radius));
    }
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
    globe.add(line);
  }
}

export default function RoadGlobe() {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || window.matchMedia("(max-width: 1023px)").matches) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "low-power",
      });
    } catch {
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 40);
    camera.position.set(0, 0, 8.2);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);

    const globe = new THREE.Group();
    globe.rotation.x = -0.16;
    globe.rotation.y = -0.42;
    scene.add(globe);
    scene.add(new THREE.AmbientLight(0x8dddeb, 1.8));

    const keyLight = new THREE.DirectionalLight(0x67e8f9, 3.1);
    keyLight.position.set(-3, 4, 6);
    scene.add(keyLight);

    const radius = 2.23;
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 64, 48),
      new THREE.MeshStandardMaterial({
        color: 0x0c2c3a,
        metalness: 0.36,
        roughness: 0.48,
        transparent: true,
        opacity: 0.92,
      }),
    );
    globe.add(sphere);

    const atmosphere = new THREE.Mesh(
      new THREE.SphereGeometry(radius * 1.045, 48, 32),
      new THREE.MeshBasicMaterial({
        color: 0x22d3ee,
        transparent: true,
        opacity: 0.075,
        side: THREE.BackSide,
        depthWrite: false,
      }),
    );
    globe.add(atmosphere);
    addGraticule(globe, radius * 1.002);

    const points: number[] = [];
    const pointCount = 520;
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    for (let index = 0; index < pointCount; index += 1) {
      const y = 1 - (index / (pointCount - 1)) * 2;
      const radialDistance = Math.sqrt(1 - y * y);
      const angle = goldenAngle * index;
      points.push(
        Math.cos(angle) * radialDistance * radius * 1.006,
        y * radius * 1.006,
        Math.sin(angle) * radialDistance * radius * 1.006,
      );
    }
    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    globe.add(new THREE.Points(
      pointGeometry,
      new THREE.PointsMaterial({
        color: 0xa5f3fc,
        size: 0.022,
        transparent: true,
        opacity: 0.66,
        sizeAttenuation: true,
        depthWrite: false,
      }),
    ));

    const routeMaterials: THREE.LineDashedMaterial[] = [];
    const nodeGroups: THREE.Group[] = [];
    const nodeMaterial = new THREE.MeshBasicMaterial({ color: 0x8bf0dc });
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0x34d399,
      transparent: true,
      opacity: 0.24,
      depthWrite: false,
    });

    for (let index = 0; index < cities.length; index += 1) {
      const start = pointOnGlobe(cities[index], radius * 1.012);
      const node = new THREE.Group();
      node.position.copy(start);
      const normal = start.clone().normalize();
      node.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
      node.add(new THREE.Mesh(new THREE.SphereGeometry(0.042, 14, 12), nodeMaterial));
      node.add(new THREE.Mesh(new THREE.CircleGeometry(0.105, 24), glowMaterial));
      globe.add(node);
      nodeGroups.push(node);

      if (index === 0) continue;
      const destination = pointOnGlobe(cities[index], radius * 1.012);
      const previous = pointOnGlobe(cities[index - 1], radius * 1.012);
      const control = previous.clone().add(destination).normalize().multiplyScalar(radius * 1.38);
      control.y += 0.12;
      const curve = new THREE.QuadraticBezierCurve3(previous, control, destination);
      const route = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(100)),
        new THREE.LineDashedMaterial({
          color: index % 2 === 0 ? 0x5eead4 : 0x67e8f9,
          dashSize: 0.075,
          gapSize: 0.065,
          transparent: true,
          opacity: 0.78,
          depthWrite: false,
        }),
      );
      route.computeLineDistances();
      globe.add(route);
      routeMaterials.push(route.material as THREE.LineDashedMaterial);
    }

    const orbit = new THREE.Mesh(
      new THREE.TorusGeometry(radius * 1.16, 0.008, 6, 180),
      new THREE.MeshBasicMaterial({
        color: 0x67e8f9,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      }),
    );
    orbit.rotation.set(0.9, 0.16, -0.34);
    globe.add(orbit);

    const resize = () => {
      const width = host.clientWidth;
      const height = host.clientHeight;
      if (!width || !height) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      renderer.render(scene, camera);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(host);
    resize();

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const clock = new THREE.Clock();
    let frameId = 0;
    let isVisible = true;
    const renderFrame = () => {
      frameId = window.requestAnimationFrame(renderFrame);
      if (!isVisible || document.hidden || reducedMotion) return;
      const elapsed = clock.getDelta();
      globe.rotation.y += elapsed * 0.055;
      routeMaterials.forEach((material, index) => {
        material.opacity = 0.56 + (Math.sin(clock.elapsedTime * 1.35 + index * 0.7) + 1) * 0.11;
      });
      nodeGroups.forEach((node, index) => {
        const pulse = 1 + Math.sin(clock.elapsedTime * 2.2 + index * 0.82) * 0.12;
        node.scale.setScalar(pulse);
      });
      renderer.render(scene, camera);
    };
    if (!reducedMotion) renderFrame();

    const visibilityObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
      if (isVisible) renderer.render(scene, camera);
    });
    visibilityObserver.observe(host);

    return () => {
      window.cancelAnimationFrame(frameId);
      visibilityObserver.disconnect();
      resizeObserver.disconnect();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div ref={hostRef} aria-hidden="true" className="h-full w-full" />;
}
