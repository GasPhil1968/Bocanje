"""Render + master all music loops (base and synchronous layer stems)."""
import os, sys, json, time, zlib
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'galeb_sfx'))
from master import loudness, true_peak, write_wav
from lib import circ_filter
import songs

CEIL_DB = -3.2
LAYER_REL_DB = -6.0
TARGET = {'mus_menu': -20.0, 'mus_fever': -19.0, 'mus_end_screen': -21.0}   # cities: -20


def eq(x):
    """loop-safe master EQ: subsonic high-pass, gentle top roll-off for small speakers."""
    return circ_filter(x, lambda f: (1 / np.sqrt(1 + (35 / f) ** 4)) / np.sqrt(1 + (f / 12000) ** 4))


def render_song(name):
    t0 = time.time()
    s = songs.SONGS[name]()
    base = eq(s.reverb(s.render('base')))
    has_layer = any(e['part'] == 'layer' for e in s.events)
    layer = eq(s.reverb(s.render('layer'))) if has_layer else None
    base -= base.mean(axis=0)
    L0 = loudness(base, loop=True)
    tgt = TARGET.get(name, -20.0)
    g = 10 ** ((tgt - L0) / 20)
    gl = 0.0
    tp = true_peak(base * g)
    if layer is not None:
        layer -= layer.mean(axis=0)
        gl = 10 ** ((tgt + LAYER_REL_DB - loudness(layer, loop=True)) / 20)   # layer sits 6 dB under the base
        tp = max(tp, true_peak(base * g + layer * gl))
    if tp > 10 ** (CEIL_DB / 20):
        k = 10 ** (CEIL_DB / 20) / tp; g *= k; gl *= k
    meta = dict(bpm=s.bpm, beats_per_bar=s.bpb, bars=s.nbars, samples=s.nsamples, gain_db=20 * np.log10(g),
                loud_in=L0, render_s=time.time() - t0, has_layer=has_layer)
    return name, base * g, (layer * gl if layer is not None else None), meta


def render_all(out_root, names=None, procs=4):
    names = names or list(songs.SONGS)
    info = {}
    d = os.path.join(out_root, 'music'); os.makedirs(d, exist_ok=True)
    with Pool(procs) as p:
        for name, base, layer, meta in p.imap_unordered(render_song, names):
            write_wav(os.path.join(d, name + '.wav'), base, zlib.crc32(name.encode()))
            if layer is not None:
                write_wav(os.path.join(d, name + '_layer.wav'), layer, zlib.crc32((name + 'L').encode()))
            info[name] = meta
            print(f'{name}: {meta["samples"] / 44100:.2f}s gain {meta["gain_db"]:+.1f} dB render {meta["render_s"]:.0f}s', flush=True)
    return info


if __name__ == '__main__':
    info = render_all(sys.argv[1], sys.argv[2:] or None)
    json.dump(info, open(os.path.join(sys.argv[1], 'render_info.json'), 'w'), indent=1)
