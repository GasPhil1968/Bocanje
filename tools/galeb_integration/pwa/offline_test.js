const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const ctx = await chromium.launchPersistentContext(process.argv[2], { viewport: { width: 820, height: 1180 }, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  const toasts = [];
  await page.exposeFunction('__toast', t => toasts.push(t));
  await page.addInitScript(() => { new MutationObserver(ms => { for (const m of ms) { const t = m.target.textContent || ''; if (/offline|Offline/.test(t) && t.length < 60) window.__toast(t); } })
    .observe(document, { subtree: true, childList: true, characterData: true }); });
  const url = 'http://127.0.0.1:8767/index.html';
  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'load' });
  // wait until the SW has cached everything
  let n = 0, total = 0;
  for (let i = 0; i < 120; i++) {
    const r = await page.evaluate(async () => { const ks = await caches.keys(); let n = 0; for (const k of ks) n += (await (await caches.open(k)).keys()).length; return { n, ctrl: !!navigator.serviceWorker.controller }; });
    n = r.n; if (r.n >= 296 && r.ctrl) break; await page.waitForTimeout(500);
  }
  const onlineSecs = (Date.now() - t0) / 1000;
  await page.waitForTimeout(800);
  // -------- now cut the network completely and reload
  await ctx.setOffline(true);
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(2000);
  const off = {};
  off.title = await page.title();
  off.canvasVisible = await page.evaluate(() => !!document.querySelector('canvas'));
  await page.mouse.click(410, 590); await page.waitForTimeout(1200);
  const pb = await page.$('#playBtn'); if (pb && await pb.isVisible()) { await pb.click({ force: true }); off.started = true; }
  for (let i = 0; i < 25; i++) { await page.mouse.click(410, 400); await page.waitForTimeout(260); }
  off.fetches = await page.evaluate(async () => {
    const urls = ['assets/audio/music/mus_city_podaca.m4a', 'assets/audio/ambience/amb_rain.m4a', 'assets/audio/sfx/sfx_score_tick.m4a', 'assets/img/city_podaca.png', 'apple-touch-icon.png', 'manifest.webmanifest'];
    const out = {}; for (const u of urls) { try { const r = await fetch(u); out[u] = r.status + ' ' + (await r.arrayBuffer()).byteLength; } catch (e) { out[u] = 'ERR ' + e; } } return out;
  });
  off.navigatorOnline = await page.evaluate(() => navigator.onLine);
  await page.screenshot({ path: process.argv[3] });
  console.log(JSON.stringify({ cachedEntries: n, onlineSecs, toasts: [...new Set(toasts)], offline: off, errors }, null, 1));
  await ctx.close();
})();
