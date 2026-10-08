// Smoke test: loads the built single-file game in Chromium, walks through all
// scenes and every opponent, simulates fights, and writes screenshots.
// Usage: node smoke_test.js <game.html> <out_dir>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const file = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3] || 'shots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto('file://' + file);
  await page.waitForFunction(() => window.__jdkf, null, { timeout: 20000 });
  const shot = async name => page.screenshot({ path: path.join(out, name + '.png') });
  await page.waitForTimeout(600);
  await shot('01_boot');
  // assets ready?
  const ready = await page.evaluate(async () => {
    for (let i = 0; i < 200; i++) { if (window.__jdkf.S.scene !== 'boot') return true; await new Promise(r => setTimeout(r, 100)); }
    return false;
  });
  if (!ready) errors.push('boot never finished (assets not ready?)');
  await page.waitForTimeout(500);
  await shot('02_title');

  // run game steps fast via the test hook
  const run = (ms) => page.evaluate((ms) => { const g = window.__jdkf; for (let t = 0; t < ms; t += 16.67) g.step(16.67); g.render(); }, ms);
  await page.evaluate(() => window.__jdkf.startGame());
  await run(2600); await shot('03_versus_levat');

  for (let st = 0; st < 7; st++) {
    await page.evaluate((st) => {
      const g = window.__jdkf; g.S.stage = st; g.spawnFoe(); g.player.hp = 100; g.player.x = 420; g.foe.x = 760;
      g.setScene('versus');
    }, st);
    await run(2700); await shot(`1${st}_versus`);
    await page.evaluate(() => { const g = window.__jdkf; g.setScene('fight'); g.S.timer = 60000; });
    // player attacks + AI acts
    const seq = ['punch', 'kick', 'punch', 'kick'];
    for (let i = 0; i < 6; i++) {
      await page.evaluate((k) => { const g = window.__jdkf; g.player.hp = 100; g.KP[k] = true; g.K.right = (k === 'kick'); }, seq[i % 4]);
      await run(260);
      await page.evaluate(() => { const g = window.__jdkf; g.K.right = false; });
      if (i === 1 || i === 4) await shot(`1${st}_fight_${i}`);
    }
    await run(1500); await shot(`1${st}_fight_ai`);
    // knock out the foe -> ko frames, dropped weapon, clear scene
    await page.evaluate(() => { const g = window.__jdkf; g.foe.hp = 1; g.player.x = g.foe.x - 110; g.player.dir = 1; g.KP.kick = true; });
    await run(1200); await shot(`1${st}_after_ko`);
  }
  // explicit poses on Saner
  for (const [name, setup] of Object.entries({
    jump: "g.player.onGround=false;g.player.y=480;g.player.vy=-6;g.player.state='jump';",
    crouch: "g.K.down=true;",
    block: "g.K.left=true;",
  })) {
    await page.evaluate((src) => { const g = window.__jdkf; g.S.stage = 3; g.spawnFoe(); g.setScene('fight'); g.player.state = 'idle'; g.player.x = 400; g.foe.x = 900; new Function('g', src)(g); }, setup);
    await page.evaluate(() => { const g = window.__jdkf; g.step(16.67); g.render(); });
    await shot('30_' + name);
    await page.evaluate(() => { const g = window.__jdkf; g.K.down = false; g.K.left = false; });
  }
  // travel / over / ending
  await page.evaluate(() => { const g = window.__jdkf; g.S.stage = 2; g.spawnFoe(); g.setScene('travel'); });
  await run(1800); await shot('40_travel');
  await page.evaluate(() => { const g = window.__jdkf; g.setScene('over'); });
  await run(1300); await shot('41_over');
  await page.evaluate(() => { const g = window.__jdkf; g.setScene('ending'); });
  await run(2400); await shot('42_ending');
  await page.evaluate(() => { const g = window.__jdkf; g.S.stage = 1; g.spawnFoe(); g.setScene('clear'); g.foe.state = 'ko'; g.foe.deadT = 400; });
  await run(1500); await shot('43_clear');

  // touch layout
  const ctx2 = await browser.newContext({ viewport: { width: 1280, height: 720 }, hasTouch: true });
  const p2 = await ctx2.newPage();
  p2.on('pageerror', e => errors.push('touch pageerror: ' + e.message));
  await p2.goto('file://' + file);
  await p2.waitForFunction(() => window.__jdkf && window.__jdkf.S.scene !== 'boot', null, { timeout: 30000 });
  await p2.touchscreen.tap(60, 680); // language chip
  await p2.waitForTimeout(200);
  await p2.screenshot({ path: path.join(out, '50_title_touch_lang.png') });
  await p2.evaluate(() => { const g = window.__jdkf; g.startGame(); g.setScene('fight'); g.S.stage = 0; });
  await p2.waitForTimeout(400);
  await p2.screenshot({ path: path.join(out, '51_fight_touch.png') });

  await browser.close();
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no runtime errors');
  process.exit(errors.length ? 1 : 0);
})();
