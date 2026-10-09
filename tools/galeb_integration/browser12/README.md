# BROWSER_11 → BROWSER_12: Podaca music + gapless music loops

Input: `Galeb-nad-Jadranom-BROWSER_11.zip` (multi-file web build, music as AAC mono 32 kHz 48 kbit/s).

1. `encode_music.py` re-encodes all 17 music loops from the WAV masters (incl. the new
   `mus_city_podaca` + layer) with the same AAC settings, but with 0.5 s wrap-around padding on both
   ends, and writes `loops.json` ([loopStart, length] in seconds).
2. `patch_index.py` adds Podaca to `GALEB_MUSIC_URLS`/`GALEB_MUSIC_META`, maps `Podaca` to
   `mus_city_podaca` in `CITY_TRACK`, adds `window.GALEB_MUSIC_LOOPS` and makes the music player loop
   exactly the original period (`loopStart`/`loopEnd`), so AAC priming/padding cannot cause a gap.
3. `prep_test11.py` + `test11.js`: test copy with a debug hook; checks Podaca/fever switching, the
   absence of oscillators and renders the loop region offline for a seamlessness check. (The headless
   test Chromium has no AAC decoder, so the test copy loads ffmpeg-decoded WAV versions of the same files.)
