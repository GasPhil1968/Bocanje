"""Validate rendered WAVs and write sfx_manifest.json: python3 package.py <out_dir>"""
import sys, os, json, hashlib, subprocess
import numpy as np, soundfile as sf
from core import true_peak, loud_m, db, SR

COOLDOWN = {'voice': 4.0, 'pigeon': 1.5, 'result': 0.0, 'police': 0.0, 'cups': 0.0, 'money': 0.15, 'ui': 0.05,
            'powerup': 0.3, 'escape': 0.0, 'tv': 0.0, 'ambience': 2.0}
SPECIAL_CD = {'saner_wipe_forehead': 6.0, 'saner_nervous': 6.0, 'saner_chuckle': 5.0, 'saner_angry': 5.0,
              'saner_annoyed': 5.0, 'levat_reaction': 8.0, 'audience_murmur': 6.0, 'saner_poke': 1.2,
              'cup_slide': 0.0, 'pigeon_wings': 0.0, 'cup_set_down': 0.0, 'run_step': 0.0, 'police_step': 0.0}


def main(out):
    ent = json.load(open(os.path.join(out, '_render.json')))
    sounds, problems, hashes = [], [], {}
    for e in ent:
        vs = []
        for f in e['files']:
            p = os.path.join(out, 'audio', 'sfx', f)
            info = sf.info(p)
            x, sr = sf.read(p, dtype='float64')
            # independent decoder check
            pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', p],
                                           capture_output=True, text=True).stdout)['streams'][0]
            dur = len(x) / sr
            mono = x if x.ndim == 1 else x.mean(1)
            rms = np.sqrt(np.mean(mono ** 2))
            tp = db(true_peak(x)); sp = db(np.max(np.abs(x)))
            lead = int(np.argmax(np.abs(mono) > np.max(np.abs(mono)) * 10 ** (-50 / 20))) / sr   # first audible sample
            h = hashlib.sha1(open(p, 'rb').read()[44:]).hexdigest()
            lo, hi = e['duration_range']
            chk = {
                'pcm16_44k1': info.subtype == 'PCM_16' and sr == 44100 and pr['codec_name'] == 'pcm_s16le' and int(pr['sample_rate']) == 44100,
                'audible': db(rms) > -60 and len(x) > 0,
                'peak_le_-1dBFS': sp <= -1.0 and tp <= -1.0,
                'no_clipping': np.max(np.abs(x)) < 0.999,
                'duration_in_range': lo - 1e-3 <= dur <= hi + 1e-3,
                'lead_silence_lt_5ms': lead < 0.005,
                'clean_edges': abs(mono[0]) < 0.01 and abs(mono[-1]) < 0.01,
                'unique': h not in hashes,
            }
            hashes[h] = f
            for k, ok in chk.items():
                if not ok:
                    problems.append(f'{f}: {k}')
            vs.append(dict(file=f'audio/sfx/{f}', duration_s=round(dur, 3), channels=info.channels,
                           sample_peak_dbfs=round(sp, 2), true_peak_dbtp=round(tp, 2),
                           max_momentary_lufs=round(loud_m(x), 1)))
        cd = SPECIAL_CD.get(e['id'], COOLDOWN[e['category']])
        sounds.append(dict(id=e['id'], category=e['category'], event=e['event'], recommended_gain=e['gain'],
                           selection='random_no_immediate_repeat' if len(vs) > 1 else 'single',
                           min_retrigger_s=cd, variants=vs))
    man = dict(
        pack='TRI FILDŽANA – complete SFX', version='1.0.0',
        format=dict(container='WAV', encoding='PCM 16-bit', sample_rate_hz=44100,
                    peak_ceiling='-1 dBFS true peak', mono='Foley/voices/one-shots', stereo='musical stings, audience'),
        source=('All sounds are procedurally synthesized from physical / source-filter models '
                '(modal ceramics, wood and metal; friction and fabric noise models; Karplus-Strong strings; '
                'membrane drums; glottal-pulse voice model). No recorded Foley or voice recordings are included.'),
        gain_notes=('Files are pre-balanced (cups/fabric quieter than results/police). recommended_gain is a linear '
                    'multiplier for the playback GainNode, applied before the game master gain (currently 0.55).'),
        sound_count=len(sounds), file_count=sum(len(s['variants']) for s in sounds),
        total_duration_s=round(sum(v['duration_s'] for s in sounds for v in s['variants']), 2),
        sounds=sounds)
    json.dump(man, open(os.path.join(out, 'sfx_manifest.json'), 'w'), indent=2, ensure_ascii=False)
    # manifest <-> disk consistency
    on_disk = sorted(os.listdir(os.path.join(out, 'audio', 'sfx')))
    listed = sorted(os.path.basename(v['file']) for s in sounds for v in s['variants'])
    if on_disk != listed:
        problems.append(f'manifest/disk mismatch: {set(on_disk) ^ set(listed)}')
    print(f"{man['sound_count']} sounds, {man['file_count']} files, {man['total_duration_s']} s")
    print('PROBLEMS:', problems or 'none')
    return problems


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
