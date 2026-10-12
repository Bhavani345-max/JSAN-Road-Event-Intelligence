import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root; otherwise a stray lockfile higher up the tree
  // (e.g. in the user's home directory) makes Next.js warn on every run.
  turbopack: { root: __dirname },

  // The browser calls same-origin /api/...; forward those to the REI API.
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiBaseUrl}/api/:path*` }];
  },
};

export default nextConfig;
