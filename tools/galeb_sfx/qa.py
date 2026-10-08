"""Automatic validation of the rendered library -> qa_results.json (+ data for AUDIO_QA_REPORT.md)."""
import os, sys, json, wave, hashlib, itertools
import numpy as np
from scipy import signal as ss
sys.path.insert(0, os.path.dirname(__file__))
import sounds
from master import loudness, true_peak

SR = 44100
REQUIRED = {
    'player': ['sfx_galeb_flap_01', 'sfx_galeb_flap_02', 'sfx_galeb_flap_03', 'sfx_galeb_call_01', 'sfx_galeb_call_02',
               'sfx_vranac_flap_01', 'sfx_vranac_flap_02', 'sfx_vranac_flap_03', 'sfx_vranac_call_01', 'sfx_vranac_call_02',
               'sfx_flight_dive', 'sfx_flight_pullup', 'sfx_flight_roll', 'sfx_flight_wingover', 'sfx_flight_glide'],
    'obstacles': ['sfx_gate_pass', 'sfx_gate_clean', 'sfx_gate_clean_streak', 'sfx_gate_nearmiss', 'sfx_gate_golden',
                  'sfx_gate_arch', 'sfx_gate_double', 'sfx_gate_triple_bonus', 'sfx_gate_tight_slowmo', 'sfx_score_tick',
                  'sfx_combo_increase', 'sfx_combo_break', 'sfx_combo_x2', 'sfx_combo_x3', 'sfx_combo_x4',
                  'sfx_fever_charge', 'sfx_fever_start', 'sfx_fever_end'],
    'collisions': ['sfx_hit_limestone', 'sfx_hit_wall', 'sfx_hit_rock', 'sfx_hit_water', 'sfx_bird_hurt', 'sfx_bird_falling',
                   'sfx_game_over', 'sfx_shield_break', 'sfx_rescue_activate', 'sfx_rescue_success'],
    'pickups': ['sfx_pickup_smokva', 'sfx_pickup_kava', 'sfx_pickup_vino', 'sfx_pickup_stit', 'sfx_pickup_duplo',
                'sfx_pickup_relic', 'sfx_pickup_passport', 'sfx_item_spawn'],
    'weather': ['sfx_weather_rain_start', 'sfx_weather_rain_end', 'sfx_weather_bura_gust_01', 'sfx_weather_bura_gust_02',
                'sfx_weather_fog_start', 'sfx_weather_fog_end', 'sfx_sea_small_splash', 'sfx_sea_wave_impact'],
    'cities': ['sfx_city_split_bell', 'sfx_city_split_harbor', 'sfx_city_dubrovnik_bell', 'sfx_city_dubrovnik_wind',
               'sfx_city_sibenik_bell', 'sfx_city_sibenik_cicadas', 'sfx_city_makarska_bura', 'sfx_city_makarska_pines',
               'sfx_city_zadar_sea_organ_01', 'sfx_city_zadar_sea_organ_02', 'sfx_city_pula_bell', 'sfx_city_pula_cicadas'],
    'props': ['sfx_prop_ferry_horn', 'sfx_prop_fishing_boat', 'sfx_prop_sailboat', 'sfx_prop_oar', 'sfx_prop_dolphin'],
    'ui': ['sfx_ui_hover', 'sfx_ui_select', 'sfx_ui_back', 'sfx_ui_start', 'sfx_ui_pause', 'sfx_ui_resume', 'sfx_ui_toggle_on',
           'sfx_ui_toggle_off', 'sfx_ui_character_select', 'sfx_ui_city_select', 'sfx_ui_difficulty_select',
           'sfx_ui_postcard_open', 'sfx_ui_postcard_export', 'sfx_ui_passport_stamp'],
    'progression': ['sfx_progress_milestone', 'sfx_progress_medal_bronze', 'sfx_progress_medal_silver',
                    'sfx_progress_medal_gold', 'sfx_progress_medal_platinum', 'sfx_progress_city_arrival',
                    'sfx_progress_city_unlocked', 'sfx_progress_relic_discovered', 'sfx_progress_mission_complete',
                    'sfx_progress_journey_complete', 'sfx_progress_new_record'],
    'ambience': ['amb_adriatic_waves_day', 'amb_adriatic_waves_evening', 'amb_adriatic_waves_bluehour', 'amb_harbor',
                 'amb_coastal_town', 'amb_cicadas', 'amb_pine_wind', 'amb_rain', 'amb_bura', 'amb_fog'],
}
# sounds heard over and over during play: stricter harshness limit
REPETITIVE = {'sfx_galeb_flap_01', 'sfx_galeb_flap_02', 'sfx_galeb_flap_03', 'sfx_vranac_flap_01', 'sfx_vranac_flap_02',
              'sfx_vranac_flap_03', 'sfx_score_tick', 'sfx_gate_pass', 'sfx_gate_clean', 'sfx_gate_clean_streak',
              'sfx_combo_increase', 'sfx_pickup_smokva', 'sfx_pickup_kava', 'sfx_ui_hover', 'sfx_ui_select'}


def rel_path(name):
    return os.path.join('ambience', name + '.wav') if name.startswith('amb_') else \
        os.path.join('sfx', next(k for k, v in REQUIRED.items() if name in v), name + '.wav')


def read(path):
    with wave.open(path) as w:
        p = dict(ch=w.getnchannels(), sw=w.getsampwidth(), sr=w.getframerate(), n=w.getnframes(), comp=w.getcomptype())
        raw = w.readframes(p['n'])
    x = np.frombuffer(raw, '<i2').astype(np.float64).reshape(-1, p['ch']) / 32768.0
    return p, x, raw


def hf_ratio(m, fc=5000):
    f, P = ss.welch(m, SR, nperseg=min(2048, len(m)))
    return float(P[f >= fc].sum() / (P.sum() + 1e-20)), float((f * P).sum() / (P.sum() + 1e-20))


def click_scan(m):
    """waveform discontinuities (the artefact behind digital clicks/pops): the error of a 3rd-order
    linear prediction at one sample is far larger than the local median error and audible in level."""
    if len(m) < 400: return []
    pred = 3 * m[2:-1] - 3 * m[1:-2] + m[:-3]
    err = np.abs(m[3:] - pred)
    w = int(0.004 * SR)
    from scipy.ndimage import median_filter, maximum_filter
    # median of the *following* 8 ms: a designed onset is followed by a body of similar texture,
    # a click/discontinuity is not
    med = median_filter(err, size=2 * w + 1, origin=-w, mode='nearest') + 1e-6
    peak = maximum_filter(np.abs(m), size=2 * w + 1, mode="nearest")[3:]
    hits = np.nonzero((err > 25 * med) & (err > 10 ** (-40 / 20)) & (err > 0.15 * peak))[0]
    out = []
    for i in hits:
        t = round((i + 3) / SR, 4)
        if not out or t - out[-1] > 0.002: out.append(float(t))
    return out


def seam(x):
    m = x.mean(1)
    steps = np.abs(np.diff(m)); wrap = abs(m[0] - m[-1])
    p999 = float(np.percentile(steps, 99.9))
    win = 2048
    def spec(seg): return np.log10(np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) + 1e-9)
    joined = np.concatenate([m[-win // 2:], m[:win // 2]])
    flux_seam = float(np.mean(np.abs(spec(joined) - spec(m[-win:]))))
    rr = np.random.default_rng(0); fl = []
    for _ in range(300):
        i = rr.integers(win, len(m) - win)
        fl.append(np.mean(np.abs(spec(m[i - win // 2:i + win // 2]) - spec(m[i - win:i]))))
    r_last = np.sqrt(np.mean(x[-SR // 10:] ** 2)); r_first = np.sqrt(np.mean(x[:SR // 10] ** 2))
    lvl = abs(20 * np.log10((r_last + 1e-12) / (r_first + 1e-12)))
    # level change across seam compared with typical 100 ms-to-100 ms change
    seg = SR // 10; k = len(m) // seg
    rms = np.sqrt((m[:k * seg].reshape(k, seg) ** 2).mean(1)) + 1e-12
    typ = float(np.percentile(np.abs(np.diff(20 * np.log10(rms))), 95))
    seam_clicks = click_scan(np.concatenate([m[-SR // 2:], m[:SR // 2]]))
    ok = wrap <= max(p999, 3e-4) and flux_seam <= np.percentile(fl, 99) and lvl <= max(typ, 1.5) \
        and not seam_clicks
    return dict(wrap_step=float(wrap), step_p999=p999, seam_flux=flux_seam, flux_p95=float(np.percentile(fl, 95)),
                flux_p99=float(np.percentile(fl, 99)), seam_flux_percentile=float((np.array(fl) < flux_seam).mean() * 100),
                seam_level_jump_db=float(lvl), typical_level_jump_db=typ, seam_clicks=seam_clicks, ok=bool(ok))


def features(m):
    f, t, S = ss.spectrogram(m, SR, nperseg=1024, noverlap=512)
    edges = np.geomspace(80, 12000, 25)
    bands = np.array([S[(f >= a) & (f < b)].sum(0) for a, b in zip(edges[:-1], edges[1:])]) + 1e-12
    spec = np.log10(bands.mean(1)); spec -= spec.mean()
    env = 10 * np.log10(bands.sum(0)); env = np.interp(np.linspace(0, 1, 32), np.linspace(0, 1, len(env)), env)
    env -= env.max()
    return spec, env


def run(root):
    res = {}; hashes = {}
    allnames = [n for v in REQUIRED.values() for n in v]
    for name in allnames:
        rp = rel_path(name); p = os.path.join(root, rp)
        meta = sounds.REG.get(name)
        r = dict(file=rp, exists=os.path.isfile(p), problems=[])
        if not r['exists'] or meta is None:
            r['problems'].append('missing'); res[name] = r; continue
        r['bytes'] = os.path.getsize(p)
        try:
            P, x, raw = read(p)
        except Exception as e:
            r['problems'].append(f'decode error {e}'); res[name] = r; continue
        hashes[name] = hashlib.sha1(raw).hexdigest()
        m = x.mean(1)
        dur = len(x) / SR
        pk = float(np.max(np.abs(x)))
        r.update(sr=P['sr'], bits=8 * P['sw'], channels=P['ch'], duration=round(dur, 3),
                 peak_dbfs=round(20 * np.log10(pk + 1e-12), 2),
                 true_peak_dbtp=round(20 * np.log10(true_peak(x if P['ch'] > 1 else m) + 1e-12), 2),
                 rms_dbfs=round(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12), 2),
                 loudness=round(loudness(x if P['ch'] > 1 else m, meta['loop']), 2), target=meta['lufs'],
                 dc=float(np.abs(x.mean(0)).max()), clipped=int(np.sum(np.abs(x) >= 32767 / 32768)),
                 first=float(np.abs(x[0]).max()), last=float(np.abs(x[-1]).max()))
        hr, cen = hf_ratio(m); r['hf_ratio_5k'] = round(hr, 4); r['centroid_hz'] = round(cen)
        r['clicks'] = click_scan(m) if not meta['loop'] else []
        lo, hi = meta['dur']
        if P['sr'] != 44100: r['problems'].append('sample rate')
        if P['sw'] != 2 or P['comp'] != 'NONE': r['problems'].append('not 16-bit PCM')
        if P['ch'] != (2 if meta['stereo'] else 1): r['problems'].append('channel layout')
        if r['bytes'] < 1000 or pk < 10 ** (-30 / 20) or r['rms_dbfs'] < -65: r['problems'].append('silent / empty')
        if not (lo - 1e-3 <= dur <= hi + 1e-3): r['problems'].append(f'duration {dur:.2f}s outside {lo}-{hi}s')
        if r['peak_dbfs'] > -3.0 or r['clipped']: r['problems'].append('peak above -3 dBFS / clipping')
        if r['dc'] > 0.002: r['problems'].append('DC offset')
        if not meta['loop'] and (r['first'] > 0.003 or r['last'] > 0.003): r['problems'].append('boundary not at zero (pop risk)')
        if r['clicks']: r['problems'].append(f'possible clicks at {r["clicks"][:5]}')
        if name in REPETITIVE and hr > 0.06: r['problems'].append(f'too bright for a repetitive sound ({hr:.1%} > 5 kHz)')
        if hr > 0.25: r['problems'].append(f'harsh top end ({hr:.1%} energy > 5 kHz)')
        if meta['loop']:
            r['seam'] = seam(x)
            if not r['seam']['ok']: r['problems'].append('loop seam not seamless')
        r['_feat'] = features(m)
        res[name] = r
    # uniqueness / distinctness
    dup = [(a, b) for a, b in itertools.combinations(hashes, 2) if hashes[a] == hashes[b]]
    for a, b in dup:
        res[a]['problems'].append(f'identical to {b}')
    groups = {}
    for name in allnames:
        if name in res and '_feat' in res[name]:
            groups.setdefault(sounds.REG[name]['category'], []).append(name)
    for cat, names in groups.items():
        for a in names:
            best, bn = 1e9, None
            for b in names:
                if a == b: continue
                sa, ea = res[a]['_feat']; sb, eb = res[b]['_feat']
                d = float(np.sqrt(np.mean((sa - sb) ** 2)) + 0.02 * np.sqrt(np.mean((ea - eb) ** 2)))
                if d < best: best, bn = d, b
            res[a]['nearest'] = bn; res[a]['nearest_dist'] = round(best, 3)
            if bn and best < 0.05: res[a]['problems'].append(f'hard to distinguish from {bn} (d={best:.3f})')
    # variation groups: waveform cross-correlation must be low
    vg = {}
    for name in allnames:
        g = sounds.REG[name]['group']
        if g: vg.setdefault(g, []).append(name)
    var = {}
    for g, names in vg.items():
        for a, b in itertools.combinations(names, 2):
            xa = read(os.path.join(root, rel_path(a)))[1].mean(1); xb = read(os.path.join(root, rel_path(b)))[1].mean(1)
            c = ss.correlate(xa, xb, 'full', method='fft')
            c = float(np.max(np.abs(c)) / (np.linalg.norm(xa) * np.linalg.norm(xb) + 1e-12))
            var[f'{a} vs {b}'] = round(c, 3)
            if c > 0.9: res[a]['problems'].append(f'variation too similar to {b} (xcorr {c:.2f})')
    for r in res.values(): r.pop('_feat', None)
    return dict(files=res, duplicates=dup, variation_xcorr=var)


if __name__ == '__main__':
    out = run(sys.argv[1])
    bad = {k: v['problems'] for k, v in out['files'].items() if v['problems']}
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
    print(f'{len(out["files"])} files checked, {len(bad)} with problems')
    for k, v in bad.items(): print(' ', k, v)
