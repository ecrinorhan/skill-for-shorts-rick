#!/usr/bin/env python3
"""Caption styling numbers that the event detector does not give: stroke width, shadow/glow, font size, voice checks.

Usage: 17_caption_style.py <work_dir> <fonts_dir> <out.json>
Part 1 (captions): for clean captions on bright backgrounds
  stroke_px          97th percentile of the distance from stroke pixels to the nearest white glyph pixel (= outside stroke width)
  margins            how far the dark ring extends beyond the glyph box on each side (asymmetry = hard drop shadow)
  halo_drop          mean luma just outside the stroke minus luma further out (negative = soft shadow / glow)
  font_px            for the best-matching free fonts: the size at which the rendered text has the observed ink height
Part 2 (voice): per sentence F0 median from the vocal stem, to see whether quoted speech is performed in other registers.
"""
import importlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
cap = importlib.import_module("08_captions")
fm = importlib.import_module("13_font_match")
agg = importlib.import_module("16_aggregate")

FONTS = [("Mona Sans 900", "MonaSans[wdth,wght].ttf", 900), ("Archivo 800", "Archivo[wdth,wght].ttf", 800), ("Chivo 900", "Chivo[wght].ttf", 900), ("Rubik 800", "Rubik[wght].ttf", 800)]


def stroke_stats(frame, det):
    pad = 34
    x0, x1, y0, y1 = det["x0"], det["x1"], det["y0"], det["y1"]
    if y0 - pad < 0 or x0 - pad < 0 or y1 + pad > frame.shape[0] or x1 + pad > frame.shape[1]:
        return None
    crop = frame[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
    mx = crop.max(axis=2).astype(np.float32)
    glyph = np.zeros(mx.shape, np.uint8)
    glyph[pad:pad + det["mask"].shape[0], pad:pad + det["mask"].shape[1]] = det["mask"]
    dist = cv2.distanceTransform(1 - glyph, cv2.DIST_L2, 5)
    far = (dist > 24) & (dist < 32)
    if far.sum() < 200 or mx[far].mean() < 120 or np.percentile(mx[far], 10) < 85:
        return None                      # background too dark to tell stroke from scene
    dark = (mx <= 70).astype(np.uint8)
    n, lab = cv2.connectedComponents(dark)
    touch = np.unique(lab[(cv2.dilate(glyph, np.ones((5, 5), np.uint8)) > 0) & (dark > 0)])
    ring = np.isin(lab, touch[touch > 0])
    if ring.sum() < 100:
        return None
    ys, xs = np.where(ring)
    gy, gx = np.where(glyph > 0)
    near = (dist > np.percentile(dist[ring], 97) + 2) & (dist < np.percentile(dist[ring], 97) + 9)
    return {
        "stroke_px": float(np.percentile(dist[ring], 97)), "stroke_px_median_edge": float(np.percentile(dist[ring], 90)),
        "top": int(gy.min() - ys.min()), "bottom": int(ys.max() - gy.max()), "left": int(gx.min() - xs.min()), "right": int(xs.max() - gx.max()),
        "halo_drop": float(mx[near].mean() - mx[far].mean()), "ink_h": int(det["mask"].shape[0]),
        "stroke_luma": float(mx[ring].mean()), "fill_luma": float(mx[glyph > 0].mean()),
    }


def main():
    root, fonts_dir, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    rows, sizes = [], {f[0]: [] for f in FONTS}
    for d in sorted(p for p in root.iterdir() if (p / "words.json").exists()):
        wj = json.loads((d / "words.json").read_text())
        cj = json.loads((d / "captions.json").read_text())
        cal = cj["calibration"]
        line = (cal["line_top_px"] - 14, cal["line_top_px"] + 1.32 * cal["line_glyph_h_px"] + 10, cal["line_glyph_h_px"])
        good = [c for c in wj["captions"] if c["frames"] >= 6 and c["text"].strip(".,!?") == c["spoken"].strip(".,!?") and c["spoken"].replace(" ", "").strip(".,!?").isalpha() and len(c["spoken"]) >= 4]
        got = 0
        for c in good[::max(1, len(good) // 40)]:
            f = (c["on_f"] + c["off_f"]) // 2
            frame = cv2.imread(str(d / "frames" / f"{f:05d}.jpg"))
            det = cap.detect(frame, line)
            if det is None:
                continue
            s = stroke_stats(frame, det)
            if s is None:
                continue
            s.update({"video": d.name, "frame": f, "text": c["spoken"]})
            rows.append(s)
            got += 1
            text = c["text"]
            for name, file, wt in FONTS:
                fp = fonts_dir / file
                if fp.exists():
                    ren = fm.render(text, fp, wt, px=160)
                    if ren is not None and abs(ren.shape[1] / ren.shape[0] - det["mask"].shape[1] / det["mask"].shape[0]) < 0.25 * ren.shape[1] / ren.shape[0]:
                        sizes[name].append(160.0 * det["mask"].shape[0] / ren.shape[0])
            if got >= 12:
                break
    def med(k):
        return round(float(np.median([r_[k] for r_ in rows])), 2)
    res = {
        "n_samples": len(rows), "stroke_px_p97": med("stroke_px"), "stroke_px_p90": med("stroke_px_median_edge"),
        "ring_margin_px": {k: med(k) for k in ("top", "bottom", "left", "right")}, "halo_drop_luma": med("halo_drop"),
        "stroke_luma": med("stroke_luma"), "fill_luma": med("fill_luma"),
        "font_px_at_1080x1920": {k: {"median": round(float(np.median(v)), 1), "p10_p90": [round(float(np.percentile(v, 10)), 1), round(float(np.percentile(v, 90)), 1)], "n": len(v)} for k, v in sizes.items() if v},
        "samples": rows[:60],
    }
    # ---- voice: sentence-level F0, quoted speech vs narration
    voice = []
    for d in sorted(p for p in root.iterdir() if (p / "audio_curves.npz").exists() and (p / "words.json").exists()):
        z = np.load(d / "audio_curves.npz")
        ft, f0 = z["f0_t"], z["f0"]
        S = agg.sentences(json.loads((d / "words.json").read_text())["words"])
        allv = f0[~np.isnan(f0)]
        base = float(np.median(allv))
        per = []
        for s in S:
            seg = f0[(ft >= s["start"]) & (ft <= s["end"])]
            seg = seg[~np.isnan(seg)]
            if len(seg) >= 8:
                per.append({"start": s["start"], "n": s["n"], "st_vs_video": float(12 * np.log2(np.median(seg) / base)), "exclaim": s["text"].endswith("!"), "question": s["text"].endswith("?")})
        st = np.array([p["st_vs_video"] for p in per])
        ex = np.array([p["st_vs_video"] for p in per if p["exclaim"] or p["question"]])
        voice.append({"video": d.name, "f0_median_hz": round(base, 1), "sentence_f0_sd_st": round(float(st.std()), 2), "sentence_f0_min_max_st": [round(float(st.min()), 1), round(float(st.max()), 1)],
                      "exclaim_or_question_mean_st": round(float(ex.mean()), 2) if len(ex) else None, "n_exclaim_or_question": int(len(ex)),
                      "sentences_3st_above": int((st > 3).sum()), "sentences_3st_below": int((st < -3).sum()), "sentences": len(per)})
    res["voice_sentence_pitch"] = {"per_video": voice, "sentence_f0_sd_st_mean": round(float(np.mean([v["sentence_f0_sd_st"] for v in voice])), 2),
                                   "exclaim_or_question_mean_st": round(float(np.mean([v["exclaim_or_question_mean_st"] for v in voice if v["exclaim_or_question_mean_st"] is not None])), 2),
                                   "share_sentences_3st_off": round(float(sum(v["sentences_3st_above"] + v["sentences_3st_below"] for v in voice) / sum(v["sentences"] for v in voice)), 3)}
    outp.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ("samples", "voice_sentence_pitch")}))
    print("voice:", json.dumps({k: v for k, v in res["voice_sentence_pitch"].items() if k != "per_video"}))
    print("f0 medians:", [v["f0_median_hz"] for v in voice])


if __name__ == "__main__":
    main()
