const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 820, height: 1180 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) errors.push(m.type() + ': ' + m.text()); });
  await page.goto('http://127.0.0.1:8768/__test.html', { waitUntil: 'load' });
  await page.waitForTimeout(6000);
  const r = {};
  r.beforeTap = await page.evaluate(() => __G.sfxStat);
  r.version = await page.evaluate(() => document.getElementById('fg').textContent);
  await page.mouse.click(410, 590); await page.waitForTimeout(6000);
  r.afterTap = await page.evaluate(() => __G.sfxStat);
  await page.screenshot({ path: out + '/v16_menu.png' });
  r.toggled0 = await page.evaluate(() => ({ sound: document.getElementById('sound').className, music: document.getElementById('music').className,
    jezikTop: getComputedStyle(document.getElementById('jezik')).top, pauseOff: document.getElementById('pause').className }));
  await page.screenshot({ path: out + '/v16_buttons_off.png', clip: { x: 0, y: 0, width: 260, height: 240 } });
  const pb = await page.$('#playBtn'); if (pb) await pb.click({ force: true });
  for (let i = 0; i < 30; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); }
  await page.evaluate(() => __G.goto(6));
  for (let i = 0; i < 10; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); }
  await page.click('#sound'); await page.click('#music'); await page.waitForTimeout(300);
  r.toggled = await page.evaluate(() => ({ sound: document.getElementById('sound').className, music: document.getElementById('music').className }));
  await page.screenshot({ path: out + '/v16_buttons_off.png', clip: { x: 0, y: 0, width: 260, height: 240 } });
  await page.click('#sound'); await page.click('#music');
  r.place = await page.evaluate(() => ({ html: document.getElementById('place').innerText, jezikTop: getComputedStyle(document.getElementById('jezik')).top }));
  await page.screenshot({ path: out + '/v16_flight.png' });
  await page.screenshot({ path: out + '/v16_hud.png', clip: { x: 520, y: 0, width: 300, height: 120 } });
  r.errors = errors;
  console.log(JSON.stringify(r, null, 1)); await browser.close();
})();
