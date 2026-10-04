"""Croatian grapheme->IPA for Kokoro phoneme input, plus Whisper ASR check."""
import re, os, numpy as np
M = os.path.join(os.path.dirname(__file__), '..', 'models')
DIG = [('dž','ʤ'),('lj','ʎ'),('nj','ɲ')]
SNG = {'a':'a','b':'b','c':'ʦ','č':'ʧ','ć':'ʨ','d':'d','đ':'ʥ','e':'e','f':'f','g':'ɡ','h':'x',
       'i':'i','j':'j','k':'k','l':'l','m':'m','n':'n','o':'o','p':'p','r':'r','s':'s','š':'ʃ',
       't':'t','u':'u','v':'ʋ','z':'z','ž':'ʒ','y':'i','w':'ʋ','q':'k','x':'ks'}
V = set('aeiou')
def word_ipa(w, stress=True):
    w = w.lower()
    out = []; i = 0
    while i < len(w):
        for g,p in DIG:
            if w.startswith(g, i): out.append(p); i += len(g); break
        else:
            ch = w[i]; i += 1
            if ch in SNG:
                # vowel repetition -> length mark (Trulooo, Ajmeee)
                if ch in V and out and out[-1] in (SNG[ch], SNG[ch]+'ː'):
                    if not out[-1].endswith('ː'): out[-1] += 'ː'
                    continue
                out.append(SNG[ch])
    if stress:
        for k,p in enumerate(out):
            if p[0] in V: out.insert(k, 'ˈ'); break
    return ''.join(out)
def ipa(text):
    """keep punctuation Kokoro knows: , . ! ? … —"""
    toks = re.findall(r"[A-Za-zčćžšđČĆŽŠĐ]+|[,.!?…—]", text)
    res = []
    for t in toks:
        if re.match(r"[,.!?…—]", t): 
            if res: res[-1] += t
            else: res.append(t)
        else: res.append(word_ipa(t))
    return ' '.join(res)

_k = None
def kokoro():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(os.path.join(M,'kokoro-v1.0.onnx'), os.path.join(M,'voices-v1.0.bin'))
    return _k
def voice_vec(mix):
    k = kokoro()
    if isinstance(mix, str): return k.get_voice_style(mix)
    v = None
    for name, w in mix:
        s = k.get_voice_style(name) * w
        v = s if v is None else v + s
    return v
def say(text, mix, speed=1.0, phon=None):
    k = kokoro()
    ph = phon if phon is not None else ipa(text)
    a, sr = k.create(ph, voice=voice_vec(mix), speed=speed, is_phonemes=True)
    return np.asarray(a, dtype=np.float64), sr

_asr = None
def asr(x, sr, lang='hr'):
    global _asr
    import sherpa_onnx
    if _asr is None:
        d = os.path.join(M, 'sherpa-onnx-whisper-small')
        _asr = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=d+'/small-encoder.int8.onnx', decoder=d+'/small-decoder.int8.onnx',
            tokens=d+'/small-tokens.txt', language=lang, task='transcribe', num_threads=4)
    if sr != 16000:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(sr, 16000); x = resample_poly(x, 16000//g, sr//g)
    x = np.concatenate([np.zeros(4000), x, np.zeros(8000)]).astype(np.float32)
    s = _asr.create_stream(); s.accept_waveform(16000, x); _asr.decode_stream(s)
    return s.result.text.strip()
