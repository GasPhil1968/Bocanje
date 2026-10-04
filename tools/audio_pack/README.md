# Boće na rivi – audio pack build scripts

These scripts render `boce_na_rivi_complete_audio.zip` (in the repository root).

| Script | Produces |
|---|---|
| `gen_physical.py` | balls, bulin, gravel, rolling loops, stop scrape, throws, wooden boards |
| `gen_voices.py` | 8 character voices × 5 clips (Kokoro TTS via phonemes, ASR-checked) |
| `gen_crowd.py` | applause (procedural clap model) and crowd reaction calls |
| `gen_amb.py` | sea / wind / café loops, cicadas, gulls, optional cat |
| `gen_music.py` | UI sounds, mandolin-like stingers and intro title cues |
| `validate.py`, `previews.py`, `build_meta.py` | technical checks, preview mixes, metadata |

Shared helpers: `dsp.py`, `hrtts.py` (Croatian→IPA, Kokoro wrapper, Whisper ASR), `meta.py`, `spk.py`, `sheet.py`.

Requirements: Python 3.11, `numpy scipy soundfile kokoro-onnx onnxruntime sherpa-onnx praat-parselmouth pyloudnorm matplotlib`, and ffmpeg for the MP3s.
Models (in `../models/` relative to the scripts):
- `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the kokoro-onnx GitHub release `model-files-v1.0`
- `sherpa-onnx-whisper-small` and `wespeaker_en_voxceleb_resnet34.onnx` from the sherpa-onnx GitHub releases

Each generator takes the output pack directory as its argument, e.g. `python3 gen_physical.py ../boce_na_rivi_complete_audio`.
