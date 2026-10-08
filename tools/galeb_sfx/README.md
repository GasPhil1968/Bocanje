# Galeb nad Jadranom – SFX pack build scripts

These scripts render `galeb_nad_jadranom_complete_sfx.zip` (repository root): 111 original sounds
(101 one-shots + 10 seamless ambience loops) as 44.1 kHz / 16-bit WAV, Ogg Vorbis copies,
`audio_manifest.json`, `AUDIO_INTEGRATION_GUIDE.md` and `AUDIO_QA_REPORT.md`.

| Script | Purpose |
|---|---|
| `lib.py` | DSP + instrument models (Karplus-Strong strings, modal bells/stone/wood/glass, STFT-shaped air & wind, bubbles, rain, creaks, gull/cormorant voices) |
| `sounds.py` | one recipe per sound + its manifest metadata (event, trigger, priority, cooldown, loudness target …) |
| `master.py` | render + master: trim, fades, per-category loudness, −3.2 dBTP ceiling, loop seam rotation, 16-bit TPDF dither |
| `qa.py` | automatic validation (names, format, duration, silence, clipping, DC, clicks, harshness, distinctness, variations, loop seams) |
| `docs.py` | manifest, integration guide and QA report |
| `build.py` | everything end to end, incl. OGG encode/decode check and ZIP verification |
| `sheet.py` | spectrogram contact sheets for visual review |

Requirements: Python 3.11+, `numpy scipy` (+ `soundfile` for the reference OGG decode check, `matplotlib` for `sheet.py`), ffmpeg with libvorbis for the OGG copies.

```
python3 build.py /tmp/work ../../galeb_nad_jadranom_complete_sfx.zip
```

Rendering is deterministic (fixed seeds); a full build takes about a minute. No samples or third-party audio are used.
