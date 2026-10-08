import sys, os, glob, wave, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
def read(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float).reshape(-1, w.getnchannels()) / 32768
    return x.mean(1)
fs = sorted(glob.glob(os.path.join(sys.argv[1], 'music', '*.wav')))
fig, axs = plt.subplots(len(fs), 2, figsize=(16, 1.9 * len(fs)), gridspec_kw={'width_ratios': [3, 1]})
for (a, b), f in zip(axs, fs):
    x = read(f)
    a.specgram(x + 1e-9, NFFT=2048, Fs=44100, noverlap=1024, cmap='magma', vmin=-140, vmax=-40); a.set_ylim(0, 6000)
    a.set_title(os.path.basename(f), fontsize=8); a.tick_params(labelsize=6)
    seg = x[44100 * 4:44100 * 10]
    b.specgram(seg + 1e-9, NFFT=4096, Fs=44100, noverlap=3584, cmap='magma', vmin=-140, vmax=-40); b.set_ylim(0, 2500); b.tick_params(labelsize=6)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=60)
