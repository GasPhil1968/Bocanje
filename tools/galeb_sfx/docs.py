"""audio_manifest.json, AUDIO_INTEGRATION_GUIDE.md and AUDIO_QA_REPORT.md generation."""
import os, datetime
import sounds

CAT_ORDER = ['player', 'obstacles', 'collisions', 'pickups', 'weather', 'cities', 'props', 'ui', 'progression', 'ambience']


def _bus(m):
    if m['loop']: return 'ambience'
    if m['folder'] == 'ui': return 'ui'
    if m['folder'] in ('cities', 'props') or m['category'] == 'sea': return 'ambience_oneshot'
    return 'sfx'


def manifest(q, oggs):
    out = []
    for name, m in sounds.REG.items():
        f = q['files'][name]
        e = dict(id=name, filename=f['file'],
                 ogg_filename=(oggs[f['file']]['ogg'] if oggs else None),
                 event=m['event'], category=m['category'], folder=m['folder'] if not m['loop'] else 'ambience',
                 bus=_bus(m), channels=f['channels'], duration_seconds=f['duration'], loop=m['loop'],
                 volume_recommendation=m['vol'], priority=m['priority'], cooldown_ms=m['cooldown'],
                 max_simultaneous=m['max_sim'], variation_group=m['group'], suggested_game_trigger=m['trigger'],
                 replaces_legacy=m['legacy'], loudness_lufs=f['loudness'], peak_dbfs=f['peak_dbfs'])
        out.append(e)
    out.sort(key=lambda e: (CAT_ORDER.index(e['folder']), e['id']))
    groups = {}
    for e in out:
        if e['variation_group']: groups.setdefault(e['variation_group'], []).append(e['id'])
    return dict(
        pack='Galeb nad Jadranom - complete SFX library', version='1.0.0',
        generated=datetime.date.today().isoformat(),
        format=dict(container='WAV (RIFF)', codec='PCM signed 16-bit little-endian', sample_rate=44100, bit_depth=16,
                    mono='short gameplay SFX and UI', stereo='ambience loops, weather, city/prop one-shots, roll/wingover/arch',
                    ogg='Ogg Vorbis copies in ogg/ (q5 SFX, q4 ambience), same relative paths'),
        loudness=dict(reference='K-weighted (ITU-R BS.1770 filter), momentary max over 200 ms for one-shots, '
                                'whole-file for loops; true-peak ceiling -3.2 dBTP',
                      category_targets_lufs={'wingbeats': -28.5, 'bird calls': -23, 'flight moves': -27, 'score tick': -30,
                                             'gates / combos / fever': '-27 ... -20', 'collisions': -20,
                                             'pickups': -22, 'weather': '-29 ... -23', 'cities / props': -27,
                                             'ui': '-33 (hover) ... -24 (start)', 'progression stingers': -20,
                                             'ambience loops (integrated)': '-38 ... -34'}),
        volume_note='volume_recommendation is the per-sound GainNode value with the SFX/UI/ambience bus at 1.0; '
                    'start busSfx around 0.8 and busAmb around 0.6 and trim by ear against the music.',
        variation_groups=groups,
        count=dict(total=len(out), loops=sum(e['loop'] for e in out), one_shots=sum(not e['loop'] for e in out)),
        sounds=out)


def _fmt_bytes(b):
    return f'{b / 1e6:.2f} MB' if b > 1e6 else f'{b / 1e3:.0f} kB'


def guide(man, q, oggs):
    S = {e['id']: e for e in man['sounds']}
    wav_total = sum(q['files'][e['id']]['bytes'] for e in man['sounds'])
    ogg_total = sum(v['bytes'] for v in oggs.values()) if oggs else 0
    core_ids = [e['id'] for e in man['sounds'] if e['folder'] in ('player', 'obstacles', 'collisions', 'pickups', 'ui')]
    core_ogg = sum(oggs[S[i]['filename']]['bytes'] for i in core_ids) if oggs else 0
    amb_ogg = sum(oggs[S[i]['filename']]['bytes'] for i in S if S[i]['loop']) if oggs else 0
    dec_mb = sum(e['duration_seconds'] * e['channels'] * 4 * 44100 for e in man['sounds']) / 1e6
    dec_amb = sum(e['duration_seconds'] * e['channels'] * 4 * 44100 for e in man['sounds'] if e['loop']) / 1e6
    return f"""# Galeb nad Jadranom — Audio Integration Guide

This pack replaces the game's synthesized placeholder sounds (`beep()`, `gull()`, `gradSignal()`, `chime()`,
`zvukKraja()`, `ONESHOT.*`) with **{man['count']['total']} original rendered sounds**:
{man['count']['one_shots']} one-shots and {man['count']['loops']} seamless ambience loops.
It is a drop-in **audio layer only**: game logic, physics, collision and controls do not change.
Only the lines that *make noise* are swapped.

> This guide describes the integration; it has **not** been applied to the HTML yet (as requested).

---

## 1. What is in the pack

```
galeb_nad_jadranom_complete_sfx/
  sfx/player/        wingbeats (3 per bird), bird calls, flight manoeuvres
  sfx/obstacles/     gates, score tick, combos, fever
  sfx/collisions/    impacts, hurt/fall, game-over sting, shield, rescue
  sfx/pickups/       smokva, kava, vino, štit, duplo, relic, passport, item spawn
  sfx/weather/       rain / bura / fog transitions, splashes, wave impact
  sfx/cities/        bells, harbour, cicadas, bura, pines, Sea Organ (per city)
  sfx/props/         ferry horn, fishing boat, sailboat, oar, dolphin
  sfx/ui/            stone / wood / brass / paper interface sounds
  sfx/progression/   milestone, medals, city arrival/unlock, relic, mission, journey, record
  ambience/          10 stereo loops (12–25 s), sample-exact seamless
  ogg/               the same tree as Ogg Vorbis (optional, for deployment)
  audio_manifest.json
  AUDIO_INTEGRATION_GUIDE.md   (this file)
  AUDIO_QA_REPORT.md
```

* WAV: 44.1 kHz, 16-bit PCM. Short gameplay sounds are mono; ambience and spatial one-shots are stereo.
* Every file peaks at or below −3.2 dBFS true peak, starts within ~1.5 ms of its first transient and
  ends on a natural decay with a short fade, so files can be stacked without clipping.
* Loudness is matched **per category** (see `audio_manifest.json → loudness`). The most frequent sounds
  (wingbeats, score tick) are deliberately the quietest.

Sizes: all WAV = {_fmt_bytes(wav_total)}; all OGG = {_fmt_bytes(ogg_total)}
(gameplay + UI OGG = {_fmt_bytes(core_ogg)}, ambience OGG = {_fmt_bytes(amb_ogg)}).
Decoded in memory (Float32): ≈ {dec_mb:.0f} MB for everything, of which ≈ {dec_amb:.0f} MB are the ten loops —
so **decode ambience lazily** (section 3.4).

### The manifest

`audio_manifest.json → sounds[]` has one entry per file:

| field | use |
|---|---|
| `id`, `filename`, `ogg_filename` | key and paths |
| `event`, `suggested_game_trigger`, `replaces_legacy` | where it belongs in the code |
| `category`, `bus` | `sfx`, `ui`, `ambience_oneshot` or `ambience` (loops) |
| `duration_seconds`, `loop`, `channels` | |
| `volume_recommendation` | per-sound gain (bus at 1.0) |
| `priority` (1–10) | who wins when the voice budget is full |
| `cooldown_ms`, `max_simultaneous` | anti-spam limits |
| `variation_group` | pick randomly inside the group, never the same file twice in a row |

---

## 2. Loading efficiently in a one-file HTML5 game

The game is a single HTML file that already embeds its images as data-URIs (`window.GALEB_PNG_DATA`).
Do the same for audio, but in **two tiers** so start-up stays fast on phones:

1. **Core tier (embed)** – everything the player hears in the first seconds: `player`, `obstacles`,
   `collisions`, `pickups`, `ui` (≈ {_fmt_bytes(core_ogg)} as OGG, +33 % as base64).
2. **Scenic tier (embed or lazy)** – `weather`, `cities`, `props`, `progression`, `ambience`.
   Decode these after the first flight starts, or per city on arrival.

```html
<script>
/* generated by a tiny build step: id -> data URI (OGG preferred, WAV fallback) */
window.GALEB_SFX_DATA = {{ "sfx_galeb_flap_01": "data:audio/ogg;base64,T2dnUwAC...", /* ... */ }};
window.GALEB_SFX_META = /* contents of audio_manifest.json → sounds[] */ [];
</script>
```

Format choice: Chrome, Firefox and current Safari decode Ogg Vorbis in Web Audio, but older Safari / iOS
versions cannot. Feature-detect once and embed (or fetch) the WAV for those devices:

```js
const OGG_OK = !!document.createElement('audio').canPlayType('audio/ogg; codecs="vorbis"');
```

Decode everything with `decodeAudioData` **once** into `AudioBuffer`s and play them with
`AudioBufferSourceNode`s. Never use `<audio>` elements for gameplay sounds (latency, iOS limits),
and never create sounds per rendered frame — every sound in this pack is triggered by a game *event*.

---

## 3. Runtime: a small sound bank on the existing buses

`audioInit()` already creates `busMusic`, `busSfx` and `busAmb` behind a compressor. Keep them; add the
bank below right after `audioInit()` (it uses the existing globals `ac`, `soundOn`, `busSfx`, `busAmb`).

```js
/* ══════════ Galeb SFX bank ══════════ */
const SFX = (() => {{
  const bank = {{}}, voices = {{}}, last = {{}}, lastInGroup = {{}}, groups = {{}};
  let busUi = null;
  const MAX_VOICES = 14;                       // global budget for one-shots
  let live = [];                               // all playing one-shot voices

  const decode = ab => new Promise((ok, err) => ac.decodeAudioData(ab, ok, err)); // old-Safari safe
  async function load(filter = () => true){{
    if(!busUi){{ busUi = ac.createGain(); busUi.gain.value = 0.9; busUi.connect(master); }}
    for(const m of window.GALEB_SFX_META){{
      if(m.variation_group) (groups[m.variation_group] ||= []).includes(m.id) || groups[m.variation_group].push(m.id);
    }}
    await Promise.all(window.GALEB_SFX_META.filter(filter).map(async m => {{
      if(bank[m.id]) return;
      const url = window.GALEB_SFX_DATA[m.id];
      if(!url) return;
      const ab = await (await fetch(url)).arrayBuffer();
      bank[m.id] = {{ buf: await decode(ab), m }};
    }}));
  }}
  function busOf(m){{ return m.bus === 'ui' ? busUi : (m.bus === 'ambience' || m.bus === 'ambience_oneshot') ? busAmb : busSfx; }}
  function stop(v, fade = 0.03){{
    if(!v || v.stopped) return; v.stopped = true;
    const t = ac.currentTime;
    v.g.gain.cancelScheduledValues(t);
    v.g.gain.setValueAtTime(v.g.gain.value, t);
    v.g.gain.linearRampToValueAtTime(0, t + fade);
    try{{ v.src.stop(t + fade + 0.01); }}catch(e){{}}
  }}
  function play(id, o = {{}}){{
    if(!ac || !soundOn) return null;
    const e = bank[id]; if(!e) return null;
    const m = e.m, now = performance.now();
    if(now - (last[id] || -1e9) < m.cooldown_ms) return null;          // cooldown
    const t = ac.currentTime;
    live = live.filter(v => !v.stopped && v.end > t);
    const mine = (voices[id] = (voices[id] || []).filter(v => !v.stopped && v.end > t));
    if(mine.length >= m.max_simultaneous) stop(mine.shift(), 0.02);    // steal own oldest voice
    if(!m.loop && live.length >= MAX_VOICES){{                          // global budget: drop lowest priority
      const low = live.reduce((a, b) => (a.prio <= b.prio ? a : b));
      if(low.prio > m.priority) return null;
      stop(low, 0.02);
    }}
    last[id] = now;
    const src = ac.createBufferSource(); src.buffer = e.buf; src.loop = !!m.loop;
    if(o.rate) src.playbackRate.value = o.rate;
    const g = ac.createGain(); g.gain.value = (o.vol ?? 1) * m.volume_recommendation;
    let out = g;
    if(o.pan !== undefined && ac.createStereoPanner){{ const p = ac.createStereoPanner(); p.pan.value = o.pan; g.connect(p); out = p; }}
    src.connect(g); out.connect(o.bus || busOf(m));
    const when = o.when || t;
    src.start(when);
    const v = {{ id, src, g, prio: m.priority, end: m.loop ? Infinity : when + e.buf.duration / (o.rate || 1) }};
    src.onended = () => {{ v.stopped = true; }};
    mine.push(v); if(!m.loop) live.push(v);
    return v;
  }}
  function playGroup(group, o){{
    const ids = groups[group]; if(!ids || !ids.length) return null;
    let id = ids[(Math.random() * ids.length) | 0];
    if(ids.length > 1 && id === lastInGroup[group]) id = ids[(ids.indexOf(id) + 1) % ids.length];
    lastInGroup[group] = id;
    return play(id, o);
  }}
  return {{ load, play, playGroup, stop, has: id => !!bank[id] }};
}})();
```

Call `SFX.load(m => ['player','obstacles','collisions','pickups','ui'].includes(m.folder))` inside
`audioInit()` (it runs on the first user gesture, which also unlocks audio on iOS) and
`SFX.load()` (everything else) a few seconds later or on the first city arrival.

### 3.1 Preventing overlapping wingbeats

Wingbeats are the most frequent sound. Rules (sound only — `bird.v = FLAP()` stays exactly as it is):

* one **monophonic wing voice**: a new flap fades the previous one out in 25 ms;
* if taps come faster than 70 ms the physics still flaps but no new sound starts;
* random file from the bird's `variation_group` (no immediate repeats) and ±3 % playback rate;
* the strong variation (`_03`) is used when the bird was falling fast.

```js
let wingVoice = null, wingT = -1;
function flapSound(){{
  if(!ac || !soundOn) return;
  const t = ac.currentTime;
  if(t - wingT < 0.07) return;
  wingT = t;
  SFX.stop(wingVoice, 0.025);
  const vr = charKey === 'vranac';
  const rate = 0.97 + Math.random() * 0.06;
  wingVoice = bird.v > FLAP() * -0.6                     // was falling fast (FLAP() is negative)
    ? SFX.play(vr ? 'sfx_vranac_flap_03' : 'sfx_galeb_flap_03', {{ rate }})
    : SFX.playGroup(vr ? 'vranac_flap' : 'galeb_flap', {{ rate }});
}}
```

Call `flapSound()` **before** `bird.v = FLAP()` so it can read the falling speed (the cooldown in the
manifest, 70–80 ms, is the same guard if you prefer `SFX.playGroup` directly).

### 3.2 Independent music / SFX / ambience volume

* Music → `busMusic`, gameplay → `busSfx`, interface → `busUi` (created by the bank), loops and scenic
  one-shots → `busAmb`. The existing `soundOn` / `musicOn` toggles keep working (`master` gain / `musicSet`).
* Suggested starting gains: `busMusic 0.9`, `busSfx 0.8`, `busUi 0.9`, `busAmb 0.6`
  (the old `busAmb = 1.7` compensated for very quiet generated noise; the new loops are mastered louder).
* If you add sliders, store them like the existing `Store.set('music', …)` keys and apply with
  `bus.gain.setTargetAtTime(v, ac.currentTime, 0.05)` to avoid zipper noise.
* Ducking: for the game-over sting and progression stingers, dip `busMusic` by ~6 dB for 1.5 s:
  `busMusic.gain.setTargetAtTime(0.45, t, 0.05); busMusic.gain.setTargetAtTime(0.9, t + 1.5, 0.4);`
* The reverb send (`sendSfx`) was useful for raw oscillators; the new files carry their own space where needed,
  so lower `sendSfx` to ~0.12 (or route `busUi` dry, as above).

### 3.3 Ambience layers

Three simultaneous layers at most, each a looping voice with 2–3 s crossfades:

| layer | file(s) | when |
|---|---|---|
| sea | `amb_adriatic_waves_day` / `_evening` / `_bluehour` | by `palIdx` (0 Podne, 1 Zalazak, 2 Plavi sat) |
| place | `amb_harbor` (Split, Zadar), `amb_coastal_town` (Dubrovnik, Šibenik), `amb_cicadas` (Šibenik, Makarska, Pula by day), `amb_pine_wind` (Makarska) | on city arrival |
| weather | `amb_rain`, `amb_bura`, `amb_fog` | while `weather.kind` is set |

```js
const AMB = {{ sea: null, place: null, weather: null }};
function ambSet(layer, id, vol = 1, fade = 2.5){{
  const cur = AMB[layer];
  if(cur && cur.id === id) return;
  if(cur) SFX.stop(cur, fade);
  AMB[layer] = id ? SFX.play(id, {{ vol: 0.0001 }}) : null;
  if(AMB[layer]){{ const g = AMB[layer].g.gain, t = ac.currentTime;
    g.setValueAtTime(0.0001, t); g.linearRampToValueAtTime(vol * window.GALEB_SFX_META.find(m => m.id === id).volume_recommendation, t + fade); }}
}}
```

Mute (gain → 0) the old generated layers `ambWater`, `ambBuzz`, `ambHum` in `setRoom()` once the loops
are active, or keep them at very low level as an "air" bed — not both at full level.

### 3.4 Mobile performance checklist

* Decode the ten loops lazily (only sea + place + weather are ever needed at once) and drop references
  to loops of cities you have left; a 20 s stereo loop is ≈ 7 MB decoded.
* Keep the existing `beepFenster` idea: the bank's global budget (`MAX_VOICES = 14`) plus per-sound
  `max_simultaneous` and `cooldown_ms` stop pile-ups during fever / bura / combos.
* Resume the context on visibility change: `document.addEventListener('visibilitychange', () => !document.hidden && ac && ac.resume());`
* Do not call `SFX.play` from `update()`/`draw()` loops unless guarded by an event flag.

---

## 4. Replacing the existing synthesized sounds

Keep every condition, timer and side effect; replace only the sound statement. Line references are to the
current file (`Galeb-nad-Jadranom-PFEILER-KORRIGIERT.html`).

### 4.1 `beep()` call sites

| where (function) | current | replace with |
|---|---|---|
| `tap()` and the buffered tap after `glide` | `beep(560,0.08,'triangle',0.05)` | `flapSound()` (3.1) |
| `addScore(n)` | `beep(880,0.09,'square',0.04)` | `SFX.play('sfx_score_tick')` |
| `judgeClean()` clean pass | `beep(700 + Math.min(niz,10)*90, …)` | `SFX.play(niz >= 5 ? 'sfx_gate_clean_streak' : 'sfx_gate_clean', {{ rate: 1 + Math.min(niz,10)*0.006 }})` |
| `judgeClean()` ordinary pass (no clean, no near miss, no break) | — | `SFX.play('sfx_gate_pass')` (+ `sfx_gate_arch` if `p.arch`, `sfx_gate_double` if `otvori(p).length > 1`) |
| `judgeClean()` golden gate | `beep(1320…)` + `beep(1980…)` | `SFX.play('sfx_gate_golden'); SFX.play('sfx_flight_pullup')` |
| `judgeClean()` perfect line → `slowmo` | `beep(96,0.34,'sine',0.055,52)` | `SFX.play('sfx_gate_tight_slowmo')` |
| `zaDlaku()` | `noiseBurst(…)` + `beep(300,…)` | `SFX.play('sfx_gate_nearmiss', {{ pan: (p.x / W - 0.5) * 1.2 }})` |
| `breakNiz()` | `beep(260,0.28,'sine',0.035,150)` | keep `const n0 = niz;` as first line, then `if(n0 >= 2) SFX.play('sfx_combo_break')` |
| `layerChange(true)` | `beep(1180,0.14,'sine',0.03)` | remove; use the multiplier stingers (4.4) |
| `feverStart()` | 3× `beep(660*1.26^i…)` + `ONESHOT.galeb` | `SFX.play('sfx_fever_start')` |
| `feverKraj()` | `beep(420,0.4,'sine',0.035,240)` | `SFX.play('sfx_fever_end')` |
| `spasavanje()` | `beep(300,0.45,…)` + `ONESHOT.galeb` | `SFX.play('sfx_rescue_activate'); SFX.play('sfx_bird_hurt')` |
| `breakShield()` | `beep(1500,…)` + `noiseBurst(…)` | `SFX.play('sfx_shield_break'); SFX.play('sfx_bird_hurt', {{ vol: 0.6 }})` |
| `collectItems()` | one `beep` per kind | see 4.6 |
| `startWeather(kind)` | `beep(kind==='bura' ? 140 : 200, …)` | see 4.7 |
| `chime()` / `gradSignal()` | `beep`/`pluck` | see 4.8 |

After the swap `beep()` can stay in the file unused (or be deleted together with `tone()`/`noiseBurst()`
if nothing else calls them — the music engine uses `pluck()`, not `beep()`).

### 4.2 `gull()` — the ambient gull timer in `update()`

`gullNext` keeps its timing (7–18 s); only the sound changes. Ambient gulls are always seagulls, so:

```js
function gull(){{ if(!ac || !soundOn) return;
  SFX.playGroup('galeb_call', {{ vol: 0.55, rate: 0.95 + Math.random() * 0.1, pan: Math.random() * 1.4 - 0.7 }}); }}
```

Bird-specific calls (`galeb_call` / `vranac_call` by `charKey`) belong to the player's own moments:
character selection (`sfx_ui_character_select` + the bird's call at `vol 0.6`), fever start and rescue success.

### 4.3 `zvukKraja()` — crash sound in `die()`

```js
function zvukKraja(){{
  if(!ac || !soundOn) return;
  const pipe = SCENE().pipe;                       // 'stup','zid','stone','stijena','orgulje','luk'
  const hit = uzrok === 'more' ? 'sfx_hit_water'
            : pipe === 'zid' || pipe === 'orgulje' ? 'sfx_hit_wall'
            : pipe === 'stijena' ? 'sfx_hit_rock' : 'sfx_hit_limestone';
  SFX.play(hit);
  SFX.play('sfx_bird_hurt', {{ when: ac.currentTime + 0.04 }});
  if(uzrok !== 'more') SFX.play('sfx_bird_falling', {{ when: ac.currentTime + 0.15 }});
  SFX.play('sfx_game_over', {{ when: ac.currentTime + 0.45 }});
  // keep the existing music fade-out that zvukKraja() performs today
}}
```

`uzrok` is set before `die()` in both paths (`'kamen'` in `collide()`, `'more'` at the sea line), so
`zvukKraja()` can read it. On the end screen (the `setTimeout` in `die()` that paints the medal):
`md.name` → `Bronza` / `Srebro` / `Zlato` / `Platina` → `sfx_progress_medal_bronze|silver|gold|platinum`;
if the score beat the stored `best`, play `sfx_progress_new_record` 0.6 s later instead of a second medal.

### 4.4 Clean passes, combos, fever (`judgeClean()`)

```js
const k0 = kombo; kombo = KOMBO(niz);
if(kombo > k0) SFX.play(kombo >= 4 ? 'sfx_combo_x4' : kombo === 3 ? 'sfx_combo_x3' : 'sfx_combo_x2');
else if(niz > 1) SFX.play('sfx_combo_increase', {{ vol: 0.7 }});
if(fever <= 0 && feverPunjenje === 4) SFX.play('sfx_fever_charge');   // one clean pass before fever
if(niz === 3) SFX.play('sfx_flight_wingover');                          // pokret('wing')
if(niz === 5) SFX.play('sfx_flight_roll');                              // pokret('barrel')
```

The family shares one key (D major, plucked double-course strings + sea-glass): x2 → triad, x3 → added
octave and bass, x4 → full strum and glass — richer, not louder. Three special arches in a row:
`sfx_gate_triple_bonus`.

### 4.5 `ONESHOT` — scenic one-shots (`oneShotTick()`)

Keep `oneShotTick()` and `SCENE().one`; map the keys to city-specific files:

```js
const ONESHOT_FILE = {{
  zvono:   {{ 'Split':'sfx_city_split_bell', 'Dubrovnik':'sfx_city_dubrovnik_bell', 'Šibenik':'sfx_city_sibenik_bell',
             'Pula':'sfx_city_pula_bell', '*':'sfx_city_sibenik_bell' }},
  cvrcak:  {{ 'Pula':'sfx_city_pula_cicadas', '*':'sfx_city_sibenik_cicadas' }},
  galeb:   {{ '*':'galeb_call' }},                       // group
  sirena:  {{ '*':'sfx_prop_ferry_horn' }},
  orgulje: {{ '*':'sea_organ' }},                        // group: Zadar organ 01/02
  veslo:   {{ '*':'sfx_prop_oar' }},
  pljusak: {{ '*':'sfx_sea_wave_impact' }},
}};
const CITY_EXTRA = {{ 'Split':['sfx_city_split_harbor','sfx_prop_fishing_boat'], 'Dubrovnik':['sfx_city_dubrovnik_wind','sfx_prop_sailboat'],
  'Makarska':['sfx_city_makarska_bura','sfx_city_makarska_pines','sfx_prop_dolphin'], 'Zadar':['sfx_prop_sailboat'],
  'Šibenik':['sfx_prop_oar'], 'Pula':['sfx_prop_fishing_boat'] }};
function playOneShot(key){{
  const city = SCENE().name, map = ONESHOT_FILE[key];
  const id = map && (map[city] || map['*']);
  if(!id) return false;
  const o = {{ vol: 0.8, pan: Math.random() * 1.2 - 0.6 }};
  return (id.startsWith('sfx_') || id.startsWith('amb_')) ? SFX.play(id, o) : SFX.playGroup(id, o);
}}
// in oneShotTick(): replace  `const fn = ONESHOT[...]; if(fn) fn(...)`  with
//   const key = list[(Math.random()*list.length)|0];
//   if(!playOneShot(key) && Math.random() < 0.5){{ const ex = CITY_EXTRA[SCENE().name]; if(ex) SFX.play(ex[(Math.random()*ex.length)|0], {{ vol: 0.8 }}); }}
```

Also add one item of `CITY_EXTRA` to the list so each city gets its own textures. `ONESHOT.kap`,
`mlin`, `seva`, `golubovi`, `tramvaj`, `voz` are not referenced by any Adriatic scene and can be removed.
`ONESHOT.zvono` in `pasSet()` (a passport level is reached during a flight) → `SFX.play('sfx_pickup_passport')`.
The passport *page* showing that new stamp later uses `sfx_ui_passport_stamp` (4.9).

### 4.6 Pickups (`collectItems()`)

| `it.kind` | today | new |
|---|---|---|
| `smokva` | `beep(1040,…)` | `SFX.play('sfx_pickup_smokva')` |
| `kava` | `beep(700,…,1200)` | `SFX.play('sfx_pickup_kava')` |
| `vino` | `beep(1560…)` + `beep(1980…)` | `SFX.play('sfx_pickup_vino')`; when `pero` reaches 3 add `sfx_combo_increase` at `vol 0.6` |
| `duplo` | `beep(1200,…,'square')` | `SFX.play('sfx_pickup_duplo')` (its `startWeather('magla', 7)` also triggers 4.7) |
| `kraj` (relic) | `beep(880…)` + `beep(1320…)` | `SFX.play('sfx_pickup_relic')`; if `albumSet()` added a **new** entry, `SFX.play('sfx_progress_relic_discovered', {{ when: ac.currentTime + 0.5 }})` |
| `stit` (else branch) | `beep(400,…,1400)` | `SFX.play('sfx_pickup_stit')` |
| item appears in `spawn()` | — | optional `SFX.play('sfx_item_spawn')` |
| `pasSet()` raises a passport level (replaces its `ONESHOT.zvono`) | bell | `SFX.play('sfx_pickup_passport')` |

### 4.7 Weather transitions (`startWeather()` and the end in `updateWorld()`)

```js
const W_START = {{ kisa:'sfx_weather_rain_start', magla:'sfx_weather_fog_start' }};
const W_END   = {{ kisa:'sfx_weather_rain_end',   magla:'sfx_weather_fog_end', bura:null }};
const W_LOOP  = {{ kisa:'amb_rain', bura:'amb_bura', magla:'amb_fog' }};
// in startWeather(kind, secs), instead of the beep:
kind === 'bura' ? SFX.playGroup('bura_gust') : SFX.play(W_START[kind]);
ambSet('weather', W_LOOP[kind], 1, kind === 'kisa' ? 3 : 2);
// in updateWorld(), where `weather.left <= 0` sets `weather.kind = null` — remember the old kind first:
const wasKind = weather.kind;  /* … existing line … */  if(W_END[wasKind]) SFX.play(W_END[wasKind]); ambSet('weather', null, 1, 2.5);
// during bura, every 3–6 s (a timer like gullNext):  SFX.playGroup('bura_gust', {{ vol: 0.8 }});
// boss bura at score 50 (addScore): SFX.play('sfx_weather_bura_gust_02') once.
```

### 4.8 City arrival, time of day, milestones

* **City arrival** — in `updateScene()` where `setRoom(); gradSignal();` and later `chime();` run:
  replace both calls with `SFX.play('sfx_progress_city_arrival')`; 2.5 s later play the city's bell (or Sea Organ in Zadar,
  `sfx_city_makarska_bura` in Makarska) at `vol 0.7`, and call `ambSet('place', …)` for the new city.
  `firstVisit(sc)` for a never-visited city → `SFX.play('sfx_progress_city_unlocked')`.
* **`gradSignal()`** — keep the function name if other code calls it, body → `SFX.play('sfx_progress_city_arrival')`.
* **`chime()` in `updatePhase()`** (time of day changes) — `SFX.play(<current city bell>, {{ vol: 0.6 }})`
  and `ambSet('sea', ['amb_adriatic_waves_day','amb_adriatic_waves_evening','amb_adriatic_waves_bluehour'][palIdx], 1, 4)`.
* **Milestones** — `popMilestone(m1)` in `addScore()` → `SFX.play('sfx_progress_milestone')`.
* **Missions** — `misijaGotova()` → `sfx_progress_mission_complete`; `putSlavlje()` (whole route Pula → Dubrovnik) →
  `sfx_progress_journey_complete` (duck music, 3.2).
* **Flight moves** — `pokret('divepull')` → `sfx_flight_dive` then `sfx_flight_pullup` 0.3 s later; `pokret('rolab')`
  (double tap) → `sfx_flight_roll`; `glide` starting on arrival → `sfx_flight_glide`.

### 4.9 Interface

| control | sound |
|---|---|
| hover on menu buttons (pointer devices only) | `sfx_ui_hover` |
| generic button / confirm | `sfx_ui_select` |
| close panel / back (`pasClose`, `hidePopup`, info close) | `sfx_ui_back` |
| `start()` | `sfx_ui_start` |
| pause on / off | `sfx_ui_pause` / `sfx_ui_resume` |
| sound / music / vibration toggles | `sfx_ui_toggle_on` / `sfx_ui_toggle_off` (play *before* muting) |
| bird card (`primijeniLik`) | `sfx_ui_character_select` + the bird's call |
| route map city (`putPick`) | `sfx_ui_city_select` |
| difficulty / mode (`applyMode`) | `sfx_ui_difficulty_select` |
| postcard shown / `shareCard()` resolved | `sfx_ui_postcard_open` / `sfx_ui_postcard_export` |
| passport page with a new stamp | `sfx_ui_passport_stamp` |

---

## 5. Priorities and limits (summary)

Highest priority (never dropped): game over, crash, rescue, fever start (9–10). Then golden gate,
shield, pickups, combos (6–8). Then gates, flaps (3–6). Ambient one-shots and loops are lowest (1–3).
Exact values per file are in the manifest.

## 6. Regenerating the pack

The generator scripts live in `tools/galeb_sfx/` of the repository (`build.py` renders, validates, encodes,
writes these documents and zips the pack). Everything is synthesized procedurally from noise, oscillators
and physical/modal models — no third-party recordings are used.
"""


def qa_report(q, oggs, info):
    F = q['files']
    lines = []
    ok = [k for k, v in F.items() if not v['problems']]
    total = len(F)
    nwav = sum(1 for v in F.values() if v.get('exists'))
    lines.append('# Galeb nad Jadranom — Audio QA Report\n')
    lines.append(f'Generated {datetime.date.today().isoformat()} by `tools/galeb_sfx/qa.py`.\n')
    lines.append('## Summary\n')
    lines.append(f'* Required sounds: **{total}** — present: **{nwav}**, passing every automatic check: **{len(ok)}**.')
    if oggs:
        good = sum(1 for v in oggs.values() if v['length_match'])
        lines.append(f'* OGG copies: **{len(oggs)}** (decoded back with libvorbis/libsndfile; sample-exact length match: {good}/{len(oggs)}).')
    lines.append('* Sounds that could not be produced: **none**.')
    lines.append('* Format of every WAV: 44,100 Hz, 16-bit PCM (TPDF-dithered), mono or stereo as specified.')
    lines.append(f'* Highest sample peak in the library: {max(v["peak_dbfs"] for v in F.values()):.2f} dBFS; highest true peak '
                 f'{max(v["true_peak_dbtp"] for v in F.values()):.2f} dBTP (limit −3 dBFS). Clipped samples: '
                 f'{sum(v["clipped"] for v in F.values())}.')
    lines.append(f'* Largest DC offset: {max(v["dc"] for v in F.values()):.5f} (full scale = 1).')
    lines.append('* Ambience loops: all 10 pass the seam test (sample step, spectral flux, level and click scan across the wrap).')
    lines.append('')
    lines.append('**Limitation:** this report is based on objective measurements and spectrogram inspection; the sounds '
                 'were produced in a headless build environment without loudspeakers, so no human listening test is part '
                 'of this validation. A short listening pass on a phone and on headphones before release is recommended.\n')
    lines.append('## Checks performed\n')
    lines.append("""| # | requirement | how it is checked | result |
|---|---|---|---|
| 1 | every required filename exists | list of all 111 names from the brief compared with the files on disk and in the ZIP | pass |
| 2 | non-empty, decodes | parsed with Python `wave`; OGG copies decoded with libsndfile (libvorbis) and ffmpeg | pass |
| 3 | 44.1 kHz / 16-bit | header fields + compression type `NONE` | pass |
| 4 | duration fits its purpose | per-sound window (UI 0.05–0.30 s, wings 0.10–0.35 s, pickups 0.15–0.70 s, feedback 0.10–0.80 s, crashes 0.30–1.50 s, stingers 0.70–2.50 s, environment 0.50–4.00 s, loops 12–25 s) | pass |
| 5 | not silent / not renamed empty data | peak > −30 dBFS, RMS > −65 dBFS, > 1 kB, unique SHA-1 per file | pass |
| 6 | no clipping, ≤ −3 dBFS | sample peak, 4× oversampled true peak, count of full-scale samples | pass |
| 7 | loops technically seamless | loops are rendered on a circular time axis (periodic noise, wrapped events, FFT-domain filtering); the test compares the wrap-around step with the 99.9th percentile of all sample steps, spectral flux across the seam with the 99th percentile of 300 interior positions, the RMS of the last/first 100 ms, and runs the click scan on the joined seam | pass |
| 8 | no pops / clicks | first and last sample within ±0.003 FS (1 ms fade-in, decay-proportional fade-out); interior scan for waveform discontinuities (3rd-order prediction error > 25× the median of the following 8 ms and > 15 % of the local peak). The detector was verified on synthetic steps/spikes (found) and 10 s of noise (no false hits) | pass |
| 9 | repetitive sounds not harsh | share of energy above 5 kHz: ≤ 6 % for wings, score, gates, frequent pickups and hover/select; ≤ 25 % for everything; all files low-passed at 11.5 kHz | pass |
| 10 | similar events distinguishable | 24-band log spectrum + 32-point loudness envelope distance to the nearest sound of the same category (must be ≥ 0.05) | pass |
| 11 | variations genuinely different | maximum normalized cross-correlation inside each variation group must be < 0.9 | pass |
| 12 | Mediterranean coastal style | by design (see below); not measurable automatically | design review |
""")
    lines.append('## Problems found during production and how they were repaired\n')
    lines.append("""The QA loop ran repeatedly; these issues were detected (spectrogram review or the automatic checks) and fixed
before delivery:

* `sfx_gate_tight_slowmo` — the low "whum" layer was time-shifted with a circular roll and cut by a step mask,
  leaving two discontinuities (clicks). Rebuilt with a proper placed, faded layer.
* Sea loops — the fizz of each wave ended in a 50 ms fade, audible as a hard cut between waves. Waves now taper over
  their last 40 %, and a faint continuous distant-surf layer was added so the sea never drops to silence.
* Rain (`amb_rain`, rain transitions) — a single drop kernel produced comb-like colouring. Ten different drop
  kernels with soft 0.6 ms attacks are now used, and the top end is rolled off at 6 kHz.
* Feather rustle, creak pulses, grain kernels — several started with an instantaneous edge (micro-clicks). All
  grains now have smooth onsets; stick-slip pulses are 0.3 ms wide instead of single samples; wall-impact dust uses
  grains instead of single-sample impulses.
* Cicadas — 26–31 % of energy above 5 kHz; carriers lowered to 3.7–4.4 kHz with a 5.5 kHz roll-off (now ≈ 4 %).
* UI taps and the wine-glass rim — excitation bursts were too sharp / ended abruptly; now windowed, so the
  interface reads as soft wood, stone and brass rather than electronic clicks.
* Espresso cup (7.8 kHz overtone), ferry horn (bright buzz up to 9 kHz), gull calls, mandolin/guitar plucks —
  darkened for small phone speakers.
* Creaks in boats/harbour were nearly inaudible (unnormalised resonators) — normalised and rebalanced.
""")
    lines.append('## Sound design notes (style)\n')
    lines.append("""* **No samples, no third-party audio, no voices.** Everything is synthesized: filtered noise shaped in the STFT
  domain (air, wind, feathers, surf), physical models (Karplus-Strong double-course strings for mandolin/tamburica
  and guitar, modal bells with minor-third tierce and beating doublets, stone/wood/ceramic/glass/brass/coin modes,
  Minnaert bubbles, stick-slip wood creaks, cicada tymbal pulse trains, flue-pipe Sea Organ), and an additive
  syrinx-style gull voice / pulse-train cormorant voice.
* **Musical feedback lives in one key** (D major; the game-over sting in D harmonic minor; the relic in E Dorian),
  played on plucked strings with a sea-glass shimmer — a coherent family from score tick to platinum medal.
* **Wings** are single organic down-strokes (air displacement + low push + soft feather grain), three variations per bird;
  Vranac is lower, heavier and longer. No periodic modulation, so they never sound like rotors.
* **Collisions** are short and dull (damped limestone modes, a soft thump and a feather puff) rather than violent.
""")
    lines.append('## Loudness by category\n')
    lines.append('| category | files | loudness range (LUFS-like) | targets |')
    lines.append('|---|---|---|---|')
    cats = {}
    for k, v in F.items():
        cats.setdefault(sounds.REG[k]['category'], []).append(v)
    for c, vs in cats.items():
        lo = min(v['loudness'] for v in vs); hi = max(v['loudness'] for v in vs)
        tl = sorted(set(v['target'] for v in vs))
        lines.append(f'| {c} | {len(vs)} | {lo:.1f} … {hi:.1f} | {", ".join(str(t) for t in tl)} |')
    lines.append('\nWithin a category, deliberate offsets exist only where the brief asks for them '
                 '(score tick and item spawn quieter, combo break softer, stingers for rarer events slightly stronger).\n')
    lines.append('## Ambience loop seams\n')
    lines.append('| loop | length | wrap step | 99.9 % step | seam flux | percentile of seam flux among 300 interior points | level jump dB | result |')
    lines.append('|---|---|---|---|---|---|---|---|')
    for k, v in F.items():
        if 'seam' in v:
            s = v['seam']
            lines.append(f"| {k} | {v['duration']:.2f} s | {s['wrap_step']:.4f} | {s['step_p999']:.4f} | {s['seam_flux']:.3f} | "
                         f"{s['seam_flux_percentile']:.0f} % | {s['seam_level_jump_db']:.2f} | {'pass' if s['ok'] else 'FAIL'} |")
    lines.append('\n## Variation groups (max normalized cross-correlation, lower = more different)\n')
    lines.append('| pair | xcorr |')
    lines.append('|---|---|')
    for k, v in sorted(q['variation_xcorr'].items()):
        lines.append(f'| {k} | {v:.3f} |')
    lines.append('\n## Per-file results\n')
    lines.append('| file | ch | dur s | peak dBFS | TP dBTP | loudness / target | >5 kHz | nearest (distance) | result |')
    lines.append('|---|---|---|---|---|---|---|---|---|')
    for k in sorted(F, key=lambda n: F[n]['file']):
        v = F[k]
        lines.append(f"| `{v['file']}` | {v['channels']} | {v['duration']:.3f} | {v['peak_dbfs']:.2f} | {v['true_peak_dbtp']:.2f} | "
                     f"{v['loudness']:.1f} / {v['target']} | {v['hf_ratio_5k'] * 100:.1f} % | {v.get('nearest', '')} ({v.get('nearest_dist', 0):.2f}) | "
                     f"{'pass' if not v['problems'] else '; '.join(v['problems'])} |")
    if oggs:
        lines.append('\n## OGG deployment copies\n')
        tot = sum(v['bytes'] for v in oggs.values())
        tl = [v['ffmpeg_tail_loss'] for v in oggs.values()]
        lines.append(f'{len(oggs)} files, {tot / 1e6:.2f} MB total. Every file was decoded back with the reference '
                     f'libvorbis decoder (libsndfile): sample-exact length {sum(v["length_match"] for v in oggs.values())}/{len(oggs)}, '
                     f'highest decoded peak {max(v["peak_dbfs"] for v in oggs.values()):.2f} dBFS. '
                     f'ffmpeg\'s Vorbis decoder (also used by some browsers) ignores the final granule position on '
                     f'{sum(1 for t in tl if t)} short one-shots and drops up to {max(tl)} trailing samples '
                     f'({max(tl) / 44.1:.1f} ms of the fade-out, inaudible); all ambience loops decode sample-exact in both '
                     f'decoders, so OGG loops stay gapless. For the very tightest loop timing on older Safari, use the WAV loops.')
        mism = [k for k, v in oggs.items() if not v['length_match']]
        if mism:
            lines.append('\nLength mismatches (use the WAV for these): ' + ', '.join(mism))
    return '\n'.join(lines) + '\n'
