const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 420, height: 860 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) errors.push(m.type() + ': ' + m.text()); });
  await page.addInitScript(() => { window.__osc = 0; const P = (window.AudioContext).prototype; const o = P.createOscillator; P.createOscillator = function () { window.__osc++; return o.apply(this, arguments); }; });
  await page.goto('http://127.0.0.1:8765/__test.html', { waitUntil: 'load', timeout: 120000 });
  await page.waitForTimeout(1500);
  await page.mouse.click(210, 430); await page.waitForTimeout(1500);
  const pb = await page.$('#playBtn'); if (pb) await pb.click({ force: true });
  await page.waitForTimeout(2500);
  const r = {};
  r.aacDecodable = await page.evaluate(async () => { try { const ab = await (await fetch('__testaudio/mus_city_podaca.wav')).arrayBuffer(); const b = await __G.ac.decodeAudioData(ab); return { ok: true, dur: b.duration, sr: b.sampleRate, ch: b.numberOfChannels }; } catch (e) { return { ok: false, err: String(e) }; } });
  r.start = await page.evaluate(() => ({ scene: __G.scene, music: __G.MUSIC.current }));
  await page.evaluate(() => __G.goto(6));                         // index 6 in SCENES = Podaca
  for (let i = 0; i < 40; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); }
  r.podaca = await page.evaluate(() => ({ scene: __G.scene, track: __G.cityTrack(), music: __G.MUSIC.current }));
  await page.evaluate(() => __G.setNiz(10)); await page.waitForTimeout(400);
  await page.evaluate(() => __G.feverStart());
  for (let i = 0; i < 25; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); }
  r.fever = await page.evaluate(() => __G.MUSIC.current);
  await page.evaluate(() => __G.feverKraj());
  for (let i = 0; i < 30; i++) { await page.evaluate(() => { if (__G.bird.y > __G.H * 0.42) __G.bird.v = -300; }); await page.waitForTimeout(100); }
  r.afterFever = await page.evaluate(() => ({ scene: __G.scene, music: __G.MUSIC.current }));
  // gapless proof: render 2.2 loop periods of the loop region offline
  for (const id of ['mus_city_podaca', 'mus_fever']) {
    const b64 = await page.evaluate(async (id) => {
      const lp = window.GALEB_MUSIC_LOOPS[id];
      const ab = await (await fetch('__testaudio/' + id + '.wav')).arrayBuffer();
      const sr = 32000, len = Math.floor(sr * lp[1] * 2.2);
      const oc = new OfflineAudioContext(1, len, sr); const buf = await oc.decodeAudioData(ab);
      const n = oc.createBufferSource(); n.buffer = buf; n.loop = true; n.loopStart = lp[0]; n.loopEnd = lp[0] + lp[1];
      n.connect(oc.destination); n.start(0, lp[0]);
      const d = (await oc.startRendering()).getChannelData(0);
      const i16 = new Int16Array(d.length); for (let i = 0; i < d.length; i++) i16[i] = Math.max(-32767, Math.min(32767, Math.round(d[i] * 32767)));
      let bin = ''; const by = new Uint8Array(i16.buffer); for (let i = 0; i < by.length; i += 32768) bin += String.fromCharCode.apply(null, by.subarray(i, i + 32768));
      return btoa(bin);
    }, id);
    fs.writeFileSync(process.argv[2] + '/_loop_' + id + '.raw', Buffer.from(b64, 'base64'));
  }
  r.osc = await page.evaluate(() => window.__osc);
  r.errors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
