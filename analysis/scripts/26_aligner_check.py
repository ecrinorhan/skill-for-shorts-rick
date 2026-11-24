#!/usr/bin/env python3
"""How far do word times move when the word-timing model changes?

Usage: 26_aligner_check.py <work_dir> <scratch_dir> <analysis_dir>
Reads  <work>/<video>/{whisper,captions,words}.json and stems/vocals.wav
Writes <analysis>/data/aligner_check.json

The word times stored in analysis/data came from torchaudio MMS_FA, whose weights are CC-BY-NC 4.0. The skill's tools use
WAV2VEC2_ASR_BASE_960H (MIT) instead. This re-aligns every reference video with that model in <scratch_dir>, leaving the
stored files alone, and reports the shift in word starts and the caption lead each model gives.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


def spread(x):
    return {"mean": round(float(np.mean(x)), 3), "sd": round(float(np.std(x)), 3), "min": round(float(np.min(x)), 3), "max": round(float(np.max(x)), 3)}


def main():
    work, scratch, adir = (Path(p) for p in sys.argv[1:4])
    vids = sorted(p.name for p in work.iterdir() if (p / "words.json").exists() and (p / "stems" / "vocals.wav").exists())
    for v in vids:
        (scratch / v / "stems").mkdir(parents=True, exist_ok=True)
        for n in ("whisper.json", "captions.json", "stems/vocals.wav"):
            shutil.copy(work / v / n, scratch / v / n)
    subprocess.run([sys.executable, str(Path(__file__).with_name("10_align.py")), str(scratch)], check=True, env={**os.environ, "ALIGN_MODEL": "wav2vec2"})
    rows, pooled = [], []
    for v in vids:
        a, b = (json.loads((d / v / "words.json").read_text()) for d in (work, scratch))
        same = [w["text"] for w in a["words"]] == [w["text"] for w in b["words"]]
        row = {"video": v, "words": len(b["words"]), "same_words": same,
               "caption_lead_frames_mms": -a["stats"]["caption_on_minus_word_frames_median"],
               "caption_lead_frames_wav2vec2": -b["stats"]["caption_on_minus_word_frames_median"]}
        if same:
            d = np.array([q["start"] - p["start"] for p, q in zip(a["words"], b["words"])]) * 1000
            pooled += list(d)
            row.update(start_shift_ms_median=round(float(np.median(d)), 1), within_one_frame=round(float(np.mean(np.abs(d) <= 33.4)), 3))
        rows.append(row)
    p = np.array(pooled)
    out = {"reference_model": "torchaudio MMS_FA (CC-BY-NC 4.0)", "tool_model": "torchaudio WAV2VEC2_ASR_BASE_960H (MIT)", "n_videos": len(rows),
           "videos_with_same_words": sum(r["same_words"] for r in rows), "n_words_compared": len(p),
           "word_start_shift_ms": {"median": round(float(np.median(p)), 1), "abs_median": round(float(np.median(np.abs(p))), 1), "abs_p90": round(float(np.percentile(np.abs(p), 90)), 1),
                                   "abs_max": round(float(np.abs(p).max()), 1), "within_one_frame": round(float(np.mean(np.abs(p) <= 33.4)), 3),
                                   "within_two_frames": round(float(np.mean(np.abs(p) <= 66.7)), 3)},
           "caption_lead_frames": {"mms": spread([r["caption_lead_frames_mms"] for r in rows]), "wav2vec2": spread([r["caption_lead_frames_wav2vec2"] for r in rows])},
           "videos": rows}
    (adir / "data" / "aligner_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "videos"}))


if __name__ == "__main__":
    main()
