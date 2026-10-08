"""DSP + instrument library for the Galeb nad Jadranom SFX pack.

Everything is synthesised from scratch (noise, oscillators, physical/modal models).
Internal processing is float64 at 44.1 kHz; files are written as 16-bit PCM with TPDF dither.
"""
import numpy as np
from scipy import signal as ss

SR = 44100
NOTE = {'C': -9, 'C#': -8, 'Db': -8, 'D': -7, 'D#': -6, 'Eb': -6, 'E': -5, 'F': -4, 'F#': -3,
        'Gb': -3, 'G': -2, 'G#': -1, 'Ab': -1, 'A': 0, 'A#': 1, 'Bb': 1, 'B': 2}


def hz(name):
    """'A4' -> 440.0, 'F#5' -> 739.99"""
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[p] + 12 * (o - 4)) / 12)


def N(dur):
    return int(round(dur * SR))


def tax(n):
    return np.arange(n) / SR


def rng(seed):
    return np.random.default_rng(seed)


def undb(d):
    return 10 ** (d / 20)


# ------------------------------------------------------------------ filters
def _sos(kind, f, order):
    nyq = SR / 2 * 0.98
    if kind == 'bandpass':
        lo, hi = max(15.0, f[0]), min(nyq, f[1])
        return ss.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    return ss.butter(order, min(max(f, 10.0), nyq), kind, fs=SR, output='sos')


def lp(x, f, o=2): return ss.sosfilt(_sos('lowpass', f, o), x, axis=0)
def hp(x, f, o=2): return ss.sosfilt(_sos('highpass', f, o), x, axis=0)
def bp(x, lo, hi, o=2): return ss.sosfilt(_sos('bandpass', (lo, hi), o), x, axis=0)


def lp_zero(x, f, o=2):  # zero phase (for envelopes / control)
    return ss.sosfiltfilt(_sos('lowpass', f, o), x, axis=0)


def resonator(x, f, q):
    r = np.exp(-np.pi * f / (q * SR)); w = 2 * np.pi * f / SR
    b = [(1 - r * r) / 2, 0, -(1 - r * r) / 2]; a = [1, -2 * r * np.cos(w), r * r]
    return ss.lfilter(b, a, x, axis=0)


def peaking(x, f0, gain_db, q):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return ss.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def shelf_hi(x, f0, gain_db):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w); sA = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
    a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    return ss.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def tv_filter(x, fc, bw_oct=1.0, mode='band', order=2.0):
    """Time-varying spectral shaping in the STFT domain.
    fc / bw_oct: scalar or per-sample arrays.  mode 'band' (log-gaussian), 'lp', 'hp'."""
    n = len(x)
    nper, hop = 1024, 256
    f, tt, Z = ss.stft(x, fs=SR, nperseg=nper, noverlap=nper - hop, boundary='even', padded=True)
    fr = np.clip(tt * SR, 0, n - 1).astype(int)
    fcv = np.broadcast_to(np.asarray(fc, float), (n,))[fr] if np.ndim(fc) else np.full(len(fr), float(fc))
    bwv = np.broadcast_to(np.asarray(bw_oct, float), (n,))[fr] if np.ndim(bw_oct) else np.full(len(fr), float(bw_oct))
    ff = np.maximum(f, 1.0)[:, None]
    if mode == 'band':
        d = (np.log2(ff) - np.log2(fcv[None, :])) / (bwv[None, :] / 2.355)
        m = np.exp(-0.5 * d * d)
    elif mode == 'lp':
        m = 1 / np.sqrt(1 + (ff / fcv[None, :]) ** (2 * order))
    else:
        m = 1 / np.sqrt(1 + (fcv[None, :] / ff) ** (2 * order))
    _, y = ss.istft(Z * m, fs=SR, nperseg=nper, noverlap=nper - hop, boundary=True)
    return y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))


def circ_filter(x, shape):
    """Circular (loop-safe) static filtering in the FFT domain. shape(f)->gain."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = shape(np.maximum(f, 0.5))
    if X.ndim > 1: g = g[:, None]
    return np.fft.irfft(X * g, n=len(x), axis=0)


def band_shape(lo, hi, o=2):
    return lambda f: 1 / np.sqrt(1 + (lo / f) ** (2 * o)) / np.sqrt(1 + (f / hi) ** (2 * o))


# ------------------------------------------------------------------ sources
def noise(n, r, color='white'):
    w = r.standard_normal(n)
    if color == 'pink':
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        w = ss.lfilter(b, a, w)
    elif color == 'brown':
        w = ss.lfilter([1], [1, -0.995], w); w = hp(w, 18)
    return w / (np.std(w) + 1e-12)


def circ_noise(n, r, color='white'):
    """Periodic noise (loop-safe): random-phase spectrum."""
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = np.ones_like(f)
    if color == 'pink': mag = 1 / np.sqrt(np.maximum(f, 5))
    if color == 'brown': mag = 1 / np.maximum(f, 15)
    mag[0] = 0
    ph = r.uniform(0, 2 * np.pi, len(f))
    y = np.fft.irfft(mag * np.exp(1j * ph), n=n)
    return y / (np.std(y) + 1e-12)


def smooth(n, rate, r):
    """slowly varying random control (unit std)."""
    k = max(4, int(n * rate / SR) + 4)
    pts = r.standard_normal(k)
    from scipy.interpolate import CubicSpline
    return CubicSpline(np.arange(k), pts)(np.linspace(0, k - 3, n))


def circ_smooth(n, rate, r):
    """periodic slowly varying control (unit std) - loop-safe."""
    k = max(2, int(n * rate / SR))
    f = np.zeros(n // 2 + 1, complex)
    kk = np.arange(1, k + 1)
    f[kk] = r.standard_normal(k) * np.exp(1j * r.uniform(0, 2 * np.pi, k)) / np.sqrt(kk)
    y = np.fft.irfft(f, n=n)
    return y / (np.std(y) + 1e-12)


def env_pts(n, pts, curve='lin'):
    """piecewise envelope from [(t_sec, value), ...]."""
    t = tax(n); ts, vs = zip(*pts)
    e = np.interp(t, ts, vs)
    if curve == 'smooth':
        e = lp_zero(e, 40)
    return e


def adsr(n, a, d, peak=1.0, shape=4.0):
    """attack (sine ease) then exponential decay with time-constant d (seconds to -60*shape/6.9 dB)."""
    t = tax(n); ia = max(1, N(a))
    e = np.exp(-(t - a) / max(d, 1e-4))
    e[:ia] = np.sin(np.linspace(0, np.pi / 2, ia)) ** 2
    return e * peak


def hann_env(n, a_frac=0.3):
    """asymmetric bell envelope (rise a_frac, fall rest)."""
    t = np.linspace(0, 1, n)
    e = np.where(t < a_frac, np.sin(np.pi / 2 * t / a_frac) ** 2,
                 np.cos(np.pi / 2 * (t - a_frac) / (1 - a_frac)) ** 2)
    return e


def place(out, x, t, g=1.0, i=None):
    i = N(t) if i is None else i
    if i >= len(out): return out
    m = min(len(x), len(out) - i)
    out[i:i + m] += x[:m] * g
    return out


def place_wrap(out, x, i, g=1.0):
    """add x into periodic buffer out starting at sample i (wrapping)."""
    n = len(out); i %= n
    idx = (np.arange(len(x)) + i) % n
    np.add.at(out, idx, x * g)
    return out


def pan(x, p):
    a = (np.clip(p, -1, 1) + 1) * np.pi / 4
    if np.ndim(p):
        return np.stack([x * np.cos(a), x * np.sin(a)], 1)
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def stereo(x):
    return np.stack([x, x], 1) if x.ndim == 1 else x


def mix(*xs):
    n = max(len(x) for x in xs)
    st = any(x.ndim == 2 for x in xs)
    out = np.zeros((n, 2)) if st else np.zeros(n)
    for x in xs:
        x = stereo(x) if st else x
        out[:len(x)] += x
    return out


def early_ref(x, taps=((0.013, 0.20, -0.5), (0.023, 0.14, 0.6), (0.037, 0.09, -0.7), (0.061, 0.05, 0.8)),
              tone=4000):
    """a few discrete stone reflections (not a reverb). mono->stereo."""
    n = len(x) + N(max(t for t, _, _ in taps) + 0.01)
    y = np.zeros((n, 2)); y[:len(x)] += pan(x, 0)
    xl = lp(x, tone)
    for d, g, p in taps:
        i = N(d); y[i:i + len(x)] += pan(xl * g, p)
    return y


def decor_stereo(x, r, width=0.35):
    """mono -> stereo with a short decorrelating allpass on one side."""
    a = 0.6
    y2 = x.copy()
    for d in (37, 113, 241):
        b = np.zeros(d + 1); b[0] = -a; b[d] = 1
        aa = np.zeros(d + 1); aa[0] = 1; aa[d] = -a
        y2 = ss.lfilter(b, aa, y2)
    m = x; s = (y2 - x) * width
    return np.stack([m + s, m - s], 1)


# ------------------------------------------------------------------ musical instruments
def ks_string(f, dur, r, bright=0.5, decay=1.5, pick=0.18, exc_len=None):
    """Karplus-Strong string with allpass fractional-delay tuning.
    decay: T60 in seconds at fundamental (approx)."""
    n = N(dur)
    P = SR / f
    Ni = int(np.floor(P - 0.5 - 0.15))
    d = P - 0.5 - Ni
    c = (1 - d) / (1 + d)
    g = 10 ** (-3 / (decay * f))
    g = min(g, 0.99995)
    # loop: y = x + g*0.5*(1+z^-1) * A(z) * z^-Ni * y
    den = np.zeros(Ni + 3)
    den[0] = 1; den[1] += c
    den[Ni] -= g * 0.5 * c
    den[Ni + 1] -= g * 0.5 * (1 + c)
    den[Ni + 2] -= g * 0.5
    num = np.array([1.0, c])
    L = exc_len or Ni
    exc = r.uniform(-1, 1, L)
    # brightness: one-pole smoothing of the excitation
    a = 1 - bright
    exc = ss.lfilter([1 - a], [1, -a], exc) if a > 0 else exc
    exc -= exc.mean()
    # pick position comb
    pd = max(1, int(pick * Ni))
    exc2 = exc.copy(); exc2[pd:] -= exc[:-pd]
    x = np.zeros(n); x[:L] = exc2
    y = ss.lfilter(num, den, x)
    return y / (np.max(np.abs(y)) + 1e-9)


def body_res(x, freqs=((280, 6, 0.9), (520, 8, 0.6), (1150, 7, 0.35), (2400, 6, 0.15))):
    y = x * 0.6
    for f, q, g in freqs:
        y = y + resonator(x, f, q) * g * 2
    return y


def mandolin(f, dur, r, vel=1.0, bright=0.55, decay=None):
    """double-course plucked string (mandolin / tamburica colour)."""
    decay = decay or max(0.35, 1.6 * (440 / f) ** 0.5)
    det = 2 ** (2.5 / 1200)
    a = ks_string(f * det, dur, r, bright=bright * (0.8 + 0.4 * vel), decay=decay, pick=0.13)
    b = ks_string(f / det, dur, r, bright=bright * (0.8 + 0.4 * vel), decay=decay * 0.92, pick=0.16)
    b = np.roll(b, N(0.0025)); b[:N(0.0025)] = 0
    y = body_res(a + b * 0.85)
    # pick noise
    k = N(0.006); pn = hp(r.standard_normal(k), 1500) * np.exp(-np.arange(k) / (k / 4)) * 0.15
    y[:k] += pn
    y = lp(y, 6200, 4)
    y *= adsr(len(y), 0.0015, 10)  # tiny attack de-click
    return y / (np.max(np.abs(y)) + 1e-9) * vel


def guitar(f, dur, r, vel=1.0, bright=0.45, decay=None):
    decay = decay or max(0.6, 2.4 * (220 / f) ** 0.5)
    y = ks_string(f, dur, r, bright=bright, decay=decay, pick=0.22)
    y = body_res(y, ((110, 5, 0.9), (220, 7, 0.6), (420, 7, 0.45), (900, 6, 0.2)))
    y = lp(y, 5000, 4)
    y *= adsr(len(y), 0.002, 10)
    return y / (np.max(np.abs(y)) + 1e-9) * vel


def tremolo(f, dur, r, rate=13.0, vel=0.8, inst=mandolin, swell=None):
    """tremolo picking (tamburica / mandolin)."""
    n = N(dur + 0.6); out = np.zeros(n)
    t = 0.0; k = 0
    while t < dur:
        v = vel * (0.75 + 0.25 * r.random()) * (0.92 if k % 2 else 1.0)
        if swell is not None: v *= swell(t / dur)
        nt = inst(f, min(0.5, dur - t + 0.4), r, vel=v, decay=0.5)
        place(out, nt, t)
        t += 1 / rate * (1 + 0.06 * r.standard_normal()); k += 1
    # damp the earlier note when re-picked is implicit through short decay
    return out


def strum(freqs, dur, r, spread=0.022, vel=0.8, inst=mandolin, up=False):
    n = N(dur); out = np.zeros(n)
    order = list(freqs)[::-1] if up else list(freqs)
    for i, f in enumerate(order):
        place(out, inst(f, dur, r, vel=vel * (0.9 + 0.1 * r.random())), i * spread)
    return out


def arp(notes, times, dur, r, inst=mandolin, vel=0.8, vels=None):
    n = N(dur); out = np.zeros(n)
    for i, (nm, t) in enumerate(zip(notes, times)):
        f = hz(nm) if isinstance(nm, str) else nm
        v = vels[i] if vels else vel
        place(out, inst(f, max(0.3, dur - t), r, vel=v), t)
    return out


def modal(modes, n, r=None, rand_phase=False):
    """modes: [(freq, amp, t60)]"""
    t = tax(n); y = np.zeros(n)
    for f, a, t60 in modes:
        if f >= SR / 2 * 0.9: continue
        ph = r.uniform(0, 2 * np.pi) if (rand_phase and r is not None) else 0.0
        y += a * np.exp(-6.91 * t / t60) * np.sin(2 * np.pi * f * t + ph)
    return y


def bell(f, dur, r, bright=1.0, warm=1.0, strike=0.25):
    """church bell (minor-third tierce), f = prime/strike pitch."""
    parts = [(0.5, 0.55 * warm, 1.00), (1.0, 0.75, 0.62), (1.183, 0.55, 0.48), (1.506, 0.28, 0.34),
             (2.0, 0.85 * bright, 0.30), (2.52, 0.32 * bright, 0.17), (2.66, 0.26 * bright, 0.15),
             (3.01, 0.22 * bright, 0.11), (4.07, 0.14 * bright, 0.07), (5.33, 0.07 * bright, 0.045)]
    n = N(dur); modes = []
    for ratio, a, tf in parts:
        fr = f * ratio * (1 + 0.002 * r.standard_normal())
        dd = 0.6 + 0.5 * r.random()
        modes += [(fr * (1 - 0.0009 * dd), a * 0.55, dur * tf), (fr * (1 + 0.0009 * dd), a * 0.45, dur * tf * 0.95)]
    y = modal(modes, n, r, rand_phase=True)
    # strike: short metallic clank
    k = N(0.03); sn = bp(r.standard_normal(k), 1200, 4500) * np.exp(-np.arange(k) / (k / 5))
    y[:k] += sn * strike
    y *= adsr(n, 0.0025, 100)
    return y / (np.max(np.abs(y)) + 1e-9)


def glass(f, dur, r, beat=1.2):
    """wine-glass / sea-glass resonance."""
    n = N(dur)
    modes = [(f - beat / 2, 0.5, dur * 0.9), (f + beat / 2, 0.5, dur * 0.85),
             (f * 2.32, 0.22, dur * 0.4), (f * 4.25, 0.08, dur * 0.18), (f * 6.63, 0.03, dur * 0.1)]
    y = modal(modes, n, r, rand_phase=True)
    y *= adsr(n, 0.004, 100)
    return y / (np.max(np.abs(y)) + 1e-9)


def noise_modal(modes, n, r, exc_ms=2.5):
    """modes excited by a short noise burst (more natural than pure decaying sines)."""
    k = max(8, N(exc_ms / 1000))
    exc = np.zeros(n); exc[:k] = lp(r.standard_normal(k), 5000) * np.hanning(k)
    y = np.zeros(n)
    for f, a, t60 in modes:
        if f >= SR / 2 * 0.9: continue
        q = max(0.7, t60 * np.pi * f / 6.91)
        y += resonator(exc, f, q) * a
    return y


def wood_tap(f, r, dur=0.12, damp=1.0, click=0.4):
    n = N(dur)
    modes = [(f, 1.0, 0.035 / damp), (f * 2.37, 0.6, 0.022 / damp), (f * 4.1, 0.3, 0.013 / damp),
             (f * 6.3, 0.12, 0.008 / damp)]
    y = noise_modal(modes, n, r)
    y /= (np.max(np.abs(y)) + 1e-9)
    k = N(0.004); y[:k] += lp(hp(r.standard_normal(k), 1200), 4000) * np.hanning(k) * click * 0.6
    y *= adsr(n, 0.0007, 100)
    return lp(y, 7000) / (np.max(np.abs(y)) + 1e-9)


def stone_tap(f, r, dur=0.08):
    n = N(dur)
    modes = [(f, 1.0, 0.025), (f * 1.62, 0.7, 0.018), (f * 2.33, 0.5, 0.012), (f * 3.4, 0.3, 0.008)]
    y = noise_modal(modes, n, r, 2.5)
    y /= (np.max(np.abs(y)) + 1e-9)
    k = N(0.003); y[:k] += bp(r.standard_normal(k), 1500, 5000) * np.hanning(k) * 0.25
    y *= adsr(n, 0.0006, 100)
    return lp(y, 7000) / (np.max(np.abs(y)) + 1e-9)


def brass_tink(f, r, dur=0.35):
    n = N(dur)
    modes = [(f, 1.0, dur * 0.8), (f * 2.76, 0.45, dur * 0.4), (f * 5.40, 0.18, dur * 0.2), (f * 8.93, 0.06, dur * 0.1)]
    y = modal(modes, n, r, rand_phase=True)
    y *= adsr(n, 0.0008, 100)
    return lp(y, 7500) / (np.max(np.abs(y)) + 1e-9)


def ceramic(f, r, dur=0.4):
    n = N(dur)
    modes = [(f, 1.0, 0.22), (f * 1.53, 0.5, 0.15), (f * 2.41, 0.4, 0.12), (f * 3.62, 0.2, 0.06), (f * 4.9, 0.1, 0.04)]
    y = modal(modes, n, r, rand_phase=True)
    y *= adsr(n, 0.0006, 100)
    return y / (np.max(np.abs(y)) + 1e-9)


def coin(f, r, dur=0.5):
    n = N(dur)
    modes = [(f, 0.8, 0.45), (f * 1.47, 0.6, 0.38), (f * 2.09, 0.55, 0.3), (f * 2.83, 0.3, 0.2), (f * 3.6, 0.18, 0.12)]
    y = modal(modes, n, r, rand_phase=True)
    y *= adsr(n, 0.0005, 100)
    return lp(y, 8000) / (np.max(np.abs(y)) + 1e-9)


# ------------------------------------------------------------------ air / feathers / wind
def whoosh(dur, fc, bw, r, env=None, color='pink', mode='band'):
    n = N(dur)
    x = noise(n, r, color)
    y = tv_filter(x, fc, bw, mode)
    if env is not None: y *= env
    return y


def feather_rustle(n, density_env, r, lo=1800, hi=6500, rate=600):
    """sparse micro-grains: feather vane friction."""
    p = np.clip(density_env, 0, None) * rate / SR
    hits = r.random(n) < p
    imp = hits * r.standard_normal(n)
    k = N(0.006); ker = np.hanning(k) ** 1.5          # soft grains: "shff", not crackle
    g = np.convolve(imp, ker)[:n]
    return bp(g, lo, min(hi, 5200))


def wingbeat(r, dur=0.22, fc0=1400, fc1=700, bw=1.4, low_f=260, low_g=0.6, rustle=0.25,
             peak=0.35, second=None):
    """one organic down-stroke: swelling air displacement + low push + feather grain."""
    n = N(dur); t = np.linspace(0, 1, n)
    e = hann_env(n, peak) ** 1.3
    if second:  # a later secondary feather layer (e.g. heavier bird, staggered primaries)
        t2, g2 = second
        e = e + g2 * np.roll(hann_env(n, peak) ** 1.6, int(t2 * n)) * (t > t2)
    fc = fc0 * (fc1 / fc0) ** (t ** 0.8)
    air = whoosh(dur, fc, bw, r, color='pink'); air = air / (np.std(air) + 1e-9) * e
    low = lp(noise(n, r, 'brown'), low_f, 2); low = low / (np.std(low) + 1e-9)
    e_low = np.concatenate([np.zeros(N(0.012)), e[:-N(0.012)]])
    low = low * e_low * low_g * 0.6
    fr = feather_rustle(n, e, r); fr = fr / (np.std(fr) + 1e-9) * e * rustle * 0.5
    y = air + low + fr
    y = hp(y, 55)
    return y


def gust_env(n, r, att=0.4, hold=0.4, rel=0.8, flutter=0.25, rate=6):
    t = tax(n); T = t[-1]
    a, h = att * T, hold * T
    e = np.where(t < a, np.sin(np.pi / 2 * t / a) ** 2, 1.0)
    e = np.where(t > a + h, np.cos(np.pi / 2 * np.clip((t - a - h) / (T - a - h), 0, 1)) ** 2, e)
    e *= 1 + flutter * smooth(n, rate, r) * 0.5
    return np.clip(e, 0, None)


def wind(n, r, speed, howl=0.15, hf=0.4, circular=False):
    """wind bed. speed: per-sample 0..1 control. returns mono."""
    src = (lambda c: circ_noise(n, r, c)) if circular else (lambda c: noise(n, r, c))
    low = src('brown')
    low = circ_filter(low, band_shape(30, 320, 2)) if circular else bp(low, 30, 320)
    mid = src('pink')
    if circular:
        # speed-dependent brightness via blend of two static bands (loop-safe)
        m1 = circ_filter(mid, band_shape(200, 900, 2))
        m2 = circ_filter(mid, band_shape(700, 2600, 2))
        y = low * (0.5 + 0.8 * speed) + m1 * (0.3 + 0.7 * speed) + m2 * hf * speed ** 1.6
    else:
        fc = 300 + 1500 * speed ** 1.4
        y = low * (0.5 + 0.8 * speed) + tv_filter(mid, fc, 1.8) * (0.4 + 0.9 * speed) + \
            tv_filter(src('pink'), fc * 2.2, 1.2) * hf * speed ** 1.6
    if howl > 0:
        for k, (base, q, g) in enumerate(((420, 35, 1.0), (640, 45, 0.6), (980, 50, 0.35))):
            exc = src('white')
            if circular:
                h = circ_filter(exc, lambda f, b=base, qq=q: 1 / (1 + ((f - b) / (b / qq)) ** 2))
            else:
                fcv = base * (0.75 + 0.5 * speed)
                h = tv_filter(exc, fcv, 0.07 + 0.02 * k)
            y = y + h * howl * g * speed ** 2 * 2.5
    return y * speed


# ------------------------------------------------------------------ water
def bubble(f0, dur, r, rise=0.12):
    n = N(dur); t = tax(n)
    f = f0 * (1 + rise * t / max(dur, 1e-3))
    ph = 2 * np.pi * np.cumsum(f) / SR
    d = max(0.006, 2.2 / f0 * 6)
    return np.sin(ph) * np.exp(-t / d) * adsr(n, 0.0008, 100)


def bubbles(n, times, r, fmin=500, fmax=2500, amp=1.0):
    out = np.zeros(n)
    for tt in times:
        f = np.exp(r.uniform(np.log(fmin), np.log(fmax)))
        place(out, bubble(f, 0.06, r, rise=r.uniform(0.05, 0.3)), tt, amp * r.uniform(0.3, 1.0))
    return out


def splash(r, size=1.0, dur=0.7, bright=4500):
    """water impact: cavity plop + spray + droplet bubbles."""
    n = N(dur); t = tax(n)
    f = 260 + 650 * np.exp(-t / 0.035) * (1 / size ** 0.5)
    plop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.05 * size)) * adsr(n, 0.002, 100)
    spray_env = adsr(n, 0.008, 0.09 * size)
    spray = tv_filter(noise(n, r, 'pink'), bright * (0.6 + 0.4 * np.exp(-t / 0.2)), 2.2) * spray_env
    low = lp(noise(n, r, 'brown'), 300) * adsr(n, 0.004, 0.06 * size)
    k = int(14 * size)
    bt = 0.02 + r.exponential(0.12 * size, k)
    bb = bubbles(n, bt[bt < dur - 0.07], r, 700, 3000, 0.18)
    drops = np.zeros(n)
    for tt in 0.12 + r.uniform(0, dur * 0.7, int(8 * size)):
        if tt < dur - 0.05:
            place(drops, bubble(r.uniform(1400, 3200), 0.04, r, 0.25), tt, 0.1 * r.random())
    y = plop * 0.9 + spray * 0.8 + low * 0.7 + bb + drops
    return hp(y, 40)


def wave_wash(dur, r, size=1.0, bright=1.0, circular=False):
    """one wave: rising swell, break, fizzing recede."""
    n = N(dur); t = np.linspace(0, 1, n)
    pk = 0.28
    e = np.where(t < pk, np.sin(np.pi / 2 * t / pk) ** 2, np.exp(-(t - pk) / 0.28))
    e *= adsr(n, 0.05, 100)
    taper = np.cos(np.pi / 2 * np.clip((t - 0.6) / 0.4, 0, 1)) ** 2
    e *= taper
    x = noise(n, r, 'pink')
    fc = (350 + 1500 * bright * np.where(t < pk, t / pk, np.exp(-(t - pk) / 0.35)))
    body = tv_filter(x, fc, 1.0, mode='lp', order=1.2)
    fizz = tv_filter(noise(n, r, 'white'), 2600 * bright + 400, 1.6) * np.where(t > pk, np.exp(-(t - pk) / 0.45), (t / pk) ** 3)
    nb = int(40 * size)
    bt = pk * dur + r.exponential(0.25 * dur, nb)
    bb = bubbles(n, bt[bt < dur - 0.08], r, 600, 2600, 0.06)
    y = (body * e * 1.0 + fizz * 0.22 * bright) * taper + bb
    return hp(y, 30) * size


def droplets_kernel(seed=7):
    k = N(0.004)
    rr = rng(seed)
    f = rr.uniform(1500, 4500)
    t = np.arange(k) / SR
    k = N(0.007); t = np.arange(k) / SR
    rise = np.sin(np.pi / 2 * np.minimum(1, t / 0.0006)) ** 2
    return (lp(rr.standard_normal(k), 5000) * 0.5 + np.sin(2 * np.pi * f * t) * 0.5) * np.exp(-t / rr.uniform(0.0012, 0.0024)) * rise


def rain(n, r, density, circular=False):
    """rain on water/stone. density: per-sample drops per second (array)."""
    p = np.clip(density, 0, None) / SR
    y = np.zeros(n)
    for kk in range(10):                     # ten different drop kernels: no comb colouring
        hits = (r.random(n) < p / 10) * r.lognormal(0, 0.5, n)
        ker = droplets_kernel(1000 + kk)
        if circular:
            y += np.real(np.fft.ifft(np.fft.fft(hits) * np.fft.fft(ker, n)))
        else:
            y += np.convolve(hits, ker)[:n]
    # occasional resonant drops on water
    bi = np.nonzero(r.random(n) < p * 0.04)[0]
    for i in bi:
        b = bubble(r.uniform(1800, 3600), 0.03, r, 0.3) * 0.5 * r.random()
        if circular:
            place_wrap(y, b, i)
        else:
            place(y, b, 0, i=i)
    bed_src = circ_noise(n, r, 'pink') if circular else noise(n, r, 'pink')
    bed = circ_filter(bed_src, band_shape(400, 5000, 1)) if circular else bp(bed_src, 400, 5000, 1)
    dn = density / 1500.0
    return y * 0.55 + bed * 0.22 * np.clip(dn, 0, None) ** 0.8


# ------------------------------------------------------------------ voices (birds)
def harmonic_voice(f0, amps_fn, r, kmax=None, jitter=0.006, shimmer=0.05, sub=0.0):
    """additive harmonic source following an f0 contour (array)."""
    n = len(f0)
    f = f0 * (1 + jitter * smooth(n, 35, r))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros(n)
    kmax = kmax or int(9000 / np.max(f0))
    for k in range(1, kmax + 1):
        a = amps_fn(k)
        alias = (k * f) < SR / 2 * 0.9
        y += a * np.sin(k * ph) * alias
    if sub > 0:
        y *= 1 + sub * np.sin(ph / 2)
    y *= 1 + shimmer * smooth(n, 25, r)
    return y


def gull_syllable(dur, f_start, f_peak, f_end, r, peak_at=0.3, rough=0.25, nasal=1.0, breath=0.06):
    n = N(dur); t = np.linspace(0, 1, n)
    f0 = np.where(t < peak_at, f_start + (f_peak - f_start) * np.sin(np.pi / 2 * t / peak_at),
                  f_peak + (f_end - f_peak) * np.clip((t - peak_at) / (1 - peak_at), 0, 1) ** 1.2)
    src = harmonic_voice(f0, lambda k: 1 / k ** 0.9, r, sub=rough)
    # nasal formants of a gull's syrinx/trachea
    y = src * 0.25
    for fc, q, g in ((1650, 5, 1.0 * nasal), (2900, 6, 0.75), (4200, 7, 0.35), (850, 4, 0.4)):
        y += resonator(src, fc, q) * g
    y += bp(noise(n, r), 2000, 4500) * breath * 3
    e = np.where(t < 0.08, np.sin(np.pi / 2 * t / 0.08) ** 2, 1.0) * np.cos(np.pi / 2 * np.clip((t - 0.75) / 0.25, 0, 1)) ** 1.5
    return lp(y * e, 5200, 4)


def cormorant_grunt(dur, f0, r, f_end=None, form=(480, 1050, 2300), rough=0.5):
    """guttural pulse-train croak with jittered periods and wide formants."""
    n = N(dur); t = tax(n)
    f_end = f_end or f0 * 0.85
    fcon = np.linspace(f0, f_end, n)
    imp = np.zeros(n); pos = 0.0
    while pos < n - 1:
        i = int(pos)
        imp[i] = 1.0 * (0.6 + 0.4 * r.random())
        per = SR / fcon[i] * (1 + rough * 0.25 * r.standard_normal())
        pos += max(SR / 400, per)
    glott = ss.lfilter([1], [1, -0.94], imp)
    glott = hp(glott, 60)
    y = glott * 0.2
    for fc, q, g in zip(form, (3, 4, 5), (1.0, 0.6, 0.25)):
        y += resonator(glott, fc, q) * g
    y += bp(noise(n, r), 400, 2500) * 0.08 * rough
    e = adsr(n, 0.02, 100) * np.where(t > dur - 0.08, np.cos(np.pi / 2 * (t - (dur - 0.08)) / 0.08) ** 2, 1)
    return lp(y * e, 4500)


# ------------------------------------------------------------------ impacts
def thump(r, f0=95, f1=45, dur=0.25, decay=0.07):
    n = N(dur); t = tax(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay) * adsr(n, 0.002, 100)


def stone_impact(r, mass=1.0, rough=0.3, dur=0.6, scale=1.0):
    n = N(dur)
    th = thump(r, 105 / mass ** 0.4, 48 / mass ** 0.3, dur, 0.06 * mass ** 0.5)
    nb = lp(noise(n, r, 'pink'), 1800 / mass ** 0.3) * adsr(n, 0.001, 0.018 * mass ** 0.5)
    modes = [(f * scale / mass ** 0.25, a, t60) for f, a, t60 in
             ((310, 0.5, 0.11), (720, 0.4, 0.08), (1240, 0.3, 0.06), (1890, 0.15, 0.04), (2650, 0.07, 0.03))]
    md = modal(modes, n, r, rand_phase=True) * adsr(n, 0.0008, 100)
    grit = np.zeros(n)
    for tt in 0.03 + r.exponential(0.12, int(10 * rough + 2)):
        if tt < dur - 0.03:
            place(grit, stone_tap(r.uniform(1800, 3800), r, 0.03), tt, r.uniform(0.02, 0.09) * rough)
    return th * 1.0 + nb * 0.6 + md * 0.35 + grit


def friction_creak(dur, r, f_rate=(30, 90), modes=(240, 610, 1180), q=(12, 15, 18), env=None):
    """stick-slip wood creak: irregular pulse train exciting wood resonances."""
    n = N(dur); t = np.linspace(0, 1, n)
    rate = f_rate[0] + (f_rate[1] - f_rate[0]) * (0.5 + 0.5 * np.sin(np.pi * t * r.uniform(0.8, 1.6) + r.uniform(0, 3)))
    imp = np.zeros(n); pos = 0.0
    while pos < n - 1:
        i = int(pos); imp[i] = r.uniform(0.5, 1.0)
        pos += SR / rate[i] * (1 + 0.15 * r.standard_normal())
        pos = max(pos, i + 1)
    imp = np.convolve(imp, np.hanning(15))[:n]       # stick-slip pulse ~0.3 ms, not a digital impulse
    y = np.zeros(n)
    for fc, qq in zip(modes, q):
        y += resonator(imp, fc * r.uniform(0.95, 1.05), qq)
    e = env if env is not None else hann_env(n, 0.4)
    y = hp(y * e, 120)
    return y / (np.max(np.abs(y)) + 1e-9)
