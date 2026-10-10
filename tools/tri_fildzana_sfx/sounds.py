"""Sound designs. Each function returns a float signal (mono 1-D or stereo (n,2))."""
from models import *


def nz(x):
    return x / (np.max(np.abs(x)) + 1e-12)


# ============================================================ 1. cups / table / gameplay
CUP_F0 = [2250, 2480, 2120, 2640]


def cup_set_down(r, v):
    f0 = CUP_F0[v]
    contact = [0.0026, 0.0022, 0.0034, 0.0016][v]
    wood = nz(wood_hit(r, contact=contact * 1.6, scale=[1.6, 1.75, 1.45, 1.9][v], damp=0.9, length=0.25, knock=0.45))
    cer = nz(cup_hit(r, f0, t60=[0.26, 0.17, 0.15, 0.24][v], contact=contact, bright=[0.5, 0.55, 0.4, 0.65][v]))
    cl = nz(cloth_puff(r, 0.03, (250, 2500), 0.007))
    if v == 1:     # tilted landing: rim touches on one side, then settles
        cer2 = nz(cup_hit(r, f0, t60=0.09, contact=contact * 0.8, bright=0.6))
        return mix(0.3, (wood, 0, 0.55), (cer, 0, 0.22), (wood, 0.016, 0.8), (cer2, 0.016, 0.42), (cl, 0, 0.12))
    if v == 2:     # set down with a tiny slide-in
        sl = friction(r, 0.05, lambda u: np.sin(np.pi * u) ** 0.8, band=(400, 3000), grains=0.3)
        return mix(0.3, (nz(sl), 0, 0.10), (wood, 0.035, 1.0), (cer, 0.035, 0.3), (cl, 0.033, 0.18))
    return mix(0.3, (wood, 0, 1.0), (cer, 0, [0.38, 0, 0, 0.5][v]), (cl, 0, 0.14))


def cup_slide(r, v):
    d = [0.24, 0.31, 0.19, 0.27][v]
    envs = [lambda u: np.sin(np.pi * u) ** 0.9,
            lambda u: np.sin(np.pi * u) ** 0.7 * (1 - 0.55 * np.exp(-((u - 0.45) / 0.06) ** 2)),   # small catch
            lambda u: np.exp(-u * 2.2) * np.clip(u * 25, 0, 1),                                  # quick flick
            lambda u: np.sin(np.pi * u ** 0.75) ** 1.1]
    bands = [(350, 3400), (300, 3000), (450, 4000), (320, 3200)]
    x = friction(r, d, envs[v], band=bands[v], grain_rate=[500, 700, 400, 600][v], rough=0.5, grains=0.45)
    # the dragged cup colours the friction slightly
    col = conv(x, modal(cup_modes(r, CUP_F0[v], 0.05, 0.5), N(0.1)))[:len(x)]
    y = nz(x) + 0.12 * nz(col)
    y = lp(y, 4200)
    if v == 1:
        tick = nz(cup_hit(r, CUP_F0[v], t60=0.04, contact=0.0012, bright=0.4))
        place(y, tick * 0.18, d * 0.45)
    return y


def cup_lift(r, v):
    f0 = CUP_F0[v + 1]
    grip = nz(cup_hit(r, f0, t60=0.035, contact=0.0011, bright=0.35))
    skin = nz(fabric_rustle(r, 0.04, lambda u: np.sin(np.pi * u), band=(1800, 7000), crumple=0.1))
    rel = nz(cloth_puff(r, 0.06, (200, 1800), 0.02))
    air = nz(swoosh(r, 0.09, 600, 1400, q=0.7))
    if v == 0:
        return mix(0.2, (grip, 0, 0.35), (skin, 0.002, 0.25), (rel, 0.055, 0.5), (air, 0.05, 0.2))
    return mix(0.2, (skin, 0, 0.3), (grip, 0.012, 0.25), (rel, 0.045, 0.35), (air, 0.03, 0.3),
               (nz(wood_hit(r, contact=0.004, scale=1.9, damp=0.3, length=0.05)), 0.044, 0.15))


def cup_select(r, v=0):
    nail = nz(cup_hit(r, 2380, t60=0.15, contact=0.00028, bright=0.62))
    pad = nz(cup_hit(r, 2380, t60=0.05, contact=0.0012, bright=0.4))
    return lp(mix(0.15, (nail, 0, 0.6), (pad, 0.0006, 0.5)), 9000)


def cup_rattle(r, v):
    out = np.zeros(N(0.5))
    if v == 0:      # cup tilted against its neighbour: decaying chatter
        times = np.cumsum([0, 0.07, 0.055, 0.045, 0.035, 0.03, 0.026])
        amps = [1, 0.75, 0.6, 0.45, 0.35, 0.25, 0.18]
    else:           # picked up together with another cup: irregular clatter
        times = np.sort(np.concatenate([[0, 0.03], r.uniform(0.05, 0.33, 7)]))
        amps = list(r.uniform(0.35, 1.0, len(times)))
    fA, fB = 2300, 2560
    for t, a in zip(times, amps):
        h = cup_hit(r, fA, t60=0.2, contact=r.uniform(0.0002, 0.0005), bright=0.65) * r.uniform(0.4, 1)
        place(h, cup_hit(r, fB, t60=0.18, contact=r.uniform(0.0002, 0.0005), bright=0.65) * r.uniform(0.4, 1), 0)
        place(out, h * a, t)
    if v == 1:
        place(out, nz(fabric_rustle(r, 0.35, lambda u: np.sin(np.pi * u), band=(400, 4000), crumple=0.3)) * 0.004, 0.02)
    return lp(out, 9000)


def table_bump(r, v=0):
    thud = nz(wood_hit(r, contact=0.009, scale=0.85, damp=2.4, length=0.5, knock=0.15))
    creak = np.zeros(N(0.08))
    for k in range(6):
        place(creak, conv(pulse(0.0006), modal([(r.uniform(500, 900), 1, 0.02), (r.uniform(1400, 2000), 0.5, 0.015)], N(0.03))), k * 0.011)
    out = mix(0.5, (thud, 0, 1.0), (nz(creak), 0.02, 0.08))
    for c, f0 in enumerate((2250, 2480, 2120)):
        t = 0.012 + c * 0.007
        for k in range(r.integers(3, 5)):
            place(out, nz(cup_hit(r, f0, t60=0.14, contact=r.uniform(0.0004, 0.0008), bright=0.5)) * r.uniform(0.12, 0.22) / (k + 1) ** 0.8, t)
            t += r.uniform(0.03, 0.07)
    return lp(out, 6000)


def ball_reveal(r, v=0):
    a = string_track(0.5, [dict(t=0, f=NOTE['A5'], vel=0.9, pos=0.12)], r, t60=0.45, S=0.3, pick_bright=0.9)
    b = string_track(0.5, [dict(t=0.0, f=NOTE['D5'] * 2, vel=0.8, pos=0.1)], r, t60=0.4, S=0.3, pick_bright=0.9)
    return mix(0.5, (nz(a), 0.0, 0.8), (nz(b), 0.045, 0.7))


def cheat_glint(r, v=0):
    z1 = nz(zil(r, f0=4500, t60=0.16, length=0.3))
    z2 = nz(zil(r, f0=4720, t60=0.12, length=0.3))
    return mix(0.3, (z1, 0, 1.0), (z2, 0.038, 0.55))


# ============================================================ 2. UI / money / results
def ui_confirm(r, v=0):
    p = string_track(0.25, [dict(t=0, f=NOTE['G3'] * 2, vel=0.8, off=0.07, mute=0.05, pos=0.2)], r, t60=0.6, S=0.48, pick_bright=0.45)
    k = nz(conv(pulse(0.0004), hardwood_ir(r, t60=0.02, length=0.06)))
    return mix(0.2, (nz(p), 0.001, 1.0), (k, 0, 0.18))


def bet_place(r, v=0):
    paper = paper_crackle(r, 0.26, lambda u: np.sin(np.pi * u) ** 0.8, rate=1100, band=(1300, 8000), body=(400, 3500), body_amt=0.9)
    slap = nz(cloth_puff(r, 0.04, (200, 2500), 0.01))
    coin = coin_drop(r, on='cloth', bounces=2, h0=0.035, e=0.4)
    return mix(0.45, (nz(paper), 0, 0.55), (slap, 0.19, 0.35), (nz(coin), 0.24, 0.6))


def banknotes_count(r, v=0):
    out = np.zeros(N(0.95))
    t = 0.0
    for k in range(5):
        place(out, nz(note_flick(r)) * (0.85 + 0.15 * r.random()) * (1.0 if k < 4 else 1.15), t)
        t += r.uniform(0.13, 0.16)
    handle = paper_crackle(r, 0.8, lambda u: 0.25 + 0.2 * np.sin(np.pi * u), rate=250, body=(300, 2500), body_amt=0.6)
    place(out, nz(handle) * 0.18, 0)
    return out


def money_handover(r, v=0):
    slide = paper_crackle(r, 0.4, lambda u: np.sin(np.pi * u) ** 1.2, rate=350, band=(1200, 7000), body=(300, 3000), body_amt=1.0)
    skin = fabric_rustle(r, 0.25, lambda u: np.sin(np.pi * u), band=(800, 5000), crumple=0.2)
    fold = paper_crackle(r, 0.08, lambda u: np.exp(-u * 3), rate=2500, band=(1500, 8000), body_amt=0.3)
    return lp(mix(0.55, (nz(slide), 0, 0.6), (nz(skin), 0.08, 0.25), (nz(fold), 0.3, 0.45)), 7000)


def coins_small(r, v=0):
    out = np.zeros(N(0.6))
    f = [3100, 3650, 2850]
    place(out, coin_drop(r, on='cloth', bounces=3, h0=0.04, f0=f[0]), 0)
    place(out, coin_hit(r, f[1], t60=0.35, contact=0.00012) * 0.5, 0.085)
    place(out, coin_hit(r, f[0], t60=0.25, contact=0.00012) * 0.35, 0.086)
    place(out, coin_drop(r, on='cloth', bounces=2, h0=0.03, f0=f[2]) * 0.8, 0.19)
    return out


def coins_large(r, v=0):
    out = np.zeros(N(0.95))
    times = np.sort(np.concatenate([r.gamma(2.0, 0.07, 11), [0.0]]))
    times = times[times < 0.48]
    for k, t in enumerate(times):
        if k > 1 and r.random() < 0.6:    # lands on the pile: ringing coin-on-coin
            h = coin_hit(r, t60=0.45, contact=0.00012)
            place(h, 0.6 * coin_hit(r, t60=0.3, contact=0.00012), 0)
        else:
            h = coin_drop(r, on='cloth', bounces=2, h0=0.03)
        place(out, h * r.uniform(0.4, 1.0), t)
    # last coin wobbles to rest (accelerating ticks)
    t = times[-1] + 0.05; dt = 0.05; a = 0.35; f0 = 3400
    for k in range(6):
        place(out, coin_hit(r, f0, t60=0.12, contact=0.0002) * a, t); t += dt; dt *= 0.72; a *= 0.8
    return out


def _st(*tracks):
    """tracks: (mono, pan, gain) -> stereo with a little room"""
    L = max(len(x) for x, _, _ in tracks)
    y = np.zeros((L, 2))
    for x, p, g in tracks:
        y[:len(x)] += pan(nz(x), p) * g
    return y


def stereo_room(y, r, wet=0.10, t60=0.45):
    return np.stack([room(y[:, 0], rng(7), t60=t60, wet=wet), room(y[:, 1], rng(8), t60=t60, wet=wet)], 1)


def round_win(r, v=0):
    n1 = string_track(1.2, [dict(t=0.00, f=NOTE['D5'], vel=0.75), dict(t=0.065, f=NOTE['Eb5'], vel=0.7),
                            dict(t=0.13, f=NOTE['F5s'], vel=0.8), dict(t=0.195, f=NOTE['G5'], vel=0.85),
                            dict(t=0.27, f=NOTE['A5'], vel=1.0, glide=0.03)]
                      + tremolo(0.42, NOTE['A5'], 0.22, rate=18, vel=0.5, r=r, decresc=0.6), r, t60=0.6, S=0.32)
    n2 = string_track(1.2, [dict(t=0.27, f=NOTE['D5'], vel=0.8)] + tremolo(0.42, NOTE['D5'], 0.22, rate=18, vel=0.4, r=r, decresc=0.6), r, t60=0.6, S=0.32)
    bass = string_track(1.2, [dict(t=0.27, f=NOTE['D3'], vel=0.9, pos=0.2)], r, t60=0.55, S=0.45, body=BASS_BODY)
    dr = mix(1.2, (nz(drum(r, 105, 'dum', t60=0.3)), 0.27, 1.0), (nz(drum(r, 105, 'tek', t60=0.15)), 0.70, 0.55),
             (nz(jingles(r, 5, t60=0.25)), 0.27, 0.35), (nz(jingles(r, 4, t60=0.2)), 0.70, 0.3))
    pk = string_track(1.2, [dict(t=0.70, f=NOTE['D5'] * 2, vel=0.7, pos=0.1)], r, t60=0.35, S=0.3)
    y = _st((n1, -0.25, 0.7), (n2, 0.25, 0.5), (bass, 0, 0.45), (dr, 0.05, 0.55), (pk, 0.3, 0.35))
    return stereo_room(y, r)


def round_lose(r, v=0):
    s = string_track(0.9, [dict(t=0, f=NOTE['A3'], vel=0.9), dict(t=0.15, f=NOTE['F3s'] * 0.97, vel=0.0, glide=0.17),
                           dict(t=0.36, f=NOTE['D3'], vel=0.75, off=0.12, mute=0.08)], r, t60=1.0, S=0.42)
    b = string_track(0.9, [dict(t=0.36, f=NOTE['D2'], vel=0.8, off=0.1, mute=0.07, pos=0.25)], r, t60=0.8, S=0.5, body=BASS_BODY)
    d = nz(drum(r, 80, 'dum', t60=0.18, length=0.4))
    y = _st((s, -0.1, 0.75), (b, 0.05, 0.5), (mix(0.9, (d, 0.36, 1)), 0, 0.4))
    return stereo_room(y, r, wet=0.07)


def game_over(r, v=0):
    m = string_track(1.9, [dict(t=0.0, f=NOTE['Bb4'], vel=0.75), dict(t=0.2, f=NOTE['A4'], vel=0.7),
                           dict(t=0.4, f=NOTE['G4'], vel=0.7), dict(t=0.62, f=NOTE['Eb4'], vel=0.8),
                           dict(t=0.80, f=NOTE['D4'], vel=0.0, glide=0.12)]
                     + tremolo(0.94, NOTE['D4'], 0.3, rate=15, vel=0.5, r=r, decresc=0.8)
                     + [dict(t=1.24, f=NOTE['D4'] * 0.985, vel=0.0, glide=0.1)], r, t60=0.55, S=0.36)
    b = string_track(1.9, [dict(t=0.62, f=NOTE['D3'], vel=0.8), dict(t=0.94, f=NOTE['A2'], vel=0.75)], r, t60=0.6, S=0.45, body=BASS_BODY)
    d = mix(1.9, (nz(drum(r, 78, 'dum', t60=0.4)), 0.94, 1.0))
    y = _st((m, -0.15, 0.75), (b, 0.15, 0.5), (d, 0, 0.35))
    return stereo_room(y, r, wet=0.12)


def escape_victory(r, v=0):
    run = [NOTE[k] for k in ('D4', 'Eb4', 'F4s', 'G4', 'A4', 'Bb4', 'C5', 'D5')]
    ev = [dict(t=0.06 + i * 0.042, f=f, vel=0.65 + 0.04 * i) for i, f in enumerate(run)]
    m = string_track(1.6, ev + tremolo(0.42, NOTE['D5'], 0.55, rate=17, vel=0.6, r=r, decresc=0.7)
                     + [dict(t=1.0, f=NOTE['A5'], vel=0.9)], r, t60=0.45, S=0.32)
    ch = [string_track(1.6, [dict(t=0.40 + k * 0.012, f=f, vel=0.85)], r, t60=0.9, S=0.35) for k, f in
          enumerate((NOTE['D4'], NOTE['A4'], NOTE['D5'], NOTE['F5s']))]  # strum
    b = string_track(1.6, [dict(t=0.40, f=NOTE['D3'], vel=1.0), dict(t=1.0, f=NOTE['D2'], vel=0.9)], r, t60=0.5, S=0.45, body=BASS_BODY)
    d = mix(1.6, (nz(drum(r, 100, 'dum', t60=0.3)), 0.0, 0.7), (nz(drum(r, 100, 'dum', t60=0.35)), 0.40, 1.0),
            (nz(drum(r, 100, 'tek', t60=0.12)), 0.72, 0.4), (nz(drum(r, 100, 'tek', t60=0.12)), 0.86, 0.45),
            (nz(drum(r, 100, 'dum', t60=0.25)), 1.0, 0.9),
            (nz(jingles(r, 5)), 0.40, 0.4), (nz(jingles(r, 5, t60=0.18)), 1.0, 0.45))
    y = _st((m, -0.2, 0.7), (ch[0], 0.3, 0.3), (ch[1], 0.15, 0.3), (ch[2], 0.35, 0.3), (ch[3], 0.2, 0.25),
            (b, 0, 0.5), (d, 0.05, 0.6))
    return stereo_room(y, r, wet=0.12)


def bribe_rejected(r, v=0):
    s = string_track(0.5, [dict(t=0, f=NOTE['D3'], vel=1.0, off=0.07, mute=0.05), dict(t=0.14, f=NOTE['A2'], vel=1.0, off=0.12, mute=0.06)],
                     r, t60=0.8, S=0.48, body=BASS_BODY)
    d = mix(0.5, (nz(drum(r, 72, 'dum', t60=0.2, length=0.4)), 0.14, 1.0))
    k = mix(0.5, (nz(conv(pulse(0.0003), hardwood_ir(r, t60=0.03))), 0.14, 1.0))
    return lp(nz(s) * 0.8 + nz(d) * 0.45 + k * 0.12, 6000)


# ============================================================ 3. characters
def _breath(seg_dur, att, dec):
    return lambda u: np.clip(u * seg_dur / att, 0, 1) * np.exp(-np.clip(u * seg_dur - att, 0, None) / dec)


def saner_annoyed(r, v):
    if v == 0:     # "pfff" through the lips, a creaky grumble underneath
        lips = lip_puff(r, 0.42, _breath(0.42, 0.02, 0.16))
        g = SANER.render(0.62, [(0, 108), (0.62, 84)], [(0, '@'), (0.62, 'o')],
                         [(0, 0), (0.1, 0), (0.18, 0.35), (0.4, 0.25), (0.6, 0)],
                         [(0, 0), (0.05, 4), (0.3, 2.5), (0.62, 0)], r, fry_pts=[(0, 0), (0.3, 0.3), (0.62, 0.9)])
        return mix(0.66, (nz(lips), 0, 0.8), (nz(g), 0.02, 0.6))
    g = SANER.render(0.68, [(0, 118), (0.2, 100), (0.26, 100), (0.30, 108), (0.68, 86)], [(0, 'm'), (0.68, 'm')],
                     [(0, 0), (0.025, 1), (0.2, 0.8), (0.235, 0), (0.29, 0), (0.32, 0.9), (0.6, 0.5), (0.68, 0)],
                     [(0, 0.5), (0.68, 0.5)], r, fry_pts=[(0, 0), (0.15, 0.2), (0.4, 0.3), (0.68, 0.9)])
    nb = nasal_breath(r, 0.12, _breath(0.12, 0.02, 0.05), flutter=0.2)
    return mix(0.7, (nz(g), 0, 1.0), (nz(nb), 0.215, 0.25))


def saner_angry(r, v):
    if v == 0:     # snort
        sn = nasal_breath(r, 0.36, _breath(0.36, 0.008, 0.09), flutter=0.75)
        gr = SANER.render(0.12, [(0, 140), (0.12, 118)], [(0, 'm'), (0.12, 'm')],
                          [(0, 0), (0.01, 0.9), (0.08, 0.5), (0.12, 0)], [(0, 1), (0.12, 1)], r, fry_pts=[(0, 0.3), (0.12, 0.6)])
        return lp(mix(0.45, (nz(sn), 0, 1.0), (nz(gr), 0.004, 0.35)), 4500)
    hm = SANER.render(0.22, [(0, 150), (0.22, 112)], [(0, 'm'), (0.22, 'm')],
                      [(0, 0), (0.008, 1.0), (0.16, 0.7), (0.22, 0)], [(0, 0.5), (0.22, 1.5)], r, fry_pts=[(0, 0.2), (0.22, 0.7)])
    sn = nasal_breath(r, 0.3, _breath(0.3, 0.01, 0.08), flutter=0.6)
    return mix(0.6, (nz(hm), 0, 0.8), (nz(sn), 0.13, 1.0))


def saner_nervous(r, v=0):
    n = N(0.3)
    inh = SANER.render(0.3, [(0, 120), (0.3, 120)], [(0, 'h'), (0.3, 'u')], [(0, 0), (0.3, 0)],
                       [(0, 0), (0.05, 3), (0.25, 4), (0.3, 0)], r)
    inh = inh * (1 + 0.6 * np.sin(2 * np.pi * 7.5 * tax(len(inh))))
    click = conv(pulse(0.0004), modal([(1450, 1, 0.012), (2300, 0.5, 0.008)], N(0.03)))
    glk = SANER.render(0.08, [(0, 96), (0.08, 88)], [(0, 'u'), (0.08, 'u')], [(0, 0), (0.01, 0.7), (0.06, 0.4), (0.08, 0)],
                       [(0, 0.3), (0.08, 0.3)], r, fry_pts=[(0, 0.6), (0.08, 0.8)], lowpass=1500)
    thump = lp(r.standard_normal(N(0.03)), 180) * np.exp(-tax(N(0.03)) / 0.008)
    exh = nasal_breath(r, 0.15, _breath(0.15, 0.03, 0.05), flutter=0.1)
    return mix(0.62, (nz(inh), 0, 0.5), (nz(click), 0.34, 0.35), (nz(glk), 0.345, 0.5), (nz(thump), 0.345, 0.3), (nz(exh), 0.44, 0.18))


def saner_gasp(r, v=0):
    g = SANER.render(0.32, [(0, 185), (0.32, 235)], [(0, 'h'), (0.1, '@'), (0.3, 'a')],
                     [(0, 0), (0.17, 0), (0.23, 0.22), (0.29, 0.12), (0.32, 0)],
                     [(0, 0), (0.012, 7), (0.16, 6), (0.28, 3), (0.32, 0)], r)
    turb = bp(noise(N(0.3), r, 'pink'), 900, 4500) * env_pts(N(0.3), [(0, 0), (0.012, 1), (0.15, 0.6), (0.3, 0)])
    return lp(mix(0.34, (nz(g), 0, 1.0), (nz(turb), 0, 0.12)), 6500)


def _bursts(starts, lens, f0s, vowel, onset=0.016, fall=0.08):
    vp = [(0, 0)]; ap = [(0, 0)]; fp = []
    for s, L, f in zip(starts, lens, f0s):
        vp += [(s + onset * 0.6, 0), (s + onset, 1.0), (s + L * 0.7, 0.7), (s + L, 0)]
        ap += [(s, 0), (s + 0.004, 3.0), (s + onset, 1.2), (s + L, 0.6), (s + L + 0.02, 0.2)]
        fp += [(s, f), (s + L, f * (1 - fall))]
    return fp, vp, ap


def saner_chuckle(r, v):
    if v == 0:     # "heh-heh-heh-heh" through a half-open grin
        st = [0, 0.125, 0.24, 0.35]; ln = [0.075, 0.07, 0.068, 0.12]
        fp, vp, ap = _bursts(st, ln, [152, 144, 136, 126], 'e')
        fp += [(0.62, 110)]; ap += [(0.5, 2.0), (0.62, 0)]
        y = SANER.render(0.64, fp, [(0, 'e'), (0.36, '@'), (0.64, '@')], vp, ap, r, fry_pts=[(0, 0), (0.4, 0.2), (0.6, 0.6)])
        return y
    st = [0, 0.115, 0.225, 0.33]; ln = [0.07, 0.068, 0.07, 0.24]
    fp, vp, ap = _bursts(st, ln, [138, 133, 128, 122], 'm', fall=0.15)
    y = SANER.render(0.72, fp + [(0.72, 98)], [(0, 'm'), (0.72, 'm')], vp, [(t, a * 0.3) for t, a in ap], r,
                     fry_pts=[(0, 0), (0.45, 0.25), (0.7, 0.8)])
    nb = np.zeros(N(0.75))
    for s in st[:3]:
        place(nb, nz(nasal_breath(r, 0.05, _breath(0.05, 0.005, 0.015), flutter=0.2)), s + 0.07, 0.25)
    return mix(0.75, (nz(y), 0, 1.0), (nb, 0, 1.0))


def saner_wipe_forehead(r, v=0):
    y = fabric_rustle(r, 0.5, lambda u: np.clip(u / 0.15, 0, 1) * np.clip((1 - u) / 0.35, 0, 1), band=(450, 5500),
                      crumple=0.25, crumple_rate=120)
    return lp(y, 6000)


def saner_poke(r, v=0):
    vo = SANER.render(0.28, [(0, 122), (0.05, 132), (0.18, 192), (0.28, 178)], [(0, '@'), (0.05, 'e'), (0.28, 'e')],
                      [(0, 0), (0.006, 1.0), (0.17, 0.9), (0.27, 0)], [(0, 1.5), (0.03, 0.4), (0.2, 0.6), (0.28, 1.5)], r)
    fl = fabric_rustle(r, 0.12, lambda u: np.exp(-u * 4), band=(300, 3500), crumple=0.5)
    return mix(0.32, (nz(vo), 0.012, 1.0), (nz(fl), 0, 0.12))


def levat_reaction(r, v=0):
    y = LEVAT.render(0.52, [(0, 100), (0.2, 94), (0.3, 92), (0.5, 118)], [(0, 'm'), (0.52, 'm')],
                     [(0, 0), (0.03, 1), (0.45, 0.9), (0.52, 0)], [(0, 0.6), (0.52, 0.3)], r)
    nb = nasal_breath(r, 0.06, _breath(0.06, 0.005, 0.02), flutter=0.1)
    return mix(0.56, (nz(nb), 0, 0.12), (nz(y), 0.02, 1.0))


def minka_attention(r, v=0):
    a = MINKA.render(0.15, [(0, 200), (0.15, 185)], [(0, '@'), (0.15, '@')], [(0, 0), (0.01, 0.5), (0.12, 0.4), (0.15, 0)],
                     [(0, 0), (0.008, 3.5), (0.1, 2.0), (0.15, 0)], r, fry_pts=[(0, 0.9), (0.15, 0.7)], bw_mul=1.6)
    pulses = np.zeros(N(0.13)); t = 0.0
    while t < 0.125:        # irregular throat-clearing flutter (vocal-fold fry, ~40-60 Hz)
        place(pulses, np.exp(-tax(N(0.006)) / 0.0015), t, r.uniform(0.5, 1)); t += r.uniform(0.016, 0.026)
    rasp = bp(noise(N(0.13), r, 'pink'), 500, 3500) * (0.3 + pulses) * env_pts(N(0.13), [(0, 0), (0.01, 1), (0.13, 0)])
    b = MINKA.render(0.26, [(0, 238), (0.12, 228), (0.26, 206)], [(0, 'm'), (0.26, 'm')],
                     [(0, 0), (0.02, 1), (0.2, 0.8), (0.26, 0)], [(0, 0.5), (0.26, 0.3)], r)
    return mix(0.48, (nz(a), 0, 0.55), (nz(rasp), 0, 0.15), (nz(b), 0.19, 1.0))


def audience_murmur(r, v=0):
    dur = 0.98; L = N(dur); out = np.zeros((L, 2))
    vowels = ['a', 'e', 'o', '@', 'u', 'i', 'm']
    for k in range(16):
        male = r.random() < 0.55
        f0 = r.uniform(95, 135) if male else r.uniform(180, 240)
        vc = Voice(f0, scale=(0.97 if male else 1.16) * r.uniform(0.96, 1.04), jitter=0.012, shimmer=0.06, breath=0.35, seed=k)
        t0 = r.uniform(0, 0.25); d = dur - t0
        sy = []; t = 0; fp = []; vp = [(0, 0)]; vw = []
        while t < d:
            L1 = r.uniform(0.09, 0.2)
            if r.random() < 0.75:
                vp += [(t + 0.02, 0), (t + 0.04, r.uniform(0.5, 1)), (t + L1 - 0.03, r.uniform(0.3, 0.8)), (t + L1, 0)]
                fp += [(t, f0 * r.uniform(0.9, 1.15)), (t + L1, f0 * r.uniform(0.85, 1.05))]
                vw += [(t, vowels[r.integers(len(vowels))]), (t + L1, vowels[r.integers(len(vowels))])]
            t += L1 + r.uniform(0.0, 0.06)
        if not fp:
            continue
        fp = [(0, fp[0][1])] + fp + [(d, fp[-1][1])]
        vw = [(0, vw[0][1])] + vw + [(d, vw[-1][1])]
        y = vc.render(d, fp, vw, vp + [(d, 0)], [(0, 0.6), (d, 0.6)], r)
        y = nz(y) * r.uniform(0.4, 1.0)
        place(out, pan(y, r.uniform(-0.8, 0.8)), t0)
    swell = env_pts(L, [(0, 0.15), (0.3, 1.0), (0.55, 0.8), (dur, 0)])
    out *= swell[:, None]
    out = np.stack([lp(out[:, c], 3200) for c in range(2)], 1)
    return stereo_room(out, r, wet=0.35, t60=0.5)


# ============================================================ 4. power-ups / pigeon / wind
def coffee_activate(r, v=0):
    n = N(0.3)
    slurp = bp(noise(n, r), 1400, 7000) * env_pts(n, [(0, 0), (0.03, 0.6), (0.18, 1), (0.3, 0)])
    bub = np.zeros(n)
    for t in np.sort(r.uniform(0.02, 0.26, 12)):
        m = N(r.uniform(0.008, 0.016)); f = np.linspace(r.uniform(600, 900), r.uniform(1200, 1900), m)
        place(bub, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(m), t, r.uniform(0.4, 1))
    smack = conv(pulse(0.0006), modal([(r.uniform(900, 1300), 1, 0.01)], N(0.02)))
    p = string_track(0.6, [dict(t=0, f=NOTE['G4'], vel=0.6, pos=0.2), dict(t=0.1, f=NOTE['D5'], vel=0.55, pos=0.2)], r, t60=0.4, S=0.42, pick_bright=0.5)
    return mix(0.75, (nz(smack), 0, 0.25), (nz(slurp), 0.01, 0.35), (nz(bub), 0.01, 0.25), (nz(p), 0.3, 0.8))


def eye_activate(r, v=0):
    evs = [dict(t=0, f=NOTE['E5'], vel=0.5, pos=0.45), dict(t=0.05, f=NOTE['B4'] * 2, vel=0.5, pos=0.45),
           dict(t=0.1, f=NOTE['E6'], vel=0.55, pos=0.45)]
    y = sum(nz(string_track(0.45, [e], r, t60=0.32, S=0.3, pick_bright=0.25)) * g for e, g in zip(evs, (0.7, 0.6, 0.7)))
    return y


def pigeon_coo(r, v):
    if v == 0:
        segs = [(0.0, 0.11, [(0, 470), (0.11, 560)], 0.0), (0.15, 0.40, [(0, 565), (0.12, 615), (0.4, 455)], 0.45),
                (0.6, 0.15, [(0, 520), (0.15, 465)], 0.1)]
        dur = 0.8
    else:
        segs = [(0.0, 0.16, [(0, 440), (0.16, 520)], 0.1), (0.2, 0.48, [(0, 530), (0.15, 575), (0.48, 420)], 0.55)]
        dur = 0.72
    out = np.zeros(N(dur))
    for s, d, fpts, trill in segs:
        n = N(d); f = env_pts(n, fpts)
        ph = 2 * np.pi * np.cumsum(f) / SR
        am = 1 - trill * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(28 + 4 * smooth(n, 5, r)) / SR))
        e = env_pts(n, [(0, 0), (0.03, 1), (d - 0.05, 0.8), (d, 0)])
        tone = (np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)) * am * e
        br = bp(noise(n, r, 'pink'), 300, 1500) * e * 0.06
        place(out, tone + br, s)
    out = peaking(lp(out, 1600), 600, 4, 1.5)
    return out


def _flap(r, gain=1.0, clap=0.0, lpf=8000):
    n = N(0.07)
    whoof = lp(noise(n, r, 'pink'), 900) * env_pts(n, [(0, 0), (0.008, 1), (0.05, 0.2), (0.07, 0)])
    thump = bp(r.standard_normal(n), 120, 500) * env_pts(n, [(0, 0), (0.006, 1), (0.03, 0)])
    feath = bp(noise(n, r), 2000, 8000) * env_pts(n, [(0, 0), (0.01, 0.5), (0.04, 0)])
    y = nz(whoof) * 0.8 + nz(thump) * 0.5 + nz(feath) * 0.35
    if clap:
        c = bp(r.standard_normal(N(0.006)), 800, 7000) * np.exp(-tax(N(0.006)) / 0.0012)
        place(y, nz(c) * clap, 0)
    return lp(y, lpf) * gain


def pigeon_wings(r, v):
    out = np.zeros(N(0.7))
    if v == 0:     # take-off / departure: claps, then flaps receding
        t = 0.0; dt = 0.105
        for k in range(6):
            place(out, _flap(r, gain=1.0 - 0.13 * k, clap=1.3 if k < 2 else 0, lpf=8000 - 900 * k), t)
            t += dt; dt *= 0.93
    else:          # arrival: slowing flaps, braking flutter, feet on the cup
        t = 0.0
        for k, dt in enumerate([0.1, 0.105, 0.11]):
            place(out, _flap(r, gain=0.6 + 0.12 * k), t); t += dt
        for k in range(4):
            place(out, _flap(r, gain=0.55, lpf=6000), t); t += 0.055
        place(out, nz(cup_hit(r, 2400, t60=0.05, contact=0.0006, bright=0.45)) * 0.18, t + 0.02)
    return out


def wind_gust(r, v=0):
    dur = 0.92; n = N(dur)
    e = env_pts(n, [(0, 0), (0.25, 0.7), (0.42, 1.0), (0.62, 0.6), (dur, 0)])
    fc = env_pts(n, [(0, 300), (0.42, 900), (dur, 420)])
    body = tv_filter(noise(n, r, 'pink'), fc, 0.7) + 0.5 * lp(noise(n, r, 'brown'), 300)
    whis = tv_filter(noise(n, r), fc * 1.9 * (1 + 0.05 * smooth(n, 4, r)), 14) * 0.25
    rust = paper_crackle(r, dur, lambda u: np.exp(-((u - 0.5) / 0.18) ** 2), rate=500, band=(2000, 8000), body_amt=0.0)
    return nz(body * e) + 0.35 * nz(whis * e) + 0.12 * nz(rust)


# ============================================================ 5. police / escape
def police_siren(r, v=0):
    dur = 2.5; n = N(dur); t = tax(n)
    fh, fl = 612.0, 458.0
    seq = [fh, fl, fh, fl]; step = 0.6
    f = np.zeros(n)
    for k, ff in enumerate(seq):
        f[N(k * step):] = ff
    f = lp(f, 22, 1)                                                    # pneumatic switching glide
    f[:N(0.2)] = f[:N(0.2)] * (0.82 + 0.18 * np.clip(t[:N(0.2)] / 0.2, 0, 1) ** 0.6)   # compressor spin-up
    f *= 1 + 0.004 * np.sin(2 * np.pi * 3.1 * t) + 0.002 * smooth(n, 6, r)            # old compressor wow
    amp = env_pts(n, [(0, 0), (0.12, 1), (2.32, 1), (dur, 0)])
    amp *= 1 - 0.25 * np.exp(-((t[:, None] - np.arange(1, 4)[None] * step) / 0.02) ** 2).sum(1)
    y = np.zeros(n)
    for det in (1.0, 1.0047):
        ph = 2 * np.pi * np.cumsum(f * det) / SR
        for h in range(1, 14):
            if fh * h > 9000:
                break
            y += np.sin(h * ph + r.random()) / h ** 0.75
    y *= amp
    y = sum(resonator(y, fr, 4) * g for fr, g in ((950, 1), (1850, 0.6), (2750, 0.35))) + 0.2 * y
    y = np.tanh(1.6 * nz(y)) + 0.02 * bp(noise(n, r), 2000, 6000) * amp
    y = hp(lp(y, 5200), 300)
    return room(y, rng(3), t60=0.35, wet=0.12, lpf=3500)


def police_step(r, v):
    return footstep(r, 'police')


def police_grab(r, v=0):
    cr = fabric_rustle(r, 0.3, lambda u: np.clip(u / 0.04, 0, 1) * np.exp(-u * 5), band=(250, 5000), crumple=0.9, crumple_rate=700)
    th = lp(r.standard_normal(N(0.05)), 300) * np.exp(-tax(N(0.05)) / 0.012) + \
        np.sin(2 * np.pi * 110 * tax(N(0.05))) * np.exp(-tax(N(0.05)) / 0.015) * 0.5
    st = fabric_rustle(r, 0.15, lambda u: np.sin(np.pi * u), band=(200, 1500), crumple=0.3)
    return mix(0.36, (nz(th), 0.0, 0.6), (nz(cr), 0.0, 0.8), (nz(st), 0.14, 0.3))


def police_warning(r, v=0):
    d = nz(drum(r, 62, 'dum', t60=0.45, length=0.6, drop=0.08))
    b = string_track(0.6, [dict(t=0, f=NOTE['D2'], vel=1.0, pos=0.22)], r, t60=0.7, S=0.45, body=BASS_BODY)
    b2 = string_track(0.6, [dict(t=0.01, f=NOTE['Eb3'], vel=0.6, pos=0.2)], r, t60=0.5, S=0.45)
    y = _st((d, 0, 0.9), (b, -0.15, 0.55), (b2, 0.2, 0.25))
    return stereo_room(y, r, wet=0.08)


def run_step(r, v):
    return footstep(r, 'run')


def table_overturn(r, v=0):
    out = np.zeros(N(0.95))
    t = 0.0; rate = 85
    while t < 0.3:     # leg creak: wood stick-slip
        h = conv(pulse(0.0005), modal([(r.uniform(380, 420), 1, 0.02), (r.uniform(950, 1050), 0.6, 0.015),
                                       (r.uniform(1900, 2100), 0.35, 0.01)], N(0.03)))
        place(out, h * (0.4 + 0.6 * np.sin(np.pi * t / 0.3)) * r.uniform(0.3, 1.0), t)
        t += 1 / rate * r.uniform(0.55, 1.6); rate = 70 + 60 * (t / 0.3) + 25 * np.sin(t * 40)   # irregular stick-slip
    out = nz(out) * 0.3
    place(out, nz(swoosh(r, 0.2, 300, 900, q=0.7)) * 0.2, 0.24)
    big = nz(wood_hit(r, contact=0.007, scale=0.6, damp=2.6, length=0.6, knock=0.3))
    place(out, big, 0.42)
    for dt, g, sc in ((0.05, 0.45, 1.3), (0.13, 0.25, 1.5), (0.19, 0.1, 1.6)):
        place(out, nz(wood_hit(r, contact=0.003, scale=sc, damp=0.7, length=0.2, knock=0.4)) * g, 0.42 + dt)
    place(out, nz(cloth_puff(r, 0.08, (200, 2000), 0.014)) * 0.2, 0.44)
    return lp(out, 7000)


def cups_scatter(r, v=0):
    out = np.zeros(N(0.75))
    starts = [0.0, 0.055, 0.12, 0.2]
    for k, s in enumerate(starts):
        f0 = CUP_F0[k] * r.uniform(0.97, 1.03)
        t = s; a = 1.0
        for b in range(2):
            place(out, nz(cup_hit(r, f0, t60=0.22, contact=0.0005, bright=0.6)) * a, t)
            place(out, nz(wood_hit(r, contact=0.002, scale=2.0, damp=0.5, length=0.08)) * 0.25 * a, t)
            t += r.uniform(0.05, 0.09); a *= 0.45
        for m in range(r.integers(5, 9)):     # rolls a little on its rim
            place(out, nz(cup_hit(r, f0, t60=0.06, contact=0.0009, bright=0.4)) * 0.12 * (1 - m / 9), t)
            t += r.uniform(0.025, 0.04)
    place(out, nz(cup_hit(r, 2500, t60=0.2, contact=0.0003, bright=0.7)) * 0.4, 0.14)   # one cup knocks another
    return lp(out, 9000)


def cloth_swish(r, v=0):
    s = swoosh(r, 0.38, 400, 2600, q=0.6, env_pts_=((0, 0), (0.55, 1), (1, 0)), flutter=0.5)
    c = fabric_rustle(r, 0.38, lambda u: np.sin(np.pi * u) ** 2, band=(500, 6000), crumple=0.6, flutter=0.4)
    snap = bp(r.standard_normal(N(0.01)), 600, 6000) * np.exp(-tax(N(0.01)) / 0.002)
    return mix(0.45, (nz(s), 0, 0.8), (nz(c), 0, 0.4), (nz(snap), 0.3, 0.35))


def bundle_pack(r, v=0):
    out = mix(0.7, (nz(fabric_rustle(r, 0.62, lambda u: 0.5 + 0.5 * np.sin(np.pi * u), band=(300, 5000), crumple=0.7, crumple_rate=400)), 0, 0.6))
    for t, f0 in ((0.07, 2250), (0.2, 2480), (0.29, 2120)):
        place(out, lp(nz(cup_hit(r, f0, t60=0.07, contact=0.0006, bright=0.45)), 3000) * 0.55, t)
        place(out, lp(nz(cup_hit(r, f0 * 1.11, t60=0.05, contact=0.0005, bright=0.45)), 3000) * 0.3, t + 0.012)
    tug = fabric_rustle(r, 0.1, lambda u: np.exp(-u * 3), band=(200, 2500), crumple=1.0, crumple_rate=900)
    place(out, nz(tug) * 0.7, 0.5)
    return out


def smoke_puff(r, v=0):
    n = N(0.85)
    th = lp(noise(N(0.12), r), 260) * env_pts(N(0.12), [(0, 0), (0.004, 1), (0.12, 0)])
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(115, 45, N(0.14))) / SR) * np.exp(-tax(N(0.14)) / 0.05)
    body = lp(bp(noise(n, r, 'pink'), 150, 2200), 1800) * env_pts(n, [(0, 0), (0.01, 1), (0.12, 0.5), (0.4, 0.15), (0.85, 0)])
    fizz = bp(noise(n, r), 2500, 7000) * env_pts(n, [(0, 0), (0.05, 0.25), (0.25, 0.08), (0.7, 0)])
    sp = paper_crackle(r, 0.75, lambda u: np.exp(-u * 3), rate=300, band=(3000, 9000), body_amt=0)
    return mix(0.88, (nz(th), 0, 0.7), (nz(sub), 0, 0.35), (nz(body), 0, 0.75), (nz(fizz), 0, 0.12), (nz(sp), 0.03, 0.08))


def distraction_whistle(r, v=0):
    a = whistle(r, 0.13, [(0, 1850), (0.04, 2350), (0.13, 2600)], [(0, 0), (0.015, 1), (0.11, 0.9), (0.13, 0)])
    b = whistle(r, 0.19, [(0, 2500), (0.05, 2450), (0.19, 1720)], [(0, 0), (0.015, 1), (0.15, 0.8), (0.19, 0)])
    return mix(0.36, (a, 0, 1.0), (b, 0.165, 1.0))


def escape_swish(r, v=0):
    s = swoosh(r, 0.3, 500, 3200, q=0.9, env_pts_=((0, 0), (0.35, 1), (1, 0)), flutter=0.25)
    c = fabric_rustle(r, 0.22, lambda u: np.sin(np.pi * u), band=(500, 5000), crumple=0.5)
    return mix(0.32, (nz(s), 0, 1.0), (nz(c), 0.02, 0.3))


# ============================================================ 6. TV intro / interludes
def tv_switch_on(r, v=0):
    clk = lambda: conv(pulse(0.00015), modal([(r.uniform(2800, 3400), 1, 0.012), (r.uniform(5200, 6000), 0.6, 0.008)], N(0.03)))
    knock = nz(conv(pulse(0.0008), hardwood_ir(r, f=(650, 1200, 1900, 2700), t60=0.02, length=0.05)))
    n = N(0.4); t = tax(n)
    stat = bp(noise(n, r), 300, 9000) * env_pts(n, [(0, 0), (0.03, 1), (0.08, 0.7), (0.4, 0)])
    stat *= 1 + 0.5 * (np.sin(2 * np.pi * 50 * t) > 0.6)
    crack = paper_crackle(r, 0.3, lambda u: np.exp(-u * 4), rate=400, band=(2000, 9000), body_amt=0)
    hum = (np.sin(2 * np.pi * 50 * t) + 0.4 * np.sin(2 * np.pi * 100 * t)) * env_pts(n, [(0, 0), (0.02, 1), (0.25, 0)])
    thump = lp(r.standard_normal(N(0.06)), 140) * np.exp(-tax(N(0.06)) / 0.02)
    return mix(0.42, (nz(clk()), 0, 0.5), (knock, 0.001, 0.3), (nz(clk()), 0.011, 0.35), (nz(thump), 0.015, 0.45),
               (nz(stat), 0.02, 0.4), (nz(crack), 0.025, 0.2), (nz(hum), 0.015, 0.12))


def tv_test_tone(r, v=0):
    n = N(1.45); t = tax(n)
    y = np.sin(2 * np.pi * 1000 * t) + undb(-48) * np.sin(2 * np.pi * 50 * t) + undb(-58) * noise(n, r, 'pink')
    return fade(y, 0.006, 0.01)


def tv_static_cut(r, v=0):
    n = N(0.36); t = tax(n)
    st = bp(noise(n, r), 250, 9500) * env_pts(n, [(0, 0), (0.015, 1), (0.22, 0.8), (0.3, 0.3), (0.36, 0)])
    buzz = np.sign(np.sin(2 * np.pi * 50 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 15.6 * t))
    zz = bp(buzz * r.standard_normal(n), 400, 3000) * env_pts(n, [(0, 0), (0.1, 0), (0.12, 1), (0.2, 0.8), (0.22, 0)])
    cut = conv(pulse(0.0002), modal([(3100, 1, 0.01), (1200, 0.6, 0.02)], N(0.03)))
    thump = lp(r.standard_normal(N(0.05)), 150) * np.exp(-tax(N(0.05)) / 0.015)
    return mix(0.38, (nz(st), 0, 0.6), (nz(zz), 0, 0.3), (nz(thump), 0.0, 0.4), (nz(cut), 0.3, 0.35))


def film_clapper(r, v=0):
    hinge = conv(pulse(0.0001), modal([(6200, 1, 0.006), (8900, 0.6, 0.004)], N(0.02)))
    clap = conv(pulse(0.00012), hardwood_ir(r, t60=0.035, length=0.12))
    pop = bp(r.standard_normal(N(0.004)), 1500, 11000) * np.exp(-tax(N(0.004)) / 0.0007)
    y = mix(0.25, (nz(hinge), 0, 0.08), (nz(clap), 0.0015, 1.0), (nz(pop), 0.0015, 0.7))
    return room(y, rng(5), t60=0.25, wet=0.1, pre=0.004)


def telephone_ring(r, v=0):
    out = np.zeros(N(1.25))
    g1 = [bell(r, 1210, t60=0.38, length=0.6) for _ in range(3)]
    g2 = [bell(r, 1530, t60=0.34, length=0.6) for _ in range(3)]
    t = 0.0; k = 0; rate = 23.0
    while t < 0.68:
        a = min(1, 0.4 + t / 0.06) * (1 + 0.1 * r.normal())
        place(out, nz((g1 if k % 2 == 0 else g2)[k % 3]) * a * 0.6, t)
        place(out, bp(r.standard_normal(N(0.004)), 1000, 5000) * 0.03 * a, t)
        t += 1 / rate; k += 1
    out = out * 0.8 + 0.3 * bp(out, 500, 3000)
    return room(out, rng(9), t60=0.35, wet=0.1)


def telephone_pickup(r, v=0):
    hook = conv(pulse(0.00015), modal([(3600, 1, 0.02), (4700, 0.6, 0.015), (900, 0.4, 0.02)], N(0.05)))
    hand = nz(conv(pulse(0.0012), hardwood_ir(r, f=(520, 980, 1630, 2400, 3300), t60=0.03, length=0.08)))
    ding = nz(bell(r, 1210, t60=0.28, length=0.35))
    rub = fabric_rustle(r, 0.15, lambda u: np.sin(np.pi * u), band=(600, 4000), crumple=0.2)
    return mix(0.3, (hand, 0, 0.7), (nz(hook), 0.012, 0.6), (ding, 0.014, 0.1), (nz(rub), 0.04, 0.12))


def title_sting(r, v=0):
    m = string_track(1.1, [dict(t=0.0, f=NOTE['C5'], vel=0.7), dict(t=0.05, f=NOTE['D5'], vel=0.0, glide=0.025)]
                     + tremolo(0.1, NOTE['D5'], 0.45, rate=17, vel=0.55, r=r, decresc=0.7) + [dict(t=0.62, f=NOTE['A5'], vel=0.9)],
                     r, t60=0.45, S=0.32)
    ch = [string_track(1.1, [dict(t=0.1 + k * 0.013, f=f, vel=0.9)], r, t60=0.9, S=0.36)
          for k, f in enumerate((NOTE['D4'], NOTE['A4'], NOTE['D5'], NOTE['Eb5']))]  # strum
    b = string_track(1.1, [dict(t=0.1, f=NOTE['D3'], vel=1.0), dict(t=0.62, f=NOTE['D2'], vel=0.8)], r, t60=0.45, S=0.45, body=BASS_BODY)
    d = mix(1.1, (nz(drum(r, 96, 'dum', t60=0.35)), 0.1, 1.0), (nz(jingles(r, 6)), 0.1, 0.45),
            (nz(drum(r, 96, 'tek', t60=0.12)), 0.62, 0.55), (nz(jingles(r, 4)), 0.62, 0.35))
    y = _st((m, -0.2, 0.6), (ch[0], 0.25, 0.3), (ch[1], 0.1, 0.3), (ch[2], 0.35, 0.28), (ch[3], 0.2, 0.18), (b, 0, 0.5), (d, 0.05, 0.6))
    return stereo_room(y, r, wet=0.12)


def scene_transition(r, v=0):
    seq = [('A3', -0.3), ('D4', -0.15), ('Eb4', 0.0), ('F4s', 0.15), ('A4', 0.3), ('D5', 0.1)]
    tr = []
    for k, (nm, p) in enumerate(seq):
        t0 = k * 0.06 if k < 5 else 0.34
        tr.append((string_track(1.0, [dict(t=t0, f=NOTE[nm], vel=0.65 + 0.06 * k)], r, t60=0.55 + 0.03 * k, S=0.35), p, 0.5 if k < 5 else 0.6))
    return stereo_room(_st(*tr), r, wet=0.12)


def advert_sting(r, v=0):
    m = string_track(0.9, [dict(t=0.0, f=NOTE['G4'], vel=0.7, off=0.06), dict(t=0.075, f=NOTE['B4'], vel=0.7, off=0.06),
                           dict(t=0.15, f=NOTE['D5'], vel=0.75, off=0.06), dict(t=0.27, f=NOTE['G5'], vel=0.9)], r, t60=0.6, S=0.36)
    b = string_track(0.9, [dict(t=0.27, f=NOTE['G3'] / 2, vel=0.8, off=0.09)], r, t60=0.6, S=0.5, body=BASS_BODY)
    blk = mix(0.9, (nz(conv(pulse(0.0003), hardwood_ir(r, f=(1050, 2900, 4800), t60=0.05))), 0.27, 1.0))
    dg = mix(0.9, (nz(bell(r, 2090, t60=0.45, length=0.6)), 0.3, 1.0))
    y = _st((m, -0.15, 0.7), (b, 0.1, 0.45), (blk, 0.3, 0.25), (dg, 0.25, 0.22))
    return stereo_room(y, r, wet=0.09)


def news_sting(r, v=0):
    roll = np.zeros(N(0.95))
    for k in range(9):
        place(roll, nz(drum(r, 120, 'tek' if k % 2 else 'dum', t60=0.1, length=0.2)) * (0.15 + 0.07 * k), k * 0.032)
    hit = mix(0.95, (nz(drum(r, 74, 'dum', t60=0.45, drop=0.06)), 0.31, 1.0))
    lo = string_track(0.95, [dict(t=0.31, f=NOTE['D2'], vel=1.0)], r, t60=0.9, S=0.45, body=BASS_BODY)
    mid = string_track(0.95, [dict(t=0.31, f=NOTE['D3'], vel=0.9), dict(t=0.31, f=NOTE['A3'], vel=0.0)], r, t60=0.9, S=0.4)
    fi = string_track(0.95, [dict(t=0.316, f=NOTE['A3'], vel=0.8)], r, t60=0.9, S=0.4)
    hi = string_track(0.95, [dict(t=0.31, f=NOTE['D5'], vel=0.85), dict(t=0.43, f=NOTE['A4'], vel=0.75, off=0.08), dict(t=0.52, f=NOTE['D5'], vel=0.9)], r, t60=0.6, S=0.34)
    y = _st((roll, 0, 0.5), (hit, 0, 0.8), (lo, 0, 0.55), (mid, -0.2, 0.35), (fi, 0.2, 0.3), (hi, 0.15, 0.45))
    return stereo_room(y, r, wet=0.1)


def moving_rumble(r, v=0):
    d = 0.62
    sc = friction(r, d, lambda u: np.sin(np.pi * u) ** 0.6 * (1 - 0.5 * np.exp(-((u - 0.5) / 0.08) ** 2)),
                  band=(120, 1600), grain_rate=900, grain_band=(300, 2500), rough=0.9, grains=0.8)
    sc = conv(sc, wood_ir(r, scale=0.9, damp=0.6, length=0.15))[:N(d)]
    rum = lp(noise(N(d), r, 'brown'), 160) * env_pts(N(d), [(0, 0), (0.1, 1), (0.5, 0.9), (d, 0)])
    return lp(nz(sc) * 0.7 + nz(rum) * 0.5, 3500)


def paper_map(r, v=0):
    y = paper_crackle(r, 0.4, lambda u: 0.3 + np.exp(-((u - 0.2) / 0.08) ** 2) + 0.8 * np.exp(-((u - 0.62) / 0.1) ** 2),
                      rate=1500, band=(900, 8000), res=[1700, 2500], body=(250, 2500), body_amt=0.8)
    sw = swoosh(r, 0.3, 300, 900, q=0.6)
    return mix(0.42, (nz(y), 0, 0.8), (nz(sw), 0.05, 0.25))


def transition_swish(r, v=0):
    s = swoosh(r, 0.34, 320, 1500, q=0.6, env_pts_=((0, 0), (0.5, 1), (1, 0)))
    s2 = swoosh(r, 0.34, 900, 3200, q=1.2, env_pts_=((0, 0), (0.55, 1), (1, 0)))
    return nz(s) * 0.8 + nz(s2) * 0.2
