import sherpa_onnx, numpy as np, os
from scipy.signal import resample_poly
_ex=None
def emb(x, sr):
    global _ex
    if _ex is None:
        _ex = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=os.path.join(os.path.dirname(__file__),'..','models','wespeaker_en_voxceleb_resnet34.onnx'), num_threads=4))
    from math import gcd
    g=gcd(sr,16000); y=resample_poly(x,16000//g,sr//g).astype(np.float32)
    s=_ex.create_stream(); s.accept_waveform(16000,y); s.input_finished()
    e=np.array(_ex.compute(s)); return e/np.linalg.norm(e)
