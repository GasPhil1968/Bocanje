# Galeb nad Jadranom as an offline web app (iPad / iPhone)

`make_pwa.py <web build> <out>` turns the multi-file web build (BROWSER_15) into an installable offline app:
static `apple-touch-icon.png` / `icon-192.png` / `icon-512.png`, `manifest.webmanifest`, and `sw.js`, which
precaches every file of the build (cache name = content hash, older caches are deleted on update). The page
shows the caching progress and, once complete, "Offline bereit ✓" (hr/en/de via the game's `L()`).

`offline_test.js <profile dir> <screenshot>` (serve the folder on http://127.0.0.1:8767 first): opens the
game once online, waits until all files are cached, cuts the network, reloads and checks that the game
starts and that music, ambience, SFX and images are served offline.

Result: `galeb-web.zip` (folder `galeb`, 13.4 MB, 295 files + `./`) in the repository root.
