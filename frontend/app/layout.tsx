import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
// Country flags (MIT), served with the console: the header's country choice.
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JSAN Road Event Intelligence — Hyderabad PoC",
  description: "Road Event Intelligence proof of concept: road events for Hyderabad from live sources on an interactive map.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full font-sans">{children}</body>
    </html>
  );
}
