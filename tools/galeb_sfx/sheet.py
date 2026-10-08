"""Spectrogram contact sheets for visual inspection."""
import sys, os, glob, wave
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
        ch = w.getnchannels()
    return x.reshape(-1, ch).mean(1), 44100

def sheet(files, out, cols=4):
    rows = (len(files) + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 4.2, rows * 2.6))
    for ax, f in zip(np.ravel(axs), files):
        x, sr = read(f)
        ax.specgram(x + 1e-9, NFFT=1024, Fs=sr, noverlap=768, cmap='magma', vmin=-130, vmax=-30)
        ax.set_ylim(0, 9000)
        t = np.arange(len(x)) / sr
        ax2 = ax.twinx(); ax2.plot(t, x, color='cyan', lw=0.3, alpha=0.6); ax2.set_ylim(-1, 1); ax2.set_yticks([])
        ax.set_title(os.path.basename(f).replace('.wav', ''), fontsize=8)
        ax.tick_params(labelsize=6)
    for ax in np.ravel(axs)[len(files):]: ax.axis('off')
    fig.tight_layout(); fig.savefig(out, dpi=70); plt.close(fig)

if __name__ == '__main__':
    root, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for d in sorted(glob.glob(os.path.join(root, 'sfx', '*'))) + [os.path.join(root, 'ambience')]:
        fs = sorted(glob.glob(os.path.join(d, '*.wav')))
        for k in range(0, len(fs), 12):
            sheet(fs[k:k + 12], os.path.join(out, f'{os.path.basename(d)}_{k // 12}.png'))
