const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 420, height: 860 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (['error', 'warning'].includes(m.type()) && !/sfx_/.test(m.text())) errors.push(m.type() + ': ' + m.text()); });
  await page.addInitScript(() => { window.__osc = 0; const P = AudioContext.prototype, o = P.createOscillator; P.createOscillator = function () { window.__osc++; return o.apply(this, arguments); }; });
  await page.goto('http://127.0.0.1:8766/__test.html', { waitUntil: 'load', timeout: 120000 });
  await page.waitForTimeout(1500); await page.mouse.click(210, 430); await page.waitForTimeout(1500);
  const pb = await page.$('#playBtn'); if (pb) await pb.click({ force: true });
  const keep = async (n) => { for (let i = 0; i < n; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); } };
  await keep(30);
  const r = {};
  r.flight = await page.evaluate(() => ({ scene: __G.scene, music: __G.MUSIC.current, amb: __G.amb }));
  await page.evaluate(() => __G.goto(6)); await keep(30);
  r.podaca = await page.evaluate(() => ({ scene: __G.scene, music: __G.MUSIC.current, amb: __G.amb }));
  await page.evaluate(() => __G.rain()); await keep(35);
  r.rain = await page.evaluate(() => ({ state: __G.state, amb: __G.amb }));
  for (const id of ['amb_rain', 'amb_adriatic_waves_day']) {
    const b64 = await page.evaluate(async (id) => {
      const lp = __G.ambLoops[id]; const ab = await (await fetch('__testaudio/' + id + '.wav')).arrayBuffer();
      const sr = 32000, oc = new OfflineAudioContext(1, Math.floor(sr * lp[1] * 2.2), sr), buf = await oc.decodeAudioData(ab);
      const n = oc.createBufferSource(); n.buffer = buf; n.loop = true; n.loopStart = lp[0]; n.loopEnd = lp[0] + lp[1]; n.connect(oc.destination); n.start(0, lp[0]);
      const d = (await oc.startRendering()).getChannelData(0), i16 = new Int16Array(d.length);
      for (let i = 0; i < d.length; i++) i16[i] = Math.max(-32767, Math.min(32767, Math.round(d[i] * 32767)));
      let bin = ''; const by = new Uint8Array(i16.buffer); for (let i = 0; i < by.length; i += 32768) bin += String.fromCharCode.apply(null, by.subarray(i, i + 32768));
      return btoa(bin);
    }, id);
    fs.writeFileSync(process.argv[2] + '/_loop_' + id + '.raw', Buffer.from(b64, 'base64'));
  }
  r.osc = await page.evaluate(() => window.__osc); r.errors = errors;
  console.log(JSON.stringify(r, null, 1)); await browser.close();
})();
