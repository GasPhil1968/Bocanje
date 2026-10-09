"""Ambience loops -> AAC stereo 32 kHz 64 kbit/s, +GAIN dB, 0.5 s wrap-around padding.
usage: encode_amb.py <out_dir> <loops.json> <gain_db> <master.wav> ..."""
import sys, os, wave, json, subprocess, numpy as np
out_dir, loops_path, gain_db, masters = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4:]
loops = {}
for p in masters:
    nm = os.path.basename(p)[:-4]
    with wave.open(p) as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').reshape(-1, ch).astype(np.float64)
    g = 10 ** (gain_db / 20)
    assert np.abs(x).max() * g < 32767 * 10 ** (-3 / 20), nm          # stays below -3 dBFS
    pad = sr // 2
    y = np.concatenate([x[-pad:], x, x[:pad]]) * g
    tmp = os.path.join(out_dir, f'_{nm}.wav')
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.round(y).astype('<i2').tobytes())
    dst = os.path.join(out_dir, nm + '.m4a')
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', tmp, '-ac', '2', '-ar', '32000',
                    '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', dst], check=True)
    os.remove(tmp)
    loops[nm] = [round(pad / sr, 6), round(n / sr, 6)]
    print(nm, f'{os.path.getsize(dst) / 1e3:.0f} kB', loops[nm])
json.dump(loops, open(loops_path, 'w'))
