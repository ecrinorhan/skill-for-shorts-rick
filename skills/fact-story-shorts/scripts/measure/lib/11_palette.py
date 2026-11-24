#!/usr/bin/env python3
"""Colour, grade and palette measurements.

Usage: 11_palette.py <work_dir> [jobs=6] [only=<video-stem>]
Reads  frames/, frame_metrics.csv, shots.json
Writes color.json:
  video_palette      k=8 k-means in CIELAB over every 15th frame (hex, share)
  segment_palettes   k=5 per hold segment (hex, share) + mean saturation / luma / warm-cool split
  grade              black/white levels, contrast, saturation, colourfulness, vignette, grain estimate, bloom estimate,
                     luma histogram (32 bins), hue histogram (12 bins, saturation-weighted)
  curves             1-second means of luma / contrast / saturation (to see changes at key moments)
The caption line (68.5-72.8 % of height, middle 64 % of width) is masked out so the white text does not enter the palette.
"""
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

FPS = 30.0


def to_hex(lab):
    px = np.array([[lab]], np.float32)
    bgr = cv2.cvtColor(px, cv2.COLOR_Lab2BGR)[0, 0]
    r, g, b = [int(np.clip(round(v * 255), 0, 255)) for v in bgr[::-1]]
    return f"#{r:02X}{g:02X}{b:02X}"


def lab_pixels(fp, size=(72, 128)):
    im = cv2.imread(str(fp), cv2.IMREAD_REDUCED_COLOR_4)
    im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]
    mask = np.ones((h, w), bool)
    mask[int(0.685 * h):int(0.728 * h) + 1, int(0.18 * w):int(0.82 * w)] = False
    lab = cv2.cvtColor(im.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)
    return lab[mask]


def kmeans(px, k):
    px = px.astype(np.float32)
    if len(px) > 60000:
        px = px[np.random.default_rng(0).choice(len(px), 60000, replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(labels.ravel(), minlength=k) / len(labels)
    order = np.argsort(-share)
    out = []
    for i in order:
        L, a, b = centers[i]
        out.append({"hex": to_hex(centers[i]), "share": round(float(share[i]), 3), "L": round(float(L), 1),
                    "chroma": round(float(np.hypot(a, b)), 1), "hue_deg": round(float(np.degrees(np.arctan2(b, a)) % 360), 0)})
    return out


def grain_and_bloom(fp):
    """Grain: std of the high-pass residual in flat areas (8-bit luma units). Bloom: mean luma lift in a 12-40 px ring
    around near-white regions relative to the frame median (both rough estimates)."""
    im = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    blur = cv2.GaussianBlur(im, (0, 0), 2.0)
    resid = im - blur
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1)
    flat = (np.hypot(gx, gy) < 4) & (im > 30) & (im < 225)
    grain = float(resid[flat].std()) if flat.sum() > 5000 else None
    hot = (im > 245).astype(np.uint8)
    bloom = None
    if hot.mean() > 0.002:
        inner = cv2.dilate(hot, np.ones((25, 25), np.uint8))
        outer = cv2.dilate(hot, np.ones((81, 81), np.uint8))
        ring = (outer > 0) & (inner == 0)
        far = outer == 0
        if ring.sum() > 2000 and far.sum() > 2000:
            bloom = float(im[ring].mean() - np.median(im[far]))
    return grain, bloom


def one(d: Path):
    frames = sorted((d / "frames").glob("*.jpg"))
    n = len(frames)
    with open(d / "frame_metrics.csv") as fh:
        rows = list(csv.DictReader(fh))
    m = {k: np.array([float(r[k]) for r in rows]) for k in rows[0].keys()}
    sj = json.loads((d / "shots.json").read_text())
    vid_px = np.concatenate([lab_pixels(frames[i]) for i in range(0, n, 15)])
    video_palette = kmeans(vid_px, 8)
    seg_pal = []
    for s in sj["segments"]:
        if s["type"] != "hold" or s["dur"] < 0.4:
            continue
        idx = np.unique(np.linspace(s["start_f"], s["end_f"], 5).astype(int))
        px = np.concatenate([lab_pixels(frames[i]) for i in idx])
        seg_pal.append({"start": s["start"], "end": s["end"], "palette": kmeans(px, 5),
                        "luma": s["luma_mean"], "contrast": s["luma_std"], "sat": s["sat_mean"], "warm_frac": s["warm_frac"], "cool_frac": s["cool_frac"]})
    # hue + luma histograms from sampled frames
    hue_hist = np.zeros(12)
    luma_hist = np.zeros(32)
    for i in range(0, n, 15):
        im = cv2.resize(cv2.imread(str(frames[i]), cv2.IMREAD_REDUCED_COLOR_4), (135, 240), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[..., 0].astype(np.float32) * 2, hsv[..., 1].astype(np.float32) / 255, hsv[..., 2].astype(np.float32) / 255
        wgt = s * v
        hue_hist += np.bincount((h // 30).astype(int).ravel() % 12, weights=wgt.ravel(), minlength=12)
        y = 0.2126 * im[..., 2] + 0.7152 * im[..., 1] + 0.0722 * im[..., 0]
        luma_hist += np.histogram(y, bins=32, range=(0, 256))[0]
    hue_hist /= hue_hist.sum() + 1e-9
    luma_hist /= luma_hist.sum() + 1e-9
    gb = [grain_and_bloom(frames[i]) for i in np.linspace(0, n - 1, 12).astype(int)]
    grains = [g for g, _ in gb if g is not None]
    blooms = [b for _, b in gb if b is not None]
    sec = np.floor(m["t"]).astype(int)
    curves = {k: [round(float(m[k][sec == s].mean()), 1) for s in range(sec.max() + 1)] for k in ("luma_mean", "luma_std", "sat_mean", "colorfulness")}
    hue_names = ["red", "orange", "yellow", "yellow-green", "green", "spring green", "cyan", "azure", "blue", "violet", "magenta", "rose"]
    grade = {
        "luma_mean": round(float(m["luma_mean"].mean()), 1), "luma_mean_p05_p95": [round(float(np.percentile(m["luma_mean"], p)), 1) for p in (5, 95)],
        "contrast_rms_mean": round(float(m["luma_std"].mean()), 1), "contrast_rms_p05_p95": [round(float(np.percentile(m["luma_std"], p)), 1) for p in (5, 95)],
        "black_level_p01_median": round(float(np.median(m["p01"])), 1), "black_level_p05_median": round(float(np.median(m["p05"])), 1),
        "white_level_p99_median": round(float(np.median(m["p99"])), 1), "white_level_p95_median": round(float(np.median(m["p95"])), 1),
        "median_luma_p50": round(float(np.median(m["p50"])), 1),
        "saturation_mean": round(float(m["sat_mean"].mean()), 1), "saturation_p05_p95": [round(float(np.percentile(m["sat_mean"], p)), 1) for p in (5, 95)],
        "saturation_p90_within_frame_mean": round(float(m["sat_p90"].mean()), 1),
        "colorfulness_mean": round(float(m["colorfulness"].mean()), 1), "chroma_lab_mean": round(float(m["chroma_mean"].mean()), 1),
        "lab_a_mean": round(float(m["lab_a"].mean()), 1), "lab_b_mean": round(float(m["lab_b"].mean()), 1),
        "warm_frac_mean": round(float(m["warm_frac"].mean()), 3), "cool_frac_mean": round(float(m["cool_frac"].mean()), 3),
        "warm_dominant_time_frac": round(float((m["warm_frac"] > m["cool_frac"]).mean()), 3),
        "vignette_corner_over_centre_median": round(float(np.median(m["vignette"])), 3),
        "sharpness_laplacian_var_median": round(float(np.median(m["sharp"])), 0),
        "edge_density_median": round(float(np.median(m["edge_density"])), 4),
        "grain_sigma_8bit_median": round(float(np.median(grains)), 2) if grains else None,
        "bloom_ring_lift_8bit_median": round(float(np.median(blooms)), 1) if blooms else None,
        "luma_hist_32": [round(float(v), 4) for v in luma_hist],
        "hue_hist_12_sat_weighted": {hue_names[i]: round(float(hue_hist[i]), 3) for i in range(12)},
        "luma_1s_sd": round(float(np.std(curves["luma_mean"])), 1), "sat_1s_sd": round(float(np.std(curves["sat_mean"])), 1),
    }
    (d / "color.json").write_text(json.dumps({"video": d.name, "video_palette": video_palette, "segment_palettes": seg_pal, "grade": grade, "curves_1s": curves}, indent=1))
    return f"{d.name}: luma {grade['luma_mean']} contrast {grade['contrast_rms_mean']} sat {grade['saturation_mean']} warm {grade['warm_frac_mean']} cool {grade['cool_frac_mean']} top: " + " ".join(f"{p['hex']}({p['share']:.2f})" for p in video_palette[:5])


def main():
    root = Path(sys.argv[1])
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    only = sys.argv[3] if len(sys.argv) > 3 else None
    dirs = sorted(p for p in root.iterdir() if (p / "shots.json").exists() and (only is None or p.name == only))
    cv2.setNumThreads(1)
    with ProcessPoolExecutor(jobs) as ex:
        for line in ex.map(one, dirs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
