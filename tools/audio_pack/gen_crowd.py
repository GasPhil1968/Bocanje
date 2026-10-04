"""Batch 2b: spectators - applause (procedural clap model) and reaction voices (layered Kokoro voices)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import *
from hrtts import say, asr, ipa
import meta, parselmouth
from gen_voices import KOKORO, psola_shift

B = 'crowd'
APPLAUSE_METHOD = ('procedural applause synthesis after the clapper model of Peltola et al. (2007): '
                   'each spectator has an individual hand-resonance, clap tempo, timing jitter, distance '
                   'and stereo position; outdoor stone-riva early reflections. Original code, no samples.')

# ------------------------------------------------------------------ applause
def clapper_signal(r, n, start, stop, rate, fc, q, level, swell):
    x = np.zeros(n)
    t = start
    period = 1/rate
    while t < stop:
        i = int(t*SR)
        k = int(0.03*SR)
        tt = np.arange(k)/SR
        ex = r.standard_normal(k)*np.minimum(1, tt/0.0006)*np.exp(-tt/r.uniform(0.004, 0.0075))
        c = resonator(ex, fc*r.uniform(0.95, 1.05), q*r.uniform(0.85, 1.15))*1.6
        c += 0.35*hp(ex, 2500, 1)                                 # skin 'slap' broadband
        c += 0.25*resonator(ex, fc*r.uniform(1.8, 2.4), q*1.5)
        g = level*undb(r.normal(0, 1.8))*swell(t)
        if i < n:
            m = min(k, n-i); x[i:i+m] += c[:m]*g
        t += period*r.normal(1, 0.07)
        period *= r.uniform(0.995, 1.012)                         # hands tire, tempo eases
    return x

def applause(seed, kind):
    r = rng(seed)
    P = {'light':        dict(people=7,  dur=r.uniform(1.4, 1.8), peak=-10.0),
         'enthusiastic': dict(people=10, dur=r.uniform(2.3, 2.8), peak=-6.0),
         'triumphant':   dict(people=15, dur=r.uniform(3.3, 3.8), peak=-3.5)}[kind]
    D = P['dur']; n = int((D+0.5)*SR)
    out = np.zeros((n, 2))
    for p in range(P['people']):
        rate = r.uniform(3.2, 6.0) if kind != 'light' else r.uniform(2.8, 5.0)
        start = r.uniform(0, 1/rate) + r.exponential(0.06)     # random phase + reaction delay
        stop = D*r.uniform(0.55, 1.0)
        dist = r.uniform(2.5, 9.0)
        fc = np.exp(r.uniform(np.log(650), np.log(2300))); q = r.uniform(2.0, 6.0)
        if kind == 'triumphant':
            sw = lambda t, D=D: 0.75 + 0.35*np.sin(np.pi*min(1, t/(D*0.55)))**2 * (1 - 0.4*max(0, t-D*0.7)/(D*0.3))
        else:
            sw = lambda t, D=D: max(0.25, 1 - 0.5*(t/D)**2)
        x = clapper_signal(r, n, start, stop, rate, fc, q, 1/dist, sw)
        x = lp(x, 12000 - dist*600, 1)
        out += pan(x, r.uniform(-0.75, 0.75))
    # stone riva: a few reflections, no hall
    y = np.zeros((n+int(0.08*SR), 2)); y[:n] += out
    for d, g, sw in [(0.013, 0.20, False), (0.027, 0.13, True), (0.043, 0.08, False)]:
        i = int(d*SR); s = lp(out[:, ::-1] if sw else out, 6000, 1)*g; y[i:i+n] += s
    y = shelf_hi(y, 8000, -3)
    y = dc_block(y)
    y = trim_lead(y, -40, 0.003); y = trim_tail(y, -55)
    y = fade(y, 0.002, 0.15)
    return norm_peak(y, P['peak'] + r.uniform(-0.5, 0.5))

# ------------------------------------------------------------------ crowd voices
CROWD_POOL = ['am_michael', 'am_adam', 'bm_fable', 'hm_psi', 'em_santa', 'bm_lewis',
              'af_nicole', 'bf_isabella', 'bf_emma', 'ef_dora', 'af_aoede', 'ff_siwis', 'hf_beta', 'af_sky']

def crowd_member(r):
    a, b = r.choice(len(CROWD_POOL), 2, replace=False)
    w = r.uniform(0.55, 0.85)
    return [(CROWD_POOL[a], w), (CROWD_POOL[b], 1-w)], r.uniform(0.92, 1.1)

def glide(x, sr, start=1.0, end=0.82):
    snd = parselmouth.Sound(x, sr)
    man = parselmouth.praat.call(snd, 'To Manipulation', 0.01, 60, 500)
    pt = parselmouth.praat.call(man, 'Extract pitch tier')
    # replace by a falling contour relative to the median
    pitch = snd.to_pitch(pitch_floor=60, pitch_ceiling=500).selected_array['frequency']
    med = np.median(pitch[pitch > 0]) if np.any(pitch > 0) else 150
    parselmouth.praat.call(pt, 'Remove points between', snd.xmin, snd.xmax)
    for k in range(9):
        tt = snd.xmin + (snd.xmax-snd.xmin)*k/8
        parselmouth.praat.call(pt, 'Add point', tt, med*(start + (end-start)*(k/8)**1.3))
    parselmouth.praat.call([pt, man], 'Replace pitch tier')
    return parselmouth.praat.call(man, 'Get resynthesis (overlap-add)').values[0]

def layer(r, items, length, spread=0.18, peak=-6.0, lowpass=None, gains=None, fall=None, speed=1.0):
    """items: list of (phonemes, transcript). each crowd member says one item."""
    n = int(length*SR)
    out = np.zeros((n, 2)); voices = []
    for k, (ph, tx) in enumerate(items):
        mix, sp = crowd_member(r)
        a, sr = say(tx, mix, speed=sp*speed, phon=ph)
        if fall: a = glide(a, sr, *fall)
        a = psola_shift(a, sr, r.uniform(-1.2, 1.2))
        a = resample(a, sr, SR)
        a = trim_tail(a, -40, min_len=0.1); a = trim_lead(a, -40, 0.002); a = fade(a, 0.004, 0.06)
        dist = r.uniform(1.5, 5.0)
        a = lp(a, 9000 - dist*700, 1)/dist
        if lowpass: a = lp(a, lowpass, 2)
        a *= (gains[k] if gains else 1.0)*undb(r.normal(0, 1.5))
        off = int(r.uniform(0, spread)*SR) if k else 0
        m = min(len(a), n-off)
        out[off:off+m] += pan(a[:m], r.uniform(-0.7, 0.7))
        voices.append([list(x) for x in mix])
    y = np.zeros((n+int(0.06*SR), 2)); y[:n] = out
    for d, g in [(0.014, 0.18), (0.031, 0.10)]:
        i = int(d*SR); y[i:i+n] += lp(out[:, ::-1], 5000, 1)*g
    y = dc_block(y); y = trim_lead(y, -40, 0.003); y = trim_tail(y, -50)
    y = fade(y, 0.003, 0.12)
    return norm_peak(y, peak), voices

def P(t): return ipa(t)

CROWD = {
 'ooo':  [dict(items=[('ˈuːː!', 'Uuuu!')]*5, spread=0.16, peak=-6, fall=(1.08, 0.95), speed=0.7),
          dict(items=[('ˈuːː!', 'Uuuu!')]*6, spread=0.20, peak=-5, fall=(1.0, 1.12), speed=0.66),
          dict(items=[('ˈuːː!', 'Uuuu!')]*4, spread=0.12, peak=-7, fall=(1.1, 0.9), speed=0.74)],
 'ajme': [dict(items=[(P('Ajmeee!'), 'Ajmeee!')]*4 + [(P('Ajme!'), 'Ajme!')], spread=0.15, peak=-6),
          dict(items=[(P('Ajme majko!'), 'Ajme majko!')]*2 + [(P('Ajmeee!'), 'Ajmeee!')]*2, spread=0.18, peak=-6),
          dict(items=[(P('Jooooj!'), 'Jooooj!')]*3 + [(P('Ajme!'), 'Ajme!')]*2, spread=0.15, peak=-6)],
 'bravo':[dict(items=[(P('Bravo!'), 'Bravo!')]*5, spread=0.18, peak=-6),
          dict(items=[(P('Bravo, bravo!'), 'Bravo, bravo!')]*3 + [(P('Bravo!'), 'Bravo!')]*2, spread=0.22, peak=-5),
          dict(items=[(P('To je to!'), 'To je to!')]*2 + [(P('Bravo!'), 'Bravo!')]*3, spread=0.2, peak=-6)],
 'groan':[dict(items=[('ˈoːːx…', '(nonverbal groan)')]*5, spread=0.15, peak=-8, fall=(1.0, 0.78), speed=0.75),
          dict(items=[('ˈeːːx…', '(nonverbal groan)')]*4 + [('ˈoːːx…', '(nonverbal groan)')]*2, spread=0.18, peak=-8, fall=(1.02, 0.8), speed=0.75),
          dict(items=[('ˈaːːx…', '(nonverbal groan)')]*5, spread=0.2, peak=-8.5, fall=(1.0, 0.75), speed=0.75)],
 'laugh':[dict(items=[('hˈa ha hˈaː!', 'Ha-ha-haaa!')]*4 + [('hˈɛ hɛ hɛ.', '(nonverbal chuckle)')], spread=0.3, peak=-7),
          dict(items=[('hˈa ha hˈaː!', 'Ha-ha-haaa!')]*3 + [('hˈa ha.', '(nonverbal chuckle)')]*2, spread=0.35, peak=-7),
          dict(items=[('hˈɛ hɛ hɛ.', '(nonverbal chuckle)')]*3 + [('hˈa ha hˈaː!', 'Ha-ha-haaa!')]*2, spread=0.4, peak=-8)],
}
MURMUR_LINES = ['Polako, nije utrka.', 'Pazi na vitar, nosi je.', 'Ne diraj, dobro leži.', 'Ajmo dalje.',
                'Trulo ili bulanje — to je pitanje.', 'Vidi kako je lipo more danas.', 'Šta čekamo?', 'Neka.',
                'Samo mirno, samo mirno.', 'Bacaj već jednom.', 'Iduća.', 'Ja san to već vidija prije.']

def murmur(r, k):
    lines = r.choice(MURMUR_LINES, 5, replace=False)
    items = [(ipa(t), t) for t in lines]
    y, voices = layer(r, items, r.uniform(1.4, 1.8), spread=0.35, peak=-15, lowpass=2600)
    # brief: fade the overlap into a short burst of commenting
    y = trim_lead(y[:int(min(len(y), 1.8*SR))], -36, 0.0); y = fade(y, 0.002, 0.35)
    return y, voices, list(lines)

def main():
    meta.reset(B)
    seed = 3000
    for kind in ['light', 'enthusiastic', 'triumphant']:
        for v in (1, 2):
            seed += 1; rel = f'crowd/crowd_applause_{kind}_{v:02d}.wav'
            write(rel, applause(seed, kind))
            meta.add(B, file=rel, group=f'applause_{kind}', event='spectators applaud',
                     hook='pljesak(snaga) <- slavniTrenutak, glasPublike("bravo"), stinger(), UVODI',
                     select={'light': 'snaga < 1.1', 'enthusiastic': '1.1 <= snaga < 1.7', 'triumphant': 'snaga >= 1.7'}[kind],
                     gain_db=0.0, rate=[0.97, 1.03], cooldown_ms=600, max_voices=2,
                     status='existing-trigger', method=APPLAUSE_METHOD, transcript='')
    hooks = {'ooo': 'glasPublike("ooo") <- povikPublike("Uuuu!"), valPublike("ooo") (UVODI trulo)',
             'ajme': 'glasPublike("ajme") <- povikPublike("Ajme…" / "Joo…")',
             'bravo': 'glasPublike("bravo") <- povikPublike("Bravo…"/"To je to!"), slavniTrenutak, zavrsiRundu, UVODI',
             'groan': 'glasPublike("stenjanje") <- valPublike("stenjanje") (round lost, ball out)',
             'laugh': 'glasPublike("smijeh") <- valPublike("smijeh") (ball out), povikPublike("Ha-ha…"/"Ma vidi ga!")',
             'murmur': 'glasPublike("zamor") <- povikPublike(other text), side board 30 %, valPublike("zamor") (UVODI trulo)'}
    for kind in ['ooo', 'ajme', 'bravo', 'groan', 'laugh', 'murmur']:
        for v in (1, 2, 3):
            seed += 1; r = rng(seed); rel = f'crowd/crowd_{kind}_{v:02d}.wav'
            if kind == 'murmur':
                y, voices, lines = murmur(r, v); tx = 'unintelligible overlap of: ' + ' | '.join(lines)
            else:
                spec = CROWD[kind][v-1]
                y, voices = layer(r, spec['items'], 2.2, spread=spec['spread'], peak=spec['peak'], fall=spec.get('fall'),
                                  speed=spec.get('speed', 1.0))
                tx = ' + '.join(sorted(set(t for _, t in spec['items'])))
            write(rel, y)
            heard = asr(y.mean(axis=1), SR)
            meta.add(B, file=rel, group=f'crowd_{kind}', event=f'spectator reaction: {kind}', hook=hooks[kind],
                     gain_db=0.0, rate=[0.95, 1.05], cooldown_ms=350, max_voices=2,
                     status='existing-trigger', method=KOKORO + '; small-group layering (4-7 distinct blended voices, '
                     'offsets, panning, distance, stone reflections)', transcript=tx,
                     permitted_text='USKLICI.publika lines mapped by vrstaPovika() to this group' if kind not in ('groan', 'murmur') else 'any',
                     asr_heard=heard, voices=voices)
            print(f'{rel:40s} {len(y)/SR:4.2f}s | {tx[:60]:60s} | ASR: {heard}', flush=True)

if __name__ == '__main__':
    dsp.OUT = sys.argv[1]
    main()
