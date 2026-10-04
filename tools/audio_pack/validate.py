"""Technical validation of every master WAV; writes registry/validation.json."""
import sys, os, glob, json, wave, hashlib, re
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from dsp import true_peak, loop_seam_report, SR
import pyloudnorm as pyln

ROOT = sys.argv[1]
OUTJ = os.path.join(os.path.dirname(__file__), '..', 'registry', 'validation.json')

RANGES = [  # (regex, min_s, max_s, expected channels)
    (r'sfx_ball_collision', 0.15, 0.65, 1), (r'sfx_bulin_collision', 0.10, 0.40, 1),
    (r'sfx_gravel_land', 0.15, 0.65, 1), (r'sfx_gravel_roll_.*_loop', 3.0, 6.0, 1),
    (r'sfx_gravel_stop', 0.15, 0.40, 1), (r'sfx_throw_', 0.15, 0.45, 1),
    (r'sfx_wood_boundary', 0.15, 0.60, 1),
    (r'crowd_applause_light', 1.2, 2.0, 2), (r'crowd_applause_enthusiastic', 2.0, 3.0, 2),
    (r'crowd_applause_triumphant', 3.0, 4.0, 2),
    (r'crowd_laugh', 0.5, 2.2, 2), (r'crowd_', 0.5, 1.8, 2),
    (r'voice_', 0.3, 2.2, 1),
    (r'amb_.*_loop', 15.0, 30.0, 2), (r'amb_cicada', 1.5, 3.0, 2),
    (r'animal_gull_takeoff', 0.3, 1.5, 1), (r'animal_gull', 0.2, 1.6, 1), (r'animal_cat', 0.4, 1.2, 1),
    (r'ui_round', 0.2, 0.8, None), (r'ui_', 0.04, 0.25, 1),
    (r'music_match', 1.2, 2.5, 2), (r'music_trophy', 2.0, 3.5, 2), (r'music_intro', 1.2, 2.5, 2),
    (r'music_(stage|achievement)', 0.8, 1.8, 2),
]
def rng_for(name):
    for rx, a, b, ch in RANGES:
        if re.search(rx, name): return a, b, ch
    return None, None, None

def centroid(x):
    m = x if x.ndim == 1 else x.mean(1)
    S = np.abs(np.fft.rfft(m*np.hanning(len(m))))**2; f = np.fft.rfftfreq(len(m), 1/SR)
    return float(np.sum(f*S)/np.sum(S)), float(np.sum(S[f > 8000])/np.sum(S)), float(np.sum(S[f > 5000])/np.sum(S))

def main():
    files = sorted(glob.glob(os.path.join(ROOT, '**', '*.wav'), recursive=True))
    files = [f for f in files if '/previews/' not in f and '/browser/' not in f]
    meter = pyln.Meter(SR)
    res = {}
    for f in files:
        rel = os.path.relpath(f, ROOT); name = os.path.basename(f)
        info = sf.info(f); x, sr = sf.read(f, always_2d=False)
        with wave.open(f) as w:   # independent header parse
            hdr = dict(ch=w.getnchannels(), sw=w.getsampwidth(), sr=w.getframerate(), frames=w.getnframes())
        loop = name.endswith('_loop.wav')
        m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), 1)
        pk = float(m.max()); tp = true_peak(x)
        lead = int(np.argmax(m > pk*10**(-40/20)))/SR
        dc = float(np.max(np.abs(np.mean(x, axis=0))))
        edge_in = float(np.max(np.abs(x[0]))); edge_out = float(np.max(np.abs(x[-1])))
        cen, hf8, hf5 = centroid(x)
        acen = centroid(x[int(lead*SR):int(lead*SR)+int(0.03*SR)])[0] if len(x) > 0.04*SR else cen
        try: lufs = float(meter.integrated_loudness(x if len(x) > 0.41*SR else np.concatenate([x, np.zeros((int(0.42*SR),)+x.shape[1:])])))
        except Exception: lufs = None
        a, b, ch = rng_for(name)
        d = info.frames/sr
        r = dict(file=rel, duration=round(d, 4), samplerate=sr, subtype=info.subtype, bit_depth=24 if info.subtype == 'PCM_24' else 16,
                 channels=info.channels, frames=info.frames, header_ok=(hdr['sr'] == sr and hdr['ch'] == info.channels and hdr['frames'] == info.frames and hdr['sw'] == 3),
                 finite=bool(np.all(np.isfinite(x))), sample_peak_dbfs=round(20*np.log10(pk), 2), true_peak_dbtp=round(20*np.log10(tp), 2),
                 clipped_samples=int(np.sum(m >= 0.999)), dc_offset=dc, lead_silence_ms=round(lead*1000, 1),
                 first_sample=edge_in, last_sample=edge_out, lufs=None if lufs is None or not np.isfinite(lufs) else round(lufs, 1),
                 rms_dbfs=round(20*np.log10(np.sqrt(np.mean(x**2))+1e-12), 1), centroid_hz=round(cen), attack_centroid_hz=round(acen), hf_above_8k=round(hf8, 4), hf_above_5k=round(hf5, 4),
                 md5=hashlib.md5(open(f, 'rb').read()).hexdigest(), loop=loop, range=[a, b], expected_channels=ch)
        issues = []
        if not r['header_ok']: issues.append('header mismatch')
        if not r['finite']: issues.append('non-finite samples')
        if tp > 10**(-0.5/20): issues.append('true peak > -0.5 dBTP')
        if r['clipped_samples']: issues.append('clipped samples')
        if dc > 1e-3: issues.append('DC offset')
        if not loop and lead > 0.010: issues.append(f'lead silence {lead*1000:.0f} ms')
        if not loop and (edge_in > 2e-3 or edge_out > 2e-3): issues.append('edge not faded')
        if a is not None and not (a*0.98 <= d <= b*1.02): issues.append(f'duration {d:.2f}s outside suggested {a}-{b}s')
        if ch is not None and info.channels != ch: issues.append(f'channels {info.channels} (expected {ch})')
        if x.ndim > 1:
            L, R = x[:, 0], x[:, 1]
            corr = float(np.corrcoef(L, R)[0, 1])
            st = np.sqrt((np.mean(L**2)+np.mean(R**2))/2); mo = np.sqrt(np.mean(((L+R)/2)**2))
            r['lr_correlation'] = round(corr, 3); r['mono_sum_loss_db'] = round(20*np.log10(mo/st), 2)
            if corr < 0 or r['mono_sum_loss_db'] < -4.5: issues.append('mono compatibility')
        if loop:
            rep = loop_seam_report(x); r['seam'] = rep
            if not rep['ok']: issues.append('loop seam')
        if hf8 > 0.25 and 'cicada' not in name: issues.append('HF build-up (>25 % energy above 8 kHz)')
        r['issues'] = issues
        res[rel] = r
    # variants nonidentical: max normalized cross-correlation inside numbered groups
    groups = {}
    for rel in res:
        g = re.sub(r'_\d\d\.wav$', '', rel)
        if g != rel: groups.setdefault(g, []).append(rel)
    var = {}
    for g, fs in groups.items():
        sims = []
        for i in range(len(fs)):
            for j in range(i+1, len(fs)):
                a, _ = sf.read(os.path.join(ROOT, fs[i])); b, _ = sf.read(os.path.join(ROOT, fs[j]))
                a = a.mean(1) if a.ndim > 1 else a; b = b.mean(1) if b.ndim > 1 else b
                n = max(len(a), len(b)); A = np.fft.rfft(a, 2*n); Bf = np.fft.rfft(b, 2*n)
                cc = np.fft.irfft(A*np.conj(Bf)); sims.append(float(np.max(np.abs(cc))/(np.linalg.norm(a)*np.linalg.norm(b))))
                if res[fs[i]]['md5'] == res[fs[j]]['md5']: res[fs[i]]['issues'].append('identical variant')
        var[g] = dict(n=len(fs), max_xcorr=round(max(sims), 3) if sims else None)
        if sims and max(sims) > 0.95:
            for fsn in fs: res[fsn]['issues'].append('variants nearly identical')
    def stat(pattern, key):
        v = [r[key] for k, r in res.items() if re.search(pattern, k)]
        return dict(n=len(v), mean=round(float(np.mean(v)), 1), min=round(float(np.min(v)), 1), max=round(float(np.max(v)), 1))
    timbre = {g: dict(centroid=stat(p, 'centroid_hz'), attack_centroid=stat(p, 'attack_centroid_hz'), duration=stat(p, 'duration'), rms=stat(p, 'rms_dbfs'))
              for g, p in [('ball_soft', 'ball_collision_soft'), ('ball_medium', 'ball_collision_medium'), ('ball_hard', 'ball_collision_hard'),
                           ('bulin_soft', 'bulin_collision_soft'), ('bulin_hard', 'bulin_collision_hard'),
                           ('land_soft', 'gravel_land_soft'), ('land_hard', 'gravel_land_hard'),
                           ('wood_soft', 'wood_boundary_soft'), ('wood_hard', 'wood_boundary_hard'),
                           ('throw_bulanje', 'throw_bulanje'), ('throw_trulo', 'throw_trulo')]}
    json.dump(dict(files=res, variants=var, timbre=timbre), open(OUTJ, 'w'), indent=1)
    bad = {k: r['issues'] for k, r in res.items() if r['issues']}
    print(len(res), 'files;', len(bad), 'with issues')
    for k, v in bad.items(): print(' ', k, v)
    for g, t in timbre.items(): print(g, t)
    print({g: v['max_xcorr'] for g, v in var.items()})

if __name__ == '__main__':
    main()
