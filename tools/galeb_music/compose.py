"""Tiny composition + rendering framework: songs are lists of note events rendered on a circular
time axis (sample-exact seamless loops, reverb tails wrap around)."""
import numpy as np
from instruments import INST, SR, N, rng, lp, hp, noise, tax
import instruments as I

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
      'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11),
        'sus4': (0, 5, 7), '6': (0, 4, 7, 9), 'm6': (0, 3, 7, 9), 'dim': (0, 3, 6), '5': (0, 7)}
MAJOR = (0, 2, 4, 5, 7, 9, 11); MINOR = (0, 2, 3, 5, 7, 8, 10); HMINOR = (0, 2, 3, 5, 7, 8, 11)


def midi(name):
    p, o = name[:-1], int(name[-1])
    return 12 * (o + 1) + PC[p]


def mhz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord(sym):
    root = sym[:2] if len(sym) > 1 and sym[1] in '#b' else sym[:1]
    q = sym[len(root):]
    return PC[root], [(PC[root] + i) % 12 for i in QUAL[q]]


def parse(line):
    """'G#4:2 A4:1 r:1' -> [(midi|None, beats)]"""
    out = []
    for tok in line.split():
        p, d = tok.split(':')
        out.append((None if p == 'r' else midi(p), float(d)))
    return out


def nearest(pc, target):
    """midi note with pitch class pc nearest to target."""
    base = target - ((target - pc) % 12)
    return base if target - base <= 6 else base + 12


def below(pcs, m, gap=1):
    """highest midi < m - gap whose pitch class is in pcs."""
    x = m - gap - 1
    while x % 12 not in pcs: x -= 1
    return x


class Song:
    def __init__(self, name, bpm, bpb, chords, key_pc, scale=MAJOR, trans=0, seed=1, rt60=1.6, wet=0.22,
                 predelay=0.02):
        self.name, self.bpm, self.bpb, self.trans = name, bpm, bpb, trans
        # chords: list per bar of 'Sym' or 'Sym1 Sym2' (split bar evenly)
        self.bars = []
        for c in chords:
            parts = c.split()
            self.bars.append([(p, bpb / len(parts)) for p in parts])
        self.key_pc = (key_pc + trans) % 12
        self.scale = scale
        self.events = []
        self.r = rng(seed)
        self.rt60, self.wet, self.predelay = rt60, wet, predelay

    @property
    def nbars(self): return len(self.bars)

    @property
    def beats(self): return self.nbars * self.bpb

    @property
    def spb(self): return 60.0 / self.bpm

    @property
    def nsamples(self): return int(round(self.beats * self.spb * SR))

    def chord_at(self, beat):
        b = int(beat // self.bpb) % self.nbars; x = beat - int(beat // self.bpb) * self.bpb
        acc = 0
        for sym, d in self.bars[b]:
            if x < acc + d - 1e-9:
                rpc, pcs = chord(sym)
                return (rpc + self.trans) % 12, [(p + self.trans) % 12 for p in pcs], b * self.bpb + acc, d
            acc += d
        sym, d = self.bars[b][-1]; rpc, pcs = chord(sym)
        return (rpc + self.trans) % 12, [(p + self.trans) % 12 for p in pcs], b * self.bpb + acc - d, d

    def chord_spans(self, b0, b1):
        out = []
        for b in range(b0, b1):
            acc = 0
            for sym, d in self.bars[b % self.nbars]:
                rpc, pcs = chord(sym)
                out.append(((rpc + self.trans) % 12, [(p + self.trans) % 12 for p in pcs], b * self.bpb + acc, d))
                acc += d
        return out

    def add(self, inst, beat, dur, m, vel=0.8, pan=0.0, part='base', **opts):
        self.events.append(dict(inst=inst, t=beat, dur=dur, m=None if m is None else m + (self.trans if opts.pop('transpose', True) else 0),
                                vel=vel, pan=pan, part=part, opts=opts))

    def scale_step(self, m, steps):
        """move m by diatonic steps in the song key (m already transposed)."""
        sc = [(self.key_pc + s) % 12 for s in self.scale]
        x = m
        for _ in range(abs(steps)):
            x += 1 if steps > 0 else -1
            while x % 12 not in sc: x += 1 if steps > 0 else -1
        return x

    # ------------------------------------------------------------------ writing helpers
    def melody(self, line, bar, inst='mandolin', vel=0.75, pan=0.0, part='base', oct=0, trem_from=None, **opts):
        t = bar * self.bpb
        for m, d in parse(line):
            if m is not None:
                use = inst
                if inst == 'mandolin' and trem_from is not None and d * self.spb >= trem_from:
                    use = 'mandolin_trem'
                self.add(use, t, d, m + 12 * oct, vel * (0.92 + 0.08 * self.r.random()), pan, part, **opts)
            t += d
        return t

    def klapa(self, line, bar, vowel='o', vel=0.7, oct=-1, part='base', lower=True, pan=(0.25, -0.15, 0.15, -0.25)):
        """four-part klapa: melody (1st tenor), parallel diatonic third below (2nd tenor),
        baritone on a chord tone below, bass on the chord root; lower parts held per chord."""
        t = bar * self.bpb
        notes = parse(line)
        for m, d in notes:
            if m is not None:
                mm = m + 12 * oct + self.trans
                self.add('voice', t, d * 0.97, mm, vel, pan[0], part, vowel=vowel, transpose=False)
                t2 = self.scale_step(mm, -2)
                self.add('voice', t + 0.01, d * 0.97, t2, vel * 0.8, pan[1], part, vowel=vowel, transpose=False)
            t += d
        if not lower: return
        end = t
        prev_bar, prev_bass = 55, 43
        for rpc, pcs, s, d in self.chord_spans(bar, bar + int(np.ceil((end - bar * self.bpb) / self.bpb))):
            if s >= end: break
            # breathe where the melody rests for a whole beat or more
            mel_rest = self._rest_in(notes, bar * self.bpb, s, d)
            dd = d - (0.35 if mel_rest else 0.05)
            bs = nearest(rpc, prev_bass); bs = bs if 38 <= bs <= 51 else (bs - 12 if bs > 51 else bs + 12)
            cand = [nearest(p, prev_bar) for p in pcs if p != rpc] or [nearest(rpc, prev_bar)]
            br = min(cand, key=lambda x: abs(x - prev_bar)); br = br if 47 <= br <= 60 else (br - 12 if br > 60 else br + 12)
            self.add('voice', s + 0.02, dd, br, vel * 0.72, pan[2], part, vowel=vowel, transpose=False)
            self.add('voice', s + 0.03, dd, bs, vel * 0.85, pan[3], part, vowel=vowel, transpose=False)
            prev_bar, prev_bass = br, bs

    @staticmethod
    def _rest_in(notes, t0, s, d):
        t = t0
        for m, dd in notes:
            if m is None and t < s + d and t + dd > s and dd >= 1: return True
            t += dd
        return False

    def pad(self, b0, b1, inst='voice', vowel='u', vel=0.4, part='base', voicing=(0, 1, 2), low=52, pans=(-0.4, 0, 0.4), **opts):
        prev = low + 7
        for rpc, pcs, s, d in self.chord_spans(b0, b1):
            for i, idx in enumerate(voicing):
                p = pcs[idx % len(pcs)]
                m = nearest(p, prev + 3 * i)
                while m < low: m += 12
                self.add(inst, s + 0.02 * i, d * 0.98, m, vel, pans[i % len(pans)], part, vowel=vowel, transpose=False, **opts)

    def arpeggio(self, b0, b1, pattern, inst='guitar', vel=0.55, part='base', low=40, pan=-0.2, step=0.5, accent=1.0):
        """pattern: chord-tone indices per step, 'B' = bass root, '-' = rest, e.g. 'B 2 1 2 0 2 1 2'."""
        pat = pattern.split()
        for rpc, pcs, s, d in self.chord_spans(b0, b1):
            bass = nearest(rpc, low + 5)
            while bass < low: bass += 12
            tones = sorted(nearest(p, bass + 12) for p in pcs)
            tones = [x if x > bass + 2 else x + 12 for x in tones]
            tones.sort()
            k = 0; t = s
            while t < s + d - 1e-6:
                tok = pat[k % len(pat)]
                if tok != '-':
                    m = bass if tok == 'B' else tones[int(tok) % len(tones)] + 12 * (int(tok) // len(tones))
                    v = vel * (accent if k == 0 else 1.0) * (0.85 + 0.15 * self.r.random())
                    self.add(inst, t + 0.004 * self.r.standard_normal(), step * 1.6, m, v, pan, part, transpose=False)
                k += 1; t += step

    def strum(self, b0, b1, beats, inst='guitar_mute', vel=0.45, part='base', low=52, pan=0.25, up=False):
        for rpc, pcs, s, d in self.chord_spans(b0, b1):
            for bt in beats:
                if bt >= d: continue
                tones = sorted(nearest(p, low + 4) for p in pcs)
                tones = [x + 12 if x < low else x for x in tones]
                for i, m in enumerate(sorted(tones, reverse=up)):
                    self.add(inst, s + bt + i * 0.012 * (self.bpm / 60), 0.3, m, vel * (0.9 - 0.08 * i), pan, part, transpose=False)

    def basses(self, b0, b1, beats=(0,), alt_fifth=True, vel=0.7, part='base', low=33, inst='bass'):
        k = 0
        for rpc, pcs, s, d in self.chord_spans(b0, b1):
            for bt in beats:
                if bt >= d: continue
                p = rpc if (k % 2 == 0 or not alt_fifth) else (rpc + 7) % 12
                m = nearest(p, low + 6)
                while m < low: m += 12
                self.add(inst, s + bt, min(d - bt, 1.0), m, vel, 0.0, part, transpose=False)
                k += 1

    def drums(self, b0, b1, pattern, part='base', vel=1.0, swing=0.0):
        """pattern: dict inst -> list of (beat_in_bar, velocity)."""
        for b in range(b0, b1):
            for inst, hits in pattern.items():
                for bt, v in hits:
                    j = 0.006 * self.r.standard_normal()
                    off = swing if (bt % 1) >= 0.5 else 0
                    self.add(inst, b * self.bpb + bt + off + j, 0.2, None, v * vel * (0.88 + 0.12 * self.r.random()),
                             self.r.uniform(-0.15, 0.15), part)

    # ------------------------------------------------------------------ render
    def render(self, part):
        n = self.nsamples; out = np.zeros((n, 2))
        spb = self.spb
        for e in self.events:
            if e['part'] != part: continue
            f = None if e['m'] is None else mhz(e['m'])
            y = INST[e['inst']](f, e['dur'] * spb, self.r, vel=e['vel'], **e['opts'])
            i = int(round(e['t'] * spb * SR)) % n
            a = (np.clip(e['pan'], -1, 1) + 1) * np.pi / 4
            idx = (np.arange(len(y)) + i) % n
            np.add.at(out[:, 0], idx, y * np.cos(a))
            np.add.at(out[:, 1], idx, y * np.sin(a))
        return out

    def reverb(self, x):
        """circular convolution with a synthetic stereo room/hall IR (loop-safe)."""
        n = len(x); r = rng(991)
        L = min(n, N(self.rt60 * 1.3))
        t = tax(L)
        ir = np.zeros((L, 2))
        for c in range(2):
            w = r.standard_normal(L) * np.exp(-6.91 * t / self.rt60)
            # high frequencies die faster: blend of bright early and dark late tail
            w = lp(w, 6000) * np.exp(-t / (self.rt60 * 0.25)) + lp(w, 2200) * (1 - np.exp(-t / (self.rt60 * 0.25)))
            w *= np.minimum(1, t / 0.01)
            pd = N(self.predelay)
            ir[pd:, c] = w[:L - pd]
            for d, g in ((0.011, 0.5), (0.019, 0.35), (0.029, 0.25)):
                ir[N(d + self.predelay * 0.5) + c * 7, c] += g
        ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True)) + 1e-12
        X = np.fft.rfft(x, axis=0); H = np.fft.rfft(np.pad(ir, ((0, n - L), (0, 0))), axis=0)
        wet = np.fft.irfft(X * H, n=n, axis=0)
        wet = hp(np.concatenate([wet, wet, wet]), 120)[n:2 * n]        # keep the low end dry
        return x + wet * self.wet
