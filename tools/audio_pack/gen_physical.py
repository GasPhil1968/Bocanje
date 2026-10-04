"""Batch 1: balls, bulin, gravel, rolling loops, stop scrape, throws, wooden boards."""
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import *
import meta

B = 'physical'

# ------------------------------------------------------------------ building blocks
def ball_modes(r, scale=1.0, ring=1.0, bright=1.0):
    """Hollow metal bocce shell: inharmonic shell modes, restrained ring (ball rests in gravel)."""
    base = 2380*scale*(1+r.uniform(-0.035, 0.035))
    ratios = [1.0, 1.58, 2.27, 2.96, 3.71, 4.62]
    amps   = [1.0, 0.72, 0.52, 0.34, 0.22, 0.13]
    modes = []
    for k, (q, a) in enumerate(zip(ratios, amps)):
        f = base*q*(1+r.uniform(-0.012, 0.012))
        t60 = (0.42/(1+0.55*k))*ring*r.uniform(0.85, 1.15)
        modes.append((f, a*(bright**k)*r.uniform(0.8, 1.2), t60, r.uniform(0, 2*np.pi)))
        # split degenerate pair -> gentle beating, typical of real spheres
        modes.append((f*(1+r.uniform(0.002, 0.006)), a*0.45*(bright**k), t60*0.9, r.uniform(0, 2*np.pi)))
    return modes

def jack_modes(r):
    """Small hard synthetic/wood bulin (~40 mm): high, short, few modes."""
    base = 5200*(1+r.uniform(-0.05, 0.05))
    return [(base*q*(1+r.uniform(-0.02, 0.02)), a, t, r.uniform(0, 6.28))
            for q, a, t in [(1, 1, 0.11), (1.71, 0.6, 0.075), (2.48, 0.35, 0.05), (3.3, 0.2, 0.035)]]

def gravel_burst(r, n, t0, count, spread, fmin, fmax, amp, decay=3.0, qmin=3, qmax=9,
                 dmin=0.0015, dmax=0.006):
    """cluster of pebble ticks starting at t0, density decaying over `spread` s."""
    out = np.zeros(n)
    times = t0 + spread*(-np.log(1-r.uniform(0, 0.97, count))/decay)
    for ti in times:
        f = np.exp(r.uniform(np.log(fmin), np.log(fmax)))
        g = grain(r, f, r.uniform(qmin, qmax), r.uniform(dmin, dmax))
        a = amp*r.lognormal(0, 0.55)*np.exp(-(ti-t0)/(spread*0.9))
        i = int(ti*SR)
        if i < n:
            m = min(len(g), n-i); out[i:i+m] += g[:m]*a
    return out

def thump(r, n, f0, t60, amp, noise_amt=0.6, nlp=500):
    t = np.arange(n)/SR
    f = f0*(1+0.35*np.exp(-t/0.01))            # slight pitch drop as the gravel compacts
    ph = 2*np.pi*np.cumsum(f)/SR
    s = np.sin(ph)*np.exp(-6.91*t/t60)
    nz = lp(r.standard_normal(n), nlp, 2)*np.exp(-t/0.018)
    s = s + noise_amt*nz/np.max(np.abs(nz))
    return amp*s

# ------------------------------------------------------------------ A. ball-ball
def ball_collision(seed, tier):
    r = rng(seed)
    P = {'soft':   dict(tau=0.00085, ring=0.75, peak=-11.0, crunch=0.0,  click=0.25, body=0.45),
         'medium': dict(tau=0.00045, ring=1.0,  peak=-5.0,  crunch=0.10, click=0.55, body=0.55),
         'hard':   dict(tau=0.00022, ring=1.2,  peak=-1.2,  crunch=0.22, click=0.9,  body=0.65)}[tier]
    dur = {'soft': 0.42, 'medium': 0.55, 'hard': 0.7}[tier]
    n = int(dur*SR)
    pulse = hertz_pulse(P['tau']*r.uniform(0.85, 1.2))
    # two balls, slightly different shells
    br = {'soft': 0.62, 'medium': 0.9, 'hard': 1.08}[tier]          # upper shell modes: hit harder -> brighter
    ha = modal(ball_modes(r, 1.0, P['ring'], bright=br), n)
    hb = modal(ball_modes(r, r.uniform(0.93, 1.07), P['ring'], bright=br), n)
    x = conv(pulse, ha*1.0 + hb*r.uniform(0.6, 0.9))[:n]
    x /= np.max(np.abs(x))
    # dry contact click (the 'tak'): differentiated pulse, brighter for hard hits
    clk = np.zeros(n); d = np.diff(pulse, prepend=0); clk[:len(d)] = d
    clk = hp(clk, 1500 if tier != 'soft' else 900); clk /= np.max(np.abs(clk))+1e-12
    # body: the struck ball shoves into the gravel - short low knock
    body = thump(r, n, r.uniform(240, 340), 0.05, 1.0, noise_amt=0.5, nlp=900)
    x = x*1.0 + P['click']*clk + P['body']*body
    if P['crunch'] > 0:     # struck ball breaks out of its gravel bed
        x += gravel_burst(r, n, r.uniform(0.004, 0.012), int(40*P['crunch']/0.1), 0.12,
                          1500, 7000, P['crunch']*0.5)
    if tier == 'soft':      # gentle tap: darker, rounder
        x = lp(x, 4200, 2)
    elif tier == 'hard':    # forceful: extra snap in the 4-8 kHz region
        x = peaking(x, 5500, 3.0, 1.2)
    x = shelf_hi(x, 9000, -3)          # phone-friendly: no fizzy top
    return finish(x, P['peak'] + r.uniform(-0.6, 0.4), fout=0.04, tail_db=-58)

# ------------------------------------------------------------------ B. ball-bulin
def bulin_collision(seed, tier):
    r = rng(seed)
    hard = tier == 'hard'
    n = int((0.32 if hard else 0.24)*SR)
    pulse = hertz_pulse((0.00012 if hard else 0.00026)*r.uniform(0.85, 1.2))   # light jack: short contact (t ~ m^0.4)
    hj = modal(jack_modes(r), n)
    hb = modal(ball_modes(r, 1.0, 0.3, bright=0.8), n)*0.09    # big ball barely rings
    x = conv(pulse, hj + hb)[:n]; x /= np.max(np.abs(x))
    clk = np.zeros(n); d = np.diff(pulse, prepend=0); clk[:len(d)] = d
    clk = hp(clk, 2500); clk /= np.max(np.abs(clk))+1e-12
    x = x + (0.8 if hard else 0.35)*clk
    x += thump(r, n, r.uniform(700, 900), 0.015, 0.05)          # tiny body, light object
    if hard:   # the light jack skitters off over the gravel
        x += gravel_burst(r, n, r.uniform(0.02, 0.04), 18, 0.18, 2500, 8000, 0.10, decay=2)
    else:
        x = lp(x, 9000, 2)
    x = hp(x, 1200, 2)                                            # light object: no low body
    x = shelf_hi(x, 10000, -3)
    return finish(x, (-3.5 if hard else -12.0) + r.uniform(-0.6, 0.4), fout=0.03, tail_db=-56)

# ------------------------------------------------------------------ C. gravel landing
def gravel_land(seed, tier):
    r = rng(seed)
    hard = tier == 'hard'
    n = int((0.62 if hard else 0.42)*SR)
    x = thump(r, n, r.uniform(78, 105) if hard else r.uniform(90, 120),
              0.13 if hard else 0.12, 1.0, noise_amt=0.8, nlp=600 if hard else 420)
    x += gravel_burst(r, n, 0.001, 130 if hard else 38, 0.09 if hard else 0.06,
                      900, 8500 if hard else 5000, 0.55 if hard else 0.28,
                      qmin=2.5, qmax=8)
    if hard:   # thrown-up pebbles fall back
        x += gravel_burst(r, n, r.uniform(0.11, 0.17), 16, 0.22, 1800, 7500, 0.12, decay=1.6)
        # ball shell rings faintly against the stones
        ring = conv(hertz_pulse(0.0006), modal(ball_modes(r, 1.0, 0.45, 0.8), n))[:n]
        x += 0.10*ring/np.max(np.abs(ring))
    # broadband gravel 'shh' displacement
    sh = bp(r.standard_normal(n), 700, 4500)*np.exp(-np.arange(n)/SR/(0.05 if hard else 0.035))
    x += (0.18 if hard else 0.09)*sh
    x = shelf_hi(x, 9000, -4)
    return finish(x, (-3.0 if hard else -10.0) + r.uniform(-0.6, 0.4), fout=0.05, tail_db=-60)

# ------------------------------------------------------------------ D. rolling loops
def gravel_roll(seed, speed):
    r = rng(seed)
    L, XF = 5.0, 0.6
    n = int((L+XF)*SR)
    fast = speed == 'fast'
    rate = 330 if fast else 120
    # Poisson grain stream, clumped: rate varies with a slow random control
    ctrl = np.clip(1 + 0.45*smooth_noise(n, 3.0, r), 0.2, 2.2)
    cum = np.cumsum(ctrl)/SR*rate
    k = int(cum[-1]); targets = np.sort(r.uniform(0, cum[-1], k))
    times = np.interp(targets, cum, np.arange(n)/SR)
    x = np.zeros(n)
    fmin, fmax = (1100, 7000) if fast else (800, 4800)
    for ti in times:
        f = np.exp(r.uniform(np.log(fmin), np.log(fmax)))
        a = r.lognormal(0, 0.6)*(3.0 if r.uniform() < 0.025 else 1.0)
        g = grain(r, f, r.uniform(2.5, 8), r.uniform(0.0015, 0.005))*a
        i = int(ti*SR); m = min(len(g), n-i); x[i:i+m] += g[:m]
    x /= np.std(x)+1e-12
    # rumble of the heavy ball pressing the bed
    rum = lp(noise(n, r, 'brown'), 180 if fast else 130, 4)
    rum *= np.clip(1 + 0.3*smooth_noise(n, 6, r), 0.3, 2)
    rum /= np.std(rum)
    hiss = bp(r.standard_normal(n), 500, 2600)*np.clip(1+0.35*smooth_noise(n, 4, r), 0.2, 2)
    hiss /= np.std(hiss)
    y = 0.55*x + (0.9 if fast else 1.0)*rum + (0.35 if fast else 0.22)*hiss
    y = shelf_hi(y, 8500, -4)
    y = dc_block(y)
    y = make_loop(y, XF)
    y = norm_peak(y, -9.0 if fast else -12.0)
    return y

# ------------------------------------------------------------------ E. stop scrape
def gravel_stop(seed):
    r = rng(seed)
    dur = r.uniform(0.22, 0.34); n = int((dur+0.08)*SR)
    t = np.arange(n)/SR
    # decelerating grain stream
    rate0 = r.uniform(160, 240)
    times = []; tt = 0.0
    while tt < dur:
        cur = rate0*max(0.03, (1-tt/dur))**1.3
        tt += r.exponential(1/cur); times.append(tt)
    x = np.zeros(n)
    for ti in times[:-1]:
        g = grain(r, np.exp(r.uniform(np.log(900), np.log(5000))), r.uniform(3, 8),
                  r.uniform(0.0015, 0.004))*r.lognormal(0, 0.5)
        i = int(ti*SR); m = min(len(g), n-i); x[i:i+m] += g[:m]
    x /= np.max(np.abs(x))+1e-12
    fr = bp(r.standard_normal(n), 600, 3200)*np.clip(1-t/dur, 0, 1)**1.5
    x += 0.35*fr/np.max(np.abs(fr))
    # last settle: ball rocks into its bed
    x += thump(r, n, 140, 0.04, 0.0)  # (placeholder zero amp keeps rng sequence stable)
    i = int(dur*0.92*SR); s = thump(r, n-i, r.uniform(120, 170), 0.05, 0.35, 0.6, 500)
    x[i:] += s
    x = shelf_hi(x, 8000, -4)
    return finish(x, -15.0 + r.uniform(-0.5, 0.5), fout=0.04, tail_db=-55)

# ------------------------------------------------------------------ F. throws
def cloth(r, n, amount, center, width, density):
    t = np.arange(n)/SR
    env = np.exp(-0.5*((t-center)/width)**2)
    # fabric: dense micro-crackle with irregular folds
    folds = np.clip(1 + 0.8*smooth_noise(n, 22, r), 0, None)
    k = int(density*n/SR)
    times = r.uniform(0, n/SR, k)
    x = np.zeros(n)
    for ti in times:
        g = grain(r, np.exp(r.uniform(np.log(1500), np.log(7000))), r.uniform(0.8, 2.5),
                  r.uniform(0.0006, 0.002))*r.lognormal(0, 0.7)
        i = int(ti*SR); m = min(len(g), n-i); x[i:i+m] += g[:m]
    x = x*env*folds
    swish = bp(r.standard_normal(n), 900, 5000)*env*folds
    x = x/(np.max(np.abs(x))+1e-12) + 0.6*swish/(np.max(np.abs(swish))+1e-12)
    return amount*x

def air_swing(r, n, center, width, amount, f_lo, f_hi):
    """broadband, untonal body/arm movement through air - no whistle."""
    t = np.arange(n)/SR
    env = np.exp(-0.5*((t-center)/width)**2)
    w = noise(n, r, 'pink')
    # moving low-Q band: gentle 'fff' that swells and recedes
    lo = bp(w, f_lo, f_hi, 1)
    return amount*lo*env/(np.max(np.abs(lo*env))+1e-12)

def throw(seed, kind):
    r = rng(seed)
    tr = kind == 'trulo'
    dur = r.uniform(0.40, 0.46) if tr else r.uniform(0.28, 0.36)
    n = int(dur*SR)
    c = dur*r.uniform(0.45, 0.58); w = dur*(0.17 if tr else 0.2)
    x = air_swing(r, n, c, w, 1.0, 180 if tr else 160, 1400 if tr else 900)
    x += cloth(r, n, 0.75 if tr else 0.5, c - w*0.4, w*1.2, 900 if tr else 450)
    if tr:   # pivot foot plants in the gravel just before release
        x += gravel_burst(r, n, c - w*1.1, 22, 0.05, 900, 4500, 0.35)
        x += thump(r, n, 1, 0.01, 0.0)  # keep rng stream aligned
        i = int((c - w*1.1)*SR)
        x[i:] += thump(r, n-i, r.uniform(70, 95), 0.06, 0.45, 0.8, 300)
    x = lp(x, 7000, 2)
    return finish(x, (-6.5 if tr else -12.5) + r.uniform(-0.6, 0.4), fin=0.004, fout=0.05,
                  trim=True, lead_db=-40, tail_db=-50)

# ------------------------------------------------------------------ G. wooden boundary
def wood_boundary(seed, tier):
    r = rng(seed)
    hard = tier == 'hard'
    n = int((0.5 if hard else 0.36)*SR)
    f1 = r.uniform(150, 195)
    beam = [(f1*q*(1+r.uniform(-0.02, 0.02)), a, t*r.uniform(0.85, 1.15), r.uniform(0, 6.28))
            for q, a, t in [(1, 1.0, 0.30), (2.76, 0.7, 0.17), (5.40, 0.45, 0.09),
                            (8.93, 0.25, 0.05), (13.3, 0.12, 0.03)]]
    # plank cross-modes / grain
    beam += [(r.uniform(600, 1300), r.uniform(0.15, 0.35), r.uniform(0.03, 0.06), 0) for _ in range(4)]
    pulse = hertz_pulse((0.0006 if hard else 0.0013)*r.uniform(0.85, 1.2))
    x = conv(pulse, modal(beam, n))[:n]; x /= np.max(np.abs(x))
    clk = np.zeros(n); d = np.diff(pulse, prepend=0); clk[:len(d)] = d
    clk = bp(clk, 800, 5000); clk /= np.max(np.abs(clk))+1e-12
    x += (0.35 if hard else 0.12)*clk
    x += thump(r, n, r.uniform(85, 110), 0.14, 0.5 if hard else 0.35, 0.4, 350)  # board into its stakes
    ring = conv(hertz_pulse(0.0008), modal(ball_modes(r, 1.0, 0.4, 0.8), n))[:n]
    x += (0.05 if hard else 0.02)*ring/np.max(np.abs(ring))                      # metal ball, faint
    if hard:   # minimal rattle: board settles once against a stake
        i = int(r.uniform(0.018, 0.03)*SR)
        x[i:] += 0.12*conv(hertz_pulse(0.0009), modal(beam[2:5], n-i))[:n-i]/0.5
        x += gravel_burst(r, n, 0.01, 14, 0.08, 1200, 5000, 0.06)
    else:
        x = lp(x, 4500, 2)
    return finish(x, (-2.0 if hard else -9.0) + r.uniform(-0.6, 0.4), fout=0.05, tail_db=-60)

# ------------------------------------------------------------------ run
def main():
    meta.reset(B)
    seed = 1000
    def reg(rel, group, event, hook, gain, rate, cool, conc, status='existing-trigger', loop=None, **kw):
        meta.add(B, file=rel, group=group, event=event, hook=hook, gain_db=gain, rate=rate,
                 cooldown_ms=cool, max_voices=conc, status=status, method=meta.PROC, loop=loop, **kw)
    for tier in ['soft', 'medium', 'hard']:
        for v in range(1, 4):
            seed += 1; rel = f'sfx/balls/sfx_ball_collision_{tier}_{v:02d}.wav'
            write(rel, ball_collision(seed, tier))
            reg(rel, f'ball_collision_{tier}', 'bocca hits bocca',
                'klak(jacina, false) <- korak() pair-collision branch (pass 0, fx != null)',
                0.0, [0.94, 1.07], 45, 3,
                select={'soft': 'jacina < 0.25', 'medium': '0.25 <= jacina < 0.6', 'hard': 'jacina >= 0.6'}[tier])
    for tier in ['soft', 'hard']:
        for v in range(1, 4):
            seed += 1; rel = f'sfx/balls/sfx_bulin_collision_{tier}_{v:02d}.wav'
            write(rel, bulin_collision(seed, tier))
            reg(rel, f'bulin_collision_{tier}', 'bocca hits bulin (jack)',
                'klak(jacina, true) <- korak() pair-collision branch when a.strana or b.strana === "bulin"',
                0.0, [0.94, 1.07], 45, 2, select={'soft': 'jacina < 0.4', 'hard': 'jacina >= 0.4'}[tier])
    for tier in ['soft', 'hard']:
        for v in range(1, 4):
            seed += 1; rel = f'sfx/gravel/sfx_gravel_land_{tier}_{v:02d}.wav'
            write(rel, gravel_land(seed, tier))
            reg(rel, f'gravel_land_{tier}', 'ball lands / bounces on gravel',
                'tup(jac) <- korak() ground-impact branch (b.vz < -0.35); jac = min(1, -vz/8)',
                0.0, [0.9, 1.1], 35, 3, select={'soft': 'jac < 0.35', 'hard': 'jac >= 0.35'}[tier],
                note='successive bounces: same family, gain = 20*log10(jac/jac_first) dB')
    for sp in ['slow', 'fast']:
        seed += 1; rel = f'sfx/gravel/sfx_gravel_roll_{sp}_loop.wav'
        y = gravel_roll(seed, sp); write(rel, y)
        reg(rel, 'gravel_roll', f'rolling on gravel ({sp})',
            'kotrljajZvuk(brzina) <- azuriraj(): fastest grounded ball while stanje LET or PONOVKA',
            0.0, [0.8, 1.25], 0, 1, loop={'start': 0, 'end': len(y)},
            select='slow: 0.12 < brzina <= 2.5 m/s, fast: brzina >= 1.5; equal-power crossfade 1.5-2.5')
    for v in range(1, 4):
        seed += 1; rel = f'sfx/gravel/sfx_gravel_stop_{v:02d}.wav'
        write(rel, gravel_stop(seed))
        reg(rel, 'gravel_stop', 'ball settles (final scrape)',
            'skripa() <- korak() stop branch (speed < 0.05 and s > 0.052)', 0.0, [0.92, 1.08], 60, 2)
    for kind in ['bulanje', 'trulo']:
        for v in range(1, 4):
            seed += 1; rel = f'sfx/throws/sfx_throw_{kind}_{v:02d}.wav'
            write(rel, throw(seed, kind))
            reg(rel, f'throw_{kind}', f'release of a {kind} throw', f'zamahZvuk("{kind}") <- baci(); UVODI intro throws',
                0.0, [0.95, 1.05], 200, 1)
    for tier in ['soft', 'hard']:
        for v in range(1, 4):
            seed += 1; rel = f'sfx/boundaries/sfx_wood_boundary_{tier}_{v:02d}.wav'
            write(rel, wood_boundary(seed, tier))
            reg(rel, f'wood_boundary_{tier}', 'ball hits wooden board (side or rear)',
                'korak(): side-board else-branch (|x| > X_ZID-r, z <= VIS_ZIDA; currently tup(0.5)) '
                'and rear-board else-branch (y > Y_KRAJ-r, z <= VIS_ZIDA; currently silent)',
                0.0, [0.92, 1.08], 80, 2, status='new-routing (missing sound for existing physical event)',
                select={'soft': '|v_normal| < 2.5 m/s', 'hard': '|v_normal| >= 2.5 m/s'}[tier])

if __name__ == '__main__':
    dsp.OUT = sys.argv[1]
    main()
