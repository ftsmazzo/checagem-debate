const CACHE = "mentirometro-ouvir-1";
const SHELL = [
  "/pwa",
  "/static/pwa.css",
  "/static/pwa.js",
  "/static/card.js",
  "/static/logo-ie-icon.png",
  "/static/logo-ie-mark.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch.png",
  "/static/fonts/montserrat-500.woff2",
  "/static/fonts/montserrat-700.woff2",
  "/static/fonts/montserrat-800.woff2",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok && SHELL.includes(url.pathname)) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
