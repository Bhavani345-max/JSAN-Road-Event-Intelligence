// Renders the stills of the sign-in city (public/login/rei-city-<width>.webp)
// from the live WebGL scene in features/auth/RoadScene.tsx, so phones,
// tablets and browsers without WebGL show the same city.
//
// Needs the app running (npm run dev) and a local Chrome or Edge.
// Usage: node scripts/render-login-backdrop.mjs [url]
//   CHROME_PATH   browser executable (default: Chrome on Windows)
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const url = process.argv[2] ?? "http://localhost:3000/login";
const chromePath = process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const outDir = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public", "login");
const sizes = [
  [1920, 1080],
  [1280, 720],
];
const port = 9480;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Hide everything but the 3D scene (header, copy, card, veil, still, and the
// Next.js development badge).
const hideInterface = `(() => {
  const style = document.createElement("style");
  style.textContent = "header, .login-veil, .login-backdrop, main > div.z-10, nextjs-portal { visibility: hidden !important; }";
  document.head.appendChild(style);
})()`;

async function render(width, height) {
  const profile = mkdtempSync(path.join(tmpdir(), "rei-backdrop-"));
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--hide-scrollbars",
    `--user-data-dir=${profile}`,
    `--remote-debugging-port=${port}`,
    `--window-size=${width},${height}`,
    "about:blank",
  ], { stdio: "ignore" });
  try {
    let target;
    for (let attempt = 0; attempt < 50 && !target; attempt += 1) {
      await sleep(200);
      try {
        target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((entry) => entry.type === "page");
      } catch {
        /* not ready yet */
      }
    }
    if (!target) throw new Error("The browser did not start.");
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.onopen = resolve;
      socket.onerror = reject;
    });
    let nextId = 1;
    const pending = new Map();
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      pending.get(message.id)?.(message);
      pending.delete(message.id);
    };
    const send = (method, params = {}) =>
      new Promise((resolve) => {
        const id = nextId++;
        pending.set(id, resolve);
        socket.send(JSON.stringify({ id, method, params }));
      });

    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    // Reduced motion: the scene draws one still frame, with depth of field.
    await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
    await send("Page.enable");
    await send("Page.navigate", { url });
    await sleep(15000);
    await send("Runtime.evaluate", { expression: hideInterface });
    await sleep(500);
    const shot = await send("Page.captureScreenshot", { format: "webp", quality: 84 });
    if (!shot.result?.data) throw new Error(`No screenshot: ${JSON.stringify(shot.error ?? shot)}`);
    const file = path.join(outDir, `rei-city-${width}.webp`);
    writeFileSync(file, Buffer.from(shot.result.data, "base64"));
    console.log(`saved ${path.relative(process.cwd(), file)}`);
    socket.close();
  } finally {
    chrome.kill();
    await sleep(800);
    rmSync(profile, { recursive: true, force: true, maxRetries: 3 });
  }
}

mkdirSync(outDir, { recursive: true });
for (const [width, height] of sizes) await render(width, height);
