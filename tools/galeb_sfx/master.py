"""Render + master every recipe: trim, fades, loudness per category, true-peak ceiling, 16-bit WAV."""
import os, sys, wave, json, time, zlib
import numpy as np
from multiprocessing import Pool
from scipy import signal as ss
import lib
from lib import SR, lp, hp, circ_filter, band_shape
import sounds

CEIL_DB = -3.2          # true-peak ceiling (sample peak therefore < -3 dBFS)
WIN_S = 0.2             # momentary window for short-sound loudness


def kweight(x):
    def hs(G, Q, fc):
        A = 10 ** (G / 40); w0 = 2 * np.pi * fc / SR; al = np.sin(w0) / (2 * Q); c = np.cos(w0)
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
        return np.array(b) / a[0], np.array(a) / a[0]

    def hpf(Q, fc):
        w0 = 2 * np.pi * fc / SR; al = np.sin(w0) / (2 * Q); c = np.cos(w0)
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
        return np.array(b) / a[0], np.array(a) / a[0]
    b1, a1 = hs(3.99984385397, 0.7071752369554193, 1681.9744509555319)
    b2, a2 = hpf(0.5003270373253953, 38.13547087613982)
    return ss.lfilter(b2, a2, ss.lfilter(b1, a1, x, axis=0), axis=0)


def loudness(x, loop=False):
    """momentary-max (200 ms) K-weighted loudness for one-shots; whole-file for loops (LUFS-like)."""
    y = kweight(x)
    p = y ** 2 if y.ndim == 1 else (y ** 2).sum(axis=1)
    if loop:
        return -0.691 + 10 * np.log10(p.mean() + 1e-20)
    w = int(WIN_S * SR)
    p = np.concatenate([p, np.zeros(w)])
    c = np.cumsum(np.concatenate([[0], p]))
    ms = (c[w:] - c[:-w]) / w
    return -0.691 + 10 * np.log10(ms.max() + 1e-20)


def true_peak(x):
    return float(np.max(np.abs(ss.resample_poly(x, 4, 1, axis=0))))


def _env_abs(x):
    return np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)


def trim(x, lead_db=-48, tail_db=-62):
    m = _env_abs(x); pk = m.max()
    if pk <= 0: return x
    i0 = int(np.argmax(m > pk * 10 ** (lead_db / 20)))
    i0 = max(0, i0 - int(0.0015 * SR))
    above = np.nonzero(m > pk * 10 ** (tail_db / 20))[0]
    i1 = min(len(x), above[-1] + int(0.012 * SR))
    return x[i0:i1]


def fade(x, fin, fout):
    x = x.copy(); n = len(x)
    i, o = max(1, int(fin * SR)), max(1, int(fout * SR))
    wi = np.sin(np.linspace(0, np.pi / 2, i)) ** 2; wo = np.cos(np.linspace(0, np.pi / 2, o)) ** 2
    if x.ndim > 1: wi, wo = wi[:, None], wo[:, None]
    x[:i] *= wi; x[-o:] *= wo
    return x


def calm_point(x, win=2048, step=1024):
    """sample index (on the circular loop) where the sound changes least: lowest spectral flux and
    no transient - used as the loop start so the seam sits in the calmest moment."""
    mono = x.mean(axis=1) if x.ndim > 1 else x
    ext = np.concatenate([mono, mono[:2 * win]])
    hw = np.hanning(win)
    spec = lambda s: np.log10(np.abs(np.fft.rfft(s * hw)) + 1e-9)
    best, bi = 1e9, 0
    for i in range(win, len(mono) + win, step):
        a = ext[i - win:i]; b = ext[i:i + win]
        flux = np.mean(np.abs(spec(b) - spec(a)))
        lvl = abs(np.log10((np.std(b) + 1e-9) / (np.std(a) + 1e-9)))
        score = flux + lvl
        if score < best: best, bi = score, i % len(mono)
    return bi


def master(name):
    m = sounds.REG[name]
    x = np.asarray(m['fn'](), dtype=np.float64)
    assert np.all(np.isfinite(x)), name
    if m['stereo'] and x.ndim == 1:
        x = np.stack([x, x], 1)
    if not m['stereo'] and x.ndim == 2:
        x = x.mean(axis=1)
    if m['loop']:
        x = x - x.mean(axis=0)
        x = circ_filter(x, lambda f: (1 / np.sqrt(1 + (22 / f) ** 4)) / np.sqrt(1 + (f / 11000) ** 4))
        x = np.roll(x, -calm_point(x), axis=0)      # periodic signal: rotating keeps it seamless
    else:
        x = hp(x, 22, 2)                       # DC / subsonic
        x = lp(x, 11500, 2)                    # mobile-speaker friendly top end
        x = trim(x)
        d = len(x) / SR
        x = fade(x, 0.0012, min(0.04, max(0.006, d * 0.08)))
        lo = m['dur'][0]
        if d < lo:
            pad = int((lo - d) * SR) + 64
            x = np.concatenate([x, np.zeros((pad,) + x.shape[1:])])
    L0 = loudness(x, m['loop'])
    g = 10 ** ((m['lufs'] - L0) / 20)
    x = x * g
    tp = true_peak(x)
    limited = False
    if tp > 10 ** (CEIL_DB / 20):
        x *= 10 ** (CEIL_DB / 20) / tp; limited = True
    return name, x, dict(loud_in=L0, gain_db=20 * np.log10(g), limited=limited)


def write_wav(path, x, seed):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = np.random.default_rng(seed)
    d = (r.random(x.shape) - r.random(x.shape))          # TPDF dither, +-1 LSB
    q = np.clip(np.round(x * 32767 + d), -32767, 32767).astype('<i2')
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(q.tobytes())


def render_all(out_root, names=None, procs=4):
    names = names or list(sounds.REG)
    info = {}
    t0 = time.time()
    with Pool(procs) as p:
        for k, (name, x, inf) in enumerate(p.imap_unordered(master, names)):
            m = sounds.REG[name]
            rel = os.path.join('ambience' if m['loop'] else os.path.join('sfx', m['folder']), name + '.wav')
            write_wav(os.path.join(out_root, rel), x, zlib.crc32(name.encode()))
            inf['rel'] = rel
            info[name] = inf
            print(f'[{k + 1:3d}/{len(names)}] {rel}  {len(x) / SR:5.2f}s  gain {inf["gain_db"]:+.1f} dB'
                  f'{"  (peak-limited)" if inf["limited"] else ""}', flush=True)
    print(f'rendered {len(info)} files in {time.time() - t0:.1f}s')
    return info


if __name__ == '__main__':
    out = sys.argv[1]
    names = sys.argv[2:] or None
    info = render_all(out, names)
    with open(os.path.join(os.path.dirname(os.path.abspath(out)), 'render_info.json'), 'w') as f:
        json.dump(info, f, indent=1)
