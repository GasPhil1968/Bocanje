// Offline test: online visit -> "Offline bereit" -> server stopped + offline -> game starts from cache.
const { chromium } = require('playwright-core');
const { spawn } = require('child_process');
const dir = process.argv[2], shots = process.argv[3];
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const srv = spawn('python3', ['-m', 'http.server', '8765', '--bind', '127.0.0.1'], { cwd: dir, stdio: 'ignore' });
  await sleep(1500);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const ctx = await browser.newContext({ viewport: { width: 820, height: 1180 }, hasTouch: true, locale: 'de-DE' });
  const errors = [];
  let page = await ctx.newPage();
  page.on('pageerror', e => errors.push(String(e)));
  const t0 = Date.now();
  await page.goto('http://127.0.0.1:8765/index.html');
  await page.waitForFunction(() => window.BoceArt && window.BoceArt.loaded, null, { timeout: 120000 });
  console.log('art loaded online after', (Date.now() - t0) / 1000, 's');
  const toast = await page.waitForSelector('div[role=status]', { timeout: 150000 });
  console.log('notice after', (Date.now() - t0) / 1000, 's:', (await toast.innerText()).replace(/\n/g, ' | '));
  await page.screenshot({ path: shots + '/1_online_notice.png' });
  const cached = await page.evaluate(async () => {
    const out = {};
    for (const k of await caches.keys()) out[k] = (await (await caches.open(k)).keys()).map(r => new URL(r.url).pathname);
    return out;
  });
  console.log('caches:', JSON.stringify(cached));
  const swCtl = await page.evaluate(() => !!navigator.serviceWorker.controller);
  console.log('page controlled by SW:', swCtl);
  await page.close();

  // ---- offline: stop server AND cut the network
  srv.kill(); await sleep(500);
  await ctx.setOffline(true);
  for (const url of ['http://127.0.0.1:8765/index.html', 'http://127.0.0.1:8765/']) {
    page = await ctx.newPage();
    page.on('pageerror', e => errors.push(String(e)));
    const t1 = Date.now();
    await page.goto(url);
    await page.waitForFunction(() => window.BoceArt && window.BoceArt.loaded, null, { timeout: 60000 });
    console.log('OFFLINE', url, 'game artwork loaded after', (Date.now() - t1) / 1000, 's, state =', await page.evaluate(() => BoceArt.state));
    await sleep(2500);
    await page.mouse.click(410, 590); await sleep(800);
    await page.mouse.click(410, 590); await sleep(1500);
    console.log('  after taps state =', await page.evaluate(() => BoceArt.state));
    await page.screenshot({ path: shots + '/2_offline_' + (url.endsWith('/') ? 'root' : 'index') + '.png' });
    await page.close();
  }
  console.log('page errors:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
