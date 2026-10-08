"""Every sound of the pack as a recipe.  Each recipe returns float64 mono (n,) or stereo (n, 2).

Registry fields:
  folder, event, category, loop, vol (runtime gain 0..1), priority (1 low .. 10 high),
  cooldown_ms, max_sim, group (variation group), trigger, lufs (target loudness), dur (min, max) seconds
"""
import numpy as np
from lib import *

REG = {}


def sfx(name, folder, event, trigger, lufs, dur, vol=0.8, priority=5, cooldown=60, max_sim=2,
        group=None, loop=False, category=None, stereo=False, legacy=None):
    def deco(fn):
        REG[name] = dict(fn=fn, folder=folder, event=event, trigger=trigger, lufs=lufs, dur=dur, vol=vol,
                         priority=priority, cooldown=cooldown, max_sim=max_sim, group=group, loop=loop,
                         category=category or folder, stereo=stereo, legacy=legacy)
        return fn
    return deco


WING = (0.10, 0.35); UI = (0.05, 0.30); PICK = (0.15, 0.70); FEED = (0.10, 0.80)
CRASH = (0.30, 1.50); STING = (0.70, 2.50); ENV = (0.50, 4.00); LOOP = (12.0, 25.0)


# =====================================================================  A. PLAYER
@sfx('sfx_galeb_flap_01', 'player', 'Galeb wingbeat (light upstroke)', 'tap() while charKey==galeb - random pick from galeb_flap group, never the same file twice in a row',
     -29, WING, vol=0.55, priority=6, cooldown=70, max_sim=1, group='galeb_flap', legacy='tap(): beep(560,0.08,"triangle",0.05)')
def galeb_flap_01():
    return wingbeat(rng(101), 0.22, 1500, 760, 1.4, 280, 0.35, 0.25, 0.33)


@sfx('sfx_galeb_flap_02', 'player', 'Galeb wingbeat (feather variation)', 'tap() while charKey==galeb (variation)',
     -29, WING, vol=0.55, priority=6, cooldown=70, max_sim=1, group='galeb_flap')
def galeb_flap_02():
    return wingbeat(rng(102), 0.19, 1950, 1100, 1.2, 300, 0.25, 0.55, 0.30)


@sfx('sfx_galeb_flap_03', 'player', 'Galeb wingbeat (stronger)', 'tap() while charKey==galeb (variation; prefer after a long fall, bird.v > 0.6*max)',
     -28, WING, vol=0.55, priority=6, cooldown=70, max_sim=1, group='galeb_flap')
def galeb_flap_03():
    return wingbeat(rng(103), 0.26, 1300, 600, 1.5, 260, 0.55, 0.3, 0.27)


@sfx('sfx_vranac_flap_01', 'player', 'Vranac wingbeat (heavy)', 'tap() while charKey==vranac - random pick from vranac_flap group',
     -28, WING, vol=0.6, priority=6, cooldown=80, max_sim=1, group='vranac_flap', legacy='tap(): beep(560,0.08,"triangle",0.05)')
def vranac_flap_01():
    return wingbeat(rng(111), 0.28, 850, 380, 1.6, 210, 0.8, 0.2, 0.33)


@sfx('sfx_vranac_flap_02', 'player', 'Vranac wingbeat (feather displacement)', 'tap() while charKey==vranac (variation)',
     -28, WING, vol=0.6, priority=6, cooldown=80, max_sim=1, group='vranac_flap')
def vranac_flap_02():
    return wingbeat(rng(112), 0.31, 1000, 420, 1.5, 230, 0.85, 0.5, 0.28, second=(0.33, 0.55))


@sfx('sfx_vranac_flap_03', 'player', 'Vranac wingbeat (short powerful downstroke)', 'tap() while charKey==vranac (variation)',
     -27, WING, vol=0.6, priority=6, cooldown=80, max_sim=1, group='vranac_flap')
def vranac_flap_03():
    return wingbeat(rng(113), 0.20, 720, 330, 1.6, 200, 0.95, 0.15, 0.22)


def _gull_call(r, plan):
    out = np.zeros(N(sum(p[0] + p[-1] for p in plan) + 0.2))
    t = 0.0
    for dur, a, b, c, pk, rough, gap in plan:
        place(out, gull_syllable(dur, a, b, c, r, pk, rough), t)
        t += dur + gap
    return out


@sfx('sfx_galeb_call_01', 'player', 'Galeb call - long call with laughing notes',
     'gull() ambient timer (every 7-18 s) when charKey==galeb, feverStart(), spasavanje() - pick from galeb_call group',
     -23, (0.3, 1.5), vol=0.5, priority=4, cooldown=4000, max_sim=1, group='galeb_call', legacy='gull(); ONESHOT.galeb')
def galeb_call_01():
    r = rng(121)
    return _gull_call(r, [(0.42, 700, 1150, 640, 0.32, 0.22, 0.07), (0.16, 880, 1010, 720, 0.35, 0.3, 0.06),
                          (0.15, 860, 980, 700, 0.35, 0.3, 0.06), (0.14, 830, 940, 660, 0.35, 0.32, 0.0)])


@sfx('sfx_galeb_call_02', 'player', 'Galeb call - short "kyow"', 'gull() timer (variation), bird hover in character select',
     -23, (0.2, 1.0), vol=0.5, priority=4, cooldown=4000, max_sim=1, group='galeb_call')
def galeb_call_02():
    r = rng(122)
    return _gull_call(r, [(0.32, 760, 1080, 640, 0.28, 0.25, 0.0)])


@sfx('sfx_vranac_call_01', 'player', 'Vranac call - guttural cormorant croaks',
     'gull() timer / feverStart() / spasavanje() when charKey==vranac', -23, (0.3, 1.5), vol=0.5, priority=4,
     cooldown=4000, max_sim=1, group='vranac_call', legacy='gull(); ONESHOT.galeb')
def vranac_call_01():
    r = rng(131)
    out = np.zeros(N(1.0))
    for t, d, f0, fe in ((0.0, 0.22, 96, 84), (0.31, 0.18, 90, 78), (0.56, 0.15, 84, 70)):
        place(out, cormorant_grunt(d, f0, r, fe), t)
    return out


@sfx('sfx_vranac_call_02', 'player', 'Vranac call - single short croak', 'variation of vranac_call',
     -23, (0.2, 1.0), vol=0.5, priority=4, cooldown=4000, max_sim=1, group='vranac_call')
def vranac_call_02():
    return cormorant_grunt(0.36, 112, rng(132), 80, form=(540, 1180, 2450), rough=0.6)


@sfx('sfx_flight_dive', 'player', 'Dive - descending wind', "pokret('divepull') first half, or bird.v exceeds 85% terminal velocity (cooldown 1.5 s)",
     -27, FEED, vol=0.5, priority=3, cooldown=1500, max_sim=1, group='flight_move')
def flight_dive():
    r = rng(141); n = N(0.7); t = np.linspace(0, 1, n)
    fc = 1700 * (450 / 1700) ** (t ** 0.7)
    e = hann_env(n, 0.6) ** 1.2
    y = whoosh(0.7, fc, 1.3, r) * e + lp(noise(n, r, 'brown'), 220) * e * 0.5 + feather_rustle(n, e, r) * 0.08
    return y


@sfx('sfx_flight_pullup', 'player', 'Pull-up - upward air displacement', "pokret('divepull') second half / golden gate salute",
     -27, FEED, vol=0.5, priority=3, cooldown=1200, max_sim=1, group='flight_move')
def flight_pullup():
    r = rng(142); n = N(0.6); t = np.linspace(0, 1, n)
    fc = 450 * (1600 / 450) ** (t ** 0.9)
    y = whoosh(0.6, fc, 1.4, r) * hann_env(n, 0.42) ** 1.3
    place(y, wingbeat(r, 0.24, 1100, 500, 1.5, 230, 0.9, 0.25, 0.3), 0.0, 0.9)
    return y


@sfx('sfx_flight_roll', 'player', 'Barrel roll - air sweep (stereo)', "pokret('barrel') / pokret('rolab') (double tap), glideRoll on city arrival",
     -27, FEED, vol=0.5, priority=3, cooldown=900, max_sim=1, group='flight_move', stereo=True)
def flight_roll():
    r = rng(143); n = N(0.8); t = np.linspace(0, 1, n)
    fc = 950 + 420 * np.sin(2 * np.pi * 2.3 * t - 1.2)
    e = hann_env(n, 0.45)
    flut = 1 + 0.35 * np.sin(2 * np.pi * 16 * t * (1 - 0.3 * t)) * np.sin(np.pi * t) ** 2
    y = whoosh(0.8, fc, 1.2, r) * e * flut + feather_rustle(n, e, r) * 0.12
    p = -0.8 + 1.6 * t ** 1.1
    return pan(y, p)


@sfx('sfx_flight_wingover', 'player', 'Wingover - graceful directional sweep (stereo)', "pokret('wing') (3 clean passes in a row)",
     -27, FEED, vol=0.5, priority=3, cooldown=900, max_sim=1, group='flight_move', stereo=True)
def flight_wingover():
    r = rng(144); n = N(0.8); t = np.linspace(0, 1, n)
    fc = 650 + 750 * np.sin(np.pi * t) ** 1.5
    y = whoosh(0.8, fc, 1.3, r) * hann_env(n, 0.5) ** 1.1
    return pan(y, 0.6 - 1.0 * t)


@sfx('sfx_flight_glide', 'player', 'Glide - settling into a glide', 'glide starts (city sightseeing, glide>0) or knife pose end',
     -30, FEED, vol=0.4, priority=2, cooldown=2000, max_sim=1, group='flight_move')
def flight_glide():
    r = rng(145); n = N(0.75); t = np.linspace(0, 1, n)
    fc = 1150 * (780 / 1150) ** t
    e = hann_env(n, 0.18) ** 0.9
    y = whoosh(0.75, fc, 1.5, r) * e
    rs = feather_rustle(n, np.exp(-t / 0.12), r, 1500, 5000, 900) * 0.35
    return y + rs


# =====================================================================  B. PILLARS, PASSAGES, COMBOS
def _mpl(note, dur, r, vel=0.8, decay=None):
    return mandolin(hz(note), dur, r, vel=vel, decay=decay)


@sfx('sfx_score_tick', 'obstacles', 'Point confirmation', 'addScore(n) - once per call (not per point); duck under gate/combo sounds',
     -30, (0.05, 0.30), vol=0.45, priority=2, cooldown=45, max_sim=2, category='score', legacy='addScore(): beep(880,0.09,"square",0.04)')
def score_tick():
    r = rng(201)
    y = lp(mandolin(hz('E6'), 0.12, r, vel=0.8, decay=0.09, bright=0.3), 4500, 2) * adsr(N(0.12), 0.001, 0.03)
    place(y, wood_tap(1900, r, 0.05, 1.5, 0.2), 0.0, 0.3)
    return y


@sfx('sfx_gate_pass', 'obstacles', 'Ordinary pillar passage', 'pillar passed (judgeClean(p) with offset between CLEAN and EDGE)',
     -27, FEED, vol=0.5, priority=3, cooldown=80, max_sim=2)
def gate_pass():
    r = rng(202); n = N(0.32); t = np.linspace(0, 1, n)
    y = whoosh(0.32, 1200 * (2100 / 1200) ** t, 1.3, r) * hann_env(n, 0.22) ** 1.5 * 0.9
    place(y, _mpl('A5', 0.3, r, 0.5, 0.25), 0.03, 0.35)
    return y


@sfx('sfx_gate_clean', 'obstacles', 'Clean pass through the centre', 'judgeClean(p): clean pass, niz < 5',
     -23, FEED, vol=0.65, priority=6, cooldown=80, max_sim=2, group='gate_clean',
     legacy='judgeClean(): beep(700 + min(niz,10)*90, 0.12, "sine", 0.045)')
def gate_clean():
    r = rng(203); n = N(0.6)
    y = whoosh(0.6, 1600, 1.2, r) * hann_env(n, 0.1) ** 2 * 0.25
    place(y, _mpl('A5', 0.55, r, 0.7), 0.0)
    place(y, _mpl('D6', 0.5, r, 0.6), 0.035)
    return y


@sfx('sfx_gate_clean_streak', 'obstacles', 'Clean pass (streak)', 'judgeClean(p): clean pass with niz >= 5 (alternate with gate_clean on niz>=10 for colour)',
     -23, FEED, vol=0.65, priority=6, cooldown=80, max_sim=2, group='gate_clean')
def gate_clean_streak():
    r = rng(204); n = N(0.72)
    y = whoosh(0.72, 1900, 1.2, r) * hann_env(n, 0.1) ** 2 * 0.25
    place(y, _mpl('A5', 0.65, r, 0.65), 0.0)
    place(y, _mpl('D6', 0.6, r, 0.6), 0.03)
    place(y, _mpl('F#6', 0.55, r, 0.5), 0.065)
    place(y, glass(hz('A6'), 0.55, r, 2.0) * 0.18, 0.07)
    return y


@sfx('sfx_gate_nearmiss', 'obstacles', 'Near miss - air scrape past stone', 'zaDlaku(p, k) (haarscharf am Stein)',
     -24, FEED, vol=0.6, priority=6, cooldown=150, max_sim=1,
     legacy='zaDlaku(): noiseBurst(0.22,bandpass,...) + beep(300,0.08,"sawtooth",0.025)')
def gate_nearmiss():
    r = rng(205); n = N(0.36); t = np.linspace(0, 1, n)
    y = whoosh(0.36, 2600 * (800 / 2600) ** t, 1.1, r, color='white') * hann_env(n, 0.12) ** 1.4 * 0.8
    grit = np.zeros(n)
    for tt in np.sort(r.uniform(0.0, 0.14, 14)):
        place(grit, stone_tap(r.uniform(2200, 4200), r, 0.025), tt, r.uniform(0.05, 0.16))
    y += lp(grit, 6500)
    y += lp(noise(n, r, 'brown'), 250) * hann_env(n, 0.15) * 0.3
    return y


@sfx('sfx_gate_golden', 'obstacles', 'Golden gate passage', 'judgeClean(p): p.zlatna && off <= CLEAN*0.75',
     -21, (0.3, 1.2), vol=0.75, priority=8, cooldown=300, max_sim=1,
     legacy='judgeClean() golden: beep(1320..)+beep(1980..)')
def gate_golden():
    r = rng(206); n = N(1.1)
    y = np.zeros(n)
    place(y, strum([hz('D5'), hz('F#5'), hz('A5'), hz('D6')], 1.0, r, 0.028, 0.7), 0.0)
    place(y, lp(bell(hz('D5'), 1.05, r, bright=0.7, strike=0.1), 4500) * 0.35, 0.05)
    place(y, glass(hz('A6'), 0.8, r, 2.5) * 0.15, 0.12)
    return y


@sfx('sfx_gate_arch', 'obstacles', 'Stone arch passage (stereo)', 'pillar passed where p.arch is true (Pula arena arches / Split pipe=luk)',
     -24, FEED, vol=0.6, priority=5, cooldown=150, max_sim=1, stereo=True)
def gate_arch():
    r = rng(207); n = N(0.55); t = np.linspace(0, 1, n)
    w = whoosh(0.55, 900 * (1500 / 900) ** np.sin(np.pi * t), 1.2, r) * hann_env(n, 0.35) ** 1.3
    place(w, guitar(hz('A4'), 0.5, r, 0.5) * 0.5, 0.12)
    return early_ref(w, ((0.009, 0.32, -0.6), (0.016, 0.26, 0.6), (0.027, 0.15, -0.4), (0.041, 0.09, 0.5)), 3500)


@sfx('sfx_gate_double', 'obstacles', 'Double-opening passage', 'pillar with two openings passed (otvori(p).length > 1)',
     -23, FEED, vol=0.6, priority=5, cooldown=150, max_sim=1)
def gate_double():
    r = rng(208); n = N(0.6)
    y = np.zeros(n)
    for i, (tt, nt) in enumerate(((0.0, 'A5'), (0.1, 'E6'))):
        place(y, whoosh(0.2, 1500 + 500 * i, 1.2, r) * hann_env(N(0.2), 0.3) * 0.35, tt)
        place(y, _mpl(nt, 0.5, r, 0.65), tt)
    return y


@sfx('sfx_gate_triple_bonus', 'obstacles', 'Three special arches completed', 'third consecutive arch/golden passage in one location',
     -21, (0.7, 1.5), vol=0.75, priority=8, cooldown=500, max_sim=1)
def gate_triple_bonus():
    r = rng(209); n = N(1.4); y = np.zeros(n)
    for i, nt in enumerate(('D6', 'F#6', 'A6')):
        place(y, glass(hz(nt), 0.9, r, 1.8) * 0.35, i * 0.12)
        place(y, _mpl(nt[:-1] + '5', 0.8, r, 0.6), i * 0.12)
    place(y, strum([hz('D4'), hz('A4'), hz('D5'), hz('F#5')], 1.0, r, 0.025, 0.65, inst=guitar), 0.36)
    place(y, tremolo(hz('D6'), 0.5, r, 14, 0.35, swell=lambda u: 1 - u), 0.38)
    return y


@sfx('sfx_gate_tight_slowmo', 'obstacles', 'Near-perfect tight passage (slow-motion moment)', 'judgeClean(): off <= CLEAN*0.42 && narrow gap -> slowmo',
     -23, FEED, vol=0.65, priority=7, cooldown=800, max_sim=1, legacy='judgeClean(): beep(96,0.34,"sine",0.055,52)')
def gate_tight_slowmo():
    r = rng(210); n = N(0.75); t = np.linspace(0, 1, n)
    swell = np.where(t < 0.62, (t / 0.62) ** 2.2, np.exp(-(t - 0.62) / 0.07))
    air = whoosh(0.75, 320 * (1000 / 320) ** t, 1.5, r) * swell * 0.8
    y = air
    place(y, thump(r, 70, 38, 0.33, 0.1) * 0.55 * np.cos(np.pi / 2 * np.linspace(0, 1, N(0.33))) ** 2, 0.42)
    place(y, glass(hz('D6'), 0.3, r, 3) * 0.12 * adsr(N(0.3), 0.002, 0.08), 0.46)
    return y


@sfx('sfx_combo_increase', 'obstacles', 'Combo step up', 'kombo/niz increases without reaching a new multiplier tier',
     -24, FEED, vol=0.55, priority=5, cooldown=100, max_sim=1, group='combo', category='combo')
def combo_increase():
    r = rng(211); y = np.zeros(N(0.5))
    place(y, _mpl('E5', 0.45, r, 0.6), 0.0)
    place(y, _mpl('A5', 0.42, r, 0.7), 0.07)
    return y


@sfx('sfx_combo_break', 'obstacles', 'Combo lost', 'breakNiz() when niz > 0', -26, FEED, vol=0.5, priority=5,
     cooldown=300, max_sim=1, group='combo', category='combo', legacy='breakNiz(): beep(260,0.28,"sine",0.035,150)')
def combo_break():
    r = rng(212); y = np.zeros(N(0.5))
    place(y, guitar(hz('A4'), 0.4, r, 0.6, decay=0.3), 0.0)
    place(y, guitar(hz('F4'), 0.4, r, 0.55, decay=0.25), 0.11)
    n = len(y); t = np.linspace(0, 1, n)
    y += whoosh(0.5, 900 * (350 / 900) ** t, 1.4, r) * hann_env(n, 0.2) * 0.12
    return y * adsr(n, 0.001, 0.25) ** 0.5


@sfx('sfx_combo_x2', 'obstacles', 'Multiplier x2', 'kombo changes to 2 (niz reaches 3)', -22, FEED, vol=0.65,
     priority=7, cooldown=300, max_sim=1, group='combo', category='combo', legacy='layerChange(true): beep(1180,0.14,"sine",0.03)')
def combo_x2():
    r = rng(213); y = np.zeros(N(0.75))
    for i, nt in enumerate(('D5', 'F#5', 'A5')):
        place(y, _mpl(nt, 0.6, r, 0.65), i * 0.06)
    place(y, tremolo(hz('A5'), 0.25, r, 15, 0.25, swell=lambda u: 1 - u), 0.2)
    return y


@sfx('sfx_combo_x3', 'obstacles', 'Multiplier x3', 'kombo changes to 3 (niz reaches 6)', -22, (0.3, 1.0), vol=0.65,
     priority=7, cooldown=300, max_sim=1, group='combo', category='combo')
def combo_x3():
    r = rng(214); y = np.zeros(N(0.9))
    place(y, guitar(hz('D4'), 0.85, r, 0.55), 0.0)
    for i, nt in enumerate(('D5', 'F#5', 'A5', 'D6')):
        place(y, _mpl(nt, 0.7, r, 0.62), i * 0.055)
    place(y, glass(hz('D6'), 0.6, r, 2) * 0.18, 0.17)
    return y


@sfx('sfx_combo_x4', 'obstacles', 'Multiplier x4 (maximum)', 'kombo changes to 4 (niz reaches 10)', -22, (0.3, 1.2), vol=0.65,
     priority=8, cooldown=300, max_sim=1, group='combo', category='combo')
def combo_x4():
    r = rng(215); y = np.zeros(N(1.1))
    place(y, strum([hz('D3'), hz('A3'), hz('D4'), hz('F#4')], 1.0, r, 0.02, 0.55, inst=guitar), 0.0)
    for i, nt in enumerate(('D5', 'F#5', 'A5', 'D6', 'F#6')):
        place(y, _mpl(nt, 0.8, r, 0.6), 0.03 + i * 0.05)
    place(y, glass(hz('A6'), 0.8, r, 2.5) * 0.14, 0.24)
    place(y, glass(hz('D6'), 0.8, r, 1.7) * 0.16, 0.24)
    place(y, brass_tink(hz('D7'), r, 0.5) * 0.05, 0.25)
    return y


@sfx('sfx_fever_charge', 'obstacles', 'Fever ready - rising intensity', 'feverPunjenje reaches 4 (one clean pass before fever)',
     -23, (0.3, 1.0), vol=0.6, priority=7, cooldown=1000, max_sim=1, group='fever', category='fever')
def fever_charge():
    r = rng(221); n = N(0.95); t = np.linspace(0, 1, n)
    y = whoosh(0.95, 400 * (2400 / 400) ** t, 1.3, r) * (t ** 1.8) * np.where(t > 0.92, (1 - t) / 0.08, 1) * 0.45
    tt = 0.0; k = 0; notes = ['A4', 'D5', 'F#5', 'A5', 'A5', 'D6']
    while tt < 0.8:
        nt = notes[min(len(notes) - 1, int(tt / 0.8 * len(notes)))]
        place(y, mandolin(hz(nt), 0.25, r, vel=0.35 + 0.5 * tt / 0.8, decay=0.25), tt)
        tt += 0.11 * (1 - 0.55 * tt / 0.8); k += 1
    return y


@sfx('sfx_fever_start', 'obstacles', 'Fever mode activation', 'feverStart()', -20, (0.7, 1.5), vol=0.75,
     priority=9, cooldown=2000, max_sim=1, group='fever', category='fever',
     legacy='feverStart(): 3x beep(660*1.26^i) + ONESHOT.galeb')
def fever_start():
    r = rng(222); n = N(1.3); t = np.linspace(0, 1, n)
    y = whoosh(1.3, 500 * (2600 / 500) ** np.clip(t * 2.5, 0, 1), 1.4, r) * hann_env(n, 0.15) ** 1.5 * 0.35
    place(y, strum([hz('D3'), hz('A3'), hz('D4'), hz('F#4')], 1.2, r, 0.018, 0.8, inst=guitar), 0.0)
    place(y, strum([hz('A4'), hz('D5'), hz('F#5'), hz('A5')], 1.2, r, 0.015, 0.75), 0.02)
    place(y, tremolo(hz('D6'), 0.7, r, 14, 0.4, swell=lambda u: (1 - u) ** 1.5), 0.1)
    place(y, glass(hz('F#6'), 1.0, r, 2) * 0.12, 0.1)
    place(y, gull_syllable(0.3, 820, 1150, 760, r, 0.3, 0.2) * 0.12, 0.35)
    return y


@sfx('sfx_fever_end', 'obstacles', 'Fever ends - graceful return', 'feverKraj()', -24, (0.5, 1.2), vol=0.6,
     priority=6, cooldown=1000, max_sim=1, group='fever', category='fever', legacy='feverKraj(): beep(420,0.4,"sine",0.035,240)')
def fever_end():
    r = rng(223); n = N(1.0); t = np.linspace(0, 1, n)
    y = whoosh(1.0, 1500 * (450 / 1500) ** t, 1.4, r) * hann_env(n, 0.2) * 0.3
    for i, nt in enumerate(('A5', 'F#5', 'D5', 'A4')):
        place(y, _mpl(nt, 0.8 - i * 0.1, r, 0.6 - i * 0.06), i * 0.11)
    return y


# =====================================================================  C. COLLISIONS / DAMAGE / RESCUE
def _feather_poof(r, dur=0.3, fc=1800, g=0.3):
    n = N(dur)
    e = adsr(n, 0.01, 0.08)
    return (whoosh(dur, fc, 1.5, r) * e + feather_rustle(n, e, r, rate=1200) * 0.6) * g


@sfx('sfx_hit_limestone', 'collisions', 'Impact on a limestone pillar', "die() with uzrok='kamen' and pipe in ('stup','stone','luk') - Split/Sibenik/Pula pillars",
     -20, CRASH, vol=0.8, priority=9, cooldown=300, max_sim=1, group='hit', legacy='zvukKraja() impact part')
def hit_limestone():
    r = rng(301)
    y = stone_impact(r, 1.0, 0.35, 0.65)
    place(y, _feather_poof(r), 0.005)
    return y


@sfx('sfx_hit_wall', 'collisions', 'Heavier city-wall collision', "die() with pipe 'zid' (Dubrovnik walls) or 'orgulje' (Zadar riva stone)",
     -19, CRASH, vol=0.8, priority=9, cooldown=300, max_sim=1, group='hit')
def hit_wall():
    r = rng(302)
    y = stone_impact(r, 1.7, 0.6, 0.85, 0.85)
    n = len(y); t = tax(n)
    dens = np.exp(-np.maximum(t - 0.06, 0) / 0.18) * (t > 0.06)
    y += lp(feather_rustle(n, dens, r, 2000, 5200, 700), 6000) * 0.5
    place(y, _feather_poof(r, 0.3, 1500, 0.25), 0.004)
    return y


@sfx('sfx_hit_rock', 'collisions', 'Rough karst cliff collision', "die() with pipe 'stijena' (Makarska / Biokovo rock)",
     -19, CRASH, vol=0.8, priority=9, cooldown=300, max_sim=1, group='hit')
def hit_rock():
    r = rng(303); n = N(0.8); y = np.zeros(n)
    for tt, m, g in ((0.0, 0.9, 1.0), (0.019, 0.7, 0.55), (0.046, 0.8, 0.4)):
        place(y, stone_impact(r, m, 0.9, 0.7, 1.25), tt, g)
    sn = N(0.3); te = np.linspace(0, 1, sn)
    scrape = bp(noise(sn, r), 700, 3200) * (0.5 + 0.5 * np.abs(smooth(sn, 60, r))) * hann_env(sn, 0.15)
    place(y, scrape * 0.22, 0.04)
    place(y, _feather_poof(r, 0.28, 1700, 0.25), 0.003)
    return y


@sfx('sfx_hit_water', 'collisions', 'Falling into the sea', 'bird hits the ground/sea line (GROUND()) - die() from below',
     -20, CRASH, vol=0.8, priority=9, cooldown=300, max_sim=1, group='hit')
def hit_water():
    return splash(rng(304), 1.0, 0.9)


@sfx('sfx_bird_hurt', 'collisions', 'Startled bird reaction', 'breakShield(), spasavanje() start, die() (layer under impact)',
     -22, CRASH, vol=0.6, priority=7, cooldown=400, max_sim=1)
def bird_hurt():
    r = rng(305); n = N(0.42); y = np.zeros(n)
    place(y, gull_syllable(0.15, 950, 1350, 1050, r, 0.25, 0.5, breath=0.12), 0.0, 0.7)
    e = np.exp(-tax(n) / 0.12)
    y += feather_rustle(n, e, r, 1500, 6000, 2500) * 0.9 + whoosh(0.42, 1400, 1.6, r) * e * 0.3
    return y


@sfx('sfx_bird_falling', 'collisions', 'Bird falling - descending air', 'state=="dead" after impact while the bird tumbles (start ~0.15 s after hit)',
     -24, CRASH, vol=0.6, priority=6, cooldown=1000, max_sim=1)
def bird_falling():
    r = rng(306); n = N(1.3); t = np.linspace(0, 1, n)
    fc = 1500 * (380 / 1500) ** t
    rate = 13 - 6 * t
    flut = 0.6 + 0.4 * np.abs(np.sin(np.pi * np.cumsum(rate) / SR))
    e = hann_env(n, 0.35)
    return whoosh(1.3, fc, 1.3, r) * e * flut + feather_rustle(n, e * flut, r, rate=500) * 0.2


@sfx('sfx_game_over', 'collisions', 'Game over - melancholic Adriatic sting', 'die() - start ~0.35 s after the hit sound (replaces the melodic part of zvukKraja())',
     -22, STING, vol=0.7, priority=10, cooldown=3000, max_sim=1, category='stinger', legacy='zvukKraja()')
def game_over():
    r = rng(307); n = N(2.3); y = np.zeros(n)
    for i, (nt, tt) in enumerate((('F4', 0.0), ('E4', 0.2), ('D4', 0.4), ('C#4', 0.62))):
        place(y, mandolin(hz(nt), 0.6, r, vel=0.65 - i * 0.04, decay=0.8), tt)
    place(y, strum([hz('D3'), hz('A3'), hz('D4'), hz('F4')], 1.4, r, 0.035, 0.6, inst=guitar), 0.9)
    place(y, tremolo(hz('D5'), 0.75, r, 12, 0.22, swell=lambda u: (1 - u) ** 2), 0.92)
    return y


@sfx('sfx_shield_break', 'collisions', 'Coral shield shatters', 'breakShield()', -21, CRASH, vol=0.75, priority=9,
     cooldown=400, max_sim=1, legacy='breakShield(): beep(1500..)+noiseBurst(highpass 3000)')
def shield_break():
    r = rng(308); n = N(0.85); y = np.zeros(n)
    k = N(0.02); y[:k] += bp(r.standard_normal(k), 1500, 6000) * np.exp(-np.arange(k) / (k / 5)) * np.minimum(1, np.arange(k) / 20) * 0.8
    y += thump(r, 160, 80, 0.85, 0.05) * 0.4
    for tt in np.sort(r.exponential(0.09, 26)):
        if tt < 0.6:
            f = r.uniform(1700, 4400)
            place(y, glass(f, r.uniform(0.12, 0.3), r, r.uniform(1, 8)) * r.uniform(0.05, 0.22) * np.exp(-tt / 0.25), tt)
    return lp(y, 7500)


@sfx('sfx_rescue_activate', 'collisions', 'Three-feather rescue activates', 'spasavanje() returns true', -21, CRASH, vol=0.75,
     priority=10, cooldown=1000, max_sim=1, group='rescue', legacy='spasavanje(): beep(300,0.45,"sine",0.06,1300)+ONESHOT.galeb')
def rescue_activate():
    r = rng(309); n = N(1.05); y = np.zeros(n)
    for i in range(3):
        m = N(0.22); tt = np.linspace(0, 1, m)
        place(y, whoosh(0.22, (700 + 350 * i) * (1.8 ** tt), 1.2, r) * hann_env(m, 0.4) * 0.6
              + feather_rustle(m, hann_env(m, 0.4), r, rate=1500) * 0.4, i * 0.13)
    sw = N(0.8); te = np.linspace(0, 1, sw)
    sw_env = np.sin(np.pi * np.clip(te / 0.5, 0, 1) / 2) ** 2 * np.exp(-np.maximum(te - 0.5, 0) / 0.25)
    for nt in ('D5', 'A5', 'D6'):
        place(y, glass(hz(nt), 0.8, r, 1.5) * sw_env * 0.25, 0.2)
    place(y, tremolo(hz('A5'), 0.45, r, 13, 0.3, swell=lambda u: np.sin(np.pi * u)), 0.3)
    return y


@sfx('sfx_rescue_success', 'collisions', 'Bird recovers flight', 'shieldGrace from rescue ends with the bird alive (~2 s after spasavanje())',
     -21, CRASH, vol=0.75, priority=8, cooldown=1000, max_sim=1, group='rescue')
def rescue_success():
    r = rng(310); n = N(1.1); y = np.zeros(n)
    place(y, wingbeat(r, 0.28, 1200, 520, 1.5, 230, 1.0, 0.3, 0.3), 0.0, 0.9)
    for i, nt in enumerate(('A4', 'D5', 'F#5', 'A5')):
        place(y, _mpl(nt, 0.8, r, 0.6), 0.08 + i * 0.07)
    place(y, gull_syllable(0.22, 820, 1100, 900, r, 0.3, 0.15) * 0.1, 0.45)
    return y


# =====================================================================  D. COLLECTIBLES
@sfx('sfx_pickup_smokva', 'pickups', 'Fig pickup', "collectItems(): it.kind=='smokva'", -22, PICK, vol=0.65, priority=6,
     cooldown=60, max_sim=2, legacy='collectItems(): beep(1040,0.12,"sine",0.05)')
def pickup_smokva():
    r = rng(401); n = N(0.32); t = tax(n)
    f = 260 + 520 * np.exp(-t / 0.025)
    plop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045) * adsr(n, 0.002, 100)
    wet = bp(noise(n, r), 900, 3500) * np.exp(-t / 0.015) * 0.25
    y = plop + wet
    place(y, guitar(hz('D5'), 0.3, r, 0.55, decay=0.35) * 0.6, 0.012)
    return y


@sfx('sfx_pickup_kava', 'pickups', 'Espresso cup pickup (ceramic clink)', "collectItems(): it.kind=='kava'", -22, PICK,
     vol=0.65, priority=6, cooldown=60, max_sim=2, legacy='collectItems(): beep(700,0.16,"sine",0.05,1200)')
def pickup_kava():
    r = rng(402); y = np.zeros(N(0.45))
    place(y, ceramic(2150, r, 0.4), 0.0, 0.9)
    place(y, ceramic(1620, r, 0.35), 0.065, 0.55)
    place(y, wood_tap(420, r, 0.06, 1.2, 0.1) * 0.25, 0.064)
    return lp(y, 6000, 4)


@sfx('sfx_pickup_vino', 'pickups', 'Wine pickup - glass resonance (rescue feather +1)', "collectItems(): it.kind=='vino'",
     -22, PICK, vol=0.65, priority=7, cooldown=80, max_sim=1, legacy='collectItems(): beep(1560..)+beep(1980..)')
def pickup_vino():
    r = rng(403); y = np.zeros(N(0.7))
    place(y, glass(hz('D6'), 0.68, r, 1.6), 0.0, 0.55)
    place(y, glass(hz('E6') * 1.012, 0.65, r, 2.3), 0.006, 0.45)
    k = N(0.005); y[:k] += bp(r.standard_normal(k), 2500, 6000) * np.hanning(k) * 0.3
    return y


@sfx('sfx_pickup_stit', 'pickups', 'Coral shield pickup - sea-glass shimmer', "collectItems(): it.kind=='stit' (else branch)",
     -21, PICK, vol=0.7, priority=7, cooldown=80, max_sim=1, legacy='collectItems(): beep(400,0.35,"sine",0.06,1400)')
def pickup_stit():
    r = rng(404); n = N(0.68); t = np.linspace(0, 1, n)
    y = whoosh(0.68, 280 * (1300 / 280) ** t, 1.4, r) * hann_env(n, 0.35) * 0.35
    y += bubbles(n, np.sort(r.uniform(0, 0.35, 14)), r, 500, 1600, 0.25)
    sw = adsr(n, 0.07, 0.25)
    for nt, d in (('D5', 0.0), ('A5', 0.04), ('F#6', 0.12), ('A6', 0.18)):
        place(y, glass(hz(nt), 0.6, r, 3.0) * 0.22 * sw[:N(0.6)], d)
    return lp(y, 7500)


@sfx('sfx_pickup_duplo', 'pickups', 'Double-points coin', "collectItems(): it.kind=='duplo'", -21, PICK, vol=0.7,
     priority=7, cooldown=80, max_sim=1, legacy='collectItems(): beep(1200,0.3,"square",0.05,300)')
def pickup_duplo():
    r = rng(405); y = np.zeros(N(0.6))
    place(y, coin(2650, r, 0.45), 0.0, 0.5)
    place(y, coin(3020, r, 0.45), 0.075, 0.42)
    place(y, _mpl('A5', 0.5, r, 0.6), 0.0)
    place(y, _mpl('A6', 0.45, r, 0.5), 0.075)
    return y


@sfx('sfx_pickup_relic', 'pickups', 'Rare historic relic found', "collectItems(): it.kind=='kraj' (discovery)", -21, PICK,
     vol=0.7, priority=8, cooldown=200, max_sim=1, legacy='collectItems() kraj: beep(880..)+beep(1320..)')
def pickup_relic():
    r = rng(406); n = N(0.7)
    y = modal([(182, 0.6, 0.45), (414, 0.4, 0.3), (697, 0.25, 0.2), (1130, 0.1, 0.12)], n, r, True) * adsr(n, 0.001, 100) * 0.5
    place(y, lp(bell(hz('E5'), 0.7, r, 0.6, strike=0.05), 4000) * 0.35, 0.02)
    place(y, _mpl('E5', 0.6, r, 0.5), 0.08)
    place(y, _mpl('B5', 0.5, r, 0.5), 0.2)
    return y


def _paper(r, dur, fc=2500, g=1.0, crinkle=0.6):
    n = N(dur); e = hann_env(n, 0.3)
    sw = whoosh(dur, fc, 1.8, r, color='white') * e
    cr = feather_rustle(n, e, r, 1500, 6500, 1500) * crinkle
    return lp(sw * 0.6 + cr, 6000, 2) * g


def _stamp(r, g=1.0):
    n = N(0.22); t = tax(n)
    y = thump(r, 150, 75, 0.22, 0.03) * 0.8
    y += lp(noise(n, r, 'pink'), 1800) * np.exp(-t / 0.012) * 0.7
    y += wood_tap(330, r, 0.22, 1.5, 0.2) * 0.35
    return y * g


@sfx('sfx_pickup_passport', 'pickups', 'Collectible stamped into the passport', "putovnica(what) / pasSet() raises a location level during flight",
     -22, PICK, vol=0.65, priority=6, cooldown=300, max_sim=1)
def pickup_passport():
    r = rng(407); y = np.zeros(N(0.55))
    place(y, _paper(r, 0.13, 2600, 0.6), 0.0)
    place(y, _stamp(r), 0.11)
    place(y, _mpl('D6', 0.4, r, 0.45), 0.14)
    return y


@sfx('sfx_item_spawn', 'pickups', 'Item appears (optional, very subtle)', 'spawn() creates an item on screen (optional)', -34, PICK,
     vol=0.3, priority=1, cooldown=500, max_sim=1)
def item_spawn():
    r = rng(408); n = N(0.3); t = np.linspace(0, 1, n)
    y = whoosh(0.3, 2600, 1.0, r) * hann_env(n, 0.3) * 0.3
    place(y, glass(1760, 0.28, r, 4) * adsr(N(0.28), 0.03, 0.08) * 0.4, 0.02)
    return y


# =====================================================================  E. WEATHER
def _rain_st(dur, dens_fn, seed):
    out = []
    for ch in range(2):
        r = rng(seed + ch); n = N(dur); t = np.linspace(0, 1, n)
        out.append(rain(n, r, dens_fn(t)))
    y = np.stack(out, 1)
    return lp(y, 6000, 2)


@sfx('sfx_weather_rain_start', 'weather', 'Rain arrives over the coast', "startWeather('kisa', secs)", -26, ENV, vol=0.6, priority=4,
     cooldown=5000, max_sim=1, group='weather_rain', stereo=True, legacy="startWeather(): beep(200,0.7,'sine',0.03,90)")
def weather_rain_start():
    return _rain_st(3.5, lambda t: 1300 * np.clip(t * 1.15, 0, 1) ** 2.2, 501)


@sfx('sfx_weather_rain_end', 'weather', 'Rain fades away', "weather.left <= 0 while weather.kind=='kisa'", -27, ENV, vol=0.6,
     priority=3, cooldown=5000, max_sim=1, group='weather_rain', stereo=True)
def weather_rain_end():
    return _rain_st(3.0, lambda t: 1300 * (1 - t) ** 2.5, 503)


def _gust(dur, seed, spd, howl, p0, p1):
    r = rng(seed); n = N(dur); t = np.linspace(0, 1, n)
    s = spd(t)
    L = wind(n, r, s, howl); R = wind(n, rng(seed + 50), s, howl)
    p = p0 + (p1 - p0) * t
    st = np.stack([L * np.cos((p + 1) * np.pi / 4) + R * 0.35, R * np.sin((p + 1) * np.pi / 4) + L * 0.35], 1)
    st *= np.minimum(1, t[:, None] / 0.05) * np.minimum(1, (1 - t[:, None]) / 0.1)
    return lp(st, 6000)


@sfx('sfx_weather_bura_gust_01', 'weather', 'Bura gust', "startWeather('bura') and every 3-6 s during bura (random of group)", -24, ENV,
     vol=0.6, priority=4, cooldown=2500, max_sim=1, group='bura_gust', stereo=True, legacy="startWeather(): beep(140,0.7,'sine',0.03,90)")
def bura_gust_01():
    return _gust(2.8, 511, lambda t: 0.25 + 0.75 * np.sin(np.pi * np.clip(t / 0.85, 0, 1)) ** 1.5, 0.25, -0.5, 0.5)


@sfx('sfx_weather_bura_gust_02', 'weather', 'Bura blast (stronger)', "bura boss (score 50) start and its strongest gusts", -23, ENV,
     vol=0.6, priority=4, cooldown=2500, max_sim=1, group='bura_gust', stereo=True)
def bura_gust_02():
    def s(t):
        return np.clip(0.3 + 0.7 * np.exp(-((t - 0.3) / 0.14) ** 2) + 0.55 * np.exp(-((t - 0.62) / 0.12) ** 2), 0, 1.05) * np.minimum(1, (1 - t) / 0.3 + 0.2)
    return _gust(3.2, 512, s, 0.4, 0.6, -0.6)


def _fog(dur, seed, rising):
    r = rng(seed); n = N(dur); t = np.linspace(0, 1, n)
    u = t if rising else 1 - t
    low = lp(noise(n, r, 'brown'), 160) * np.sin(np.pi * t) ** 1.2
    air = tv_filter(noise(n, r, 'pink'), 3200 * (450 / 3200) ** u, 1.8, mode='lp', order=1.5) * (0.6 * np.sin(np.pi * t) ** 1.5)
    L = low + air
    R = lp(noise(n, rng(seed + 1), 'brown'), 160) * np.sin(np.pi * t) ** 1.2 + \
        tv_filter(noise(n, rng(seed + 2), 'pink'), 3200 * (450 / 3200) ** u, 1.8, mode='lp', order=1.5) * (0.6 * np.sin(np.pi * t) ** 1.5)
    return np.stack([L, R], 1)


@sfx('sfx_weather_fog_start', 'weather', 'Fog rolls in', "startWeather('magla')", -28, ENV, vol=0.55, priority=3,
     cooldown=5000, max_sim=1, group='weather_fog', stereo=True)
def weather_fog_start():
    return _fog(3.0, 521, True)


@sfx('sfx_weather_fog_end', 'weather', 'Fog clears', "weather ends while kind=='magla'", -29, ENV, vol=0.55, priority=3,
     cooldown=5000, max_sim=1, group='weather_fog', stereo=True)
def weather_fog_end():
    return _fog(2.5, 523, False)


@sfx('sfx_sea_small_splash', 'weather', 'Small water splash', 'fish/item dropping in the sea, leaves touching water, scenery splash', -25, ENV,
     vol=0.5, priority=3, cooldown=300, max_sim=2, category='sea')
def sea_small_splash():
    return splash(rng(531), 0.55, 0.6, 3800)


@sfx('sfx_sea_wave_impact', 'weather', 'Wave hits limestone shore (stereo)', 'scenery: wave breaking on the riva / rocks (random 15-40 s, or bura)',
     -25, ENV, vol=0.5, priority=3, cooldown=4000, max_sim=1, category='sea', stereo=True)
def sea_wave_impact():
    r = rng(532); dur = 2.6; n = N(dur)
    w = wave_wash(dur, r, 1.0, 1.0)
    i = N(0.72)
    hit = thump(r, 85, 45, 0.6, 0.12) * 0.6 + lp(noise(N(0.6), r, 'pink'), 2500) * adsr(N(0.6), 0.004, 0.08) * 0.8
    place(w, hit, 0, i=i)
    drops = bubbles(n, 0.8 + r.exponential(0.4, 40), r, 900, 3000, 0.1)
    w += drops
    return decor_stereo(lp(w, 7000), r, 0.45)


# =====================================================================  F. CITIES (stereo, distant)
def _distant(x, cut=2600, taps=None, width=0.25, seed=0):
    x = lp(x, cut)
    if taps:
        return early_ref(x, taps, cut * 0.8)
    return decor_stereo(x, rng(seed), width)


@sfx('sfx_city_split_bell', 'cities', 'Split - distant St. Domnius bell', "SCENE().one 'zvono' in Split; chime() on time-of-day change in Split",
     -27, ENV, vol=0.5, priority=3, cooldown=15000, max_sim=1, group='city_bell', stereo=True, legacy="ONESHOT.zvono / chime()")
def city_split_bell():
    r = rng(601); y = np.zeros(N(4.0))
    place(y, bell(hz('G3') * 0.99, 4.0, r, 0.8, 1.1), 0.0)
    place(y, bell(hz('G3') * 0.99, 2.0, r, 0.8, 1.1) * 0.55 * adsr(N(2.0), 0.002, 100), 2.0)
    return _distant(y, 2200, ((0.07, 0.18, -0.6), (0.13, 0.1, 0.7)))


@sfx('sfx_city_split_harbor', 'cities', 'Split harbour - masts, ropes, boats', "SCENE().one in Split (ambient one-shot every 9-20 s)",
     -27, ENV, vol=0.5, priority=2, cooldown=8000, max_sim=1, stereo=True)
def city_split_harbor():
    r = rng(602); n = N(4.0); L = np.zeros(n); R = np.zeros(n)
    for tt, p in ((0.1, -0.4), (1.7, 0.3), (3.0, -0.1)):
        lap = wave_wash(1.0, r, 0.4, 0.5)
        s = pan(lp(lap, 1400), p); L[N(tt):N(tt) + len(s)] += s[:n - N(tt), 0]; R[N(tt):N(tt) + len(s)] += s[:n - N(tt), 1]
    cr = friction_creak(0.7, r, (25, 70), (230, 580, 1100)) * 0.25
    s = pan(cr, 0.5); i = N(0.6); L[i:i + len(s)] += s[:, 0]; R[i:i + len(s)] += s[:, 1]
    for tt, f, p in ((1.2, 2280, -0.6), (1.35, 2510, -0.6), (2.6, 2180, 0.7)):
        s = pan(brass_tink(f, r, 0.6) * 0.18, p); i = N(tt); m = min(len(s), n - i)
        L[i:i + m] += s[:m, 0]; R[i:i + m] += s[:m, 1]
    s = pan(wood_tap(140, r, 0.25, 0.5, 0.1) * 0.35, 0.2); i = N(2.2); L[i:i + len(s)] += s[:, 0]; R[i:i + len(s)] += s[:, 1]
    return np.stack([L, R], 1)


@sfx('sfx_city_dubrovnik_bell', 'cities', 'Dubrovnik - warm church bell with stone reflections', "SCENE().one 'zvono' in Dubrovnik",
     -27, ENV, vol=0.5, priority=3, cooldown=15000, max_sim=1, group='city_bell', stereo=True, legacy='ONESHOT.zvono / chime()')
def city_dubrovnik_bell():
    r = rng(611); y = np.zeros(N(4.0))
    place(y, bell(hz('D3'), 3.6, r, 0.65, 1.3), 0.0)
    place(y, bell(hz('D3'), 2.3, r, 0.65, 1.3) * 0.7, 1.7)
    return _distant(y, 2800, ((0.018, 0.22, -0.7), (0.031, 0.17, 0.6), (0.052, 0.11, -0.3), (0.083, 0.07, 0.8)))


@sfx('sfx_city_dubrovnik_wind', 'cities', 'Dubrovnik - gentle wind over the walls', "SCENE().one in Dubrovnik", -28, ENV, vol=0.5,
     priority=2, cooldown=8000, max_sim=1, stereo=True)
def city_dubrovnik_wind():
    return _gust(4.0, 612, lambda t: 0.2 + 0.35 * np.sin(np.pi * t) ** 1.3, 0.35, -0.3, 0.4)


@sfx('sfx_city_sibenik_bell', 'cities', 'Sibenik - distant cathedral bell', "SCENE().one 'zvono' in Sibenik", -27, ENV, vol=0.5,
     priority=3, cooldown=15000, max_sim=1, group='city_bell', stereo=True, legacy='ONESHOT.zvono')
def city_sibenik_bell():
    r = rng(621); y = np.zeros(N(4.0))
    place(y, bell(hz('A#3'), 3.8, r, 0.75, 1.0), 0.0)
    place(y, bell(hz('A#3'), 2.6, r, 0.75, 1.0) * 0.5, 1.35)
    return _distant(y, 1900, ((0.09, 0.15, 0.5), (0.16, 0.08, -0.6)))


def cicada_layer(n, r, carrier=4700, prate=190, phrase=3.2, duty=0.55, circular=False, depth=1.0):
    t = tax(n)
    period = SR / prate
    pos = np.cumsum(np.full(int(n / period) + 2, period) * (1 + 0.04 * r.standard_normal(int(n / period) + 2)))
    pos = pos[pos < n].astype(int)
    imp = np.zeros(n); imp[pos] = r.uniform(0.6, 1.0, len(pos))
    k = N(0.004); tk = np.arange(k) / SR
    ker = (np.sin(2 * np.pi * carrier * tk) + 0.35 * np.sin(2 * np.pi * carrier * 1.38 * tk)) * np.exp(-tk / 0.0011) * np.minimum(1, tk / 0.0002)
    if circular:
        y = np.real(np.fft.ifft(np.fft.fft(imp) * np.fft.fft(ker, n)))
    else:
        y = np.convolve(imp, ker)[:n]
    ph = (t * phrase + r.random()) % 1
    pe = np.clip(np.sin(np.pi * np.clip(ph / duty, 0, 1)), 0, 1) ** 0.6
    pe = 1 - depth + depth * pe
    return y * pe


@sfx('sfx_city_sibenik_cicadas', 'cities', 'Sibenik - dry Dalmatian cicadas', "SCENE().one 'cvrcak' in Sibenik", -29, ENV, vol=0.45,
     priority=2, cooldown=8000, max_sim=1, group='cicada', stereo=True, legacy='ONESHOT.cvrcak')
def city_sibenik_cicadas():
    r = rng(622); n = N(4.0); t = np.linspace(0, 1, n)
    env = np.sin(np.pi * np.clip(t / 0.25, 0, 1) / 2) ** 2 * np.cos(np.pi / 2 * np.clip((t - 0.7) / 0.3, 0, 1)) ** 2
    out = np.zeros((n, 2))
    for i, (car, pr, phr, p, g) in enumerate(((4100, 185, 3.1, -0.5, 1.0), (4400, 205, 3.6, 0.6, 0.7), (3800, 170, 2.6, 0.1, 0.45))):
        out += pan(cicada_layer(n, r, car, pr, phr) * g, p)
    out *= env[:, None]
    return lp(out, 5500, 4)


@sfx('sfx_city_makarska_bura', 'cities', 'Makarska - bura descending from Biokovo', "SCENE().one in Makarska / start of bura in Makarska",
     -26, ENV, vol=0.55, priority=3, cooldown=8000, max_sim=1, stereo=True)
def city_makarska_bura():
    r = rng(631); n = N(4.0); t = np.linspace(0, 1, n)
    s = 0.2 + 0.8 * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 1.2
    hw = np.zeros(n)
    for base, g in ((900, 1.0), (1350, 0.5)):
        fc = base * (0.55 ** t)
        hw += tv_filter(noise(n, r), fc, 0.08) * g
    L = wind(n, r, s, 0.0) + hw * s ** 2 * 0.7
    R = wind(n, rng(632), s, 0.0) + hw * s ** 2 * 0.5
    p = -0.8 + 1.4 * t
    st = np.stack([L * np.cos((p + 1) * np.pi / 4), R * np.sin((p + 1) * np.pi / 4)], 1)
    st *= np.minimum(1, (1 - t[:, None]) / 0.12)
    return lp(st, 6000)


def pine_layer(n, r, speed, circular=False):
    src = circ_noise(n, r, 'pink') if circular else noise(n, r, 'pink')
    hiss = circ_filter(src, band_shape(1300, 4800, 2)) if circular else bp(src, 1300, 4800)
    fl = (circ_smooth(n, 22, r) if circular else smooth(n, 22, r))
    needles = hiss * (0.55 + 0.25 * fl) * speed ** 1.3
    return needles


@sfx('sfx_city_makarska_pines', 'cities', 'Makarska - wind through pine branches', "SCENE().one in Makarska", -29, ENV, vol=0.45,
     priority=2, cooldown=8000, max_sim=1, stereo=True)
def city_makarska_pines():
    r = rng(633); n = N(4.0); t = np.linspace(0, 1, n)
    s = 0.25 + 0.6 * np.sin(np.pi * t) ** 1.4
    L = pine_layer(n, r, s) + wind(n, r, s * 0.6, 0.0) * 0.6
    R = pine_layer(n, rng(634), s) + wind(n, rng(635), s * 0.6, 0.0) * 0.6
    y = np.stack([L, R], 1)
    cr = friction_creak(0.5, r, (18, 45), (300, 720, 1500)) * 0.05
    y[N(1.8):N(1.8) + len(cr)] += pan(cr, 0.4)
    return lp(y, 7000)


def organ_pipe(f, n, r, press, stopped=True):
    t = tax(n)
    wob = 1 + 0.0025 * smooth(n, 3, r) + 0.004 * (press - press.mean())
    ph = 2 * np.pi * np.cumsum(f * wob) / SR
    amps = [1, 0.18, 0.45, 0.08, 0.22, 0.05, 0.1] if stopped else [1, 0.5, 0.3, 0.2, 0.1, 0.08, 0.05]
    y = sum(a * np.sin((k + 1) * ph) for k, a in enumerate(amps) if (k + 1) * f < 6000)
    br = bp(noise(n, r), f * 1.5, min(f * 8, 6000)) * 0.12
    return (y + br) * press


def organ_press(n, r, t0, rise, hold, fall):
    t = tax(n)
    e = np.clip((t - t0) / rise, 0, 1)
    e = np.sin(np.pi / 2 * e) ** 2
    e *= np.cos(np.pi / 2 * np.clip((t - t0 - rise - hold) / fall, 0, 1)) ** 2
    e *= 1 + 0.2 * smooth(n, 5, r)
    return np.clip(e, 0, None)


def _sea_organ(notes, seed, dur=4.0, slosh=0.25):
    r = rng(seed); n = N(dur); L = np.zeros(n); R = np.zeros(n)
    for i, (nm, t0, rise, hold, fall, g, p) in enumerate(notes):
        pr = organ_press(n, r, t0, rise, hold, fall)
        y = organ_pipe(hz(nm), n, r, pr) * g
        s = pan(y, p); L += s[:, 0]; R += s[:, 1]
    w = wave_wash(dur, r, 0.6, 0.45)
    gur = lp(w, 900) * slosh
    st = np.stack([L, R], 1) + decor_stereo(gur, r, 0.5)
    t = np.linspace(0, 1, n)
    st *= np.minimum(1, (1 - t[:, None]) / 0.08)
    return lp(st, 5000)


@sfx('sfx_city_zadar_sea_organ_01', 'cities', 'Zadar - Sea Organ, low tones', "SCENE().one 'orgulje' in Zadar", -27, ENV, vol=0.5,
     priority=3, cooldown=10000, max_sim=1, group='sea_organ', stereo=True, legacy='ONESHOT.orgulje')
def zadar_organ_01():
    return _sea_organ([('E2', 0.0, 0.9, 1.2, 1.4, 1.0, -0.3), ('B2', 0.35, 0.8, 1.0, 1.4, 0.7, 0.3),
                       ('E3', 0.75, 0.7, 0.9, 1.3, 0.5, -0.1), ('G#3', 1.2, 0.6, 0.7, 1.3, 0.35, 0.5)], 641)


@sfx('sfx_city_zadar_sea_organ_02', 'cities', 'Zadar - Sea Organ, soft harmonic response', "SCENE().one 'orgulje' in Zadar (alternate)",
     -27, ENV, vol=0.5, priority=3, cooldown=10000, max_sim=1, group='sea_organ', stereo=True)
def zadar_organ_02():
    return _sea_organ([('A3', 0.0, 0.6, 0.8, 1.2, 0.9, 0.2), ('C#4', 0.25, 0.7, 0.9, 1.3, 0.6, -0.4),
                       ('E4', 0.6, 0.6, 0.8, 1.2, 0.45, 0.5), ('F#4', 1.1, 0.7, 0.6, 1.3, 0.35, -0.2),
                       ('A2', 0.15, 1.0, 1.1, 1.4, 0.5, 0.0)], 642)


@sfx('sfx_city_pula_bell', 'cities', 'Pula - distant Istrian church bell', "SCENE().one 'zvono' in Pula", -27, ENV, vol=0.5,
     priority=3, cooldown=15000, max_sim=1, group='city_bell', stereo=True, legacy='ONESHOT.zvono')
def city_pula_bell():
    r = rng(651); y = np.zeros(N(3.8))
    for i, tt in enumerate((0.0, 0.95, 1.9)):
        place(y, bell(hz('E4'), 3.8 - tt, r, 0.85, 0.9) * (1 - 0.1 * i), tt)
    return _distant(y, 2500, ((0.06, 0.15, 0.6), (0.11, 0.08, -0.5)))


def cricket_layer(n, r, f=4300, every=0.55, pulses=3, circular=False):
    t = 0.0; y = np.zeros(n)
    while t < n / SR:
        for k in range(pulses):
            m = N(0.016); tt = np.arange(m) / SR
            ch = np.sin(2 * np.pi * f * tt) * np.sin(np.pi * tt / tt[-1]) ** 2
            i = N(t + k * 0.034)
            if circular:
                place_wrap(y, ch, i, 1.0)
            else:
                place(y, ch, 0, i=i)
        t += every * (1 + 0.08 * r.standard_normal())
    return y


@sfx('sfx_city_pula_cicadas', 'cities', 'Pula - warm Istrian evening insects', "SCENE().one 'cvrcak' in Pula (esp. Zalazak / Plavi sat)",
     -29, ENV, vol=0.45, priority=2, cooldown=8000, max_sim=1, group='cicada', stereo=True, legacy='ONESHOT.cvrcak')
def city_pula_cicadas():
    r = rng(652); n = N(4.0); t = np.linspace(0, 1, n)
    env = np.minimum(1, t / 0.15) * np.minimum(1, (1 - t) / 0.2)
    out = pan(cricket_layer(n, r, 4250, 0.52) * 0.5, -0.5) + pan(cricket_layer(n, r, 3950, 0.61, 4) * 0.4, 0.6)
    out += pan(lp(cicada_layer(n, r, 4200, 150, 1.4, 0.8, depth=0.5), 4500) * 0.25, 0.1)
    return lp(out * env[:, None], 6500)


# =====================================================================  props
@sfx('sfx_prop_ferry_horn', 'props', 'Distant Adriatic ferry horn', "ONESHOT.sirena (trajekt passing; Split, Zadar)", -26, ENV, vol=0.5,
     priority=3, cooldown=20000, max_sim=1, stereo=True, legacy='ONESHOT.sirena')
def prop_ferry_horn():
    r = rng(701); dur = 3.4; n = N(dur); t = tax(n)
    f0 = 116.5 * (1 + 0.025 * (1 - np.exp(-t / 0.12)) - 0.01) * (1 + 0.002 * smooth(n, 4, r))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = sum((1 / k ** 1.25) * np.sin(k * ph) for k in range(1, 30) if k * 116.5 < 3500)
    y = src * 0.3 + resonator(src, 330, 3) * 0.8 + resonator(src, 720, 4) * 0.4 + resonator(src, 1250, 5) * 0.15
    y += bp(noise(n, r), 150, 900) * 0.08
    e = np.minimum(1, t / 0.18) ** 1.5 * np.where(t > 2.5, np.cos(np.pi / 2 * np.clip((t - 2.5) / 0.35, 0, 1)) ** 2, 1)
    y = lp(y * e, 1000, 4)
    out = np.zeros(N(4.0)); out[:n] += y
    st = early_ref(out, ((0.35, 0.22, -0.7), (0.82, 0.10, 0.6)), 900)
    return st[:N(4.0)]


@sfx('sfx_prop_fishing_boat', 'props', 'Wooden fishing boat creaking', "barka (camac) on screen - one-shot while visible", -27, ENV, vol=0.45,
     priority=2, cooldown=8000, max_sim=1, stereo=True)
def prop_fishing_boat():
    r = rng(702); n = N(3.2); y = np.zeros(n)
    place(y, friction_creak(0.9, r, (20, 55), (180, 470, 960), (10, 12, 14)) * 0.3, 0.1)
    place(y, friction_creak(0.7, r, (35, 80), (210, 540, 1100)) * 0.22, 1.6)
    place(y, wood_tap(120, r, 0.3, 0.4, 0.05) * 0.35, 1.25)
    lap = lp(wave_wash(2.0, r, 0.4, 0.4), 1100)
    place(y, lap * 0.6, 0.9)
    return decor_stereo(y, r, 0.3)


@sfx('sfx_prop_sailboat', 'props', 'Sail and rope movement', "jedrilica on screen", -27, ENV, vol=0.45, priority=2, cooldown=8000,
     max_sim=1, stereo=True)
def prop_sailboat():
    r = rng(703); n = N(2.8); t = np.linspace(0, 1, n)
    fl = 0.5 + 0.5 * np.abs(np.sin(np.pi * np.cumsum(9 + 6 * smooth(n, 3, r)) / SR))
    sail = bp(noise(n, r, 'pink'), 250, 2600) * fl * np.sin(np.pi * np.clip((t - 0.05) / 0.55, 0, 1)) ** 2 * 0.6
    y = sail.copy()
    place(y, friction_creak(0.45, r, (40, 90), (420, 980, 1900), (14, 16, 18)) * 0.12, 1.5)
    place(y, brass_tink(2650, r, 0.35) * 0.1, 0.95)
    place(y, brass_tink(2880, r, 0.3) * 0.07, 1.05)
    return decor_stereo(y, r, 0.35)


@sfx('sfx_prop_oar', 'props', 'Wooden oar entering the water', "rowing boat (camac/veslo) on screen; replaces ONESHOT.veslo",
     -26, (0.5, 2.0), vol=0.45, priority=2, cooldown=3000, max_sim=1, stereo=True, legacy='ONESHOT.veslo')
def prop_oar():
    r = rng(704); n = N(1.4); y = np.zeros(n)
    place(y, wood_tap(240, r, 0.15, 0.8, 0.2) * 0.4, 0.0)
    place(y, friction_creak(0.15, r, (60, 110), (300, 800, 1600)) * 0.1, 0.0)
    m = N(0.5); tt = np.linspace(0, 1, m)
    entry = tv_filter(noise(m, r, 'pink'), 2400 * (700 / 2400) ** tt, 1.6) * hann_env(m, 0.15) * 0.6
    place(y, entry, 0.16)
    place(y, splash(r, 0.45, 0.5, 2500) * 0.6, 0.16)
    place(y, bubbles(N(0.6), np.sort(r.uniform(0.0, 0.5, 6)), r, 1200, 3000, 0.25), 0.5)
    return decor_stereo(y, r, 0.25)


@sfx('sfx_prop_dolphin', 'props', 'Dolphin breaking the surface', "dupin() visible / dolphin jump event", -26, ENV, vol=0.5, priority=3,
     cooldown=10000, max_sim=1, stereo=True)
def prop_dolphin():
    r = rng(705); n = N(2.2); y = np.zeros(n)
    place(y, splash(r, 0.8, 0.8, 4000) * 0.7, 0.0)
    m = N(0.32); tt = np.linspace(0, 1, m)
    blow = tv_filter(noise(m, r), 1400 * (900 / 1400) ** tt, 2.0) * np.where(tt < 0.08, tt / 0.08, np.exp(-(tt - 0.08) / 0.25)) * 0.9
    blow += lp(noise(m, r, 'brown'), 300) * np.where(tt < 0.08, tt / 0.08, np.exp(-(tt - 0.08) / 0.15)) * 0.3
    place(y, blow, 0.22)
    place(y, splash(r, 0.6, 0.9, 3500) * 0.55, 1.05)
    out = decor_stereo(y, r, 0.3)
    p = np.linspace(-0.3, 0.3, n)
    return out * np.stack([np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)], 1) * 1.41


# =====================================================================  G. UI (mono)
@sfx('sfx_ui_hover', 'ui', 'Menu hover', 'pointerenter on menu buttons (desktop only; skip on touch)', -33, UI, vol=0.4, priority=1,
     cooldown=40, max_sim=1)
def ui_hover():
    r = rng(801)
    return lp(wood_tap(1500, r, 0.07, 1.1, 0.0), 5000, 2)


@sfx('sfx_ui_select', 'ui', 'Menu select / confirm', 'any menu button click (generic)', -26, UI, vol=0.6, priority=4, cooldown=60, max_sim=1)
def ui_select():
    r = rng(802); y = wood_tap(880, r, 0.16, 1.0, 0.35)
    place(y, brass_tink(2350, r, 0.15) * 0.18, 0.008)
    return y


@sfx('sfx_ui_back', 'ui', 'Back / close', 'closing a panel (pasClose, info close, hidePopup)', -27, UI, vol=0.55, priority=4, cooldown=60, max_sim=1)
def ui_back():
    r = rng(803); y = np.zeros(N(0.18))
    place(y, wood_tap(760, r, 0.1, 1.1, 0.3), 0.0, 0.8)
    place(y, wood_tap(540, r, 0.12, 1.0, 0.25), 0.055, 0.9)
    return y


@sfx('sfx_ui_start', 'ui', 'Start flight', 'start() - flight begins', -24, UI, vol=0.7, priority=6, cooldown=500, max_sim=1)
def ui_start():
    r = rng(804); y = np.zeros(N(0.3))
    place(y, _paper(r, 0.1, 3000, 0.4), 0.0)
    place(y, _mpl('D5', 0.26, r, 0.6, 0.3), 0.02)
    place(y, _mpl('A5', 0.24, r, 0.65, 0.3), 0.075)
    place(y, brass_tink(hz('A6'), r, 0.22) * 0.25, 0.075)
    return y


@sfx('sfx_ui_pause', 'ui', 'Pause', 'pauseBtn -> paused = true', -27, UI, vol=0.55, priority=4, cooldown=150, max_sim=1)
def ui_pause():
    r = rng(805); y = wood_tap(470, r, 0.16, 0.9, 0.25)
    y += thump(r, 120, 80, 0.16, 0.03) * 0.25
    return y


@sfx('sfx_ui_resume', 'ui', 'Resume', 'pauseBtn -> paused = false', -27, UI, vol=0.55, priority=4, cooldown=150, max_sim=1)
def ui_resume():
    r = rng(806); y = np.zeros(N(0.16))
    place(y, wood_tap(560, r, 0.1, 1.0, 0.25), 0.0, 0.8)
    place(y, wood_tap(840, r, 0.1, 1.1, 0.3), 0.045, 0.85)
    return y


@sfx('sfx_ui_toggle_on', 'ui', 'Toggle on (sound/music/vibration on)', 'sound/music/vibration button switched on', -27, UI, vol=0.55,
     priority=4, cooldown=100, max_sim=1)
def ui_toggle_on():
    r = rng(807); y = np.zeros(N(0.14))
    place(y, stone_tap(3100, r, 0.02) * 0.5, 0.0)
    place(y, brass_tink(2650, r, 0.12) * 0.6 * adsr(N(0.12), 0.0005, 0.04), 0.012)
    return y


@sfx('sfx_ui_toggle_off', 'ui', 'Toggle off', 'sound/music/vibration button switched off (play before muting)', -28, UI, vol=0.55,
     priority=4, cooldown=100, max_sim=1)
def ui_toggle_off():
    r = rng(808); y = np.zeros(N(0.1))
    place(y, brass_tink(1850, r, 0.1) * 0.55 * adsr(N(0.1), 0.0005, 0.025), 0.0)
    place(y, lp(stone_tap(2300, r, 0.03), 5000, 2) * 0.45, 0.018)
    return y


@sfx('sfx_ui_character_select', 'ui', 'Bird chosen (Galeb / Vranac)', 'primijeniLik() / character card click', -25, UI, vol=0.6,
     priority=5, cooldown=200, max_sim=1)
def ui_character_select():
    r = rng(809); n = N(0.28); y = np.zeros(n)
    e = hann_env(N(0.14), 0.3)
    place(y, feather_rustle(N(0.14), e, r, 1500, 6000, 2000) * 0.7 + whoosh(0.14, 1500, 1.4, r) * e * 0.4, 0.0)
    place(y, _mpl('A5', 0.24, r, 0.6, 0.3), 0.05)
    return y


@sfx('sfx_ui_city_select', 'ui', 'City chosen on the route map', 'putPick(ev) - city selected', -25, UI, vol=0.6, priority=5,
     cooldown=200, max_sim=1)
def ui_city_select():
    r = rng(810); y = np.zeros(N(0.28))
    place(y, lp(stone_tap(1150, r, 0.08), 3800, 2), 0.0, 0.7)
    place(y, _mpl('E5', 0.26, r, 0.6, 0.35), 0.03)
    return y


@sfx('sfx_ui_difficulty_select', 'ui', 'Difficulty / mode chosen', 'applyMode() / difficulty buttons', -26, UI, vol=0.55, priority=4,
     cooldown=150, max_sim=1)
def ui_difficulty_select():
    r = rng(811); y = np.zeros(N(0.2))
    for i, f in enumerate((2100, 1980, 1850)):
        place(y, lp(wood_tap(f * 0.8, r, 0.04, 1.3, 0.0), 5000, 2) * 0.35, i * 0.026)
    place(y, wood_tap(690, r, 0.12, 1.0, 0.1), 0.08)
    return y


@sfx('sfx_ui_postcard_open', 'ui', 'Postcard opens', 'postcard / share card shown (end screen razglednica)', -27, UI, vol=0.55, priority=4,
     cooldown=300, max_sim=1)
def ui_postcard_open():
    r = rng(812); y = np.zeros(N(0.3))
    place(y, _paper(r, 0.16, 2200, 1.0, 0.7), 0.0)
    place(y, _paper(r, 0.12, 3200, 0.6, 0.5), 0.13)
    return y


@sfx('sfx_ui_postcard_export', 'ui', 'Postcard exported / shared', 'postcard image saved or share() resolved', -26, UI, vol=0.6,
     priority=4, cooldown=500, max_sim=1)
def ui_postcard_export():
    r = rng(813); y = np.zeros(N(0.3))
    m = N(0.16); tt = np.linspace(0, 1, m)
    place(y, whoosh(0.16, 1500 * (3200 / 1500) ** tt, 1.6, r, color='white') * hann_env(m, 0.5) * 0.5, 0.0)
    place(y, brass_tink(hz('D7') / 1.0, r, 0.2) * 0.3, 0.12)
    place(y, _mpl('D6', 0.18, r, 0.5, 0.25), 0.12)
    return y


@sfx('sfx_ui_passport_stamp', 'ui', 'Passport stamp', 'passport (putovnica) page shows a newly earned stamp', -25, UI, vol=0.6, priority=5,
     cooldown=200, max_sim=1)
def ui_passport_stamp():
    r = rng(814)
    return _stamp(r)


# =====================================================================  H. PROGRESSION (stingers)
def _prog(name, event, trigger, lufs=-20, dur=STING, vol=0.75, priority=8, legacy=None, group=None):
    return sfx(name, 'progression', event, trigger, lufs, dur, vol=vol, priority=priority, cooldown=1500, max_sim=1,
               category='stinger', legacy=legacy, group=group)


@_prog('sfx_progress_milestone', 'Score milestone reached', 'addScore(): milestoneFor(score) changes -> popMilestone()')
def progress_milestone():
    r = rng(901); y = np.zeros(N(1.0))
    for i, nt in enumerate(('D5', 'F#5', 'A5')):
        place(y, _mpl(nt, 0.9 - i * 0.08, r, 0.65), i * 0.08)
    place(y, glass(hz('D6'), 0.75, r, 1.8) * 0.3, 0.24)
    place(y, _mpl('D6', 0.7, r, 0.6), 0.24)
    return y


@_prog('sfx_progress_medal_bronze', 'Bronze medal', 'end screen: medalFor(score).name == "Bronza" (also pasSet level 1)', group='medal')
def medal_bronze():
    r = rng(911); y = np.zeros(N(1.2))
    for i, nt in enumerate(('D4', 'A4', 'D5')):
        place(y, guitar(hz(nt), 1.1 - i * 0.1, r, 0.7), i * 0.1)
    place(y, wood_tap(520, r, 0.1, 1, 0.2) * 0.2, 0.0)
    return y


@_prog('sfx_progress_medal_silver', 'Silver medal', 'end screen: medal "Srebro" (pasSet level 2)', group='medal')
def medal_silver():
    r = rng(912); y = np.zeros(N(1.5))
    place(y, guitar(hz('D4'), 1.4, r, 0.55), 0.0)
    for i, nt in enumerate(('D5', 'F#5', 'A5', 'D6')):
        place(y, _mpl(nt, 1.2, r, 0.6), i * 0.09)
    place(y, glass(hz('A6'), 1.1, r, 2) * 0.13, 0.3)
    return y


@_prog('sfx_progress_medal_gold', 'Gold medal', 'end screen: medal "Zlato" (pasSet level 3)', group='medal')
def medal_gold():
    r = rng(913); y = np.zeros(N(2.0))
    place(y, strum([hz('D3'), hz('A3'), hz('D4'), hz('F#4')], 1.9, r, 0.03, 0.7, inst=guitar), 0.0)
    for i, nt in enumerate(('A4', 'D5', 'F#5', 'A5', 'D6')):
        place(y, _mpl(nt, 1.6, r, 0.6), 0.05 + i * 0.08)
    place(y, lp(bell(hz('D5'), 1.6, r, 0.7, strike=0.1), 5000) * 0.3, 0.37)
    place(y, tremolo(hz('D6'), 0.6, r, 14, 0.25, swell=lambda u: (1 - u) ** 1.5), 0.45)
    return y


@_prog('sfx_progress_medal_platinum', 'Platinum medal', 'end screen: medal "Platina" (score >= 50)', group='medal')
def medal_platinum():
    r = rng(914); y = np.zeros(N(2.45))
    place(y, strum([hz('G3'), hz('D4'), hz('G4'), hz('B4')], 0.7, r, 0.03, 0.6, inst=guitar), 0.0)
    place(y, strum([hz('D3'), hz('A3'), hz('D4'), hz('F#4'), hz('A4')], 1.9, r, 0.03, 0.7, inst=guitar), 0.5)
    place(y, tremolo(hz('B5'), 0.45, r, 14, 0.35), 0.02)
    place(y, tremolo(hz('A5'), 0.3, r, 14, 0.35), 0.5)
    place(y, tremolo(hz('D6'), 0.8, r, 14, 0.4, swell=lambda u: (1 - u) ** 1.3), 0.8)
    place(y, lp(bell(hz('A5'), 1.5, r, 0.6, strike=0.08), 5000) * 0.22, 0.5)
    for i, nt in enumerate(('D6', 'F#6', 'A6')):
        place(y, glass(hz(nt), 1.3, r, 2) * 0.1, 0.55 + i * 0.07)
    return y


@_prog('sfx_progress_city_arrival', 'Arriving at a new city', 'updateScene(): new SCENES[sceneShown] - replaces gradSignal() + chime()',
       legacy='gradSignal(); chime()', lufs=-22)
def progress_city_arrival():
    r = rng(921); n = N(1.9); y = np.zeros(n); t = np.linspace(0, 1, n)
    y += whoosh(1.9, 700, 1.6, r) * np.sin(np.pi * t) ** 2 * 0.15
    place(y, lp(bell(hz('A4'), 1.8, r, 0.6, strike=0.08), 3000) * 0.3, 0.0)
    for i, nt in enumerate(('A4', 'D5', 'E5', 'F#5')):
        place(y, _mpl(nt, 1.3 - i * 0.1, r, 0.6), 0.12 + i * 0.15)
    return y


@_prog('sfx_progress_city_unlocked', 'City unlocked on the route', 'first arrival at a city (firstVisit(sc)) / route node unlocked')
def progress_city_unlocked():
    r = rng(922); y = np.zeros(N(1.5))
    place(y, brass_tink(1650, r, 0.12) * 0.4 * adsr(N(0.12), 0.0005, 0.03), 0.0)
    place(y, stone_tap(2400, r, 0.03) * 0.4, 0.0)
    place(y, wood_tap(620, r, 0.1, 1.2, 0.3) * 0.5, 0.09)
    place(y, strum([hz('D4'), hz('A4'), hz('D5'), hz('F#5'), hz('A5')], 1.3, r, 0.035, 0.7, up=False), 0.18)
    place(y, glass(hz('D6'), 1.0, r, 2) * 0.15, 0.35)
    return y


@_prog('sfx_progress_relic_discovered', 'Relic discovered (album entry)', "collectItems() kind=='kraj' -> albumSet() for a new entry (after pickup_relic)")
def progress_relic_discovered():
    r = rng(923); n = N(2.1)
    y = modal([(164.8, 0.5, 1.2), (392, 0.3, 0.8), (659, 0.15, 0.5)], n, r, True) * adsr(n, 0.004, 100) * 0.35
    place(y, guitar(hz('E3'), 2.0, r, 0.6), 0.0)
    for i, nt in enumerate(('E4', 'B4', 'D5', 'E5')):
        place(y, _mpl(nt, 1.7 - i * 0.15, r, 0.55), 0.1 + i * 0.18)
    place(y, lp(bell(hz('E4'), 1.9, r, 0.5, strike=0.05), 3500) * 0.25, 0.1)
    return y


@_prog('sfx_progress_mission_complete', 'Location mission complete', 'misijaGotova(name, m) / misijaSlavlje(name)')
def progress_mission_complete():
    r = rng(924); y = np.zeros(N(1.7))
    place(y, strum([hz('A3'), hz('E4'), hz('A4'), hz('C#5')], 0.6, r, 0.025, 0.65, inst=guitar), 0.0)
    place(y, strum([hz('D4'), hz('A4'), hz('D5'), hz('F#5')], 1.25, r, 0.025, 0.7, inst=guitar), 0.42)
    place(y, _mpl('C#6', 0.4, r, 0.5), 0.0)
    place(y, _mpl('D6', 1.1, r, 0.6), 0.42)
    place(y, glass(hz('D6'), 1.1, r, 2) * 0.12, 0.45)
    return y


@_prog('sfx_progress_journey_complete', 'Whole route Pula -> Dubrovnik complete', 'putSlavlje() / passport complete (pasFullPending)', lufs=-20)
def progress_journey_complete():
    r = rng(925); y = np.zeros(N(2.5))
    chords = ((0.0, ('D3', 'A3', 'D4', 'F#4'), 'F#5'), (0.42, ('G3', 'D4', 'G4', 'B4'), 'G5'),
              (0.84, ('A3', 'E4', 'A4', 'C#5'), 'A5'), (1.26, ('D3', 'A3', 'D4', 'F#4', 'A4'), 'D6'))
    for i, (tt, ch, top) in enumerate(chords):
        last = i == len(chords) - 1
        place(y, strum([hz(c) for c in ch], 1.2 if last else 0.6, r, 0.025, 0.65, inst=guitar), tt)
        if last:
            place(y, tremolo(hz(top), 0.75, r, 14, 0.4, swell=lambda u: (1 - u) ** 1.4), tt)
        else:
            place(y, _mpl(top, 0.5, r, 0.6), tt)
    place(y, lp(bell(hz('D5'), 1.2, r, 0.6, strike=0.08), 4500) * 0.28, 1.26)
    place(y, glass(hz('A6'), 1.1, r, 2) * 0.1, 1.3)
    return y


@_prog('sfx_progress_new_record', 'New personal record', 'end screen: score > previous best (renderBoard hi)')
def progress_new_record():
    r = rng(926); y = np.zeros(N(1.9))
    for i, nt in enumerate(('D5', 'E5', 'F#5', 'G5', 'A5', 'B5', 'C#6')):
        place(y, _mpl(nt, 0.5, r, 0.45 + i * 0.03), i * 0.045)
    place(y, strum([hz('D4'), hz('A4'), hz('D5'), hz('F#5')], 1.5, r, 0.02, 0.7, inst=guitar), 0.33)
    place(y, _mpl('D6', 1.3, r, 0.7), 0.33)
    place(y, lp(bell(hz('D5'), 1.3, r, 0.7, strike=0.08), 5000) * 0.25, 0.34)
    return y


# =====================================================================  I. AMBIENCE LOOPS (stereo, periodic)
def amb(name, event, trigger, lufs, vol=0.35, legacy=None):
    return sfx(name, 'ambience', event, trigger, lufs, LOOP, vol=vol, priority=1, cooldown=0, max_sim=1,
               loop=True, category='ambience', stereo=True, legacy=legacy)


def cyc(x, fn):
    """apply a (non-circular) process to a periodic signal and keep it periodic."""
    n = len(x)
    y = fn(np.concatenate([x, x, x], axis=0))
    return y[n:2 * n]


def LL(sec):
    return int(round(sec * SR / 256)) * 256


def _sea(seed, sec, waves, size, bright, bed, lap_rate, slap):
    r = rng(seed); n = LL(sec); out = np.zeros((n, 2))
    t = 0.0
    while t < sec:
        d = r.uniform(4.0, 6.5)
        w = wave_wash(d, r, size * r.uniform(0.7, 1.1), bright * r.uniform(0.8, 1.1))
        p = r.uniform(-0.7, 0.7)
        s = pan(w, p)
        for c in range(2): place_wrap(out[:, c], s[:, c], N(t))
        s2 = pan(lp(w, 1500) * 0.35, -p)
        for c in range(2): place_wrap(out[:, c], s2[:, c], N(t + 0.03))
        t += sec / waves * r.uniform(0.75, 1.25)
    for c in range(2):
        b = circ_filter(circ_noise(n, rng(seed + 10 + c), 'brown'), band_shape(25, 380, 2))
        mod = 0.7 + 0.3 * circ_smooth(n, 0.25, rng(seed + 20 + c))
        out[:, c] += b * bed * mod
        surf = circ_filter(circ_noise(n, rng(seed + 30 + c), 'pink'), band_shape(150, 400 + 1100 * bright, 2))
        out[:, c] += surf * 0.12 * size * (0.8 + 0.2 * circ_smooth(n, 0.4, rng(seed + 40 + c)))
    k = int(sec * lap_rate)
    for i in range(k):
        sp = splash(r, r.uniform(0.15, 0.3), 0.35, 2600) * slap * r.uniform(0.3, 1.0)
        s = pan(lp(sp, 3500), r.uniform(-0.9, 0.9))
        ii = r.integers(0, n)
        for c in range(2): place_wrap(out[:, c], s[:, c], ii)
    return out


@amb('amb_adriatic_waves_day', 'Gentle daylight Adriatic waves', "palIdx==0 (Podne) over sea scenes; crossfade on phase change", -34,
     legacy='ambWater noise layer (noiseGain)')
def amb_waves_day():
    return _sea(1001, 20, 4, 1.0, 1.0, 0.5, 0.9, 0.25)


@amb('amb_adriatic_waves_evening', 'Softer evening sea', 'palIdx==1 (Zalazak)', -35)
def amb_waves_evening():
    return _sea(1002, 20, 3, 0.8, 0.65, 0.55, 0.5, 0.18)


@amb('amb_adriatic_waves_bluehour', 'Restrained blue-hour sea', 'palIdx==2 (Plavi sat)', -36)
def amb_waves_bluehour():
    return _sea(1003, 22, 3, 0.65, 0.4, 0.6, 0.25, 0.12)


@amb('amb_harbor', 'Working harbour - water on hulls, halyards, ropes', "Split / Zadar scenes (back:backLuka) under the sea layer", -35)
def amb_harbor():
    r = rng(1011); sec = 22; n = LL(sec); out = np.zeros((n, 2))
    for c in range(2):
        b = circ_filter(circ_noise(n, rng(1012 + c), 'brown'), band_shape(30, 500, 2))
        out[:, c] += b * 0.35 * (0.75 + 0.25 * circ_smooth(n, 0.3, rng(1014 + c)))
    t = 0.0
    while t < sec:
        w = lp(wave_wash(r.uniform(1.2, 2.2), r, 0.35, 0.45), 1100) * r.uniform(0.25, 0.6)
        s = pan(w, r.uniform(-0.8, 0.8))
        for c in range(2): place_wrap(out[:, c], s[:, c], N(t))
        t += r.uniform(0.6, 2.4)
    for _ in range(5):
        tt = r.uniform(0, sec); p = r.uniform(-0.9, 0.9); f = r.uniform(2050, 2700)
        for k in range(r.integers(1, 4)):
            s = pan(brass_tink(f * r.uniform(0.98, 1.02), r, 0.7) * 0.07 * r.uniform(0.5, 1), p)
            for c in range(2): place_wrap(out[:, c], s[:, c], N(tt + k * r.uniform(0.12, 0.3)))
    for _ in range(4):
        cr = friction_creak(r.uniform(0.5, 1.0), r, (20, 60), (200, 520, 1050)) * 0.05
        s = pan(cr, r.uniform(-0.8, 0.8))
        for c in range(2): place_wrap(out[:, c], s[:, c], N(r.uniform(0, sec)))
    for _ in range(3):
        s = pan(wood_tap(r.uniform(110, 160), r, 0.3, 0.5, 0.05) * 0.12, r.uniform(-0.6, 0.6))
        for c in range(2): place_wrap(out[:, c], s[:, c], N(r.uniform(0, sec)))
    # distant gull and a far engine
    g = lp(gull_syllable(0.3, 760, 1050, 650, r, 0.28, 0.25), 3000) * 0.05
    s = pan(g, 0.6)
    for c in range(2): place_wrap(out[:, c], s[:, c], N(7.3))
    tt = tax(n)
    eng = (np.sin(2 * np.pi * (round(47 * sec) / sec) * tt) + 0.5 * np.sin(2 * np.pi * (round(94 * sec) / sec) * tt)) * \
          (0.7 + 0.3 * np.sin(2 * np.pi * (round(5.5 * sec) / sec) * tt)) * 0.02
    out += np.stack([eng, eng * 0.8], 1)
    return out


def walla_voice(n, r, circular=True):
    out = np.zeros(n)
    vowels = ((700, 1200), (400, 2000), (300, 2300), (500, 900), (350, 800), (600, 1700))
    t = r.uniform(0, 1)
    base = r.uniform(105, 230)
    while t < n / SR:
        if r.random() < 0.15:
            t += r.uniform(0.4, 1.6); continue
        d = r.uniform(0.11, 0.26); m = N(d)
        f0 = base * (1 + 0.12 * np.sin(np.linspace(0, np.pi, m)) * r.uniform(-1, 1)) * r.uniform(0.92, 1.08)
        per = SR / f0
        imp = np.zeros(m); pos = 0.0
        while pos < m:
            imp[int(pos)] = 1.0; pos += per[int(pos)]
        g = ss.lfilter([1], [1, -0.95], imp)
        F1, F2 = vowels[r.integers(0, len(vowels))]
        y = resonator(g, F1, 5) + resonator(g, F2, 7) * 0.5
        e = np.sin(np.linspace(0, np.pi, m)) ** 1.5
        place_wrap(out, y * e, N(t))
        t += d + r.uniform(0.0, 0.08)
    return out


@amb('amb_coastal_town', 'Quiet town atmosphere (no intelligible speech)', 'folk/town scenes: Split riva, Dubrovnik Stradun, Sibenik', -36,
     legacy='ambHum layer (Grundrauschen der Stadt)')
def amb_coastal_town():
    r = rng(1021); sec = 24; n = LL(sec); out = np.zeros((n, 2))
    for i in range(12):
        v = walla_voice(n, rng(1100 + i))
        v = cyc(v, lambda x: lp(hp(x, 180), 1300, 2))
        s = pan(v * r.uniform(0.4, 1.0), r.uniform(-0.9, 0.9))
        out += s
    out *= 0.05
    for c in range(2):
        b = circ_filter(circ_noise(n, rng(1030 + c), 'pink'), band_shape(60, 700, 2))
        out[:, c] += b * 0.05
    # footsteps on limestone crossing the stereo field
    for walker in range(3):
        t0 = r.uniform(0, sec); step = r.uniform(0.48, 0.58); k = r.integers(8, 14); p0 = r.uniform(-0.9, 0.9)
        for j in range(k):
            p = np.clip(p0 + (j / k) * (0.9 if p0 < 0 else -0.9), -1, 1)
            s = pan(lp(stone_tap(r.uniform(900, 1300), r, 0.05) + thump(r, 110, 70, 0.05, 0.01) * 0.6, 2500) * 0.05 * np.sin(np.pi * (j + 1) / (k + 1)), p)
            for c in range(2): place_wrap(out[:, c], s[:, c], N(t0 + j * step + r.uniform(-0.02, 0.02)))
    for _ in range(6):
        s = pan(lp(ceramic(r.uniform(1900, 2600), r, 0.3), 4000) * 0.03, r.uniform(-0.8, 0.8))
        for c in range(2): place_wrap(out[:, c], s[:, c], N(r.uniform(0, sec)))
    cr = friction_creak(0.8, r, (30, 70), (260, 640, 1300)) * 0.015
    s = pan(cr, -0.6)
    for c in range(2): place_wrap(out[:, c], s[:, c], N(15.2))
    return out


@amb('amb_cicadas', 'Mediterranean cicadas', 'summer daytime scenes with amb.buzz (Sibenik, Makarska, Pula) - replaces ambBuzz layer', -37,
     legacy='ambBuzz layer')
def amb_cicadas():
    r = rng(1031); sec = 20; n = LL(sec); out = np.zeros((n, 2))
    specs = ((4100, 185, 3.1, -0.6, 1.0), (4400, 205, 3.6, 0.5, 0.8), (3850, 172, 2.7, 0.0, 0.6),
             (4250, 195, 4.1, -0.2, 0.45), (3700, 160, 2.2, 0.8, 0.5))
    for i, (car, pr, phr, p, g) in enumerate(specs):
        rr = rng(1040 + i)
        x = cicada_layer(n, rr, car, pr, round(phr * sec) / sec, circular=True, depth=0.8)
        swell = np.clip(0.55 + 0.45 * circ_smooth(n, 0.12, rr), 0.05, 1.2)
        out += pan(x * g * swell, p)
    out = cyc(out, lambda x: lp(x, 5500, 4))
    return out


@amb('amb_pine_wind', 'Coastal wind through pines', 'Makarska / back:backBorovi scenes', -36)
def amb_pine_wind():
    r = rng(1051); sec = 20; n = LL(sec); out = np.zeros((n, 2))
    for c in range(2):
        rr = rng(1052 + c)
        s = 0.35 + 0.18 * circ_smooth(n, 0.15, rng(1060))
        out[:, c] = pine_layer(n, rr, s, True) + wind(n, rr, s * 0.7, 0.0, circular=True) * 0.6
    for _ in range(2):
        cr = friction_creak(0.6, r, (15, 40), (300, 700, 1500)) * 0.02
        s2 = pan(cr, r.uniform(-0.7, 0.7))
        for c in range(2): place_wrap(out[:, c], s2[:, c], N(r.uniform(0, sec)))
    return out


@amb('amb_rain', 'Steady moderate rain', "weather.kind=='kisa' (crossfade in with sfx_weather_rain_start)", -35)
def amb_rain():
    sec = 16; n = LL(sec); out = np.zeros((n, 2))
    for c in range(2):
        rr = rng(1071 + c)
        d = 1100 * (1 + 0.15 * circ_smooth(n, 0.3, rng(1080)))
        out[:, c] = rain(n, rr, d, circular=True)
    return cyc(out, lambda x: lp(x, 6000, 2))


@amb('amb_bura', 'Persistent strong bura wind', "weather.kind=='bura' and the score-50 bura boss", -34)
def amb_bura():
    sec = 20; n = LL(sec); out = np.zeros((n, 2))
    base = 0.72 + 0.2 * circ_smooth(n, 0.35, rng(1090))
    for c in range(2):
        rr = rng(1091 + c)
        s = np.clip(base + 0.06 * circ_smooth(n, 1.2, rr), 0.3, 1.0)
        out[:, c] = wind(n, rr, s, 0.3, circular=True)
    return cyc(out, lambda x: lp(x, 6000))


@amb('amb_fog', 'Subdued coastal fog atmosphere', "weather.kind=='magla' / Sibenik channel fog", -38)
def amb_fog():
    r = rng(1101); sec = 20; n = LL(sec); out = np.zeros((n, 2))
    for c in range(2):
        rr = rng(1102 + c)
        s = 0.22 + 0.06 * circ_smooth(n, 0.2, rr)
        out[:, c] = wind(n, rr, s, 0.0, circular=True) * 0.8
    sea = _sea(1110, sec, 3, 0.6, 0.3, 0.5, 0.0, 0.0)
    out += cyc(sea, lambda x: lp(x, 500)) * 0.8
    b = lp(bell(hz('G4'), 3.5, r, 0.4, strike=0.02), 1200) * 0.025
    s = pan(b, 0.5)
    for c in range(2): place_wrap(out[:, c], s[:, c], N(6.0))
    return out
