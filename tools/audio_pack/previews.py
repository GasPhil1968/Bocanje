"""Preview mixes assembled ONLY from delivered master files (no extra synthesis)."""
import sys, os, json
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from dsp import SR, undb, fade, norm_peak, pan
ROOT = sys.argv[1]
idx = []

def load(rel):
    x, sr = sf.read(os.path.join(ROOT, rel), always_2d=True)
    assert sr == SR
    if x.shape[1] == 1: x = np.repeat(x, 2, axis=1)*np.sqrt(0.5)   # centred, equal power
    return x

class Mix:
    def __init__(self, name, dur):
        self.name = name; self.y = np.zeros((int(dur*SR), 2)); self.log = []
    def add(self, rel, t, gain_db=0.0, note=None, length=None, fade_out=None, rate=1.0, log=True):
        x = load(rel)
        if rate != 1.0:
            pos = np.arange(0, len(x)-1, rate); x = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in (0, 1)], 1)
        if length: x = x[:int(length*SR)]
        if fade_out: x = fade(x, 0.0, fade_out)
        i = int(t*SR); m = min(len(x), len(self.y)-i)
        self.y[i:i+m] += x[:m]*undb(gain_db)
        if log: self.log.append((t, rel, gain_db, note or ''))
    def loop(self, rel, t0, t1, gain_db, env=None, note=None):
        x = load(rel); n = int((t1-t0)*SR)
        reps = int(np.ceil(n/len(x)))+1
        L = np.concatenate([x]*reps)[:n]
        if env is not None: L = L*env(np.arange(n)/SR)[:, None]
        L = fade(L, 0.3, 0.6)
        i = int(t0*SR); self.y[i:i+n] += L*undb(gain_db)
        self.log.append((t0, rel, gain_db, (note or '') + f' (looped {t0:.1f}-{t1:.1f} s)'))
    def write(self):
        y = norm_peak(self.y, -1.0) if np.max(np.abs(self.y)) > undb(-1) else self.y
        path = os.path.join(ROOT, 'previews', self.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sf.write(path, y.astype(np.float32), SR, subtype='PCM_24')
        idx.append((self.name, len(y)/SR, sorted(self.log)))

# ---------------------------------------------------------------- gameplay (Makarska afternoon preset)
g = Mix('preview_gameplay.wav', 27.0)
g.loop('ambience/amb_sea_gentle_loop.wav', 0, 27, -6, note='sea bed, preset makarska_popodne')
g.loop('ambience/amb_wind_maestral_loop.wav', 0, 27, -9, note='maestral bed (vjetar 0.72)')
g.add('ambience/amb_cicada_01.wav', 0.8, -8, 'cvrcak()')
g.add('animals/gull/animal_gull_calm_01.wav', 2.2, -8, 'galebZvuk(false) - gull arrives')
g.add('voices/mare/voice_mare_chat.wav', 3.4, -3, 'glasLika chat (opponent Teta Mare)')
g.add('sfx/throws/sfx_throw_bulanje_01.wav', 5.0, 0, 'zamahZvuk("bulanje")')
g.add('animals/gull/animal_gull_startled_02.wav', 5.15, -6, 'galebZvuk(true) - otjerajGaleba()')
g.add('animals/gull/animal_gull_takeoff_wings_01.wav', 5.2, -6, 'galebZvuk(true) wings')
g.add('sfx/gravel/sfx_gravel_land_hard_01.wav', 5.75, -2, 'tup(0.55) first landing')
g.add('sfx/gravel/sfx_gravel_land_soft_02.wav', 6.05, -9, 'tup(0.17) small bounce, reduced gain')
# rolling: crossfade fast->slow loop as the ball decelerates (as documented in event_mapping)
roll_t0, roll_t1 = 6.1, 9.0
def fast_env(t): return np.clip(1 - t/1.6, 0, 1)**0.5
def slow_env(t): return np.clip(t/1.2, 0, 1)**0.5*np.clip((roll_t1-roll_t0-t)/1.4, 0, 1)
g.loop('sfx/gravel/sfx_gravel_roll_fast_loop.wav', roll_t0, roll_t1, -6, fast_env, 'kotrljajZvuk(v) fast loop, v falling')
g.loop('sfx/gravel/sfx_gravel_roll_slow_loop.wav', roll_t0, roll_t1, -3, slow_env, 'kotrljajZvuk(v) slow loop, equal-power crossfade')
g.add('sfx/gravel/sfx_gravel_stop_01.wav', 8.95, 0, 'skripa() ball settles')
g.add('voices/jure/voice_jure_happy.wav', 9.5, -2, 'reci("ti", "Vidiš to?! Vidiš?!") exact-text clip')
g.add('crowd/crowd_murmur_02.wav', 10.2, -6, 'glasPublike("zamor")')
g.add('sfx/throws/sfx_throw_trulo_02.wav', 12.0, 0, 'zamahZvuk("trulo")')
g.add('sfx/gravel/sfx_gravel_land_hard_03.wav', 12.55, -3, 'tup() trulo touches down short')
g.loop('sfx/gravel/sfx_gravel_roll_fast_loop.wav', 12.6, 13.25, -5, note='fast roll into the pack')
g.add('sfx/balls/sfx_ball_collision_hard_02.wav', 13.2, 0, 'klak(0.8, false) - trulo hits a bocca')
g.add('sfx/balls/sfx_bulin_collision_soft_01.wav', 13.42, -2, 'klak(0.2, true) - knocked bocca nudges the bulin')
g.add('sfx/boundaries/sfx_wood_boundary_hard_01.wav', 13.95, -1, 'side board (new routing for existing branch)')
g.add('crowd/crowd_ooo_02.wav', 13.5, -2, 'povikPublike("Uuuu!") -> glasPublike("ooo")')
g.add('sfx/gravel/sfx_gravel_stop_03.wav', 14.6, 0, 'skripa()')
g.add('voices/jure/voice_jure_effort.wav', 14.3, -2, 'reci: "Rušim! Rušiiim!" exact-text clip')
g.add('crowd/crowd_applause_enthusiastic_01.wav', 14.9, -3, 'pljesak(1.4) - slavniTrenutak')
g.add('crowd/crowd_bravo_02.wav', 15.0, -2, 'glasPublike("bravo", 1.4) (no applause baked in)')
g.add('voices/mare/voice_mare_disbelief.wav', 17.6, -2, 'reci("pro", "Jooj, u more!")')
g.add('ui/ui_measure_tick.wav', 19.5, 0, 'mjerenjeZvuk() tick 1/3')
g.add('ui/ui_measure_tick.wav', 19.73, 0, 'tick 2/3 (engine schedules 3 x 230 ms)')
g.add('ui/ui_measure_tick.wav', 19.96, 0, 'tick 3/3')
g.add('ui/ui_round_win.wav', 21.0, -1, 'puntZvuk(true)')
g.add('crowd/crowd_bravo_01.wav', 21.05, -3, 'glasPublike("bravo") at round end')
g.add('crowd/crowd_applause_light_01.wav', 21.1, -4, 'pljesak(1.0)')
g.add('voices/mare/voice_mare_disappointed.wav', 22.4, -2, 'reci("pro", "Ajme meni jadnoj…")')
g.add('crowd/crowd_laugh_02.wav', 23.6, -5, 'valPublike("smijeh") single clip')
g.write()

# ---------------------------------------------------------------- characters
ORDER = ['sime', 'jure', 'kate', 'ante', 'vicko', 'mare', 'duje', 'frane']
KINDS = ['chat', 'happy', 'disappointed', 'disbelief', 'effort']
c = Mix('preview_characters.wav', 8*5*2.4)
t = 0.3
for cid in ORDER:
    for k in KINDS:
        rel = f'voices/{cid}/voice_{cid}_{k}.wav'
        d = sf.info(os.path.join(ROOT, rel)).duration
        c.add(rel, t, 0, f'{cid} / {k}'); t += d + 0.35
    t += 0.8
c.y = c.y[:int((t+0.2)*SR)]
c.write()

# ---------------------------------------------------------------- UI and stingers
u = Mix('preview_ui_and_stingers.wav', 40)
t = 0.3
for rel, rep in [('ui/ui_click.wav', 3), ('ui/ui_throw_select.wav', 2), ('ui/ui_perfect_timing.wav', 1),
                 ('ui/ui_measure_tick.wav', 3), ('ui/ui_round_win.wav', 1), ('ui/ui_round_loss.wav', 1)]:
    for k in range(rep):
        u.add(rel, t, 0, f'{os.path.basename(rel)}' + (f' ({k+1}/{rep}, 230 ms apart as mjerenjeZvuk)' if 'tick' in rel else f' ({k+1}/{rep})' if rep > 1 else ''))
        t += 0.23 if 'tick' in rel else (0.35 if rep > 1 else 0)
    t += sf.info(os.path.join(ROOT, rel)).duration + 0.6
t += 0.4
for rel in ['music/stingers/music_achievement.wav', 'music/stingers/music_stage_complete.wav', 'music/stingers/music_match_win.wav',
            'music/stingers/music_match_loss.wav', 'music/stingers/music_trophy_win.wav', 'music/intros/music_intro_jutro.wav',
            'music/intros/music_intro_trulo.wav', 'music/intros/music_intro_maestral.wav', 'music/intros/music_intro_fjaka.wav']:
    u.add(rel, t, 0, os.path.basename(rel)); t += sf.info(os.path.join(ROOT, rel)).duration + 0.8
u.y = u.y[:int(t*SR)]
u.write()

with open(os.path.join(ROOT, 'previews', 'preview_index.txt'), 'w', encoding='utf-8') as f:
    f.write('BOĆE NA RIVI - preview index\n')
    f.write('Previews are assembled only from the delivered master files (gains in dB relative to file level).\n')
    f.write('They are for review and do NOT prove integration into the HTML game.\n\n')
    for name, dur, log in idx:
        f.write(f'{name}  ({dur:.2f} s)\n')
        for tt, rel, gdb, note in log:
            f.write(f'  {int(tt//60):02d}:{tt%60:06.3f}  {rel:58s} {gdb:+5.1f} dB  {note}\n')
        f.write('\n')
print(open(os.path.join(ROOT, 'previews', 'preview_index.txt')).read()[:1500])
