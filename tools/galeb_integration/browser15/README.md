# BROWSER_14 → BROWSER_15: Podaca music + the 10 ambience loops

Input: `Galeb-nad-Jadranom-BROWSER_14.zip` (same audio code as BROWSER_11; Podaca mapped to Makarska music,
ambience files missing).

1. Music: the 17 padded AAC music loops from `../browser12/encode_music.py` (incl. `mus_city_podaca`)
   and `../browser12/patch_index.py` (Podaca → `mus_city_podaca`, `GALEB_MUSIC_LOOPS`, exact loop region).
2. Ambience: `encode_amb.py <out> amb_loops.json 12 <masters>` encodes the 10 loops as AAC stereo
   32 kHz 64 kbit/s, +12 dB (so they sit ~13 dB under the music with the game's existing gains:
   per-loop 0.12–0.44, busAmb 0.45), with 0.5 s wrap-around padding → `assets/audio/ambience/`.
3. `patch_amb.py` adds the paths to `GALEB_SFX_DATA`, adds `GALEB_AMB_LOOPS` and makes `refreshAmbient()`
   loop exactly the original period (random start position inside the loop).
4. `test14.js` (with a test copy made by `../browser12/prep_test11.py`, extra hook fields `amb`,
   `rain`, `ambLoops`): checks ambience per city and weather, Podaca music, oscillator count, and renders
   the loop region offline for the seam check.
