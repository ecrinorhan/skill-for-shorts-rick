#!/usr/bin/env python3
"""Dialogue / music / effects separation with the CDX23 cinematic demixing checkpoints (HT-Demucs trained on DnR).

Checkpoints: github.com/ZFTurbo/MVSEP-CDX23-Cinematic-Sound-Demixing release v.1.0.0 (three seeds, averaged).
Usage: 05b_separate_dnr.py <work_dir> <models_dir> [threads=8] [only=<video-stem>]
Writes <work>/<video>/stems_dnr/{speech,music,sfx}.wav (44.1 kHz stereo float32).
"""
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.states import load_model

URL = "https://github.com/ZFTurbo/MVSEP-CDX23-Cinematic-Sound-Demixing/releases/download/v.1.0.0/"
CKPTS = ["97d170e1-a778de4a.th", "97d170e1-dbb4db15.th", "97d170e1-e41a5468.th"]


def main():
    root, mdir = Path(sys.argv[1]), Path(sys.argv[2])
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    only = sys.argv[4] if len(sys.argv) > 4 else None
    torch.set_num_threads(threads)
    mdir.mkdir(parents=True, exist_ok=True)
    models = []
    for name in CKPTS:
        fp = mdir / name
        if not fp.exists():
            torch.hub.download_url_to_file(URL + name, str(fp))
        m = load_model(str(fp))
        m.eval()
        models.append(m)
    print("sources:", models[0].sources, "sr:", models[0].samplerate, flush=True)
    for d in sorted(p for p in root.iterdir() if (p / "audio.wav").exists() and (only is None or p.name == only)):
        out = d / "stems_dnr"
        if (out / "sfx.wav").exists():
            continue
        out.mkdir(exist_ok=True)
        t0 = time.time()
        wav, sr = sf.read(d / "audio.wav", dtype="float32", always_2d=True)
        x = torch.from_numpy(wav.T)[None]
        acc = None
        with torch.no_grad():
            for m in models:
                est = apply_model(m, x, shifts=1, split=True, overlap=0.5, progress=False)[0]
                acc = est if acc is None else acc + est
        acc = (acc / len(models)).numpy()
        for i, s in enumerate(models[0].sources):
            sf.write(out / f"{s}.wav", np.clip(acc[i].T, -1, 1), sr, subtype="FLOAT")
        print(f"{d.name}: {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
