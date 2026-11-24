#!/usr/bin/env python3
"""Per-frame measurements on the 30 fps frame dumps (every frame, no sampling).

Usage: 06_frame_metrics.py <work_dir> [jobs=8] [only=<video-stem>]
Writes <work>/<video>/frame_metrics.csv  (one row per frame)

Columns
  f,t                      frame index, seconds
  luma_mean,luma_std       Rec.709 luma 0-255: brightness, RMS contrast
  p01,p05,p50,p95,p99      luma percentiles (black / white levels)
  sat_mean,sat_p90         HSV saturation 0-255
  val_mean                 HSV value 0-255
  colorfulness             Hasler-Suesstrunk M3
  chroma_mean              CIELAB chroma C*ab
  lab_L,lab_a,lab_b        mean CIELAB (a>0 red, b>0 yellow -> warm)
  warm_frac,cool_frac      share of saturated pixels (S>60,V>40) with warm hue (300-360,0-90 deg) / cool hue (150-270 deg)
  sharp                    variance of Laplacian at 540x960
  edge_density             Canny edge pixel share at 270x480
  vignette                 mean luma of 4 corners / mean luma of centre (1.0 = none)
  mad                      mean abs luma difference to previous frame (0-255)
  hist_d                   Bhattacharyya distance of HSV histograms to previous frame (0-1)
  edge_change              share of edge pixels that are new vs previous frame (dilated compare)
  flow_mag,flow_med        mean / median optical-flow magnitude, % of frame height per frame
  g_scale                  global similarity scale per frame (1.0 = no zoom; >1 push-in)
  g_rot                    global rotation, degrees per frame
  g_tx,g_ty                global translation, % of frame width / height per frame (content motion)
  g_inl                    RANSAC inlier ratio of the global fit (low = not a rigid camera move)
  resid_med                median flow magnitude after removing global motion, % of frame height
"""
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

FPS = 30.0
COLS = [
    "f", "t", "luma_mean", "luma_std", "p01", "p05", "p50", "p95", "p99", "sat_mean", "sat_p90", "val_mean",
    "colorfulness", "chroma_mean", "lab_L", "lab_a", "lab_b", "warm_frac", "cool_frac", "sharp", "edge_density",
    "vignette", "mad", "hist_d", "edge_change", "flow_mag", "flow_med", "g_scale", "g_rot", "g_tx", "g_ty", "g_inl",
    "resid_med",
]


def luma709(bgr):
    b, g, r = bgr[..., 0].astype(np.float32), bgr[..., 1].astype(np.float32), bgr[..., 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def colorfulness(bgr):
    b, g, r = [bgr[..., i].astype(np.float32) for i in range(3)]
    rg = r - g
    yb = 0.5 * (r + g) - b
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def one_video(d: Path):
    frames = sorted((d / "frames").glob("*.jpg"))
    rows = []
    prev_small = prev_gray8 = prev_hist = prev_edges = None
    grid = None
    for i, fp in enumerate(frames):
        im2 = cv2.imread(str(fp), cv2.IMREAD_REDUCED_COLOR_2)  # 540x960
        im4 = cv2.resize(im2, (270, 480), interpolation=cv2.INTER_AREA)
        y = luma709(im4)
        hsv = cv2.cvtColor(im4, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(im4.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)
        h, s, v = hsv[..., 0].astype(np.float32) * 2.0, hsv[..., 1].astype(np.float32), hsv[..., 2].astype(np.float32)
        satmask = (s > 60) & (v > 40)
        nsat = max(int(satmask.sum()), 1)
        warm = ((h >= 300) | (h < 90)) & satmask
        cool = ((h >= 150) & (h < 270)) & satmask
        pcts = np.percentile(y, [1, 5, 50, 95, 99])
        gray2 = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
        sharp = float(cv2.Laplacian(gray2, cv2.CV_64F).var())
        gray4 = cv2.cvtColor(im4, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray4, 80, 160)
        hh, ww = y.shape
        c = int(0.12 * ww)
        corners = np.concatenate([y[:c, :c].ravel(), y[:c, -c:].ravel(), y[-c:, :c].ravel(), y[-c:, -c:].ravel()])
        centre = y[int(0.35 * hh):int(0.65 * hh), int(0.3 * ww):int(0.7 * ww)]
        row = {
            "f": i, "t": round(i / FPS, 4),
            "luma_mean": y.mean(), "luma_std": y.std(),
            "p01": pcts[0], "p05": pcts[1], "p50": pcts[2], "p95": pcts[3], "p99": pcts[4],
            "sat_mean": s.mean(), "sat_p90": np.percentile(s, 90), "val_mean": v.mean(),
            "colorfulness": colorfulness(im4),
            "chroma_mean": float(np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2).mean()),
            "lab_L": float(lab[..., 0].mean()), "lab_a": float(lab[..., 1].mean()), "lab_b": float(lab[..., 2].mean()),
            "warm_frac": warm.sum() / nsat, "cool_frac": cool.sum() / nsat,
            "sharp": sharp, "edge_density": float((edges > 0).mean()),
            "vignette": float(corners.mean() / max(centre.mean(), 1e-3)),
        }
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [18, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, 1.0, 0.0, cv2.NORM_L1)
        gray8 = cv2.resize(gray4, (135, 240), interpolation=cv2.INTER_AREA)
        if prev_small is None:
            row.update({k: 0.0 for k in ("mad", "hist_d", "edge_change", "flow_mag", "flow_med", "g_rot", "g_tx", "g_ty", "resid_med")})
            row.update({"g_scale": 1.0, "g_inl": 1.0})
        else:
            row["mad"] = float(np.abs(y - prev_small).mean())
            row["hist_d"] = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            dil_prev = cv2.dilate(prev_edges, np.ones((5, 5), np.uint8))
            new_edges = (edges > 0) & (dil_prev == 0)
            row["edge_change"] = float(new_edges.sum() / max(int((edges > 0).sum()), 1))
            flow = cv2.calcOpticalFlowFarneback(prev_gray8, gray8, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            H8, W8 = gray8.shape
            if grid is None:
                ys, xs = np.mgrid[6:H8 - 6:6, 6:W8 - 6:6]
                # ignore the burned-in caption line (measured at 68.5-72.5 % of frame height) so word changes do not count as motion
                keep = ~((ys > 0.675 * H8) & (ys < 0.735 * H8) & (xs > 0.18 * W8) & (xs < 0.82 * W8))
                grid = (ys[keep].astype(np.float32), xs[keep].astype(np.float32))
            gy, gx = grid
            fl = flow[gy.astype(int), gx.astype(int)]
            mag = np.hypot(fl[:, 0], fl[:, 1])
            row["flow_mag"] = float(mag.mean() / H8 * 100)
            row["flow_med"] = float(np.median(mag) / H8 * 100)
            src = np.stack([gx, gy], 1)
            dst = src + fl
            M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=1.0, maxIters=400)
            if M is None:
                row.update({"g_scale": 1.0, "g_rot": 0.0, "g_tx": 0.0, "g_ty": 0.0, "g_inl": 0.0, "resid_med": row["flow_med"]})
            else:
                sc = float(np.hypot(M[0, 0], M[1, 0]))
                rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
                cx, cy = W8 / 2, H8 / 2
                # translation measured at the frame centre so zoom does not leak into pan
                tx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx
                ty = M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy
                pred = (src @ M[:, :2].T) + M[:, 2]
                resid = np.hypot(*(dst - pred).T)
                row.update({
                    "g_scale": sc, "g_rot": rot, "g_tx": float(tx / W8 * 100), "g_ty": float(ty / H8 * 100),
                    "g_inl": float(inl.mean()) if inl is not None else 0.0,
                    "resid_med": float(np.median(resid) / H8 * 100),
                })
        rows.append(row)
        prev_small, prev_gray8, prev_hist, prev_edges = y, gray8, hist, edges
    with open(d / "frame_metrics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(float(r[k]), 5) if k not in ("f",) else r[k]) for k in COLS})
    return d.name, len(rows)


def main():
    root = Path(sys.argv[1])
    jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    only = sys.argv[3] if len(sys.argv) > 3 else None
    dirs = sorted(p for p in root.iterdir() if (p / "frames").is_dir() and (only is None or p.name == only))
    cv2.setNumThreads(1)
    with ProcessPoolExecutor(jobs) as ex:
        for name, n in ex.map(one_video, dirs):
            print(name, n, "frames", flush=True)


if __name__ == "__main__":
    main()
