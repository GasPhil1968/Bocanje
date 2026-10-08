# Jedan-Dva Kung-Fu – v11 (raster sprites)

v11 replaces all procedural Canvas drawings of v10 (fighters, weapons, backgrounds,
HUD, touch controls, effects, logos, speech bubbles, travel map) with the raster
asset pack `jdkf_complete_assets_v1`.

| File | Purpose |
|---|---|
| `jedan-dva-kung-fu-v11.html` | **The game.** Single file, offline, every image embedded as a data URI. Just open it. |
| `src/jedan-dva-kung-fu.html` | Source. Loads `../assets/` via `assets/manifest.json` when served over HTTP (e.g. `npx http-server jedan-dva-kung-fu`, then open `/src/jedan-dva-kung-fu.html`). |
| `assets/` | Game-ready assets (fighter frames cropped to WebP + anchor offsets, backgrounds as WebP, UI/FX/overlays as PNG), `manifest.json`, `CLEANUP_REPORT.txt`. |

## What is still drawn in code
Only things that are not graphics: live text (score, timer, names, dialogue, BKS/DE),
full-screen dimming/fades, the black cinematic bars, the radial vignette, screen
shake, mirroring and rotation of sprites.

## How the sprites are driven
The pose skeleton from v10 still runs and still produces the hitboxes
(`buildPts` → `hurtCircles`, `attackPoint`). Rendering picks one frame per
fighter from state, move phase (wind-up / strike / recover from the move's
`st`/`ac`/`rc` timings), jump velocity and walk phase (`frameNames()`), with
fallbacks when a fighter has no dedicated frame. Zumbul's iron ball is a separate
sprite that follows the AI-controlled `ball` position, linked by chain sprites.

## Rebuild
```
python3 tools/jdkf/prepare_assets.py <extracted jdkf_complete_assets_v1> jedan-dva-kung-fu/assets
python3 tools/jdkf/build_single_html.py jedan-dva-kung-fu jedan-dva-kung-fu/jedan-dva-kung-fu-v11.html
node tools/jdkf/smoke_test.js jedan-dva-kung-fu/jedan-dva-kung-fu-v11.html /tmp/shots
```
`tools/jdkf/apply_patch.py` is the one-off migration from the v10 file to `src/`
(kept for reference; edit `src/` directly from now on).

## Known limitations of the asset pack (not code bugs)
- The opponents are recolours/retouches of one base figure (see the pack's
  `FINAL_MANIFEST.txt`). Zumbul's "bald head" retouch shows as a flat disc over
  the face; several head-gear retouches are rough.
- Many frames contained detached "ghost limbs" (stray fists/feet); they are removed
  automatically by `prepare_assets.py` (list in `assets/CLEANUP_REPORT.txt`).
- Several wind-up/recover frames reuse the nearest pose, so some moves animate in
  only two steps.
- Backgrounds are simple flat illustrations, less detailed than the fighters.
