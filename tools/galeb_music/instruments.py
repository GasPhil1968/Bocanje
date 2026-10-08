"""Instrument models for the Galeb nad Jadranom music pack (no oscillator 'synth' voices:
physical string models, formant-shaped vocal ensembles, reed and drum models)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'galeb_sfx'))
from lib import (SR, N, tax, rng, lp, hp, bp, resonator, noise, smooth, adsr, ks_string, body_res, mandolin as _mand,
                 guitar as _guit, modal, thump, place)

# male vowel formants (F, bandwidth, gain)
VOWELS = {
    'a': ((700, 110, 1.0), (1150, 120, 0.55), (2650, 160, 0.22), (3300, 220, 0.12)),
    'o': ((480, 90, 1.0), (820, 100, 0.65), (2550, 150, 0.14), (3300, 220, 0.08)),
    'u': ((330, 80, 1.0), (720, 100, 0.35), (2450, 150, 0.06), (3300, 220, 0.04)),
    'e': ((480, 90, 1.0), (1750, 130, 0.45), (2550, 160, 0.25), (3350, 220, 0.12)),
    'm': ((260, 70, 1.0), (1000, 200, 0.06), (2300, 250, 0.02), (3300, 300, 0.01)),
}


def _formant_gain(fk, vowel, singer=0.25):
    fk = np.asarray(fk, float)
    g = np.full_like(fk, 0.012)
    for F, B, A in VOWELS[vowel]:
        g += A / np.sqrt(1 + ((fk - F) / (B / 2)) ** 2)
    g += singer * 0.25 / np.sqrt(1 + ((fk - 2900) / 250) ** 2)       # ring of a trained voice
    return g


def voice(f, dur, r, vel=0.8, vowel='o', att=0.13, rel=0.22, vib=0.45, scoop=True, breath=0.03):
    """one sung note of a male voice (additive glottal source shaped by vowel formants)."""
    n = N(dur + rel); t = tax(n)
    cents = np.zeros(n)
    if scoop:
        cents -= 35 * np.exp(-t / 0.05)
    rate = 5.0 + 0.5 * r.random()
    depth = vib * 100 * 0.01 * np.clip((t - 0.25) / 0.5, 0, 1)            # vibrato grows in after 0.25 s
    cents += depth * 60 * np.sin(2 * np.pi * rate * t + r.uniform(0, 6.28))
    cents += 6 * smooth(n, 6, r)                                          # natural drift / jitter
    ff = f * 2 ** (cents / 1200)
    ph = 2 * np.pi * np.cumsum(ff) / SR
    K = max(1, min(48, int(4800 / f)))
    k = np.arange(1, K + 1)
    tilt = 1 / k ** 1.0 * np.exp(-(k * f) / 6000)                     # soft glottal roll-off, no hard edge
    amps = tilt * _formant_gain(k * f, vowel, 0.35 + 0.2 * (f > 180))
    amps /= amps.max()
    y = np.zeros(n)
    for kk, a in zip(k, amps):
        if a > 0.003:
            drift = 1 + 0.12 * smooth(n, 2.5, r)                         # partials breathe independently
            y += a * drift * np.sin(kk * ph)
    y *= 1 + 0.05 * smooth(n, 18, r)                                     # shimmer
    # aspiration: noise pulsed at the glottal rate and shaped like the vowel -> breathy, human
    asp = noise(n, r)
    asp = sum(resonator(asp, F, F / B * 1.4) * A for F, B, A in VOWELS[vowel][:3])
    asp *= 0.6 + 0.4 * np.maximum(0, np.sin(ph))
    asp = asp / (np.std(asp) + 1e-9) * np.std(y) * 0.06
    br = bp(noise(n, r), 600, 3500) * breath * np.exp(-t / 0.15) + asp
    e = np.clip(t / att, 0, 1) ** 1.5
    e = np.sin(np.pi / 2 * e) ** 2
    rl = np.clip((t - dur) / rel, 0, 1)
    e *= np.cos(np.pi / 2 * rl) ** 2
    e *= 1 + 0.06 * np.sin(np.pi * np.clip(t / max(dur, 0.2), 0, 1))    # gentle swell
    y = lp((y + br) * e, 5000, 4)
    return y / (np.max(np.abs(y)) + 1e-9) * vel


def choir_voice(f, dur, r, vel=0.8, vowel='o', **kw):
    """two singers per part, slightly detuned and offset -> natural ensemble."""
    vel = vel * 0.45                       # sustained voices: trim against plucked instruments
    a = voice(f * 2 ** (4 / 1200), dur, r, vel * 0.55, vowel, **kw)
    b = voice(f * 2 ** (-5 / 1200), dur, r, vel * 0.55, vowel, **kw)
    off = N(0.012 + 0.012 * r.random())
    out = np.zeros(len(a) + off); out[:len(a)] += a; out[off:off + len(b)] += b
    return out


def mandolin(f, dur, r, vel=0.8, **kw):
    return _mand(f, min(dur + 0.6, 2.5), r, vel=vel, **kw)


def mandolin_trem(f, dur, r, vel=0.8, rate=13.5, **kw):
    n = N(dur + 0.5); out = np.zeros(n); t = 0.0; k = 0
    while t < dur:
        v = vel * (0.78 + 0.18 * r.random()) * (0.86 if k % 2 else 1.0) * (1 - 0.15 * t / max(dur, 0.1))
        place(out, _mand(f, 0.5, r, vel=v, decay=0.45), t)
        t += (1 / rate) * (1 + 0.05 * r.standard_normal()); k += 1
    return out


def guitar(f, dur, r, vel=0.8, decay=None, **kw):
    return _guit(f, min(dur + 1.0, 3.5), r, vel=vel, decay=decay, bright=kw.get('bright', 0.42))


def guitar_mute(f, dur, r, vel=0.8, **kw):
    y = _guit(f, 0.35, r, vel=vel, decay=0.22, bright=0.35)
    return y * adsr(len(y), 0.001, 0.09)


def bass(f, dur, r, vel=0.8, **kw):
    """plucked double bass / berda."""
    y = ks_string(f, min(dur + 0.6, 2.5), r, bright=0.28, decay=1.4, pick=0.3)
    y = body_res(y, ((70, 4, 0.8), (140, 5, 0.6), (260, 6, 0.3), (520, 6, 0.1)))
    y = lp(y, 1400, 4)
    y *= adsr(len(y), 0.004, 100) * np.exp(-tax(len(y)) / max(0.3, dur * 1.2))
    return y / (np.max(np.abs(y)) + 1e-9) * vel


def sopila(f, dur, r, vel=0.8, **kw):
    """Istrian shawm: bright double reed, nasal formants, straight tone, slight pitch settle."""
    n = N(dur + 0.08); t = tax(n)
    cents = 18 * np.exp(-t / 0.04) + 4 * smooth(n, 5, r)
    ph = 2 * np.pi * np.cumsum(f * 2 ** (cents / 1200)) / SR
    K = min(30, int(6500 / f))
    y = np.zeros(n)
    for k in range(1, K + 1):
        fk = k * f
        a = (1 / k ** 0.55) * (0.35 + 1.0 / np.sqrt(1 + ((fk - 1250) / 300) ** 2) + 0.6 / np.sqrt(1 + ((fk - 2600) / 400) ** 2))
        if k % 2 == 0: a *= 0.75
        y += a * np.sin(k * ph + r.uniform(0, 0.3))
    y += bp(noise(n, r), 1500, 4500) * 0.12                              # reed buzz / breath
    e = np.sin(np.pi / 2 * np.clip(t / 0.025, 0, 1)) ** 2 * np.cos(np.pi / 2 * np.clip((t - dur) / 0.08, 0, 1)) ** 2
    y = lp(y * e, 5500, 4)
    return y / (np.max(np.abs(y)) + 1e-9) * vel


def pipe_pad(f, dur, r, vel=0.5, **kw):
    """soft breathy flue pipes (a nod to the Zadar Sea Organ), slow swell."""
    n = N(dur + 0.8); t = tax(n)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.0015 * smooth(n, 2, r))) / SR
    y = np.sin(ph) + 0.2 * np.sin(2 * ph) + 0.28 * np.sin(3 * ph) + 0.06 * np.sin(5 * ph)
    y += bp(noise(n, r), f * 1.5, min(f * 7, 5000)) * 0.1
    e = np.sin(np.pi / 2 * np.clip(t / 0.7, 0, 1)) ** 2 * np.cos(np.pi / 2 * np.clip((t - dur) / 0.8, 0, 1)) ** 2
    e *= 1 + 0.12 * smooth(n, 1.2, r)
    y = lp(y * e, 3500)
    return y / (np.max(np.abs(y)) + 1e-9) * vel * 0.45


# ------------------------------------------------------------------ percussion
def tapan(f=None, dur=0.3, r=None, vel=0.8, **kw):
    """large two-headed folk drum: deep head."""
    y = thump(r, 105, 52, 0.45, 0.13) * 1.0
    n = len(y); t = tax(n)
    y += lp(noise(n, r, 'pink'), 1200) * np.exp(-t / 0.03) * 0.35 * adsr(n, 0.001, 100)
    return lp(y, 4000) * vel


def tapan_rim(f=None, dur=0.1, r=None, vel=0.6, **kw):
    """the thin switch on the other head."""
    n = N(0.12); t = tax(n)
    y = bp(noise(n, r), 1500, 5000) * np.exp(-t / 0.018) * np.minimum(1, t / 0.0006)
    y += modal([(610, 0.4, 0.05), (1340, 0.2, 0.03)], n, r, True) * adsr(n, 0.0008, 100)
    return lp(y, 6000) * vel


def def_drum(f=None, dur=0.2, r=None, vel=0.6, jingle=0.6, **kw):
    """frame drum with jingles (def / tambourine)."""
    n = N(0.3); t = tax(n)
    y = thump(r, 190, 120, 0.3, 0.05) * 0.5
    for _ in range(6):
        fj = r.uniform(2800, 5200)
        y += modal([(fj, 0.25, 0.09), (fj * 1.41, 0.15, 0.06)], n, r, True) * adsr(n, 0.0008, 100) * jingle * r.uniform(0.4, 1)
    return lp(y, 6500) * vel


def shaker(f=None, dur=0.1, r=None, vel=0.4, **kw):
    n = N(0.11); t = tax(n)
    e = np.sin(np.pi * np.clip(t / 0.07, 0, 1)) ** 1.5
    return lp(bp(noise(n, r), 2500, 7000) * e, 6500) * vel


INST = dict(voice=choir_voice, solo_voice=voice, mandolin=mandolin, mandolin_trem=mandolin_trem, guitar=guitar,
            guitar_mute=guitar_mute, bass=bass, sopila=sopila, pipe_pad=pipe_pad, tapan=tapan, tapan_rim=tapan_rim,
            def_drum=def_drum, shaker=shaker)
