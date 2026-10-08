"""The nine pieces. Each song builds a 'base' part and (for cities) a synchronous 'layer' stem."""
from compose import Song, MAJOR, MINOR, HMINOR, parse, midi

SONGS = {}


def song(fn):
    SONGS[fn.__name__] = fn
    return fn


def check(lines, bpb):
    for i, l in enumerate(lines):
        s = sum(d for _, d in parse(l))
        assert abs(s - bpb) < 1e-6, (i, l, s)
    return ' '.join(lines)


def layer_mandolin_arp(s, b0, b1, pattern, vel=0.32, step=0.5, low=55, pan=0.45):
    s.arpeggio(b0, b1, pattern, inst='mandolin', vel=vel, part='layer', low=low, pan=pan, step=step)


# ---------------------------------------------------------------- menu / title
MENU_A = ['F#5:2 E5:1', 'D5:2 A4:1', 'B4:1 D5:1 G5:1', 'F#5:3', 'D5:2 F#5:1', 'G5:1 F#5:1 E5:1', 'E5:2 C#5:1', 'A4:2 r:1']
MENU_B = ['D5:1 G5:1 B5:1', 'A5:2 F#5:1', 'G5:1 F#5:1 E5:1', 'F#5:2 D5:1', 'B4:1 D5:1 G5:1', 'F#5:2 A5:1', 'G5:1 E5:1 C#5:1', 'D5:3']


@song
def mus_menu():
    ca = ['D', 'D', 'G', 'D', 'Bm', 'Em', 'A', 'A']; cb = ['G', 'D', 'Em', 'Bm', 'G', 'D', 'A', 'D']
    s = Song('mus_menu', 80, 3, ca + cb + ca + cb, 2, MAJOR, seed=11, rt60=1.5, wet=0.2)
    A, B = check(MENU_A, 3), check(MENU_B, 3)
    s.arpeggio(0, 32, 'B 1 2 0 2 1', inst='guitar', vel=0.5, low=38, pan=-0.25, step=0.5, accent=1.15)
    s.melody(A, 0, 'mandolin', 0.62, 0.2, trem_from=0.7)
    s.melody(B, 8, 'mandolin', 0.62, 0.2, trem_from=0.7)
    s.melody(A, 16, 'mandolin', 0.6, 0.2, oct=-1, trem_from=0.7)
    s.pad(16, 32, vowel='u', vel=0.35)
    s.melody(B, 24, 'mandolin', 0.62, 0.2, trem_from=0.7)
    return s


# ---------------------------------------------------------------- Split: klapa, warm major
SPLIT_A = ['G#4:2 A4:1 B4:1', 'B4:3 G#4:1', 'A4:1.5 B4:0.5 C#5:1 A4:1', 'B4:3 r:1',
           'C#5:1.5 B4:0.5 A4:1 G#4:1', 'A4:2 F#4:1 G#4:1', 'A4:1 G#4:1 F#4:2', 'F#4:3 r:1']
SPLIT_B = ['B4:1 C#5:1 E5:2', 'D#5:1.5 C#5:0.5 B4:2', 'C#5:1 B4:1 A4:1 C#5:1', 'B4:3 r:1',
           'A4:1 B4:1 C#5:1 A4:1', 'B4:2 A4:1 F#4:1', 'G#4:3 F#4:1', 'E4:3 r:1']


@song
def mus_city_split():
    ca = ['E', 'E', 'A', 'E', 'C#m', 'F#m', 'B', 'B7']; cb = ['E', 'G#m', 'A', 'E', 'F#m', 'B', 'E', 'E']
    s = Song('mus_city_split', 72, 4, ca + cb + ca, 4, MAJOR, trans=-5, seed=21, rt60=1.8, wet=0.24)
    A, B = check(SPLIT_A, 4), check(SPLIT_B, 4)
    s.arpeggio(0, 24, 'B 2 1 2 0 2 1 2', inst='guitar', vel=0.5, low=38, pan=-0.3, step=0.5, accent=1.2)
    s.klapa(A, 0, 'o', 0.62, oct=0)
    s.klapa(B, 8, 'a', 0.62, oct=0)
    s.melody(A, 16, 'mandolin', 0.6, 0.25, oct=1, trem_from=0.6)
    s.pad(16, 24, vowel='u', vel=0.3, low=50)
    # layer: shimmering mandolin arpeggio + soft frame drum
    layer_mandolin_arp(s, 0, 24, '0 1 2 1', vel=0.4, step=0.5, low=62)
    s.drums(0, 24, {'def_drum': [(1, 0.25), (3, 0.3)], 'shaker': [(0.5, 0.18), (1.5, 0.14), (2.5, 0.18), (3.5, 0.14)]}, part='layer')
    return s


# ---------------------------------------------------------------- Dubrovnik: solemn minor klapa in stone
DUB_A = ['A4:2 F4:1 G4:1', 'A4:1 Bb4:1 G4:2', 'G4:1.5 A4:0.5 E4:2', 'F4:3 r:1',
         'D5:2 C5:1 Bb4:1', 'A4:1 G4:1 Bb4:2', 'A4:2 G4:1 F4:1', 'E4:3 r:1']
DUB_B = ['D5:2 C5:1 A4:1', 'C5:1.5 A4:0.5 F4:2', 'G4:1 A4:1 Bb4:1 D5:1', 'A4:3 r:1',
         'Bb4:1 A4:1 G4:1 F4:1', 'G4:2 E4:2', 'G4:1 F4:1 E4:2', 'D4:3 r:1']


@song
def mus_city_dubrovnik():
    ca = ['Dm', 'Gm', 'C', 'F', 'Bb', 'Gm', 'A', 'A7']; cb = ['Dm', 'F', 'Gm', 'Dm', 'Bb', 'C', 'A7', 'Dm']
    ci = ['Dm', 'Bb', 'Gm', 'A7']
    s = Song('mus_city_dubrovnik', 60, 4, ca + cb + ci, 2, HMINOR, trans=-4, seed=31, rt60=2.6, wet=0.3, predelay=0.03)
    A, B = check(DUB_A, 4), check(DUB_B, 4)
    s.klapa(A, 0, 'a', 0.62, oct=0)
    s.klapa(B, 8, 'o', 0.62, oct=0)
    s.arpeggio(0, 16, 'B 0 1 2', inst='mandolin', vel=0.22, low=50, pan=-0.35, step=1.0)
    s.arpeggio(16, 20, 'B 0 1 2 1 2 0 1', inst='mandolin', vel=0.38, low=50, pan=-0.2, step=0.5)
    s.pad(16, 20, vowel='m', vel=0.3, low=48)
    s.melody('A5:4 F5:2 D5:2 G5:4 A5:4', 16, 'mandolin', 0.45, 0.3, trem_from=0.6)
    # layer: high tremolo on the chord thirds + a slow tapan heartbeat
    for rpc, pcs, st, d in s.chord_spans(0, 20):
        from compose import nearest
        s.add('mandolin_trem', st, d * 0.95, nearest(pcs[1], 76), 0.2, 0.5, 'layer', transpose=False)
    s.drums(0, 20, {'tapan': [(0, 0.35)], 'tapan_rim': [(2, 0.18)]}, part='layer')
    return s


# ---------------------------------------------------------------- Sibenik: poskočica, lively mandolins
SIB_A = ['E5:0.5 C#5:0.5 A4:0.5 C#5:0.5', 'E5:0.5 F#5:0.5 E5:1', 'D5:0.5 B4:0.5 G#4:0.5 B4:0.5', 'D5:0.5 E5:0.5 D5:1',
         'B4:0.5 D5:0.5 E5:0.5 D5:0.5', 'B4:0.5 G#4:0.5 E4:0.5 G#4:0.5', 'A4:0.5 C#5:0.5 B4:0.5 G#4:0.5', 'A4:2']
SIB_A2 = SIB_A[:6] + ['B4:0.5 D5:0.5 C#5:0.5 B4:0.5', 'A4:1 E4:1']
SIB_B = ['F#5:0.5 E5:0.5 D5:0.5 F#5:0.5', 'A5:1 F#5:1', 'E5:0.5 C#5:0.5 A4:0.5 C#5:0.5', 'E5:2',
         'D5:0.5 E5:0.5 F#5:0.5 E5:0.5', 'D5:0.5 B4:0.5 G#4:0.5 B4:0.5', 'A4:0.5 C#5:0.5 E5:0.5 C#5:0.5', 'A4:1 r:1']
SIB_B2 = SIB_B[:7] + ['A4:2']


@song
def mus_city_sibenik():
    ca = ['A', 'A', 'E', 'E', 'E', 'E', 'A', 'A']; ca2 = ['A', 'A', 'E', 'E', 'E', 'E', 'E7', 'A']
    cb = ['D', 'D', 'A', 'A', 'E', 'E', 'A', 'A E']; cb2 = ['D', 'D', 'A', 'A', 'E', 'E', 'A', 'A']
    prog = ca + ca2 + cb + cb2
    s = Song('mus_city_sibenik', 126, 2, prog + prog, 9, MAJOR, seed=41, rt60=1.1, wet=0.16)
    lines = [check(SIB_A, 2), check(SIB_A2, 2), check(SIB_B, 2), check(SIB_B2, 2)]
    for k, l in enumerate(lines):
        s.melody(l, 8 * k, 'mandolin', 0.62, 0.2, trem_from=0.45)
        s.melody(l, 32 + 8 * k, 'mandolin', 0.6, 0.25, trem_from=0.45)
    # second pass: a second mandolin a third below
    for k, l in enumerate(lines):
        t = (32 + 8 * k) * 2
        for m, d in parse(l):
            if m is not None:
                s.add('mandolin_trem' if d >= 1 else 'mandolin', t + 0.01, d, s.scale_step(m, -2), 0.4, -0.3, 'base')
            t += d
    s.basses(0, 64, beats=(0,), alt_fifth=True, vel=0.6)
    s.strum(0, 64, (1.0,), inst='guitar_mute', vel=0.45, low=55, pan=-0.2)
    s.strum(0, 64, (0.5, 1.5), inst='guitar_mute', vel=0.16, low=60, pan=0.3)
    s.drums(0, 64, {'tapan': [(0, 0.4)], 'tapan_rim': [(1, 0.3), (1.5, 0.15)]})
    s.drums(0, 64, {'def_drum': [(0.5, 0.25), (1.5, 0.25)], 'shaker': [(0.25, 0.12), (0.75, 0.12), (1.25, 0.12), (1.75, 0.12)]}, part='layer')
    layer_mandolin_arp(s, 0, 64, '0 2 1 2', vel=0.24, step=0.25, low=64, pan=0.5)
    return s


# ---------------------------------------------------------------- Makarska: relaxed minor, guitar + klapa
MAK_A = ['F#4:2 D4:1', 'B4:2 A4:1', 'G4:1 F#4:1 E4:1', 'F#4:3', 'G4:2 B4:1', 'F#4:2 D4:1', 'E4:1 C#4:1 E4:1', 'F#4:2 r:1']
MAK_B = ['B4:2 D5:1', 'A4:2 F#4:1', 'G4:1 A4:1 B4:1', 'F#4:3', 'G4:1 B4:1 D5:1', 'C#5:2 A4:1', 'A#4:1 C#5:1 A#4:1', 'B4:3']


@song
def mus_city_makarska():
    ca = ['Bm', 'Bm', 'G', 'D', 'Em', 'Bm', 'F#7', 'F#7']; cb = ['G', 'D', 'Em', 'Bm', 'G', 'A', 'F#', 'Bm']
    s = Song('mus_city_makarska', 84, 3, ca + cb + ca + cb, 11, HMINOR, trans=-4, seed=51, rt60=1.7, wet=0.22)
    A, B = check(MAK_A, 3), check(MAK_B, 3)
    s.arpeggio(0, 32, 'B 2 1 2 0 2', inst='guitar', vel=0.52, low=36, pan=-0.3, step=0.5, accent=1.2)
    s.melody(A, 0, 'mandolin', 0.6, 0.25, oct=1, trem_from=0.6)
    s.klapa(B, 8, 'o', 0.6, oct=0)
    s.klapa(A, 16, 'a', 0.6, oct=0)
    s.melody(B, 24, 'mandolin', 0.6, 0.25, oct=1, trem_from=0.6)
    s.pad(24, 32, vowel='u', vel=0.3, low=50)
    layer_mandolin_arp(s, 0, 32, '2 1 0 1 2 1', vel=0.36, step=0.5, low=62, pan=0.5)
    s.drums(0, 32, {'shaker': [(0, 0.16), (0.5, 0.1), (1, 0.14), (1.5, 0.1), (2, 0.14), (2.5, 0.1)], 'def_drum': [(0, 0.22)]}, part='layer')
    return s


# ---------------------------------------------------------------- Zadar: open major, breathing pipes
ZAD_A = ['A4:2 C5:2', 'G4:2 E4:1 G4:1', 'F4:1 A4:1 D5:2', 'D5:1 C5:1 Bb4:2',
         'A4:3 C5:1', 'D5:2 C5:1 Bb4:1', 'A4:1 G4:1 E4:1 G4:1', 'G4:3 r:1']
ZAD_B = ['A4:2 F4:1 A4:1', 'C5:2 A4:2', 'D5:1.5 C5:0.5 Bb4:2', 'A4:3 r:1',
         'Bb4:1 A4:1 G4:1 Bb4:1', 'G4:2 C5:2', 'A4:2 G4:1 F4:1', 'G4:3 r:1']


@song
def mus_city_zadar():
    ca = ['F', 'C', 'Dm', 'Bb', 'F', 'Bb', 'C', 'C']; cb = ['Dm', 'Am', 'Bb', 'F', 'Gm', 'C', 'F', 'C']
    ci = ['F', 'Bb', 'F', 'C']
    s = Song('mus_city_zadar', 66, 4, ca + cb + ci, 5, MAJOR, trans=-3, seed=61, rt60=2.0, wet=0.26)
    A, B = check(ZAD_A, 4), check(ZAD_B, 4)
    s.pad(0, 20, inst='pipe_pad', vel=0.15, low=50, voicing=(0, 1, 2))
    s.klapa(A, 0, 'o', 0.6, oct=0)
    s.klapa(B, 8, 'a', 0.6, oct=0)
    s.arpeggio(0, 20, 'B 1 2 0', inst='guitar', vel=0.45, low=38, pan=-0.3, step=1.0)
    s.melody('A5:2 C6:2 D6:2 Bb5:2 A5:2 F5:2 G5:4', 16, 'mandolin', 0.55, 0.3, trem_from=0.6)
    layer_mandolin_arp(s, 0, 20, '0 1 2 1', vel=0.36, step=0.5, low=64, pan=0.5)
    s.drums(0, 20, {'def_drum': [(0, 0.2), (2, 0.16)], 'shaker': [(1, 0.12), (3, 0.12)]}, part='layer')
    return s


# ---------------------------------------------------------------- Pula: Istrian two-part on the six-tone scale
PULA_P1 = ['F5:0.5 Gb5:0.5 F5:0.5 Eb5:0.5', 'D5:0.5 F5:0.5 Gb5:1', 'Ab5:0.5 Gb5:0.5 F5:0.5 Gb5:0.5', 'F5:1.5 r:0.5',
           'Gb5:0.5 Ab5:0.5 A5:0.5 Ab5:0.5', 'Gb5:0.5 F5:0.5 Gb5:1', 'F5:0.5 Eb5:0.5 F5:0.5 Eb5:0.5', 'D5:1.5 r:0.5']
PULA_P2 = ['A5:1 Ab5:0.5 Gb5:0.5', 'Ab5:0.5 A5:0.5 Ab5:1', 'Gb5:0.5 F5:0.5 Gb5:0.5 Ab5:0.5', 'Gb5:1.5 r:0.5',
           'F5:0.5 Gb5:0.5 F5:0.5 Eb5:0.5', 'F5:0.5 Gb5:0.5 F5:1', 'Eb5:1 F5:0.5 Eb5:0.5', 'D5:1.5 r:0.5']
ISTRIAN = (0, 1, 3, 4, 6, 7)          # D Eb F Gb Ab A


def istrian_pair(s, line, bar, inst, vel, oct=0, pans=(0.3, -0.3), vowel='a'):
    t = bar * s.bpb
    notes = parse(line)
    for i, (m, d) in enumerate(notes):
        if m is not None:
            up = m + 12 * oct
            lo = s.scale_step(up, -2)
            if up - lo == 6: lo = up - 12                   # avoid the bare tritone: open octave
            last = i + 1 < len(notes) and notes[i + 1][0] is None and d >= 1.5
            if last: lo = up - 12                           # phrase ends in the octave
            kw = dict(vowel=vowel) if inst == 'voice' else {}
            s.add(inst, t, d * 0.98, up, vel, pans[0], 'base', transpose=False, **kw)
            s.add(inst, t + 0.005, d * 0.98, lo - 0.0, vel * 0.85, pans[1], 'base', transpose=False, **kw)
        t += d


@song
def mus_city_pula():
    s = Song('mus_city_pula', 112, 2, ['D5'] * 64, 2, ISTRIAN, seed=71, rt60=1.2, wet=0.18)
    P1, P2 = check(PULA_P1, 2), check(PULA_P2, 2)
    istrian_pair(s, P1, 0, 'sopila', 0.42); istrian_pair(s, P2, 8, 'sopila', 0.42)
    istrian_pair(s, P1, 16, 'voice', 1.0, oct=-1); istrian_pair(s, P2, 24, 'voice', 1.0, oct=-1, vowel='o')
    istrian_pair(s, P1, 32, 'sopila', 0.42); istrian_pair(s, P2, 40, 'sopila', 0.42)
    istrian_pair(s, P1, 48, 'sopila', 0.34); istrian_pair(s, P2, 56, 'sopila', 0.34)
    istrian_pair(s, P1, 48, 'voice', 0.65, oct=-1); istrian_pair(s, P2, 56, 'voice', 0.65, oct=-1, vowel='o')
    for b in range(64):                                   # berda: open D and A, no functional harmony
        s.add('bass', b * 2, 1.0, midi('D2') if b % 4 != 3 else midi('A1'), 0.5, 0.0, 'base', transpose=False)
    s.drums(0, 64, {'tapan': [(0, 0.45)], 'tapan_rim': [(1, 0.22)]})
    s.drums(0, 64, {'def_drum': [(0.5, 0.22), (1.5, 0.22)], 'tapan': [(1.5, 0.2)], 'shaker': [(0.25, 0.1), (0.75, 0.1), (1.25, 0.1), (1.75, 0.1)]}, part='layer')
    for b in range(0, 64, 1):                             # tamburica off-beats on D/A (layer)
        s.add('mandolin', b * 2 + 0.5, 0.4, midi('A4'), 0.18, 0.45, 'layer', transpose=False)
        s.add('mandolin', b * 2 + 1.5, 0.4, midi('D5'), 0.16, 0.45, 'layer', transpose=False)
    return s


# ---------------------------------------------------------------- Fever: fast, bright, 2/4
FEV_A = ['A4:0.5 D5:0.5 F#5:0.5 D5:0.5', 'A5:1 F#5:1', 'G5:0.5 E5:0.5 C#5:0.5 E5:0.5', 'A5:2',
         'B5:0.5 A5:0.5 G5:0.5 F#5:0.5', 'E5:0.5 F#5:0.5 G5:0.5 E5:0.5', 'D5:0.5 F#5:0.5 E5:0.5 C#5:0.5', 'D5:2']
FEV_B = ['F#5:0.5 G5:0.5 A5:0.5 F#5:0.5', 'D6:1 A5:1', 'B5:0.5 A5:0.5 G5:0.5 B5:0.5', 'A5:2',
         'G5:0.5 F#5:0.5 E5:0.5 G5:0.5', 'F#5:0.5 E5:0.5 D5:0.5 F#5:0.5', 'E5:0.5 D5:0.5 C#5:0.5 E5:0.5', 'D5:1 A4:1']


@song
def mus_fever():
    ci = ['D', 'D', 'A', 'A']; ca = ['D', 'D', 'A', 'A', 'G', 'A', 'A', 'D']; cb = ['D', 'D', 'G', 'D', 'Em', 'D', 'A', 'D']
    co = ['G', 'A', 'G', 'A7']
    s = Song('mus_fever', 152, 2, ci + ca + cb + ca + cb + co, 2, MAJOR, seed=81, rt60=1.0, wet=0.14)
    A, B = check(FEV_A, 2), check(FEV_B, 2)
    s.melody(A, 4, 'mandolin', 0.66, 0.15, trem_from=0.3)
    s.melody(B, 12, 'mandolin', 0.66, 0.15, trem_from=0.3)
    for line, bar in ((A, 20), (B, 28)):
        s.melody(line, bar, 'mandolin', 0.62, 0.2, trem_from=0.3)
        t = bar * 2
        for m, d in parse(line):
            if m is not None:
                s.add('mandolin_trem' if d * s.spb >= 0.3 else 'mandolin', t + 0.01, d, s.scale_step(m, -2), 0.42, -0.35, 'base')
            t += d
    s.add('mandolin_trem', 72, 8, midi('A5'), 0.45, 0.1, 'base')       # turnaround tremolo
    s.basses(0, 40, beats=(0, 1), alt_fifth=True, vel=0.5)
    s.strum(0, 40, (0.5, 1.5), inst='guitar_mute', vel=0.34, low=57, pan=-0.25)
    s.drums(0, 40, {'tapan': [(0, 0.4)], 'tapan_rim': [(1, 0.35)], 'def_drum': [(0.5, 0.3), (1.5, 0.3)],
                    'shaker': [(0.25, 0.14), (0.75, 0.14), (1.25, 0.14), (1.75, 0.14)]})
    return s


# ---------------------------------------------------------------- End screen: calm, melancholic
END_M = ['A4:2 F4:1', 'D5:3', 'C5:2 A4:1', 'G4:3', 'F4:1 A4:1 D5:1', 'Bb4:2 G4:1', 'A4:1 C#5:1 E5:1', 'A4:3',
         'D5:2 F5:1', 'C5:3', 'Bb4:1 A4:1 G4:1', 'A4:3', 'D5:1 C5:1 Bb4:1', 'G4:2 E4:1', 'C#5:2 E4:1', 'D5:3']


@song
def mus_end_screen():
    ch = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Gm', 'A', 'A', 'Bb', 'F', 'Gm', 'Dm', 'Bb', 'C', 'A7', 'Dm']
    s = Song('mus_end_screen', 66, 3, ch, 2, HMINOR, seed=91, rt60=2.0, wet=0.26)
    s.arpeggio(0, 16, 'B 1 2 0 2 1', inst='guitar', vel=0.45, low=38, pan=-0.2, step=0.5, accent=1.15)
    s.melody(check(END_M, 3), 0, 'mandolin', 0.48, 0.25, trem_from=0.8)
    s.pad(8, 16, vowel='u', vel=0.35, low=50)
    return s
