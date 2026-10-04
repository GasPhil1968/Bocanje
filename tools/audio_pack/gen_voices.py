"""Batch 2a: eight character voice identities x five reaction types (Kokoro-82M, phoneme input)."""
import sys, os, json, re, unicodedata
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import *
from hrtts import say, asr, ipa
import meta, parselmouth

B = 'voices'
KOKORO = ('Kokoro-82M v1.0 neural TTS (hexgrad, Apache-2.0) run locally via kokoro-onnx 0.6.1 (MIT); '
          'model+voice files from github.com/thewh1teagle/kokoro-onnx release model-files-v1.0; '
          'Croatian fed as hand-written IPA (lib/hrtts.py); voice = fixed blend of stock style vectors, '
          'not a clone of any real person; rendered 24 kHz, resampled to 48 kHz (content band-limited to 12 kHz)')

# Frozen identities: blend of stock style vectors + tempo + subtle formant-preserving pitch offset.
VOICES = {
  'sime':  dict(mix=[('bm_george', .70), ('im_nicola', .30)], speed=1.0, semis=-1.0, gain=-1.0,
                desc='elderly, warm, patient, understated'),
  'jure':  dict(mix=[('em_alex', .70), ('am_puck', .30)],     speed=1.10, semis=0.0, gain=0.5,
                desc='young adult, energetic, competitive'),
  'kate':  dict(mix=[('pf_dora', .50), ('bf_lily', .50)],     speed=.95, semis=-0.5, gain=-1.5,
                desc='elderly woman, precise, composed, dry humour'),
  'ante':  dict(mix=[('am_onyx', .60), ('pm_santa', .40)],    speed=.98, semis=0.0, gain=0.0,
                desc='weathered fisherman, grounded, unhurried'),
  'vicko': dict(mix=[('hm_psi', .60), ('am_adam', .40)],     speed=1.04, semis=0.0, gain=-0.5,
                desc='meticulous, restrained, thoughtful'),
  'mare':  dict(mix=[('if_sara', .55), ('hf_alpha', .45)],    speed=1.06, semis=0.0, gain=1.0,
                desc='lively, confident, highly expressive'),
  'duje':  dict(mix=[('am_fenrir', .50), ('am_echo', .50)],   speed=.92, semis=-3.0, gain=1.0,
                desc='powerful, terse, low-key and emphatic'),
  'frane': dict(mix=[('am_eric', .70), ('am_liam', .30)],     speed=1.13, semis=0.0, gain=0.5,
                desc='eager newcomer, restless, occasionally overconfident'),
}
ORDER = ['sime', 'jure', 'kate', 'ante', 'vicko', 'mare', 'duje', 'frane']

# (category) -> (transcript or None for nonverbal, phoneme override, source list in HTML)
NONVERBAL_CHAT = 'mˈhm.'
LINES = {
 'sime':  {'happy': ('Eto, tako se to legne.', 'LIKOVI.sime.reakcije.dobro'),
           'disappointed': ('Ruka mi je ostarila.', 'LIKOVI.sime.reakcije.lose'),
           'disbelief': ('Ode, ode…', 'LIKOVI.sime.reakcije.vanka'),
           'effort': ('Pomakni se!', 'USKLICI.trulo')},
 'jure':  {'happy': ('Vidiš to?! Vidiš?!', 'LIKOVI.jure.reakcije.dobro'),
           'disappointed': ('Opet prekratko!', 'LIKOVI.jure.reakcije.lose'),
           'disbelief': ('Ma nemoguće!', 'LIKOVI.jure.reakcije.lose'),
           'effort': ('Rušim! Rušiiim!', 'LIKOVI.jure.reakcije.trulo')},
 'kate':  {'happy': ('Eto.', 'LIKOVI.kate.reakcije.dobro'),
           'disappointed': ('Nije mi se dalo.', 'LIKOVI.kate.reakcije.lose'),
           'disbelief': ('Ajme meni.', 'LIKOVI.kate.reakcije.vanka'),
           'effort': ('Ako triba, triba.', 'LIKOVI.kate.reakcije.trulo')},
 'ante':  {'happy': ('Ovo je za rakiju!', 'LIKOVI.ante.reakcije.savrseno / prica'),
           'disappointed': ('More je danas nemirno.', 'LIKOVI.ante.reakcije.lose'),
           'disbelief': ('U more je otišla!', 'LIKOVI.ante.reakcije.vanka'),
           'effort': ('Sad ću ga izbacit!', 'LIKOVI.ante.reakcije.trulo')},
 'vicko': {'happy': ('Račun se slaže.', 'LIKOVI.vicko.reakcije.dobro'),
           'disappointed': ('Krivo sam izračuna.', 'LIKOVI.vicko.reakcije.lose'),
           'disbelief': ('Izvan svih granica.', 'LIKOVI.vicko.reakcije.vanka'),
           'effort': ('Po mojoj računici — sad.', 'LIKOVI.vicko.reakcije.trulo / prica')},
 'mare':  {'happy': ('Ajme kako je lipa!', 'LIKOVI.mare.reakcije.dobro'),
           'disappointed': ('Ajme meni jadnoj…', 'LIKOVI.mare.reakcije.lose / prica'),
           'disbelief': ('Jooj, u more!', 'LIKOVI.mare.reakcije.vanka / prica'),
           'effort': ('Miči se ti odatle!', 'LIKOVI.mare.reakcije.trulo')},
 'duje':  {'happy': ('Tako.', 'LIKOVI.duje.reakcije.dobro / prica'),
           'disappointed': ('Hm.', 'LIKOVI.duje.reakcije.lose'),
           'disbelief': ('Prejako.', 'LIKOVI.duje.reakcije.vanka'),
           'effort': ('Bum!', 'LIKOVI.duje.reakcije.savrseno / prica')},
 'frane': {'happy': ('Vidi me, vidi me!', 'LIKOVI.frane.reakcije.dobro'),
           'disappointed': ('Ma daaaj…', 'LIKOVI.frane.reakcije.lose'),
           'disbelief': ('Ups, malo previše.', 'LIKOVI.frane.reakcije.vanka'),
           'effort': ('Gledajte ovo!', 'LIKOVI.frane.reakcije.trulo')},
}
PHON_OVERRIDE = {'Hm.': ['hˈm.', 'hˈːm.'], 'Bum!': ['bˈum!'],
                 'Eto.': ['ˈeto.', 'ˈɛto.', 'ˈeːto.', 'ˈeto!'],
                 'Ma daaaj…': ['ma dˈaːj.', 'mˈa dˈaːːj.', 'ma dˈaːj!'],
                 'Ups, malo previše.': ['ˈups, mˈalo prˈeʋiʃe.'],
                 'Ode, ode…': ['ˈode, ˈode.', 'ˈɔde, ˈɔde.', 'ˈode. ˈode.']}

def norm_txt(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'([a-z])\1+', r'\1', s)          # collapse elongations (Rusiiim, daaaj)
    return re.sub(r'[^a-z ]', '', s).strip()

def cer(a, b):
    a, b = norm_txt(a).replace(' ', ''), norm_txt(b).replace(' ', '')
    if not a: return 1.0
    d = np.arange(len(b)+1)
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            cur = min(d[j]+1, d[j-1]+1, prev+(ca != cb)); prev, d[j] = d[j], cur
    return d[len(b)]/len(a)

def psola_shift(x, sr, semis):
    if abs(semis) < 0.01: return x
    snd = parselmouth.Sound(x, sr)
    man = parselmouth.praat.call(snd, 'To Manipulation', 0.01, 60, 400)
    pt = parselmouth.praat.call(man, 'Extract pitch tier')
    parselmouth.praat.call(pt, 'Multiply frequencies', snd.xmin, snd.xmax, 2**(semis/12))
    parselmouth.praat.call([pt, man], 'Replace pitch tier')
    out = parselmouth.praat.call(man, 'Get resynthesis (overlap-add)')
    return out.values[0]

def polish(x, sr, v, kind):
    x = psola_shift(x, sr, v['semis'])
    x = resample(x, sr, SR)
    x = hp(x, 70, 2)
    # trailing-artifact guard: cut after the last voiced/energetic frame + 80 ms
    x = trim_tail(x, -42, min_len=0.15)
    x = np.concatenate([x, np.zeros(int(0.03*SR))])
    x = trim_lead(x, -40, keep=0.004)
    x = fade(x, 0.003, 0.05)
    # level: speech RMS (active frames) to a per-character target, peak cap
    fr = int(0.02*SR); m = len(x)//fr
    rms = np.sqrt(np.mean(x[:m*fr].reshape(m, fr)**2, axis=1))
    act = rms[rms > rms.max()*0.1]
    lvl = np.sqrt(np.mean(act**2))
    target = undb(-20 + v['gain'] + (1.5 if kind == 'effort' else 0) - (3 if kind == 'chat' else 0))
    x = x*target/lvl
    p = true_peak(x)
    if p > undb(-2): x *= undb(-2)/p
    return x

def render(cid, kind, text, phon=None, tries=None):
    v = VOICES[cid]
    best = None
    tries = tries or [(1.0, None), (0.94, None), (1.06, None), (0.9, None)]
    for sp, ph in tries:
        a, sr = say(text or '', v['mix'], speed=v['speed']*sp, phon=ph or phon)
        if text is None:
            return a, sr, '', 0.0, sp, ph or phon
        heard = asr(a, sr)
        c = cer(text, heard)
        if best is None or c < best[3]: best = (a, sr, heard, c, sp, ph)
        if c <= 0.12: break
    return best

def main():
    meta.reset(B)
    report = []
    for cid in ORDER:
        v = VOICES[cid]
        # chat: nonverbal, generic
        a, sr, heard, c, sp, _ = render(cid, 'chat', None, phon=NONVERBAL_CHAT)
        x = polish(a, sr, v, 'chat')
        rel = f'voices/{cid}/voice_{cid}_chat.wav'; write(rel, x)
        meta.add(B, file=rel, group=f'voice_{cid}', character=cid, kind='chat', transcript='',
                 nonverbal='closed-mouth "mhm" hum (no lexical content)', permitted_text='ANY line of this character',
                 event='character speech bubble (prica / fraze / brbljanje / suigrac)',
                 hook='glasLika(lik, txt) <- reci(); korakBrbljanja() glasLika(lik, "brbljanje")',
                 gain_db=0.0, rate=[0.97, 1.03], cooldown_ms=1200, max_voices=1,
                 status='existing-trigger (replace synthetic glasLika babble) / category routing needed',
                 method=KOKORO, phonemes=NONVERBAL_CHAT, asr_heard='(not applicable: nonverbal)',
                 voice_blend=v['mix'], speed=v['speed'], pitch_semitones=v['semis'])
        report.append((cid, 'chat', '(nonverbal mhm)', '', None))
        for kind in ['happy', 'disappointed', 'disbelief', 'effort']:
            text, src = LINES[cid][kind]
            phs = PHON_OVERRIDE.get(text) or [ipa(text.replace('…', '.'))]
            tries = [(sp, p) for p in phs for sp in (1.0, 0.94, 1.06)]
            a, sr, heard, c, sp, used_ph = render(cid, kind, text, tries=tries)
            x = polish(a, sr, v, kind)
            rel = f'voices/{cid}/voice_{cid}_{kind}.wav'; write(rel, x)
            meta.add(B, file=rel, group=f'voice_{cid}', character=cid, kind=kind, transcript=text,
                     permitted_text=f'exact on-screen text "{text}" only', html_source=src,
                     event={'happy': 'own good/perfect result, round won', 'disappointed': 'own weak result (lose)',
                            'disbelief': 'ball out (vanka) / incredulous reaction', 'effort': 'trulo call at/after a trulo throw'}[kind],
                     hook='glasLika(lik, txt) <- reci(strana, txt) when txt === transcript',
                     gain_db=0.0, rate=[1.0, 1.0], cooldown_ms=1500, max_voices=1,
                     status='existing-trigger (glasLika) with exact-text routing',
                     method=KOKORO, phonemes=used_ph, asr_heard=heard, asr_cer=round(float(c), 3),
                     speed=round(v['speed']*sp, 3), voice_blend=v['mix'], pitch_semitones=v['semis'])
            report.append((cid, kind, text, heard, c))
            print(f'{cid:6s} {kind:13s} {text:28s} | ASR: {heard:30s} CER {c:.2f} | {len(x)/SR:.2f}s', flush=True)
    json.dump({k: dict(v, mix=[list(m) for m in v['mix']]) for k, v in VOICES.items()},
              open(os.path.join(os.path.dirname(__file__), '..', 'registry', 'voice_identities.json'), 'w'),
              ensure_ascii=False, indent=1)

if __name__ == '__main__':
    dsp.OUT = sys.argv[1]
    main()
