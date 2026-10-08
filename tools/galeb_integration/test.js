// usage: node test.js <html> [seconds]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
(async () => {
  const file = path.resolve(process.argv[2]); const secs = +(process.argv[3] || 25);
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 420, height: 860 }, isMobile: true, hasTouch: true });
  const errors = [], logs = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') logs.push(m.type() + ': ' + m.text()); });
  await page.addInitScript(() => {
    window.__audio = { osc: 0, bufsrc: 0, decodeOk: 0, decodeFail: 0, buffersCreated: 0, conv: 0, started: [] };
    const AC = window.AudioContext || window.webkitAudioContext;
    const P = AC.prototype;
    const o1 = P.createOscillator; P.createOscillator = function () { window.__audio.osc++; return o1.apply(this, arguments); };
    const o2 = P.createBufferSource; P.createBufferSource = function () { window.__audio.bufsrc++; return o2.apply(this, arguments); };
    const o3 = P.createBuffer; P.createBuffer = function () { window.__audio.buffersCreated++; return o3.apply(this, arguments); };
    const o4 = P.createConvolver; P.createConvolver = function () { window.__audio.conv++; return o4.apply(this, arguments); };
    const BA = window.BaseAudioContext ? window.BaseAudioContext.prototype : P;
    const d = BA.decodeAudioData;
    BA.decodeAudioData = function (ab, ok, err) {
      const pr = d.call(this, ab);
      pr.then(() => window.__audio.decodeOk++, () => window.__audio.decodeFail++);
      if (ok || err) pr.then(ok, err);
      return pr;
    };
  });
  const t0 = Date.now();
  await page.goto('file://' + file, { waitUntil: 'load', timeout: 180000 });
  const loadMs = Date.now() - t0;
  await page.waitForTimeout(1500);
  // wrap playSfx / MUSIC.play if present
  await page.evaluate(() => {
    window.__played = window.__played || [];
    const M = window.__G.MUSIC;
    if (M) { const p = M.play; M.play = function (id, f) { window.__played.push('MUSIC:' + id); return p.call(M, id, f); }; }
  });
  const box = await page.viewportSize();
  await page.mouse.click(box.width / 2, box.height / 2);          // dismiss intro / unlock audio
  await page.waitForTimeout(1500);
  const playBtn = await page.$('#playBtn');
  if (playBtn && await playBtn.isVisible()) await playBtn.click({ force: true });
  await page.waitForTimeout(800);
  const tEnd = Date.now() + secs * 1000;
  let k = 0;
  while (Date.now() < tEnd) {                                      // keep the bird in the air, crash eventually
    const st = await page.evaluate(() => {
      const b = __G.bird; let target = __G.H * 0.45;
      const p = __G.pipes.find(q => q.x > b.x - 30);
      if (p) { const o = __G.gap(p)[0]; target = (o.t + o.b) / 2 + (o.b - o.t) * 0.1; }
      return { state: __G.state, y: b.y, v: b.v, target };
    });
    if (st.state === 'dead') { await page.waitForTimeout(4200); await page.screenshot({ path: 'shot_dead.png' }); const ag = await page.$('#againBtn'); if (ag && await ag.isVisible()) await ag.click({ force: true }); await page.waitForTimeout(500); }
    else if (st.state === 'playing') { if (st.y > st.target && st.v > -40) await page.mouse.click(box.width / 2, box.height / 3); if (k === 150) await page.screenshot({ path: 'shot_play.png' }); }
    await page.waitForTimeout(40); k++;
  }
  const res = await page.evaluate(() => ({ audio: window.__audio, played: window.__played || [], acState: __G.ac && __G.ac.state,
    music: __G.MUSIC ? __G.MUSIC.current : null, score: __G.score }));
  const counts = {}; for (const p of res.played) counts[p] = (counts[p] || 0) + 1;
  console.log(JSON.stringify({ loadMs, errors, logs: logs.slice(0, 20), acState: res.acState, audio: res.audio, music: res.music,
    distinctPlayed: Object.keys(counts).length, counts }, null, 1));
  await browser.close();
})();
