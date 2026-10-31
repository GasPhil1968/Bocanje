# v16 – ideas from Soko v100, step 1

`patch_v16.py <BROWSER_15 index.html> <out index.html>`:
1. all 101 SFX are fetched after page load and decoded two at a time after the first tap
   (before, a sound was loaded on first use and dropped if that took > 0.85 s); 5 s back-off after errors;
2. 44 px buttons with speaker / note icons, "off" = faded + red slash; language button moves up when
   the pause button is hidden;
3. place badge: larger name on a dark plate with gold rim, route Pula → Dubrovnik as 7 dots and "n/7"
   (places visited in this flight);
4. version mark "© by FG · v16" (+ meta galeb-version).

Outputs in the repository root: `Galeb-nad-Jadranom-BROWSER_16.zip` (web build) and `galeb-web.zip`
(iPad offline app built with `../pwa/make_pwa.py`, now with Netlify `_headers`).
`test16.js` checks preloading, buttons, place badge and version (test copy with decoded WAVs, see browser12).
