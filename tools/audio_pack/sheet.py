"""Visual audition: spectrogram + waveform grid for a list of wav files."""
import sys, numpy as np, soundfile as sf, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, os
def sheet(files, out, cols=3, fmax=16000):
    rows = (len(files)+cols-1)//cols
    fig, ax = plt.subplots(rows, cols, figsize=(5*cols, 2.6*rows), squeeze=False)
    for k, f in enumerate(files):
        x, sr = sf.read(f); m = x.mean(1) if x.ndim > 1 else x
        a = ax[k//cols][k % cols]
        a.specgram(m+1e-9*np.random.randn(len(m)), NFFT=1024 if len(m)>sr*2 else 512, Fs=sr, noverlap=384 if len(m)<=sr*2 else 768, cmap='magma', vmin=-130, vmax=-20)
        a.set_ylim(0, fmax); a.set_title(os.path.basename(f)[:-4], fontsize=8)
        t = np.arange(len(m))/sr
        a2 = a.twinx(); a2.plot(t, m, color='c', lw=0.4, alpha=0.7); a2.set_ylim(-1, 1); a2.set_yticks([])
        a.tick_params(labelsize=6)
    for k in range(len(files), rows*cols): ax[k//cols][k % cols].axis('off')
    fig.tight_layout(); fig.savefig(out, dpi=70); plt.close(fig)
if __name__ == '__main__':
    sheet(sys.argv[2:], sys.argv[1])
