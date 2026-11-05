// Renders the link-preview image (app/opengraph-image.jpg): the picture chat
// apps and social sites show when someone shares a link to REI.
//
// It is the sign-in city still (public/login/rei-city-1920.webp) with a white
// card holding the JSAN mark, the name and the sign-in headline. The card sits
// in the middle because small previews (Outlook, Teams, WhatsApp) crop the
// image to a square from its centre; the event pins stay visible to its right.
// JPEG, kept small: some apps skip preview images over a few hundred kB.
//
// Usage: node scripts/render-share-image.mjs
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.join(root, "public", "login", "rei-city-1920.webp");
const output = path.join(root, "app", "opengraph-image.jpg");

const W = 1200;
const H = 630;

// Sign-in page colours (features/auth/loginTheme.ts) and the JSAN mark's blue.
const navy = "#0B1F3A";
const accent = "#1667D6";
const body = "#475569";
const subtitle = "#5F6E80";
const divider = "#C5D2E1";
const markBlue = "#00558C";

// The part of the 1920x1080 still to show: the left of the city, so the four
// event pins land to the right of the card.
const crop = { left: 0, top: 330, width: 1127, height: 592 };

const card = { x: 290, y: 100, w: 560, h: 430, r: 28 };
const cx = card.x + card.w / 2;
const font = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif";

// The JSAN mark (public/jsan-mark.png) traced as two L shapes, 67 units square.
const markSize = 108;
const mark = `
  <svg x="${cx - markSize / 2}" y="${card.y + 34}" width="${markSize}" height="${markSize}" viewBox="13 21 67 67">
    <path fill="${markBlue}" d="M13 21H80V36H28V88H13Z M66 50H80V88H42V73H66Z" />
  </svg>`;

const overlay = `
<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
  <defs>
    <filter id="lift" x="-20%" y="-20%" width="140%" height="150%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="18" />
      <feOffset dy="10" result="blur" />
      <feComponentTransfer><feFuncA type="linear" slope="0.22" /></feComponentTransfer>
      <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
  </defs>
  <rect x="${card.x}" y="${card.y}" width="${card.w}" height="${card.h}" rx="${card.r}"
        fill="#FFFFFF" stroke="${divider}" stroke-width="1.5" filter="url(#lift)" />
  ${mark}
  <text x="${cx}" y="${card.y + 214}" text-anchor="middle" font-family="${font}" font-size="64"
        font-weight="700" letter-spacing="-1" fill="${navy}">JSAN</text>
  <text x="${cx}" y="${card.y + 254}" text-anchor="middle" font-family="${font}" font-size="19"
        font-weight="600" letter-spacing="3.8" fill="${subtitle}">ROAD EVENT INTELLIGENCE</text>
  <line x1="${cx - 150}" y1="${card.y + 290}" x2="${cx + 150}" y2="${card.y + 290}" stroke="${divider}" stroke-width="1.5" />
  <text x="${cx}" y="${card.y + 344}" text-anchor="middle" font-family="${font}" font-size="31"
        font-weight="700" letter-spacing="-0.5" fill="${navy}">See what’s <tspan fill="${accent}">changing</tspan> on the road.</text>
  <text x="${cx}" y="${card.y + 385}" text-anchor="middle" font-family="${font}" font-size="18"
        fill="${body}">Official feeds and local news, on one map</text>
</svg>`;

const city = await sharp(source).extract(crop).resize(W, H).toBuffer();
const info = await sharp(city)
  .composite([{ input: Buffer.from(overlay) }])
  .jpeg({ quality: 86, mozjpeg: true })
  .toFile(output);

console.log(`${path.relative(root, output)}: ${info.width}x${info.height}, ${Math.round(info.size / 1024)} kB`);
