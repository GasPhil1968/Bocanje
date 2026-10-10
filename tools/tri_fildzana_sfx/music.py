"""Background music loops for TRI FILDŽANA (one per scene background).
python3 music.py <out_dir>  ->  <out_dir>/audio/music/music_<name>.mp3 + music.json

Each loop is rendered longer than its musical length L and the overflow (ringing strings, room)
is folded back onto the start, so the signal is exactly periodic with period L. The file holds
L + 0.6 s of that periodic signal; the game loops [0.25 s, 0.25 s + L), which stays seamless
whatever encoder/decoder delay the MP3 adds."""
import sys, os, json, subprocess, zlib
from models import *
from sounds import nz, stereo_room
from core import _kweight

PC = lambda m: m % 12
mf = lambda m: 440.0 * 2 ** ((m - 69) / 12)
QUAL = {'M': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10]}
NAMES = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}


def chord(sym):
    root = sym[:2] if len(sym) > 1 and sym[1] in '#b' else sym[:1]
    q = sym[len(root):] or 'M'
    return [(NAMES[root] + i) % 12 for i in QUAL[q]]


def place_pc(pc, lo):
    """lowest midi >= lo with pitch class pc"""
    return lo + ((pc - lo) % 12)


# ------------------------------------------------------------------------------- track specs
TRACKS = {
 # name: scene index in SCENE_OF / BG_NAMES order
 'studio': dict(scene=0, bpm=104, bb=4, key=2, scale=[0, 2, 4, 5, 7, 9, 11],
     chords='D D G D A7 A7 D D G G D Bm Em A7 D A7'.split(),
     bass=[(0, 'r', 0.9), (2, '5', 0.9)], comp=[(1, .55, .55), (3, .5, .55)], arp=None,
     motifs={'a': [(0, 1), (1, .5), (1.5, .5), (2, 1), (3, 1), (4, 2), (6, 2)],
             'b': [(0, .5), (.5, .5), (1, 1), (2, .5), (2.5, .5), (3, 1), (4, 3)]},
     phrases=[(0, 'a'), (2, 'b'), (4, 'a'), (6, 'b'), (8, 'b'), (10, 'a'), (12, 'b'), (14, 'a')],
     mel=(62, 86, 74), trem=1.5, perc=[(0, 'dum', .5), (2, 'dum', .3), (1, 'tek', .25), (3, 'tek', .25)],
     mel_t60=0.9, gains=dict(mel=.55, bass=.5, comp=.32, perc=.2)),
 'kafana': dict(scene=1, bpm=92, bb=3, key=9, scale=[0, 1, 4, 5, 7, 8, 10],
     chords='A A Dm Dm Gm Gm A A Dm Dm Gm Gm A Bb A A'.split(),
     bass=[(0, 'r', 1.4)], comp=[(1, .45, .85), (2, .4, .85)], arp=None,
     motifs={'a': [(0, 2), (2, 1), (3, 1.5), (4.5, .5), (5, 1)],
             'b': [(0, 3), (3, 1), (4, 1), (5, 1)]},
     phrases=[(0, 'a'), (2, 'b'), (4, 'a'), (6, 'b'), (8, 'b'), (10, 'a'), (12, 'a'), (14, 'b')],
     mel=(57, 81, 69), trem=1.9, perc=[(0, 'dum', .3)], mel_t60=1.2, mel_S=0.4,
     gains=dict(mel=.6, bass=.5, comp=.3, perc=.15)),
 'noc': dict(scene=2, bpm=72, bb=4, key=2, scale=[0, 2, 3, 5, 7, 8, 10],
     chords='Dm Dm Bb Bb Gm Gm A A Dm Bb Gm A'.split(),
     bass=[(0, 'r', 3.6)], comp=None,
     arp=[(0, 0, .45, 1), (1, 1, .35, 1), (2, 2, .4, 1), (3, 1, .32, 1)],
     motifs={'a': [(0, 1.5), (1.5, .5), (2, 2)], 'b': [(0, 1), (1, 1), (2, 2), (4, 4)]},
     phrases=[(2, 'a'), (6, 'b'), (10, 'a')],
     mel=(62, 81, 69), trem=1.9, perc=[], mel_t60=1.4, mel_S=0.45,
     gains=dict(mel=.5, bass=.45, comp=.35, perc=0)),
 'ured': dict(scene=3, bpm=126, bb=2, key=7, scale=[0, 2, 3, 5, 7, 8, 11],
     chords=('Gm Gm D7 D7 Gm Gm Cm D7 Gm Gm Cm Cm D7 D7 Gm Gm '
             'Eb Eb Bb Bb Cm Cm D7 D7 Gm Gm Cm Cm Gm D7 Gm D7').split(),
     bass=[(0, 'r', .45)], comp=[(1, .5, .2)], arp=None, bass_stacc=True,
     motifs={'a': [(0, .5), (.5, .5), (1, .5), (1.5, .5), (2, 1), (3, 1)],
             'b': [(0, 1), (1, .5), (1.5, .5), (2, .5), (3, 1)]},
     phrases=[(i, 'a' if (i // 2) % 2 == 0 else 'b') for i in range(0, 32, 2) if i not in (14, 30)],
     mel=(67, 86, 74), trem=None, stacc=0.55, perc=[(1, 'tick', .35)], mel_t60=0.7,
     gains=dict(mel=.5, bass=.5, comp=.3, perc=.2)),
 'autobus': dict(scene=4, bpm=300, bb=7, key=4, scale=[0, 1, 4, 5, 7, 8, 10],
     chords='E E F E Dm Dm E E Am Am Dm E E E F E Dm Dm F E Dm E'.split(),
     bass=[(0, 'r', 1.6), (2, '5', 1.6), (4, 'r', 2.6)], comp=[(1, .45, .7), (3, .45, .7), (5, .4, .7), (6, .35, .7)], arp=None,
     motifs={'a': [(0, 2), (2, 1), (3, 1), (4, 3), (7, 2), (9, 2), (11, 3)],
             'b': [(0, 4), (4, 3), (7, 1), (8, 1), (9, 2), (11, 3)]},
     phrases=[(0, 'a'), (2, 'b'), (4, 'a'), (6, 'b'), (10, 'a'), (12, 'b'), (14, 'a'), (16, 'b'), (18, 'a')],
     mel=(64, 88, 76), trem=3.5, perc=[(0, 'dum', .45), (2, 'tek', .25), (4, 'dum', .35), (5, 'tek', .2), (6, 'tek', .2)],
     mel_t60=0.9, gains=dict(mel=.55, bass=.5, comp=.3, perc=.25)),
 'montaza': dict(scene=5, bpm=92, bb=4, key=4, scale=[0, 2, 3, 5, 7, 8, 10],
     chords='Em Em C C Am Am B B Em Em C C Am B Em B'.split(),
     bass=[(0, 'r', 1.8), (2, 'r', 1.8)], comp=None,
     arp=[(0, 0, .35, .45), (.5, 1, .28, .45), (1, 2, .3, .45), (1.5, 1, .28, .45),
          (2, 0, .33, .45), (2.5, 1, .28, .45), (3, 2, .3, .45), (3.5, 3, .28, .45)],
     motifs={'a': [(0, 1.5), (1.5, .5), (2, 1), (3, 1), (4, 4)], 'b': [(0, 1), (1, 1), (2, 1), (3, 1), (4, 2), (6, 2)]},
     phrases=[(2, 'a'), (6, 'b'), (10, 'a'), (14, 'b')],
     mel=(64, 84, 71), trem=None, perc=[(0, 'tick', .3), (1, 'tick', .18), (2, 'tick', .25), (3, 'tick', .18)],
     mel_t60=1.0, gains=dict(mel=.5, bass=.45, comp=.3, perc=.12)),
 'nocna_smjena': dict(scene=6, bpm=72, bb=4, key=9, scale=[0, 2, 3, 5, 7, 8, 11],
     chords='Am Am F F Dm Dm E E Am F E E'.split(),
     bass=[(0, 'r', 1.8), (2, '5', 1.8)], comp=None,
     arp=[(0, 0, .4, 1), (1, 1, .3, 1), (2, 2, .35, 1), (3, 1, .3, 1)],
     motifs={'a': [(0, 3), (3, 1), (4, 4)], 'b': [(0, 2), (2, 1), (3, 1), (4, 4)]},
     phrases=[(1, 'a'), (5, 'b'), (9, 'a')],
     mel=(57, 77, 64), trem=1.9, perc=[], mel_t60=1.4, mel_S=0.45,
     gains=dict(mel=.55, bass=.45, comp=.35, perc=0)),
}


# ------------------------------------------------------------------------------- composer
def compose_melody(sp, r):
    lo, hi, start = sp['mel']; bb = sp['bb']
    sc = [m for m in range(lo, hi + 1) if PC(m - sp['key']) in sp['scale']]
    prev = start; notes = []
    for k, (bar0, mk) in enumerate(sp['phrases']):
        mot = sp['motifs'][mk]
        dirn = 1 if k % 2 == 0 else -1
        for j, (on, du) in enumerate(mot):
            t = bar0 * bb + on
            bar = int(t // bb) % len(sp['chords'])
            ct = chord(sp['chords'][bar])
            strong = abs((on % bb)) < 1e-6 or (bb == 4 and abs(on % 2) < 1e-6) or (bb == 7 and (on % 7) in (0, 2, 4))
            if j == len(mot) - 1:          # phrase end: root (cadence) or third
                tgt = [ct[0]] if k % 2 else ct[:2]
                cands = [m for m in sc if PC(m) in tgt] or sc
                p = min(cands, key=lambda m: abs(m - prev) + (0 if m >= prev - 5 else 2))
            elif strong:
                cands = [m for m in sc if PC(m) in ct]
                pref = [m for m in cands if 0 < dirn * (m - prev) <= 7]
                p = min(pref or cands, key=lambda m: abs(m - prev))
            else:
                i = min(range(len(sc)), key=lambda i: abs(sc[i] - prev))
                st = 2 if r.random() < 0.25 else 1
                i2 = i + dirn * st
                if i2 < 0 or i2 >= len(sc):
                    dirn = -dirn; i2 = i + dirn * st
                p = sc[max(0, min(len(sc) - 1, i2))]
            if r.random() < 0.3 and j > 0:
                dirn = -dirn
            if j == len(mot) // 2:
                dirn = -1 if k % 2 == 0 else 1     # arch contour
            notes.append((t, p, du, 0.82 if strong else 0.66))
            prev = p
    return notes


def build(sp, r):
    beat = 60.0 / sp['bpm']; bb = sp['bb']; nb = len(sp['chords'])
    L = nb * bb * beat; tail = 3.0; dur = L + tail
    hum = lambda: r.normal(0, 0.006)
    T = lambda b: b * beat
    # melody
    ev = []
    for (t, p, du, v) in compose_melody(sp, r):
        tt = T(t) + hum()
        if sp.get('trem') and du >= sp['trem']:
            ev += tremolo(tt, mf(p), T(du) * 0.92, rate=15, vel=v * 0.75, r=r, decresc=0.35)
            ev[-1]['off'] = 0.12; ev[-1]['mute'] = 0.35
        else:
            if du >= 1 and r.random() < 0.22 and tt > 0.1:   # grace note from above, then slide
                up = p + (2 if PC(p - sp['key'] + 2) in sp['scale'] else 1)
                ev.append(dict(t=tt - 0.07, f=mf(up), vel=v * 0.6))
                ev.append(dict(t=tt, f=mf(p), vel=0.0, glide=0.03, off=T(du) * 0.98, mute=0.3))
            else:
                ev.append(dict(t=tt, f=mf(p), vel=v, off=T(du) * sp.get('stacc', 0.98), mute=0.3 if 'stacc' not in sp else 0.15))
    ev = sorted(ev, key=lambda e: e['t'])
    mel = string_track(dur, [e for e in ev if e['t'] >= 0], r, t60=sp['mel_t60'], S=sp.get('mel_S', 0.34))
    # bass
    bev = []
    for b, sym in enumerate(sp['chords']):
        ct = chord(sym)
        for (bt, sel, du) in sp['bass']:
            pc = {'r': ct[0], '5': ct[2], '3': ct[1]}[sel]
            m = place_pc(pc, 38)
            bev.append(dict(t=T(b * bb + bt) + hum(), f=mf(m), vel=0.85 if bt == 0 else 0.7, off=T(du) if sp.get('bass_stacc') else None, mute=0.15, pos=0.22))
    bass = string_track(dur, bev, r, t60=2.0, S=0.5, body=BASS_BODY)
    # comp: strummed off-beat chords (3 strings) or arpeggios (one string)
    comp = []
    if sp['comp']:
        for s in range(3):
            cev = []
            for b, sym in enumerate(sp['chords']):
                ct = chord(sym)[:3]
                vo = sorted(place_pc(pc, 55) for pc in ct)
                for (bt, v, du) in sp['comp']:
                    off = (s if (b + int(bt)) % 2 == 0 else 2 - s) * 0.011
                    cev.append(dict(t=T(b * bb + bt) + off + hum() * 0.5, f=mf(vo[s]), vel=v * r.uniform(0.85, 1.05), off=T(du), mute=0.18, pos=0.2))
            comp.append(string_track(dur, cev, r, t60=0.7, S=0.42, pick_bright=0.55))
    if sp['arp']:
        aev = []
        for b, sym in enumerate(sp['chords']):
            ct = chord(sym)[:3]
            vo = sorted(place_pc(pc, 52) for pc in ct) + [place_pc(ct[0], 52) + 12]
            for (bt, idx, v, du) in sp['arp']:
                aev.append(dict(t=T(b * bb + bt) + hum(), f=mf(vo[idx]), vel=v * r.uniform(0.85, 1.05), pos=0.2))
        comp.append(string_track(dur, aev, r, t60=2.2, S=0.4, pick_bright=0.45))
    # percussion
    perc = np.zeros(N(dur))
    for b in range(nb):
        for (bt, kind, v) in sp['perc']:
            t = T(b * bb + bt) + hum()
            if kind == 'tick':
                x = nz(conv(pulse(0.0004), hardwood_ir(r, f=(1150, 2400, 3900), t60=0.03, length=0.06)))
            else:
                x = nz(drum(r, 100, kind, t60=0.25 if kind == 'dum' else 0.1, length=0.5))
            place(perc, x * v * r.uniform(0.85, 1.05), t)
    g = sp['gains']
    tracks = [(mel, -0.12, g['mel']), (bass, 0.05, g['bass'])]
    for k, c in enumerate(comp):
        tracks.append((c, [0.3, 0.15, 0.4, 0.25][k], g['comp'] / (len(comp) ** 0.5)))
    if np.any(perc):
        tracks.append((perc, -0.05, g['perc']))
    n = N(dur); y = np.zeros((n, 2))
    for x, p, gg in tracks:
        y[:min(n, len(x))] += pan(nz(x[:n]), p) * gg
    y = stereo_room(y, r, wet=0.24, t60=1.0)
    y = np.stack([lp(y[:, c], 9000) for c in range(2)], 1)
    # fold the overflow back onto the start -> exactly periodic with period L
    nL = N(L); z = y[:nL].copy(); over = y[nL:]
    for s0 in range(0, len(over), nL):
        seg = over[s0:s0 + nL]; z[:len(seg)] += seg
    z = hp(z, 30)
    return z, nL


def integrated_k(x):
    k = _kweight(x)
    return -0.691 + 10 * np.log10(np.mean(np.sum(k ** 2, axis=1)) + 1e-20)


def main(out):
    d = os.path.join(out, 'audio', 'music'); os.makedirs(d, exist_ok=True)
    meta = []
    for name, sp in TRACKS.items():
        r = rng(zlib.crc32(name.encode()))
        z, nL = build(sp, r)
        z *= undb(-20.0 - integrated_k(z))
        tp = true_peak(z)
        if tp > undb(-1.5):
            z *= undb(-1.5) / tp
        full = np.vstack([z, z[:N(0.6)]])
        wav = os.path.join(d, f'_{name}.wav'); mp3 = os.path.join(d, f'music_{name}.mp3')
        write16(wav, full)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-c:a', 'libmp3lame', '-b:a', '128k', mp3], check=True)
        os.remove(wav)
        L = nL / SR
        meta.append(dict(id=f'music_{name}', file=f'audio/music/music_{name}.mp3', scene=sp['scene'], loop_start_s=0.25,
                         loop_end_s=round(0.25 + L, 6), loop_length_s=round(L, 6), bpm=sp['bpm'],
                         loudness_lufs=round(integrated_k(z), 1), true_peak_dbtp=round(db(true_peak(z)), 2),
                         size_kb=os.path.getsize(mp3) // 1024))
        print(meta[-1])
    json.dump(meta, open(os.path.join(out, 'music.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
