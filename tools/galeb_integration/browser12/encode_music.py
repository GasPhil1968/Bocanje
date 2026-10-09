"""Re-encode every music loop as AAC (same settings as the BROWSER build: mono, 32 kHz, 48 kbit/s)
with 0.5 s wrap-around padding on both ends -> gapless looping via loopStart/loopEnd.
usage: encode_music.py <out_music_dir> <loops.json> <master.wav> ..."""
import sys, os, wave, json, subprocess, numpy as np
out_dir, loops_path, masters = sys.argv[1], sys.argv[2], sys.argv[3:]
PAD_S = 0.5
loops = {}
for p in masters:
    nm = os.path.basename(p)[:-4]
    with wave.open(p) as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').reshape(-1, ch)
    pad = int(PAD_S * sr)
    y = np.concatenate([x[-pad:], x, x[:pad]])
    tmp = os.path.join(out_dir, f'_{nm}.wav')
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())
    dst = os.path.join(out_dir, nm + '.m4a')
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', tmp, '-ac', '1', '-ar', '32000',
                    '-c:a', 'aac', '-b:a', '48k', '-movflags', '+faststart', dst], check=True)
    os.remove(tmp)
    loops[nm] = [round(pad / sr, 6), round(n / sr, 6)]          # [loopStart, loop length] in seconds
    print(nm, f'{os.path.getsize(dst) / 1e3:.0f} kB', loops[nm])
json.dump(loops, open(loops_path, 'w'), indent=0)
