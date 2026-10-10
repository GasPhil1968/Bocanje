"""Core DSP for the TRI FILDŽANA SFX pack (44.1 kHz, float64 internally, 16-bit output)."""
import os
import numpy as np
import soundfile as sf
from scipy import signal as ss

SR = 44100


def rng(seed):
    return np.random.default_rng(seed)


def N(dur):
    return int(round(dur * SR))


def tax(n):
    return np.arange(n) / SR


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def undb(d):
    return 10 ** (d / 20)


# ------------------------------------------------------------------ filters
def _sos(kind, f, order):
    ny = SR / 2 * 0.98
    if kind == 'bp':
        return ss.butter(order, [max(10, f[0]), min(ny, f[1])], 'bandpass', fs=SR, output='sos')
    return ss.butter(order, min(f, ny), {'lp': 'lowpass', 'hp': 'highpass'}[kind], fs=SR, output='sos')


def lp(x, f, o=2):
    return ss.sosfilt(_sos('lp', f, o), x, axis=0)


def hp(x, f, o=2):
    return ss.sosfilt(_sos('hp', f, o), x, axis=0)


def bp(x, lo, hi, o=2):
    return ss.sosfilt(_sos('bp', (lo, hi), o), x, axis=0)


def peaking(x, f0, gain_db, q):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return ss.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def resonator(x, f, q):
    """2-pole constant-peak-gain resonator."""
    r = np.exp(-np.pi * f / (q * SR)); w = 2 * np.pi * f / SR
    b = [(1 - r * r) / 2, 0, -(1 - r * r) / 2]; a = [1, -2 * r * np.cos(w), r * r]
    return ss.lfilter(b, a, x, axis=0)


def tv_filter(x, freqs, qs, kind='bp', block=64):
    """Time-varying resonant band-pass (freqs: per-sample array). Block-wise coefficients
    with carried state."""
    y = np.zeros_like(x); zi = np.zeros(2)
    qs = np.broadcast_to(qs, freqs.shape)
    for s in range(0, len(x), block):
        e = min(len(x), s + block)
        f = float(np.clip(freqs[s], 20, SR * 0.45)); q = float(qs[s])
        r = np.exp(-np.pi * f / (q * SR)); w = 2 * np.pi * f / SR
        if kind == 'bp':
            b = [(1 - r * r) / 2, 0, -(1 - r * r) / 2]
        else:   # unit-DC-gain all-pole formant
            b = [1 - 2 * r * np.cos(w) + r * r, 0, 0]
        a = [1, -2 * r * np.cos(w), r * r]
        y[s:e], zi = ss.lfilter(b, a, x[s:e], zi=zi)
    return y


def tv_lp(x, freqs, block=64):
    """time-varying one-pole low-pass"""
    y = np.zeros_like(x); zi = np.zeros(1)
    for s in range(0, len(x), block):
        e = min(len(x), s + block)
        a = np.exp(-2 * np.pi * float(np.clip(freqs[s], 20, SR * 0.45)) / SR)
        y[s:e], zi = ss.lfilter([1 - a], [1, -a], x[s:e], zi=zi)
    return y


# ------------------------------------------------------------------ sources
def noise(n, r, color='white'):
    w = r.standard_normal(n)
    if color == 'pink':
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        w = ss.lfilter(b, a, w); w /= np.std(w) + 1e-12
    elif color == 'brown':
        w = ss.lfilter([1], [1, -0.995], w); w = hp(w, 15); w /= np.std(w) + 1e-12
    return w


def smooth(n, rate_hz, r):
    """slowly varying random control signal, ~unit std."""
    from scipy.interpolate import CubicSpline
    k = max(4, int(n * rate_hz / SR) + 4)
    return CubicSpline(np.arange(k), r.standard_normal(k))(np.linspace(0, k - 1, n))


def modal(modes, n):
    """modes: iterable of (freq, amp, T60[, phase]) -> impulse response"""
    t = tax(n); y = np.zeros(n)
    for m in modes:
        f, a, t60 = m[0], m[1], m[2]
        ph = m[3] if len(m) > 3 else 0.0
        if f >= SR / 2 * 0.95 or a == 0:
            continue
        y += a * np.exp(-6.91 * t / t60) * np.sin(2 * np.pi * f * t + ph)
    return y


def pulse(dur, power=1.5):
    """contact-force pulse (half sine^power), unit area"""
    n = max(3, int(dur * SR)); p = np.sin(np.linspace(0, np.pi, n)) ** power
    return p / p.sum()


def conv(x, h):
    return ss.fftconvolve(x, h)


def place(out, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(out) or i < 0:
        return out
    m = min(len(x), len(out) - i)
    seg = np.array(x[:m], dtype=np.float64)
    k = min(m, N(0.003))
    if k > 1:   # never let a placed segment end on a step
        w = np.cos(np.linspace(0, np.pi / 2, k)) ** 2
        seg[-k:] *= w if seg.ndim == 1 else w[:, None]
    out[i:i + m] += gain * seg
    return out


def mix(length, *items):
    """items: (signal, start_time, gain)"""
    out = np.zeros(N(length))
    for x, t, g in items:
        place(out, x, t, g)
    return out


def env_ad(n, a, d, curve=3.0):
    t = tax(n)
    return np.where(t < a, t / max(a, 1e-6), np.exp(-curve * (t - a) / max(d, 1e-6)))


def env_pts(n, pts):
    """piecewise-linear envelope from (time, value) points"""
    tt, vv = zip(*pts)
    return np.interp(tax(n), tt, vv)


def fade(x, fin=0.001, fout=0.02):
    x = np.array(x, dtype=np.float64)
    i = int(fin * SR); o = int(fout * SR)
    if i > 1:
        w = np.sin(np.linspace(0, np.pi / 2, i)) ** 2
        x[:i] *= w if x.ndim == 1 else w[:, None]
    if o > 1:
        w = np.cos(np.linspace(0, np.pi / 2, o)) ** 2
        x[-o:] *= w if x.ndim == 1 else w[:, None]
    return x


def pan(x, p):
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def room(x, r, t60=0.35, wet=0.12, pre=0.008, stereo=False, lpf=4500, er=True):
    """small warm room (kafana / TV studio). Mono in -> mono or stereo out."""
    m = N(t60 * 1.2); tt = tax(m)
    chans = 2 if stereo else 1
    out = []
    for c in range(chans):
        ir = r.standard_normal(m) * np.exp(-6.91 * tt / t60)
        ir = lp(ir, lpf); ir[:N(pre)] = 0
        if er:
            for d, g in ((0.0047, 0.5), (0.0083, 0.35), (0.0131, 0.25), (0.0197, 0.18)):
                k = N(d * (1 + 0.13 * c)) + N(pre * 0.3)
                if k < m:
                    ir[k] += g * (1 if (k + c) % 2 else -1) * 3
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-12
        out.append(ss.fftconvolve(x if x.ndim == 1 else x[:, c], ir))
    L = max(len(o) for o in out)
    y = np.zeros((L, chans))
    for c in range(chans):
        y[:len(out[c]), c] = out[c]
    dry = np.zeros((L, chans))
    if x.ndim == 1:
        dry[:len(x)] = x[:, None]
    else:
        dry[:len(x)] = x
    y = dry + wet * y * np.sqrt(np.mean(x ** 2) / (np.mean(y ** 2) + 1e-20))
    return y[:, 0] if chans == 1 else y


# ------------------------------------------------------------------ measurement
def true_peak(x):
    y = ss.resample_poly(x, 4, 1, axis=0)
    return float(np.max(np.abs(y)))


def _kweight(x):
    # ITU-R BS.1770 K-weighting at 44.1 kHz (bilinear designs)
    b1 = [1.53084123, -2.65097999, 1.16907226]; a1 = [1.0, -1.66364666, 0.71279760]
    b2 = [1.0, -2.0, 1.0]; a2 = [1.0, -1.98916967, 0.98919535]
    return ss.lfilter(b2, a2, ss.lfilter(b1, a1, x, axis=0), axis=0)


def loud_m(x):
    """max momentary (400 ms) K-weighted loudness in LUFS (short files zero-padded)"""
    if x.ndim == 1:
        x = x[:, None]
    k = _kweight(x)
    w = N(0.4)
    if len(k) < w:
        k = np.vstack([k, np.zeros((w - len(k), k.shape[1]))])
    p = np.sum(k ** 2, axis=1)
    c = np.concatenate([[0], np.cumsum(p)])
    hop = N(0.01)
    ms = [(c[i + w] - c[i]) / w for i in range(0, len(p) - w + 1, hop)]
    return -0.691 + 10 * np.log10(max(max(ms), 1e-20))


def trim_lead(x, thresh_db=-45, keep=0.0015):
    m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    pk = m.max()
    idx = int(np.argmax(m > pk * undb(thresh_db)))
    return x[max(0, idx - N(keep)):]


def trim_tail(x, thresh_db=-58):
    m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    # smoothed envelope so a zero-crossing doesn't end the file
    e = ss.lfilter([1 - 0.995], [1, -0.995], m[::-1])[::-1]
    e = np.maximum(e, m)
    above = np.nonzero(e > m.max() * undb(thresh_db))[0]
    end = above[-1] + N(0.006) if len(above) else len(x)
    return x[:min(len(x), end)]


def finish(x, rng_dur, loud=None, peak_db=-1.2, tail_db=-58, fout=0.012, lead_db=-45, fin=0.0012):
    """DC block, trim, fit into [min,max] duration (fade-out only, never pad), set level."""
    x = hp(np.asarray(x, dtype=np.float64), 20, 2)
    x = trim_lead(x, lead_db)
    x = trim_tail(x, tail_db)
    lo, hi = rng_dur
    if len(x) > N(hi):
        x = x[:N(hi) - N(0.003)]
        fo = min(0.05, 0.25 * len(x) / SR)
        x = fade(x, 0, fo)
    x = fade(x, fin, fout)
    d = len(x) / SR
    assert d >= lo - 1e-3, ('too short', d, rng_dur)
    if loud is not None:
        x = x * undb(loud - loud_m(x))
    p = true_peak(x)
    if p > undb(peak_db) or loud is None:
        x = x * (undb(peak_db) / p)
    return x


def write16(path, x, r=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    assert np.all(np.isfinite(x)), path
    r = r or rng(0)
    d = (r.random(x.shape) - r.random(x.shape)) / 32768.0   # TPDF dither, 1 LSB
    q = np.clip(np.round((x + d) * 32767), -32767, 32767).astype(np.int16)
    sf.write(path, q, SR, subtype='PCM_16')
    return path
