# TRI FILDŽANA — SFX mapping

How the files in `audio/sfx/` map onto the existing `AU` audio manager in `index.html`.
Line numbers refer to the `index.html` in the supplied ZIP; the game itself was not modified.

**Labels**

| Label | Meaning |
|---|---|
| **REPLACE** | Replacement for an existing audio call (`AU.thunk()`, `AU.tone(...)`, …) |
| **NEW** | New sound for an existing animation or state that currently has no audio trigger |
| **REUSE** | Reuse of an asset from this pack in a second context |

**Source of the audio.** Every file is procedurally synthesized with physical and source-filter models: modal ceramic, wood and metal; friction and fabric noise; Karplus–Strong plucked strings; membrane drums; a glottal-pulse voice model. **None of it is recorded Foley or a voice recording.** The vocal reactions (`saner_*`, `levat_reaction`, `minka_attention`, `audience_murmur`) are the least natural part of the pack. Replace them with recordings from a voice actor before release if possible. The filenames and triggers below stay valid either way.

---

## 1. Audit of the current audio code

`AU` (lines 110–209) creates every sound with oscillators (`AU.tone`) and band-passed noise (`AU.noise`). The named helpers are only wrappers around those two primitives:

| Helper | Lines | What it synthesizes | Call sites outside `AU` | Distinct meanings |
|---|---|---|---|---|
| `thunk` | 168 | sine 150→58 Hz + noise burst | 13 | cup set down, table bump, police grab, confiscation, raid, bribe refusal, intro cups, wind settle, klapa hit, flee table |
| `whoosh` | 169 | noise sweep 700→2200 Hz | 4 | cup slide (swap), flee "milicija" vanish, flee "inventura" pack |
| `tap` | 170 | square 760→520 | 1 | cup pick |
| `chip` | 171 | two triangle blips | 18 | bet / UI buttons / round start / interlude panel |
| `glint` | 172 | high triangle blips | 2 | cheating tell **and** eye power-up (must be split) |
| `coin(n)` | 173–175 | n triangle blips | 3 | Levat bribe, accepted police bribe, advert interlude |
| `win` | 176–181 | plucked hijaz run | 3 | round win, New-Year start, escape victory |
| `lose` | 182–186 | sawtooth/square drop | 1 | round lose |
| `coo` | 187–191 | three sine glides | 2 | pigeon perch, pigeon power-up |
| `ring` | 192–197 | square double beeps | 2 | Minka phone call, telephone interlude |
| `sirena` | 198–203 | square 760/560 alternation | 2 | raid, taken away |
| `poke` | 204 | square + sine blip | 1 | Šaner tapped |
| `gameover` | 205–208 | descending plucks | 2 | out of money, arrested |
| `pluck` | 161–166 | triangle+sine | 5 | coffee power-up, interlude plucks, title |
| `tone` (direct) | 133 | oscillator | 39 total (≈30 direct) | see table below |
| `noise` (direct) | 146 | filtered noise | 11 total (≈10 direct) | see table below |

`AU.init`, `AU.ok`, `AU.on`, `AU.ctx` and the `master` gain node stay. Everything else in the table above is to be removed.

---

## 2. Call-site mapping

### State changes, rounds, results

| Line | Function / context | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 2427 | `newGame` – New-Year special (`G.silvester`) | `AU.win()` | `title_sting` + `audience_murmur` | REUSE |
| 2451 | `toBet` – Hakala heckles from the audience | `AU.tone(520,…square)` | `audience_murmur` | REPLACE |
| 2479 | `toOver` – broke, game over | `AU.gameover()` | `game_over` | REPLACE |
| 2494 | `toRacija` – raid | `AU.sirena()` | `police_siren`, then `saner_gasp` at +0.15 s | REPLACE + NEW (gasp) |
| 2516 | `pokreniMito` – bribe demand | `AU.tone(200,…sawtooth)` | `police_warning` | REPLACE |
| 2537 | `toUhapsen` – arrested | `AU.gameover()` | `game_over` (+ escort, see §3) | REPLACE |
| 2552 | `toOdveli` – taken away, money kept | `AU.sirena()` | `police_siren` (+ escort, see §3) | REUSE |
| 2620 | `startLevatLeave` | `AU.tone(180,…sine)` | `levat_reaction` | REPLACE |
| 2655 | `toFlee` – Šaner gives up | `AU.tone(240,…sawtooth)` | `saner_annoyed_01` | REPLACE |
| 2672 | `toPobjeda` – level won by flight | `AU.win()` | `escape_victory` | REPLACE |
| 2766 | `startRound` – bet placed | `AU.chip()` | `bet_place` | REPLACE |
| 2768 | `startRound` – Minka calls (`G.minka===1`) | `AU.ring()` | `telephone_ring` | REPLACE |
| 2783 | `startRound` – drunk Hakala takes over the shuffle | `AU.tone(340,…square)` | `cup_rattle_02` | REPLACE |
| 2846 | `doPick` | `AU.tap()` | `cup_select` | REPLACE |
| 2870 | `resolve` – win | `AU.win()` | `round_win` + `coins_large` at +0.12 s (14 coins spawn) | REPLACE + NEW (coins) |
| 2880 | `resolve` – lose | `AU.lose()` | `round_lose` | REPLACE |
| 2896 | `resolve` – Ćiro chased away | `AU.tone(200,…sawtooth)` | `saner_angry_02` | REPLACE |
| 2902 | `resolve` – Ćiro got it wrong | `AU.tone(520,…triangle)` | `audience_murmur` | REUSE |
| 2915 | `idleGunđanje` step 1 | `AU.tone(330,…square)` | `saner_annoyed_02` | REPLACE |
| 2921 | `idleGunđanje` step 3 | `AU.tone(220,…sawtooth)` | `saner_annoyed_01` | REUSE |
| 2925 | `idleGunđanje` – auto bet | `AU.chip()` | `bet_place` | REUSE |
| 3110 | `update` – Šaner answers Hakala | `AU.tone(180,…sawtooth)` | `saner_annoyed_*` (random) | REUSE |
| 3218 | `update` – Minka arrives in person | two `AU.tone(1400,…square)` | `minka_attention` | REPLACE |
| 3730 | `pokeSaner` | `AU.poke()` | `saner_poke` (min. 1.2 s retrigger; fall back to silence, never a beep) | REPLACE |

### Shuffling and cups

| Line | Context | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 2825 | `beginSwap` – swap starts without a hand reach | `AU.whoosh()` | `cup_slide_0[1-4]` | REPLACE |
| 3448 | MIX – hand reach finished, swap starts | `AU.whoosh()` | `cup_slide_0[1-4]` | REPLACE |
| 3480 | MIX – swap finished (`t>=1`) | `AU.tone(110,…)` | `cup_set_down_0[1-4]` | REPLACE |
| 3459 | MIX – cheat at half-swap (`G.tell`) | `AU.glint()` | `cheat_glint` | REPLACE |
| 3488 | MIX – "navika": he noticed your habit, one more swap | `AU.tone(420,…triangle)` | `saner_chuckle_02` | REPLACE |
| 3416 | SHOW – ball cup comes down | `AU.thunk()` | `cup_set_down_*` | REPLACE |
| — | SHOW – ball cup lifts (`G.t≈0`) | none | `cup_lift_01` | NEW |
| 3443 | MIX – Hakala forgot, lifts the cup | `AU.tone(300,…sine)` | `cup_lift_02` + `audience_murmur` | REPLACE |
| 3436 | MIX – Hakala puts it back | `AU.thunk()` | `cup_set_down_*` | REPLACE |
| — | REVEAL – picked cup lifts (`G.t>0.38`) | none | `cup_lift_*` | NEW |
| — | REVEAL revPhase 1 – true cup lifts | none | `cup_lift_*` | NEW |
| 3603 | REVEAL – ball's real place shown | `AU.tone(660,…triangle)` | `ball_reveal` | REPLACE |
| — | RESULT – cups lowered (`G.t` 2.0–2.5) | none | `cup_set_down_*` once at 2.5 s | NEW |
| 3121 | `update` – Levat bumps the table | `AU.thunk()` | `table_bump`, then `cup_rattle_01` at +0.1 s (ball cup tilts, `nakrivT`) | REPLACE + NEW |
| 3578 | PICK – tilted cup settles | `AU.thunk()` | `cup_set_down_*` | REPLACE |
| 3545 | PICK – night wind starts | `AU.noise(0.8,320,…)` | `wind_gust` | REPLACE |
| 3567 | PICK – wind finished, cups land | `AU.thunk()` | `cup_set_down_*` (one, not three) | REPLACE |
| 3519 | PICK – Ćiro shouts a tip | `AU.tone(600,…square)` | `audience_murmur` | REUSE |

### Power-ups and pigeon

| Line | Context | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 4551 | Coffee | `AU.pluck(392,…)` | `coffee_activate` | REPLACE |
| 4556 | Eye | `AU.glint()` | `eye_activate` (deliberately distinct from `cheat_glint`) | REPLACE |
| 4568 | Paid pigeon | `AU.coo()` | `pigeon_wings_02` now; `pigeon_coo_*` when it perches (line 3712) | REPLACE |
| — | `updateBird` phase 0 starts (random pigeon at line ~3500) | none | `pigeon_wings_02` | NEW |
| 3712 | `updateBird` – perches | `AU.coo()` | `pigeon_coo_0[1-2]` | REPLACE |
| 3717 | `updateBird` – takes off | `AU.noise(0.28,900,…)` | `pigeon_wings_01` | REPLACE |

**Coffee (55 % shuffle speed).** Don't slow down or pitch-shift any audio. Slide and set-down sounds are triggered by the swap events at lines 2825/3448/3480. Under coffee those events simply arrive 1/0.55 times further apart, so the audio follows the motion on its own.

### Police and bribery

| Line | Context | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 3631 | RACIJA arrest – police grab (`MILICIJA_UVOD`) | `AU.thunk()` | `police_grab` | REPLACE |
| 3644 | RACIJA – cup confiscated | `AU.thunk()` | `cup_rattle_01` (cup leaves to the right) | REPLACE |
| 3677 | MITO – no answer, both taken | `AU.thunk()` | `bribe_rejected` + `police_grab` at +0.2 s | REPLACE |
| 4518 | MITO – "not a single mark" | `AU.tone(160,…sawtooth)` | `bribe_rejected` | REPLACE |
| 4530 | MITO – bribe accepted | `AU.coin(4)` | `money_handover` + `coins_large` at +0.2 s (12 coins spawn) | REPLACE |
| 4534 | MITO – bribe too small | `AU.thunk()` | `money_handover`, `bribe_rejected` at +0.35 s | REPLACE |
| 4545 | Levat bribe (`levmito`) | `AU.coin(2)` | `money_handover` + `coins_small` | REPLACE |

### Escape (`FLEE_VARS`)

| Line | Variant / moment | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 2964 | `fleeRun` – each step (every 0.17 s) | `AU.tone(96,…)` | `run_step_01…04` round-robin | REPLACE |
| — | run starts (`ft` crosses `G.fleeRunAt`) | none | `escape_swish` | NEW |
| 2977 | **sto** `ft>0.9` | `AU.tone(180,…sawtooth)` | `table_overturn` (its impact lands at +0.42 s ≈ `ft` 1.32, matching `tableFlip`) | REPLACE |
| 2981 | **sto** `ft>1.3` | `AU.thunk()` + `AU.noise(0.55,260,…)` | `cups_scatter` + `coins_large` (9 coins) | REPLACE |
| 2989 | **sto** per-cup tones | `AU.tone(500+i*120,…)` ×3 | covered by `cups_scatter`; remove | REPLACE |
| 3011 | **dim** `ft>0.9` | `AU.tone(700,…triangle)` | `saner_chuckle_01` | REPLACE |
| 3015–3016 | **dim** `ft>1.5` smoke bomb | `AU.noise(0.7,…)` + `AU.tone(90,…)` | `smoke_puff` | REPLACE |
| — | **dim** Šaner fades out (`sanerA` → 0) | none | `escape_swish` at +0.05 s | NEW |
| 3032–3033 | **milicija** `ft>0.75` "police!" | two `AU.tone(2100,…square)` | `distraction_whistle` | REPLACE |
| 3038 | **milicija** `ft>1.7` vanish | `AU.whoosh()` | `escape_swish` | REPLACE |
| 3049 | **inventura** `ft>0.9` | `AU.whoosh()` | `bundle_pack` (its three clinks line up with the cups at `ft` 0.95/1.10/1.25) | REPLACE |
| 3061 | **inventura** per-cup grab | `AU.tone(560+i*110,…)` ×3 | covered by `bundle_pack`; remove | REPLACE |
| 3069 | **inventura** rug flies | `AU.noise(0.35,520,…)` | `cloth_swish` | REPLACE |

### Intro (`S.INTRO`, four variants `G.introVar`)

| Line | Cue | Current call | New sound(s) | Label |
|---|---|---|---|---|
| 3312 | cue 1, `it>0.02` | `AU.noise(0.10,2400,…)` + `AU.tone(70,…)` | `tv_switch_on` | REPLACE |
| 3317 | cue 2, `it>0.9` (variants 0/2/3) | `AU.tone(1000,1.45,…)` | `tv_test_tone` | REPLACE |
| 3316 | cue 2, variant 1 | `AU.tone(440,0.35,…)` | `tv_test_tone`, stopped after 0.35 s with a 30 ms gain ramp | REUSE |
| 3323 | cue 3, variant 1 (film set) | `AU.thunk()` + `AU.tone(1600,…square)` | `film_clapper` | REPLACE |
| 3326 | cue 3, other variants | `AU.noise(0.5,1100,…)` | `tv_static_cut` | REPLACE |
| — | variant 0 "counting money", cue 4 (`it>2.98`) | none | `banknotes_count` | NEW |
| 3364–3365 | variant 0 "are we recording?!" | `AU.noise` + `AU.tone(180,…)` | `saner_gasp` | REPLACE |
| 3337 | variant 2 phone beat | `AU.tone(880,…square)` | `telephone_pickup` | REPLACE |
| 3342 | variant 2 panic | `AU.tone(180,…sawtooth)` | `saner_gasp` | REUSE |
| 3349 | variant 3 Levat as newsreader | `AU.tone(520,…square)` | `news_sting` | REUSE |
| 3381 | cups dropped onto the table (5.10 + i·0.30 s) | `AU.thunk()` | `cup_set_down_01/02/03` (one per cup) | REPLACE |
| 3394–3395 | cue 7, title | `AU.tone(84,…)` + `AU.pluck(293.66,…)` | `title_sting` | REPLACE |

### Interludes (`MEDJU`, 12 entries; `levatLeavePhase===4`)

The current code only distinguishes interludes 0–5. Interludes 6–11 all fall into the `else` branch (one noise sweep). The plan below covers all twelve with shared files; no interlude gets its own soundtrack.

| # | Interlude | Cue 1 – opener (line 3164–3169) | Cue 2 – mid hit (3174–3177, at `cut×0.5`) |
|---|---|---|---|
| 0 | klapa (clapper) | `transition_swish` (REPLACE `AU.noise`) | `film_clapper` (REPLACE `AU.thunk`+`noise`) |
| 1 | selidba (moving) | `moving_rumble` (REPLACE `AU.tone(120)`) | — |
| 2 | reklama (advert) | `advert_sting` (REPLACE two `AU.pluck`) | `coins_small` (REPLACE `AU.coin(3)`) |
| 3 | dnevnik (news) | `news_sting` (REPLACE `AU.tone(440,square)`) | `tv_static_cut` (NEW) |
| 4 | telefon | `telephone_ring` (REPLACE `AU.ring`) | `telephone_pickup` (REPLACE `AU.tone(300)`) |
| 5 | karta puta (route map + stamp) | `paper_map` (REPLACE `AU.noise`) | `paper_map` again for the stamp (REPLACE `AU.tone(520)`)* |
| 6 | sjednica (meeting) | `transition_swish` (REPLACE else-branch noise) | `audience_murmur` at `t>2` when it turns from quarrel to "approved" (NEW) |
| 7 | dnevnik 2 | `news_sting` (REUSE) | `tv_static_cut` (NEW) |
| 8 | audicija (audition, camera prop) | `transition_swish` (REPLACE) | `film_clapper` (NEW) |
| 9 | pauza (whispered break) | `transition_swish` (REPLACE) | — (keep it quiet) |
| 10 | gost (guest) | `transition_swish` (REPLACE) | `levat_reaction` (NEW, optional) |
| 11 | reklama 2 | `advert_sting` (REUSE) | `coins_small` (NEW) |

\* The brief has no dedicated rubber-stamp sound. Add `stamp.wav` later if you want one.

| Line | Shared cue | Current call | New sound | Label |
|---|---|---|---|---|
| 3183 | Cue 3 – cut to the next location | four `AU.pluck` | `scene_transition` | REPLACE |
| 3185 | Cue 4 – "next level" panel | `AU.chip()` | `ui_confirm` | REPLACE |

### Menus / interface

| Lines | Context | Current call | New sound | Label |
|---|---|---|---|---|
| 4462, 4463, 4466 | `onUp` – continue after interlude / new game | `AU.chip()` | `ui_confirm` | REPLACE |
| 4475, 4482, 4485, 4489, 4492, 4493, 4494, 4501–4504 | `handle` – demo stop, language, pixel mode, options, sound on, easy, start, stats, share, again | `AU.chip()` | `ui_confirm` | REPLACE |
| 4651 | key `M` – sound toggled on | `AU.chip()` | `ui_confirm` | REPLACE |

---

## 3. New triggers for existing animations (no audio today)

| Sound | Where to trigger | Rule |
|---|---|---|
| `saner_angry_0[1-2]` | `S.RESULT && G.won`, once when `G.t` crosses 1.0 (`sanerEmotion` switches scared→angry) | once per win, 5 s retrigger guard |
| `saner_chuckle_0[1-2]` | `S.RESULT && !G.won`, once when `G.t` crosses 2.95 (`saner_gloat_*` frames start) | once per loss; skip if the previous loss already chuckled (alternate with silence) |
| `saner_wipe_forehead` | `sanerPose` returns `saner_wipe_0` (start of the wipe, `t%8` crosses 6.4) | once per wipe; idle sweat drops stay silent |
| `saner_nervous` | `update`, where `G.nerv > G.nervRekao` raises the nerve level (~line 3100) | at most once per level change, 6 s guard |
| `saner_gasp` | `toRacija` (+0.15 s after the siren); intro variants 0 and 2 (see above) | — |
| `police_step_01…04` | RACIJA entry: `G.t` 0.10 / 0.38 / 0.66 (walk-in, `entry<1`); escort in `policeAnimation` (`taken && G.t≥0.7`): one step every 0.26 s while `progress<1`, alternating variants | round-robin, gain 0.9 → 0.6 as they walk off screen |
| `police_grab` | `toUhapsen` / `toOdveli` at `G.t≈0` (grab frames 4–7) and RACIJA grab at line 3631 | — |
| `cup_lift_0[1-2]` | SHOW start; REVEAL picked-cup lift; REVEAL true-cup lift; Hakala check | — |
| `pigeon_wings_02` | Pigeon phase 0 starts (both random pigeon and paid pigeon) | — |
| `escape_swish` | Flee run start; "dim" disappearance | — |
| `banknotes_count` | Intro variant 0 (`saner_count` pose) at cue 4 | — |
| `coins_large` | With `spawnCoin` bursts: win (14), bribe accepted (12), table overturn (9) | — |
| `levat_reaction` | Optional: when Levat peeks in (`levatPeek` rises above 0.5 from idle timer, ~line 3195) | 8 s guard; skip during Minka's call |

**Not given sound on purpose:** blinks, winks, sweat droplets, idle breathing, the Levat speech bubbles, Šaner's per-letter talk frames, and Minka's speech bubbles. There are also no handcuff sounds, because the game never shows handcuffs.

---

## 4. Integration rules (for the later code change)

1. **Remove** `AU.tone`, `AU.noise`, `AU.pluck`, the `noiseBuf` and every helper listed in §1. No `OscillatorNode` or synthetic `noiseBuf` may remain.
2. **Load** the files once after the first user gesture: `fetch` → `decodeAudioData` → a `Map` keyed by sound id holding its variant buffers, as listed in `sfx_manifest.json`.
3. **Play** through one function, e.g. `AU.play(id, {delay, gain, pan, variant})`: `AudioBufferSourceNode` → `GainNode(recommended_gain × gain)` → optional `StereoPannerNode` (mono Foley only) → `AU.master`.
4. **No fallback beep.** If a buffer is missing or not yet decoded, `AU.play` returns silently, without calling an oscillator, `console.warn` spam, or a retry loop.
5. **Variants.** Use `random_no_immediate_repeat` for multi-file ids. `run_step` and `police_step` should go round-robin.
6. **Retrigger guards.** Honour `min_retrigger_s` from the manifest, especially for voices: at most one Šaner vocal at a time, and a new vocal cuts any running one with a 30 ms fade.
7. **Ball secrecy.** Slide and set-down variants are chosen at random per swap, never from the cup or ball index. Fake swaps get the same sounds as real ones.
8. **Coffee.** Never change `playbackRate` or apply a global slowdown. The audio follows the slower swap events by itself.
9. **Mute.** `AU.on` keeps gating `AU.play`. The `snd` button and the `M` key play `ui_confirm` only after turning sound back on, as they do today.
