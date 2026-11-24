#!/usr/bin/env python3
"""What are the picture changes timed to? Offsets (in frames) between joins / camera moves and words, sentences,
SFX onsets and music beats, each compared with a chance baseline.

Usage: 15_sync.py <work_dir> [only=<video-stem>]
Writes <work>/<video>/sync.json and prints a pooled summary.

For every query set (joins, dissolve starts, move starts, move peaks) and every event set (word starts, sentence starts,
clause starts, SFX onsets, music beats) the script reports
  median |offset| in frames, the same for 4000 random times (chance), their ratio, the signed median (query - event),
  and the share of queries within +-3 frames of an event (and that share for random times).
ratio << 1 means "timed to it"; ratio ~ 1 means no relationship.
"""
import json
import sys
from pathlib import Path

import numpy as np

FPS = 30.0
RNG = np.random.default_rng(7)


def nearest(q, ev):
    ev = np.sort(np.asarray(ev, float))
    q = np.asarray(q, float)
    i = np.searchsorted(ev, q)
    lo = ev[np.clip(i - 1, 0, len(ev) - 1)]
    hi = ev[np.clip(i, 0, len(ev) - 1)]
    return np.where(np.abs(q - lo) <= np.abs(hi - q), q - lo, q - hi)


def compare(q, ev, dur):
    if len(q) == 0 or len(ev) == 0:
        return None
    off = nearest(q, ev) * FPS
    rnd = nearest(RNG.uniform(0.3, dur - 0.3, 4000), ev) * FPS
    return {
        "n": int(len(q)), "abs_median_f": round(float(np.median(np.abs(off))), 2), "chance_abs_median_f": round(float(np.median(np.abs(rnd))), 2),
        "ratio": round(float(np.median(np.abs(off)) / max(np.median(np.abs(rnd)), 1e-6)), 2),
        "signed_median_f": round(float(np.median(off)), 2),
        "within_3f": round(float((np.abs(off) <= 3).mean()), 3), "chance_within_3f": round(float((np.abs(rnd) <= 3).mean()), 3),
        "offsets_f": [round(float(o), 1) for o in off],
    }


def events(d: Path):
    wj = json.loads((d / "words.json").read_text())
    sj = json.loads((d / "shots.json").read_text())
    aj = json.loads((d / "audio.json").read_text())
    W = wj["words"]
    sent_starts, clause_starts, sent_ends = [W[0]["start"]], [W[0]["start"]], []
    for a, b in zip(W[:-1], W[1:]):
        last = a["text"].rstrip("\"'”’")[-1:]
        if last in ".?!":
            sent_starts.append(b["start"])
            sent_ends.append(a["end"])
        if last in ".?!,;:":
            clause_starts.append(b["start"])
    sent_ends.append(W[-1]["end"])
    joins = sj["joins"]
    moves = [s for s in sj["segments"] if s["type"] == "move"]
    q = {
        "join_mid": [j["t"] for j in joins],
        "cut": [j["t"] for j in joins if j["type"] == "cut"],
        "dissolve_start": [j["from_frame"] / FPS for j in joins if j["type"] == "dissolve"],
        "dissolve_end": [j["to_frame"] / FPS for j in joins if j["type"] == "dissolve"],
        "move_start": [m["start"] for m in moves],
        "move_peak": [m["start"] + m.get("peak_pos", 0.5) * m["dur"] for m in moves],
        "sfx_onset": [e["start"] for e in aj["sfx"]["events"]],
    }
    ev = {
        "word_start": [w["start"] for w in W], "sentence_start": sent_starts, "sentence_end": sent_ends, "clause_start": clause_starts,
        "sfx_onset": [e["start"] for e in aj["sfx"]["events"]], "sfx_peak": [e["peak_t"] for e in aj["sfx"]["events"]],
        "music_beat": aj["beats"], "caption_on": [c["on"] for c in wj["captions"]],
        "join_mid": [j["t"] for j in joins], "move_start": [m["start"] for m in moves],
    }
    return q, ev, sj["duration"]


PAIRS = [("join_mid", "sentence_start"), ("join_mid", "clause_start"), ("join_mid", "word_start"), ("join_mid", "caption_on"), ("join_mid", "sfx_onset"),
         ("join_mid", "music_beat"), ("cut", "sentence_start"), ("cut", "word_start"), ("cut", "caption_on"), ("cut", "sfx_onset"),
         ("dissolve_start", "sentence_start"), ("dissolve_end", "sentence_start"), ("dissolve_start", "sentence_end"), ("dissolve_start", "word_start"),
         ("move_start", "sentence_start"), ("move_start", "clause_start"), ("move_start", "word_start"), ("move_start", "sfx_onset"), ("move_peak", "sfx_peak"),
         ("move_start", "music_beat"), ("sfx_onset", "word_start"), ("sfx_onset", "sentence_start"), ("sfx_onset", "music_beat"), ("sfx_onset", "join_mid"), ("sfx_onset", "move_start")]


def main():
    root = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None
    pooled = {p: {"off": [], "rnd": []} for p in PAIRS}
    for d in sorted(p for p in root.iterdir() if (p / "words.json").exists() and (p / "audio.json").exists() and (only is None or p.name == only)):
        q, ev, dur = events(d)
        res = {}
        for a, b in PAIRS:
            r = compare(q[a], ev[b], dur)
            res[f"{a}__vs__{b}"] = r
            if r:
                pooled[(a, b)]["off"].extend(r["offsets_f"])
                pooled[(a, b)]["rnd"].extend((nearest(RNG.uniform(0.3, dur - 0.3, 1500), ev[b]) * FPS).tolist())
        (d / "sync.json").write_text(json.dumps(res, indent=1))
    out = {}
    print(f"{'query':<15} {'event':<15} {'n':>4} {'|off| med f':>11} {'chance':>7} {'ratio':>6} {'signed med':>10} {'<=3f':>6} {'chance':>7}")
    for (a, b), v in pooled.items():
        off, rnd = np.array(v["off"]), np.array(v["rnd"])
        if len(off) == 0:
            continue
        rec = {"n": int(len(off)), "abs_median_f": round(float(np.median(np.abs(off))), 2), "chance_abs_median_f": round(float(np.median(np.abs(rnd))), 2),
               "ratio": round(float(np.median(np.abs(off)) / max(np.median(np.abs(rnd)), 1e-6)), 2), "signed_median_f": round(float(np.median(off)), 2),
               "signed_p25_p75_f": [round(float(np.percentile(off, 25)), 1), round(float(np.percentile(off, 75)), 1)],
               "within_3f": round(float((np.abs(off) <= 3).mean()), 3), "chance_within_3f": round(float((np.abs(rnd) <= 3).mean()), 3)}
        out[f"{a}__vs__{b}"] = rec
        print(f"{a:<15} {b:<15} {rec['n']:>4} {rec['abs_median_f']:>11} {rec['chance_abs_median_f']:>7} {rec['ratio']:>6} {rec['signed_median_f']:>10} {rec['within_3f']:>6} {rec['chance_within_3f']:>7}")
    if only is None:
        (root / "sync_pooled.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
