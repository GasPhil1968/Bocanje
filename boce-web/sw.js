/* Boće na rivi - offline cache (cache-first). New deploy = new CACHE name. */
const CACHE = 'boce-fd617513e4';
const FILES = ["index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png", "boce-whatsapp-20261004.jpg"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => c.addAll(FILES.map(f => new Request(f, {cache: 'reload'}))))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k.startsWith('boce-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (req.mode === 'navigate') {            // "/", "/index.html", "/?x" -> the game page
    e.respondWith(caches.open(CACHE).then(c => c.match('index.html'))
      .then(r => r || fetch(req)).catch(() => fetch(req)));
    return;
  }
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(r => r || fetch(req)));
});
