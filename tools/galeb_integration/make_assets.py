"""Padded-loop MP3s for music + ambience -> assets.json {id: {b64, pre, n, sr}}"""
import sys, os, wave, json, base64, subprocess, numpy as np, glob
S = sys.argv[1]; out = sys.argv[2]
PAD = 22050
jobs = []
for p in sorted(glob.glob(f'{S}/mwork/galeb_nad_jadranom_music/music/*.wav')):
    nm = os.path.basename(p)[:-4]
    jobs.append((nm, p, '96k' if nm.endswith('_layer') else '128k', 'music'))
for p in sorted(glob.glob(f'{S}/pack/galeb_nad_jadranom_complete_sfx/ambience/*.wav')):
    jobs.append((os.path.basename(p)[:-4], p, '96k', 'amb'))
res = {}
for nm, p, br, kind in jobs:
    with wave.open(p) as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').reshape(-1, ch)
    padded = np.concatenate([x[-PAD:], x, x[:PAD]])
    tmpw = f'/tmp/_pad_{nm}.wav'; tmpm = f'/tmp/_pad_{nm}.mp3'
    with wave.open(tmpw, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(padded.tobytes())
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', tmpw, '-c:a', 'libmp3lame', '-b:a', br,
                    '-map_metadata', '-1', tmpm], check=True)
    b = open(tmpm, 'rb').read()
    res[nm] = dict(kind=kind, b64=base64.b64encode(b).decode(), pre=PAD, n=n, sr=sr, bytes=len(b))
    os.remove(tmpw); os.remove(tmpm)
    print(nm, kind, br, f'{len(b)/1e6:.2f} MB', n)
json.dump(res, open(out, 'w'))
print('total MB', sum(v['bytes'] for v in res.values()) / 1e6)
