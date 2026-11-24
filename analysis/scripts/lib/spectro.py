#!/usr/bin/env python3
"""Spectrogram + level overview of mix / voice stem / music+SFX stem for visual inspection.

Usage: spectro.py <work/video_dir> <out.png> [t0] [t1]
"""
import sys
from pathlib import Path

import librosa
import librosa.display
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

args = [a for a in sys.argv[1:] if a != "--dnr"]
dnr = "--dnr" in sys.argv
d = Path(args[0])
out = args[1]
t0 = float(args[2]) if len(args) > 2 else 0.0
t1 = float(args[3]) if len(args) > 3 else None
if dnr:
    files = [("speech stem (DnR model)", d / "stems_dnr" / "speech.wav"), ("music stem (DnR model)", d / "stems_dnr" / "music.wav"), ("sfx stem (DnR model)", d / "stems_dnr" / "sfx.wav")]
else:
    files = [("mix", d / "audio.wav"), ("voice stem", d / "stems" / "vocals.wav"), ("bed stem (music+SFX)", d / "stems" / "no_vocals.wav")]
fig, axes = plt.subplots(4, 1, figsize=(22, 15), constrained_layout=True)
envs = {}
for ax, (name, fp) in zip(axes, files):
    y, sr = librosa.load(fp, sr=44100, mono=True, offset=t0, duration=(t1 - t0) if t1 else None)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=512)), ref=1.0)
    librosa.display.specshow(S, sr=sr, hop_length=512, x_axis="time", y_axis="log", ax=ax, vmin=-70, vmax=30, cmap="magma")
    ax.set_title(name)
    ax.set_ylim(40, 20000)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    envs[name] = 20 * np.log10(rms + 1e-9)
    ax.xaxis.set_major_locator(plt.MultipleLocator(1.0 if (t1 or 99) - t0 <= 30 else 2.0))
ax = axes[3]
for name, e in envs.items():
    ax.plot(librosa.frames_to_time(np.arange(len(e)), sr=44100, hop_length=512), e, label=name, lw=1)
ax.set_ylim(-70, 0)
ax.set_ylabel("RMS dBFS")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
ax.xaxis.set_major_locator(plt.MultipleLocator(1.0 if (t1 or 99) - t0 <= 30 else 2.0))
ax.set_xlim(0, len(next(iter(envs.values()))) * 512 / 44100)
fig.savefig(out, dpi=70)
print(out)
