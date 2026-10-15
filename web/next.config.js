/** @type {import('next').NextConfig} */
// Where the Next.js *server* (rewrite proxy) reaches the FastAPI backend.
// - Plain `npm run dev` / `npm run build && npm start` on a dev box: no
//   compose network, so this defaults to localhost:8000 (run uvicorn there).
// - docker-compose: the web container sets API_PROXY_TARGET=http://api:8000
//   (the "api" service name resolves on the compose network; localhost would
//   point at the web container itself).
// Accept a couple of historical/alternate names for this so whichever one
// docker-compose.yml ends up setting on the web service just works:
// API_PROXY_TARGET (what we asked for), API_ORIGIN (earlier convention), or
// a non-empty NEXT_PUBLIC_API_URL (docs-API-CONTRACT-for-frontend.md's
// convention -- read server-side here too, which works fine since Next.js
// still populates process.env with it even though the NEXT_PUBLIC_ prefix
// is really about client-bundle inlining).
const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET ||
  process.env.API_ORIGIN ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  // Standalone output so the Docker final stage can run `node server.js`
  // without needing the full node_modules tree copied in.
  output: "standalone",
  // We intentionally keep build-blocking lint off: this is a fast-moving
  // demo build and we want `npm run build` to fail only on real TS/build
  // errors, not on style nits.
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_PROXY_TARGET}/api/:path*` },
      { source: "/health", destination: `${API_PROXY_TARGET}/health` },
    ];
  },
};

module.exports = nextConfig;

// Build-time (client-inlined) env vars used by this app — Next.js inlines
// any NEXT_PUBLIC_* value present in the environment when `next build` runs,
// so Docker must pass them as build ARGs exported to ENV before the build
// step (see web/Dockerfile):
//   NEXT_PUBLIC_API_BASE       - base path prefix for client fetches, default "/api"
//   NEXT_PUBLIC_DEMO_API_KEY   - sandbox tz_test_... key for the pre-login
//                                branch/terminal picker on /login (see lib/api.ts
//                                and app/login/page.tsx for the graceful-fallback
//                                behavior when this is unset).
