# TRI FILDŽANA – SFX pack build scripts

These scripts render `tri_fildzana_complete_sfx.zip` in the repository root: 59 sound ids and 78 WAV files, PCM 16-bit at 44.1 kHz.

Every sound is **procedurally synthesized**, not recorded:

| File | Contents |
|---|---|
| `core.py` | filters, envelopes, trimming and fades, K-weighted loudness, true peak, 16-bit TPDF-dithered writer |
| `models.py` | physical models (modal ceramic cups, wood, coins, bells, membrane drum + jingles, friction, fabric, paper); Karplus–Strong strings with re-pluck and glides; glottal-pulse/formant voice model (`SANER`, `LEVAT`, `MINKA`) |
| `sounds.py` | one design function per sound id |
| `build.py` | catalogue (id, variants, duration range, loudness target, gain, event) → renders `audio/sfx/*.wav` |
| `package.py` | decodes every file (soundfile + ffprobe), checks the format, audibility, −1 dBFS ceiling, duration range, lead silence, clean edges and duplicates, and writes `sfx_manifest.json` |

Requirements: Python 3.11+, `numpy scipy soundfile`, and ffmpeg/ffprobe.

```
python3 build.py OUT && python3 package.py OUT
cp SFX_MAPPING.md OUT/   # the mapping doc lives in the zip; edit it there
```

Rendering is deterministic: each file is seeded from the CRC32 of its filename.
