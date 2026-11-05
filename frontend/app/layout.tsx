import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
// Country flags (MIT), served with the console: the header's country choice.
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import { APPEARANCE_SCRIPT } from "@/features/theme/appearanceScript";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteName = "JSAN Road Event Intelligence";
const siteDescription =
  "REI collects road events from official feeds, detects them in local news and places each one on an interactive map.";

export const metadata: Metadata = {
  // The public address: link previews need full URLs, and without it Next.js
  // would point the preview image at localhost.
  metadataBase: new URL("https://jsan-rei.up.railway.app"),
  title: siteName,
  description: siteDescription,
  // The link preview chat apps and social sites show. Its image is
  // app/opengraph-image.jpg (made by scripts/render-share-image.mjs).
  openGraph: {
    type: "website",
    siteName,
    title: siteName,
    description: siteDescription,
  },
  twitter: {
    card: "summary_large_image",
    title: siteName,
    description: siteDescription,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // data-theme is set by the script below before the first paint (a saved
    // dark appearance), so the server's markup differs from it on purpose.
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: APPEARANCE_SCRIPT }} />
      </head>
      <body className="h-full font-sans">{children}</body>
    </html>
  );
}
