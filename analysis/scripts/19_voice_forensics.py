#!/usr/bin/env python3
"""Voice forensics: numbers that bear on "human or TTS?" and on how the voice track was edited.

Usage: 19_voice_forensics.py <work_dir> <out.json> [reference.wav ...]
Per video (Demucs vocal stem, Praat via parselmouth):
  formant spacing -> apparent vocal-tract length (cm)      long tract + high pitch = pitched-up / sped-up or performed voice
  jitter, shimmer, HNR                                      micro-variation of the glottal source
  inter-sentence gap median and spread (forced alignment)   near-constant gaps = automatic silence removal or clip concatenation
  speaking-rate spread across sentences (syllables per s)   TTS is usually steadier than a person
Optional reference files (for example TTS probes) are measured the same way for comparison.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import parselmouth
from parselmouth.praat import call


def measure(path, t0=None, t1=None):
    snd = parselmouth.Sound(str(path))
    if snd.n_channels > 1:
        snd = snd.convert_to_mono()
    if t0 is not None:
        snd = snd.extract_part(from_time=t0, to_time=t1)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]
    ts = pitch.xs()
    voiced = f0 > 0
    form = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=5500)
    inten = snd.to_intensity(time_step=0.01)
    thr = np.percentile(inten.values[0], 60)
    disp = []
    f1s, f2s, f3s, f4s = [], [], [], []
    for t, v in zip(ts, voiced):
        if not v or inten.get_value(t) is None or inten.get_value(t) < thr:
            continue
        f = [form.get_value_at_time(k, t) for k in (1, 2, 3, 4)]
        if any(x is None or np.isnan(x) for x in f):
            continue
        f1s.append(f[0]); f2s.append(f[1]); f3s.append(f[2]); f4s.append(f[3])
        disp.append((f[3] - f[0]) / 3.0)
    pp = call(snd, "To PointProcess (periodic, cc)", 75, 500)
    jitter = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    shimmer = call([snd, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    hnr = call(snd.to_harmonicity_cc(0.01, 75, 0.1, 1.0), "Get mean", 0, 0)
    d = float(np.median(disp)) if disp else None
    return {
        "f0_median_hz": round(float(np.median(f0[voiced])), 1) if voiced.any() else None,
        "formant_spacing_hz": round(d, 0) if d else None, "vocal_tract_cm_est": round(35000 / (2 * d), 1) if d else None,
        "f1_f2_f3_f4_median_hz": [round(float(np.median(x))) for x in (f1s, f2s, f3s, f4s)] if disp else None,
        "jitter_local_pct": round(jitter * 100, 2), "shimmer_local_pct": round(shimmer * 100, 2), "hnr_db": round(float(hnr), 1),
    }


def syllables(text):
    return sum(max(1, len(re.findall(r"[aeiouy]+", re.sub(r"e\b", "", w.lower())))) for w in text.split())


def main():
    root, outp = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for d in sorted(p for p in root.iterdir() if (p / "stems" / "vocals.wav").exists() and (p / "words.json").exists()):
        m = measure(d / "stems" / "vocals.wav")
        W = json.loads((d / "words.json").read_text())["words"]
        sents, cur = [], []
        for w in W:
            cur.append(w)
            if w["text"].rstrip("\"'”’")[-1:] in ".?!":
                sents.append(cur)
                cur = []
        if cur:
            sents.append(cur)
        gaps = [b[0]["start"] - a[-1]["end"] for a, b in zip(sents[:-1], sents[1:])]
        rates = [syllables(" ".join(w["text"] for w in s)) / max(s[-1]["end"] - s[0]["start"], 0.2) for s in sents if len(s) >= 4]
        wgaps = [b["start"] - a["end"] for a, b in zip(W[:-1], W[1:])]
        m.update({"video": d.name, "sentence_gap_median_ms": round(float(np.median(gaps)) * 1000), "sentence_gap_p10_p90_ms": [round(float(np.percentile(gaps, 10)) * 1000), round(float(np.percentile(gaps, 90)) * 1000)],
                  "sentence_gap_max_ms": round(float(max(gaps)) * 1000), "word_gap_p99_ms": round(float(np.percentile(wgaps, 99)) * 1000),
                  "rate_syll_s_median": round(float(np.median(rates)), 2), "rate_cv": round(float(np.std(rates) / np.mean(rates)), 3)})
        rows.append(m)
        print(d.name, {k: m[k] for k in ("f0_median_hz", "formant_spacing_hz", "vocal_tract_cm_est", "jitter_local_pct", "shimmer_local_pct", "hnr_db", "sentence_gap_median_ms", "sentence_gap_p10_p90_ms", "rate_cv")}, flush=True)
    refs = []
    for ref in sys.argv[3:]:
        m = measure(ref)
        m["file"] = Path(ref).name
        refs.append(m)
        print("REF", m["file"], {k: m[k] for k in ("f0_median_hz", "formant_spacing_hz", "vocal_tract_cm_est", "jitter_local_pct", "shimmer_local_pct", "hnr_db")})

    def agg(k):
        v = [r_[k] for r_ in rows if r_[k] is not None]
        return {"mean": round(float(np.mean(v)), 2), "sd": round(float(np.std(v)), 2), "min": round(float(min(v)), 2), "max": round(float(max(v)), 2)}
    summary = {k: agg(k) for k in ("f0_median_hz", "formant_spacing_hz", "vocal_tract_cm_est", "jitter_local_pct", "shimmer_local_pct", "hnr_db", "sentence_gap_median_ms", "sentence_gap_max_ms", "word_gap_p99_ms", "rate_syll_s_median", "rate_cv")}
    outp.write_text(json.dumps({"summary": summary, "videos": rows, "references": refs}, indent=1))
    print("SUMMARY", json.dumps(summary))


if __name__ == "__main__":
    main()
