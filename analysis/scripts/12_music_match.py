#!/usr/bin/env python3
"""Is the same music track reused? Pairwise similarity of the music stems, plus loudness-independent descriptors.

Usage: 12_music_match.py <work_dir> <out.json>
Method: beat-independent chroma (CQT, harmonic part, ~5.4 frames/s) of each DnR music stem; for each pair the best mean
cosine similarity over all lags with >= 20 s overlap. Identical recordings give >= 0.9 at one sharp lag; different
tracks in the same key give ~0.6-0.75 with no sharp peak. "peak_sharpness" = best minus the median over lags.
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np

HOP = 4096
SR = 22050


def chroma(fp):
    y, _ = librosa.load(fp, sr=SR, mono=True)
    yh = librosa.effects.harmonic(y, margin=2.0)
    c = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=HOP)
    c = c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)
    return c


def best_lag(a, b, min_overlap):
    na, nb = a.shape[1], b.shape[1]
    scores = {}
    for lag in range(-(nb - min_overlap), na - min_overlap + 1):
        a0, b0 = max(0, lag), max(0, -lag)
        L = min(na - a0, nb - b0)
        if L < min_overlap:
            continue
        scores[lag] = float((a[:, a0:a0 + L] * b[:, b0:b0 + L]).sum(axis=0).mean())
    lags = np.array(sorted(scores))
    vals = np.array([scores[lg] for lg in lags])
    k = int(vals.argmax())
    return float(vals[k]), float(lags[k] * HOP / SR), float(vals[k] - np.median(vals))


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    dirs = sorted(p for p in root.iterdir() if (p / "stems_dnr" / "music.wav").exists())
    names = [d.name for d in dirs]
    ch = [chroma(d / "stems_dnr" / "music.wav") for d in dirs]
    min_ov = int(20 * SR / HOP)
    n = len(dirs)
    sim = np.eye(n)
    lag = np.zeros((n, n))
    sharp = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s, lg, sh = best_lag(ch[i], ch[j], min_ov)
            sim[i, j] = sim[j, i] = s
            lag[i, j], lag[j, i] = lg, -lg
            sharp[i, j] = sharp[j, i] = sh
        print(names[i], " ".join(f"{sim[i, j]:.2f}" for j in range(n)), flush=True)
    # cluster: same track if similarity >= 0.88 and the peak is sharp
    same = (sim >= 0.88) & (sharp >= 0.12)
    groups, seen = [], set()
    for i in range(n):
        if i in seen:
            continue
        grp, stack = [], [i]
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            grp.append(k)
            stack.extend(j for j in range(n) if same[k, j] and j not in seen)
        groups.append(sorted(grp))
    res = {
        "videos": names, "similarity": np.round(sim, 3).tolist(), "lag_s": np.round(lag, 2).tolist(), "peak_sharpness": np.round(sharp, 3).tolist(),
        "same_track_groups": [[names[k] for k in g] for g in groups],
        "offdiag_similarity_median": round(float(np.median(sim[np.triu_indices(n, 1)])), 3),
        "offdiag_similarity_max": round(float(sim[np.triu_indices(n, 1)].max()), 3),
    }
    out.write_text(json.dumps(res, indent=1))
    print("groups:", res["same_track_groups"])
    print("off-diagonal similarity median/max:", res["offdiag_similarity_median"], res["offdiag_similarity_max"])


if __name__ == "__main__":
    main()
