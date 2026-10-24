"""Build the offline web-app (PWA) version of Boće na rivi for iPad.
usage: python3 -I build_pwa.py <original index.html> <og jpg> <out dir>"""
import sys, os, re, base64, io, json, hashlib, shutil
from PIL import Image

src, jpg, out = sys.argv[1:4]
html = open(src, encoding='utf-8').read()
os.makedirs(out, exist_ok=True)

def replace_once(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:60])
    return s.replace(old, new)

# 1. icons: WebP 1024 from the embedded artwork -> PNG files iOS can use
m = re.search(r'"icons/app_1024\.png":\{"u":"data:image/webp;base64,([A-Za-z0-9+/=]+)"', html)
icon = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert('RGBA')
bg = Image.new('RGBA', icon.size, (13, 42, 58, 255))          # #0d2a3a, iOS shows no transparency
icon_flat = Image.alpha_composite(bg, icon).convert('RGB')
for n in (180, 192, 512):
    icon_flat.resize((n, n), Image.LANCZOS).save(os.path.join(out, f'icon-{n}.png'), optimize=True)

# 2. head: real manifest + Apple home-screen tags (the old blob-URL manifest is then skipped)
head = ('<title>Boće na rivi</title>\n'
        '<link rel="manifest" href="manifest.webmanifest">\n'
        '<link rel="apple-touch-icon" href="icon-180.png">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="Boće">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black">\n'
        '<meta name="theme-color" content="#0d2a3a">')
html = replace_once(html, '<title>Boće na rivi</title>', head)

# 3. register the service worker instead of removing it (?nosw still switches it off)
html = replace_once(html,
    "const bezWorkera = true;   // Artifact-Fassung: es gibt hier keine sw.js",
    "const bezWorkera = /[?&]nosw\\b/.test(location.search);   // Web-App-Fassung: sw.js liegt daneben")

html = replace_once(html,
    "(location.protocol === 'https:' || location.hostname === 'localhost'))",
    "(window.isSecureContext || location.protocol === 'https:'))")

# 4. "offline ready" notice once the whole game is in the cache
notice = r"""
<script>
/* Web-App: Hinweis, sobald das ganze Spiel im Offline-Speicher liegt. */
(function(){
  if(!('serviceWorker' in navigator) || !window.caches || /[?&]nosw\b/.test(location.search)) return;
  var TXT = { hr:['Spremno za offline','Igra sada radi i bez interneta.'],
              de:['Offline bereit','Das Spiel läuft jetzt auch ohne Internet.'],
              en:['Ready offline','The game now works without internet.'] };
  function jezik(){ try{ return (typeof JEZIK==='string' && TXT[JEZIK]) ? JEZIK : 'hr'; }catch(e){ return 'hr'; } }
  function pokazi(){
    var t = TXT[jezik()], d = document.createElement('div');
    d.setAttribute('role','status');
    d.style.cssText = 'position:fixed;left:50%;bottom:max(24px,env(safe-area-inset-bottom));transform:translateX(-50%);'+
      'z-index:30;background:#ffe7a8;color:#241a12;border:3px solid #241a12;border-radius:16px;padding:12px 20px;'+
      'font:600 18px "Avenir Next",system-ui,sans-serif;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.45);'+
      'transition:opacity .6s;pointer-events:none;max-width:86vw';
    d.innerHTML = '✓ '+t[0]+'<div style="font-weight:400;font-size:14px;margin-top:2px">'+t[1]+'</div>';
    document.body.appendChild(d);
    setTimeout(function(){ d.style.opacity='0'; }, 5000);
    setTimeout(function(){ d.remove(); }, 5800);
  }
  var VERZIJA = '__CACHE__', KLJUC = 'boce-offline-spremno';
  navigator.serviceWorker.ready.then(function(){
    var pokusaj = 0;
    (function provjeri(){
      caches.open(VERZIJA).then(function(c){ return c.match('index.html'); }).then(function(r){
        if(r){ var bilo=null; try{ bilo = localStorage.getItem(KLJUC); localStorage.setItem(KLJUC, VERZIJA); }catch(e){}
               if(bilo !== VERZIJA) pokazi(); }
        else if(++pokusaj < 120) setTimeout(provjeri, 1000);
      }).catch(function(){});
    })();
  }).catch(function(){});
})();
</script>
"""
# 5. service worker: cache-first, precache everything, versioned by content hash
files = ['index.html', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png', 'icon-512.png', os.path.basename(jpg)]
ver = 'boce-' + hashlib.sha256((html + notice).encode()).hexdigest()[:10]
html = replace_once(html, '</script>\n\n</body></html>', '</script>\n' + notice.replace('__CACHE__', ver) + '\n</body></html>')
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
shutil.copy(jpg, os.path.join(out, os.path.basename(jpg)))

json.dump({'name': 'Boće na rivi', 'short_name': 'Boće', 'lang': 'hr', 'start_url': 'index.html', 'scope': './',
           'display': 'standalone', 'orientation': 'portrait', 'background_color': '#0d2a3a', 'theme_color': '#0d2a3a',
           'icons': [{'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                     {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'}]},
          open(os.path.join(out, 'manifest.webmanifest'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

sw = """/* Boće na rivi - offline cache (cache-first). New deploy = new CACHE name. */
const CACHE = '%s';
const FILES = %s;
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
""" % (ver, json.dumps(files))
open(os.path.join(out, 'sw.js'), 'w').write(sw)

# Netlify: never let the browser keep an old sw.js / manifest around
open(os.path.join(out, '_headers'), 'w').write(
    '/sw.js\n  Cache-Control: no-cache\n/manifest.webmanifest\n  Cache-Control: no-cache\n'
    '/index.html\n  Cache-Control: no-cache\n/\n  Cache-Control: no-cache\n')
print('built', out, 'cache', ver, sorted(os.listdir(out)))
