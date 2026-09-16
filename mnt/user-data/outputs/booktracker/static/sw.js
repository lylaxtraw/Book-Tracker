/* Keeps the app shell on the phone so it opens instantly and survives a dead
   signal. API calls always go to the network — a stale library is worse than an
   honest error. Bump CACHE when you change anything in /static. */

const CACHE = "library-v1";

const SHELL = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/manifest.webmanifest",
  "/static/icons/icon-192.png",
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;   // covers, fonts: let them through
  if (url.pathname.startsWith("/api/")) return;      // never cache the library itself

  event.respondWith(
    caches.match(request).then(hit => {
      const fresh = fetch(request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then(cache => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => hit);
      return hit || fresh;
    })
  );
});
