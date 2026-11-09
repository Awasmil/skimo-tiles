// Service worker: que la pagina y sus recursos arranquen sin conexion.
// Los mapas (.pmtiles) NO pasan por aqui: la pagina los lee directamente de la cache "skimo-offline".
const RUNTIME = "skimo-runtime-v2";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith("skimo-shell") || (k.startsWith("skimo-runtime") && k !== RUNTIME)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url);
  if (url.pathname.endsWith(".pmtiles")) return;

  const sameOrigin = url.origin === self.location.origin;
  const isLib = url.hostname === "unpkg.com";
  if (!sameOrigin && !isLib) return;   // ortofoto, ICGC, Overpass... solo con red

  if (isLib) {
    // Librerias con version fija: primero cache
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(RUNTIME).then(c => c.put(req, copy)); }
      return res;
    })));
    return;
  }
  // Mismo origen: red primero (ver cambios al momento); sin red, lo guardado (cualquier cache)
  e.respondWith(fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(RUNTIME).then(c => c.put(req, copy)); }
    return res;
  }).catch(async () => (await caches.match(req, { ignoreSearch: true })) || Response.error()));
});
