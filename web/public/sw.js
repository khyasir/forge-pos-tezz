// Minimal hand-rolled service worker so the PWA still opens offline.
// It never caches /api/* -- offline data lives in IndexedDB (lib/db.ts).
//
// Strategy (v2):
//  - Pages and Next.js RSC payloads: NETWORK FIRST, cache only as an offline
//    fallback. v1 served these cache-first, so after `git pull` + rebuild the
//    browser kept running the OLD app build until a second reload.
//  - /_next/static/* (content-hashed, immutable): cache first.
// Bumping CACHE_NAME makes the activate step delete the old v1 cache.
const CACHE_NAME = "tezz-pos-shell-v2";
const APP_SHELL = ["/login", "/pos", "/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const stale = (await caches.keys()).filter((k) => k !== CACHE_NAME);
      await Promise.all(stale.map((k) => caches.delete(k)));
      await self.clients.claim();
      // Upgrading from an older worker: open tabs are still running the old
      // build it served from cache, and the old page code cannot reload
      // itself. Navigate them once so they pick up the new build.
      if (stale.length) {
        const wins = await self.clients.matchAll({ type: "window" });
        await Promise.all(wins.map((w) => w.navigate(w.url).catch(() => undefined)));
      }
    })()
  );
});

function putInCache(req, res) {
  if (res && res.ok) {
    const copy = res.clone();
    caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
  }
  return res;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/health")) return;

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(caches.match(req).then((cached) => cached || fetch(req).then((res) => putInCache(req, res))));
    return;
  }

  // Everything else (navigations, RSC payloads, manifest, icons): network first.
  event.respondWith(
    (async () => {
      try {
        return putInCache(req, await fetch(req));
      } catch (err) {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (req.mode === "navigate") {
          const shell = await caches.match(url.pathname.startsWith("/login") ? "/login" : "/pos");
          if (shell) return shell;
        }
        return Response.error();
      }
    })()
  );
});
