# Galeb nad Jadranom – music pack build scripts

These scripts render `galeb_nad_jadranom_music.zip` (repository root): 9 seamless stereo music loops
(menu, six cities, fever, end screen) plus 6 synchronous intensity layers for the cities, Ogg Vorbis copies,
`music_manifest.json`, `MUSIC_INTEGRATION_GUIDE.md` and `MUSIC_QA_REPORT.md`.

| Script | Purpose |
|---|---|
| `instruments.py` | instrument models: formant-shaped male voices (klapa), mandolin/guitar/double bass (Karplus-Strong), Istrian sopila, flue pipes, tapan, frame drum, shaker |
| `compose.py` | composition framework: chords, melody notation, 4-part klapa harmony, arpeggios, strums, drums; circular rendering and reverb so every loop is sample-exact |
| `songs.py` | the nine compositions (hand-written melodies and progressions) |
| `render.py` | render + master (loudness, true-peak ceiling shared by base and layer) |
| `build_music.py` | everything end to end incl. QA, OGG, manifest, guide, report, ZIP |
| `diag.py`, `msheet.py` | per-instrument level analysis and spectrogram sheets |

Uses the DSP helpers and QA functions from `../galeb_sfx`. Requirements: Python 3.11+, `numpy scipy soundfile`,
ffmpeg with libvorbis.

```
python3 build_music.py /tmp/work ../../galeb_nad_jadranom_music.zip
```

Rendering is deterministic (fixed seeds) and takes a few minutes. No samples or third-party audio are used.
