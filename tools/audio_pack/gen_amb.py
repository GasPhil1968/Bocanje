"""Batch 3: waterfront ambience loops, cicadas, gulls, optional cat."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import *
import meta
from hrtts import say, asr, ipa
from gen_voices import KOKORO, psola_shift

B = 'ambience'
WATER = ('procedural water synthesis: filtered-noise swells plus Minnaert/van den Doel bubble model '
         'for lapping against stone; original code, no samples')
BIO = ('procedural bioacoustic synthesis (original code, no samples): source-filter model with '
       'species-typical pitch contours, roughness and formant structure - NOT a field recording')

# ------------------------------------------------------------------ helpers
def bubble(r, f0, dur):
    n = int(dur*SR); t = np.arange(n)/SR
    rise = r.uniform(0.05, 0.25)*f0/dur          # pitch rises as the bubble nears the surface
    f = f0 + rise*t
    d = f0*0.012 + 8                              # damping ~ proportional to frequency
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-d*t)*np.minimum(1, t/0.0008)

def events_loop(total, xfade, maker, r, rate_s=(3, 7), stereo=True):
    """place events over total+xfade then wrap to a loop."""
    n = int((total+xfade)*SR); y = np.zeros((n, 2))
    t = r.uniform(0, 1)
    while t < total+xfade:
        e, p = maker(r)
        i = int(t*SR); m = min(len(e), n-i)
        y[i:i+m] += pan(e[:m], p)
        t += r.uniform(*rate_s)
    return y

# ------------------------------------------------------------------ sea
def sea_loop(seed):
    r = rng(seed); L, XF = 24.0, 3.0; n = int((L+XF)*SR)
    # 1. low swell bed, two decorrelated channels
    bed = np.stack([lp(noise(n, r, 'pink'), 380, 2), lp(noise(n, r, 'pink'), 380, 2)], 1)
    sw = np.clip(0.55 + 0.35*smooth_noise(n, 0.18, r), 0.15, 1.2)
    bed *= sw[:, None]*0.5
    # 2. lapping events: slosh + bubble trickle
    def lap(r):
        d = r.uniform(1.2, 2.6); m = int(d*SR); t = np.arange(m)/SR
        a = r.uniform(0.08, 0.2)
        env = np.minimum(1, t/a)*np.exp(-(t-a).clip(0)/r.uniform(0.35, 0.7))
        sl = bp(r.standard_normal(m), r.uniform(250, 400), r.uniform(1400, 2600))*env*r.uniform(0.5, 1)
        tr = np.zeros(m)
        for _ in range(int(r.uniform(40, 120))):
            tb = a + r.exponential(0.35)
            if tb > d-0.05: continue
            rad = r.lognormal(np.log(0.0025), 0.5)            # bubble radius (m)
            f0 = np.clip(3.26/rad, 400, 4500)                  # Minnaert
            b = bubble(r, f0, r.uniform(0.02, 0.06))*r.uniform(0.02, 0.09)*np.exp(-(tb-a)/0.5)
            i = int(tb*SR); k = min(len(b), m-i); tr[i:i+k] += b[:k]
        thud = lp(r.standard_normal(m), 160, 2)*env*0.6       # water mass meeting the stone
        return fade(sl*0.6 + tr*1.6 + thud, 0.01, 0.2), r.uniform(-0.8, 0.8)
    laps = events_loop(L, XF, lap, r, (1.6, 4.2))
    # 3. faint far shimmer
    sh = np.stack([hp(noise(n, r), 2500, 2), hp(noise(n, r), 2500, 2)], 1)
    sh *= np.clip(0.5+0.4*smooth_noise(n, 0.3, r), 0.05, 1)[:, None]*0.012
    y = bed + laps + sh
    y = shelf_hi(y, 7000, -4); y = dc_block(y)
    y = make_loop(y, XF)
    return norm_peak(y, -16.0)

# ------------------------------------------------------------------ wind
def wind_loop(seed):
    r = rng(seed); L, XF = 24.0, 3.0; n = int((L+XF)*SR)
    gust = np.clip(0.6 + 0.3*smooth_noise(n, 0.12, r) + 0.15*smooth_noise(n, 0.6, r), 0.1, 1.4)
    out = np.zeros((n, 2))
    for c in range(2):
        w = noise(n, r, 'pink')
        # time-varying band: brighter in gusts (process in short blocks, overlap-add)
        blk = int(0.25*SR); hop = blk//2; win = np.hanning(blk)
        y = np.zeros(n)
        for s in range(0, n-blk, hop):
            g = gust[s+blk//2]
            seg = w[s:s+blk]
            lo, hi = 180 + 160*g, 650 + 900*g
            y[s:s+blk] += bp(seg, lo, hi, 1)*win
        y *= gust
        # foliage / palm-frond rustle rides on the gusts
        rus = hp(noise(n, r), 2200, 2)*np.clip(gust-0.55, 0, None)**1.5*0.25
        out[:, c] = y + rus
    out = shelf_hi(out, 6000, -3); out = dc_block(out)
    out = make_loop(out, XF)
    return norm_peak(out, -18.0)

# ------------------------------------------------------------------ distant cafe
CAFE_LINES = ['Danas je vrućina, moj brate.', 'More je danas mirno ka ulje.', 'Vidi kako je lipo more danas.',
              'Sinoć nisan spava od komaraca.', 'Kad završimo, idemo na bevandu.', 'Poslije ovoga jedna gemišt.',
              'Nemoj mi reć da si opet gladan.', 'Doma me čeka ručak, žena me čeka.', 'Moja žena kaže da previše boćan.',
              'Znaš da san ja jednom igra na Visu?', 'Fjaka me uvatila, brate.', 'Danas mi se ništa ne da.',
              'Na Visu se drugačije igra.', 'Hvar je za ljepotu, ovo je za živce.', 'Ajmo, sunce zalazi.',
              'Bolje od ništa, a ništa nije.', 'Ja san to već vidija prije.', 'Polako, nije utrka.']
POOL = ['am_michael', 'am_adam', 'bm_fable', 'hm_psi', 'em_santa', 'bm_lewis', 'am_eric', 'pm_alex',
        'af_nicole', 'bf_isabella', 'bf_emma', 'ef_dora', 'af_aoede', 'ff_siwis', 'hf_beta', 'af_sky', 'if_sara']

def cup_clink(r):
    m = int(0.25*SR)
    modes = [(r.uniform(2400, 3400)*q, a, t, 0) for q, a, t in [(1, 1, 0.12), (2.3, 0.5, 0.07), (3.9, 0.25, 0.04)]]
    return conv(hertz_pulse(0.0002), modal(modes, m))[:m]

def cafe_loop(seed):
    r = rng(seed); L, XF = 26.0, 3.0; n = int((L+XF)*SR)
    y = np.zeros((n, 2))
    # each "table": a talker who chats in turns
    tables = 14
    for k in range(tables):
        a, b = r.choice(len(POOL), 2, replace=False); w = r.uniform(0.6, 0.9)
        mix = [(POOL[a], w), (POOL[b], 1-w)]
        p = r.uniform(-0.9, 0.9); dist = r.uniform(6, 16)
        t = r.uniform(0, 3)
        while t < L+XF:
            line = CAFE_LINES[r.integers(len(CAFE_LINES))]
            s, sr = say(line, mix, speed=r.uniform(0.95, 1.12))
            s = resample(s, sr, SR)
            s = lp(s, 1500 - dist*30, 3)/dist
            i = int(t*SR); m = min(len(s), n-i)
            y[i:i+m] += pan(s[:m], p)
            t += len(s)/SR + r.uniform(0.6, 4.0)
    # occasional cups and spoons, far away
    t = r.uniform(0, 2)
    while t < L+XF:
        c = cup_clink(r)*r.uniform(0.004, 0.012)
        i = int(t*SR); m = min(len(c), n-i); y[i:i+m] += pan(c[:m], r.uniform(-0.8, 0.8))
        t += r.uniform(1.2, 4.5)
    # distance: diffuse tail
    m = int(0.7*SR); tt = np.arange(m)/SR
    shared = r.standard_normal(m)
    dry = y.copy()
    for c in range(2):
        ir = (0.75*shared + 0.66*r.standard_normal(m))*np.exp(-6.91*tt/0.7)   # partly shared: mono-safe
        ir = lp(ir, 3000); ir /= np.sqrt(np.sum(ir**2))
        y[:, c] = 0.3*dry[:, c] + 1.0*ss_conv(dry.mean(1), ir)[:n]
    y = dc_block(y); y = make_loop(y, XF)
    return norm_peak(y, -22.0)

def ss_conv(x, h):
    from scipy.signal import fftconvolve
    return fftconvolve(x, h)

# ------------------------------------------------------------------ cicadas
def cicada_individual(r, dur, rate, fc, echeme_hz, depth, n):
    """tymbal click train with echeme amplitude pattern."""
    t = np.arange(n)/SR
    clicks = np.zeros(n)
    tt = 0.0
    while tt < dur:
        i = int(tt*SR)
        if i < n: clicks[i] = r.uniform(0.6, 1.0)
        tt += (1/rate)*r.normal(1, 0.04)
    body = resonator(clicks, fc, r.uniform(7, 12)) + 0.4*resonator(clicks, fc*r.uniform(1.45, 1.6), 10)
    ech = 1 - depth*(0.5+0.5*np.sign(np.sin(2*np.pi*echeme_hz*t + r.uniform(0, 6))))*0.9
    ech = onepole_lp(ech, 60)
    return body*ech

def cicada_phrase(seed):
    r = rng(seed)
    dur = r.uniform(1.8, 2.8); n = int((dur+0.3)*SR); t = np.arange(n)/SR
    y = np.zeros((n, 2))
    k = 3
    for j in range(k):
        main = j == 0
        on = r.uniform(0, 0.25) if not main else 0
        d = dur - on - r.uniform(0, 0.3)
        x = cicada_individual(r, d, r.uniform(220, 420), r.uniform(4300, 6200),
                              r.uniform(4, 9) if r.uniform() < 0.6 else r.uniform(18, 30),
                              r.uniform(0.3, 0.8), n)
        ramp = np.clip((t-on)/r.uniform(0.25, 0.5), 0, 1)**1.5
        if main: ramp = 0.3 + 0.7*ramp                    # the nearest cicada is already singing
        env = ramp * np.clip((on+d - t)/r.uniform(0.3, 0.6), 0, 1)
        x = x*env*(1.0 if main else r.uniform(0.25, 0.5))
        if not main: x = lp(x, 6000, 1)
        y += pan(x, r.uniform(-0.6, 0.6))
    y = hp(y, 2500, 2); y = shelf_hi(y, 9000, -6)
    y = dc_block(y); y = trim_lead(y, -40, 0.002); y = fade(y, 0.006, 0.25)
    return norm_peak(y, -20.0 + r.uniform(-1, 1))

# ------------------------------------------------------------------ gull
def harmonic_voice(r, f0, amps_fn, n, jitter=0.015, sub=0.0, shimmer=0.08):
    t = np.arange(n)/SR
    jit = 1 + jitter*smooth_noise(n, 40, r)
    ph = 2*np.pi*np.cumsum(f0*jit)/SR
    y = np.zeros(n)
    for h in range(1, 14):
        fh = f0*h
        a = amps_fn(fh)*(fh < SR/2*0.9)
        y += a*np.sin(h*ph + r.uniform(0, 6))
    if sub > 0:   # period-doubling roughness typical of gull calls
        for h in range(1, 14, 2):
            y += sub*amps_fn(f0*h/2)*np.sin(h*ph/2 + r.uniform(0, 6))
    y *= 1 + shimmer*smooth_noise(n, 30, r)
    return y

def gull_note(r, dur, f_start, f_peak, f_end, harsh=0.0, peak_pos=0.25):
    n = int(dur*SR); u = np.linspace(0, 1, n)
    f0 = np.where(u < peak_pos, f_start + (f_peak-f_start)*np.sin(np.pi/2*u/peak_pos),
                  f_peak + (f_end-f_peak)*(np.clip(u-peak_pos, 0, None)/(1-peak_pos))**0.8)
    spec = lambda f: np.exp(-((np.log(f)-np.log(1700))**2)/0.9) + 0.5*np.exp(-((np.log(f)-np.log(3300))**2)/0.3)
    y = harmonic_voice(r, f0, spec, n, jitter=0.012+0.02*harsh, sub=0.25*harsh+0.05)
    nz = bp(r.standard_normal(n), 1200, 4500)*(0.05 + 0.25*harsh)
    env = np.minimum(1, u/0.06)**0.7 * np.minimum(1, (1-u)/0.35)**1.2
    y = (y/np.max(np.abs(y)) + nz)*env
    y = peaking(y, 1300, 5, 2); y = peaking(y, 2700, 3, 2)     # nasal 'kyow' resonances
    return y

def gull_call(seed, startled):
    r = rng(seed)
    if not startled:   # 'kyow' - one or two long notes, relaxed
        notes = []
        for k in range(r.integers(1, 3)):
            notes.append((gull_note(r, r.uniform(0.32, 0.48), r.uniform(520, 620), r.uniform(820, 980),
                                    r.uniform(560, 650), harsh=r.uniform(0.0, 0.25), peak_pos=r.uniform(0.18, 0.3)),
                          r.uniform(0.18, 0.32)))
    else:              # alarm 'ga-ga-ga' - short, harsher, higher, ~190 ms apart (as galebZvuk(true))
        notes = [(gull_note(r, r.uniform(0.10, 0.15), r.uniform(700, 800), r.uniform(950, 1100),
                            r.uniform(760, 860), harsh=r.uniform(0.5, 0.85), peak_pos=0.3), r.uniform(0.05, 0.08))
                 for _ in range(r.integers(3, 6))]
    out = np.zeros(int(3*SR)); t = 0.0
    for y, gap in notes:
        i = int(t*SR); out[i:i+len(y)] += y*r.uniform(0.75, 1.0); t += len(y)/SR + gap
    out = out[:int((t+0.15)*SR)]
    out = lp(out, 9000, 2)
    # outdoor: one faint stone reflection
    d = int(0.022*SR); out2 = out.copy(); out2[d:] += 0.12*lp(out[:-d], 4000)
    return finish(out2, (-8.0 if startled else -12.0) + r.uniform(-0.6, 0.4), fin=0.003, fout=0.06, tail_db=-55)

def gull_wings(seed):
    r = rng(seed)
    flaps = r.integers(6, 9); n = int(1.6*SR); y = np.zeros(n)
    t = 0.0; gap = r.uniform(0.085, 0.11)
    for k in range(flaps):
        m = int(r.uniform(0.07, 0.11)*SR); tt = np.arange(m)/SR
        env = np.sin(np.pi*tt/tt[-1])**2
        down = bp(noise(m, r, 'pink'), 120, 1100, 2)*env
        feathers = hp(r.standard_normal(m), 2500, 2)*env*np.clip(1+smooth_noise(m, 200, r), 0, None)*0.12
        f = (down + feathers)
        g = min(1, (k+1)/2.0)*(0.92**k)                     # strongest at lift-off, then away
        i = int(t*SR); mm = min(m, n-i); y[i:i+mm] += f[:mm]*g
        t += gap; gap *= r.uniform(1.05, 1.12)
    # take-off scrabble: claws/feet on the stone
    sc = np.zeros(n); sc[:int(0.06*SR)] = hp(r.standard_normal(int(0.06*SR)), 3000)*0.05
    y += sc
    y = y[:int((t+0.1)*SR)]
    y = dc_block(y); y = fade(y, 0.003, 0.08)
    return norm_peak(y, -9.0 + r.uniform(-0.5, 0.5))

# ------------------------------------------------------------------ cat (optional)
def meow(seed):
    r = rng(seed)
    dur = r.uniform(0.6, 0.85); n = int(dur*SR); u = np.linspace(0, 1, n)
    f0 = 520 + 230*np.sin(np.pi*np.clip(u/0.75, 0, 1))**1.2 - 60*u
    f0 *= 1 + 0.01*np.sin(2*np.pi*6*u*dur)
    # glottal-ish source: harmonics with -10 dB/oct tilt
    src = harmonic_voice(r, f0, lambda f: (f/500.0)**-1.6, n, jitter=0.006, sub=0.0, shimmer=0.05)
    src += 0.04*r.standard_normal(n)
    # formant trajectory m-i-a-u
    F1 = 400 + 550*np.sin(np.pi*np.clip((u-0.1)/0.7, 0, 1)); F2 = 1700 + 300*np.sin(np.pi*u) - 500*u**2
    blk = 512; y = np.zeros(n); win = np.hanning(blk); hopn = blk//2
    for s in range(0, n-blk, hopn):
        seg = src[s:s+blk]; c = s+blk//2
        z = resonator(seg, F1[c], 4)*1.0 + resonator(seg, F2[c], 8)*0.6 + resonator(seg, 3200, 10)*0.25
        y[s:s+blk] += z*win
    env = np.minimum(1, u/0.12)**1.5*np.minimum(1, (1-u)/0.3)
    nasal = np.where(u < 0.12, 0.35, 1.0)
    y = lp(y*env*onepole_lp(nasal, 30), 7000, 2)
    return finish(y, -14.0 + r.uniform(-0.6, 0.4), fin=0.01, fout=0.08)

# ------------------------------------------------------------------ run
def main():
    meta.reset(B)
    seed = 5000
    loops = [('ambience/amb_sea_gentle_loop.wav', sea_loop, 'sea / gentle lapping on the stone riva',
              'sagradiZvuk() zvuk.more bed; postaviAmbijent(M) sets level; utisajAmbijent() fades', WATER),
             ('ambience/amb_wind_maestral_loop.wav', wind_loop, 'maestral wind (level per M.vjetar)',
              'sagradiZvuk() zvuk.vitar bed; postaviAmbijent(M) sets level (night x1.35); utisajAmbijent()',
              'procedural wind synthesis: gust-modulated band-passed noise + foliage rustle; original code'),
             ('ambience/amb_cafe_distant_loop.wav', cafe_loop, 'distant cafe conversation',
              'zamor() (intermittent, zalazak/vecer) -> continuous low layer or faded segments; see mix_presets',
              KOKORO + '; 14 distant talkers overlapped, low-passed ~1.1-1.3 kHz, diffuse tail; cup clinks procedural')]
    for rel, fn, ev, hook, method in loops:
        seed += 1; y = fn(seed); write(rel, y)
        rep = loop_seam_report(y)
        meta.add(B, file=rel, group=os.path.basename(rel)[:-9], event=ev, hook=hook, gain_db=0.0, rate=[1.0, 1.0],
                 cooldown_ms=0, max_voices=1, status='existing-trigger' if 'cafe' not in rel else 'existing-trigger (zamor) / routing choice',
                 method=method, loop={'start': 0, 'end': len(y)}, seam=rep, transcript='')
        print(rel, round(len(y)/SR, 2), rep, flush=True)
        if 'cafe' in rel:
            heard = [asr(y[int(s*SR):int((s+6)*SR)].mean(1)*8, SR) for s in range(0, 24, 6)]
            print('  cafe ASR windows:', heard)
            meta.add(B, file='__cafe_asr__', asr_windows=heard)
    for v in (1, 2, 3):
        seed += 1; rel = f'ambience/amb_cicada_{v:02d}.wav'; write(rel, cicada_phrase(seed))
        meta.add(B, file=rel, group='cicada', event='cicada phrase (noon / afternoon)',
                 hook='cvrcak() <- korakAmbijenta() every 4-11 s when dobaSad() is podne/popodne; UVODI fjaka',
                 gain_db=0.0, rate=[0.95, 1.05], cooldown_ms=3000, max_voices=2, status='existing-trigger',
                 method=BIO + ' (tymbal click trains, echeme modulation, 3 individuals)', transcript='')
    for v in (1, 2, 3):
        seed += 1; rel = f'animals/gull/animal_gull_calm_{v:02d}.wav'; write(rel, gull_call(seed, False))
        meta.add(B, file=rel, group='gull_calm', event='gull arrives / calls', hook='galebZvuk(false) <- korakAmbijenta(), UVODI jutro',
                 gain_db=0.0, rate=[0.95, 1.06], cooldown_ms=4000, max_voices=1, status='existing-trigger', method=BIO, transcript='')
    for v in (1, 2, 3):
        seed += 1; rel = f'animals/gull/animal_gull_startled_{v:02d}.wav'; write(rel, gull_call(seed, True))
        meta.add(B, file=rel, group='gull_startled', event='gull startled by a throw', hook='galebZvuk(true) <- otjerajGaleba() in baci(); UVODI maestral',
                 gain_db=0.0, rate=[0.95, 1.06], cooldown_ms=4000, max_voices=1, status='existing-trigger', method=BIO, transcript='')
    for v in (1, 2):
        seed += 1; rel = f'animals/gull/animal_gull_takeoff_wings_{v:02d}.wav'; write(rel, gull_wings(seed))
        meta.add(B, file=rel, group='gull_wings', event='gull takes off', hook='galebZvuk(true) wing-beat part (currently 5x sumniPrasak at 95 ms)',
                 gain_db=-2.0, rate=[0.95, 1.05], cooldown_ms=4000, max_voices=1, status='existing-trigger',
                 method='procedural wing-beat synthesis (pink-noise flaps + feather rustle); original code', transcript='')
    for v in (1, 2):
        seed += 1; rel = f'animals/cat/animal_cat_meow_{v:02d}.wav'; write(rel, meow(seed))
        meta.add(B, file=rel, group='cat_meow', event='OPTIONAL: cat on the dry-stone wall meows rarely',
                 hook='none - ambijent.macak* has movement only (korakAmbijenta); needs a new infrequent trigger',
                 gain_db=-4.0, rate=[0.95, 1.05], cooldown_ms=60000, max_voices=1,
                 status='optional-new-trigger', method=BIO, transcript='', optional=True)

if __name__ == '__main__':
    dsp.OUT = sys.argv[1]
    main()
