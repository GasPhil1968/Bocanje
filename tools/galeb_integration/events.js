const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 420, height: 860 } });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text()); });
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'load', timeout: 180000 });
  await page.waitForTimeout(1200);
  await page.mouse.click(210, 430); await page.waitForTimeout(1200);
  await page.click('#playBtn', { force: true }); await page.waitForTimeout(3000);
  const r = {};
  r.atStart = await page.evaluate(() => __G.MUSIC.current);
  await page.evaluate(() => __G.setNiz(10)); await page.waitForTimeout(300);
  r.layerAt10 = await page.evaluate(() => __G.nizLayer());
  await page.evaluate(() => { __G.feverStart(); }); for (let i=0;i<25;i++){ await page.evaluate(()=>{ if(__G.bird.y>__G.H*0.42) __G.bird.v=-300; }); await page.waitForTimeout(100);} 
  r.duringFever = await page.evaluate(() => __G.MUSIC.current);
  r.stateBeforeKraj = await page.evaluate(() => __G.state); await page.evaluate(() => __G.feverKraj()); for (let i=0;i<25;i++){ await page.evaluate(()=>{ if(__G.bird.y>__G.H*0.42) __G.bird.v=-300; }); await page.waitForTimeout(100);} 
  r.afterFever = await page.evaluate(() => __G.MUSIC.current);
  // decode every embedded sound and every music file in this browser
  r.decode = await page.evaluate(async () => {
    const out = { sfxOk: 0, sfxFail: [], musOk: 0, musFail: [], leadMaxMs: 0 };
    for (const id of __G.SFXIDS) { const b = await __G.decodeSfx(id); if (b) { out.sfxOk++; out.leadMaxMs = Math.max(out.leadMaxMs, (b.__lead || 0) * 1000); } else out.sfxFail.push(id); }
    for (const id of Object.keys(window.GALEB_MUSIC_DATA)) {
      try { const s = atob(window.GALEB_MUSIC_DATA[id]); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
        const b = await __G.ac.decodeAudioData(u.buffer); const lp = GALEB_LOOPS[id];
        if (b.duration >= lp[0] + lp[1]) out.musOk++; else out.musFail.push(id + ' too short'); } catch (e) { out.musFail.push(id + ' ' + e); }
    }
    return out;
  });
  // gapless proof: render 2.2 loop periods of a looping source offline, hand the samples back
  for (const id of process.argv.slice(3)) {
    const data = await page.evaluate(async (id) => {
      const src = (window.GALEB_MUSIC_DATA[id] || null);
      const b64 = src || (await (async () => { return null; })());
      const s = atob(b64 || window.__AMB[id]); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
      const lp = GALEB_LOOPS[id]; const sr = 44100; const len = Math.floor(sr * (lp[1] * 2.2));
      const oc = new OfflineAudioContext(1, len, sr);
      const buf = await oc.decodeAudioData(u.buffer);
      const n = oc.createBufferSource(); n.buffer = buf; n.loop = true; n.loopStart = lp[0]; n.loopEnd = lp[0] + lp[1];
      n.connect(oc.destination); n.start(0, lp[0]);
      const r = await oc.startRendering(); const d = r.getChannelData(0);
      let bin = ''; const i16 = new Int16Array(d.length); for (let i = 0; i < d.length; i++) i16[i] = Math.max(-32767, Math.min(32767, Math.round(d[i] * 32767)));
      const by = new Uint8Array(i16.buffer); for (let i = 0; i < by.length; i += 32768) bin += String.fromCharCode.apply(null, by.subarray(i, i + 32768));
      return btoa(bin);
    }, id);
    fs.writeFileSync(`/tmp/_loop_${id}.raw`, Buffer.from(data, 'base64'));
  }
  r.errors = errors;
  console.log(JSON.stringify(r, null, 1));
  await browser.close();
})();
