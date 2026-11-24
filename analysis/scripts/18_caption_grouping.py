#!/usr/bin/env python3
"""How are spoken words grouped into on-screen captions? Fits a simple rule to the 20 videos.

Usage: 18_caption_grouping.py <work_dir> <out.json>
Reads words.json (each word carries the index of the caption it was shown in).
Reports merge probabilities by word length and fits the rule used by the skill's caption builder:
  merge word[i] and word[i+1] into one caption when
    min(len_i, len_j) <= SHORT  and  len_i + 1 + len_j <= MAXCHARS  and  no sentence/clause punctuation after word[i]
The fit maximises agreement with the real caption boundaries; it also reports the words-per-caption it produces.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def letters(t):
    return re.sub(r"[^A-Za-z0-9']", "", t)


def group(words, short, maxchars, max3, stop_punct):
    """words: list of (text, gap_to_next_s). Returns list of caption word-index lists."""
    caps, i = [], 0
    while i < len(words):
        cur = [i]
        while len(cur) < 3 and cur[-1] + 1 < len(words):
            a, b = words[cur[-1]][0], words[cur[-1] + 1][0]
            if a.rstrip("\"'”’")[-1:] in stop_punct:
                break
            text = " ".join(words[k][0] for k in cur) + " " + b
            la, lb = len(letters(a)), len(letters(b))
            if len(cur) == 1:
                ok = min(la, lb) <= short and len(text) <= maxchars
            else:
                ok = max(len(letters(words[k][0])) for k in cur) <= 4 and lb <= 5 and len(text) <= max3
            if not ok:
                break
            cur.append(cur[-1] + 1)
        caps.append(cur)
        i = cur[-1] + 1
    return caps


def main():
    root, outp = Path(sys.argv[1]), Path(sys.argv[2])
    vids = []
    for d in sorted(p for p in root.iterdir() if (p / "words.json").exists()):
        W = json.loads((d / "words.json").read_text())["words"]
        vids.append(W)
    merge_by_len, tot_by_len = Counter(), Counter()
    two_combo, sizes, after_punct = Counter(), Counter(), Counter()
    chars2 = []
    for W in vids:
        capsize = Counter(w["cap"] for w in W)
        for c, n in capsize.items():
            sizes[min(n, 4)] += 1
        for a, b in zip(W[:-1], W[1:]):
            la, lb = len(letters(a["text"])), len(letters(b["text"]))
            merged = a["cap"] == b["cap"]
            key = min(min(la, lb), 7)
            tot_by_len[key] += 1
            merge_by_len[key] += merged
            p = a["text"].rstrip("\"'”’")[-1:]
            if p in ".?!,":
                after_punct[(p, merged)] += 1
            if merged:
                two_combo[(min(la, 6), min(lb, 6))] += 1
                chars2.append(la + 1 + lb)
    res = {"caption_size_hist": dict(sizes),
           "merge_prob_by_shorter_word_len": {k: round(merge_by_len[k] / tot_by_len[k], 3) for k in sorted(tot_by_len)},
           "merge_after_punct": {f"{p} merged={m}": n for (p, m), n in sorted(after_punct.items())},
           "merged_pair_chars_p50_p90_max": [float(np.percentile(chars2, 50)), float(np.percentile(chars2, 90)), int(max(chars2))]}
    # fit
    best = None
    for short in (2, 3, 4):
        for maxchars in range(8, 17):
            for max3 in (0, 10, 11, 12, 13, 15):
                for stop in (".?!", ".?!,"):
                    agree, n, ncap, nw = 0, 0, 0, 0
                    for W in vids:
                        words = [(w["text"], 0) for w in W]
                        caps = group(words, short, maxchars, max3, stop)
                        pred_same = set()
                        for c in caps:
                            for k in c[:-1]:
                                pred_same.add(k)
                        for k in range(len(W) - 1):
                            agree += (k in pred_same) == (W[k]["cap"] == W[k + 1]["cap"])
                            n += 1
                        ncap += len(caps)
                        nw += len(W)
                    rec = (agree / n, short, maxchars, max3, stop, nw / ncap)
                    if best is None or rec[0] > best[0]:
                        best = rec
    res["best_rule"] = {"boundary_agreement": round(best[0], 4), "SHORT": best[1], "MAXCHARS": best[2], "MAX3": best[3], "stop_punct": best[4], "words_per_caption": round(best[5], 3)}
    real = sum(len(W) for W in vids) / sum(len({w["cap"] for w in W}) for W in vids)
    res["real_words_per_caption"] = round(real, 3)
    outp.write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
