"""Music pack build: render -> QA -> OGG -> manifest / guide / QA report -> ZIP (+ verification).

usage: python3 build_music.py <work_dir> <zip_out>
"""
import os, sys, json, shutil, subprocess, zipfile, wave, datetime, itertools, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'galeb_sfx'))
import render, songs
from master import loudness, true_peak
from qa import seam, click_scan, hf_ratio, features
from build import ogg_encode

PACK = 'galeb_nad_jadranom_music'
SR = 44100
NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

TRACKS = {
    'mus_menu': dict(use='Title screen, intro (uvod), menus, route map, passport', city=None, style='Dalmatian serenade waltz: guitar, mandolin, hummed voices',
                     trigger='pokreniUvod() / any menu state (state==="ready" before the first flight, end of zavrsiUvod())', mode='major'),
    'mus_city_split': dict(use='Flight over Split', city='Split', style='Klapa (4-part male a cappella, wordless) with guitar; mandolin verse',
                           trigger='SCENE().name==="Split" while playing'),
    'mus_city_dubrovnik': dict(use='Flight over Dubrovnik', city='Dubrovnik', style='Solemn minor klapa in stone acoustics, mandolin interlude',
                               trigger='SCENE().name==="Dubrovnik" while playing'),
    'mus_city_sibenik': dict(use='Flight over Šibenik', city='Šibenik', style='Poskočica: lively mandolins, guitar chop, berda bass, tapan',
                             trigger='SCENE().name==="Šibenik" while playing'),
    'mus_city_makarska': dict(use='Flight over Makarska', city='Makarska', style='Relaxed minor 3/4: guitar arpeggios, mandolin and klapa verses',
                              trigger='SCENE().name==="Makarska" while playing'),
    'mus_city_zadar': dict(use='Flight over Zadar', city='Zadar', style='Open major klapa over breathing flue pipes (a nod to the Sea Organ)',
                           trigger='SCENE().name==="Zadar" while playing'),
    'mus_city_pula': dict(use='Flight over Pula', city='Pula', style='Istrian two-part music on the six-tone Istrian scale: sopile and voices, tapan',
                          trigger='SCENE().name==="Pula" while playing'),
    'mus_fever': dict(use='Fever mode ("GALEB!", 6 s)', city=None, style='Fast bright 2/4: tremolo mandolins in thirds, bass, tapan, def',
                      trigger='feverStart() .. feverKraj()'),
    'mus_end_screen': dict(use='End screen after a crash (score, medal, postcard)', city=None,
                           style='Calm melancholic 3/4: guitar, soft mandolin, hummed voices', trigger='die(): after the game-over sting'),
}
DUR = {'mus_fever': (25, 40), 'mus_end_screen': (35, 60)}


def read(path):
    with wave.open(path) as w:
        p = dict(ch=w.getnchannels(), sw=w.getsampwidth(), sr=w.getframerate(), n=w.getnframes(), comp=w.getcomptype())
        x = np.frombuffer(w.readframes(p['n']), '<i2').astype(float).reshape(-1, p['ch']) / 32768
    return p, x


def music_seam(x, nbars):
    """A music loop restarts on a downbeat, so the loop point must behave like any other bar line:
    no waveform discontinuity (click scan across the joined seam), a wrap step within the normal sample-step
    range, and spectral flux / level change no larger than at the bar lines inside the piece."""
    m = x.mean(1); n = len(m); win = 2048; seg = SR // 10
    def spec(a): return np.log10(np.abs(np.fft.rfft(a * np.hanning(len(a)))) + 1e-9)
    def metrics(i):
        ext = np.concatenate([m[-win:], m, m[:win]]); j = i + win
        flux = float(np.mean(np.abs(spec(ext[j:j + win]) - spec(ext[j - win:j]))))
        e2 = np.concatenate([m[-seg:], m, m[:seg]]); k = i + seg
        lvl = abs(20 * np.log10((np.sqrt(np.mean(e2[k:k + seg] ** 2)) + 1e-9) / (np.sqrt(np.mean(e2[k - seg:k] ** 2)) + 1e-9)))
        return flux, lvl
    bar = n / nbars
    inner = [metrics(int(round(b * bar))) for b in range(1, nbars)]
    sf, sl = metrics(0)
    steps = np.abs(np.diff(m)); p999 = float(np.percentile(steps, 99.9)); wrap = float(abs(m[0] - m[-1]))
    clicks = click_scan(np.concatenate([m[-SR // 2:], m[:SR // 2]]))
    fmax = max(f for f, _ in inner); lmax = max(l for _, l in inner)
    ok = (not clicks) and wrap <= p999 and sf <= fmax * 1.1 and sl <= lmax + 1.0
    return dict(wrap_step=wrap, step_p999=p999, seam_flux=sf, barline_flux_max=fmax, seam_level_jump_db=sl,
                barline_level_jump_max_db=lmax, seam_clicks=clicks, ok=bool(ok),
                seam_flux_percentile=float(np.mean([f < sf for f, _ in inner]) * 100))


def key_of(s):
    pc = s.key_pc
    minor = s.scale in (songs.MINOR, songs.HMINOR)
    if s.scale == songs.ISTRIAN:
        return f'{NOTE_NAMES[pc]} Istrian six-tone scale'
    return f'{NOTE_NAMES[pc]} {"minor" if minor else "major"}'


def qa(root, info):
    res = {}; feats = {}
    for name in songs.SONGS:
        s = songs.SONGS[name]()
        for kind in ('base', 'layer'):
            fn = name + ('_layer' if kind == 'layer' else '') + '.wav'
            p = os.path.join(root, 'music', fn)
            if kind == 'layer' and not info[name]['has_layer']: continue
            r = dict(file='music/' + fn, problems=[])
            if not os.path.isfile(p):
                r['problems'].append('missing'); res[fn] = r; continue
            P, x = read(p)
            m = x.mean(1); dur = len(x) / SR
            pk = float(np.max(np.abs(x)))
            r.update(sr=P['sr'], bits=P['sw'] * 8, channels=P['ch'], frames=len(x), duration=round(dur, 3),
                     expected_frames=s.nsamples, peak_dbfs=round(20 * np.log10(pk + 1e-12), 2),
                     true_peak_dbtp=round(20 * np.log10(true_peak(x) + 1e-12), 2),
                     loudness=round(loudness(x, loop=True), 2), clipped=int(np.sum(np.abs(x) >= 32767 / 32768)),
                     dc=float(np.abs(x.mean(0)).max()), bytes=os.path.getsize(p))
            hr, cen = hf_ratio(m); r['hf_ratio_5k'] = round(hr, 4); r['centroid_hz'] = round(cen)
            r['seam'] = music_seam(x, s.nbars)
            r['clicks'] = click_scan(m)
            lo, hi = DUR.get(name, (60, 90))
            if P['sr'] != SR or P['sw'] != 2 or P['comp'] != 'NONE': r['problems'].append('format')
            if P['ch'] != 2: r['problems'].append('not stereo')
            if len(x) != s.nsamples: r['problems'].append('length is not the exact bar grid')
            if not (lo <= dur <= hi): r['problems'].append(f'duration {dur:.1f}s outside {lo}-{hi}s')
            if r['peak_dbfs'] > -3.0 or r['clipped']: r['problems'].append('peak above -3 dBFS')
            if 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12) < -50: r['problems'].append('silent')
            if r['dc'] > 0.002: r['problems'].append('DC')
            if not r['seam']['ok']: r['problems'].append('loop seam')
            if r['clicks']: r['problems'].append(f'clicks {r["clicks"][:5]}')
            if hr > 0.12: r['problems'].append(f'too bright ({hr:.1%} > 5 kHz)')
            if kind == 'base': feats[name] = features(m)
            res[fn] = r
        if info[name]['has_layer']:
            _, xb = read(os.path.join(root, 'music', name + '.wav'))
            _, xl = read(os.path.join(root, 'music', name + '_layer.wav'))
            sm = xb + xl
            c = dict(frames_equal=len(xb) == len(xl), sum_peak_dbfs=round(20 * np.log10(np.max(np.abs(sm)) + 1e-12), 2),
                     sum_true_peak_dbtp=round(20 * np.log10(true_peak(sm) + 1e-12), 2),
                     layer_rel_db=round(loudness(xl, True) - loudness(xb, True), 1), sum_seam=music_seam(sm, s.nbars)['ok'],
                     sum_loudness=round(loudness(sm, True), 2))
            res[name + '.wav']['with_layer'] = c
            if not c['frames_equal']: res[name + '.wav']['problems'].append('layer length differs')
            if c['sum_peak_dbfs'] > -3.0: res[name + '.wav']['problems'].append('base+layer above -3 dBFS')
            if not c['sum_seam']: res[name + '.wav']['problems'].append('base+layer seam')
    # distinctness of the tracks
    for a in feats:
        best, bn = 9, None
        for b in feats:
            if a == b: continue
            d = float(np.sqrt(np.mean((feats[a][0] - feats[b][0]) ** 2)))
            if d < best: best, bn = d, b
        res[a + '.wav']['nearest'] = bn; res[a + '.wav']['nearest_dist'] = round(best, 3)
    return res


def manifest(q, info, oggs):
    out = []
    for name, t in TRACKS.items():
        s = songs.SONGS[name]()
        for kind in ('base', 'layer'):
            if kind == 'layer' and not info[name]['has_layer']: continue
            fn = name + ('_layer' if kind == 'layer' else '') + '.wav'
            r = q[fn]
            e = dict(id=fn[:-4], filename=r['file'], ogg_filename=oggs[r['file']]['ogg'] if oggs else None,
                     role='intensity layer (play in sync with the base track)' if kind == 'layer' else 'base track',
                     layer_of=name if kind == 'layer' else None, layer_id=(name + '_layer') if kind == 'base' and info[name]['has_layer'] else None,
                     city=t['city'], use=t['use'], style=t['style'], suggested_game_trigger=t['trigger'],
                     loop=True, loop_start_sample=0, loop_end_sample=r['frames'], duration_seconds=r['duration'],
                     bpm=s.bpm, meter=f'{s.bpb}/4', bars=s.nbars, key=key_of(s), channels=2,
                     volume_recommendation=0.75 if kind == 'base' else 0.75, loudness_lufs=r['loudness'],
                     peak_dbfs=r['peak_dbfs'], fade_in_s=2.0 if name.startswith('mus_city') else 1.0, fade_out_s=1.5)
            out.append(e)
    return dict(pack='Galeb nad Jadranom - background music', version='1.0.0', generated=datetime.date.today().isoformat(),
                format=dict(wav='44.1 kHz, 16-bit PCM, stereo', ogg='Ogg Vorbis q5 copies in ogg/'),
                loudness='integrated K-weighted loudness (BS.1770 filter, ungated): cities/menu -20, fever -19, end screen -21; '
                         'true peak <= -3.2 dBTP also for base+layer played together',
                loops='every file loops sample-exactly from its first to its last sample; base and layer have identical length '
                      'and must be started at the same AudioContext time',
                count=len(out), tracks=out)


def guide(man, q, oggs):
    T = {e['id']: e for e in man['tracks']}
    rows = '\n'.join(f"| `{e['id']}` | {e['use'] if not e['layer_of'] else 'layer for ' + e['layer_of']} | {e['duration_seconds']:.1f} s | "
                     f"{e['bpm']} | {e['meter']} | {e['key']} | {e['bars']} |" for e in man['tracks'])
    ogg_total = sum(oggs[e['filename']]['bytes'] for e in man['tracks']) / 1e6 if oggs else 0
    wav_total = sum(q[os.path.basename(e['filename'])]['bytes'] for e in man['tracks']) / 1e6
    dec = {e['id']: e['duration_seconds'] * 2 * 4 * SR / 1e6 for e in man['tracks']}
    return f"""# Galeb nad Jadranom — Music Integration Guide

{man['count']} seamless stereo loops: a title/menu theme, one piece per city (each with a synchronous
**intensity layer**), a fever track and an end-screen track. They replace the game's real-time
synthesized music engine. This guide only describes the integration; the HTML has **not** been changed.

## 1. Tracks

| file | use | length | BPM | meter | key | bars |
|---|---|---|---|---|---|---|
{rows}

* Styles follow the game's existing per-city identities (`SCENES[].style`): klapa for Split, Dubrovnik,
  Makarska and Zadar, poskočica for Šibenik, Istrian two-part music for Pula.
* All instruments are rendered from physical / vocal models (plucked double-course mandolin, guitar,
  double bass, a wordless 4-part male klapa, Istrian sopile, tapan, frame drum, shaker) — no samples,
  no oscillator "beeps", no lyrics.
* Format: 44.1 kHz / 16-bit stereo WAV ({wav_total:.1f} MB) and Ogg Vorbis copies in `ogg/` ({ogg_total:.1f} MB).
  Because of its size the pack is delivered as several ZIP parts (`…_part1ofN.zip` …): unpack **all** parts into the
  same folder; part 1 contains the documents, the manifest and all OGG files.
* Every file is an exact number of bars and loops sample-exactly (reverb tails are already wrapped into the
  beginning). Base and layer of a city have the same length and are meant to run in lock-step.
* Loudness: cities and menu −20, fever −19, end screen −21 (integrated, K-weighted); base + layer together
  stay below −3 dBFS. This leaves room for the SFX pack, which is mastered for the SFX bus.

## 2. Removing the synthesized music engine ("alles Synthetische muss weg")

Everything below generates sound with oscillators or noise buffers at run time. Delete it once the file-based
player (section 3) and the SFX bank from `AUDIO_INTEGRATION_GUIDE.md` (SFX pack) are in place:

**Music engine**
* globals `musicNode`, `musicNext`, `musicStep`, `musicDrone` (keep `musicOn`)
* `MODES`, `SCALE`, `scaleOf()`, `PHRASE`, `PHRASES`, `KLAPA_KADENCA`, `RITAM`, `korak()` — after checking
  that `scaleOf()` is no longer used by `gradSignal()` / `zvukKraja()` (those are replaced by the SFX pack)
* instruments `pluck()`, `pluckBuffer()`, `pluckCache`, `frula()`, `harmonika()`, `tambura()`, `mandolina()`,
  `glas()`, `sopile()`, `INSTR`, `tupan()`, `bas()`, `def()`
* `musicStart()`, `musicTick()` and its call in the main loop (`update(dt); render(); musicTick();`)
* the drone handling inside `setRoom()` (`musicNode.drone`, `musicNode.kvinta`, `musicDrone`)
* the music fade inside `zvukKraja()` and the gain ramps on `musicNode.g` in `start()` / `reset()`
  (≈ line 2851/2856) and in the radio ducking (≈ line 4810–4815) — re-point them to `MUSIC.out` (below)

**Other run-time synthesis (covered by the SFX pack)**
* `beep()`, `tone()`, `noiseBurst()`, `chime()`, `gull()`, `gradSignal()`, the oscillator/noise part of
  `zvukKraja()`, `ONESHOT` and the body of `oneShotTick()`
* in `audioInit()`: the shared noise buffer and the three generated ambience layers (`ambWater`, `ambBuzz`
  with its two LFO oscillators, `ambHum`) and, if nothing else uses it, the convolver from `makeIR()`
* the radio voice "beeps" around line 4793–4802 if they are oscillator tones

**Check:** afterwards a search for `createOscillator`, `createBuffer(` with random fills, and `makeIR` should find
nothing; the only sources left are `AudioBufferSourceNode`s playing decoded files.

## 3. A file-based music player

Uses the existing `ac`, `busMusic`, `musicOn`. Decoding works exactly like the SFX bank (data URIs embedded in the
one-file HTML, or fetched).

```js
/* ══════════ Music player (files) ══════════ */
const MUSIC = (() => {{
  const bufs = {{}};                       // id -> AudioBuffer (decoded lazily)
  let out = null, cur = null;              // cur = {{id, base, layer, g, lg}}
  const decode = ab => new Promise((ok, err) => ac.decodeAudioData(ab, ok, err));
  async function load(id){{
    if(bufs[id]) return bufs[id];
    const ab = await (await fetch(window.GALEB_MUSIC_DATA[id])).arrayBuffer();
    return (bufs[id] = await decode(ab));
  }}
  function ensureOut(){{ if(!out){{ out = ac.createGain(); out.gain.value = musicOn ? 1 : 0; out.connect(busMusic); }} return out; }}
  function startVoice(buf, gain, when){{
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
    const g = ac.createGain(); g.gain.value = gain;
    src.connect(g); g.connect(ensureOut()); src.start(when);
    return {{ src, g }};
  }}
  async function play(id, fade = 2.0){{
    if(!ac || (cur && cur.id === id)) return;
    const meta = window.GALEB_MUSIC_META.find(m => m.id === id);
    const [b, l] = await Promise.all([load(id), meta.layer_id ? load(meta.layer_id) : null]);
    const t = ac.currentTime + 0.05;                     // same start time -> base and layer in lock-step
    const old = cur;
    const v = startVoice(b, 0, t);
    v.g.gain.setValueAtTime(0, t); v.g.gain.linearRampToValueAtTime(meta.volume_recommendation, t + fade);
    let lv = null;
    if(l){{ lv = startVoice(l, 0, t); }}
    cur = {{ id, base: v, layer: lv, t0: t }};
    setLayer(typeof nizLayer === 'function' && state === 'playing' ? nizLayer() : 0, 0.5);
    if(old) stopVoice(old, fade);
  }}
  function stopVoice(v, fade){{
    const t = ac.currentTime;
    for(const x of [v.base, v.layer]) if(x){{
      x.g.gain.cancelScheduledValues(t); x.g.gain.setValueAtTime(x.g.gain.value, t);
      x.g.gain.linearRampToValueAtTime(0, t + fade); x.src.stop(t + fade + 0.05);
    }}
  }}
  function stop(fade = 1.5){{ if(cur){{ stopVoice(cur, fade); cur = null; }} }}
  /* intensity: 0 none, 1 = niz>=3, 2 = niz>=5, 3 = niz>=10 or fever  (see nizLayer()) */
  function setLayer(level, tc = 0.35){{
    if(!cur || !cur.layer) return;
    const target = [0, 0.45, 0.7, 0.9][Math.max(0, Math.min(3, level))];
    cur.layer.g.gain.setTargetAtTime(target, ac.currentTime, tc);
  }}
  function setOn(on){{ ensureOut().gain.setTargetAtTime(on ? 1 : 0, ac.currentTime, 0.2); }}
  function duck(db = -8, hold = 1.5){{
    const g = ensureOut().gain, t = ac.currentTime, v = musicOn ? 1 : 0;
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(v * Math.pow(10, db / 20), t + 0.25);
    g.setValueAtTime(v * Math.pow(10, db / 20), t + hold); g.linearRampToValueAtTime(v, t + hold + 1.0);
  }}
  function release(id){{ if(!cur || cur.id !== id) delete bufs[id]; }}   // free memory of cities left behind
  return {{ load, play, stop, setLayer, setOn, duck, release, get current(){{ return cur && cur.id; }}, get out(){{ return ensureOut(); }} }};
}})();
const CITY_TRACK = {{ 'Split':'mus_city_split', 'Dubrovnik':'mus_city_dubrovnik', 'Šibenik':'mus_city_sibenik',
                     'Makarska':'mus_city_makarska', 'Zadar':'mus_city_zadar', 'Pula':'mus_city_pula' }};
const cityTrack = () => CITY_TRACK[SCENE().name] || 'mus_city_split';
```

### Hooks (replace the old calls one-to-one)

| game moment | old | new |
|---|---|---|
| first gesture / intro (`pokreniUvod()`, tap during `uvod`) | `audioInit(); musicStart();` | `audioInit(); MUSIC.play('mus_menu', 1.0);` |
| flight starts (`start()`) | ramp `musicNode.g` | `MUSIC.play(cityTrack(), 1.5);` |
| new city (`updateScene()` arrival, where `setRoom(); gradSignal();` run) | drone retune | `MUSIC.play(cityTrack(), 2.5); MUSIC.release(previousTrack);` |
| combo layers (`layerChange(up)`, called from `judgeClean()`, `breakNiz()`, fever) | `musicNode.extra.gain…` + beep | `MUSIC.setLayer(nizLayer(), up ? 0.25 : 0.6);` |
| `feverStart()` | — | `MUSIC.play('mus_fever', 0.4);` |
| `feverKraj()` | — | `MUSIC.play(cityTrack(), 1.2);` (restarts the city loop from its top — musically clean, because every loop starts on its tonic) |
| crash (`zvukKraja()` in `die()`) | music fades in 0.7 s | `MUSIC.stop(0.7);` then after the game-over sting `setTimeout(() => state === 'dead' && MUSIC.play('mus_end_screen', 2.0), 2600);` |
| back to menu / `reset()` | ramps on `musicNode.g` | `MUSIC.play('mus_menu', 1.5);` (or keep `mus_end_screen` until the next flight) |
| music button (`musicSet(on)`) | `musicNode.g` ramp | `MUSIC.setOn(on);` — keep `Store.set('music', …)` |
| radio speaks (≈ line 4810) | duck `musicNode.g` to 0.28 for 4.4 s | `MUSIC.duck(-11, 4.4);` |
| progression stingers / journey complete | — | `MUSIC.duck(-6, 1.5);` |

`musicTick()` disappears from the main loop: file playback needs no per-frame work.

## 4. Loading and memory (mobile Safari)

* Decoded audio is large: one minute of stereo music ≈ 21 MB of Float32. Keep **only the current city
  (base + layer), the fever track and the menu/end track** decoded; call `MUSIC.release()` for cities left
  behind, and pre-load the next city's track during the 7.6 s arrival glide (`glide`).
* Decoded sizes: {', '.join(f'{k} {v:.0f} MB' for k, v in dec.items())}.
* Embed the OGG copies (≈ {ogg_total:.1f} MB, +33 % as base64) in a `window.GALEB_MUSIC_DATA` object like the images,
  or ship them next to the HTML and fetch them. Older Safari / iOS versions cannot decode Ogg Vorbis: feature-detect
  (`canPlayType('audio/ogg; codecs="vorbis"')`) and fall back to the WAVs, or convert to AAC for those devices —
  AAC adds encoder padding, so for gapless loops prefer WAV there.
* `window.GALEB_MUSIC_META` = `music_manifest.json → tracks`.

## 5. Mixing with the SFX pack

* `busMusic` 0.9 (as today), `busSfx` ≈ 0.8, `busAmb` ≈ 0.6 is a good starting point; the manifest's
  `volume_recommendation` (0.75) is applied per track by the player above.
* Each city layer (mandolin arpeggios, light percussion) is mastered 6 dB below its base track. At full layer
  gain the mix is only about 1 dB louder than the base alone (see the QA report) — the change is in texture
  and drive, not in volume, so combos feel richer without pushing the music over the effects.
"""


def qa_report(q, oggs, info):
    L = ['# Galeb nad Jadranom — Music QA Report\n', f'Generated {datetime.date.today().isoformat()} by `tools/galeb_music/build_music.py`.\n']
    ok = [k for k, v in q.items() if not v['problems']]
    L.append('## Summary\n')
    L.append(f'* Files: **{len(q)}** (9 base tracks + 6 city intensity layers), passing all checks: **{len(ok)}**.')
    if oggs:
        L.append(f'* OGG copies: {len(oggs)}, sample-exact after decoding with libvorbis/libsndfile: '
                 f'{sum(v["length_match"] for v in oggs.values())}/{len(oggs)}; loops also sample-exact with ffmpeg\'s decoder: '
                 f'{sum(v["ffmpeg_tail_loss"] == 0 for v in oggs.values())}/{len(oggs)}.')
    L.append(f'* Highest sample peak {max(v["peak_dbfs"] for v in q.values()):.2f} dBFS, highest true peak '
             f'{max(v["true_peak_dbtp"] for v in q.values()):.2f} dBTP, clipped samples {sum(v["clipped"] for v in q.values())}.')
    L.append('* Every file is exactly its bar grid long (samples = bars × beats × 60 / BPM × 44,100, rounded once), so loops stay in time.')
    L.append('')
    L.append('**Limitation:** validated with measurements and spectrograms only; no human listening test was possible in this '
             'environment. Please listen on a phone and on headphones before release — especially the sung (klapa) parts, '
             'which are the hardest element to model convincingly without recordings.\n')
    L.append('## Checks\n')
    L.append("""| check | method |
|---|---|
| format | 44.1 kHz, 16-bit PCM, stereo |
| length | exact bar-grid sample count; cities/menu 60–90 s, fever 25–40 s, end screen 35–60 s; layer length = base length |
| level | integrated K-weighted loudness; sample and 4× oversampled true peak ≤ −3 dBFS, also for base + layer summed |
| loop seam | the loop restarts on a downbeat, so it must behave like any bar line of the piece: click/discontinuity scan across the joined seam, wrap-around sample step ≤ 99.9th percentile of all steps, spectral flux and 100 ms level change at the seam ≤ the largest values at the internal bar lines (for base, layer and base + layer) |
| clicks | waveform-discontinuity scan over the whole file |
| harshness | share of energy above 5 kHz ≤ 12 % |
| distinctness | 24-band spectral distance to the most similar other track |
""")
    L.append('## Results\n')
    L.append('| file | length | BPM / bars | loudness | peak / TP | >5 kHz | seam flux vs bar lines (pct) | with layer: Δ loudness, sum peak | nearest track | result |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    for fn in sorted(q):
        v = q[fn]; nm = fn.replace('_layer.wav', '').replace('.wav', '')
        wl = v.get('with_layer')
        wls = f"+{wl['sum_loudness'] - v['loudness']:.1f} dB, {wl['sum_peak_dbfs']:.1f} dBFS" if wl else ''
        near = f"{v['nearest']} ({v['nearest_dist']})" if v.get('nearest') else ''
        res = 'pass' if not v['problems'] else '; '.join(v['problems'])
        L.append(f"| `{v['file']}` | {v['duration']:.2f} s | {info[nm]['bpm']} / {info[nm]['bars']} | {v['loudness']:.1f} | "
                 f"{v['peak_dbfs']:.1f} / {v['true_peak_dbtp']:.1f} | {v['hf_ratio_5k'] * 100:.1f} % | "
                 f"{v['seam']['seam_flux_percentile']:.0f} % | {wls} | {near} | {res} |")
    return '\n'.join(L) + '\n'


def main(work, zip_out):
    t0 = time.time()
    root = os.path.join(work, PACK)
    if os.path.isdir(root): shutil.rmtree(root)
    os.makedirs(root)
    print('== render'); info = render.render_all(root)
    print('== QA'); q = qa(root, info)
    bad = {k: v['problems'] for k, v in q.items() if v['problems']}
    print(f'{len(q)} files, problems: {bad}')
    if bad: sys.exit(1)
    print('== OGG')
    oggs = ogg_encode(root, [v['file'] for v in q.values()])
    man = manifest(q, info, oggs)
    json.dump(man, open(os.path.join(root, 'music_manifest.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    open(os.path.join(root, 'MUSIC_INTEGRATION_GUIDE.md'), 'w', encoding='utf-8').write(guide(man, q, oggs))
    open(os.path.join(root, 'MUSIC_QA_REPORT.md'), 'w', encoding='utf-8').write(qa_report(q, oggs, info))
    # GitHub refuses files > 100 MB: split into self-contained parts that unpack into the same folder
    files = []
    for dp, dn, fn in os.walk(root):
        dn.sort(); files += [os.path.join(dp, f) for f in sorted(fn)]
    first = [p for p in files if not p.endswith('.wav')]
    wavs = sorted((p for p in files if p.endswith('.wav')), key=lambda p: os.path.basename(p))
    parts = [list(first)]; size = sum(os.path.getsize(p) for p in first)
    for p in wavs:
        if size + os.path.getsize(p) > 92e6:
            parts.append([]); size = 0
        parts[-1].append(p); size += os.path.getsize(p)
    stem = zip_out[:-4]
    for old in [f for f in os.listdir(os.path.dirname(os.path.abspath(zip_out))) if f.startswith(os.path.basename(stem))]:
        os.remove(os.path.join(os.path.dirname(os.path.abspath(zip_out)), old))
    allnames = []
    for i, part in enumerate(parts, 1):
        zp = f'{stem}_part{i}of{len(parts)}.zip'
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in part: z.write(p, os.path.relpath(p, work))
        with zipfile.ZipFile(zp) as z:
            assert z.testzip() is None; allnames += z.namelist()
        print(f'{zp}: {os.path.getsize(zp) / 1e6:.1f} MB, {len(part)} files')
    expect = [os.path.relpath(p, work) for p in files]
    missing = sorted(set(expect) - set(allnames))
    print(f'{len(parts)} parts, {len(allnames)} entries, {sum(n.endswith(".wav") for n in allnames)} wav, '
          f'{sum(n.endswith(".ogg") for n in allnames)} ogg, missing={missing}; {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
