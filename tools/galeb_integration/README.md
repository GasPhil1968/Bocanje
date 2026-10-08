# Galeb nad Jadranom – audio integration

`Galeb-nad-Jadranom.html` (repository root) is the game with all sound coming from rendered files:
the 111 SFX/ambience sounds (MP3, embedded) and the background music pack (9 pieces + 6 city intensity
layers, MP3, embedded). No run-time synthesis is left (no oscillators, generated noise buffers or convolver).

Base: `Galeb-nad-Jadranom-NEUE-SFX-FERTIG.html` (SFX already wired in). `integrate.py` then
- embeds the music (`window.GALEB_MUSIC_DATA`) and replaces the ambience MP3s with gapless versions;
  every loop is stored with 0.5 s wrap-around padding and played with `loopStart`/`loopEnd`
  (`window.GALEB_LOOPS`), so MP3 encoder delay can never cause a gap,
- skips the MP3 encoder delay at the start of one-shot SFX,
- adds the `MUSIC` player (menu → city piece → fever → city → end screen, combo intensity layer,
  radio ducking, music button) and suspends audio while the tab is hidden,
- removes the procedural music engine, `pluck`, the convolver reverb and `musicTick()`.

```
python3 make_assets.py <work dir with mwork/ and pack/> assets.json
python3 integrate.py Galeb-nad-Jadranom-NEUE-SFX-FERTIG.html assets.json Galeb-nad-Jadranom.html
python3 prep_test.py Galeb-nad-Jadranom.html test.html     # test copy with a debug hook
node test.js test.html 70        # bot plays; reports errors, oscillator count, sounds played
node events.js test.html mus_fever   # fever/layer switching, decode of all files, offline loop render
```
