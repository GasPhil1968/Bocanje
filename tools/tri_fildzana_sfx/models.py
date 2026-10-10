"""Physical / source-filter models used to render the TRI FILDŽANA SFX.
Every sound in the pack is synthesized from these models - nothing here is a recording."""
import numpy as np
from scipy import signal as ss
from core import *

# ======================================================================= ceramics
CUP_RATIOS = [1.0, 2.83, 5.43, 8.8, 12.9]      # thin ring (n=2..6) bending modes


def cup_modes(r, f0, t60, bright=0.7, split=0.007):
    """handle-less porcelain fildžan; each ring mode is a slightly split pair (beating)."""
    out = []
    for k, q in enumerate(CUP_RATIOS):
        f = f0 * q * (1 + r.normal(0, 0.008))
        if f > 17000:
            break
        a = (bright ** k) * (1.0 if k == 0 else 0.8)
        tk = t60 / (1 + 0.45 * k)
        d = split * (0.6 + r.random())
        out += [(f * (1 - d / 2), a * 0.55, tk, r.random() * 6), (f * (1 + d / 2), a * 0.45, tk * 0.85, r.random() * 6)]
    return out


def cup_hit(r, f0=2300, t60=0.12, contact=0.0006, bright=0.7, length=0.4):
    """ceramic response to a contact pulse of given duration (longer = softer, fewer highs)"""
    ir = modal(cup_modes(r, f0, t60, bright), N(length))
    return conv(pulse(contact), ir)[:len(ir)]


# ======================================================================= wood
TABLE = [(92, 1.0, 0.10), (141, 0.85, 0.08), (205, 0.75, 0.07), (298, 0.6, 0.055), (430, 0.5, 0.045),
         (615, 0.38, 0.04), (870, 0.28, 0.03), (1230, 0.2, 0.025), (1750, 0.13, 0.02), (2500, 0.08, 0.015)]


def wood_ir(r, modes=TABLE, scale=1.0, damp=1.0, length=0.35, knock=0.35, knock_band=(350, 2600)):
    ms = [(f * scale * (1 + r.normal(0, 0.03)), a * (1 + r.normal(0, 0.15)), t * damp, r.random() * 6) for f, a, t in modes]
    ir = modal(ms, N(length))
    k = bp(r.standard_normal(N(length)), *knock_band) * np.exp(-tax(N(length)) / 0.006)
    return ir + knock * k / (np.max(np.abs(k)) + 1e-9) * np.max(np.abs(ir))


def wood_hit(r, contact=0.003, **kw):
    ir = wood_ir(r, **kw)
    return conv(pulse(contact), ir)[:len(ir)]


def hardwood_ir(r, f=(820, 1490, 2210, 3050, 4180, 5600, 7300), t60=0.035, length=0.12):
    ms = [(fi * (1 + r.normal(0, 0.02)), 1 / (1 + 0.3 * k), t60 / (1 + 0.15 * k), r.random() * 6) for k, fi in enumerate(f)]
    return modal(ms, N(length))


# ======================================================================= cloth / friction / air
def cloth_puff(r, dur=0.03, band=(300, 3500), decay=0.008):
    n = N(dur)
    return bp(r.standard_normal(n), *band) * np.exp(-tax(n) / decay)


def friction(r, dur, speed_env, band=(350, 3800), grain_rate=600, grain_band=(1500, 5500), rough=0.55, grains=0.5):
    """dry sliding friction of a cup on a cloth-covered table"""
    n = N(dur)
    v = speed_env(tax(n) / dur) if callable(speed_env) else speed_env
    base = bp(r.standard_normal(n), *band, o=2)
    base *= 1 + rough * smooth(n, 90, r)                 # fabric weave irregularity
    g = np.zeros(n)
    ev = r.random(n) < (grain_rate / SR) * np.clip(v, 0, None)
    g[ev] = r.standard_normal(ev.sum()) * (0.4 + r.random(ev.sum()))
    g = bp(g, *grain_band)
    y = (base * 0.6 + grains * g * 3) * v
    return lp(y, band[1] * 1.2)


def fabric_rustle(r, dur, env, band=(400, 6000), crumple=0.6, crumple_rate=250, flutter=0.0, flutter_hz=28):
    n = N(dur)
    e = env(tax(n) / dur) if callable(env) else env
    s = bp(noise(n, r, 'pink'), *band)
    s *= 1 + 0.5 * smooth(n, 40, r)
    c = np.zeros(n)
    ev = r.random(n) < crumple_rate / SR * np.clip(e * 1.5, 0, 1)
    c[ev] = r.standard_normal(ev.sum()) * r.pareto(2.5, ev.sum())
    c = bp(c, 900, 7000)
    c = ss.lfilter([1], [1, -0.6], c)
    y = (s + crumple * c * 2) * e
    if flutter:
        fm = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(flutter_hz * (1 + 0.25 * smooth(n, 8, r))) / SR)
        y *= (1 - flutter) + flutter * fm ** 2
    return y


def swoosh(r, dur, f_from, f_to, q=0.8, env_pts_=((0, 0), (0.45, 1), (1, 0)), color='pink', flutter=0.0):
    n = N(dur)
    e = env_pts(n, [(p * dur, v) for p, v in env_pts_])
    k = np.linspace(0, 1, n)
    f = f_from * (f_to / f_from) ** k
    s = tv_filter(noise(n, r, color), f, q)
    if flutter:
        s *= 1 - flutter + flutter * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(30 + 10 * smooth(n, 6, r)) / SR))
    return s * e


# ======================================================================= paper
def paper_crackle(r, dur, env, rate=900, band=(1200, 9000), body=(500, 2500), body_amt=0.4, res=None):
    n = N(dur)
    e = env(tax(n) / dur) if callable(env) else env
    c = np.zeros(n)
    ev = r.random(n) < rate / SR * np.clip(e, 0, 1)
    c[ev] = r.standard_normal(ev.sum()) * r.pareto(1.8, ev.sum())
    c = bp(c, *band)
    if res:
        c = sum(resonator(c, f, 6) for f in res) + c
    s = bp(noise(n, r, 'pink'), *body) * e * body_amt
    return c * np.sqrt(np.clip(e, 0, None)) + s


def note_flick(r, scale=1.0):
    """thumb flicking one banknote while counting"""
    d = 0.07
    s = paper_crackle(r, d, lambda u: np.exp(-u * 4) * (u < 0.9), rate=3500, band=(1400, 9000),
                      body=(700, 3500), body_amt=0.6, res=[r.uniform(2400, 3600)])
    snap = bp(r.standard_normal(N(0.004)), 1500, 8000) * np.exp(-tax(N(0.004)) / 0.0008) * 3
    out = np.zeros(N(0.1))
    place(out, s, 0); place(out, snap, 0.004 + r.random() * 0.01)
    return out * scale


# ======================================================================= coins
COIN_RATIOS = [1.0, 1.47, 2.09, 2.39, 2.84, 3.6, 4.1, 5.2]


def coin_ir(r, f0, t60, length=0.8, bright=0.85):
    ms = [(f0 * q * (1 + r.normal(0, 0.01)), (bright ** k) * (0.6 + 0.4 * r.random()), t60 / (1 + 0.25 * k), r.random() * 6)
          for k, q in enumerate(COIN_RATIOS)]
    return modal(ms, N(length))


def coin_hit(r, f0=None, t60=0.25, contact=0.00015, gain=1.0, on_cloth=False):
    f0 = f0 or r.uniform(2700, 4300)
    if on_cloth:
        t60 *= 0.25; contact *= 3
    ir = coin_ir(r, f0, t60, length=max(0.05, t60 * 1.3))
    h = conv(pulse(contact), ir)[:len(ir)]
    tick = hp(r.standard_normal(N(0.002)), 3000) * np.exp(-tax(N(0.002)) / 0.0004) * 0.004
    place(h, tick, 0)
    return h * gain


def coin_drop(r, on='cloth', bounces=3, e=0.45, h0=0.05, gain=1.0, f0=None):
    """single coin dropped: bounce series with shrinking intervals; last contact is a short settle"""
    f0 = f0 or r.uniform(2700, 4300)
    t = 0.0; dt = h0; out = np.zeros(N(0.9)); amp = 1.0
    for k in range(bounces):
        cl = (on == 'cloth')
        place(out, coin_hit(r, f0 * (1 + r.normal(0, 0.004)), t60=0.3 if not cl else 0.25, on_cloth=cl, gain=amp), t)
        if on == 'cloth':
            place(out, wood_hit(r, contact=0.002, scale=2.2, damp=0.5, length=0.08) * amp * 0.08, t)
        t += dt; dt *= e; amp *= 0.55
    return out * gain


# ======================================================================= strings (Karplus-Strong family)
SAZ_BODY = [(185, 1.0, 0.05), (280, 0.8, 0.045), (430, 0.6, 0.035), (620, 0.5, 0.03), (900, 0.42, 0.025),
            (1320, 0.35, 0.02), (1950, 0.3, 0.015), (2750, 0.24, 0.012), (3650, 0.18, 0.01)]
BASS_BODY = [(68, 1.0, 0.09), (110, 0.9, 0.08), (175, 0.7, 0.06), (260, 0.55, 0.05), (390, 0.4, 0.04),
             (600, 0.3, 0.03), (900, 0.2, 0.02)]


def body_ir(r, modes=SAZ_BODY, length=0.25, direct=0.5):
    ir = modal([(f * (1 + r.normal(0, 0.02)), a, t, r.random() * 6) for f, a, t in modes], N(length))
    ir /= np.max(np.abs(ir)) + 1e-9
    ir[0] += direct
    return ir


def string_track(dur, events, r, t60=1.4, S=0.42, ap=-0.25, body=SAZ_BODY, body_mix=0.65, pick_bright=0.75):
    """One plucked string. events: dicts with t, f, vel(=1), glide(=0, s), off(None or s after t),
    pos(pluck position 0..0.5), mute(T60 after off). Re-plucks inject into the running loop,
    glides retune the loop (left-hand slides)."""
    n = N(dur)
    ev = sorted([dict(e, t=max(0.0, e['t'])) for e in events], key=lambda e: e['t'])
    f = np.empty(n); T = np.full(n, t60); exc = np.zeros(n)
    cur = ev[0]['f']; f[:] = cur
    for j, e in enumerate(ev):
        i0 = N(e['t']); i1 = N(ev[j + 1]['t']) if j + 1 < len(ev) else n
        g = e.get('glide', 0.0)
        seg = np.full(i1 - i0, float(e['f']))
        if g > 0:
            k = min(len(seg), N(g))
            seg[:k] = cur * (e['f'] / cur) ** (np.linspace(0, 1, k) ** 0.7)
        f[i0:i1] = seg; cur = e['f']
        if e.get('off') is not None:
            T[i0 + N(e['off']):i1] = e.get('mute', 0.09)
        if e.get('vel', 1.0) > 0:
            P = int(SR / e['f'])
            x = r.standard_normal(P) * e.get('vel', 1.0)
            x = lp(x, 900 + 7000 * pick_bright * e.get('vel', 1.0))
            pp = max(1, int(P * e.get('pos', 0.16)))
            x = x - np.concatenate([np.zeros(pp), x[:-pp]])
            m = min(P, n - i0)
            exc[i0:i0 + m] += x[:m]
    # loop
    L = 4096; buf = [0.0] * L; w = 0
    y = np.zeros(n); prev = 0.0; apx = 0.0; apy = 0.0
    a = ap; apd = (1 - a) / (1 + a)          # low-freq delay of the dispersion allpass
    Tl = T.tolist(); fl = f.tolist(); el = exc.tolist()
    for i in range(n):
        D = SR / fl[i] - S - apd - 1.0
        g = 10 ** (-3.0 / (fl[i] * Tl[i]))
        di = int(D); fr = D - di
        # 3rd-order Lagrange read
        i0 = (w - di) & (L - 1)
        xm1 = buf[(i0 + 1) & (L - 1)]; x0 = buf[i0]; x1 = buf[(i0 - 1) & (L - 1)]; x2 = buf[(i0 - 2) & (L - 1)]
        d = fr
        v = (-d * (d - 1) * (d - 2) / 6) * xm1 + ((d + 1) * (d - 1) * (d - 2) / 2) * x0 \
            + (-(d + 1) * d * (d - 2) / 2) * x1 + ((d + 1) * d * (d - 1) / 6) * x2
        lpv = (1 - S) * v + S * prev; prev = v
        apo = a * lpv + apx - a * apy; apx = lpv; apy = apo
        out = g * apo + el[i]
        w = (w + 1) & (L - 1)
        buf[w] = out
        y[i] = out
    if body is not None:
        b = conv(y, body_ir(r, body))[:n]
        y = (1 - body_mix) * y / (np.max(np.abs(y)) + 1e-9) + body_mix * b / (np.max(np.abs(b)) + 1e-9)
    return y


def pluck(r, f, dur=1.0, vel=1.0, off=None, mute=0.09, pos=0.16, **kw):
    return string_track(dur, [dict(t=0, f=f, vel=vel, off=off, mute=mute, pos=pos)], r, **kw)


def tremolo(t0, f, dur, rate=16, vel=0.8, jitter=0.004, r=None, decresc=0.0, pos=0.14):
    """repeated picking on one note -> event list"""
    evs = []; k = 0; t = t0
    while t < t0 + dur:
        evs.append(dict(t=t + (r.normal(0, jitter) if r is not None else 0), f=f,
                        vel=vel * (1 - decresc * (t - t0) / dur) * (0.85 if k % 2 else 1.0), pos=pos + 0.03 * (k % 2)))
        t += 1 / rate; k += 1
    return evs


# Notes (Hz) – a D-based hijaz-flavoured palette for original motifs
NOTE = dict(A2=110.0, D3=146.83, Eb3=155.56, F3s=185.0, G3=196.0, A3=220.0, Bb3=233.08, C4=261.63, D4=293.66,
            Eb4=311.13, F4s=369.99, G4=392.0, A4=440.0, Bb4=466.16, C5=523.25, D5=587.33, Eb5=622.25,
            F5s=739.99, G5=783.99, A5=880.0, D2=73.42, A1=55.0, E5=659.26, E6=1318.5, B4=493.88, C5s=554.37)


# ======================================================================= percussion
MEMBRANE = [1.0, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.6, 4.06]


def drum(r, f0=95, kind='dum', t60=0.35, length=0.8, drop=0.05, slap=0.0):
    n = N(length); t = tax(n)
    y = np.zeros(n)
    amps = [1, 0.5, 0.35, 0.25, 0.2, 0.15, 0.12, 0.1, 0.08, 0.06] if kind == 'dum' else \
           [0.35, 0.8, 0.7, 0.5, 0.6, 0.45, 0.4, 0.35, 0.3, 0.25]
    bend = 1 + drop * np.exp(-t / 0.035)
    for k, (q, a) in enumerate(zip(MEMBRANE, amps)):
        ph = 2 * np.pi * np.cumsum(f0 * q * bend * (1 + r.normal(0, 0.006))) / SR
        y += a * np.exp(-6.91 * t / (t60 / (1 + 0.5 * k))) * np.sin(ph + r.random() * 6)
    y = conv(pulse(0.0025 if kind == 'dum' else 0.0012), y)[:n]
    if slap or kind == 'tek':
        s = bp(r.standard_normal(N(0.03)), 700, 6000) * np.exp(-tax(N(0.03)) / 0.005)
        place(y, s * (slap or 0.6) * np.max(np.abs(y)) / (np.max(np.abs(s)) + 1e-9), 0)
    return y


def zil(r, f0=None, t60=0.35, contact=0.0001, length=0.5):
    f0 = f0 or r.uniform(3800, 5200)
    ratios = [1.0, 1.36, 1.83, 2.41, 2.95, 3.66]
    ms = [(f0 * q * (1 + r.normal(0, 0.01)), 0.9 ** k, t60 / (1 + 0.2 * k), r.random() * 6) for k, q in enumerate(ratios)]
    return conv(pulse(contact), modal(ms, N(length)))


def jingles(r, n=4, spread=0.012, t60=0.25, gain=1.0):
    out = np.zeros(N(0.6))
    for _ in range(n):
        place(out, zil(r, t60=t60 * r.uniform(0.7, 1.2), length=0.5) * r.uniform(0.5, 1), abs(r.normal(0, spread)))
    return out * gain


def bell(r, f0, t60=0.7, contact=0.00012, length=1.0, ratios=(1.0, 2.32, 4.25, 6.63, 9.4), amps=(1, 0.6, 0.4, 0.25, 0.12)):
    ms = []
    for k, (q, a) in enumerate(zip(ratios, amps)):
        for s in (-1, 1):
            ms.append((f0 * q * (1 + s * 0.0025), a * 0.5, t60 / (1 + 0.4 * k), r.random() * 6))
    return conv(pulse(contact), modal(ms, N(length)))


# ======================================================================= footsteps
def footstep(r, kind='police', gain=1.0):
    if kind == 'police':     # leather heel on hard floor, then sole slap
        heel = conv(pulse(0.0005), modal([(f * r.uniform(0.95, 1.05), a, t, r.random() * 6) for f, a, t in
                                          [(1850, 1, 0.02), (2900, 0.7, 0.015), (4300, 0.5, 0.01), (6100, 0.3, 0.008)]], N(0.06)))
        thump = wood_hit(r, contact=0.004, scale=r.uniform(0.75, 0.95), damp=1.8, length=0.3, knock=0.15)
        sole = bp(r.standard_normal(N(0.05)), 300, 5000) * np.exp(-tax(N(0.05)) / 0.012)
        grit = bp(r.standard_normal(N(0.05)), 3000, 9000) * np.exp(-tax(N(0.05)) / 0.012) * (r.random(N(0.05)) < 0.2)
        x = mix(0.26, (heel / np.max(np.abs(heel)), 0, 0.55), (thump / np.max(np.abs(thump)), 0.0005, 0.9),
                (sole / np.max(np.abs(sole)), r.uniform(0.045, 0.065), r.uniform(0.3, 0.45)), (grit, 0.002, 0.15))
        x = lp(x, r.uniform(6500, 9000))
        x = room(x, r, t60=0.18, wet=0.08, pre=0.004)
    else:                    # light quick step, soft shoes
        thump = wood_hit(r, contact=r.uniform(0.004, 0.007), scale=r.uniform(1.1, 1.5), damp=0.8, length=0.13, knock=0.25)
        scuff = bp(r.standard_normal(N(0.04)), 600, 5000) * env_ad(N(0.04), 0.004, 0.015)
        tick = conv(pulse(0.0012), modal([(r.uniform(1100, 1600), 1, 0.012)], N(0.03)))
        x = mix(0.13, (thump / np.max(np.abs(thump)), 0, 1.0), (scuff / np.max(np.abs(scuff)), r.uniform(0.02, 0.035), r.uniform(0.15, 0.35)),
                (tick / np.max(np.abs(tick)), 0.0, 0.2))
        x = lp(x, 6000)
    return x * gain


# ======================================================================= voice (source-filter)
VOW = {  # adult male formants F1..F5 (Hz)
    'a': [720, 1240, 2550, 3350, 3900], 'e': [500, 1720, 2450, 3300, 3850], '@': [540, 1420, 2430, 3300, 3850],
    'o': [480, 880, 2450, 3300, 3850], 'u': [330, 800, 2300, 3250, 3800], 'i': [300, 2150, 2900, 3400, 3900],
    'm': [270, 1050, 2150, 3200, 3800], 'h': [600, 1450, 2500, 3400, 3900],
}
BW = [90, 110, 150, 220, 280]


class Voice:
    """A consistent character voice: f0 base, vocal-tract scale, roughness/breathiness."""

    def __init__(self, f0, scale=1.0, jitter=0.012, shimmer=0.06, breath=0.25, diplo=0.0, nasal=0.0, oq=0.6, seed=1):
        self.f0 = f0; self.scale = scale; self.jitter = jitter; self.shimmer = shimmer
        self.breath = breath; self.diplo = diplo; self.nasal = nasal; self.oq = oq; self.seed = seed

    def render(self, dur, f0_pts, vowel_pts, voice_pts, asp_pts, r, bw_mul=1.0, fry_pts=None, lowpass=None):
        """*_pts: lists of (time, value). vowel_pts values are keys of VOW or 5-lists of Hz."""
        n = N(dur); t = tax(n)
        f0 = env_pts(n, f0_pts) * (1 + self.jitter * 0.6 * smooth(n, 7, r))
        va = np.clip(env_pts(n, voice_pts), 0, None)
        aa = np.clip(env_pts(n, asp_pts), 0, None)
        fry = np.clip(env_pts(n, fry_pts), 0, 1) if fry_pts else np.zeros(n)
        # glottal flow: Rosenberg pulses, period-by-period jitter/shimmer, optional diplophonia/fry
        u = np.zeros(n); i = 0; k = 0
        while i < n:
            ff = f0[i] * (1 - 0.55 * fry[i])
            P = max(8, int(SR / ff * (1 + r.normal(0, self.jitter + 0.12 * fry[i]))))
            oq = self.oq * (1 - 0.45 * fry[i]); Tp = int(P * oq * 0.68); Tn = max(2, int(P * oq * 0.32))
            amp = (1 + r.normal(0, self.shimmer)) * (1 - self.diplo * (k % 2)) * (1 - 0.3 * fry[i] * (k % 3 == 1))
            seg = np.zeros(P)
            seg[:Tp] = 0.5 * (1 - np.cos(np.pi * np.arange(Tp) / Tp))
            seg[Tp:Tp + Tn] = np.cos(np.pi / 2 * np.arange(Tn) / Tn)
            m = min(P, n - i); u[i:i + m] = seg[:m] * amp; i += P; k += 1
        du = np.diff(u, prepend=0) * va * 60
        asp = noise(n, r, 'white') * aa * (0.35 + 0.65 * u) * self.breath * 0.15
        whisper = noise(n, r, 'pink') * aa * 0.05
        src = du + asp + whisper
        # formant trajectory
        vt = [(tt, np.array(VOW[v] if isinstance(v, str) else v, float)) for tt, v in vowel_pts]
        F = np.stack([np.interp(t, [p[0] for p in vt], [p[1][j] for p in vt]) for j in range(5)]) * self.scale
        y = src
        for j in range(5):
            q = F[j] / (BW[j] * bw_mul)
            y = tv_filter(y, F[j], q, kind='ap')
        if self.nasal:
            y = (1 - self.nasal) * y + self.nasal * peaking(lp(y, 1200), 260, 6, 1.2)
            y = peaking(y, 1000, -8 * self.nasal, 2.0)
        y = nz_(y) + 0.06 * nz_(bp(src, 3500, 9000))   # energy above F5 (breath, sibilance of the glottis)
        y = hp(y, 70)
        if lowpass:
            y = lp(y, lowpass)
        return fade(y, 0.003, 0.004)


SANER = Voice(f0=112, scale=0.97, jitter=0.016, shimmer=0.08, breath=0.45, diplo=0.08, nasal=0.15, oq=0.62, seed=11)
LEVAT = Voice(f0=96, scale=0.93, jitter=0.008, shimmer=0.04, breath=0.2, diplo=0.0, nasal=0.35, oq=0.55, seed=21)
MINKA = Voice(f0=215, scale=1.17, jitter=0.01, shimmer=0.05, breath=0.35, diplo=0.0, nasal=0.1, oq=0.66, seed=31)


def nz_(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def nasal_breath(r, dur, env, flutter=0.5, band=(350, 3200), res=(520, 1400, 2650)):
    """nasal exhale / snort with nostril flutter"""
    n = N(dur)
    e = env(tax(n) / dur) if callable(env) else env
    s = noise(n, r, 'pink')
    s = sum(resonator(s, f, 3.5) for f in res) + 0.3 * bp(s, *band)
    fl = 1 + flutter * np.sin(2 * np.pi * np.cumsum(34 + 12 * smooth(n, 10, r)) / SR) * np.clip(0.7 + 0.25 * smooth(n, 15, r), 0.3, 1)
    return fade(lp(s * e * np.clip(fl, 0.15, None), 3400), 0.002, 0.01)


def lip_puff(r, dur, env):
    """'pfff' – air forced through loosely closed lips"""
    n = N(dur)
    e = env(tax(n) / dur) if callable(env) else env
    s = bp(noise(n, r, 'white'), 700, 6500) * 0.6 + bp(noise(n, r, 'pink'), 150, 900)
    fl = 1 + 0.7 * np.clip(np.sin(2 * np.pi * np.cumsum(38 + 15 * smooth(n, 9, r)) / SR), 0, 1)
    pop = bp(r.standard_normal(N(0.006)), 80, 3000) * np.exp(-tax(N(0.006)) / 0.0015) * 6
    y = lp(s * e * fl, 5500)
    place(y, pop * np.max(np.abs(y)), 0)
    return fade(y, 0.0, dur * 0.3)


def whistle(r, dur, f_pts, amp_pts, breath=0.025):
    n = N(dur)
    f = env_pts(n, f_pts) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * tax(n)) + 0.002 * smooth(n, 20, r))
    a = np.clip(env_pts(n, amp_pts), 0, None)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.04 * np.sin(2 * ph)
    nb = tv_filter(r.standard_normal(n), f, 35) * 0.5
    air = bp(noise(n, r, 'pink'), 1500, 8000) * breath
    return (tone * (1 + 0.04 * smooth(n, 60, r)) + nb * 0.6 + air) * a
