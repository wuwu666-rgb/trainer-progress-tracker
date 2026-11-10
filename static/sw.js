// OneTrainer service worker: keeps the record-workout page usable without a connection.
const VERSION = "v1";
const STATIC_CACHE = `onetrainer-static-${VERSION}`;
const PAGE_CACHE = `onetrainer-pages-${VERSION}`;
const OFFLINE_URL = "/static/offline.html";
const PRECACHE = [
  OFFLINE_URL,
  "/static/style.css",
  "/static/workout.js",
  "/static/offline.js",
  "/static/repbook.webmanifest",
  "/static/icons/repbook-192.png",
  "/static/icons/repbook-180.png",
];
const RECORD_PAGE = /^\/workouts\/\d+\/record$/;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== STATIC_CACHE && key !== PAGE_CACHE).map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    // Only keep real pages: a redirect to login must not replace a good copy.
    if (response.ok && !response.redirected) await cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request, { ignoreSearch: cacheName === PAGE_CACHE });
    if (cached) return cached;
    throw error;
  }
}

async function offlineFallback() {
  const cache = await caches.open(STATIC_CACHE);
  return (await cache.match(OFFLINE_URL)) ||
    new Response("You are offline.", { status: 503, headers: { "Content-Type": "text/plain" } });
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Signing out also forgets cached workout pages (shared phones).
  if (request.method === "POST" && url.pathname === "/logout") {
    event.respondWith(fetch(request).finally(() => caches.delete(PAGE_CACHE)));
    return;
  }

  // A save submitted just as the connection drops: the entries stay in the
  // browser's local draft, so show a calm message instead of an error page.
  if (request.method === "POST" && RECORD_PAGE.test(url.pathname)) {
    event.respondWith(fetch(request).catch(offlineFallback));
    return;
  }

  if (request.method !== "GET") return;

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(networkFirst(request, STATIC_CACHE));
  } else if (request.mode === "navigate" && RECORD_PAGE.test(url.pathname)) {
    event.respondWith(networkFirst(request, PAGE_CACHE).catch(offlineFallback));
  } else if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(offlineFallback));
  }
});
