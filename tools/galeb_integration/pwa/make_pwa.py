"""Turn the Galeb nad Jadranom web build into an offline web app (iPad / iPhone home screen).

usage: python3 make_pwa.py <web build dir> <out dir>

Adds: static app icons + manifest.webmanifest, sw.js that precaches every file of the build
(versioned by a content hash, old caches are removed), and a small on-screen status
("Offline wird geladen … 45 %" -> "Offline bereit ✓") wired into the existing SW registration.
"""
import sys, os, shutil, hashlib, json
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out):
    sys.exit(f'{out} exists - choose a new output folder')
shutil.copytree(src, out)

# ------------------------------------------------------------------ icons
card = Image.open(os.path.join(out, 'assets/img/ui_card.webp')).convert('RGBA')
bird = Image.open(os.path.join(out, 'assets/img/galeb_glide.webp')).convert('RGBA')
for size, name in ((180, 'apple-touch-icon.png'), (192, 'icon-192.png'), (512, 'icon-512.png')):
    bg = card.resize((size, size), Image.LANCZOS)
    b = bird.copy(); b.thumbnail((int(size * 0.94), int(size * 0.94)), Image.LANCZOS)
    bg.alpha_composite(b, ((size - b.width) // 2, (size - b.height) // 2))
    bg.convert('RGB').save(os.path.join(out, name), optimize=True)    # iOS wants an opaque icon

manifest = {
    'name': 'Galeb nad Jadranom', 'short_name': 'Galeb', 'lang': 'hr',
    'start_url': './index.html', 'scope': './', 'display': 'standalone',
    'background_color': '#10303A', 'theme_color': '#10303A',
    'icons': [{'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
              {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
              {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]}
json.dump(manifest, open(os.path.join(out, 'manifest.webmanifest'), 'w'), indent=1, ensure_ascii=False)

# ------------------------------------------------------------------ index.html
p = os.path.join(out, 'index.html')
s = open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep('<meta name="theme-color" content="#10303A">',
    '<meta name="theme-color" content="#10303A">\n'
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">')
# the runtime icon would override the static one on iOS - keep the static file
rep("  const link=document.createElement('link');link.rel='apple-touch-icon';link.href=url;document.head.appendChild(link);",
    "  void url;   // statisches apple-touch-icon.png (Offline-App) hat Vorrang")
rep("""  if('serviceWorker' in navigator && location.protocol === 'https:')
    navigator.serviceWorker.register('sw.js').catch(()=>{});""",
    r"""  /* Offline-App: sw.js speichert das ganze Spiel; die Anzeige zeigt den Fortschritt */
  if('serviceWorker' in navigator && (location.protocol === 'https:' || /^(localhost|127\.0\.0\.1)$/.test(location.hostname))){
    const box = document.createElement('div');
    box.style.cssText = 'position:fixed;left:50%;bottom:calc(env(safe-area-inset-bottom,0px) + 14px);transform:translateX(-50%);' +
      'z-index:60;padding:8px 14px;border-radius:16px;background:rgba(16,48,58,.88);color:#F6F1E4;' +
      'font:600 13px/1.2 Georgia,serif;letter-spacing:.04em;pointer-events:none;opacity:0;transition:opacity .4s';
    document.body.appendChild(box);
    let shownDone = false, hideT = null;
    const show = (txt, ms) => { box.textContent = txt; box.style.opacity = '1';
      clearTimeout(hideT); if(ms) hideT = setTimeout(() => box.style.opacity = '0', ms); };
    const onStatus = d => {
      if(!d || d.type !== 'galeb-offline') return;
      if(d.done < d.total){
        show(L('Spremam za offline … ','Saving for offline … ','Offline wird geladen … ') + Math.floor(100 * d.done / d.total) + ' %');
      }else if(!shownDone){
        shownDone = true;
        let seen = null; try{ seen = localStorage.getItem('galeb_offline_ok'); }catch(e){}
        if(d.fresh || !seen) show(L('Spremno za offline ✓','Ready for offline ✓','Offline bereit ✓'), 4500);
        try{ localStorage.setItem('galeb_offline_ok', '1'); }catch(e){}
      }
    };
    navigator.serviceWorker.addEventListener('message', e => onStatus(e.data));
    navigator.serviceWorker.register('sw.js').then(reg => {
      const ask = () => { const w = reg.active || reg.waiting || reg.installing; if(w) w.postMessage({type:'status?'}); };
      ask(); navigator.serviceWorker.ready.then(ask);
    }).catch(()=>{});
  }""")
open(p, 'w', encoding='utf-8').write(s)

# ------------------------------------------------------------------ sw.js
files = []
for dp, dn, fn in os.walk(out):
    dn.sort()
    for f in sorted(fn):
        if f.startswith('.') or f == 'sw.js': continue
        files.append(os.path.relpath(os.path.join(dp, f), out).replace(os.sep, '/'))
h = hashlib.sha256()
for f in files:
    h.update(f.encode()); h.update(open(os.path.join(out, f), 'rb').read())
version = h.hexdigest()[:12]
sw = """/* Galeb nad Jadranom - offline service worker (generated by make_pwa.py) */
const CACHE = 'galeb-%s';
const FILES = ['./', %s];
let progress = {done: 0, total: FILES.length, fresh: false};

async function tell(msg){
  const all = await self.clients.matchAll({includeUncontrolled: true, type: 'window'});
  for(const c of all) c.postMessage(msg);
}
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    progress = {done: 0, total: FILES.length, fresh: true};
    let next = 0, last = 0;
    async function worker(){
      while(next < FILES.length){
        const url = FILES[next++];
        if(!(await cache.match(url))){
          const res = await fetch(new Request(url, {cache: 'reload'}));
          if(!res.ok) throw new Error(url + ' ' + res.status);
          await cache.put(url, res);
        }
        progress.done++;
        if(progress.done - last >= 8 || progress.done === FILES.length){
          last = progress.done; tell({type: 'galeb-offline', ...progress});
        }
      }
    }
    await Promise.all([worker(), worker(), worker(), worker(), worker(), worker()]);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for(const k of await caches.keys()) if(k.startsWith('galeb-') && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
    tell({type: 'galeb-offline', done: FILES.length, total: FILES.length, fresh: progress.fresh});
  })());
});
self.addEventListener('message', event => {
  if(event.data && event.data.type === 'status?')
    event.source && event.source.postMessage({type: 'galeb-offline', ...progress,
      done: self.registration.active ? FILES.length : progress.done});
});
self.addEventListener('fetch', event => {
  const req = event.request;
  if(req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    let hit = await cache.match(req, {ignoreSearch: true});
    if(!hit && req.mode === 'navigate') hit = await cache.match('./index.html');
    if(hit) return hit;
    try{
      const res = await fetch(req);
      if(res.ok && res.type === 'basic') cache.put(req, res.clone());
      return res;
    }catch(e){
      return new Response('offline', {status: 503, statusText: 'offline'});
    }
  })());
});
""" % (version, ', '.join(json.dumps('./' + f) for f in files))
open(os.path.join(out, 'sw.js'), 'w').write(sw)
print(f'{len(files)} files precached, cache galeb-{version}, size {sum(os.path.getsize(os.path.join(out, f)) for f in files) / 1e6:.1f} MB')
