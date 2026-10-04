"""Assemble metadata/*.json|csv|txt from the generator registry + validation results."""
import sys, os, json, csv, re, glob, datetime
sys.path.insert(0, os.path.dirname(__file__))
import meta
ROOT = sys.argv[1]
HERE = os.path.dirname(__file__)
REG = os.path.join(HERE, '..', 'registry')
MD = os.path.join(ROOT, 'metadata'); os.makedirs(MD, exist_ok=True)
VAL = json.load(open(os.path.join(REG, 'validation.json')))
SPK = json.load(open(os.path.join(REG, 'speaker_check.json')))
VOX = json.load(open(os.path.join(REG, 'voice_identities.json')))
entries = [e for e in meta.load_all() if not e['file'].startswith('__')]
cafe_asr = [e for e in meta.load_all() if e['file'] == '__cafe_asr__']

def category(rel):
    top = rel.split('/')[0]
    return {'sfx': 'physical', 'crowd': 'spectators', 'voices': 'character_voice', 'ambience': 'ambience',
            'animals': 'animal', 'ui': 'ui', 'music': 'music'}[top]

def status_letter(st):
    if st.startswith('optional'): return 'C'
    if st.startswith('new-routing (missing'): return 'B'
    return 'A'

# ------------------------------------------------------------------ manifest
manifest = []
for e in sorted(entries, key=lambda e: e['file']):
    v = VAL['files'][e['file']]
    aid = os.path.basename(e['file'])[:-4]
    loop = e.get('loop')
    item = {
        'asset_id': aid, 'file': e['file'], 'browser_file': 'browser/' + e['file'][:-4] + '.mp3',
        'category': category(e['file']), 'variant_group': e['group'],
        'duration_s': v['duration'], 'sample_rate': v['samplerate'], 'bit_depth': v['bit_depth'], 'channels': v['channels'],
        'loop': bool(loop), 'loop_start_sample': loop['start'] if loop else None,
        'loop_end_sample': loop['end'] if loop else None,
        'intended_event': e.get('event'), 'html_hook': e.get('hook'),
        'selection_rule': e.get('select'),
        'suggested_gain_db': e.get('gain_db', 0.0), 'safe_playback_rate': e.get('rate'),
        'cooldown_ms': e.get('cooldown_ms'), 'max_concurrent': e.get('max_voices'),
        'character_id': e.get('character'), 'voice_kind': e.get('kind'),
        'transcript': e.get('transcript') or None, 'permitted_text_match': e.get('permitted_text'),
        'trigger_status': e.get('status'), 'coverage_class': status_letter(e.get('status', '')),
        'optional': bool(e.get('optional', False)),
        'production_method': e.get('method'),
        'source_provenance': 'original, produced for this pack; no third-party recordings' if 'Kokoro' not in (e.get('method') or '')
                             else 'Kokoro-82M (Apache-2.0) synthetic voices via kokoro-onnx (MIT); no recordings; no cloned real person',
        'peak_dbtp': v['true_peak_dbtp'], 'lufs_integrated': v['lufs'], 'rms_dbfs': v['rms_dbfs'],
    }
    for k in ('asr_heard', 'asr_cer', 'phonemes', 'html_source', 'voice_blend', 'speed', 'pitch_semitones', 'note', 'seam'):
        if k in e: item[k] = e[k]
    manifest.append(item)
assert len(manifest) == 133, len(manifest)
json.dump({'pack': 'boce_na_rivi_complete_audio', 'generated': datetime.date.today().isoformat(),
           'master_count': len(manifest), 'format': 'WAV PCM 48 kHz 24-bit',
           'note': 'Gains, rates, cooldowns and concurrency are recommendations; they were not verified inside the game engine.',
           'assets': manifest}, open(os.path.join(MD, 'audio_manifest.json'), 'w'), ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ voice text index (exact-text routing)
vt = {}
for e in entries:
    if e['file'].startswith('voices/') and e.get('transcript'):
        vt.setdefault(e['character'], {})[e['transcript']] = e['file']
json.dump({'rule': 'glasLika(lik, txt): if txt === key for lik.id -> play file; else if the line is chatter '
                   '(lik.prica, lik.fraze, USKLICI.prica, USKLICI.suigrac, "brbljanje") -> voices/<id>/voice_<id>_chat.wav at -4 dB; '
                   'else (generic USKLICI reactions, censored psovke) -> no voice clip.',
           'exact_text': vt}, open(os.path.join(MD, 'voice_text_index.json'), 'w'), ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ event mapping
EV = [
 # id, function / branch, call sites, files, selection, layering, never-stack, gain, rate, cooldown, maxv, status
 ('ball_collision', 'klak(jacina, false)', 'korak() pair loop, pass 0, fx!=null (live play, UVODI)', 'sfx/balls/sfx_ball_collision_{soft|medium|hard}_0[1-3].wav',
  'tier by jacina: <0.25 soft, <0.6 medium, else hard; random variant, avoid repeating last; gain within tier 20*log10(0.6+0.4*jacina_norm)',
  'klak() itself may call povikPublike() (jacina>0.5, 75 %) - crowd layer stays separate', 'second klak on the same ball pair within 45 ms', 0, '0.94-1.07', 45, 3, 'A existing'),
 ('bulin_collision', 'klak(jacina, true)', 'korak() when a or b is the bulin', 'sfx/balls/sfx_bulin_collision_{soft|hard}_0[1-3].wav',
  'jacina <0.4 soft else hard', '-', 'ball_collision for the same contact (pick one family per contact)', 0, '0.94-1.07', 45, 2, 'A existing'),
 ('gravel_land', 'tup(jac)', 'korak() ground impact b.vz < -0.35 (every bounce)', 'sfx/gravel/sfx_gravel_land_{soft|hard}_0[1-3].wav',
  'jac <0.35 soft else hard; later bounces of the same ball: same family at 20*log10(jac/jac_first) dB', '-', 'more than 3 voices; same ball within 35 ms', 0, '0.9-1.1', 35, 3, 'A existing'),
 ('gravel_roll', 'kotrljajZvuk(brzina)', 'azuriraj(): fastest grounded ball while stanje LET or PONOVKA, else 0', 'sfx/gravel/sfx_gravel_roll_slow_loop.wav + sfx_gravel_roll_fast_loop.wav',
  'two looping sources always running at gain 0; slow audible 0.12-2.5 m/s, fast from 1.5 m/s; equal-power crossfade over 1.5-2.5 m/s; '
  'overall gain = existing target min(0.20,0.03+v*0.035) mapped to dB; playbackRate 0.85+min(v,9)*0.045 (stays in 0.85-1.25)',
  'replaces the noise bed in sagradiZvuk(); keep setTargetAtTime smoothing (0.05-0.1 s)', 'a second roll loop pair', 0, '0.85-1.25', 0, 1, 'A existing'),
 ('gravel_stop', 'skripa()', 'korak() when a rolling ball stops (s > 0.052)', 'sfx/gravel/sfx_gravel_stop_0[1-3].wav', 'random', '-', '-', 0, '0.92-1.08', 60, 2, 'A existing'),
 ('throw', 'zamahZvuk(tip)', 'baci(); UVODI jutro/trulo/maestral/fjaka', 'sfx/throws/sfx_throw_{bulanje|trulo}_0[1-3].wav', 'by tip', '-', '-', 0, '0.95-1.05', 200, 1, 'A existing'),
 ('wood_side', 'korak() side-board else branch', '|x| > X_ZID - r and z <= VIS_ZIDA (ball bounces off side board)', 'sfx/boundaries/sfx_wood_boundary_{soft|hard}_0[1-3].wav',
  'v = |vx| before reflection: <2.5 m/s soft else hard; gain 20*log10(clamp(v/5,0.2,1))', 'existing glasPublike("zamor",0.8) 30 % stays', 'the current tup(0.5) in this branch (replace it, do not layer)', 0, '0.92-1.08', 80, 2, 'B new routing'),
 ('wood_rear', 'korak() rear-board else branch', 'y > Y_KRAJ - r and z <= VIS_ZIDA (currently silent)', 'sfx/boundaries/sfx_wood_boundary_{soft|hard}_0[1-3].wav',
  'v = |vy| before reflection, same tiers', '-', '-', 0, '0.92-1.08', 80, 2, 'B new routing'),
 ('wood_front_sill', 'korak() front sill clamp', 'y < Y_PRAG + r (ball rolls back to the throwing line; currently silent)', 'sfx/boundaries/sfx_wood_boundary_soft_0[1-3].wav',
  'only if |vy| > 0.4 m/s, gain -6 dB', '-', '-', -6, '0.92-1.08', 120, 1, 'B new routing (assumes a board/ledge at the line)'),
 ('applause', 'pljesak(snaga)', 'slavniTrenutak, glasPublike("bravo") (internal), stinger pobjeda/pehar timers, UVODI', 'crowd/crowd_applause_{light|enthusiastic|triumphant}_0[1-2].wav',
  'snaga <1.1 light, <1.7 enthusiastic, else triumphant; gain 20*log10(snaga/tier_ref) clamp -6..+2', 'glasPublike("bravo") already calls pljesak(): ONE applause per bravo event',
  'two applause files started within 600 ms (slavniTrenutak calls pljesak AND glasPublike("bravo") which calls pljesak again - play only the stronger)', 0, '0.97-1.03', 600, 2, 'A existing'),
 ('crowd_ooo', 'glasPublike("ooo")', 'povikPublike("Uuuu!"), valPublike("ooo",6) in UVODI trulo', 'crowd/crowd_ooo_0[1-3].wav', 'random, no immediate repeat', '-', 'more than 2 crowd voice clips at once', 0, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_ajme', 'glasPublike("ajme")', 'povikPublike("Ajme…"/"Joo…"/"Ajme majko!")', 'crowd/crowd_ajme_0[1-3].wav', 'prefer transcript match (ajme_02 = "Ajme majko!", ajme_03 contains "Jooooj!")', '-', '-', 0, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_bravo', 'glasPublike("bravo", snaga)', 'povikPublike("Bravo…"/"To je to!"), slavniTrenutak, zavrsiRundu, stinger timers, UVODI', 'crowd/crowd_bravo_0[1-3].wav',
  'bravo_03 contains "To je to!"', 'applause is a separate file triggered by pljesak() inside glasPublike', 'baking applause into bravo (not done)', 0, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_groan', 'glasPublike("stenjanje")', 'valPublike("stenjanje",3) on lost round / ball out', 'crowd/crowd_groan_0[1-3].wav', 'random', '-', '-', 0, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_laugh', 'glasPublike("smijeh")', 'valPublike("smijeh",3) on ball out; povikPublike("Ha-ha-haaa!"/"Ma vidi ga!")', 'crowd/crowd_laugh_0[1-3].wav', 'random', '-', '-', 0, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_murmur', 'glasPublike("zamor") / default', 'side-board hit 30 %, povikPublike(other text e.g. "Ala puše!", "Šjor galeb!", "Lipo, lipo."), valPublike("zamor",3) UVODI trulo', 'crowd/crowd_murmur_0[1-3].wav', 'random, gain -4 dB', '-', '-', -4, '0.95-1.05', 350, 2, 'A existing'),
 ('crowd_wave', 'valPublike(vrsta, koliko)', 'n setTimeouts 170-300 ms apart, each glasPublike + povikPublike', 'files of the vrsta group (short, independent)',
  'play successive DIFFERENT variants; gains -0, -3, -5, -6 dB...; cap at max_concurrent 2 (drop extra steps rather than stack)', 'povikPublike inside each step resolves to the same vrsta normally', 'more than 2 overlapping crowd voice clips', None, '0.95-1.05', 170, 2, 'A existing'),
 ('gull_calm', 'galebZvuk(false)', 'korakAmbijenta() when a gull spawns; UVODI jutro', 'animals/gull/animal_gull_calm_0[1-3].wav', 'random', '-', '-', -4, '0.95-1.06', 4000, 1, 'A existing'),
 ('gull_startled', 'galebZvuk(true)', 'otjerajGaleba() in baci(); UVODI maestral', 'animals/gull/animal_gull_startled_0[1-3].wav + animals/gull/animal_gull_takeoff_wings_0[1-2].wav',
  'call + wings together (wings start 0-60 ms after the call)', 'calls and wings are separate files', '-', -2, '0.95-1.06', 4000, 1, 'A existing'),
 ('cicada', 'cvrcak()', 'korakAmbijenta() every 4-11 s if dobaSad() is podne/popodne; UVODI fjaka', 'ambience/amb_cicada_0[1-3].wav', 'random; skip if one is still playing', '-', '-', -6, '0.95-1.05', 3000, 2, 'A existing'),
 ('distant_voices', 'zamor()', 'korakAmbijenta() every 7-18 s if dobaSad() is zalazak/vecer; UVODI fjaka', 'ambience/amb_cafe_distant_loop.wav',
  'EITHER continuous low layer while doba is zalazak/vecer (recommended, see mix_presets) OR each zamor() call plays a 3-5 s segment from a random offset with 0.6 s fades', '-', 'both modes at once', None, '1.0', 0, 1, 'A existing (behaviour choice)'),
 ('sea_bed', 'sagradiZvuk() zvuk.more + postaviAmbijent(M)', 'built once; level per location/doba', 'ambience/amb_sea_gentle_loop.wav', 'loop; level from mix_presets formula', '-', '-', None, '1.0', 0, 1, 'A existing'),
 ('wind_bed', 'sagradiZvuk() zvuk.vitar + postaviAmbijent(M)', 'built once; level per M.vjetar (x1.35 at night)', 'ambience/amb_wind_maestral_loop.wav', 'loop; level from mix_presets formula', '-', '-', None, '1.0', 0, 1, 'A existing'),
 ('ambience_mute', 'utisajAmbijent()', 'visibilitychange hidden', '(no file) fade sea, wind, cafe, roll loops over 0.6 s', '-', '-', '-', None, '-', 0, 0, 'A existing'),
 ('voice', 'glasLika(lik, txt) <- reci(strana, txt, suigrac)', 'reactions (recenica), fraze, prica (korakBrbljanja), USKLICI, psovke', 'voices/<id>/voice_<id>_{happy|disappointed|disbelief|effort}.wav',
  'EXACT text match only (metadata/voice_text_index.json); chatter without match -> voice_<id>_chat at -4 dB; generic USKLICI reactions and psovke -> no clip', 'crowd and SFX layers continue', 'two character clips at once (max 1 per side, 1.5 s cooldown)', 0, '1.0', 1500, 1, 'A existing + routing'),
 ('voice_chat_teammate', 'glasLika(lik, "brbljanje")', 'korakBrbljanja() teammate chatter (suigrac)', 'voices/<id>/voice_<id>_chat.wav', 'by lik.id', '-', '-', -4, '0.97-1.03', 1200, 1, 'A existing'),
 ('ui_click', 'tapZvuk()', 'every gumb() button (menus, pause, settings, back, language) and menu taps', 'ui/ui_click.wav', '-', '-', '-', 0, '0.98-1.02', 60, 2, 'A existing'),
 ('ui_throw_select', 'tipZvuk()', 'BULANJE/TRULO buttons and keys', 'ui/ui_throw_select.wav', '-', '-', '-', 0, '0.98-1.02', 80, 1, 'A existing'),
 ('ui_perfect', 'tocnoZvuk()', 'sweet-spot release ("TOČNO!")', 'ui/ui_perfect_timing.wav', '-', '-', '-', 0, '1.0', 200, 1, 'A existing'),
 ('ui_measure', 'mjerenjeZvuk()', 'pocniMjerenje(): engine schedules 3 ticks 230 ms apart', 'ui/ui_measure_tick.wav (single tick)', 'play the same file 3x at 0/230/460 ms', '-', 'a file containing three ticks (not supplied on purpose)', 0, '0.98-1.02', 150, 1, 'A existing'),
 ('ui_round', 'puntZvuk(dobar)', 'zavrsiRundu()', 'ui/ui_round_win.wav | ui/ui_round_loss.wav', 'by dobar', 'bravo / groan wave stays separate', '-', 0, '1.0', 500, 1, 'A existing'),
 ('stinger_win', 'stinger("pobjeda")', 'zavrsiRundu() match won (quick game or last cup step)', 'music/stingers/music_match_win.wav', '-', 'engine adds pljesak(1.6) at +260 ms', 'second music cue', 0, '1.0', 0, 1, 'A existing'),
 ('stinger_loss', 'stinger("poraz")', 'zavrsiRundu() match lost', 'music/stingers/music_match_loss.wav', '-', '-', '-', 0, '1.0', 0, 1, 'A existing'),
 ('stinger_stage', 'stinger("postaja")', 'zavrsiRundu() cup stage won', 'music/stingers/music_stage_complete.wav', '-', 'glasPublike("bravo",1.8) from zavrsiRundu', '-', 0, '1.0', 0, 1, 'A existing'),
 ('stinger_trophy', 'stinger("pehar")', 'PEHAR screen "podigni" button', 'music/stingers/music_trophy_win.wav', '-', 'engine adds pljesak(2.0)+glasPublike("bravo",2.0) at +420 ms', 'the second trzaj pair at +900 ms is INSIDE the file - do not also synthesize it', 0, '1.0', 0, 1, 'A existing'),
 ('achievement', 'provjeriZnacke() trzaj chord', 'new badge', 'music/stingers/music_achievement.wav', '-', '-', '-', 0, '1.0', 0, 1, 'A existing'),
 ('intro_titles', 'UVODI[i].dogadjaji title event', 'jutro t=5.2, trulo t=5.6, maestral t=6.0, fjaka t=6.4', 'music/intros/music_intro_{jutro|trulo|maestral|fjaka}.wav',
  'by U.id', 'pljesak/glasPublike("bravo") (+240-320 ms) and povikPublike("Lipo, lipo.") stay runtime layers', '-', 0, '1.0', 0, 1, 'A existing'),
 ('replay', 'korakPonovke(dt)', 'PONOVKA state: korak(..., null) -> impacts silent; kotrljajZvuk follows aktivneLopte() so rolling IS audible', 'existing families',
  'OPTIONAL: pass a replay fx sink and schedule klak/tup/skripa from it at playbackRate 0.85-0.9 and -4 dB', 'live sounds are never replayed: the live round is idle during PONOVKA', 'do not let replay events reach the live crowd triggers (povikPublike in klak)', -4, '0.85-0.9', 45, 3, 'C optional new trigger'),
 ('closeup', 'krupni / korakKrupnog()', 'live collision close-up: physics slowed (tempo 0.5-0.72), events fire once in real time', 'existing families', 'no change needed; optional playbackRate 0.92 while krupni.faza==="udar"', '-', 'no duplicate', 0, '0.92-1.0', 0, 0, 'A existing (no new file)'),
 ('bulin_placement', 'baciBulin() / opponent bulin', 'bulin appears instantly; currently silent', 'sfx/throws/sfx_throw_bulanje_0x.wav + sfx/gravel/sfx_gravel_land_soft_0x.wav', 'throw at -6 dB, land at -8 dB 0.35 s later', '-', '-', -6, '1.05-1.15', 0, 1, 'C optional new trigger'),
 ('cat', 'ambijent.macak* (movement only)', 'NO current trigger', 'animals/cat/animal_cat_meow_0[1-2].wav', 'at most once every 60-120 s, only when the cat stops (macakStoji set) and never during LET', '-', 'meowing per step/animation loop', -4, '0.95-1.05', 60000, 1, 'C optional new trigger'),
]
with open(os.path.join(MD, 'event_mapping.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['event_id', 'html_function_or_branch', 'call_sites_and_condition', 'files', 'selection_rule', 'layer_with', 'never_stack',
                'suggested_gain_db', 'playback_rate_range', 'cooldown_ms', 'max_concurrent', 'status'])
    for row in EV: w.writerow(row)

# ------------------------------------------------------------------ coverage checklist
COV = [
 ('A', 'Sea bed', 'sagradiZvuk() zvuk.more; postaviAmbijent()', 'ambience/amb_sea_gentle_loop.wav', 'covered'),
 ('A', 'Wind bed', 'sagradiZvuk() zvuk.vitar; postaviAmbijent()', 'ambience/amb_wind_maestral_loop.wav', 'covered'),
 ('A', 'Rolling noise bed', 'sagradiZvuk() zvuk.kotrljanje; kotrljajZvuk()', 'sfx/gravel/sfx_gravel_roll_slow_loop.wav; sfx_gravel_roll_fast_loop.wav', 'covered'),
 ('A', 'Ambience fade on hide', 'utisajAmbijent()', '(gain automation only)', 'covered (no file needed)'),
 ('A', 'Bocca-bocca collision', 'klak(j,false)', 'sfx/balls/sfx_ball_collision_*_0[1-3] (9)', 'covered'),
 ('A', 'Bocca-bulin collision', 'klak(j,true)', 'sfx/balls/sfx_bulin_collision_*_0[1-3] (6)', 'covered'),
 ('A', 'Landing / bounce', 'tup(j) ground branch', 'sfx/gravel/sfx_gravel_land_*_0[1-3] (6)', 'covered'),
 ('A', 'Final scrape', 'skripa()', 'sfx/gravel/sfx_gravel_stop_0[1-3] (3)', 'covered'),
 ('A', 'Throw bulanje', 'zamahZvuk("bulanje")', 'sfx/throws/sfx_throw_bulanje_0[1-3]', 'covered'),
 ('A', 'Throw trulo', 'zamahZvuk("trulo") (old version added a 210 Hz sine sweep)', 'sfx/throws/sfx_throw_trulo_0[1-3]', 'covered (sweep replaced by grounded foot+cloth)'),
 ('A', 'Applause', 'pljesak(snaga)', 'crowd/crowd_applause_* (6)', 'covered'),
 ('A', 'Crowd Uuuu', 'glasPublike("ooo")', 'crowd/crowd_ooo_0[1-3]', 'covered'),
 ('A', 'Crowd Ajme / Jooj', 'glasPublike("ajme")', 'crowd/crowd_ajme_0[1-3]', 'covered'),
 ('A', 'Crowd Bravo / To je to', 'glasPublike("bravo")', 'crowd/crowd_bravo_0[1-3]', 'covered (applause kept separate)'),
 ('A', 'Crowd groan (stenjanje)', 'glasPublike("stenjanje")', 'crowd/crowd_groan_0[1-3]', 'covered'),
 ('A', 'Crowd laugh (smijeh)', 'glasPublike("smijeh")', 'crowd/crowd_laugh_0[1-3]', 'covered'),
 ('A', 'Crowd murmur (zamor/default)', 'glasPublike("zamor")', 'crowd/crowd_murmur_0[1-3]', 'covered'),
 ('A', 'Crowd wave', 'valPublike()', 'successive short clips of the group', 'covered by routing (no baked waves)'),
 ('A', 'Single spectator call', 'povikPublike(txt) -> vrstaPovika', 'group by vrstaPovika (see event_mapping)', 'covered'),
 ('A', 'Gull call (calm)', 'galebZvuk(false)', 'animals/gull/animal_gull_calm_0[1-3]', 'covered (procedural, see provenance)'),
 ('A', 'Gull alarm + take-off', 'galebZvuk(true)', 'animals/gull/animal_gull_startled_0[1-3]; animal_gull_takeoff_wings_0[1-2]', 'covered (procedural)'),
 ('A', 'Cicadas', 'cvrcak()', 'ambience/amb_cicada_0[1-3]', 'covered (procedural)'),
 ('A', 'Distant voices', 'zamor()', 'ambience/amb_cafe_distant_loop.wav', 'covered (continuous or segmented, see mix_presets)'),
 ('A', 'Character speech babble', 'glasLika(lik, txt) via reci()', 'voices/<id>/voice_<id>_* (40)', 'covered with exact-text routing'),
 ('A', 'Teammate chatter', 'glasLika(lik,"brbljanje")', 'voices/<id>/voice_<id>_chat.wav', 'covered'),
 ('A', 'Button tap', 'tapZvuk()', 'ui/ui_click.wav', 'covered (pause/settings/back/language reuse it)'),
 ('A', 'Throw-type select', 'tipZvuk()', 'ui/ui_throw_select.wav', 'covered'),
 ('A', 'Perfect timing', 'tocnoZvuk()', 'ui/ui_perfect_timing.wav', 'covered'),
 ('A', 'Measuring', 'mjerenjeZvuk() (3 ticks)', 'ui/ui_measure_tick.wav (one tick, played 3x)', 'covered'),
 ('A', 'Round won / lost', 'puntZvuk(true|false)', 'ui/ui_round_win.wav; ui/ui_round_loss.wav', 'covered'),
 ('A', 'Match won', 'stinger("pobjeda")', 'music/stingers/music_match_win.wav', 'covered'),
 ('A', 'Match lost', 'stinger("poraz")', 'music/stingers/music_match_loss.wav', 'covered'),
 ('A', 'Cup stage won', 'stinger("postaja")', 'music/stingers/music_stage_complete.wav', 'covered'),
 ('A', 'Trophy', 'stinger("pehar")', 'music/stingers/music_trophy_win.wav', 'covered'),
 ('A', 'Achievement / badge', 'provjeriZnacke() trzaj chord', 'music/stingers/music_achievement.wav', 'covered'),
 ('A', 'Intro 1 JUTRO title chord', 'UVODI jutro t=5.2', 'music/intros/music_intro_jutro.wav', 'covered'),
 ('A', 'Intro 2 TRULO title chord', 'UVODI trulo t=5.6', 'music/intros/music_intro_trulo.wav', 'covered'),
 ('A', 'Intro 3 MAESTRAL title chord', 'UVODI maestral t=6.0', 'music/intros/music_intro_maestral.wav', 'covered'),
 ('A', 'Intro 4 FJAKA title chord', 'UVODI fjaka t=6.4', 'music/intros/music_intro_fjaka.wav', 'covered'),
 ('A', 'Intro physical events', 'UVODI zamahZvuk/klak/galeb/cvrcak/zamor/valPublike/povikPublike; korak(uvod.lopte, dt, fx)', 'reuse physical, crowd, animal families', 'covered by reuse'),
 ('A', 'Close-up window', 'krupni (slowed live physics)', 'reuse; sounds fire once', 'covered (no new file)'),
 ('A', 'Master mute / limiter', 'prebaciZvuk(); DynamicsCompressor in sagradiZvuk()', '(engine)', 'unchanged'),
 ('B', 'Side board impact', 'korak() |x|>X_ZID-r, z<=VIS_ZIDA else-branch (reuses tup(0.5))', 'sfx/boundaries/sfx_wood_boundary_* (6)', 'NEW FILES - replace tup(0.5) there'),
 ('B', 'Rear board impact', 'korak() y>Y_KRAJ-r, z<=VIS_ZIDA else-branch (silent)', 'sfx/boundaries/sfx_wood_boundary_* (same family)', 'NEW FILES - add a call'),
 ('B', 'Front sill bounce', 'korak() y<Y_PRAG+r clamp (silent)', 'sfx/boundaries/sfx_wood_boundary_soft_* at -6 dB', 'routing only; assumes a board at the line'),
 ('B', 'Rolling during intros', 'kotrljajZvuk only runs in LET/PONOVKA; UVOD balls roll silently', 'sfx/gravel/sfx_gravel_roll_*_loop', 'routing only (optional)'),
 ('C', 'Replay impacts', 'korakPonovke: korak(..., null) silent impacts; rolling already audible', 'reuse families at rate 0.85-0.9, -4 dB', 'optional new trigger, no new files'),
 ('C', 'Bulin placement', 'baciBulin / opponent bulin (silent, instantaneous)', 'reuse throw + gravel_land_soft', 'optional new trigger'),
 ('C', 'Cat meow', 'ambijent.macak* movement only', 'animals/cat/animal_cat_meow_0[1-2] (OPTIONAL)', 'optional new trigger, rare'),
 ('-', 'Ball out over the board ("VANKA")', 'korak(): b.vanka=true, physics stops at the board; crowd reacts', 'none (crowd groan/laugh already plays)', 'NO splash: the ball is never simulated reaching water'),
 ('-', 'Out-of-bounds bulin', 'sljedeciPotez() pBulinVanka message (+ optional psovka voice)', 'voice routing only', 'no new file'),
]
with open(os.path.join(MD, 'coverage_checklist.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['class (A=replacement, B=missing sound for existing event, C=optional new trigger)', 'event', 'html_source', 'files', 'status'])
    for row in COV: w.writerow(row)

# ------------------------------------------------------------------ provenance
with open(os.path.join(MD, 'provenance.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['file', 'production_method', 'external_inputs', 'licence_of_inputs', 'attribution_required', 'notes'])
    for e in sorted(entries, key=lambda e: e['file']):
        m = e.get('method', '')
        if 'Kokoro' in m:
            ext = 'Kokoro-82M v1.0 ONNX model + voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx release model-files-v1.0); kokoro-onnx 0.6.1'
            lic = 'Kokoro-82M weights: Apache-2.0 (hexgrad); kokoro-onnx: MIT'
            att = 'not required for audio output; Apache-2.0 NOTICE recommended if the model itself is redistributed (it is not)'
            note = 'synthetic speech; stock voice style vectors blended; no voice cloning; no real person imitated'
        else:
            ext, lic, att, note = 'none', 'n/a', 'no', 'original procedural audio written for this pack'
        if '/cat/' in e['file'] or '/gull/animal_gull_c' in e['file'] or 'startled' in e['file'] or 'cicada' in e['file']:
            note += '; procedural approximation of an animal sound, not a field recording'
        w.writerow([e['file'], m, ext, lic, att, note])
    w.writerow(['(rejected) tuxpaint-stamps-default seagull.ogg / blackcat.ogg', 'considered as source', 'Ubuntu package tuxpaint-stamps-default 2022.06.04',
                'GPL-2', '-', 'NOT USED: GPL-2 terms for a game asset and low quality (32 kbit/s, cat at 8 kHz)'])
    w.writerow(['(unavailable) Freesound, Wikimedia Commons, xeno-canto, archive.org, HuggingFace', '-', '-', '-', '-',
                'blocked by this environment\'s network policy (HTTP 403 at the proxy); no recordings could be licensed'])

# ------------------------------------------------------------------ validation report
L = []
A = L.append
A('BOĆE NA RIVI - validation report'); A('=' * 34); A(f'date: {datetime.date.today().isoformat()}'); A('')
files = VAL['files']; bad = {k: v['issues'] for k, v in files.items() if v['issues']}
A(f'Master files checked: {len(files)}  (expected 133)')
A(f'Files with open technical issues: {len(bad)}')
for k, v in bad.items(): A(f'  {k}: {v}')
A('')
A('Checks applied to every master (all passed unless listed above):')
A('  - RIFF/WAVE header parsed independently by libsndfile and Python wave; 48000 Hz, PCM 24-bit, frame counts agree')
A('  - no NaN/Inf; no samples at full scale; true peak (4x oversampled) <= -0.5 dBTP (max found: %.2f dBTP)' % max(v['true_peak_dbtp'] for v in files.values()))
A('  - DC offset < 0.001 (max found: %.2e)' % max(v['dc_offset'] for v in files.values()))
A('  - first/last sample < 0.002 (faded, click-free) for non-loop files; lead silence <= 10 ms before the first event')
A('  - duration inside the suggested range per family (see metadata/audio_manifest.json for each duration)')
A('  - channel layout: mono for localized SFX, voices, gull, cat, UI clicks; stereo for ambience, crowd, music')
A('  - stereo files: L/R correlation >= 0 and mono-sum loss > -4.5 dB')
A('  - energy above 8 kHz < 25 % (cicadas exempt; phone-speaker harshness guard)')
A('  - numbered variants: md5 differ and max normalised cross-correlation < 0.95')
A('')
A('Stereo mono-compatibility:')
for k, v in sorted(files.items()):
    if v['channels'] == 2: A(f"  {k:52s} corr {v['lr_correlation']:+.2f}  mono-sum {v['mono_sum_loss_db']:+.2f} dB")
A('')
A('Loop seams (wrap-step vs 99.9th percentile of all sample steps; spectral flux at seam vs 95th percentile):')
for k, v in sorted(files.items()):
    if v['loop']:
        s = v['seam']; A(f"  {k:48s} wrap {s['wrap_step']:.5f} <= p99.9 {s['step_p999']:.5f}; flux {s['seam_flux']:.3f} <= p95 {s['flux_p95']:.3f}; ok={s['ok']}")
A('  Loops were built by an equal-power overlap of the tail onto the head; loop points are sample 0 and the last sample.')
A('  MP3 derivatives are NOT sample-accurate loops (encoder delay/padding) - use the WAV masters for looping.')
A('')
A('Variant distinctness (max normalised cross-correlation inside each numbered group, 1.0 = identical):')
for g, v in sorted(VAL['variants'].items()): A(f"  {g:48s} n={v['n']}  max xcorr {v['max_xcorr']}")
A('')
A('Timbre separation (spectral centroid; attack = first 30 ms):')
for g, t in VAL['timbre'].items():
    A(f"  {g:14s} attack centroid {t['attack_centroid']['mean']:7.0f} Hz  whole {t['centroid']['mean']:7.0f} Hz  rms {t['rms']['mean']:6.1f} dBFS  dur {t['duration']['mean']:.2f} s")
A('  -> ball vs bulin: bulin attack centroid ~5.1-5.4 kHz vs ball 1.3-2.9 kHz (lighter, brighter, shorter).')
A('  -> soft vs hard differ in contact time (Hertz pulse), excited upper modes, click and gravel crunch, not only level.')
A('')
A('Character voices - ASR round trip (Whisper small multilingual via sherpa-onnx, language=hr):')
for e in sorted(entries, key=lambda e: e['file']):
    if e['file'].startswith('voices/') and e.get('transcript'):
        A(f"  {e['file']:44s} \"{e['transcript']}\" -> heard \"{e['asr_heard']}\" (CER {e['asr_cer']:.2f})")
A('  CER is computed after removing accents/punctuation and elongations. Remaining non-zero scores are spelling-')
A('  level ("BOOM" for "Bum!", "HEM" for "Hm.", word joins such as "Rukami je") - no clip was heard as different words.')
A('  Chat clips are a nonverbal "mhm" (no lexical content); ASR is not applicable.')
A('')
A('Character identity consistency (speaker-embedding cosine, wespeaker ResNet34; English-trained, used as a proxy):')
for c, v in SPK['within_mean_cosine'].items(): A(f'  within {c:6s} {v:.2f}')
cross = SPK['cross_mean_cosine']
A(f"  between characters: mean {sum(cross.values())/len(cross):.2f}, max {max(cross.values()):.2f} ({max(cross, key=cross.get)})")
A('  -> every character is more similar to itself (min %.2f) than to any other character (max %.2f).' % (min(SPK['within_mean_cosine'].values()), max(cross.values())))
A('')
A('Crowd clips - ASR (mono sum):')
for e in sorted(entries, key=lambda e: e['file']):
    if e['file'].startswith('crowd/crowd_') and 'applause' not in e['file']:
        A(f"  {e['file']:30s} intended: {e['transcript'][:70]}  | heard: {e['asr_heard']}")
A('  bravo/To je to are recognised verbatim. Pure vowels (Uuuu, groans) make Whisper hallucinate words; these were')
A('  checked by spectrogram instead (sustained vowel formants, no consonant bursts). Kokoro was fed phonemes only,')
A('  so it cannot introduce words that were not in its input.')
if cafe_asr:
    A('')
    A('Cafe loop intelligibility (ASR on 6 s windows boosted +18 dB): ' + ' | '.join(cafe_asr[-1]['asr_windows']))
    A('  -> no source sentence is recovered; conversation is distant and unintelligible.')
A('')
A('LISTENING / AUDITION LIMITS - read this')
A('  The production environment had no audio output. No file was auditioned by ear. Review used: spectrogram')
A('  contact sheets of every family, objective metrics above, ASR and speaker-embedding checks. Subjective')
A('  qualities (naturalness of procedural gulls/cat/applause, voice warmth, mix balance on phones) are UNVERIFIED')
A('  by listening and should be auditioned before shipping. iOS/Safari playback was NOT tested.')
A('')
A('Not delivered / not claimed:')
A('  - No field recordings: gull, cicada, cat and applause are procedural models, labelled as such.')
A('  - No German/English voice duplicates (by design: Dalmatian lines stay Croatian).')
A('  - The HTML game was not modified and the files were not integrated or tested in the engine.')
open(os.path.join(MD, 'validation_report.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ mix presets
def sea_db(noc): return round(20*__import__('math').log10((0.055 if noc else 0.075)/0.075), 2)
def wind_db(v, noc):
    import math
    return round(20*math.log10((0.012+v*0.075)*(1.35 if noc else 1)/(0.012+0.86*0.075)), 2)
LOC = [('trogir', 'jutro', 0.35), ('vis', 'podne', 0.52), ('makarska', 'popodne', 0.72), ('hvar', 'zalazak', 0.86), ('split', 'vecer', 0.50)]
BYDOBA = {'jutro': dict(cicada=False, cafe=None, gull_rate=1.2), 'podne': dict(cicada=True, cafe=None, gull_rate=1.0),
          'popodne': dict(cicada=True, cafe=None, gull_rate=1.0), 'zalazak': dict(cicada=False, cafe=-6.0, gull_rate=0.8),
          'vecer': dict(cicada=False, cafe=-3.0, gull_rate=0.5)}
presets = {}
for loc, doba, v in LOC:
    noc = doba == 'vecer'
    presets[f'{loc}_{doba}'] = {
        'location': loc, 'default_doba': doba, 'vjetar': v,
        'sea_loop_db': sea_db(noc), 'wind_loop_db': wind_db(v, noc),
        'cafe_loop_db': BYDOBA[doba]['cafe'], 'cicada_phrases': BYDOBA[doba]['cicada'],
        'gull_spawn_rate_multiplier': BYDOBA[doba]['gull_rate']}
mix = {
 'note': 'Recommendations only. dB values are relative to each file as delivered (files keep intended relative levels: '
         'quiet beds are quiet). Not verified in the engine.',
 'buses_db': {'physical_sfx': 0.0, 'rolling': -5.0, 'crowd': -3.0, 'voices': -2.0, 'ambience_beds': -6.0,
              'ambience_events (cicada, gull, cafe)': -4.0, 'ui': -4.0, 'music': -3.0},
 'source_reference': 'GLASNOCA = { udarci 1.0, publika 1.0, kotrljanje 0.55, ambijent 0.22 }; DynamicsCompressor -14 dB / 6:1 kept on master',
 'ducking': {'ambience_beds_under_voice_or_stinger_db': -4.0, 'attack_ms': 40, 'release_ms': 400},
 'location_presets': presets,
 'level_formulas': {
   'sea_loop_db': '20*log10((noc ? 0.055 : 0.075) / 0.075)  (same ratio as postaviAmbijent)',
   'wind_loop_db': '20*log10((0.012 + M.vjetar*0.075) * (noc ? 1.35 : 1) / (0.012 + 0.86*0.075))  (Hvar day = 0 dB)',
   'noc': "dobaSad() === 'vecer'"},
 'day_night_override': {
   'rule': "Always key the preset on dobaSad(), not M.doba: nacinDana 'noc' -> 'vecer' preset at any location (night wind x1.35, "
           "cafe on, no cicadas); 'dan' -> M.doba, except Split which becomes 'popodne' (cicadas on, cafe off).",
   'retrigger': 'postaviAmbijent() currently runs only when zvucnoMjesto != igra.mjestoIdx; when nacinDana changes (menu, '
                'UVODI set/restore) the integration should call it again so the beds follow the manual setting.',
   'derived_presets': {f'{loc}_{d}': {'sea_loop_db': sea_db(d == 'vecer'), 'wind_loop_db': wind_db(v, d == 'vecer'),
                       'cafe_loop_db': BYDOBA[d]['cafe'], 'cicada_phrases': BYDOBA[d]['cicada']}
                       for loc, _, v in LOC for d in ('popodne', 'vecer', 'jutro', 'podne', 'zalazak')}},
 'cafe_mode': {'recommended': 'continuous low layer while dobaSad() is zalazak/vecer, crossfaded in/out over 2 s',
               'alternative': 'segmented: on each zamor() call play 3-5 s from a random offset of amb_cafe_distant_loop.wav with 0.6 s fades'},
 'wet_court': 'Do not add rain: a wet court in the visuals does not imply rainfall.',
 'concurrency_limits': {'collisions (ball+bulin)': 3, 'gravel_land': 3, 'gravel_stop': 2, 'wood_boundary': 2, 'applause': 2,
                        'crowd_voice_clips': 2, 'character_voices': 1, 'gull': 1, 'cicada': 2, 'ui_click': 2, 'music': 1},
 'anti_machine_gun': 'Per ball pair: ignore klak() repeats within 45 ms; per ball: ignore tup() within 35 ms; never pick the same variant twice in a row; '
                     'random rate within the safe range per hit.',
 'layering': {
   'play_together': ['bravo + applause (applause triggered by pljesak() inside glasPublike)', 'gull startled call + wings',
                     'stinger + engine-scheduled applause/bravo', 'throw + gravel land + roll loops + stop scrape'],
   'never_stack': ['two applause files from one celebratory event (slavniTrenutak calls pljesak AND glasPublike("bravo") -> keep the stronger)',
                   'tup(0.5) and wood_boundary in the side-board branch', 'a 3-tick measure file (only single tick supplied)',
                   'music cues with each other', 'more than one character voice per side']},
 'rolling_crossfade': {'slow_band_mps': [0.12, 2.5], 'fast_band_mps': [1.5, 9.0], 'crossfade': 'equal power between 1.5 and 2.5 m/s',
                       'gain': 'existing kotrljajZvuk target min(0.20, 0.03+v*0.035) as linear gain on the bus',
                       'rate': '0.85 + min(v, 9)*0.045 (0.85-1.25)', 'smoothing': 'setTargetAtTime 0.05 s gain, 0.1 s rate'},
}
json.dump(mix, open(os.path.join(MD, 'mix_presets.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(VOX, open(os.path.join(MD, 'voice_identities.json'), 'w'), ensure_ascii=False, indent=1)
print('metadata written:', sorted(os.listdir(MD)))
