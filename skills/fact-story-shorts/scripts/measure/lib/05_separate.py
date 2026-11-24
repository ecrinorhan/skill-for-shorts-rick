#!/usr/bin/env python3
"""Source separation with Demucs (htdemucs, CPU): vocals / drums / bass / other.

Usage: 05_separate.py <work_dir> [model=htdemucs] [jobs=4]
Writes <work>/<video>/stems/{vocals,drums,bass,other,no_vocals}.wav (44.1 kHz stereo, float32).
no_vocals = drums + bass + other, i.e. the music + SFX bed.
"""
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model


def main():
    root = Path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "htdemucs"
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    torch.set_num_threads(threads)
    model = get_model(name)
    model.eval()
    for d in sorted(p for p in root.iterdir() if (p / "audio.wav").exists()):
        out = d / "stems"
        if (out / "no_vocals.wav").exists():
            continue
        out.mkdir(exist_ok=True)
        t0 = time.time()
        wav, sr = sf.read(d / "audio.wav", dtype="float32", always_2d=True)
        assert sr == model.samplerate, (sr, model.samplerate)
        x = torch.from_numpy(wav.T)[None]  # 1, C, T
        ref = x.mean(1)
        mean, std = ref.mean(), ref.std() + 1e-8
        with torch.no_grad():
            est = apply_model(model, (x - mean) / std, shifts=1, split=True, overlap=0.25, progress=False)[0]
        est = est * std + mean
        stems = {s: est[i].numpy().T for i, s in enumerate(model.sources)}
        stems["no_vocals"] = sum(v for k, v in stems.items() if k != "vocals")
        for k, v in stems.items():
            sf.write(out / f"{k}.wav", np.clip(v, -1, 1), sr, subtype="FLOAT")
        print(f"{d.name}: separated in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
