"""Shared DSP helpers for the Boce na rivi audio pack (48 kHz, float64 internally)."""
import numpy as np, soundfile as sf, os
from scipy import signal as ss

SR = 48000
OUT = None          # set by build scripts: root of boce_na_rivi_complete_audio/

def rng(seed):
    return np.random.default_rng(seed)

def t_axis(dur, sr=SR):
    return np.arange(int(round(dur*sr)))/sr

def db(x):  return 20*np.log10(max(x, 1e-12))
def undb(d): return 10**(d/20)

# ---------------------------------------------------------------- filters
def sos_filt(x, kind, f, order=2, sr=SR):
    if kind == 'bp':
        sos = ss.butter(order, [max(10, f[0]), min(sr/2*0.98, f[1])], 'bandpass', fs=sr, output='sos')
    else:
        sos = ss.butter(order, min(f, sr/2*0.98), {'lp':'lowpass','hp':'highpass'}[kind], fs=sr, output='sos')
    return ss.sosfilt(sos, x, axis=0)

def lp(x, f, o=2): return sos_filt(x, 'lp', f, o)
def hp(x, f, o=2): return sos_filt(x, 'hp', f, o)
def bp(x, lo, hi, o=2): return sos_filt(x, 'bp', (lo, hi), o)

def peaking(x, f0, gain_db, q, sr=SR):
    A = 10**(gain_db/40); w = 2*np.pi*f0/sr; al = np.sin(w)/(2*q)
    b = [1+al*A, -2*np.cos(w), 1-al*A]; a = [1+al/A, -2*np.cos(w), 1-al/A]
    return ss.lfilter(np.array(b)/a[0], np.array(a)/a[0], x, axis=0)

def shelf_hi(x, f0, gain_db, sr=SR):
    A = 10**(gain_db/40); w = 2*np.pi*f0/sr; al = np.sin(w)/2*np.sqrt(2)
    c = np.cos(w); sA = 2*np.sqrt(A)*al
    b = [A*((A+1)+(A-1)*c+sA), -2*A*((A-1)+(A+1)*c), A*((A+1)+(A-1)*c-sA)]
    a = [(A+1)-(A-1)*c+sA, 2*((A-1)-(A+1)*c), (A+1)-(A-1)*c-sA]
    return ss.lfilter(np.array(b)/a[0], np.array(a)/a[0], x, axis=0)

def resonator(x, f, q, sr=SR):
    """2-pole constant-peak-gain resonator."""
    r = np.exp(-np.pi*f/(q*sr)); w = 2*np.pi*f/sr
    b = [(1-r*r)/2, 0, -(1-r*r)/2]; a = [1, -2*r*np.cos(w), r*r]
    return ss.lfilter(b, a, x, axis=0)

def onepole_lp(x, f, sr=SR):
    a = np.exp(-2*np.pi*f/sr)
    return ss.lfilter([1-a], [1, -a], x, axis=0)

# ---------------------------------------------------------------- sources
def noise(n, r, color='white'):
    w = r.standard_normal(n)
    if color == 'pink':
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        w = ss.lfilter(b, a, w); w /= np.std(w)+1e-12
    elif color == 'brown':
        w = ss.lfilter([1], [1, -0.995], w); w = hp(w, 15); w /= np.std(w)+1e-12
    return w

def smooth_noise(n, rate_hz, r, sr=SR):
    """slowly varying random control signal, ~unit std."""
    k = max(2, int(n*rate_hz/sr)+3)
    pts = r.standard_normal(k)
    xi = np.linspace(0, k-1, n)
    from scipy.interpolate import CubicSpline
    return CubicSpline(np.arange(k), pts)(xi)

def modal(modes, n, sr=SR):
    """modes: list of (freq, amp, decay_seconds_T60, phase). Returns impulse response."""
    t = np.arange(n)/sr; y = np.zeros(n)
    for m in modes:
        f, a, t60 = m[0], m[1], m[2]; ph = m[3] if len(m) > 3 else 0
        if f >= sr/2*0.95: continue
        y += a*np.exp(-6.91*t/t60)*np.sin(2*np.pi*f*t+ph)
    return y

def hertz_pulse(dur, sr=SR):
    """contact-force pulse (half-sine^1.5), dur in seconds."""
    n = max(3, int(dur*sr)); t = np.linspace(0, np.pi, n)
    return np.sin(t)**1.5

def conv(x, h):
    return ss.fftconvolve(x, h)[:len(x)+len(h)-1]

def grain(r, f, q, dur, sr=SR, sharp=6.0):
    """short resonant click (a pebble tick)."""
    n = max(8, int(dur*sr)); t = np.arange(n)/sr
    e = r.standard_normal(n)*np.exp(-t*sr/ (n/sharp))
    return resonator(e, f, q)

def scatter(n, times, amps, make, r):
    out = np.zeros(n)
    for ti, a in zip(times, amps):
        g = make(r)*a; i = int(ti*SR)
        if i >= n: continue
        m = min(len(g), n-i); out[i:i+m] += g[:m]
    return out

# ---------------------------------------------------------------- dynamics / finishing
def env_ad(n, a, d, sr=SR, curve=3.0):
    t = np.arange(n)/sr
    e = np.where(t < a, (t/max(a,1e-6)), np.exp(-curve*(t-a)/max(d,1e-6)))
    return e

def fade(x, fin=0.0015, fout=0.02, sr=SR):
    x = np.array(x, dtype=np.float64)
    n = len(x); i = int(fin*sr); o = int(fout*sr)
    if i > 0:
        w = np.sin(np.linspace(0, np.pi/2, i))**2
        x[:i] *= w if x.ndim == 1 else w[:, None]
    if o > 0:
        w = np.cos(np.linspace(0, np.pi/2, o))**2
        x[-o:] *= w if x.ndim == 1 else w[:, None]
    return x

def dc_block(x, f=18):
    return hp(x, f, 2)

def trim_lead(x, thresh_db=-50, keep=0.002, sr=SR):
    """remove silence before the first transient, keep `keep` s of pre-roll."""
    m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    pk = m.max()
    if pk <= 0: return x
    idx = np.argmax(m > pk*undb(thresh_db))
    s = max(0, idx-int(keep*sr))
    return x[s:]

def trim_tail(x, thresh_db=-62, sr=SR, min_len=0.05):
    m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    pk = m.max(); thr = pk*undb(thresh_db)
    above = np.nonzero(m > thr)[0]
    end = above[-1]+int(0.01*sr) if len(above) else len(x)
    end = max(end, int(min_len*sr))
    return x[:min(len(x), end)]

def true_peak(x):
    y = ss.resample_poly(x, 4, 1, axis=0)
    return float(np.max(np.abs(y)))

def norm_peak(x, target_db):
    p = true_peak(x)
    return x*(undb(target_db)/p) if p > 0 else x

def finish(x, peak_db, fin=0.001, fout=0.03, trim=True, tail_db=-60, lead_db=-45):
    x = dc_block(x)
    if trim:
        x = trim_lead(x, lead_db)
        x = trim_tail(x, tail_db)
    x = fade(x, fin, fout)
    x = x - (np.mean(x, axis=0) if x.ndim > 1 else np.mean(x))
    x = fade(x, fin, fout)
    return norm_peak(x, peak_db)

def pan(x, p):
    """equal-power pan, p in [-1, 1] -> stereo (n,2)."""
    a = (p+1)*np.pi/4
    return np.stack([x*np.cos(a), x*np.sin(a)], axis=1)

def early_reflections(x, r, taps=((0.011, 0.22, -0.4), (0.019, 0.16, 0.5), (0.031, 0.10, -0.7),
                                  (0.047, 0.07, 0.8)), tail=0.0, tail_t=0.35, sr=SR):
    """Outdoor stone-riva reflections: a few discrete taps + optional faint diffuse tail.
    x mono -> stereo."""
    n = len(x) + int((max(t for t, _, _ in taps)+tail_t+0.05)*sr)
    y = np.zeros((n, 2)); y[:len(x)] += pan(x, 0)
    for d, g, p in taps:
        i = int(d*sr); s = pan(lp(x, 5000)*g, p); y[i:i+len(x)] += s
    if tail > 0:
        m = int(tail_t*sr); tt = np.arange(m)/sr
        ir = np.stack([r.standard_normal(m), r.standard_normal(m)], 1)*np.exp(-6.91*tt/tail_t)[:, None]
        ir = lp(ir, 4000)
        for c in range(2):
            y[:, c] += tail*ss.fftconvolve(x, ir[:, c])[:n] / np.sqrt(m) * 4
    return y

def make_loop(x, xfade_s, sr=SR):
    """x longer than target by xfade: overlap-add tail onto head with equal-power fades.
    Result length = len(x)-xfade samples and wraps seamlessly."""
    k = int(xfade_s*sr)
    head = x[:k].copy(); tail = x[-k:].copy(); body = x[:-k].copy()
    w = np.linspace(0, 1, k)
    fi = np.sin(w*np.pi/2); fo = np.cos(w*np.pi/2)
    if x.ndim > 1: fi = fi[:, None]; fo = fo[:, None]
    body[:k] = head*fi + tail*fo
    return body

def loop_seam_report(x, sr=SR):
    """compare the sample step and short-term spectrum across the wrap point with the
    distribution elsewhere."""
    m = x if x.ndim == 1 else x.mean(axis=1)
    steps = np.abs(np.diff(m)); wrap = abs(m[0]-m[-1])
    p999 = float(np.percentile(steps, 99.9))
    win = 2048
    def spec(seg): return np.log10(np.abs(np.fft.rfft(seg*np.hanning(len(seg))))+1e-9)
    joined = np.concatenate([m[-win//2:], m[:win//2]])
    flux_seam = float(np.mean(np.abs(spec(joined)-spec(m[-win:]))))
    fl = []
    rr = np.random.default_rng(0)
    for _ in range(40):
        i = rr.integers(win, len(m)-win)
        fl.append(np.mean(np.abs(spec(m[i-win//2:i+win//2])-spec(m[i-win:i]))))
    rms_l = float(np.sqrt(np.mean(m[-sr//10:]**2))); rms_f = float(np.sqrt(np.mean(m[:sr//10]**2)))
    return dict(wrap_step=float(wrap), step_p999=p999, seam_flux=flux_seam,
                flux_median=float(np.median(fl)), flux_p95=float(np.percentile(fl, 95)),
                rms_last100ms=rms_l, rms_first100ms=rms_f,
                ok=bool(wrap <= max(p999, 1e-4) and flux_seam <= np.percentile(fl, 95)*1.15))

def write(rel, x, bits=24, sr=SR):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    assert np.all(np.isfinite(x)), rel
    assert np.max(np.abs(x)) < 1.0, rel
    sf.write(path, x.astype(np.float32), sr, subtype='PCM_24' if bits == 24 else 'PCM_16')
    return path

def resample(x, sr_in, sr_out=SR):
    from math import gcd
    g = gcd(sr_in, sr_out)
    return ss.resample_poly(x, sr_out//g, sr_in//g, axis=0)
