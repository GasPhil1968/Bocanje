"""Batch 4: UI feedback and plucked-string stingers / intro title cues."""
import sys, os
import numpy as np
from scipy import signal as ss
sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import *
import meta

B = 'music'
STRING = ('physical-model synthesis: extended Karplus-Strong double-course string (mandolin-like), '
          'pick-position comb, fractional-delay tuning, wooden body resonances; original code, no samples')

def ks_string(f, dur, r, bright=0.5, t60=1.0, pick=0.18, vel=1.0):
    """one string: y = x + g * L(z) A(z) z^-N y."""
    n = int(dur*SR)
    P = SR/f
    s = 0.5 + 0.5*bright*0.98                               # one-zero loop lowpass  L = s + (1-s) z^-1
    Ld = 1 - s                                              # its low-frequency delay in samples
    N = int(np.floor(P - Ld)); frac = P - Ld - N
    if frac < 0.1: N -= 1; frac += 1
    c = (1-frac)/(1+frac)                                  # first-order allpass coefficient
    g = 10**(-3/(t60*f))                                   # per-period loss for the requested T60
    # denominator: (1 + c z^-1) - g z^-N (s + (1-s) z^-1)(c + z^-1)
    Lp = np.array([s, 1-s]); Ap = np.array([c, 1.0])
    fb = np.convolve(Lp, Ap)*g
    den = np.zeros(N+3); den[0] = 1; den[1] = c
    den[N:N+3] -= fb
    num = np.array([1, c])
    # excitation: filtered noise burst one period long, pick-position comb
    k = int(P)
    ex = r.uniform(-1, 1, k)
    ex = onepole_lp(ex, 1500 + 7000*bright*vel)
    d = max(1, int(pick*P)); ex2 = ex.copy(); ex2[d:] -= ex[:-d]
    x = np.zeros(n); x[:k] = ex2*vel
    y = ss.lfilter(num, den, x)
    return y

def mando_note(f, dur, r, vel=1.0, t60=None, bright=0.55):
    t60 = t60 or float(np.clip(1.6*(440/f)**0.5, 0.5, 2.2))
    a = ks_string(f*2**(r.uniform(-1.2, -0.4)/1200), dur, r, bright, t60, r.uniform(0.12, 0.2), vel)
    b = ks_string(f*2**(r.uniform(0.4, 1.2)/1200), dur, r, bright*0.95, t60*0.92, r.uniform(0.12, 0.2), vel)
    y = a + b*r.uniform(0.8, 1.0)
    return y

def guitar_note(f, dur, r, vel=1.0):
    return ks_string(f, dur, r, bright=0.25, t60=2.2, pick=0.12, vel=vel)

def body(x):
    for f, gdb, q in [(290, 4, 2.5), (470, 3, 3), (1050, 2, 2), (2600, 2.5, 2.5), (5200, -3, 1)]:
        x = peaking(x, f, gdb, q)
    return x

def room(st, r, t=0.55, wet=0.12):
    n = len(st); m = int(t*SR); tt = np.arange(m)/SR
    out = st.copy()
    for c in range(2):
        ir = r.standard_normal(m)*np.exp(-6.91*tt/t); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir**2))
        out[:, c] += wet*ss.fftconvolve(st[:, c], ir)[:n]
    return out

def strum(notes, total, r, tremolo=None, bass=None, spread=0.5, body_on=True):
    """notes: list of (freq, onset, dur, vel). tremolo: list of (freq, start, length, vel)."""
    n = int(total*SR); y = np.zeros((n, 2))
    for k, (f, on, du, vel) in enumerate(notes):
        s = mando_note(f, du+0.5, r, vel)
        env = np.ones(len(s)); e0 = int(du*SR)
        if e0 < len(s): env[e0:] = np.exp(-np.arange(len(s)-e0)/SR/0.12)   # damp after the written length
        s *= env
        i = int(on*SR); m = min(len(s), n-i)
        p = np.clip((k/(max(1, len(notes)-1)) - 0.5)*spread*2, -spread, spread)
        y[i:i+m] += pan(s[:m], p)
    for f, st, ln, vel in (tremolo or []):
        rate = r.uniform(11.5, 13.5); t = st
        j = 0
        while t < st+ln:
            v = vel*(0.75 + 0.25*((j % 2) == 0))*(1 - 0.35*(t-st)/ln)
            s = mando_note(f, 0.5, r, v, t60=0.9, bright=0.45 + 0.1*((j % 2) == 0))
            s = fade(s, 0, 0.03)
            i = int(t*SR); m = min(len(s), n-i); y[i:i+m] += pan(s[:m], r.uniform(-0.15, 0.15))
            t += 1/rate; j += 1
    if bass:
        f, on, vel = bass
        s = guitar_note(f, total, r, vel)
        i = int(on*SR); m = min(len(s), n-i); y[i:i+m] += pan(s[:m]*0.8, -0.1)
    if body_on: y = body(y)
    return y

def finish_music(y, r, peak, wet=0.12):
    y = room(y, r, wet=wet)
    y = hp(y, 60); y = dc_block(y)
    y = trim_lead(y, -45, 0.002); y = trim_tail(y, -60)
    y = fade(y, 0.001, 0.25)
    return norm_peak(y, peak)

# ------------------------------------------------------------------ UI
def ui_click(r):
    n = int(0.06*SR)
    modes = [(950, 1, 0.03, 0), (2150, 0.5, 0.02, 0), (3650, 0.25, 0.012, 0)]
    x = conv(hertz_pulse(0.0004), modal(modes, n))[:n]
    x /= np.max(np.abs(x))
    x += 0.15*np.sin(2*np.pi*880*np.arange(n)/SR)*np.exp(-np.arange(n)/SR/0.012)   # faint pitch, as tapZvuk
    return finish(x, -18, fin=0.0005, fout=0.01, tail_db=-50)

def ui_throw_select(r):
    s = mando_note(659.25, 0.3, r, 0.8, t60=0.25, bright=0.35)      # muted pluck (E5)
    s = fade(s, 0, 0.06)
    return finish(body(s), -17, fout=0.04, tail_db=-48)

def ui_perfect(r):
    a = mando_note(1318.5, 0.5, r, 1.0, t60=0.5, bright=0.6)
    b = mando_note(1975.5, 0.5, r, 0.6, t60=0.45, bright=0.55)
    x = a + np.concatenate([np.zeros(int(0.012*SR)), b])[:len(a)]*0.7
    x = lp(x, 9000, 2)
    x = body(x)[:int(0.235*SR)]
    return finish(x, -10, fout=0.05, tail_db=-50)

def ui_tick(r):
    n = int(0.05*SR); t = np.arange(n)/SR
    x = np.sin(2*np.pi*2100*t)*np.exp(-t/0.008) + 0.25*np.sin(2*np.pi*4300*t)*np.exp(-t/0.004)
    x += 0.2*hp(r.standard_normal(n), 3000)*np.exp(-t/0.0015)
    return finish(x, -16, fin=0.0003, fout=0.008, tail_db=-50)

def ui_round_win(r):
    y = strum([(587.33, 0, 0.5, 1.0), (880, 0.09, 0.55, 0.85)], 0.85, r, spread=0.25)
    return finish_music(y, r, -8, wet=0.08)

def ui_round_loss(r):
    n = int(0.6*SR)
    s = mando_note(320, 0.6, r, 0.8, t60=0.5, bright=0.3)
    # gentle downward bend via time-varying resample (320 -> ~250 Hz)
    t = np.arange(n)/SR; ratio = 1 - 0.22*np.clip(t/0.35, 0, 1)**1.5
    pos = np.cumsum(ratio); pos = pos[pos < len(s)-1]
    s = np.interp(pos, np.arange(len(s)), s)
    st = np.stack([s, s], 1)
    st = body(st)
    return finish_music(st, r, -12, wet=0.06)

# ------------------------------------------------------------------ stingers / intros (note data from the HTML)
def cue(name, r):
    if name == 'match_win':      # stinger('pobjeda'): D-F#-A-D, 75 ms, 0.85 s
        notes = [(f, i*0.075, 0.85, 1.0) for i, f in enumerate([293.66, 369.99, 440, 587.33])]
        notes += [(f, 0.62+i*0.05, 0.9, 0.7) for i, f in enumerate([440, 587.33, 739.99])]
        return strum(notes, 2.2, r, bass=(146.83, 0.0, 0.7)), -4
    if name == 'match_loss':     # stinger('poraz'): A3, F3, D3
        notes = [(220, 0, 0.7, 0.9), (174.61, 0.20, 0.9, 0.85), (146.83, 0.42, 1.2, 0.8)]
        return strum(notes, 2.1, r, spread=0.2), -7
    if name == 'stage_complete': # stinger('postaja'): A4 D5 A5, 80 ms, 0.7 s
        notes = [(f, i*0.08, 0.7, 1.0) for i, f in enumerate([440, 587.33, 880])]
        return strum(notes, 1.4, r), -5
    if name == 'trophy_win':     # stinger('pehar'): arpeggio 85 ms, then A5 D6 at 0.9 s with tremolo
        notes = [(f, i*0.085, 1.0, 1.0) for i, f in enumerate([293.66, 369.99, 440, 587.33, 739.99, 880])]
        notes += [(880, 0.9, 1.4, 0.9), (1174.66, 1.0, 1.4, 0.8)]
        trem = [(1174.66, 1.25, 1.1, 0.45), (880, 1.25, 1.1, 0.35)]
        return strum(notes, 3.2, r, tremolo=trem, bass=(146.83, 0.0, 0.8)), -3
    if name == 'achievement':    # provjeriZnacke(): D5 F#5 A5, 90 ms, 0.8 s
        notes = [(f, i*0.09, 0.8, 0.95) for i, f in enumerate([587.33, 739.99, 880])]
        return strum(notes, 1.35, r, spread=0.35), -7
    if name == 'intro_jutro':    # UVODI jutro t=5.2: D-F#-A-D, 70 ms, 0.9 s, gentle
        notes = [(f, i*0.07, 0.9, 0.85) for i, f in enumerate([293.66, 369.99, 440, 587.33])]
        notes += [(739.99, 0.55, 0.9, 0.45)]
        return strum(notes, 1.9, r), -7
    if name == 'intro_trulo':    # UVODI trulo t=5.6: A-D-F-Bb, 50 ms, 1.1 s, the loudest
        notes = [(f, i*0.05, 1.1, 1.0) for i, f in enumerate([220, 293.66, 349.23, 466.16])]
        notes += [(f, 0.45+i*0.04, 1.0, 0.8) for i, f in enumerate([293.66, 349.23, 466.16])]
        return strum(notes, 2.2, r, bass=(116.54, 0.0, 0.9)), -3.5
    if name == 'intro_maestral': # UVODI maestral t=6.0: B-D#-F#-B, 60 ms, 1.0 s
        notes = [(f, i*0.06, 1.0, 0.9) for i, f in enumerate([246.94, 311.13, 369.99, 493.88])]
        trem = [(493.88, 0.5, 0.8, 0.35)]
        return strum(notes, 2.1, r, tremolo=trem), -6
    if name == 'intro_fjaka':    # UVODI fjaka t=6.4: C-E-G-C, 90 ms, 1.2 s, the quietest
        notes = [(f, i*0.09, 1.2, 0.7) for i, f in enumerate([261.63, 329.63, 392, 523.25])]
        return strum(notes, 2.3, r, spread=0.3), -10
    raise KeyError(name)

def main():
    meta.reset(B)
    seed = 7000
    ui = [('ui/ui_click.wav', ui_click, 'button tap / menu / pause / settings / back / language',
           'tapZvuk() <- gumb() wrapper (every button) and menu taps', -0.0, 60, 2),
          ('ui/ui_throw_select.wav', ui_throw_select, 'BULANJE / TRULO selected', 'tipZvuk() <- throw-type buttons & keys', 0.0, 80, 1),
          ('ui/ui_perfect_timing.wav', ui_perfect, 'perfect timing ("TOČNO!")', 'tocnoZvuk() <- power bar hit in sweet spot', 0.0, 200, 1),
          ('ui/ui_measure_tick.wav', ui_tick, 'measuring tick (ONE tick; engine plays it 3x at 230 ms)', 'mjerenjeZvuk() <- pocniMjerenje()', 0.0, 150, 1),
          ('ui/ui_round_win.wav', ui_round_win, 'round won (points)', 'puntZvuk(true) <- zavrsiRundu()', 0.0, 500, 1),
          ('ui/ui_round_loss.wav', ui_round_loss, 'round lost', 'puntZvuk(false) <- zavrsiRundu()', 0.0, 500, 1)]
    for rel, fn, ev, hook, g, cool, conc in ui:
        seed += 1; r = rng(seed); y = fn(r); write(rel, y)
        meta.add(B, file=rel, group=os.path.basename(rel)[:-4], event=ev, hook=hook, gain_db=g, rate=[0.98, 1.02],
                 cooldown_ms=cool, max_voices=conc, status='existing-trigger',
                 method=STRING if rel.endswith(('select.wav', 'timing.wav', 'win.wav', 'loss.wav')) else meta.PROC, transcript='')
    cues = [('music/stingers/music_match_win.wav', 'match_win', 'match won', 'stinger("pobjeda") <- zavrsiRundu() (quick game / final cup step)'),
            ('music/stingers/music_match_loss.wav', 'match_loss', 'match lost', 'stinger("poraz") <- zavrsiRundu()'),
            ('music/stingers/music_stage_complete.wav', 'stage_complete', 'cup stage won', 'stinger("postaja") <- zavrsiRundu() when turnir.korak < last'),
            ('music/stingers/music_trophy_win.wav', 'trophy_win', 'trophy lifted', 'stinger("pehar") <- PEHAR screen button "podigni"'),
            ('music/stingers/music_achievement.wav', 'achievement', 'new badge (znacka)', 'provjeriZnacke() inline trzaj() chord'),
            ('music/intros/music_intro_jutro.wav', 'intro_jutro', 'intro 1 JUTRO title (t=5.2 s)', 'UVODI[0].dogadjaji t=5.2 trzaj chord'),
            ('music/intros/music_intro_trulo.wav', 'intro_trulo', 'intro 2 TRULO title (t=5.6 s)', 'UVODI[1].dogadjaji t=5.6 trzaj chord'),
            ('music/intros/music_intro_maestral.wav', 'intro_maestral', 'intro 3 MAESTRAL title (t=6.0 s)', 'UVODI[2].dogadjaji t=6.0 trzaj chord'),
            ('music/intros/music_intro_fjaka.wav', 'intro_fjaka', 'intro 4 FJAKA title (t=6.4 s)', 'UVODI[3].dogadjaji t=6.4 trzaj chord')]
    for rel, name, ev, hook in cues:
        seed += 1; r = rng(seed); y, pk = cue(name, r); y = finish_music(y, r, pk); write(rel, y)
        meta.add(B, file=rel, group=name, event=ev, hook=hook, gain_db=0.0, rate=[1.0, 1.0], cooldown_ms=0, max_voices=1,
                 status='existing-trigger', method=STRING + '; stereo, short room', transcript='',
                 note='music only - applause/crowd calls that the source schedules alongside stay separate runtime layers')

if __name__ == '__main__':
    dsp.OUT = sys.argv[1]
    main()
